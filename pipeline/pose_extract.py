"""Pose keypoint extraction for video clips (used by the upload analysis path).

Unlike tracker.py which operates frame-by-frame in IMAGE mode for real-time use,
this module processes full video clips in VIDEO mode for batch analysis.
"""

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)

from pipeline.tracker import MODEL_PATH

# MediaPipe landmark indices for key joints
SHOULDER = 11
ELBOW = 13
WRIST = 15
HIP = 23
KNEE = 25
ANKLE = 27


def extract_keypoints(video_path: str) -> list[list[list[float]]]:
    """Extract pose landmarks from every frame of a video clip.

    Returns a list of frames, where each frame is a list of 33 landmarks,
    each landmark being [x, y, z].
    """
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
    )
    landmarker = PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(video_path)
    frames: list[list[list[float]]] = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        result = landmarker.detect_for_video(mp_image, frame_idx)

        if result.pose_landmarks:
            pts = [[lm.x, lm.y, lm.z] for lm in result.pose_landmarks[0]]
            frames.append(pts)
        frame_idx += 1

    cap.release()
    landmarker.close()
    return frames
