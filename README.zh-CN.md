# xr_media_ros

[English](README.md)

ROS 2 桥接包，将图像、音频话题与浏览器双向连接，并发布 WebXR 位姿、按键和手部关节。

基于 [xr_media](https://github.com/AgilexOpensource/xr_media) SDK。

## 环境要求

已在 Ubuntu 22.04 + ROS 2 Humble 上测试。

## 安装

```bash
mkdir -p ~/xr_media_ws/src && cd ~/xr_media_ws
git clone https://github.com/AgilexOpensource/xr_media_ros.git src/xr_media_ros
sudo apt install ros-humble-audio-common-msgs
source /opt/ros/humble/setup.bash
```

用系统 pip 安装 SDK 并构建：

```bash
pip3 install "git+https://github.com/AgilexOpensource/xr_media.git" 'numpy<2' 'setuptools<80'
colcon build --symlink-install
source install/setup.bash
```

或者，推荐使用虚拟环境，避免改动系统 Python。该虚拟环境仍可访问 ROS 的 Python 包：

```bash
python3 -m venv --system-site-packages ~/xr_media_ws/.venv
source ~/xr_media_ws/.venv/bin/activate
pip install "git+https://github.com/AgilexOpensource/xr_media.git" 'numpy<2' 'setuptools<80'
python3 -m colcon build --symlink-install
source install/setup.bash
```

每个新终端都要先激活虚拟环境，再执行 `source install/setup.bash`。`python3 -m colcon` 让节点使用虚拟环境中的 Python；直接用 `colcon` 会使用系统 Python，无法导入虚拟环境中的 `xr_media`。

## 快速开始

首次使用先生成 TLS 证书。每次执行都会覆盖证书和私钥，已有可用证书时跳过此步。WebXR 必须使用 HTTPS，缺少证书时节点报错退出，不会退回 HTTP。

```bash
xr_media --init-certs
```

启动桥接：

```bash
ros2 launch xr_media_ros xr_media.launch.py
```

1. 打开节点打印的地址，信任证书并允许媒体权限。
2. 选择浏览器摄像头或麦克风，启动上行卡片。
3. 查看对应的回传卡片。

默认配置将浏览器上行发布到 `/xr_media/camera` 和 `/xr_media/audio`，再订阅回传，形成回环。按 `Ctrl+C` 停止。

新终端先加载环境：

```bash
cd ~/xr_media_ws
source /opt/ros/humble/setup.bash
# 仅虚拟环境安装方式需要
source .venv/bin/activate
source install/setup.bash
```

## 更多

- [使用指南](docs/GUIDE.zh-CN.md)：配置、话题、QoS、XR 数据、RViz 和常见问题。

## 许可证

Apache-2.0，详见 [LICENSE](LICENSE)。
