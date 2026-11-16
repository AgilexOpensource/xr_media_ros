from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import rclpy
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray

from xr_media_ros.node import TlsCertificateError, XrMediaNode


def test_video_subscription_uses_shared_depth_two_qos():
    rclpy.init(args=["--ros-args", "-p", "media.video_input.camera:=/camera"])
    node = None
    try:
        with patch("xr_media_ros.node.XrMediaServer"), patch.object(
            XrMediaNode, "create_subscription"
        ) as subscribe:
            node = XrMediaNode()
            images = [c for c in subscribe.call_args_list if c.args[0] is Image]
            assert len(images) == 1
            qos = images[0].args[3]
            assert qos.depth == 2
            assert qos is node._video_qos
            assert images[0].kwargs["callback_group"] is node._media_group
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


def test_missing_default_certificate_stops_startup(default_tls_files):
    (default_tls_files / "key.pem").unlink()
    rclpy.init(args=[])
    try:
        with patch("xr_media_ros.node.XrMediaServer") as server:
            with pytest.raises(TlsCertificateError, match="key.pem.*xr_media --init-certs"):
                XrMediaNode()
            server.assert_not_called()
    finally:
        rclpy.try_shutdown()


def test_custom_certificate_paths_must_exist_and_be_paired(tmp_path):
    cert, key = tmp_path / "c.pem", tmp_path / "k.pem"
    cert.write_text("cert", encoding="utf-8")
    for params, error in (([f"server.cert_path:={cert}"], ValueError),
                          ([f"server.cert_path:={cert}", f"server.key_path:={key}"], TlsCertificateError)):
        args = ["--ros-args"] + [x for p in params for x in ("-p", p)]
        rclpy.init(args=args)
        try:
            with patch("xr_media_ros.node.XrMediaServer") as server:
                with pytest.raises(error):
                    XrMediaNode()
                server.assert_not_called()
        finally:
            rclpy.try_shutdown()
    key.write_text("key", encoding="utf-8")
    rclpy.init(args=["--ros-args", "-p", f"server.cert_path:={cert}", "-p", f"server.key_path:={key}"])
    node = None
    try:
        with patch("xr_media_ros.node.XrMediaServer") as server:
            node = XrMediaNode()
            config = server.call_args.args[0]
            assert (config.cert_path, config.key_path) == (cert, key)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


def test_haptic_topic_reaches_the_server():
    node = SimpleNamespace(_server=MagicMock(), get_logger=MagicMock())
    XrMediaNode._on_haptic(node, "left", Float32MultiArray(data=[0.8, 80.0]))
    node._server.send_haptic.assert_called_once()
    side, intensity, duration = node._server.send_haptic.call_args.args
    assert side == "left" and intensity == pytest.approx(0.8) and duration == 80.0
    XrMediaNode._on_haptic(node, "right", Float32MultiArray(data=[0.8]))
    assert node._server.send_haptic.call_count == 1
    node.get_logger.return_value.warn.assert_called_once()
