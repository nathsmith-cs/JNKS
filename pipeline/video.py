"""Video preprocessing: format conversion and clip splitting via ffmpeg."""

import os
import subprocess
import tempfile

import cv2
import numpy as np

# Maximum seconds per clip when splitting
DEFAULT_MAX_CLIP_SEC = 5


def _probe_video_codec(path: str) -> str:
    """Return the video codec name (e.g. 'h264', 'vp8') or empty string."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def convert_video(path: str) -> str:
    """Convert video to mp4 if needed (.mov, .webm, .avi, .mkv).

    If the source is already H.264, does a fast remux (~0.2s) instead of a
    full re-encode (~4s).  Returns the path to the mp4 file.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")
    if os.path.getsize(path) < 10_000:
        raise ValueError(f"{path} looks too small to be a valid video")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".mp4":
        return path

    if ext not in (".mov", ".webm", ".avi", ".mkv"):
        return path

    output = os.path.splitext(path)[0] + ".mp4"
    if os.path.exists(output):
        return output

    # Probe the codec — remux if already H.264, re-encode otherwise
    codec = _probe_video_codec(path)
    if codec == "h264":
        cmd = ["ffmpeg", "-y", "-i", path, "-c", "copy", output]
    else:
        cmd = ["ffmpeg", "-y", "-i", path,
               "-c:v", "libx264", "-c:a", "aac", output]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed: {result.stderr.decode(errors='replace')}"
        )
    return output


def split_video(video_path: str, max_sec: int = DEFAULT_MAX_CLIP_SEC) -> list[str]:
    """Split a video into clips of *max_sec* seconds each.

    Launches all ffmpeg processes concurrently for speed.
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

    # Launch all ffmpeg processes concurrently
    procs: list[tuple[str, subprocess.Popen]] = []
    for i in range(clip_count):
        start = i * max_sec
        output_clip = os.path.join(temp_dir, f"clip_{i}.mp4")
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-i", video_path,
             "-ss", str(start), "-t", str(max_sec),
             "-c:v", "libx264", "-c:a", "aac", output_clip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        procs.append((output_clip, proc))

    # Wait for all to finish
    clips: list[str] = []
    for output_clip, proc in procs:
        returncode = proc.wait()
        if returncode != 0:
            stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
            raise RuntimeError(f"FFmpeg split failed: {stderr}")
        clips.append(output_clip)

    return clips
