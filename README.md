# xr_media_ros

[English](README.md) | [简体中文](README.zh-CN.md)

Bridge ROS 2 image and audio topics bidirectionally with browsers, and publish WebXR poses, buttons and hand joints.

SDK repository: [xr_media](https://github.com/AgilexOpensource/xr_media).

## Installation

Requires ROS 2, Colcon, rosdep, Git and Python venv. Place this package under your workspace's `src/`. Run the following commands from the workspace root, using Humble as the example.

### 1. Prepare the environment

```bash
source /opt/ros/humble/setup.bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

`--system-site-packages` exposes ROS Python dependencies. Before first using rosdep, run `sudo rosdep init` and `rosdep update`; skip init if already initialized.

### 2. Install dependencies

```bash
python -m pip install "git+https://github.com/AgilexOpensource/xr_media.git" 'numpy<2' 'setuptools<80'
rosdep install --from-paths src/xr_media_ros --ignore-src --skip-keys xr_media -y
```

Pip provides the SDK, so rosdep skips `xr_media`. Adjust `src/xr_media_ros` to the actual source location.

### 3. Build the bridge

```bash
colcon build --base-paths src --packages-select xr_media_ros --symlink-install
source install/setup.bash
```

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

In a new terminal, load the environment from the workspace root before running the launch command:

```bash
source /opt/ros/humble/setup.bash
source .venv/bin/activate
source install/setup.bash
```

## More

- [Usage guide](docs/GUIDE.md): configuration, topics, QoS, XR data, RViz and common issues.

## License

Apache-2.0; see [LICENSE](LICENSE).
