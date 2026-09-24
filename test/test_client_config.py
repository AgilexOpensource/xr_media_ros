from unittest.mock import patch

import pytest
import rclpy

from xr_media_ros.node import XrMediaNode


def test_video_subscription_uses_shared_depth_two_qos():
    rclpy.init(args=["--ros-args", "-p", "media.video_input.camera:=/camera"])
    node = None
    try:
        with patch("xr_media_ros.node.XrMediaServer"), patch.object(
            XrMediaNode, "create_subscription"
        ) as subscribe:
            node = XrMediaNode()
            subscribe.assert_called_once()
            qos = subscribe.call_args.args[3]
            assert qos.depth == 2
            assert qos is node._video_qos
            assert subscribe.call_args.kwargs["callback_group"] is node._media_group
            assert node._hand_qos.depth == 10
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


def test_server_start_failure_stops_server():
    rclpy.init(args=[])
    try:
        with patch("xr_media_ros.node.XrMediaServer") as server:
            server.return_value.start_background.side_effect = RuntimeError("start failed")
            with pytest.raises(RuntimeError, match="start failed"):
                XrMediaNode()
            server.return_value.stop_background.assert_called_once()
    finally:
        rclpy.try_shutdown()


@pytest.mark.parametrize("limit", [1, 3])
def test_yaml_client_limit_reaches_server(tmp_path, limit):
    config = tmp_path / "clients.yaml"
    config.write_text(
        "xr_media_node:\n  ros__parameters:\n    server:\n"
        f"      max_clients: {limit}\n", encoding="utf-8")
    rclpy.init(args=["--ros-args", "--params-file", str(config)])
    node = None
    try:
        with patch("xr_media_ros.node.XrMediaServer") as server:
            node = XrMediaNode()
            assert server.call_args.args[0].max_clients == limit
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


@pytest.mark.parametrize("limit", [0, -1])
def test_invalid_client_limit(limit):
    rclpy.init(args=["--ros-args", "-p", f"server.max_clients:={limit}"])
    try:
        with patch("xr_media_ros.node.XrMediaServer") as server:
            with pytest.raises(ValueError, match="positive integer"):
                XrMediaNode()
            server.assert_not_called()
    finally:
        rclpy.try_shutdown()
