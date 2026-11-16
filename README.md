# xr_media_ros

[中文](README.zh-CN.md)

ROS 2 bridge that connects image and audio topics with browsers in both directions and publishes WebXR poses, buttons and hand joints.

It uses the [xr_media](https://github.com/AgilexOpensource/xr_media) SDK.

## Requirements

Tested on Ubuntu 22.04 with ROS 2 Humble.

## Install

```bash
mkdir -p ~/xr_media_ws/src && cd ~/xr_media_ws
git clone https://github.com/AgilexOpensource/xr_media_ros.git src/xr_media_ros
sudo apt install ros-humble-audio-common-msgs
source /opt/ros/humble/setup.bash
```

Install the SDK with system pip and build:

```bash
pip3 install "git+https://github.com/AgilexOpensource/xr_media.git" 'numpy<2' 'setuptools<80'
colcon build --symlink-install
source install/setup.bash
```

Or, recommended to keep the system Python clean, a virtual environment that still sees the ROS Python packages:

```bash
python3 -m venv --system-site-packages ~/xr_media_ws/.venv
source ~/xr_media_ws/.venv/bin/activate
pip install "git+https://github.com/AgilexOpensource/xr_media.git" 'numpy<2' 'setuptools<80'
python3 -m colcon build --symlink-install
source install/setup.bash
```

Activate the venv in every new terminal before `source install/setup.bash`. `python3 -m colcon` makes the nodes use the venv Python; plain `colcon` would use the system Python, which cannot import `xr_media` from the venv.

## Quick start

Create the TLS certificate once. Each run overwrites the certificate and private key, so skip it if valid certificates exist. WebXR requires HTTPS, so the node exits with an error when the certificate is missing instead of serving HTTP.

```bash
xr_media --init-certs
```

Start the bridge:

```bash
ros2 launch xr_media_ros xr_media.launch.py
```

1. Open a printed URL, trust the certificate and grant media permissions.
2. Select a browser camera or microphone and start its uplink card.
3. View the matching return card.

The default configuration publishes browser uplinks to `/xr_media/camera` and `/xr_media/audio` and subscribes to them again as a loopback. Stop with `Ctrl+C`.

In a new terminal, load the environment first:

```bash
cd ~/xr_media_ws
source /opt/ros/humble/setup.bash
# only with the venv install
source .venv/bin/activate
source install/setup.bash
```

## More

- [Usage guide](docs/GUIDE.md): configuration, topics, QoS, XR data, RViz and common issues.

## License

Apache-2.0, see [LICENSE](LICENSE).
