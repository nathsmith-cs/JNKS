"""
buildProfile.py — Build an averaged shooter profile from multiple shot JSONs.

Usage:
    python3 buildProfile.py ShooterJsons/StephCurryShot*.json -o ShooterProfiles/StephCurry.json
    python3 buildProfile.py ShooterJsons/StephCurryShot*.json -o ShooterProfiles/StephCurry.json --frames 15
"""

import argparse
import json
from pathlib import Path

NUM_LANDMARKS = 33
CANONICAL_DIR = Path(__file__).parent / "ShooterCanonicalJsons"


def load_json(path: str) -> list:
    with open(path) as f:
        data = json.load(f)
    return data["frames"]


def resample_frames(frames: list, target: int) -> list:
    """Resample a frame sequence to exactly `target` frames using linear interpolation."""
    n = len(frames)
    if n == 0:
        return []
    if n == target:
        return frames

    resampled = []
    for i in range(target):
        # Position in the original sequence
        pos = i * (n - 1) / (target - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        t = pos - lo

        lo_frame = frames[lo]
        hi_frame = frames[hi]

        # Skip frames with no detected landmarks
        if not lo_frame["landmarks"] or not hi_frame["landmarks"]:
            resampled.append(None)
            continue

        interpolated = []
        for lm_lo, lm_hi in zip(lo_frame["landmarks"], hi_frame["landmarks"]):
            interpolated.append({
                "nx": lm_lo["nx"] * (1 - t) + lm_hi["nx"] * t,
                "ny": lm_lo["ny"] * (1 - t) + lm_hi["ny"] * t,
                "nz": lm_lo["nz"] * (1 - t) + lm_hi["nz"] * t,
                "visibility": lm_lo["visibility"] * (1 - t) + lm_hi["visibility"] * t,
            })
        resampled.append({"landmarks": interpolated})

    return resampled


def average_shots(all_resampled: list, target: int) -> list:
    """Average normalized landmarks across all shots at each frame position."""
    averaged = []
    for frame_idx in range(target):
        landmark_sums = [{"nx": 0.0, "ny": 0.0, "nz": 0.0, "visibility": 0.0} for _ in range(NUM_LANDMARKS)]
        counts = [0] * NUM_LANDMARKS

        for shot in all_resampled:
            frame = shot[frame_idx]
            if frame is None or not frame["landmarks"]:
                continue
            for lm_idx, lm in enumerate(frame["landmarks"]):
                landmark_sums[lm_idx]["nx"] += lm["nx"]
                landmark_sums[lm_idx]["ny"] += lm["ny"]
                landmark_sums[lm_idx]["nz"] += lm["nz"]
                landmark_sums[lm_idx]["visibility"] += lm["visibility"]
                counts[lm_idx] += 1

        frame_avg = []
        for lm_idx in range(NUM_LANDMARKS):
            c = counts[lm_idx]
            if c == 0:
                frame_avg.append(None)
            else:
                frame_avg.append({
                    "nx": landmark_sums[lm_idx]["nx"] / c,
                    "ny": landmark_sums[lm_idx]["ny"] / c,
                    "nz": landmark_sums[lm_idx]["nz"] / c,
                    "visibility": landmark_sums[lm_idx]["visibility"] / c,
                })
        averaged.append({"frame": frame_idx, "landmarks": frame_avg})

    return averaged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an averaged shooter profile from multiple shot JSONs."
    )
    parser.add_argument("inputs", nargs="+", help="Shot JSON files to average")
    parser.add_argument("-o", "--output", required=True, help="Output profile JSON path")
    parser.add_argument(
        "--frames",
        type=int,
        default=30,
        help="Number of frames to resample each shot to before averaging (default: 30)",
    )
    args = parser.parse_args()

    print(f"Loading {len(args.inputs)} shot(s)...")
    all_resampled = []
    for path in args.inputs:
        frames = load_json(path)
        resampled = resample_frames(frames, args.frames)
        all_resampled.append(resampled)
        print(f"  {path}: {len(frames)} frames → resampled to {args.frames}")

    print("Averaging...")
    profile = average_shots(all_resampled, args.frames)

    output_path = CANONICAL_DIR / Path(args.output).name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "shots_used": len(args.inputs),
            "frames": args.frames,
            "profile": profile,
        }, f, indent=2)

    print(f"Profile saved to '{output_path}' ({len(args.inputs)} shots, {args.frames} frames).")


if __name__ == "__main__":
    main()
