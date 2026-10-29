# xr_media_ros latency test tool

[English](README.md) | [简体中文](README.zh-CN.md)

Measures two latencies without modifying the `xr_media_ros` or `xr_media` source:

- Image: node receives the image topic → headset browser displays it
- VR data: headset capture → ROS topic published (controller and hand tracking measured separately)

## Quick start

1. Plug a USB camera into the PC, load the workspace environment and run in this directory:

   ```bash
   source <ws>/install/setup.bash
   source <ws>/.venv/bin/activate   # when xr_media is installed in a venv
   ./start.sh
   ```

   Alternatively run `WS=<ws> ./start.sh`. It sources `<ws>/install/setup.bash` and uses the Python in `<ws>/.venv` if present.

2. Open `https://<pc-ip>:9444/` in the headset browser and accept the certificate.
3. The image test starts automatically. Keep the page in the foreground for about 25 s; results appear in the bottom-right panel.
4. Follow the panel prompts to enter XR: controllers for 20 s → put the controllers down and use hand tracking for 20 s → exit XR. The panel shows the VR results about 3 s later.
5. Press Ctrl-C on the PC to stop. Results are saved to `results.jsonl` in this directory.

Reload the page to repeat the image test; enter XR again to repeat the VR test.

## Requirements

- A built `xr_media_ros` workspace, with `xr_media` (including aiohttp and numpy) in the Python environment
- `ros-<distro>-image-tools` (`cam2image`)
- A USB camera; the headset and PC on the same network

## Configuration

Optional environment variables:

| Variable | Default | Description |
|---|---|---|
| `WS` | none | ROS workspace; when unset, the already loaded environment is used |
| `PYTHON` | active venv → `$WS/.venv` → `python3` | Python with `xr_media` installed |
| `CAM_DEVICE` | `0` | Camera device index |
| `ROS_DOMAIN_ID` | `79` | Keeps the test apart from everyday nodes |

The node uses port 9444, separate from the everyday node on 9443, so both can run at the same time.

## Files

| File | Purpose |
|---|---|
| `start.sh` | Starts the camera and the instrumented node |
| `xr_cam_test.yaml` | Node test parameters (port 9444) |
| `run_node.py` | Instrumentation and `/bench/*` endpoints: writes a receive-time barcode into video frames, records XR data times, clock sync, result summary |
| `bench.js` | Test script injected into the node page |
| [`SAMPLE_REPORT_PICO4U.md`](SAMPLE_REPORT_PICO4U.md) | Sample PICO 4 Ultra report |

## Implementation notes

- `run_node.py` replaces `XrMediaNode._push_video`, `_on_xr` and the `XrMediaServer` page and routes in-process, then calls the original `main()`. Only the node started by this run is affected.
- The test page is the node's own page with `bench.js` injected; video goes through the existing `client.js`.
- Relies on the private methods `XrMediaNode._push_video`, `_on_xr` and `XrMediaServer._index`; check them when the node source changes.
