"""Connect the DDROID demonstration to a running Gazebo world.

Gazebo is the 3D view. This process owns the watering logic and moves the
water surfaces, float markers, pump lamp and mode lamp to match it.
"""

import math
import os
import struct
import sys
import threading
import time
import zlib

os.environ.setdefault("GZ_PARTITION", "ddroid")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ddroid_control import Controller, Plant
from ddroid_demo import run_demo
from ddroid_scene import (
    CAMERA_POSE,
    INTAKE_XYZ,
    MODE_LAMP_XYZ,
    PUMP_XYZ,
    STATUS_XYZ,
    SLICES,
    SUPPLY,
    SUPPLY_LOW,
    TROUGH,
    TROUGH_CUTOFF,
    TROUGH_HIGH,
    TROUGH_LOW,
    slice_pose,
    switch_anchor,
    visible_slice_count,
)
from ddroid_track import HerdBook, tags_in_image

WORLD_NAME = "ddroid"
FRAME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
HIDDEN = (0.0, 0.0, -4.0)


def _load_gz():
    try:
        from gz.transport import Node
        from gz.msgs.pose_pb2 import Pose
        from gz.msgs.boolean_pb2 import Boolean
        from gz.msgs.image_pb2 import Image
        from gz.msgs.marker_pb2 import Marker
        return Node, Pose, Boolean, Image, Marker
    except ImportError:
        from gz.transport15 import Node
        from gz.msgs12.pose_pb2 import Pose
        from gz.msgs12.boolean_pb2 import Boolean
        from gz.msgs12.image_pb2 import Image
        from gz.msgs12.marker_pb2 import Marker
        return Node, Pose, Boolean, Image, Marker


def _write_png(path, width, height, rgb):
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    rows = []
    stride = width * 3
    for y in range(height):
        rows.append(b"\x00" + rgb[y * stride : (y + 1) * stride])
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(png)


