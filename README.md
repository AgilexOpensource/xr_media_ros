# xr_media_ros

[English](README.md) | [简体中文](README.zh-CN.md)

Bridge ROS 2 image and audio topics bidirectionally with browsers, and publish WebXR poses, buttons and hand joints.

SDK repository: [xr_media](https://github.com/AgilexOpensource/xr_media).

## Installation

### 1. Prepare the environment

```bash
mkdir -p ~/xr_media_ws/src && cd ~/xr_media_ws
git clone https://github.com/AgilexOpensource/xr_media_ros.git src/xr_media_ros
source /opt/ros/humble/setup.bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

`--system-site-packages` exposes ROS Python dependencies.

To install into the system Python instead, skip the two venv commands here and in new terminals; the remaining commands are unchanged. On Ubuntu 24.04 / Jazzy and later, system pip additionally requires `--break-system-packages`.

### 2. Install dependencies

```bash
python3 -m pip install "git+https://github.com/AgilexOpensource/xr_media.git" 'numpy<2' 'setuptools<80'
sudo apt install ros-humble-audio-common-msgs
```

### 3. Build the bridge

```bash
python3 -m colcon build --symlink-install
source install/setup.bash
```

`python3 -m colcon` binds the node to the venv Python; plain `colcon` would use the system Python, which cannot import `xr_media`.

## Run

### Initial certificate setup

```bash
xr_media --init-certs
```

Each execution overwrites the certificate and private key; skip this step if valid certificates already exist.

### Start the bridge

```bash
ros2 launch xr_media_ros xr_media.launch.py
```

1. Open a printed URL, trust the certificate and grant media permissions.
2. Select a browser camera or microphone and start its uplink card.
3. View the corresponding return card.

The default configuration publishes browser uplinks to `/xr_media/camera` and `/xr_media/audio`, then subscribes to them for loopback. Stop with `Ctrl+C`.

In a new terminal, load the environment before running the launch command:

```bash
cd ~/xr_media_ws
source /opt/ros/humble/setup.bash
source .venv/bin/activate
source install/setup.bash
```

## More

- [Usage guide](docs/GUIDE.md): configuration, topics, QoS, XR data, RViz and common issues.

## License

Apache-2.0; see [LICENSE](LICENSE).
