"""Launch the XR media bridge together with its RViz visualization."""

import os
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _visualizer(context):
    with open(LaunchConfiguration("config").perform(context), encoding="utf-8") as stream:
        settings = yaml.safe_load(stream) or {}
    parameters = settings.get("/**", {}).get("ros__parameters", {}).copy()
    parameters.update(settings.get("xr_media_node", {}).get("ros__parameters", {}))
    return [Node(
        package="xr_media_ros",
        executable="xr_hand_visualizer",
        name="xr_hand_visualizer",
        output="screen",
        parameters=[{"topic_prefix": parameters.get("topic_prefix", "/xr_media")}],
    )]


def generate_launch_description() -> LaunchDescription:
    package_share = get_package_share_directory("xr_media_ros")
    config = LaunchConfiguration("config")
    rviz_config = LaunchConfiguration("rviz_config")

    return LaunchDescription([
        DeclareLaunchArgument(
            "config",
            default_value=os.path.join(package_share, "config", "xr_media.yaml"),
            description="Path to the xr_media_ros parameter file",
        ),
        DeclareLaunchArgument(
            "rviz_config",
            default_value=os.path.join(package_share, "rviz", "xr_media.rviz"),
            description="Path to the RViz configuration file",
        ),
        # The bridge talks DDS over loopback only; RViz and the visualizer must match it.
        SetEnvironmentVariable("ROS_LOCALHOST_ONLY", "1"),
        Node(
            package="xr_media_ros",
            executable="xr_media_node",
            name="xr_media_node",
            output="screen",
            # RViz shows the XR frames through TF; the bridge publishes it only here.
            parameters=[config, {"publish_tf": True}],
        ),
        OpaqueFunction(function=_visualizer),
        Node(
            package="rviz2",
            executable="rviz2",
            name="xr_media_rviz",
            output="screen",
            arguments=["-d", rviz_config],
        ),
    ])
