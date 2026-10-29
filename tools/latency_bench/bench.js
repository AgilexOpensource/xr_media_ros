// Injected into the node page by run_node.py. Runs before client.js.
"use strict";
(() => {
  const WARM = 3000, SECS = 20000, SYNC_EVERY = 2000;
  const nowMs = () => performance.timeOrigin + performance.now();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const f = (v, d = 1) => (v == null || Number.isNaN(v) ? "-" : v.toFixed(d));
  const med = (a) => { const b = [...a].sort((x, y) => x - y); return b.length ? b[Math.floor(b.length / 2)] : null; };
  const post = (url, body) => fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

  // Capture the client's peer connections for getStats().
  const pcs = [];
  const NativePC = window.RTCPeerConnection;
  window.RTCPeerConnection = class extends NativePC {
    constructor(...args) { super(...args); pcs.push(this); }
  };

  // Track when the client draws a decoded frame into its tile canvas.
  let current = null; // last decoded barcode {t, seq, drawn}
  const onDraw = [];
  const nativeDraw = CanvasRenderingContext2D.prototype.drawImage;
  CanvasRenderingContext2D.prototype.drawImage = function (src, ...rest) {
    if (src instanceof HTMLVideoElement && current && !current.drawn && this.canvas !== probe) {
      current.drawn = true;
      onDraw.forEach((cb) => cb(current, nowMs()));
    }
    return nativeDraw.call(this, src, ...rest);
  };

  // ---- clock sync (headset -> PC), continuous ----
  let sync = null, ws = null;
  async function ping(n) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      ws = new WebSocket(`wss://${location.host}/bench/clock`);
      await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    }
    let best = null;
    for (let i = 0; i < n; i++) {
      const t0 = nowMs();
      const msg = await new Promise((res) => { ws.onmessage = (e) => res(JSON.parse(e.data)); ws.send(JSON.stringify({ t0 })); });
      const t3 = nowMs(), rtt = t3 - msg.t0;
      if (!best || rtt < best.rtt) best = { rtt, offset: msg.ts - (msg.t0 + t3) / 2 };
      await sleep(10);
    }
    post("/bench/offset", best);
    return best;
  }
  async function syncLoop() {
    for (;;) {
      try { const s = await ping(10); if (!sync || s.rtt <= sync.rtt * 1.5) sync = s; } catch { ws = null; }
      await sleep(SYNC_EVERY);
    }
  }

  // ---- barcode: 8x6 cells of 20 px in the top-left of the source frame ----
  const probe = Object.assign(document.createElement("canvas"), { width: 160, height: 120 });
  const probeCtx = probe.getContext("2d", { willReadFrequently: true });
  const chk = (t, seq) => Math.imul(t ^ (t >>> 12) ^ (seq << 4), 0x45d9f3b) >>> 16;
  function decode(video, scale) {
    nativeDraw.call(probeCtx, video, 0, 0, 160 * scale, 120 * scale, 0, 0, 160, 120);
    const px = probeCtx.getImageData(0, 0, 160, 120).data;
    let lo = 0, hi = 0;
    for (let i = 0; i < 48; i++) {
      const cx = (i % 8) * 20 + 10, cy = Math.floor(i / 8) * 20 + 10;
      let y = 0;
      for (let dy = -3; dy <= 3; dy += 3) for (let dx = -3; dx <= 3; dx += 3) {
        const o = ((cy + dy) * 160 + cx + dx) * 4;
        y += 0.299 * px[o] + 0.587 * px[o + 1] + 0.114 * px[o + 2];
      }
      if (y / 9 > 128) { if (i < 32) lo |= (1 << i); else hi |= (1 << (i - 32)); }
    }
    const t = lo & 0xffffff, seq = (lo >>> 24) & 0xff;
    return { t, seq, ok: chk(t, seq) === (hi & 0xffff) };
  }
  const M = 16777216;
  const since = (pcMs, t) => ((pcMs % M) - t + M) % M - 0.5;

  // ---- panel ----
  let panel;
  function show(html) { panel.innerHTML = html; }
  const table = (rows) => `<table>${rows.map((r, i) => `<tr>${r.map((c) => (i ? `<td>${c}</td>` : `<th>${c}</th>`)).join("")}</tr>`).join("")}</table>`;
  let videoHtml = "", xrHtml = "";
  const render = (status) => show(`<b>延迟测试</b><div>${status}</div>${videoHtml}${xrHtml}`);

  async function inboundStats() {
    for (const pc of [...pcs].reverse()) {
      if (pc.connectionState === "closed") continue;
      let r = null;
      const all = await pc.getStats();
      all.forEach((s) => { if (s.type === "inbound-rtp" && s.kind === "video") r = s; });
      if (r) return { ...r, codec: all.get(r.codecId)?.mimeType };
    }
    return null;
  }

  async function waitVideo() {
    for (;;) {
      const v = [...document.querySelectorAll(".tile video")].find((el) => el.videoWidth > 0 && !el.paused);
      if (v) return v;
      await sleep(200);
    }
  }

  async function runVideo() {
    render("等待视频…");
    const video = await waitVideo();
    const src = await (await fetch("/bench/video_log")).json();
    const scale = video.videoWidth / (src.width || video.videoWidth);
    const shown = [], drawn = [], decodeMs = [], ready = [];
    let bad = 0, measuring = false, alive = true;
    const sent = new Map();
    onDraw.push((c, t) => { if (measuring && sync) drawn.push(since(t + sync.offset, c.t)); });
    const onFrame = (now, meta) => {
      if (!alive) return;
      // Take times before decode() so the readback is not counted.
      const shownPc = performance.timeOrigin + (meta.expectedDisplayTime ?? now);
      const s = decode(video, scale);
      if (!s.ok) { bad += measuring ? 1 : 0; current = null; }
      else {
        current = { t: s.t, seq: s.seq, drawn: false };
        if (measuring && sync) {
          const l = since(shownPc + sync.offset, s.t);
          if (l < 2000) { shown.push(l); ready.push(now); }
          if (meta.processingDuration != null) decodeMs.push(meta.processingDuration * 1000);
        }
      }
      video.requestVideoFrameCallback(onFrame);
    };
    video.requestVideoFrameCallback(onFrame);
    render("预热…");
    await sleep(WARM);
    const s0 = await inboundStats(), t0 = nowMs();
    measuring = true;
    render("图像采样中（20 s），保持页面在前台…");
    await sleep(SECS);
    measuring = false;
    alive = false;
    const s1 = await inboundStats(), dt = (nowMs() - t0) / 1000;
    const node = await (await fetch("/bench/video_log")).json();
    const d = (k) => (s1?.[k] || 0) - (s0?.[k] || 0);
    const a = [...drawn].sort((x, y) => x - y), q = (p) => a[Math.min(a.length - 1, Math.floor(p * a.length))];
    const r = {
      n: a.length, median: q(0.5), p95: q(0.95), min: a[0], max: a[a.length - 1], bad,
      shown_median: med(shown),
      display_fps: ready.length > 1 ? (ready.length - 1) / ((ready[ready.length - 1] - ready[0]) / 1000) : null,
      source_res: `${node.width}x${node.height}`, node_recv_fps: node.recv_fps, cam_stamp_to_recv_ms: node.cam_stamp_to_recv_ms,
      decoded_res: `${s1?.frameWidth}x${s1?.frameHeight}`, codec: s1?.codec,
      mbps: d("bytesReceived") * 8 / dt / 1e6,
      jitter_buffer_ms: d("jitterBufferEmittedCount") ? d("jitterBufferDelay") / d("jitterBufferEmittedCount") * 1000 : null,
      decode_ms: med(decodeMs), frames_dropped: d("framesDropped"), packets_lost: d("packetsLost"),
      sync_err_ms: sync?.rtt / 2,
    };
    post("/bench/video_result", r);
    videoHtml = "<p>图像：节点收到话题 → 头显显示</p>" + table([
      ["项目", "值"],
      ["延迟（到画布绘制）中位 / P95 / 最大 ms", `${f(r.median)} / ${f(r.p95)} / ${f(r.max)}`],
      ["延迟（到视频帧就绪）中位 ms", f(r.shown_median)],
      ["jitter buffer / 解码 ms", `${f(r.jitter_buffer_ms)} / ${f(r.decode_ms)}`],
      ["源分辨率 / 节点收帧 fps", `${r.source_res} / ${f(r.node_recv_fps)}`],
      ["头显解码分辨率 / 显示 fps", `${r.decoded_res} / ${f(r.display_fps)}`],
      ["码率 Mbit/s / 丢包 / 丢帧", `${f(r.mbps, 2)} / ${r.packets_lost} / ${r.frames_dropped}`],
      ["相机时间戳→节点收到 ms", f(r.cam_stamp_to_recv_ms)],
      ["样本 / 解码失败 / 时钟误差 ±ms", `${r.n} / ${bad} / ${f(r.sync_err_ms)}`],
    ]);
  }

  async function watchXr() {
    let seen = (await (await fetch("/bench/xr_last")).json()).id;
    for (;;) {
      await sleep(2000);
      const r = await (await fetch("/bench/xr_last")).json();
      if (r.id === seen) continue;
      seen = r.id;
      const rows = [["模式", "样本", "Hz", "总延迟 中位/P95/最大 ms", "头显→节点 中位", "节点内发布 中位"]];
      for (const g of r.groups) rows.push([g.mode, g.total.n, f(g.hz), `${f(g.total.median)} / ${f(g.total.p95)} / ${f(g.total.max)}`, f(g.to_node.median), f(g.ros_publish.median, 2)]);
      xrHtml = `<p>VR 数据：头显采集 → ROS 发布（${f(r.duration_s, 0)} s）</p>` + table(rows) +
        `<div>时钟误差 ±${f(r.sync_err_ms)} ms，漂移 ${f(r.offset_drift_ms)} ms</div>`;
      render("完成。可再次进入 XR 重测，结果会覆盖此表。");
    }
  }

  window.addEventListener("DOMContentLoaded", async () => {
    panel = document.createElement("div");
    panel.setAttribute("role", "status");
    panel.style.cssText = "position:fixed;right:8px;bottom:8px;z-index:2147483647;max-width:46em;padding:8px 10px;" +
      "background:rgba(0,0,0,.82);color:#eee;font:13px/1.35 system-ui,sans-serif;border-radius:6px;pointer-events:none";
    const style = document.createElement("style");
    style.textContent = ".bench-p table{border-collapse:collapse;margin:4px 0}.bench-p td,.bench-p th{border:1px solid #555;padding:2px 6px;text-align:right}.bench-p td:first-child,.bench-p th:first-child{text-align:left}.bench-p p{margin:6px 0 0}";
    panel.className = "bench-p";
    document.head.append(style);
    document.body.append(panel);
    render("时钟同步…");
    try { sync = await ping(50); } catch (e) { render(`时钟同步失败: ${e}`); return; }
    syncLoop();
    watchXr();
    try { await runVideo(); } catch (e) { videoHtml = `<p>图像测试失败: ${e.message || e}</p>`; }
    render("现在进入 XR：手柄 20 s → 放下手柄用手势 20 s → 退出 XR，结果自动显示。");
  });
})();
