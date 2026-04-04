from pipeline.angles import compute_angles


def detect_phases(landmark_sequence):
    """Detect shot phases from a sequence of per-frame landmarks.

    Looks for the release point by finding the frame where the shooting
    wrist reaches its highest point (lowest y in normalized coords).

    Returns a dict with frame indices:
        {
            "release": int,       # frame index of release point
            "gather_start": int,  # earliest frame with significant knee bend
            "set_point": int,     # frame where elbow angle is tightest before release
            "follow_through": int # last frame
        }
    Returns None if phases can't be determined.
    """
    if not landmark_sequence or len(landmark_sequence) < 6:
        return None

    # Find shooting side (whichever wrist goes higher)
    best_side = _detect_shooting_side(landmark_sequence)
    if not best_side:
        return None

    wrist_key = f"{best_side}_wrist"
    elbow_key = f"{best_side}_elbow"
    knee_key = f"{best_side}_knee"

    # Release = frame where shooting wrist is highest (lowest y)
    release = _find_release(landmark_sequence, wrist_key)
    if release is None:
        return None

    # Set point = tightest elbow angle before release
    set_point = _find_set_point(landmark_sequence, release, best_side)

    # Gather start = first frame with significant knee bend (from the start)
    gather_start = _find_gather(landmark_sequence, release, best_side)

    return {
        "shooting_side": best_side,
        "gather_start": gather_start,
        "set_point": set_point,
        "release": release,
        "follow_through": len(landmark_sequence) - 1,
    }


def _detect_shooting_side(landmarks):
    """Determine which hand is the shooting hand."""
    left_min = float("inf")
    right_min = float("inf")

    for lm in landmarks:
        if not lm:
            continue
        lw = lm.get("left_wrist")
        rw = lm.get("right_wrist")
        if lw and lw["visibility"] > 0.2:
            left_min = min(left_min, lw["y"])
        if rw and rw["visibility"] > 0.2:
            right_min = min(right_min, rw["y"])

    if left_min == float("inf") and right_min == float("inf"):
        return None
    return "left" if left_min < right_min else "right"


def _find_release(landmarks, wrist_key):
    """Find the frame where the wrist reaches its highest point."""
    best_y = float("inf")
    best_idx = None

    for i, lm in enumerate(landmarks):
        if not lm:
            continue
        w = lm.get(wrist_key)
        if w and w["visibility"] > 0.2 and w["y"] < best_y:
            best_y = w["y"]
            best_idx = i

    return best_idx


def _find_set_point(landmarks, release_idx, side):
    """Find the frame with the tightest elbow angle before release."""
    best_angle = float("inf")
    best_idx = 0

    for i in range(release_idx + 1):
        lm = landmarks[i]
        if not lm:
            continue
        angles = compute_angles(lm)
        if not angles:
            continue
        elbow = angles.get(f"{side}_elbow")
        if elbow is not None and elbow < best_angle:
            best_angle = elbow
            best_idx = i

    return best_idx


def _find_gather(landmarks, release_idx, side):
    """Find the first frame with significant knee bend."""
    knee_key = f"{side}_knee"

    # Get the standing knee angle (first few frames)
    standing_angles = []
    for lm in landmarks[:5]:
        if not lm:
            continue
        angles = compute_angles(lm)
        if angles and knee_key in angles:
            standing_angles.append(angles[knee_key])

    if not standing_angles:
        return 0

    standing = sum(standing_angles) / len(standing_angles)

    # Find first frame where knee bends more than 10 degrees from standing
    for i in range(min(release_idx, len(landmarks))):
        lm = landmarks[i]
        if not lm:
            continue
        angles = compute_angles(lm)
        if not angles:
            continue
        knee = angles.get(knee_key)
        if knee is not None and standing - knee > 10:
            return i

    return 0


def compute_angle_sequence(landmark_sequence):
    """Compute joint angles for every frame in a sequence.

    Returns list of angle dicts (one per frame), aligned with input.
    """
    return [compute_angles(lm) for lm in landmark_sequence]
