import argparse
import json
import math
import sys
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
MODEL_PATH = Path(__file__).parent / "pose_landmarker_heavy.task"
SHOOTER_JSONS_DIR = Path(__file__).parent / "ShooterJsons"

# Skeleton connections between MediaPipe's 33 pose landmark indices
CONNECTIONS = [
    # Torso
    (11, 12), (11, 23), (12, 24), (23, 24),
    # Left arm
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    # Right arm
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),
    # Left leg
    (23, 25), (25, 27), (27, 29), (27, 31),
    # Right leg
    (24, 26), (26, 28), (28, 30), (28, 32),
]

LANDMARK_COLOR = (0, 255, 0)    # green dots
CONNECTION_COLOR = (255, 255, 255)  # white lines


def download_model() -> None:
    print(f"Downloading pose model to {MODEL_PATH}...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Model downloaded.")


CONNECTED_INDICES = {i for pair in CONNECTIONS for i in pair}


def draw_pose(frame, landmarks, width: int, height: int) -> None:
    points = [
        (int(lm.x * width), int(lm.y * height))
        for lm in landmarks
    ]
    for a, b in CONNECTIONS:
        if landmarks[a].visibility > 0.1 and landmarks[b].visibility > 0.1:
            cv2.line(frame, points[a], points[b], CONNECTION_COLOR, 2)
    for i in CONNECTED_INDICES:
        if landmarks[i].visibility > 0.1:
            cv2.circle(frame, points[i], 4, LANDMARK_COLOR, -1)


def normalize_landmarks(landmarks: list) -> list:
    # Midpoint of hips (indices 23, 24) as origin
    hip_x = (landmarks[23]["x"] + landmarks[24]["x"]) / 2
    hip_y = (landmarks[23]["y"] + landmarks[24]["y"]) / 2
    hip_z = (landmarks[23]["z"] + landmarks[24]["z"]) / 2

    # Midpoint of shoulders (indices 11, 12)
    shoulder_x = (landmarks[11]["x"] + landmarks[12]["x"]) / 2
    shoulder_y = (landmarks[11]["y"] + landmarks[12]["y"]) / 2
    shoulder_z = (landmarks[11]["z"] + landmarks[12]["z"]) / 2

    # Torso length as scale factor
    torso_length = math.sqrt(
        (shoulder_x - hip_x) ** 2 +
        (shoulder_y - hip_y) ** 2 +
        (shoulder_z - hip_z) ** 2
    )
    if torso_length == 0:
        return landmarks

    return [
        {
            **lm,
            "nx": (lm["x"] - hip_x) / torso_length,
            "ny": (lm["y"] - hip_y) / torso_length,
            "nz": (lm["z"] - hip_z) / torso_length,
        }
        for lm in landmarks
    ]


def save_json(input_path: str, frames_data: list) -> Path:
    SHOOTER_JSONS_DIR.mkdir(exist_ok=True)
    stem = Path(input_path).stem
    json_path = SHOOTER_JSONS_DIR / f"{stem}.json"
    with open(json_path, "w") as f:
        json.dump({"source": input_path, "frames": frames_data}, f, indent=2)
    return json_path


def process_video(input_path: str, output_path: str) -> None:
    if not MODEL_PATH.exists():
        download_model()

    base_options = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
    options = PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Error: could not open video '{input_path}'")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0
    frames_data = []

    with PoseLandmarker.create_from_options(options) as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            canvas = frame.copy()
            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                draw_pose(canvas, landmarks, width, height)
                raw = [
                    {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                    for lm in landmarks
                ]
                frames_data.append({
                    "frame": frame_count,
                    "timestamp_ms": timestamp_ms,
                    "landmarks": normalize_landmarks(raw),
                })
            else:
                frames_data.append({"frame": frame_count, "timestamp_ms": timestamp_ms, "landmarks": []})

            out.write(canvas)
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Processed {frame_count} frames...")

    cap.release()
    out.release()

    json_path = save_json(input_path, frames_data)
    print(f"Done. Video saved to '{output_path}', pose data saved to '{json_path}' ({frame_count} frames).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Overlay a pose wireframe on an NBA shooting video."
    )
    parser.add_argument("input", help="Path to the input video file")
    parser.add_argument(
        "-o",
        "--output",
        default="output.mp4",
        help="Path for the output video (default: output.mp4)",
    )
    args = parser.parse_args()
    process_video(args.input, args.output)


if __name__ == "__main__":
    main()