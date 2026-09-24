"""Convert ROS image messages into SDK video frames."""

from array import array

import numpy as np

from xr_media import VideoFrame


def _stamp_ns(message) -> int:
    stamp = message.header.stamp
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def image_to_frame(message) -> VideoFrame:
    encoding = message.encoding.lower()
    channels = {"bgr8": 3, "rgb8": 3, "mono8": 1}.get(encoding)
    if channels is None:
        raise ValueError("unsupported ROS image encoding: %s" % message.encoding)
    row_bytes = int(message.width) * channels
    if int(message.step) < row_bytes:
        raise ValueError("image step is smaller than one encoded row")
    raw = np.frombuffer(message.data, dtype=np.uint8)
    expected = int(message.height) * int(message.step)
    if raw.size < expected:
        raise ValueError("image data is shorter than height * step")
    raw = raw[:expected].reshape(int(message.height), int(message.step))[:, :row_bytes]
    if channels == 1:
        image = np.ascontiguousarray(raw.reshape(message.height, message.width))
        pixel_format = "gray8"
    else:
        image = np.ascontiguousarray(raw.reshape(message.height, message.width, channels))
        pixel_format = "bgr24" if encoding == "bgr8" else "rgb24"
    return VideoFrame(image, message.width, message.height, pixel_format, _stamp_ns(message))


def frame_to_image(frame: VideoFrame, message_type):
    """Convert a decoded SDK frame to ``sensor_msgs/Image``."""
    channels = {"bgr24": ("bgr8", 3), "rgb24": ("rgb8", 3), "gray8": ("mono8", 1)}
    if frame.pixel_format not in channels:
        raise ValueError("cannot publish ROS Image format: %s" % frame.pixel_format)
    encoding, channel_count = channels[frame.pixel_format]
    image = np.ascontiguousarray(frame.data, dtype=np.uint8)
    message = message_type()
    message.header.stamp.sec = int(frame.timestamp_ns // 1_000_000_000)
    message.header.stamp.nanosec = int(frame.timestamp_ns % 1_000_000_000)
    message.height = int(frame.height)
    message.width = int(frame.width)
    message.encoding = encoding
    message.is_bigendian = False
    message.step = int(frame.width) * channel_count
    message.data = array("B", image.tobytes())
    return message
