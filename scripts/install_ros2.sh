#!/bin/bash
# ROS 2 Lyrical is the distribution built for Ubuntu 26.04 (Resolute).
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: wsl -d Ubuntu -u root -- bash scripts/install_ros2.sh"
  exit 1
fi

printf '%s\n' 'Acquire::ForceIPv4 "true";' 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/99force-ipv4

apt-get update
apt-get install -y curl ca-certificates gnupg

install -d -m 0755 /usr/share/keyrings
curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu resolute main" \
  > /etc/apt/sources.list.d/ros2.list

apt-get update
apt-get install -y \
  ros-lyrical-ros-base \
  ros-lyrical-std-msgs \
  python3-colcon-common-extensions \
  python3-rosdep

if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  rosdep init
fi

echo "ROS 2 Lyrical installed."
bash -lc "source /opt/ros/lyrical/setup.bash && ros2 --help | head -20"
