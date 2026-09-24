"""Launch the integrated XR media ROS bridge."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    default_config = os.path.join(
        get_package_share_directory("xr_media_ros"), "config", "xr_media.yaml"
    )
    config = LaunchConfiguration("config")
    return LaunchDescription([
        DeclareLaunchArgument("config", default_value=default_config),
        Node(
            package="xr_media_ros",
            executable="xr_media_node",
            name="xr_media_node",
            output="screen",
            parameters=[config],
        ),
    ])
