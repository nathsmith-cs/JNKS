import os
from collections import deque

import cv2
from ultralytics import YOLO

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
CUSTOM_MODEL = os.path.join(MODELS_DIR, "basketball.pt")
FALLBACK_MODEL = "yolov8s.pt"

# COCO classes used as fallback when no custom model is available
FALLBACK_BALL_CLASSES = {32, 29, 35, 26}


class BallDetector:
    def __init__(self, confidence=0.25):
        if os.path.exists(CUSTOM_MODEL):
            self._model = YOLO(CUSTOM_MODEL)
            self._custom = True
            print(f"Loaded custom basketball model: {CUSTOM_MODEL}")
        else:
            self._model = YOLO(FALLBACK_MODEL)
            self._custom = False
            print("No basketball.pt found — using generic YOLO (run train_detector.py)")
        self._confidence = confidence

    def detect(self, frame_bgr):
        """Run YOLOv8 on a frame, return list of ball bounding boxes."""
        h, w = frame_bgr.shape[:2]
        long_side = max(w, h)
        if long_side > 960:
            scale = 960 / long_side
            small = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)))
        else:
            small = frame_bgr
            scale = 1.0
        results = self._model(small, conf=self._confidence, imgsz=960, verbose=False)
        boxes = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                if self._custom or cls_id in FALLBACK_BALL_CLASSES:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    boxes.append({
                        "x1": x1 / scale, "y1": y1 / scale,
                        "x2": x2 / scale, "y2": y2 / scale,
                        "confidence": float(box.conf[0]),
                    })
        return boxes


class BallTracker:
    """Temporal smoothing: requires ball detected in 3 of last 5 frames."""

    def __init__(self, window=5, threshold=2):
        self._history = deque(maxlen=window)
        self._threshold = threshold

    def update(self, landmarks, ball_boxes, frame_w, frame_h):
        # Scale threshold with frame size — 200px was calibrated for 640px wide
        threshold = int(max(frame_w, frame_h) * 0.3)
        raw = _check_near_hands(landmarks, ball_boxes, frame_w, frame_h, threshold)
        self._history.append(raw["has_ball"])

        confirmed = sum(self._history) >= self._threshold
        return {
            "has_ball": confirmed,
            "closest_ball": raw["closest_ball"] if confirmed else None,
        }


def _check_near_hands(landmarks, ball_boxes, frame_w, frame_h, threshold_px=200):
    if not landmarks or not ball_boxes:
        return {"has_ball": False, "closest_ball": None}

    wrist_keys = ["left_wrist", "right_wrist",
                  "left_index", "right_index",
                  "left_pinky", "right_pinky"]

    wrist_points = []
    for key in wrist_keys:
        lm = landmarks.get(key)
        if lm and lm["visibility"] > 0.2:
            wrist_points.append((lm["x"] * frame_w, lm["y"] * frame_h))

    if not wrist_points:
        return {"has_ball": False, "closest_ball": None}

    best_dist = float("inf")
    best_box = None

    for box in ball_boxes:
        cx = (box["x1"] + box["x2"]) / 2
        cy = (box["y1"] + box["y2"]) / 2
        for wx, wy in wrist_points:
            dist = ((cx - wx) ** 2 + (cy - wy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_box = box

    has_ball = best_dist <= threshold_px
    return {
        "has_ball": has_ball,
        "closest_ball": best_box if has_ball else None,
    }
