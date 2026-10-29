#!/usr/bin/env python3
"""Run xr_media_node with in-process latency hooks; the source tree is untouched.

- Video: each frame gets a barcode with the node receive time (PC wall clock).
- XR: each sample logs headset t_ms, node entry time and time after ROS publish.
- The node page gets bench.js injected and /bench/* routes on the same port,
  so the headset only opens the normal node URL.
"""
import asyncio
import dataclasses
import json
import statistics
import threading
import time
from pathlib import Path

import numpy as np
from aiohttp import WSMsgType, web

from xr_media.server import XrMediaServer
from xr_media_ros import node as xr_node
from xr_media_ros.image_adapter import image_to_frame

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results.jsonl"
COLS, ROWS, CELL = 8, 6, 20
XR_IDLE_MS = 3000
MODE = {"controller": "手柄", "hand": "手势", "none": "无输入"}

_lock = threading.Lock()
_xr_rows = []
_offsets = []
_video = {"n": 0, "w": 0, "h": 0, "times": [], "cam_lag": []}
_last_xr = {"id": 0}


def now_ms():
    return time.time_ns() / 1e6


def save(kind, result):
    line = json.dumps({"kind": kind, **result}, ensure_ascii=False)
    print(f"[result] {line}", flush=True)
    with open(RESULTS, "a") as f:
        f.write(line + "\n")


# ---- video barcode -------------------------------------------------------

def check16(t24, seq8):
    x = t24 ^ (t24 >> 12) ^ (seq8 << 4)
    return ((x * 0x45D9F3B) & 0xFFFFFFFF) >> 16


def stamp(img, t_ms, seq):
    t24, s8 = t_ms & 0xFFFFFF, seq & 0xFF
    bits = t24 | (s8 << 24) | (check16(t24, s8) << 32)
    for i in range(COLS * ROWS):
        r, c = divmod(i, COLS)
        img[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] = 255 if (bits >> i) & 1 else 0


