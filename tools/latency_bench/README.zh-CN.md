# xr_media_ros 延迟测试工具

[English](README.md) | [简体中文](README.zh-CN.md)

测量两项延迟，不修改 `xr_media_ros` 和 `xr_media` 源码：

- 图像：节点收到图像话题 → 头显浏览器显示
- VR 数据：头显采集 → ROS 话题发布（区分手柄 / 手势）

## 快速流程

1. PC 上插好 USB 相机，加载工作空间环境后在本目录运行：

   ```bash
   source <ws>/install/setup.bash
   source <ws>/.venv/bin/activate   # xr_media 装在 venv 里时
   ./start.sh
   ```

   也可以直接 `WS=<ws> ./start.sh`，会自动加载 `<ws>/install/setup.bash`，并使用 `<ws>/.venv` 里的 Python（如果有）。

2. 头显浏览器打开 `https://<pc-ip>:9444/`，接受证书。
3. 图像测试自动开始，保持页面在前台约 25 s，右下角面板显示结果。
4. 按面板提示进入 XR：手柄 20 s → 放下手柄用手势 20 s → 退出 XR。约 3 s 后面板显示 VR 结果。
5. PC 上 Ctrl-C 结束。结果保存在本目录的 `results.jsonl`。

刷新页面可重测图像，再次进入 XR 可重测 VR 数据。

## 依赖

- 已编译的 `xr_media_ros` 工作空间，Python 环境里装有 `xr_media`（含 aiohttp、numpy）
- `ros-<distro>-image-tools`（`cam2image`）
- USB 相机，头显与 PC 在同一网络

## 配置

可选环境变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `WS` | 无 | ROS 工作空间；不设时使用当前已加载的环境 |
| `PYTHON` | 当前 venv → `$WS/.venv` → `python3` | 装有 `xr_media` 的 Python |
| `CAM_DEVICE` | `0` | 相机设备号 |
| `ROS_DOMAIN_ID` | `79` | 与日常节点隔离 |

节点端口 9444，与日常节点 9443 分开，可以同时运行。

## 文件

| 文件 | 作用 |
|---|---|
| `start.sh` | 启动相机和带打点的节点 |
| `xr_cam_test.yaml` | 节点测试参数（端口 9444） |
| `run_node.py` | 打点和 `/bench/*` 接口：视频帧写入接收时间条码，XR 数据记录时间，时钟同步，结果汇总 |
| `bench.js` | 注入节点页面的测试脚本 |
| [`SAMPLE_REPORT_PICO4U.zh-CN.md`](SAMPLE_REPORT_PICO4U.zh-CN.md) | PICO 4 Ultra 实测报告示例 |

## 实现说明

- `run_node.py` 在进程内替换 `XrMediaNode._push_video`、`_on_xr` 和 `XrMediaServer` 的页面与路由，然后调用原 `main()`，只影响本次启动的节点。
- 测试页面就是节点自己的页面，注入了 `bench.js`，视频走原有 `client.js`。
- 依赖私有方法 `XrMediaNode._push_video`、`_on_xr` 和 `XrMediaServer._index`，节点源码变动后需要核对。
