"""Video preprocessing: format conversion and clip splitting via ffmpeg."""

import os
import subprocess
import tempfile

import cv2
import numpy as np

# Maximum seconds per clip when splitting
DEFAULT_MAX_CLIP_SEC = 5


def convert_video(path: str) -> str:
    """Convert video to mp4 if needed (.mov, .webm, .avi, .mkv).

    Returns the path to the mp4 file (may be the original if already mp4).
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")
    if os.path.getsize(path) < 10_000:
        raise ValueError(f"{path} looks too small to be a valid video")

    ext = os.path.splitext(path)[1].lower()
    if ext in (".mov", ".webm", ".avi", ".mkv"):
        output = os.path.splitext(path)[0] + ".mp4"
        if not os.path.exists(output):
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", path,
                 "-c:v", "libx264", "-c:a", "aac", output],
                capture_output=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg failed: {result.stderr.decode(errors='replace')}"
                )
        return output
    return path


def split_video(video_path: str, max_sec: int = DEFAULT_MAX_CLIP_SEC) -> list[str]:
    """Split a video into clips of *max_sec* seconds each.

    Returns a list of file paths to the clip mp4 files.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if fps <= 0:
        raise ValueError("Could not read video FPS")

    duration_sec = total_frames / fps
    clip_count = int(np.ceil(duration_sec / max_sec))
    temp_dir = tempfile.mkdtemp()
    clips: list[str] = []

    for i in range(clip_count):
        start = i * max_sec
        output_clip = os.path.join(temp_dir, f"clip_{i}.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path,
             "-ss", str(start), "-t", str(max_sec),
             "-c:v", "libx264", "-c:a", "aac", output_clip],
            capture_output=True,
            check=True,
        )
        clips.append(output_clip)

    return clips
