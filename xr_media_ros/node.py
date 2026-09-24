"""ROS 2 bridge for XR poses, controls, and WebRTC media."""

import json
import re
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import numpy as np
import rclpy
from geometry_msgs.msg import Pose, PoseArray, TransformStamped
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image, Joy
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster
from xr_media import AudioFrame, HandInput, MediaServerConfig, RigidPose, XrMediaServer
from xr_media.cli import _CaptureControl, _capture_worker, _open_capture, _video_test

from .hand_joints import HAND_JOINT_NAMES
from .image_adapter import frame_to_image, image_to_frame

try:
    from audio_common_msgs.msg import AudioData
except ImportError:  # Optional until an audio topic is configured.
    AudioData = None


def _prefix(value: str) -> str:
    value = str(value).strip().rstrip("/")
    if not value:
        return "/xr_media"
    return value if value.startswith("/") else "/" + value


class XrMediaNode(Node):
    """Serve ROS camera streams and publish browser WebXR data."""

    def __init__(self) -> None:
        super().__init__(
            "xr_media_node", automatically_declare_parameters_from_overrides=True
        )
        self._declare_parameters()
        max_clients = self.get_parameter("server.max_clients").value
        if type(max_clients) is not int or max_clients < 1:
            raise ValueError("server.max_clients must be a positive integer")
        self._media_group = MutuallyExclusiveCallbackGroup()
        self._conversion_errors = 0
        self._xr_samples = 0
        self._prefix = _prefix(self.get_parameter("topic_prefix").value)
        frame_prefix = self._prefix.lstrip("/")
        self._world_frame = "world"
        self._frames = {
            "headset": f"{frame_prefix}/headset",
            "left_controller": f"{frame_prefix}/left_controller",
            "right_controller": f"{frame_prefix}/right_controller",
        }
        self._video_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=2,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self._hand_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self._tf = TransformBroadcaster(self)
        self._transform_publishers = {
            role: self.create_publisher(
                TransformStamped, f"{self._prefix}/{role}/transform", 10
            ) for role in self._frames
        }
        self._joy_publishers = {
            role: self.create_publisher(Joy, f"{self._prefix}/{role}/buttons", 10)
            for role in ("left_controller", "right_controller")
        }
        self._hand_publishers = {
            side: self.create_publisher(
                PoseArray, f"{self._prefix}/{side}_controller/hand", self._hand_qos
            )
            for side in ("left", "right")
        }
        self._status_publisher = self.create_publisher(
            String, f"{self._prefix}/status", 10
        )

        cert = str(self.get_parameter("server.cert_path").value)
        key = str(self.get_parameter("server.key_path").value)
        config = MediaServerConfig(
            host="0.0.0.0",
            port=int(self.get_parameter("server.port").value),
            codec="h264",
            max_clients=max_clients,
            cert_path=Path(cert) if cert else None,
            key_path=Path(key) if key else None,
        )
        self._server = XrMediaServer(
            config,
            on_xr=self._on_xr,
        )
        self._source_stop = threading.Event()
        self._source_workers = []
        self._source_captures = []
        try:
            self._server.start_background()
            self._subscriptions = self._create_media_endpoints()
            for worker in self._source_workers:
                worker.start()
        except Exception:
            self._stop_sources()
            self._server.stop_background()
            raise
        self._timer = self.create_timer(1.0, self._publish_status)
        for url in self._server.page_urls:
            self.get_logger().info("Open in headset browser: %s" % url)

    def _declare_parameters(self) -> None:
        defaults = {
            "topic_prefix": "/xr_media",
            "server.port": 9443,
            "server.max_clients": 1,
            "server.cert_path": "",
            "server.key_path": "",
        }
        for name, value in defaults.items():
            if not self.has_parameter(name):
                self.declare_parameter(name, value)

    @staticmethod
    def _stream_id(category: str, topic: str) -> str:
        suffix = re.sub(r"[^A-Za-z0-9_-]+", "_", topic).strip("_") or "main"
        return "%s_%s" % (category, suffix)

    def _topics(self, name: str, output: bool = False):
        parameters = self.get_parameters_by_prefix("media." + name)
        items = [(label, str(parameter.value)) for label, parameter in parameters.items()]
        if any(not topic.strip("/") for _label, topic in items):
            raise ValueError("media.%s topics cannot be empty" % name)
        if output:
            items = [(label, self._output_topic(topic)) for label, topic in items]
        topics = [topic for _label, topic in items]
        if len(topics) != len(set(topics)):
            raise ValueError("media.%s topics must be unique" % name)
        stream_topics = {}
        for topic in topics:
            stream_id = self._stream_id(name, topic)
            if stream_id in stream_topics:
                raise ValueError(
                    "media.%s stream ID collision: %s and %s map to %s"
                    % (name, stream_topics[stream_id], topic, stream_id)
                )
            stream_topics[stream_id] = topic
        if any(
            not topic.startswith("/") and not (
                name == "video_input" and (
                    topic == "video_test"
                    or (topic.startswith("video_file:") and bool(topic[11:]))
                    or (topic.startswith("camera:") and topic[7:].isdigit())
                )
            ) for topic in topics
        ):
            raise ValueError("media.%s entries must be absolute ROS topics" % name)
        return items

    def _output_topic(self, topic: str) -> str:
        absolute = _prefix(topic)
        if absolute == self._prefix or absolute.startswith(self._prefix + "/"):
            return absolute
        return self._prefix + "/" + topic.strip("/")

    def _create_media_endpoints(self):
        subscriptions = []
        for label, topic in self._topics("video_input"):
            stream_id = self._stream_id("video_input", topic)
            if not topic.startswith("/"):
                self._create_source(stream_id, label, topic)
                continue
            self._server.register_video_stream(stream_id, label, kind="ros")
            subscriptions.append(
                self.create_subscription(
                    Image,
                    topic,
                    lambda msg, sid=stream_id, lab=label: self._push_video(
                        msg, sid, lab
                    ),
                    self._video_qos,
                    callback_group=self._media_group,
                )
            )

        self._video_publishers = {}
        for label, topic in self._topics("video_output", output=True):
            stream_id = self._stream_id("video_output", topic)
            self._video_publishers[stream_id] = self.create_publisher(
                Image, topic, self._video_qos
            )
            self._server.register_browser_input(stream_id, "video", label)
        if self._video_publishers:
            self._server.add_video_listener(self._publish_video)

        audio_input = self._topics("audio_input")
        audio_output = self._topics("audio_output", output=True)
        if (audio_input or audio_output) and AudioData is None:
            raise RuntimeError("audio topics require audio_common_msgs")
        for label, topic in audio_input:
            stream_id = self._stream_id("audio_input", topic)
            self._server.register_audio_stream(stream_id, label, "ros")
            subscriptions.append(
                self.create_subscription(
                    AudioData,
                    topic,
                    lambda msg, sid=stream_id, lab=label: self._push_audio(
                        msg, sid, lab
                    ),
                    10,
                    callback_group=self._media_group,
                )
            )

        self._audio_publishers = {}
        for label, topic in audio_output:
            stream_id = self._stream_id("audio_output", topic)
            self._audio_publishers[stream_id] = self.create_publisher(
                AudioData, topic, 10
            )
            self._server.register_browser_input(stream_id, "audio", label)
        if self._audio_publishers:
            self._server.add_audio_listener(self._publish_audio)
        return subscriptions

    def _create_source(self, stream_id, label, source):
        defaults = SimpleNamespace(width=640, height=480)
        if source == "video_test":
            self._server.register_video_stream(stream_id, label, kind="video_test")
            target = _video_test
            arguments = (self._server, self._source_stop, defaults.width,
                         defaults.height, stream_id, label)
        else:
            capture, kind, fps = _open_capture(source, {}, defaults)
            self._source_captures.append(capture)
            control = _CaptureControl(capture, kind)
            self._server.register_video_stream(
                stream_id, label, kind=kind,
                on_control=control.control if kind == "file" else None,
            )
            if kind == "file":
                self._server.set_stream_playback(stream_id, **control.snapshot())
            target = _capture_worker
            arguments = (self._server, self._source_stop, capture, stream_id,
                         label, kind, fps, control)
        self._source_workers.append(threading.Thread(
            target=target, args=arguments, daemon=True,
        ))

    def _stop_sources(self):
        self._source_stop.set()
        for worker in self._source_workers:
            if worker.ident is not None:
                worker.join(timeout=2.0)
        for capture in self._source_captures:
            capture.release()
        self._source_captures.clear()

    def _push_video(self, message, stream_id: str, label: str) -> None:
        try:
            self._server.push_video_frame(image_to_frame(message), stream_id, label)
        except (TypeError, ValueError) as exc:
            self._conversion_errors += 1
            self.get_logger().warning("dropping image from %s: %s" % (stream_id, exc))

    def _publish_video(self, stream_id: str, frame) -> None:
        publisher = self._video_publishers.get(stream_id)
        if publisher is not None:
            publisher.publish(frame_to_image(frame, Image))

    def _push_audio(self, message, stream_id: str, label: str) -> None:
        raw = bytes(message.data)
        if not raw:
            self.get_logger().warning("dropping empty PCM from %s" % stream_id)
            return
        if len(raw) % 2:
            self.get_logger().warning("dropping odd-length PCM from %s" % stream_id)
            return
        samples = np.frombuffer(raw, dtype="<i2").copy()
        self._server.push_audio_frame(AudioFrame(samples, 16000, 1, 0), stream_id, label)

    def _publish_audio(self, stream_id: str, frame: AudioFrame) -> None:
        publisher = self._audio_publishers.get(stream_id)
        if publisher is not None:
            message = AudioData()
            message.data = np.asarray(frame.data, dtype="<i2").tobytes()
            publisher.publish(message)

    def _on_xr(self, sample) -> None:
        self._xr_samples += 1
        stamp = self.get_clock().now().to_msg()
        transforms = []
        if sample.hmd_tracked:
            transforms.append(self._publish_transform(
                stamp,
                self._world_frame,
                self._frames["headset"],
                sample.hmd,
                "headset",
            ))
        for side, hand, role in (
            ("left", sample.left, "left_controller"),
            ("right", sample.right, "right_controller"),
        ):
            if not hand.tracked:
                self._maybe_publish_hand(stamp, side, {}, tracked=False)
                continue
            transforms.append(self._publish_transform(
                stamp,
                self._world_frame,
                self._frames[role],
                hand.pose,
                role,
            ))
            publisher = self._joy_publishers.get(role)
            if publisher is not None:
                publisher.publish(self._joy(stamp, self._frames[role], hand.input))
            self._maybe_publish_hand(stamp, side, hand.joints)
        if transforms:
            self._tf.sendTransform(transforms)

    def _maybe_publish_hand(self, stamp, side: str, joints, tracked: bool = True) -> None:
        if not tracked or not all(name in joints for name in HAND_JOINT_NAMES):
            return
        message = PoseArray()
        message.header.stamp = stamp
        message.header.frame_id = self._world_frame
        for name in HAND_JOINT_NAMES:
            pose = joints[name]
            joint = Pose()
            joint.position.x = pose.px
            joint.position.y = pose.py
            joint.position.z = pose.pz
            joint.orientation.x = pose.qx
            joint.orientation.y = pose.qy
            joint.orientation.z = pose.qz
            joint.orientation.w = pose.qw
            message.poses.append(joint)
        self._hand_publishers[side].publish(message)

    def _publish_transform(
        self,
        stamp,
        parent: str,
        child: str,
        pose: RigidPose,
        role: str,
    ) -> TransformStamped:
        message = TransformStamped()
        message.header.stamp = stamp
        message.header.frame_id = parent
        message.child_frame_id = child
        message.transform.translation.x = pose.px
        message.transform.translation.y = pose.py
        message.transform.translation.z = pose.pz
        message.transform.rotation.x = pose.qx
        message.transform.rotation.y = pose.qy
        message.transform.rotation.z = pose.qz
        message.transform.rotation.w = pose.qw
        self._transform_publishers[role].publish(message)
        return message

    def _joy(self, stamp, frame_id: str, value: HandInput) -> Joy:
        message = Joy()
        message.header.stamp, message.header.frame_id = stamp, frame_id
        message.axes = [
            value.stick_x,
            value.stick_y,
            value.trigger_analog,
            value.grip_analog,
        ]
        message.buttons = [
            int(value.trigger_pressed),
            int(value.grip_pressed),
            int(value.stick_clicked),
            int(value.face_primary),
            int(value.face_secondary),
        ]
        return message

    def _publish_status(self) -> None:
        status = self._server.get_stats().__dict__.copy()
        status.update(self._server.get_xr_stats())
        status.update(conversion_errors=self._conversion_errors, xr_samples=self._xr_samples)
        message = String()
        message.data = json.dumps(status, separators=(",", ":"))
        self._status_publisher.publish(message)

    def destroy_node(self) -> bool:
        self._stop_sources()
        self._server.stop_background()
        return super().destroy_node()


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = None
    executor = None
    try:
        node = XrMediaNode()
        executor = MultiThreadedExecutor()
        executor.add_node(node)
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            try:
                if executor is not None:
                    executor.shutdown()
            finally:
                if node is not None:
                    node.destroy_node()
        finally:
            rclpy.try_shutdown()


if __name__ == "__main__":
    main()
