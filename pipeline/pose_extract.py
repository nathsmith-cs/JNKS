"""Pose keypoint extraction for video clips (used by the upload analysis path).

Unlike tracker.py which operates frame-by-frame in IMAGE mode for real-time use,
this module processes full video clips in VIDEO mode for batch analysis.

Optimizations:
- Singleton PoseLandmarker (avoids ~300-500ms init per clip)
- Frame sampling (every 3rd frame by default)
"""

import threading

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)

from pipeline.tracker import MODEL_PATH, LANDMARK_NAMES

# MediaPipe landmark indices for key joints
SHOULDER = 11
ELBOW = 13
WRIST = 15
HIP = 23
KNEE = 25
ANKLE = 27


def keypoints_to_named(clip_frames: list[list[list[float]]]) -> list[dict | None]:
    """Convert index-based keypoint frames to named-dict format.

    Input:  list of frames, each frame = 33 landmarks as [x, y, z]
    Output: list of dicts mapping landmark name -> {x, y, z, visibility}

    This allows reusing pose data from extract_keypoints() in compare.py
    and phases.py, which expect the named-dict format from tracker.py.
    """
    result: list[dict | None] = []
    for frame in clip_frames:
        named = {}
        for idx, name in LANDMARK_NAMES.items():
            if idx < len(frame):
                lm = frame[idx]
                named[name] = {
                    "x": lm[0], "y": lm[1], "z": lm[2],
                    "visibility": 1.0,
                }
        result.append(named if named else None)
    return result

# Singleton landmarker — created once, reused across clips.
# A lock guards creation since clips may be processed in parallel threads.
_landmarker: PoseLandmarker | None = None
_landmarker_lock = threading.Lock()


def _get_landmarker() -> PoseLandmarker:
    global _landmarker
    if _landmarker is None:
        with _landmarker_lock:
            if _landmarker is None:
                options = PoseLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=MODEL_PATH),
                    running_mode=RunningMode.VIDEO,
                )
                _landmarker = PoseLandmarker.create_from_options(options)
    return _landmarker


def extract_keypoints(
    video_path: str,
    sample_every: int = 3,
) -> list[list[list[float]]]:
    """Extract pose landmarks from a video clip.

    Args:
        video_path: Path to the video file.
        sample_every: Process every Nth frame (default 3).
            Set to 1 to process every frame.

    Returns a list of frames, where each frame is a list of 33 landmarks,
    each landmark being [x, y, z].
    """
    landmarker = _get_landmarker()
    cap = cv2.VideoCapture(video_path)
    frames: list[list[list[float]]] = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_every == 0:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            result = landmarker.detect_for_video(mp_image, frame_idx)

            if result.pose_landmarks:
                pts = [[lm.x, lm.y, lm.z] for lm in result.pose_landmarks[0]]
                frames.append(pts)

        frame_idx += 1

    cap.release()
    return frames
