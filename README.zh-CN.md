# xr_media_ros

[English](README.md) | [简体中文](README.zh-CN.md)

将 ROS 2 图像、音频话题与浏览器双向连接，并发布 WebXR 位姿、按键和手部关节。

SDK 仓库：[xr_media](https://github.com/AgilexOpensource/xr_media)。

## 安装

### 1. 准备环境

```bash
mkdir -p ~/xr_media_ws/src && cd ~/xr_media_ws
git clone https://github.com/AgilexOpensource/xr_media_ros.git src/xr_media_ros
source /opt/ros/humble/setup.bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

`--system-site-packages` 用于访问 ROS Python 依赖。

如需装到系统 Python，跳过此处及新终端中的两条 venv 命令，其余命令不变。Ubuntu 24.04 / Jazzy 及以后，系统 pip 还需加 `--break-system-packages`。

### 2. 安装依赖

```bash
python3 -m pip install "git+https://github.com/AgilexOpensource/xr_media.git" 'numpy<2' 'setuptools<80'
sudo apt install ros-humble-audio-common-msgs
```

### 3. 构建桥接包

```bash
python3 -m colcon build --symlink-install
source install/setup.bash
```

`python3 -m colcon` 让节点绑定 venv 中的 Python；直接用 `colcon` 会绑定系统 Python，无法导入 `xr_media`。

## 运行

### 首次配置证书

```bash
xr_media --init-certs
```

每次执行都会覆盖证书和私钥；已有可用证书时跳过此步。

### 启动桥接

```bash
ros2 launch xr_media_ros xr_media.launch.py
```

1. 打开节点打印的地址，信任证书并允许媒体权限。
2. 选择浏览器摄像头或麦克风，启动上行卡片。
3. 查看对应的回传卡片。

默认配置将浏览器上行发布到 `/xr_media/camera` 和 `/xr_media/audio`，再订阅回传，形成回环。按 `Ctrl+C` 停止。

新终端先加载环境，再执行启动命令：

```bash
cd ~/xr_media_ws
source /opt/ros/humble/setup.bash
source .venv/bin/activate
source install/setup.bash
```

## 更多用法

- [使用指南](docs/GUIDE.zh-CN.md)：配置、话题、QoS、XR 数据、RViz 和常见问题。

## 许可证

Apache-2.0，详见 [LICENSE](LICENSE)。
