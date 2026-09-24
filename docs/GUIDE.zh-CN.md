# ROS 2 使用指南

[English](GUIDE.md) | [简体中文](GUIDE.zh-CN.md) · [返回首页](../README.zh-CN.md)

## 目录

- [媒体配置](#媒体配置)
- [启动与 RViz](#启动与-rviz)
- [XR 数据与话题](#xr-数据与话题)
- [验证与常见问题](#验证与常见问题)
- [其他安装方式](#其他安装方式)
- [关节索引参考](#关节索引参考)

## 媒体配置

`input`／`output` 相对于 ROS 桥接节点，不是相对于浏览器：

| 配置组 | ROS 行为 | 媒体方向 |
|---|---|---|
| `media.video_input` | 订阅图像或读取本地源 | PC → 浏览器 |
| `media.video_output` | 发布图像 | 浏览器 → PC |
| `media.audio_input` | 订阅 PCM 音频 | PC → 浏览器 |
| `media.audio_output` | 发布 PCM 音频 | 浏览器 → PC |

以下示例接入已有 ROS 话题，各组可按需增删条目。默认回环配置订阅 `/xr_media/camera` 和 `/xr_media/audio`；本例订阅独立的 `/camera` 和 `/audio`，需要外部节点提供数据。

映射键是卡片名称，值是话题或本地源。例如：

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

同一配置组的来源不可重复；ROS 输入话题使用绝对路径。图像到达后写入最新帧缓冲，不额外限频，也不保证每条消息都发送。消息时间戳保留在 SDK 帧中，不作为浏览器跨设备同步依据。输出话题统一使用 `topic_prefix`：
`/camera` 变为 `/xr_media/camera`，`/audio` 变为 `/xr_media/audio`。
已经带有所配置前缀的话题不会重复添加前缀。
卡片 ID 由配置组与来源生成，来源中的分隔符会转换为下划线。同组的 `/camera/front` 与 `/camera_front` 等来源可能产生相同 ID；发生冲突时节点拒绝启动，请调整其中一个来源名称。

### 本地视频源

仅 `media.video_input` 支持以下本地源，可替换示例中的 `/camera`：

| 值 | 来源 | 要求 |
|---|---|---|
| `video_test` | 测试图像 | 无外部图像来源 |
| `camera:0` | PC 摄像头 | OpenCV，设备索引按实际修改 |
| `video_file:/path/to/movie.mp4` | PC 视频文件 | OpenCV，替换为实际路径 |

文件按自身帧率播放，默认循环；页面可暂停、继续、停止和重播。

摄像头及本地视频文件需要 SDK 的 OpenCV 可选依赖，安装 SDK 时使用 `python -m pip install "xr_media[opencv] @ git+https://github.com/kehuanjack/xr_media.git" 'numpy<2' 'setuptools<80'`。若使用 Colcon 安装 SDK，只需在该 Python 环境补装兼容的 OpenCV。

### 服务参数

| 参数 | 节点默认值 | 说明 |
|---|---|---|
| `topic_prefix` | `/xr_media` | 发布话题及坐标系名称前缀 |
| `server.port` | `9443` | TCP 端口，1–65535 |
| `server.max_clients` | `1` | 正整数；内置 YAML 显式配置为 **2** |
| `server.cert_path` / `server.key_path` | 空字符串 | 自动查找用户 TLS 目录；自定义时成对指定 |

配置在启动时读取，服务监听所有网卡，视频编码为 H.264。

### 消息格式与 QoS

| 媒体 | ROS 消息 | 格式 | QoS |
|---|---|---|---|
| 视频 | `sensor_msgs/Image` | `bgr8`、`rgb8`、`mono8` | Keep Last，深度 2，Best Effort，Volatile |
| 音频 | `audio_common_msgs/AudioData` | 16 kHz、单声道、小端有符号 16 位 PCM，无 WAV 文件头 | Keep Last，深度 10，Reliable，Volatile |

QoS 是发布和订阅之间的传输约定；连接其他节点时需使用兼容设置。

### 使用自己的配置

编辑 `config/xr_media.yaml`，或指定其他配置文件：

```bash
ros2 launch xr_media_ros xr_media.launch.py config:=/path/to/xr_media.yaml
```

进阶：直接运行节点并覆盖参数时，使用点分名称：

```bash
ros2 run xr_media_ros xr_media_node \
  --ros-args --params-file /path/to/xr_media.yaml -p server.max_clients:=2
```

## 启动与 RViz

### 启动方式

| 目标 | 命令 |
|---|---|
| 仅桥接 | `ros2 launch xr_media_ros xr_media.launch.py` |
| 桥接、可视化和 RViz | `ros2 launch xr_media_ros xr_media_rviz.launch.py` |
| 已有桥接，仅增加可视化 | `ros2 launch xr_media_ros xr_hand_visualizer.launch.py` |

前两种不要同时启动，否则默认端口冲突。集成启动支持 `config:=/path/to/xr_media.yaml` 和 `rviz_config:=/path/to/view.rviz`。

独立可视化使用自定义前缀时，传入与桥接相同的值：
`ros2 launch xr_media_ros xr_hand_visualizer.launch.py topic_prefix:=/custom/xr`。
集成启动从 `config` YAML 的 `xr_media_node` 节读取 `topic_prefix`，
未设置时依次回退到 `/**` 节和 `/xr_media`。附带 RViz 配置的话题仍为
`/xr_media`；使用其他前缀时，在 RViz 中修改显示话题并保存，通过
`rviz_config` 指定自己的配置文件。

### 在 RViz 中查看

先在头显中进入支持手部跟踪的 XR 会话。
RViz 可直接添加 `PoseArray` 显示项订阅上述话题，`Fixed Frame` 设为
`world`，Topic 的 `Reliability Policy` 设为 `Best Effort`，
`Durability Policy` 设为 `Volatile`，Depth 可设为 `10`。
直接显示各关节位姿不需要 Marker 转换节点；需要骨骼连线和彩色关节点时，
再启动独立可视化节点并订阅 `hand_markers`。

## XR 数据与话题

默认前缀为 `/xr_media`；`{side}` 为 `left` 或 `right`，`{role}` 为 `headset`、`left_controller` 或 `right_controller`。

| 话题 | 消息类型 | 内容／发布条件 |
|---|---|---|
| `/xr_media/{role}/transform` | `geometry_msgs/msg/TransformStamped` | 对应设备被跟踪时发布位姿，并广播 TF |
| `/xr_media/{side}_controller/buttons` | `sensor_msgs/msg/Joy` | 对应控制器或手被跟踪时发布按键与轴 |
| `/xr_media/{side}_controller/hand` | `geometry_msgs/msg/PoseArray` | 该手完整的 25 个关节可用时发布 |
| `/xr_media/{side}_controller/hand_markers` | `visualization_msgs/msg/MarkerArray` | 独立可视化节点根据手部消息生成 |
| `/xr_media/status` | `std_msgs/msg/String` | 每秒发布 JSON 统计，不要求进入 XR |

### 坐标与时间戳
- 位姿已从 WebXR 转为 Z-up：+X 向前、+Y 向左、+Z 向上。
- 头显、手柄和手部使用 `world`；相对变换通过 TF 获取。坐标系名称由 `topic_prefix` 派生。
- 手部 `header.stamp` 是桥接回调时间，非头显采集时间；`header.frame_id` 为 `world`。
- 关节位置是世界坐标中的绝对位置，不是相对手腕或相邻关节的位置。

### 按键与摇杆

`/xr_media/left_controller/buttons` 和 `/xr_media/right_controller/buttons` 使用 `sensor_msgs/msg/Joy`，左右两侧的数组索引相同，均从 0 开始。

**`axes`**

| 索引 | 对应数据 | 含义 |
|---:|---|---|
| 0 | `stick_x` | 摇杆 X 轴 |
| 1 | `stick_y` | 摇杆 Y 轴 |
| 2 | `trigger_analog` | 扳机模拟量 |
| 3 | `grip_analog` | 握持模拟量 |

**`buttons`**

| 索引 | 对应数据 | 含义 |
|---:|---|---|
| 0 | `trigger_pressed` | 扳机按下 |
| 1 | `grip_pressed` | 握持按下 |
| 2 | `stick_clicked` | 摇杆按下 |
| 3 | `face_primary` | 主按键 |
| 4 | `face_secondary` | 次按键 |

- `buttons` 为 `0`／`1`，表示松开／按下。
- 手部跟踪模式下，捏合映射到扳机输入，不代表存在实体按键；浏览器合成的手部 gamepad 值会被忽略。
- 仅在对应控制器或手被跟踪时发布；接收端应判断消息是否过期。

## 验证与常见问题

启动视频上行后，在已加载 ROS 环境的另一终端检查：

```bash
ros2 topic hz /xr_media/camera
ros2 topic info /xr_media/camera --verbose
ros2 topic echo /xr_media/status --once
```

`status` 使用 `std_msgs/msg/String`，`data` 是 JSON；包含 SDK 媒体统计、XR 收到／派发／替换计数，以及 `conversion_errors`（图像转换错误）和 `xr_samples`（桥接收到的 XR 样本数）。统计不代表浏览器已经显示或播放。

| 现象 | 检查 |
|---|---|
| 回传卡片没有画面 | 默认是回环，先启动浏览器上行；确认输入话题有数据 |
| 图像转换报错 | 仅支持 `bgr8`、`rgb8`、`mono8`；检查 `step` 和数据长度 |
| RViz 收不到图像 | 订阅 QoS 设为 Best Effort、Volatile；图像深度为 2 |
| 音频异常 | 使用 16 kHz 单声道小端 int16 PCM；每 20 ms 对应 320 样本／640 字节 |
| 手部话题暂时无数据 | 进入 XR 并确认该手完整跟踪；缺失关节时不发布 |
| 启动提示端口占用 | 确认没有重复启动桥接，或修改 `server.port` |
| 自定义前缀后 RViz 无显示 | 同步修改显示话题，保存为自定义 RViz 配置 |

### 使用限制

- 多客户端共享 ROS 话题和坐标系，不自动隔离命名空间。
- XR 会话仅允许一个客户端使用。
- 网络与浏览器限制见 [SDK 文档](https://github.com/kehuanjack/xr_media)。

## 其他安装方式

首页默认使用 Git 直装 SDK。以下为替代方式，选一种即可；先按首页准备 ROS 与虚拟环境。

### 克隆后使用 pip 安装 SDK

```bash
git clone https://github.com/kehuanjack/xr_media.git /path/to/xr_media
python -m pip install /path/to/xr_media 'numpy<2' 'setuptools<80'
```

替换源码路径，然后继续首页的 rosdep 与桥接构建步骤。

### SDK 与桥接一起使用 Colcon

将两个源码包放入工作空间 `src/`，在工作空间根目录执行以下步骤，替代首页的依赖安装与构建命令：

```bash
python -m pip install aiohttp aiortc av 'numpy<2' 'setuptools<80'
rosdep install --from-paths src/xr_media src/xr_media_ros --ignore-src -y
python /usr/bin/colcon build --base-paths src --packages-up-to xr_media_ros --symlink-install
source install/setup.bash
```

两个源码路径按实际位置调整。此方式不再执行 `pip install` 安装 SDK 本身。

## 关节索引参考

左右手话题均使用标准 `geometry_msgs/msg/PoseArray`，不需要自定义消息包：

- 左手：`/xr_media/left_controller/hand`
- 右手：`/xr_media/right_controller/hand`

`poses` 使用 **从 0 开始的固定索引**，左右手顺序相同，与
`xr_media_ros/hand_joints.py` 中的 `HAND_JOINT_NAMES` 一致。
每个元素包含关节的位置 `position`（米）和姿态 `orientation`（四元数 x/y/z/w）。

| 索引 | WebXR 关节名称 | 部位 |
|---:|---|---|
| 0 | `wrist` | 手腕 |
| 1 | `thumb-metacarpal` | 拇指掌骨 |
| 2 | `thumb-phalanx-proximal` | 拇指近节 |
| 3 | `thumb-phalanx-distal` | 拇指远节 |
| 4 | `thumb-tip` | 拇指指尖 |
| 5 | `index-finger-metacarpal` | 食指掌骨 |
| 6 | `index-finger-phalanx-proximal` | 食指近节 |
| 7 | `index-finger-phalanx-intermediate` | 食指中节 |
| 8 | `index-finger-phalanx-distal` | 食指远节 |
| 9 | `index-finger-tip` | 食指指尖 |
| 10 | `middle-finger-metacarpal` | 中指掌骨 |
| 11 | `middle-finger-phalanx-proximal` | 中指近节 |
| 12 | `middle-finger-phalanx-intermediate` | 中指中节 |
| 13 | `middle-finger-phalanx-distal` | 中指远节 |
| 14 | `middle-finger-tip` | 中指指尖 |
| 15 | `ring-finger-metacarpal` | 无名指掌骨 |
| 16 | `ring-finger-phalanx-proximal` | 无名指近节 |
| 17 | `ring-finger-phalanx-intermediate` | 无名指中节 |
| 18 | `ring-finger-phalanx-distal` | 无名指远节 |
| 19 | `ring-finger-tip` | 无名指指尖 |
| 20 | `pinky-finger-metacarpal` | 小指掌骨 |
| 21 | `pinky-finger-phalanx-proximal` | 小指近节 |
| 22 | `pinky-finger-phalanx-intermediate` | 小指中节 |
| 23 | `pinky-finger-phalanx-distal` | 小指远节 |
| 24 | `pinky-finger-tip` | 小指指尖 |

例如，`poses[4]` 是拇指指尖，`poses[9]` 是食指指尖。
读取前必须检查 `len(poses) == 25`。未跟踪、没有关节数据或任一关节
缺失时，不发布该侧手部消息；不发送空数组，不压缩数组，也不以零位姿填充。
发布器和话题仍然存在，恢复完整跟踪后继续发布。
接收端应根据时间戳判断数据是否过期。
