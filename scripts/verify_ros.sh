#!/bin/bash
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source /opt/ros/lyrical/setup.bash
export DDROID_SIM="$ROOT/simulation"
export GZ_PARTITION=ddroid
cd "$ROOT/ros2_ws"
colcon build --packages-select ddroid_water_point
# shellcheck disable=SC1091
source "$ROOT/ros2_ws/install/setup.bash"
python3 "$ROOT/simulation/test_control.py"
ros2 run ddroid_water_point ddroid_demo > /tmp/ddroid_demo.log 2>&1 &
DEMO_PID=$!
cleanup() {
  kill "$DEMO_PID" 2>/dev/null || true
  wait "$DEMO_PID" 2>/dev/null || true
}
trap cleanup EXIT
sleep 4
timeout 25 ros2 topic echo --once /ddroid/status
echo "ROS topic check passed"
