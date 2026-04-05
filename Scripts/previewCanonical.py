"""
previewCanonical.py — Render a canonical profile JSON as a black background wireframe video.

Usage:
    python3 previewCanonical.py ShooterCanonicalJsons/StephCurry.json
    python3 previewCanonical.py ShooterCanonicalJsons/StephCurry.json -o StephCurryPreview.mp4 --fps 10
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

WIDTH = 640
HEIGHT = 720
VISIBILITY_THRESHOLD = 0.3

LANDMARK_COLOR = (0, 255, 0)
CONNECTION_COLOR = (255, 255, 255)

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

CONNECTED_INDICES = {i for pair in CONNECTIONS for i in pair}


def landmarks_to_pixels(landmarks: list) -> list:
    """Convert normalized (nx, ny) coordinates to pixel coordinates.

    nx/ny are centered on the hips and scaled by torso length, so they're
    roughly in the range [-2, 2]. We map that range to the frame with padding.
    """
    NX_MIN, NX_MAX = -3.0, 3.0
    NY_MIN, NY_MAX = -3.0, 2.5
    PADDING = 60

    def to_px(nx, ny):
        x = int((nx - NX_MIN) / (NX_MAX - NX_MIN) * (WIDTH - 2 * PADDING) + PADDING)
        y = int((ny - NY_MIN) / (NY_MAX - NY_MIN) * (HEIGHT - 2 * PADDING) + PADDING)
        return x, y

    return [
        to_px(lm["nx"], lm["ny"]) if lm is not None else None
        for lm in landmarks
    ]


def draw_frame(landmarks: list) -> np.ndarray:
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    points = landmarks_to_pixels(landmarks)

    for a, b in CONNECTIONS:
        lm_a = landmarks[a]
        lm_b = landmarks[b]
        if (lm_a is not None and lm_b is not None
                and lm_a["visibility"] > VISIBILITY_THRESHOLD
                and lm_b["visibility"] > VISIBILITY_THRESHOLD
                and points[a] is not None and points[b] is not None):
            cv2.line(canvas, points[a], points[b], CONNECTION_COLOR, 2)

    for i in CONNECTED_INDICES:
        lm = landmarks[i]
        if lm is not None and lm["visibility"] > VISIBILITY_THRESHOLD and points[i] is not None:
            cv2.circle(canvas, points[i], 4, LANDMARK_COLOR, -1)

    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a canonical profile JSON as a black background wireframe video."
    )
    parser.add_argument("input", help="Path to the canonical profile JSON")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output video path (default: <input_stem>_preview.mp4 alongside input)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=10.0,
        help="Playback framerate of the output video (default: 10)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.parent / f"{input_path.stem}_preview.mp4"

    with open(input_path) as f:
        data = json.load(f)

    profile_frames = data["profile"]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, args.fps, (WIDTH, HEIGHT))

    for frame_data in profile_frames:
        canvas = draw_frame(frame_data["landmarks"])
        out.write(canvas)

    out.release()
    print(f"Preview saved to '{output_path}' ({len(profile_frames)} frames at {args.fps} fps).")


if __name__ == "__main__":
    main()
