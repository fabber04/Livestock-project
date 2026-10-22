"""Per-cow water intake from the trough camera, and GPS from the same tag.

Each animal wears a coloured collar. The camera at the south lip of the
trough reads that colour. The collar position is also the GPS fix. The
plant still removes water at one herd rate; this ledger only shares that
volume among the tags the camera has picked.
"""

import time

from ddroid_scene import (
    DRINK_SHIFT_S,
    DRINK_STATIONS,
    HERD,
    TAGS,
    WANDERERS,
    along_loop,
    collar_in_drink_view,
    collar_world,
)

CAMERA_HOLD_S = 1.5
# Squared RGB distance. Far enough for a shaded tag, short of hides and concrete.
_MAX_DIST_SQ = 10000


def tag_label(name):
    kind, number = name.split("_", 1)
    prefix = "C" if kind == "cow" else "W"
    return prefix + number


def tags_in_image(width, height, rgb, min_pixels=30):
    """Return tag names whose collar colour is present in an RGB frame."""
    if width <= 0 or height <= 0:
        return []
    count = width * height
    if len(rgb) < count * 3:
        return []
    palette = [
        (name, tuple(int(round(channel * 255)) for channel in rgba[:3]))
        for name, rgba in TAGS
    ]
    hits = {name: 0 for name, _rgba in TAGS}
    stride = 4 if count > 20000 else 1
    for index in range(0, count, stride):
        offset = index * 3
        red = rgb[offset]
        green = rgb[offset + 1]
        blue = rgb[offset + 2]
        if max(red, green, blue) < 90 or max(red, green, blue) - min(red, green, blue) < 50:
            continue
        best_name = None
        best_dist = _MAX_DIST_SQ
        for name, colour in palette:
            dist = (red - colour[0]) ** 2 + (green - colour[1]) ** 2 + (blue - colour[2]) ** 2
            if dist < best_dist:
                best_dist = dist
                best_name = name
        if best_name is not None:
            hits[best_name] += stride
    return [name for name, _rgba in TAGS if hits[name] >= min_pixels]


class HerdBook:
    """Litres credited to each collar, and the latest GPS fix."""

    def __init__(self):
        self.t = 0.0
        self.at_trough = False
        self.intake = {name: 0.0 for name, _rgba in TAGS}
        self.gps = {name: (0.0, 0.0) for name, _rgba in TAGS}
        self.seen = []
        self.in_gate = []
        self.source = "tag"
        self.unbilled_l = 0.0
        self._camera_ids = ()
        self._camera_time = 0.0
        self.body_poses()

    def note_camera(self, names):
        """Tags the latest drink-camera frame contained."""
        known = {name for name, _rgba in TAGS}
        self._camera_ids = tuple(name for name in names if name in known)
        self._camera_time = time.monotonic()

    def step(self, dt, drunk_l, at_trough):
        """Advance the herd and share this step's drinking among picked tags."""
        self.t += dt
        self.at_trough = bool(at_trough)
        self.body_poses()
        picked = self._picked(self.in_gate)
        if drunk_l > 0 and picked:
            share = drunk_l / len(picked)
            for name in picked:
                self.intake[name] += share
        elif drunk_l > 0:
            self.unbilled_l += drunk_l
        self.seen = picked

    def body_poses(self):
        """Model origin and yaw for every animal. Also refreshes GPS."""
        poses = {}
        active = self._active_indexes() if self.at_trough else ()
        station = 0
        for index, (name, x, y, z, yaw, _drink_y) in enumerate(HERD):
            if index in active:
                sx, sy, syaw = DRINK_STATIONS[station]
                station += 1
                poses[name] = (sx, sy, z, syaw)
            else:
                poses[name] = (x, y, z, yaw)
        for index, (name, speed, path) in enumerate(WANDERERS):
            x, y, yaw = along_loop(path, speed * self.t + index * 3.0)
            poses[name] = (x, y, 0.0, yaw)
        self.gps = {}
        gate = []
        for name, pose in poses.items():
            cx, cy, _cz = collar_world(*pose)
            self.gps[name] = (cx, cy)
            if collar_in_drink_view(*pose):
                gate.append(name)
        order = [name for name, _rgba in TAGS]
        self.in_gate = [name for name in order if name in gate]
        return poses

    def one_line(self):
        seen = " ".join(tag_label(name) for name in self.seen) or "none"
        bits = [
            f"{tag_label(name)} {self.intake[name]:.2f}L"
            for name, _rgba in TAGS
            if name.startswith("cow_")
        ]
        return f"intake {self.source} {seen} | " + " ".join(bits)

    def board_text(self):
        seen = " ".join(tag_label(name) for name in self.seen) or "none"
        lines = [f"{self.source} {seen}"]
        for name, _rgba in TAGS:
            if not name.startswith("cow_"):
                continue
            x, y = self.gps[name]
            lines.append(f"{tag_label(name)} {self.intake[name]:5.2f} L  {x:5.1f} {y:5.1f}")
        return "\n".join(lines)

    def intake_text(self):
        return ",".join(f"{name}:{self.intake[name]:.3f}" for name, _rgba in TAGS)

    def gps_text(self):
        return ";".join(f"{name}:{self.gps[name][0]:.2f},{self.gps[name][1]:.2f}" for name, _rgba in TAGS)

    def _active_indexes(self):
        count = len(HERD)
        shift = int(self.t / DRINK_SHIFT_S) % count
        return {shift % count, (shift + 1) % count}

    def _picked(self, in_gate):
        fresh = self._camera_time > 0 and (time.monotonic() - self._camera_time) < CAMERA_HOLD_S
        if fresh and self._camera_ids:
            seen = [name for name in in_gate if name in self._camera_ids]
            if seen:
                self.source = "camera"
                return seen
        self.source = "tag"
        return list(in_gate)
