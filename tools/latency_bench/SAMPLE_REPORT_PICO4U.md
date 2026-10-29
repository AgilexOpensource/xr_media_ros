# xr_media_ros latency test report (PICO 4 Ultra)

[English](SAMPLE_REPORT_PICO4U.md) | [简体中文](SAMPLE_REPORT_PICO4U.zh-CN.md)

Test date: 2026-10-29, 3 rounds.

## Summary

| Item | Typical latency | Slow case (95% within) | Rate |
|---|---|---|---|
| Image (PC receives camera frame → headset displays it) | 105–194 ms | 153–218 ms | 27–29 fps displayed |
| Controller data (headset capture → robot side receives) | 3.9–4.7 ms | 7.7–12.0 ms | 89 Hz |
| Hand tracking data (headset capture → robot side receives) | 6.6–7.5 ms | 12.0–16.0 ms | 87–89 Hz |

- Controller and hand data stay at a few milliseconds, with little difference between rounds.
- Image latency varies with WiFi conditions; in the same environment it differed by up to 90 ms at different times.
- Hand data is larger than controller data (25 joints per hand), so it is about 2–3 ms slower.

## Test conditions

| Item | Setup |
|---|---|
| Headset | PICO 4 Ultra, system browser |
| Network | Headset connected to the PC over WiFi |
| Camera | USB camera, 640x480, 30 fps |
| Software | `xr_media_ros`, `xr_media` 0.1.0, H.264 video |

## Detailed results

### Image (20 s each)

In round 1 the page was opened twice; both results are kept, 4 runs in total.

| Run | Typical | 95% within | Min / max | Display rate | Resolution | Bitrate | Packets lost |
|---|---|---|---|---|---|---|---|
| 1a | 133 ms | 156 ms | 86 / 431 ms | 28.8 fps | 640x480 | 4.7 Mbit/s | 0 |
| 1b | 194 ms | 218 ms | 171 / 450 ms | 26.9 fps | 640x480 | 3.6 Mbit/s | 3 |
| 2 | 105 ms | 153 ms | 79 / 229 ms | 29.3 fps | 640x480 | 5.0 Mbit/s | 0 |
| 3 | 143 ms | 173 ms | 92 / 226 ms | 27.3 fps | 640x480 | 5.0 Mbit/s | 15 |

No run dropped frames, and the few lost packets caused no picture errors.

### Controller (with video streaming)

| Round | Samples | Typical | 95% within | Max | Rate |
|---|---|---|---|---|---|
| 1 | 2720 | 3.9 ms | 12.0 ms | 103 ms | 89 Hz |
| 2 | 2672 | 4.7 ms | 11.7 ms | 65 ms | 89 Hz |
| 3 | 2744 | 4.5 ms | 7.7 ms | 53 ms | 89 Hz |

### Hand tracking (with video streaming)

| Round | Samples | Typical | 95% within | Max | Rate |
|---|---|---|---|---|---|
| 1 | 2444 | 7.5 ms | 16.0 ms | 771 ms | 87 Hz |
| 2 | 2000 | 6.7 ms | 14.0 ms | 78 ms | 87 Hz |
| 3 | 1757 | 6.6 ms | 12.0 ms | 170 ms | 89 Hz |

The occasional maximum values come from momentary WiFi fluctuations; in round 1 hand tracking paused once for about 0.8 s.

## Method

- The headset and PC clocks are aligned first, with a measurement error of about ±3–6 ms.
- Image: when the PC receives each camera frame it writes the current time into a corner of the frame; when the headset displays that frame it reads the time back and computes the difference.
- Controller and hand: the headset records the time at capture, the robot side records it again on receipt, and the difference is computed.

## Notes

- Image latency excludes camera exposure and headset display refresh; the latency you actually see is 10–30 ms higher.
- Controller and hand latencies are only a few milliseconds, close to the clock error, so treat them as an order of magnitude.
- Results come from a single headset in a single WiFi environment and will differ on other networks.
