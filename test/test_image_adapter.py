from array import array

import numpy as np
import pytest
from sensor_msgs.msg import Image

from xr_media import VideoFrame
from xr_media_ros.image_adapter import frame_to_image, image_to_frame


class TypedPayloadImage(Image):
    @Image.data.setter
    def data(self, value):
        assert isinstance(value, array)
        assert value.typecode == "B"
        Image.data.fset(self, value)


@pytest.mark.parametrize("pixel_format,encoding,channels", [
    ("bgr24", "bgr8", 3), ("rgb24", "rgb8", 3), ("gray8", "mono8", 1),
])
def test_image_payload_uses_typed_array_without_byte_validation(pixel_format, encoding, channels):
    width, height = 17, 11
    shape = (height, width, channels) if channels > 1 else (height, width)
    image = np.arange(height * width * channels, dtype=np.uint8).reshape(shape)
    frame = VideoFrame(image, width, height, pixel_format, 1_234_567_890)

    message = frame_to_image(frame, TypedPayloadImage)

    assert message.encoding == encoding
    assert (message.width, message.height, message.step) == (width, height, width * channels)
    assert (message.header.stamp.sec, message.header.stamp.nanosec) == (1, 234_567_890)
    assert not message.is_bigendian
    assert message.data.tobytes() == image.tobytes()
    restored = image_to_frame(message)
    assert restored.pixel_format == pixel_format
    assert restored.timestamp_ns == frame.timestamp_ns
    np.testing.assert_array_equal(restored.data, image)


def test_noncontiguous_image_payload_is_independent_of_source():
    original = np.arange(12 * 20 * 3, dtype=np.uint8).reshape(12, 20, 3)
    image = original[::2, ::2]
    expected = image.copy()
    assert not image.flags.c_contiguous

    message = frame_to_image(VideoFrame(image, 10, 6, "bgr24", 0), TypedPayloadImage)
    original.fill(0)

    assert message.data.tobytes() == expected.tobytes()
    np.testing.assert_array_equal(image_to_frame(message).data, expected)
