from unittest.mock import patch

import pytest
from rclpy.executors import ExternalShutdownException

from xr_media_ros import node as bridge
from xr_media_ros.visualization import hand_visualizer as visualizer


@pytest.mark.parametrize("module,constructor", [
    (bridge, "XrMediaNode"), (visualizer, "HandVisualizer"),
])
def test_initialization_failure_shuts_down_ros(module, constructor):
    with patch.object(module, "rclpy") as ros, patch.object(
        module, constructor, side_effect=RuntimeError("startup failed")
    ):
        with pytest.raises(RuntimeError, match="startup failed"):
            module.main()
        ros.try_shutdown.assert_called_once()


def test_executor_initialization_failure_destroys_node():
    with patch.object(bridge, "rclpy") as ros, patch.object(
        bridge, "XrMediaNode"
    ) as node, patch.object(
        bridge, "MultiThreadedExecutor", side_effect=RuntimeError("executor failed")
    ):
        with pytest.raises(RuntimeError, match="executor failed"):
            bridge.main()
        node.return_value.destroy_node.assert_called_once()
        ros.try_shutdown.assert_called_once()


def test_executor_shutdown_failure_still_cleans_up():
    with patch.object(bridge, "rclpy") as ros, patch.object(
        bridge, "XrMediaNode"
    ) as node, patch.object(bridge, "MultiThreadedExecutor") as executor:
        executor.return_value.shutdown.side_effect = RuntimeError("executor shutdown failed")
        with pytest.raises(RuntimeError, match="executor shutdown failed"):
            bridge.main()
        node.return_value.destroy_node.assert_called_once()
        ros.try_shutdown.assert_called_once()


@pytest.mark.parametrize("module,constructor", [
    (bridge, "XrMediaNode"), (visualizer, "HandVisualizer"),
])
def test_destroy_failure_still_shuts_down_ros(module, constructor):
    with patch.object(module, "rclpy") as ros, patch.object(
        module, constructor
    ) as node, patch.object(bridge, "MultiThreadedExecutor"):
        node.return_value.destroy_node.side_effect = RuntimeError("destroy failed")
        with pytest.raises(RuntimeError, match="destroy failed"):
            module.main()
        ros.try_shutdown.assert_called_once()


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, ExternalShutdownException])
def test_bridge_shutdown_is_idempotent(interruption):
    with patch.object(bridge, "rclpy") as ros, patch.object(
        bridge, "XrMediaNode"
    ) as node, patch.object(bridge, "MultiThreadedExecutor") as executor:
        executor.return_value.spin.side_effect = interruption
        bridge.main()
        node.return_value.destroy_node.assert_called_once()
        ros.try_shutdown.assert_called_once()
        ros.shutdown.assert_not_called()


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, ExternalShutdownException])
def test_visualizer_shutdown_is_idempotent(interruption):
    with patch.object(visualizer, "rclpy") as ros, patch.object(
        visualizer, "HandVisualizer"
    ) as node:
        ros.spin.side_effect = interruption
        visualizer.main()
        node.return_value.destroy_node.assert_called_once()
        ros.try_shutdown.assert_called_once()
        ros.shutdown.assert_not_called()
