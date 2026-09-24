# xr_media_ros

[English](README.md) | [简体中文](README.zh-CN.md)

将 ROS 2 图像、音频话题与浏览器双向连接，并发布 WebXR 位姿、按键和手部关节。

SDK 仓库：[xr_media](https://github.com/kehuanjack/xr_media)。

## 安装

需要 ROS 2、Colcon、rosdep、Git 和 Python venv。将本包放入工作空间的 `src/`，以下命令从工作空间根目录执行，以 Humble 为例。

### 1. 准备环境

```bash
source /opt/ros/humble/setup.bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

`--system-site-packages` 用于访问 ROS Python 依赖。首次使用 rosdep 时，先执行 `sudo rosdep init` 和 `rosdep update`；已初始化时跳过 init。

### 2. 安装依赖

```bash
python -m pip install "git+https://github.com/kehuanjack/xr_media.git" 'numpy<2' 'setuptools<80'
rosdep install --from-paths src/xr_media_ros --ignore-src --skip-keys xr_media -y
```

SDK 由 pip 安装，因此 rosdep 跳过 `xr_media`。`src/xr_media_ros` 按实际源码位置调整。

### 3. 构建桥接包

```bash
python /usr/bin/colcon build --base-paths src --packages-select xr_media_ros --symlink-install
source install/setup.bash
```

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

新终端先从工作空间根目录加载环境，再执行启动命令：

```bash
source /opt/ros/humble/setup.bash
source .venv/bin/activate
source install/setup.bash
```

## 更多用法

- [使用指南](docs/GUIDE.zh-CN.md)：配置、话题、QoS、XR 数据、RViz 和常见问题。

## 许可证

Apache-2.0，详见 [LICENSE](LICENSE)。
