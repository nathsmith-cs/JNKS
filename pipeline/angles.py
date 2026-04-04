import math


def _angle(a, b, c):
    """Angle at point b given three landmarks (each has x, y)."""
    ba = (a["x"] - b["x"], a["y"] - b["y"])
    bc = (c["x"] - b["x"], c["y"] - b["y"])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba == 0 or mag_bc == 0:
        return None
    cos = max(-1, min(1, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos))


def compute_angles(landmarks):
    """Compute basketball-relevant joint angles from a single frame's landmarks.

    Returns a dict of angle name -> degrees, or None for low-visibility joints.
    """
    if not landmarks:
        return None

    def get(name):
        lm = landmarks.get(name)
        if lm and lm["visibility"] > 0.2:
            return lm
        return None

    angles = {}

    # Elbow angles
    for side in ["left", "right"]:
        s = get(f"{side}_shoulder")
        e = get(f"{side}_elbow")
        w = get(f"{side}_wrist")
        if s and e and w:
            angles[f"{side}_elbow"] = _angle(s, e, w)

    # Shoulder elevation (hip-shoulder-elbow)
    for side in ["left", "right"]:
        h = get(f"{side}_hip")
        s = get(f"{side}_shoulder")
        e = get(f"{side}_elbow")
        if h and s and e:
            angles[f"{side}_shoulder"] = _angle(h, s, e)

    # Knee angles (hip-knee-ankle)
    for side in ["left", "right"]:
        h = get(f"{side}_hip")
        k = get(f"{side}_knee")
        a = get(f"{side}_ankle")
        if h and k and a:
            angles[f"{side}_knee"] = _angle(h, k, a)

    # Hip angles (shoulder-hip-knee)
    for side in ["left", "right"]:
        s = get(f"{side}_shoulder")
        h = get(f"{side}_hip")
        k = get(f"{side}_knee")
        if s and h and k:
            angles[f"{side}_hip"] = _angle(s, h, k)

    # Wrist height relative to head (using shoulder as proxy)
    # Negative = wrist above shoulder, positive = below
    for side in ["left", "right"]:
        w = get(f"{side}_wrist")
        s = get(f"{side}_shoulder")
        if w and s:
            angles[f"{side}_wrist_height"] = w["y"] - s["y"]

    return angles if angles else None
