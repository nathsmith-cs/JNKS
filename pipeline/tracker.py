import os

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "pose_landmarker_lite.task")

# Only basketball-form-relevant landmarks.
# Indices reference the full 33-point MediaPipe pose model.
LANDMARK_NAMES = {
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    19: "left_index",
    20: "right_index",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
    29: "left_heel",
    30: "right_heel",
    31: "left_foot_index",
    32: "right_foot_index",
}


class PoseTracker:
    def __init__(self):
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            num_poses=1,
        )
        self._landmarker = PoseLandmarker.create_from_options(options)

    def process(self, frame_bgr):
        """Run pose inference on a BGR frame.

        Returns a dict mapping landmark names to {x, y, z, visibility},
        or None if no pose was detected.
        """
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                            data=np.ascontiguousarray(frame_bgr[:, :, ::-1]))
        result = self._landmarker.detect(mp_image)

        if not result.pose_landmarks:
            return None

        pose = result.pose_landmarks[0]
        landmarks = {}
        for idx, name in LANDMARK_NAMES.items():
            lm = pose[idx]
            landmarks[name] = {
                "x": float(lm.x),
                "y": float(lm.y),
                "z": float(lm.z),
                "visibility": float(lm.visibility),
            }
        return landmarks

    def close(self):
        self._landmarker.close()
