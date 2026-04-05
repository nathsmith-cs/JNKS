import json
import math
import os
import glob

from pipeline.phases import detect_phases, compute_angle_sequence

# Angles that matter most for shot form comparison
COMPARE_KEYS = [
    "right_elbow", "left_elbow",
    "right_shoulder", "left_shoulder",
    "right_knee", "left_knee",
    "right_hip", "left_hip",
    "right_wrist_height", "left_wrist_height",
]


def compare_shots(user_landmarks, ref_landmarks):
    """Compare a user's shot to a reference shot.

    Both inputs are lists of per-frame landmark dicts.
    Aligns from the release point backwards.

    Returns:
        {
            "overall_score": float (0-100),
            "phase_scores": {"gather": ..., "set_point": ..., "release": ..., "follow_through": ...},
            "angle_diffs": {angle_name: avg_degrees_off},
            "shooting_side": str,
            "user_phases": dict,
            "ref_phases": dict,
        }
    or None if comparison can't be made.
    """
    user_phases = detect_phases(user_landmarks)
    ref_phases = detect_phases(ref_landmarks)

    if not user_phases or not ref_phases:
        return None

    user_angles = compute_angle_sequence(user_landmarks)
    ref_angles = compute_angle_sequence(ref_landmarks)

    # Use the reference's shooting side for comparison
    side = ref_phases["shooting_side"]

    # Align from release backwards
    user_release = user_phases["release"]
    ref_release = ref_phases["release"]

    # Compare each phase
    phase_scores = {}

    # Gather: from gather_start to set_point
    phase_scores["gather"] = _compare_phase(
        user_angles, ref_angles,
        user_phases["gather_start"], user_phases["set_point"],
        ref_phases["gather_start"], ref_phases["set_point"],
        user_release, ref_release, side,
    )

    # Set point: single frame comparison
    phase_scores["set_point"] = _compare_frames(
        user_angles[user_phases["set_point"]] if user_phases["set_point"] < len(user_angles) else None,
        ref_angles[ref_phases["set_point"]] if ref_phases["set_point"] < len(ref_angles) else None,
        side,
    )

    # Release: single frame comparison
    phase_scores["release"] = _compare_frames(
        user_angles[user_release] if user_release < len(user_angles) else None,
        ref_angles[ref_release] if ref_release < len(ref_angles) else None,
        side,
    )

    # Follow-through: from release to end
    phase_scores["follow_through"] = _compare_phase(
        user_angles, ref_angles,
        user_release, len(user_angles) - 1,
        ref_release, len(ref_angles) - 1,
        user_release, ref_release, side,
    )

    # Angle diffs (averaged across all aligned frames)
    angle_diffs = _compute_angle_diffs(
        user_angles, ref_angles,
        user_release, ref_release, side,
    )

    # Weight phases: release and set_point matter most
    weights = {"gather": 0.15, "set_point": 0.3, "release": 0.35, "follow_through": 0.2}
    overall = sum(phase_scores.get(p, 0) * w for p, w in weights.items())

    return {
        "overall_score": round(overall, 1),
        "phase_scores": {k: round(v, 1) for k, v in phase_scores.items()},
        "angle_diffs": {k: round(v, 1) for k, v in angle_diffs.items()},
        "shooting_side": side,
        "user_phases": user_phases,
        "ref_phases": ref_phases,
    }


def _compare_phase(user_angles, ref_angles,
                    user_start, user_end,
                    ref_start, ref_end,
                    user_anchor, ref_anchor, side):
    """Compare a phase by resampling to the same number of steps."""
    user_slice = user_angles[user_start:user_end + 1]
    ref_slice = ref_angles[ref_start:ref_end + 1]

    if not user_slice or not ref_slice:
        return 50.0

    # Resample to the shorter length
    n = min(len(user_slice), len(ref_slice))
    user_resampled = _resample(user_slice, n)
    ref_resampled = _resample(ref_slice, n)

    scores = []
    for u, r in zip(user_resampled, ref_resampled):
        scores.append(_compare_frames(u, r, side))

    return sum(scores) / len(scores) if scores else 50.0


def _compare_frames(user_frame, ref_frame, side):
    """Compare two angle dicts. Returns 0-100 score."""
    if not user_frame or not ref_frame:
        return 50.0

    diffs = []
    for key in COMPARE_KEYS:
        # Prefer the shooting side
        if key.startswith("left_") and side == "right":
            continue
        if key.startswith("right_") and side == "left":
            continue

        u = user_frame.get(key)
        r = ref_frame.get(key)
        if u is not None and r is not None:
            if "wrist_height" in key:
                # Normalize height diff (0.1 in normalized coords ≈ 15 degrees equivalent)
                diffs.append(abs(u - r) * 150)
            else:
                diffs.append(abs(u - r))

    if not diffs:
        return 50.0

    avg_diff = sum(diffs) / len(diffs)
    # 0 degrees diff = 100, 45+ degrees diff = 0
    score = max(0, 100 - (avg_diff / 45) * 100)
    return score


