#!/usr/bin/env bash
# Run in Ubuntu after sourcing ROS and activating the project venv.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ROS_DISTRO:?First source /opt/ros/jazzy/setup.bash (or humble)}"
python - <<'PY'
import rclpy
import cv_bridge
import vision_msgs.msg
import diagnostic_msgs.msg
import launch_ros
import ultralytics
import onnxruntime
import pytest
PY
colcon build --symlink-install --event-handlers console_direct+
# ROS setup scripts can refer to optional unset environment variables.
set +u
source install/setup.bash
set -u
ros2 pkg executables ps9_cleaning_perception
ros2 launch ps9_cleaning_perception perception.launch.py --show-args
ros2 launch ps9_cleaning_perception demo.launch.py --show-args
colcon test --packages-select ps9_cleaning_perception --python-testing pytest --event-handlers console_direct+ --pytest-args -q
colcon test-result --verbose
