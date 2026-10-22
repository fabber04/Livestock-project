#!/bin/bash
# Build the ROS 2 workspace and run the water-point demonstration.
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
exec ros2 run ddroid_water_point ddroid_demo "$@"
