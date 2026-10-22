#!/bin/bash
# Open the DDROID yard in Gazebo.
# Hardware OpenGL through WSLg's D3D12 driver, on the NVIDIA GTX 1650.
# The Intel GPU is also present; the adapter name keeps Gazebo off it.
export DISPLAY=:0
export XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir
export QT_QPA_PLATFORM=xcb
export GALLIUM_DRIVER=d3d12
export MESA_LOADER_DRIVER_OVERRIDE=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA GeForce GTX 1650"
export GZ_PARTITION=ddroid
unset LIBGL_ALWAYS_SOFTWARE
unset WAYLAND_DISPLAY
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIM="$ROOT/simulation"
# The world includes props as model://<name>. Each group folder under
# models/ (Trees, Cattle, Kraal, ...) holds those names one level down.
MODEL_PATH=""
for category in "$SIM"/models/*/; do
  [ -d "$category" ] || continue
  category="${category%/}"
  MODEL_PATH="${MODEL_PATH:+$MODEL_PATH:}$category"
done
if [ -z "$MODEL_PATH" ]; then
  echo "No models under $SIM/models. Run: python3 simulation/build_world.py" >&2
  exit 1
fi
export GZ_SIM_RESOURCE_PATH="$MODEL_PATH${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
exec gz sim -v 2 -r "$SIM/worlds/ddroid_water_point.sdf"
