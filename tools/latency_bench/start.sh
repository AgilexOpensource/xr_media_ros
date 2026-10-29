#!/bin/bash
# Usage: source <ws>/install/setup.bash && ./start.sh   (or WS=<ws> ./start.sh)
# Then open https://<pc-ip>:9444/ in the headset.
set -e
D="$(cd "$(dirname "$0")" && pwd)"
CAM_DEVICE="${CAM_DEVICE:-0}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-79}"
if [ -n "$WS" ]; then
  source "$WS/install/setup.bash"
fi
if ! ros2 pkg prefix xr_media_ros >/dev/null 2>&1; then
  echo "xr_media_ros not found: source <ws>/install/setup.bash first, or set WS=<ws>" >&2
  exit 1
fi
if [ -z "$PYTHON" ]; then
  if [ -n "$VIRTUAL_ENV" ]; then PYTHON="$VIRTUAL_ENV/bin/python"
  elif [ -n "$WS" ] && [ -x "$WS/.venv/bin/python" ]; then PYTHON="$WS/.venv/bin/python"
  else PYTHON=python3; fi
fi
if ! "$PYTHON" -c "import xr_media" 2>/dev/null; then
  echo "xr_media not importable by $PYTHON: activate its venv or set PYTHON=<python>" >&2
  exit 1
fi
trap 'kill 0' EXIT
ros2 run image_tools cam2image --ros-args -p device_id:=$CAM_DEVICE -p width:=640 -p height:=480 \
  -p frequency:=30.0 -p show_camera:=false --log-level warn -r image:=/usb_cam/image_raw &
"$PYTHON" "$D/run_node.py" --ros-args --params-file "$D/xr_cam_test.yaml" &
wait
