from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from xr_media_ros.node import XrMediaNode


@pytest.mark.parametrize("data", [b"", b"\x01"])
def test_invalid_audio_is_dropped(data):
    node = Mock()
    XrMediaNode._push_audio(node, SimpleNamespace(data=data), "sound", "Sound")
    node._server.push_audio_frame.assert_not_called()
    node.get_logger.return_value.warning.assert_called_once()


def test_valid_audio_is_forwarded():
    node = Mock()
    XrMediaNode._push_audio(node, SimpleNamespace(data=b"\x01\x00\xff\xff"), "sound", "Sound")
    frame, stream_id, label = node._server.push_audio_frame.call_args.args
    np.testing.assert_array_equal(frame.data, [1, -1])
    assert (stream_id, label) == ("sound", "Sound")
    node.get_logger.return_value.warning.assert_not_called()


@pytest.mark.parametrize("category", ["video_input", "video_output", "audio_input", "audio_output"])
def test_colliding_stream_ids_are_rejected(category):
    node = Mock()
    node._stream_id = XrMediaNode._stream_id
    node._output_topic.side_effect = lambda topic: "/xr_media" + topic
    node.get_parameters_by_prefix.return_value = {
        "first": SimpleNamespace(value="/camera/front"),
        "second": SimpleNamespace(value="/camera_front"),
    }
    with pytest.raises(ValueError, match="stream ID collision"):
        XrMediaNode._topics(node, category, output=category.endswith("output"))


def test_existing_noncolliding_stream_ids_are_unchanged():
    assert XrMediaNode._stream_id("video_input", "/xr_media/camera") == "video_input_xr_media_camera"
    node = Mock()
    node._stream_id = XrMediaNode._stream_id
    node.get_parameters_by_prefix.return_value = {
        "front": SimpleNamespace(value="/camera/front"),
        "rear": SimpleNamespace(value="/camera/rear"),
    }
    assert XrMediaNode._topics(node, "video_input") == [
        ("front", "/camera/front"), ("rear", "/camera/rear"),
    ]