class GazeboView:
    def __init__(self, herd=None):
        self.herd = herd if herd is not None else HerdBook()
        Node, Pose, Boolean, Image, Marker = _load_gz()
        self._Pose = Pose
        self._Boolean = Boolean
        self._Image = Image
        self._Marker = Marker
        self._node = Node()
        self._status_pub = self._node.advertise("/marker", Marker)
        self._service = f"/world/{WORLD_NAME}/set_pose"
        self._last = {}
        self._frame_lock = threading.Lock()
        self._frame = None
        self._warned = False
        self._wait_for_world()
        self._subscribe_named("overview", self._on_image, "Saving frames from", "/overview")
        self._subscribe_named("drink_cam", self._on_drink_image, "Drink camera", "/drink_cam")

    def _wait_for_world(self):
        deadline = time.time() + 90
        while time.time() < deadline:
            try:
                services = list(self._node.service_list())
            except Exception:
                services = []
            if any(self._service in item for item in services):
                print(f"Connected to Gazebo service {self._service}")
                return
            time.sleep(0.5)
        raise SystemExit(
            "Gazebo did not advertise "
            f"{self._service}. Start Gazebo with scripts/launch_gui.sh first."
        )

    def _subscribe_named(self, key, callback, label, fallback):
        topics = []
        try:
            topics = list(self._node.topic_list())
        except Exception:
            topics = []
        preferred = [topic for topic in topics if key in topic and "camera_info" not in topic]
        candidates = preferred or [fallback]
        for topic in candidates:
            try:
                if self._node.subscribe(self._Image, topic, callback):
                    print(f"{label} {topic}")
                    return
            except Exception as exc:
                print(f"Camera subscribe failed for {topic}: {exc}")
        print(f"No {key} camera topic yet; the 3D window is still the live view.")

    def _on_image(self, msg):
        data = bytes(msg.data)
        if msg.width <= 0 or msg.height <= 0 or len(data) < msg.width * msg.height * 3:
            return
        rgb = data[: msg.width * msg.height * 3]
        with self._frame_lock:
            self._frame = (msg.width, msg.height, rgb)

    def _on_drink_image(self, msg):
        data = bytes(msg.data)
        if msg.width <= 0 or msg.height <= 0 or len(data) < msg.width * msg.height * 3:
            return
        found = tags_in_image(msg.width, msg.height, data[: msg.width * msg.height * 3])
        self.herd.note_camera(found)

    def save_frame(self, label):
        with self._frame_lock:
            frame = self._frame
        if frame is None:
            return
        os.makedirs(FRAME_DIR, exist_ok=True)
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in label)[:60]
        path = os.path.join(FRAME_DIR, f"{safe}.png")
        width, height, rgb = frame
        _write_png(path, width, height, rgb)
        print(f"Frame saved: {path}")

    def _move(self, name, pose, yaw=0.0):
        key = (round(pose[0], 4), round(pose[1], 4), round(pose[2], 4), round(yaw, 3))
        if self._last.get(name) == key:
            return
        req = self._Pose()
        req.name = name
        req.position.x = pose[0]
        req.position.y = pose[1]
        req.position.z = pose[2]
        req.orientation.z = math.sin(yaw / 2.0)
        req.orientation.w = math.cos(yaw / 2.0)
        ok, _response = self._node.request(self._service, req, self._Pose, self._Boolean, 200)
        if ok:
            self._last[name] = key
        elif not self._warned:
            print(f"Gazebo rejected a pose update for {name}.")
            self._warned = True

    def _marker(self, name, anchor, active):
        parked = (anchor[0], anchor[1], -4.0)
        self._move(f"{name}_wet", anchor if active else parked)
        self._move(f"{name}_dry", parked if active else anchor)

    def _mode_lamp(self, mode):
        selected = mode.lower()
        for name in ("stopped", "idle", "refilling", "manual", "fault"):
            pose = MODE_LAMP_XYZ if name == selected else (MODE_LAMP_XYZ[0], MODE_LAMP_XYZ[1], -4.0)
            self._move(f"mode_{name}", pose)

    def update(self, plant, ctl):
        for prefix, vessel, level in (
            ("supply", SUPPLY, plant.supply_fraction()),
            ("trough", TROUGH, plant.trough_fraction()),
        ):
            count = visible_slice_count(level)
            for index in range(SLICES):
                self._move(
                    f"{prefix}_water_{index:02d}",
                    slice_pose(vessel, index, visible=index < count),
                )
        low, high, source, cutoff = plant.raw_switches()
        self._marker("supply_low", switch_anchor(SUPPLY, SUPPLY_LOW), source)
        self._marker("trough_low", switch_anchor(TROUGH, TROUGH_LOW, -0.80), low)
        self._marker("trough_high", switch_anchor(TROUGH, TROUGH_HIGH, 0.0), high)
        self._marker("trough_cutoff", switch_anchor(TROUGH, TROUGH_CUTOFF, 0.80), cutoff)
        lamp_z = PUMP_XYZ[2] + 0.36
        on_pose = (PUMP_XYZ[0], PUMP_XYZ[1], lamp_z if plant.hardware_pump else -4.0)
        off_pose = (PUMP_XYZ[0], PUMP_XYZ[1], -4.0 if plant.hardware_pump else lamp_z)
        self._move("pump_lamp_on", on_pose)
        self._move("pump_lamp_off", off_pose)
        self._mode_lamp(ctl.mode)
        self._animals()
        self._publish_status(plant, ctl)

    def _animals(self):
        """Place each cow from the collar ledger, including animals at the lip."""
        for name, (x, y, z, yaw) in self.herd.body_poses().items():
            self._move(name, (x, y, z), yaw=yaw)

    def _publish_status(self, plant, ctl):
        """White text on the board facing the opening camera."""
        fault = ctl.fault or "none"
        pump = "ON" if plant.hardware_pump else "OFF"
        herd = "drinking" if (not plant.hardware_pump and plant.trough_l > 0.05) else "waiting"
        marker = self._Marker()
        marker.action = marker.ADD_MODIFY
        marker.type = marker.TEXT
        marker.ns = "ddroid_status"
        marker.id = 1
        marker.text = (
            f"{ctl.mode}   pump {pump}\n"
            f"trough {ctl.trough_state()}  {plant.trough_l:.1f} L\n"
            f"supply {ctl.supply_state()}  {plant.supply_l:.1f} L\n"
            f"livestock {herd}\n"
            f"fault {fault}"
        )
        marker.scale.x = 0.16
        marker.scale.y = 0.16
        marker.scale.z = 0.16
        marker.pose.position.x = STATUS_XYZ[0]
        marker.pose.position.y = STATUS_XYZ[1] - 0.08
        marker.pose.position.z = STATUS_XYZ[2]
        yaw = CAMERA_POSE[5] + math.pi
        marker.pose.orientation.z = math.sin(yaw / 2.0)
        marker.pose.orientation.w = math.cos(yaw / 2.0)
        for color in (marker.material.ambient, marker.material.diffuse, marker.material.emissive):
            color.r = 0.96
            color.g = 0.94
            color.b = 0.82
            color.a = 1.0
        self._status_pub.publish(marker)
        self._publish_intake()

    def _publish_intake(self):
        """Litres and GPS for the cows the trough camera is tracking."""
        marker = self._Marker()
        marker.action = marker.ADD_MODIFY
        marker.type = marker.TEXT
        marker.ns = "ddroid_intake"
        marker.id = 1
        marker.text = self.herd.board_text()
        marker.scale.x = 0.11
        marker.scale.y = 0.11
        marker.scale.z = 0.11
        marker.pose.position.x = INTAKE_XYZ[0]
        marker.pose.position.y = INTAKE_XYZ[1]
        marker.pose.position.z = INTAKE_XYZ[2]
        yaw = CAMERA_POSE[5] + math.pi
        marker.pose.orientation.z = math.sin(yaw / 2.0)
        marker.pose.orientation.w = math.cos(yaw / 2.0)
        for color in (marker.material.ambient, marker.material.diffuse, marker.material.emissive):
            color.r = 0.96
            color.g = 0.94
            color.b = 0.82
            color.a = 1.0
        self._status_pub.publish(marker)


def main():
    herd = HerdBook()
    view = GazeboView(herd)
    plant = Plant()
    ctl = Controller(*plant.raw_switches())
    view.update(plant, ctl)
    view.save_frame("00_startup")

    def log(text):
        print(text, flush=True)
        if text.startswith(("OPERATOR", "SAFETY", "Independent", "Demonstration")):
            slug = text.split("->", 1)[0].strip().lower().replace(" ", "_")
            view.save_frame(slug)

    run_demo(plant, ctl, view=view, herd=herd, dt=0.1, realtime=True, log=log, hold_s=20.0)
    view.update(plant, ctl)
    view.save_frame("99_complete")
    print("Gazebo is still running. Close the Gazebo window when you are finished.")


if __name__ == "__main__":
    main()
