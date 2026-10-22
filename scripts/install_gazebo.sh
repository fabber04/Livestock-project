#!/bin/bash
set -euo pipefail
printf '%s\n' 'Acquire::ForceIPv4 "true";' 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/99force-ipv4
echo "--- curl ---"
curl -4 -I --max-time 25 http://archive.ubuntu.com/ubuntu/ | head -12 || true
echo "--- cache ---"
du -sh /var/cache/apt/archives || true
echo "--- installed ---"
if command -v gz >/dev/null 2>&1; then
  gz sim --versions || true
else
  echo "gz not installed"
fi
echo "--- retry install ---"
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::http::Timeout=30 -o Acquire::Retries=3 install -y gz-jetty python3-gz-transport15 python3-gz-msgs12
echo "--- done ---"
gz sim --versions
python3 -c "from gz.transport import Node; from gz.msgs.pose_pb2 import Pose; print('python bindings ok')"