def push_video(self, message, stream_id, label):
    recv_ns = time.time_ns()
    try:
        frame = image_to_frame(message)
    except (TypeError, ValueError) as exc:
        self.get_logger().warning("dropping image: %s" % exc)
        return
    data = np.array(frame.data, copy=True)
    st = message.header.stamp
    with _lock:
        seq = _video["n"]
        _video["n"] += 1
        _video["w"], _video["h"] = frame.width, frame.height
        _video["times"] = _video["times"][-299:] + [recv_ns]
        lag = (recv_ns - (st.sec * 1_000_000_000 + st.nanosec)) / 1e6
        _video["cam_lag"] = _video["cam_lag"][-299:] + [lag]
    stamp(data, recv_ns // 1_000_000, seq)
    self._server.push_video_frame(dataclasses.replace(frame, data=data), stream_id, label)


# ---- XR timing -----------------------------------------------------------

_orig_on_xr = xr_node.XrMediaNode._on_xr


def on_xr(self, sample):
    in_ms = now_ms()
    _orig_on_xr(self, sample)
    pub_ms = now_ms()
    with _lock:
        _xr_rows.append((sample.t_ms, in_ms, pub_ms, sample.left.source_type, sample.right.source_type))


def summarize(vals):
    a = sorted(vals)
    pick = lambda p: a[min(len(a) - 1, int(p * len(a)))]
    return {"n": len(a), "median": pick(0.5), "p95": pick(0.95), "min": a[0], "max": a[-1]}


def fit_offset(offs, t0, t1):
    """Linear fit of headset->PC offset over time, using the lower-RTT half of syncs."""
    near = [o for o in offs if t0 - 60_000 <= o["pc_ms"] <= t1 + 60_000] or offs
    cut = statistics.median(o["rtt"] for o in near)
    used = [o for o in near if o["rtt"] <= cut]
    if len(used) < 2:
        o = used[0]
        return (lambda _t: o["offset"]), o["rtt"] / 2, 0.0, len(used)
    xs = [o["pc_ms"] for o in used]
    ys = [o["offset"] for o in used]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    k = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    fn = lambda t: my + k * (t - mx)
    return fn, max(o["rtt"] for o in used) / 2, k * (t1 - t0), len(used)


def xr_report(rows, offs):
    offset_at, err, drift, n_sync = fit_offset(offs, rows[0][2], rows[-1][2])
    groups = {}
    for t_ms, in_ms, pub_ms, left, right in rows:
        kinds = {left, right}
        mode = "hand" if "hand" in kinds else "controller" if "controller" in kinds else "none"
        g = groups.setdefault(mode, {"total": [], "to_node": [], "ros": [], "pc": []})
        t_pc = t_ms + offset_at(pub_ms)
        g["total"].append(pub_ms - t_pc)
        g["to_node"].append(in_ms - t_pc)
        g["ros"].append(pub_ms - in_ms)
        g["pc"].append(pub_ms)
    out = []
    for mode in ("controller", "hand", "none"):
        g = groups.get(mode)
        if not g:
            continue
        gaps = sorted(b - a for a, b in zip(g["pc"], g["pc"][1:]) if b - a < 500)
        out.append({"mode": MODE[mode], "hz": 1000 / statistics.median(gaps) if gaps else None,
                    "total": summarize(g["total"]), "to_node": summarize(g["to_node"]),
                    "ros_publish": summarize(g["ros"])})
    return {"groups": out, "sync_err_ms": err, "offset_drift_ms": drift, "n_sync": n_sync,
            "duration_s": (rows[-1][2] - rows[0][2]) / 1000}


async def xr_finalizer():
    while True:
        await asyncio.sleep(1.0)
        with _lock:
            idle = _xr_rows and now_ms() - _xr_rows[-1][2] > XR_IDLE_MS
            rows = list(_xr_rows) if idle else None
            if idle:
                _xr_rows.clear()
            offs = list(_offsets)
        if not rows:
            continue
        if not offs:
            print("[xr] no clock sync received; XR session discarded", flush=True)
            continue
        report = xr_report(rows, offs)
        save("xr", report)
        _last_xr.clear()
        _last_xr.update({"id": int(now_ms()), **report})


# ---- bench routes on the node server --------------------------------------

async def bench_js(_request):
    return web.FileResponse(HERE / "bench.js", headers={"Cache-Control": "no-store"})


async def clock(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            await ws.send_str(json.dumps({"t0": json.loads(msg.data)["t0"], "ts": now_ms()}))
    return ws


async def offset(request):
    body = await request.json()
    with _lock:
        _offsets.append({"offset": float(body["offset"]), "rtt": float(body["rtt"]), "pc_ms": now_ms()})
        del _offsets[:-600]
    return web.json_response({"ok": True})


async def video_log(_request):
    with _lock:
        times, lag = list(_video["times"]), list(_video["cam_lag"])
        out = {"frames": _video["n"], "width": _video["w"], "height": _video["h"]}
    if len(times) > 1:
        out["recv_fps"] = (len(times) - 1) / ((times[-1] - times[0]) / 1e9)
        out["cam_stamp_to_recv_ms"] = statistics.median(lag)
    return web.json_response(out)


async def video_result(request):
    save("video", await request.json())
    return web.json_response({"ok": True})


async def xr_last(_request):
    return web.json_response(_last_xr)


_orig_configure = XrMediaServer.configure_app
_orig_index = XrMediaServer._index


def configure_app(self, app):
    _orig_configure(self, app)
    app.router.add_get("/bench/bench.js", bench_js)
    app.router.add_get("/bench/clock", clock)
    app.router.add_post("/bench/offset", offset)
    app.router.add_get("/bench/video_log", video_log)
    app.router.add_post("/bench/video_result", video_result)
    app.router.add_get("/bench/xr_last", xr_last)

    async def start_finalizer(app_):
        app_["bench_task"] = asyncio.create_task(xr_finalizer())

    app.on_startup.append(start_finalizer)


async def index(self, request):
    resp = await _orig_index(self, request)
    # bench.js must run before client.js to capture the RTCPeerConnection.
    resp.text = resp.text.replace("<head>", '<head><script src="/bench/bench.js"></script>', 1)
    return resp


XrMediaServer.configure_app = configure_app
XrMediaServer._index = index
xr_node.XrMediaNode._push_video = push_video
xr_node.XrMediaNode._on_xr = on_xr
xr_node.main()