def _compute_angle_diffs(user_angles, ref_angles,
                         user_release, ref_release, side):
    """Average angle differences across all aligned frames."""
    # Walk backwards from release, aligning frame by frame
    max_back = min(user_release, ref_release)
    max_fwd = min(len(user_angles) - user_release, len(ref_angles) - ref_release)

    totals = {}
    counts = {}

    for offset in range(-max_back, max_fwd):
        ui = user_release + offset
        ri = ref_release + offset
        if ui < 0 or ri < 0 or ui >= len(user_angles) or ri >= len(ref_angles):
            continue
        u = user_angles[ui]
        r = ref_angles[ri]
        if not u or not r:
            continue

        for key in COMPARE_KEYS:
            uv = u.get(key)
            rv = r.get(key)
            if uv is not None and rv is not None:
                if "wrist_height" in key:
                    diff = abs(uv - rv) * 150
                else:
                    diff = abs(uv - rv)
                totals[key] = totals.get(key, 0) + diff
                counts[key] = counts.get(key, 0) + 1

    return {k: totals[k] / counts[k] for k in totals if counts[k] > 0}


def _resample(seq, n):
    """Resample a sequence to exactly n elements via nearest-neighbor."""
    if n <= 0:
        return []
    step = len(seq) / n
    return [seq[min(int(i * step), len(seq) - 1)] for i in range(n)]


# MediaPipe index -> name mapping (same as tracker.py)
_INDEX_TO_NAME = {
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


def _convert_ref_frame(landmarks_array):
    """Convert a 33-element landmark array (by index) to our named dict format."""
    named = {}
    for idx, name in _INDEX_TO_NAME.items():
        if idx < len(landmarks_array):
            lm = landmarks_array[idx]
            named[name] = {
                "x": lm["x"],
                "y": lm["y"],
                "z": lm["z"],
                "visibility": lm.get("visibility", 1.0),
            }
    return named


def _load_single_ref(path):
    """Load a reference JSON, handling both pipeline and external formats.

    Pipeline format: {"landmarks": [{name: {x,y,z,vis}}, ...]}
    External format: {"frames": [{"landmarks": [{x,y,z,vis,...}, ...]}, ...]}
    """
    with open(path) as f:
        data = json.load(f)

    # Pipeline format — landmarks is a list of named dicts
    landmarks = data.get("landmarks")
    if landmarks and isinstance(landmarks, list) and isinstance(landmarks[0], dict):
        first = landmarks[0]
        if any(k in first for k in ["left_shoulder", "right_shoulder"]):
            return landmarks

    # External format — frames[].landmarks[] as 33-element arrays
    frames = data.get("frames")
    if frames and isinstance(frames, list):
        converted = []
        for frame in frames:
            lm_array = frame.get("landmarks")
            if lm_array and isinstance(lm_array, list):
                converted.append(_convert_ref_frame(lm_array))
            else:
                converted.append(None)
        return converted if any(c is not None for c in converted) else None

    return None


def load_reference_shots(ref_dir):
    """Load all shot JSON files from a reference directory.

    Returns list of (filename, landmarks) tuples.
    Handles both pipeline output format and external MediaPipe format.
    """
    shots = []
    for path in sorted(glob.glob(os.path.join(ref_dir, "*.json"))):
        landmarks = _load_single_ref(path)
        if landmarks:
            shots.append((os.path.basename(path), landmarks))
    return shots


def find_best_match(user_landmarks, ref_dir):
    """Compare a user shot against all reference shots and return the best match.

    Args:
        user_landmarks: list of per-frame landmark dicts for the user's shot
        ref_dir: path to directory containing reference shot_*.json files

    Returns:
        {
            "best_ref": str (filename of best matching reference),
            "best_score": float (0-100),
            "analysis": dict (full compare_shots result for best match),
            "all_scores": [(filename, score), ...] sorted best to worst,
        }
    or None if no valid comparison could be made.
    """
    ref_shots = load_reference_shots(ref_dir)
    if not ref_shots:
        return None

    results = []
    for ref_name, ref_landmarks in ref_shots:
        result = compare_shots(user_landmarks, ref_landmarks)
        if result:
            results.append((ref_name, result))

    if not results:
        return None

    results.sort(key=lambda x: x[1]["overall_score"], reverse=True)

    best_name, best_analysis = results[0]
    return {
        "best_ref": best_name,
        "best_score": best_analysis["overall_score"],
        "analysis": best_analysis,
        "all_scores": [(name, r["overall_score"]) for name, r in results],
    }


def find_best_match_all(user_landmarks, ref_base_dir):
    """Compare a user shot against ALL reference player directories.

    Searches every subfolder in ref_base_dir (StephCurryShots, KlayThompsonShots, etc.)
    and returns the single best match across all players.
    """
    all_results = []
    if not os.path.isdir(ref_base_dir):
        return None

    for player_dir in sorted(os.listdir(ref_base_dir)):
        player_path = os.path.join(ref_base_dir, player_dir)
        if not os.path.isdir(player_path):
            continue
        match = find_best_match(user_landmarks, player_path)
        if match:
            match["player"] = player_dir
            all_results.append(match)

    if not all_results:
        return None

    all_results.sort(key=lambda x: x["best_score"], reverse=True)
    return all_results[0]
