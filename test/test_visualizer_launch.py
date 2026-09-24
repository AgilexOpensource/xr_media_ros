import importlib.util
from pathlib import Path
from unittest.mock import patch

from launch import LaunchContext
import yaml


def test_integrated_visualizer_uses_bridge_config(tmp_path):
    launch_path = Path(__file__).parents[1] / "launch/xr_media_rviz.launch.py"
    spec = importlib.util.spec_from_file_location("xr_media_rviz_launch", launch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for settings, expected in (
        ({}, "/xr_media"),
        ({"/**": {"ros__parameters": {"topic_prefix": "/shared"}}}, "/shared"),
        ({"xr_media_node": {"ros__parameters": {"topic_prefix": "/robot/xr"}}}, "/robot/xr"),
    ):
        config = tmp_path / "config.yaml"
        config.write_text(yaml.safe_dump(settings))
        context = LaunchContext()
        context.launch_configurations["config"] = str(config)
        with patch.object(module, "Node") as node:
            module._visualizer(context)
            assert node.call_args.kwargs["parameters"] == [{"topic_prefix": expected}]
