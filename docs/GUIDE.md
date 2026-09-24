# ROS 2 usage guide

[English](GUIDE.md) | [简体中文](GUIDE.zh-CN.md) · [Back to README](../README.md)

## Contents

- [Media configuration](#media-configuration)
- [Launch and RViz](#launch-and-rviz)
- [XR data and topics](#xr-data-and-topics)
- [Verification and common issues](#verification-and-common-issues)
- [Alternative installation methods](#alternative-installation-methods)
- [Joint index reference](#joint-index-reference)

## Media configuration

`input`/`output` are relative to the ROS bridge, not the browser:

| Configuration group | ROS behavior | Media direction |
|---|---|---|
| `media.video_input` | Subscribe to images or read local sources | PC → browser |
| `media.video_output` | Publish images | Browser → PC |
| `media.audio_input` | Subscribe to PCM audio | PC → browser |
| `media.audio_output` | Publish PCM audio | Browser → PC |

This example connects existing ROS topics; add or remove entries as needed. The default loopback subscribes to `/xr_media/camera` and `/xr_media/audio`; this example instead subscribes to `/camera` and `/audio`, which must be provided by other nodes.

Each mapping key names a card; its value selects a topic or local source. Example:

```yaml
xr_media_node:
  ros__parameters:
    topic_prefix: /xr_media

    server:
      port: 9443
      max_clients: 1
      cert_path: ""
      key_path: ""

    media:
      video_input:
        video0: /camera
      video_output:
        video1: /camera
      audio_input:
        audio0: /audio
      audio_output:
        audio1: /audio
```

Sources must be unique within each group; ROS input topics must be absolute. Images update a latest-frame buffer without an added rate cap; not every message is transmitted. Source timestamps are retained in SDK frames, not a browser cross-device synchronization guarantee. Output
topics always use `topic_prefix`: `/camera` becomes `/xr_media/camera` and
`/audio` becomes `/xr_media/audio`. An output already beginning with the
configured prefix is not prefixed twice.
Card IDs combine the configuration group and source, replacing source separators with underscores. Sources such as `/camera/front` and `/camera_front` in the same group can produce identical IDs; the node rejects startup on a collision. Rename one of the sources.

### Local video sources

Only `media.video_input` accepts these local sources; replace `/camera` in the example:

| Value | Source | Requirement |
|---|---|---|
| `video_test` | Generated test image | No external image source |
| `camera:0` | PC camera | OpenCV; adjust the device index |
| `video_file:/path/to/movie.mp4` | PC video file | OpenCV; replace with an actual path |

Files follow their own frame rate and loop by default; the page supports pause, resume, stop and replay.

Cameras and local video files need the SDK's OpenCV extra. Install with `python -m pip install "xr_media[opencv] @ git+https://github.com/AgilexOpensource/xr_media.git" 'numpy<2' 'setuptools<80'`. If Colcon provides the SDK, only add a compatible OpenCV installation to that Python environment.

### Server parameters

| Parameter | Node default | Meaning |
|---|---|---|
| `topic_prefix` | `/xr_media` | Prefix for published topics and frame names |
| `server.port` | `9443` | TCP port, 1–65535 |
| `server.max_clients` | `1` | Positive integer; the shipped YAML explicitly sets **2** |
| `server.cert_path` / `server.key_path` | Empty strings | Discover user TLS files; supply both for custom paths |

Configuration is read at startup. The server listens on all interfaces and uses H.264 video.

### Message formats and QoS

| Media | ROS message | Format | QoS |
|---|---|---|---|
| Video | `sensor_msgs/Image` | `bgr8`, `rgb8`, `mono8` | Keep Last, depth 2, Best Effort, Volatile |
| Audio | `audio_common_msgs/AudioData` | 16 kHz mono little-endian signed 16-bit PCM, no WAV header | Keep Last, depth 10, Reliable, Volatile |

QoS defines delivery behavior between publishers and subscribers; use compatible
settings when connecting other nodes.

### Use your own configuration

Edit `config/xr_media.yaml`, or pass another file:

```bash
ros2 launch xr_media_ros xr_media.launch.py config:=/path/to/xr_media.yaml
```

Advanced: run the node directly and override parameters using dotted names:

```bash
ros2 run xr_media_ros xr_media_node \
  --ros-args --params-file /path/to/xr_media.yaml -p server.max_clients:=2
```

## Launch and RViz

### Launch modes

| Goal | Command |
|---|---|
| Bridge only | `ros2 launch xr_media_ros xr_media.launch.py` |
| Bridge, visualizer and RViz | `ros2 launch xr_media_ros xr_media_rviz.launch.py` |
| Add visualization to a running bridge | `ros2 launch xr_media_ros xr_hand_visualizer.launch.py` |

Do not run the first two together: their default ports conflict. The combined launch accepts `config:=/path/to/xr_media.yaml` and `rviz_config:=/path/to/view.rviz`.

For a custom bridge prefix, pass the same value to the standalone visualizer:
`ros2 launch xr_media_ros xr_hand_visualizer.launch.py topic_prefix:=/custom/xr`.
The integrated launch reads `topic_prefix` from the `xr_media_node` section
of its `config` YAML (falling back to `/**` and then `/xr_media`). The shipped
RViz display topics use `/xr_media`; for another prefix, update them in RViz
and save/pass your own `rviz_config` file.

### View in RViz

First enter an XR session with hand tracking on the headset.
In RViz, add a `PoseArray` display for each hand, set `Fixed Frame` to `world`,
Topic `Reliability Policy` to `Best Effort`, `Durability Policy` to `Volatile`,
and optionally Depth to `10`. Direct pose display does not need the Marker
converter. For bone connections and colored joint markers, start the separate
visualizer and subscribe to `hand_markers`.

## XR data and topics

The default prefix is `/xr_media`. `{side}` is `left` or `right`; `{role}` is `headset`, `left_controller` or `right_controller`.

| Topic | Message type | Content / publication condition |
|---|---|---|
| `/xr_media/{role}/transform` | `geometry_msgs/msg/TransformStamped` | Pose and TF while the corresponding device is tracked |
| `/xr_media/{side}_controller/buttons` | `sensor_msgs/msg/Joy` | Buttons and axes while the controller or hand is tracked |
| `/xr_media/{side}_controller/hand` | `geometry_msgs/msg/PoseArray` | Published when all 25 hand joints are available |
| `/xr_media/{side}_controller/hand_markers` | `visualization_msgs/msg/MarkerArray` | Generated from hand messages by the separate visualizer |
| `/xr_media/status` | `std_msgs/msg/String` | JSON statistics every second; no XR session required |

### Coordinates and timestamps
- Poses are converted from WebXR to Z-up: +X forward, +Y left, +Z up.
- Headset, controllers and hands share `world`; obtain relative transforms from TF. Frame names derive from `topic_prefix`.
- Hand `header.stamp` is the bridge callback time, not capture time; `header.frame_id` is `world`.
- Joint positions are absolute in that frame, not relative to the wrist or adjacent joints.

### Buttons and axes

`/xr_media/left_controller/buttons` and `/xr_media/right_controller/buttons` use `sensor_msgs/msg/Joy`. Both sides share the same zero-based array indices.

**`axes`**

| Index | Source field | Meaning |
|---:|---|---|
| 0 | `stick_x` | Thumbstick X axis |
| 1 | `stick_y` | Thumbstick Y axis |
| 2 | `trigger_analog` | Analog trigger value |
| 3 | `grip_analog` | Analog grip value |

**`buttons`**

| Index | Source field | Meaning |
|---:|---|---|
| 0 | `trigger_pressed` | Trigger pressed |
| 1 | `grip_pressed` | Grip pressed |
| 2 | `stick_clicked` | Thumbstick pressed |
| 3 | `face_primary` | Primary button |
| 4 | `face_secondary` | Secondary button |

- `buttons` values are `0` / `1` for released / pressed.
- In hand-tracking mode, a pinch maps to trigger input rather than a physical button; browser-synthesized hand gamepad values are ignored.
- Messages are published only while the corresponding controller or hand is tracked; consumers should check for stale data.

## Verification and common issues

After starting a video uplink, check from another terminal with the ROS environment loaded:

```bash
ros2 topic hz /xr_media/camera
ros2 topic info /xr_media/camera --verbose
ros2 topic echo /xr_media/status --once
```

`status` uses `std_msgs/msg/String` with JSON in `data`: SDK media statistics, XR received/dispatched/replaced counts, `conversion_errors` (image conversion failures) and `xr_samples` (XR samples received by the bridge). Counts do not confirm browser display or playback.

| Symptom | Check |
|---|---|
| No return video | The default is loopback; start the browser uplink and check its input topic |
| Image conversion errors | Use `bgr8`, `rgb8` or `mono8`; check `step` and data length |
| RViz receives no image | Select Best Effort and Volatile; image queue depth is 2 |
| Incorrect audio | Use 16 kHz mono little-endian int16 PCM; 20 ms is 320 samples / 640 bytes |
| No hand messages | Enter XR and check complete tracking; missing joints suppress publication |
| Port already in use | Avoid duplicate bridges or change `server.port` |
| No RViz display with a custom prefix | Update display topics and save a custom RViz configuration |

### Limitations

- Clients share ROS topics and frames; namespaces are not isolated per client.
- Only one client can use an XR session at a time.
- See the [SDK guide](https://github.com/AgilexOpensource/xr_media) for network and browser limitations.

## Alternative installation methods

The README installs the SDK directly from Git. Choose one alternative below if needed; first prepare ROS and the virtual environment as described in the README.

### Clone and install the SDK with pip

```bash
git clone https://github.com/AgilexOpensource/xr_media.git /path/to/xr_media
python -m pip install /path/to/xr_media 'numpy<2' 'setuptools<80'
```

Replace the source path, then continue with the README's rosdep and bridge build steps.

### Build the SDK and bridge together with Colcon

Place both source packages under the workspace's `src/`. From the workspace root, use these commands instead of the README's dependency installation and build commands:

```bash
python -m pip install aiohttp aiortc av 'numpy<2' 'setuptools<80'
rosdep install --from-paths src/xr_media src/xr_media_ros --ignore-src -y
python /usr/bin/colcon build --base-paths src --packages-up-to xr_media_ros --symlink-install
source install/setup.bash
```

Adjust both source paths to their actual locations. Do not also install the SDK itself with pip in this workflow.

## Joint index reference

Both hands use standard `geometry_msgs/msg/PoseArray`; no custom message
package is required:

- Left: `/xr_media/left_controller/hand`
- Right: `/xr_media/right_controller/hand`

`poses` uses **fixed, zero-based indices**, identical for both hands and matching
`HAND_JOINT_NAMES` in `xr_media_ros/hand_joints.py`. Each element contains
`position` in metres and `orientation` as an x/y/z/w quaternion.

| Index | WebXR joint name |
|---:|---|
| 0 | `wrist` |
| 1 | `thumb-metacarpal` |
| 2 | `thumb-phalanx-proximal` |
| 3 | `thumb-phalanx-distal` |
| 4 | `thumb-tip` |
| 5 | `index-finger-metacarpal` |
| 6 | `index-finger-phalanx-proximal` |
| 7 | `index-finger-phalanx-intermediate` |
| 8 | `index-finger-phalanx-distal` |
| 9 | `index-finger-tip` |
| 10 | `middle-finger-metacarpal` |
| 11 | `middle-finger-phalanx-proximal` |
| 12 | `middle-finger-phalanx-intermediate` |
| 13 | `middle-finger-phalanx-distal` |
| 14 | `middle-finger-tip` |
| 15 | `ring-finger-metacarpal` |
| 16 | `ring-finger-phalanx-proximal` |
| 17 | `ring-finger-phalanx-intermediate` |
| 18 | `ring-finger-phalanx-distal` |
| 19 | `ring-finger-tip` |
| 20 | `pinky-finger-metacarpal` |
| 21 | `pinky-finger-phalanx-proximal` |
| 22 | `pinky-finger-phalanx-intermediate` |
| 23 | `pinky-finger-phalanx-distal` |
| 24 | `pinky-finger-tip` |

For example, `poses[4]` is the thumb tip and `poses[9]` is the index finger tip.
Check `len(poses) == 25` before accessing joints. If tracking is lost, no joint
data is available, or any joint is missing, no message is published for that
hand. The bridge never sends empty arrays, compacts indices, or inserts zero
poses. The publisher and topic remain available, and publication resumes when
complete tracking returns. Consumers should use timestamps to detect stale data.
