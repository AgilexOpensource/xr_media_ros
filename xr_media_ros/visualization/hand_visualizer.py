"""Convert typed XR hand messages to RViz MarkerArray messages."""

from geometry_msgs.msg import Point, PoseArray
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray
from ..hand_joints import HAND_JOINT_NAMES


_BONES = (
    ("wrist", "thumb-metacarpal"),
    ("thumb-metacarpal", "thumb-phalanx-proximal"),
    ("thumb-phalanx-proximal", "thumb-phalanx-distal"),
    ("thumb-phalanx-distal", "thumb-tip"),
    ("wrist", "index-finger-metacarpal"),
    ("index-finger-metacarpal", "index-finger-phalanx-proximal"),
    ("index-finger-phalanx-proximal", "index-finger-phalanx-intermediate"),
    ("index-finger-phalanx-intermediate", "index-finger-phalanx-distal"),
    ("index-finger-phalanx-distal", "index-finger-tip"),
    ("wrist", "middle-finger-metacarpal"),
    ("middle-finger-metacarpal", "middle-finger-phalanx-proximal"),
    ("middle-finger-phalanx-proximal", "middle-finger-phalanx-intermediate"),
    ("middle-finger-phalanx-intermediate", "middle-finger-phalanx-distal"),
    ("middle-finger-phalanx-distal", "middle-finger-tip"),
    ("wrist", "ring-finger-metacarpal"),
    ("ring-finger-metacarpal", "ring-finger-phalanx-proximal"),
    ("ring-finger-phalanx-proximal", "ring-finger-phalanx-intermediate"),
    ("ring-finger-phalanx-intermediate", "ring-finger-phalanx-distal"),
    ("ring-finger-phalanx-distal", "ring-finger-tip"),
    ("wrist", "pinky-finger-metacarpal"),
    ("pinky-finger-metacarpal", "pinky-finger-phalanx-proximal"),
    ("pinky-finger-phalanx-proximal", "pinky-finger-phalanx-intermediate"),
    ("pinky-finger-phalanx-intermediate", "pinky-finger-phalanx-distal"),
    ("pinky-finger-phalanx-distal", "pinky-finger-tip"),
)


class HandVisualizer(Node):
    def __init__(self) -> None:
        super().__init__("xr_hand_visualizer")
        prefix = str(self.declare_parameter("topic_prefix", "/xr_media").value).strip().rstrip("/")
        prefix = "/" + prefix.lstrip("/") if prefix else "/xr_media"
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self._hand_subscriptions = []
        self._hand_marker_publishers = {}
        for side in ("left", "right"):
            topic = f"{prefix}/{side}_controller/hand"
            output = f"{prefix}/{side}_controller/hand_markers"
            self._hand_marker_publishers[side] = self.create_publisher(MarkerArray, output, qos)
            self._hand_subscriptions.append(
                self.create_subscription(
                    PoseArray, topic,
                    lambda message, side=side: self._publish(side, message), qos
                )
            )

    @staticmethod
    def _point(pose) -> Point:
        point = Point()
        point.x, point.y, point.z = pose.position.x, pose.position.y, pose.position.z
        return point

    @staticmethod
    def _color(name: str):
        colors = {
            "thumb": (1.0, 0.42, 0.42), "index": (1.0, 0.82, 0.4),
            "middle": (0.35, 0.84, 0.74), "ring": (0.38, 0.66, 1.0),
            "pinky": (0.78, 0.49, 1.0),
        }
        from std_msgs.msg import ColorRGBA
        color = ColorRGBA()
        rgb = next((value for key, value in colors.items() if name.startswith(key)), (1.0, 1.0, 1.0))
        color.r, color.g, color.b, color.a = (*rgb, 1.0)
        return color

    def _publish(self, side: str, message: PoseArray) -> None:
        joints = dict(zip(HAND_JOINT_NAMES, message.poses))
        if len(message.poses) != len(HAND_JOINT_NAMES):
            marker = Marker()
            marker.header = message.header
            marker.ns = f"{side}_hand"
            marker.action = Marker.DELETEALL
            self._hand_marker_publishers[side].publish(MarkerArray(markers=[marker]))
            return
        markers = []
        for marker_id, (name, pose) in enumerate(joints.items()):
            marker = Marker()
            marker.header = message.header
            marker.ns, marker.id = f"{side}_hand/{name}", marker_id
            marker.type, marker.action = Marker.SPHERE, Marker.ADD
            marker.pose = pose
            marker.scale.x = marker.scale.y = marker.scale.z = 0.014
            marker.color = self._color(name)
            marker.lifetime.nanosec = 200_000_000
            markers.append(marker)
        bones = Marker()
        bones.header = message.header
        bones.ns, bones.id = f"{side}_hand/bones", 100
        bones.type, bones.action = Marker.LINE_LIST, Marker.ADD
        bones.pose.orientation.w = 1.0
        bones.scale.x, bones.color.a, bones.lifetime.nanosec = 0.006, 1.0, 200_000_000
        for first, second in _BONES:
            if first in joints and second in joints:
                bones.points.extend((self._point(joints[first]), self._point(joints[second])))
        markers.append(bones)
        self._hand_marker_publishers[side].publish(MarkerArray(markers=markers))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = HandVisualizer()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            rclpy.try_shutdown()


if __name__ == "__main__":
    main()
