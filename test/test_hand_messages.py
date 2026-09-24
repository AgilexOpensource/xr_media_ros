from types import SimpleNamespace
from unittest.mock import Mock

import rclpy

from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseArray
from visualization_msgs.msg import Marker

from xr_media import RigidPose
from xr_media_ros.hand_joints import HAND_JOINT_NAMES
from xr_media_ros.node import XrMediaNode
from xr_media_ros.visualization.hand_visualizer import HandVisualizer


def test_visualizer_custom_prefix():
    rclpy.init(args=["--ros-args", "-p", "topic_prefix:=robot/xr/"])
    visualizer = None
    try:
        visualizer = HandVisualizer()
        assert [subscription.topic_name for subscription in visualizer._hand_subscriptions] == [
            f"/robot/xr/{side}_controller/hand" for side in ("left", "right")]
        assert [publisher.topic_name for publisher in visualizer._hand_marker_publishers.values()] == [
            f"/robot/xr/{side}_controller/hand_markers" for side in ("left", "right")]
    finally:
        if visualizer is not None:
            visualizer.destroy_node()
        rclpy.try_shutdown()


def test_hand_order_loss_and_recovery():
    expected_names = ["wrist"] + [f"thumb-{segment}" for segment in (
        "metacarpal", "phalanx-proximal", "phalanx-distal", "tip")]
    for finger in ("index", "middle", "ring", "pinky"):
        expected_names.extend(f"{finger}-finger-{segment}" for segment in (
            "metacarpal", "phalanx-proximal", "phalanx-intermediate",
            "phalanx-distal", "tip"))
    assert list(HAND_JOINT_NAMES) == expected_names
    joints = {name: RigidPose(px=float(index), py=1.0, pz=2.0,
                              qx=0.0, qy=0.0, qz=0.0, qw=1.0)
              for index, name in reversed(list(enumerate(expected_names)))}
    publishers = {side: Mock() for side in ("left", "right")}
    bridge = SimpleNamespace(_world_frame="world", _hand_publishers=publishers)
    stamp = Time(sec=42, nanosec=123)
    for side in publishers:
        XrMediaNode._maybe_publish_hand(bridge, stamp, side, joints)
        message = publishers[side].publish.call_args.args[0]
        assert message.header.frame_id == "world"
        assert message.header.stamp == stamp
        assert [pose.position.x for pose in message.poses] == list(range(25))
        assert all(pose.position.y == 1.0 and pose.position.z == 2.0
                   and pose.orientation.w == 1.0 for pose in message.poses)
        XrMediaNode._maybe_publish_hand(bridge, stamp, side, {})
        XrMediaNode._maybe_publish_hand(bridge, stamp, side, joints, tracked=False)
        for missing in expected_names:
            incomplete = {name: pose for name, pose in joints.items() if name != missing}
            XrMediaNode._maybe_publish_hand(bridge, stamp, side, incomplete)
        assert publishers[side].publish.call_count == 1
        XrMediaNode._maybe_publish_hand(bridge, stamp, side, joints)
        assert publishers[side].publish.call_count == 2

        visualizer = SimpleNamespace(_hand_marker_publishers={side: Mock()},
                                     _point=HandVisualizer._point,
                                     _color=HandVisualizer._color)
        HandVisualizer._publish(visualizer, side, message)
        markers = visualizer._hand_marker_publishers[side].publish.call_args.args[0].markers
        assert len(markers) == 26
        assert [marker.pose.position.x for marker in markers[:25]] == list(range(25))
        assert all(marker.header == message.header for marker in markers)
        assert markers[-1].type == Marker.LINE_LIST
        assert len(markers[-1].points) == 48
        HandVisualizer._publish(visualizer, side, PoseArray())
        cleared = visualizer._hand_marker_publishers[side].publish.call_args.args[0]
        assert [marker.action for marker in cleared.markers] == [Marker.DELETEALL]
