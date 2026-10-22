"""Start the world headless and save one frame from each camera.

Run inside Ubuntu (WSL) from the repository root:

    python3 tools/snapshot_world.py [label]

Frames go to simulation/frames/<label>_overview.png and
<label>_drink_cam.png. No window is opened.
"""

import os
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_DIR = os.path.join(ROOT, "simulation")
WORLD = os.path.join(SIM_DIR, "worlds", "ddroid_water_point.sdf")
FRAME_DIR = os.path.join(SIM_DIR, "frames")
TOPICS = ("overview", "drink_cam")
WAIT_S = 90

sys.path.insert(0, SIM_DIR)

from run_sim import _load_gz, _write_png  # noqa: E402


def _resource_path():
    groups = os.path.join(SIM_DIR, "models")
    paths = [os.path.join(groups, name) for name in sorted(os.listdir(groups))]
    existing = os.environ.get("GZ_SIM_RESOURCE_PATH")
    if existing:
        paths.append(existing)
    return ":".join(paths)


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    os.makedirs(FRAME_DIR, exist_ok=True)
    os.environ["GZ_PARTITION"] = f"ddroid_snapshot_{os.getpid()}"
    os.environ["GZ_SIM_RESOURCE_PATH"] = _resource_path()
    server = subprocess.Popen(
        ["gz", "sim", "-s", "-r", "--headless-rendering", "-v", "2", WORLD],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    Node, _Pose, _Boolean, Image, _Marker = _load_gz()
    node = Node()
    frames = {}
    done = threading.Event()

    def handler(topic):
        def on_image(msg):
            data = bytes(msg.data)
            need = msg.width * msg.height * 3
            if topic in frames or msg.width <= 0 or len(data) < need:
                return
            frames[topic] = (msg.width, msg.height, data[:need])
            if len(frames) == len(TOPICS):
                done.set()

        return on_image

    try:
        for topic in TOPICS:
            node.subscribe(Image, f"/{topic}", handler(topic))
        deadline = time.time() + WAIT_S
        while not done.is_set() and time.time() < deadline:
            if server.poll() is not None:
                break
            # Skip the first frames; the scene is still streaming in.
            done.wait(0.5)
        if not done.is_set():
            error = ""
            if server.poll() is not None:
                error = server.stderr.read()[-2000:]
            missing = ", ".join(topic for topic in TOPICS if topic not in frames)
            raise SystemExit(f"No frame from {missing} within {WAIT_S} s.\n{error}")
        time.sleep(3)
        frames.clear()
        done.clear()
        done.wait(15)
        for topic in TOPICS:
            if topic not in frames:
                raise SystemExit(f"Camera {topic} stopped publishing.")
            width, height, rgb = frames[topic]
            path = os.path.join(FRAME_DIR, f"{label}_{topic}.png")
            _write_png(path, width, height, rgb)
            print(path)
    finally:
        server.terminate()
        try:
            server.wait(10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
