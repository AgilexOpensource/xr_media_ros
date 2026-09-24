"""Launch the XR hand message to MarkerArray visualizer."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument("topic_prefix", default_value="/xr_media"),
        Node(
            package="xr_media_ros",
            executable="xr_hand_visualizer",
            name="xr_hand_visualizer",
            output="screen",
            parameters=[{"topic_prefix": LaunchConfiguration("topic_prefix")}],
        ),
    ])
