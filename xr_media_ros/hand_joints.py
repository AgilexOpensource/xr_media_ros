"""Fixed WebXR joint order for the hand PoseArray wire format."""

HAND_JOINT_NAMES = (
    "wrist",
    "thumb-metacarpal",
    "thumb-phalanx-proximal",
    "thumb-phalanx-distal",
    "thumb-tip",
    *(f"{finger}-finger-{segment}" for finger in
      ("index", "middle", "ring", "pinky") for segment in
      ("metacarpal", "phalanx-proximal", "phalanx-intermediate",
       "phalanx-distal", "tip")),
)
