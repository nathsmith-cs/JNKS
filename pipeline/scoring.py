"""Hybrid scoring: blends MediaPipe pose metrics with Gemini vision scores.

Produces the final AnalysisResponse-compatible dict for the upload endpoint.
"""

import math
from datetime import datetime, timezone

from pipeline.gemini_vision import (
    extract_coach_summary,
    extract_gemini_scores,
    extract_section_feedback,
)

WEIGHTS = {
    "Elbow Angle": 0.25,
    "Follow-Through": 0.25,
    "Release Point": 0.25,
    "Stance": 0.25,
}

TIPS = {
    "Elbow Angle": {
        "high": "Great elbow alignment — maintain that L-shape on every shot.",
        "mid": "Your elbow is drifting outward — tuck it under the ball.",
        "low": "Keep your elbow at 90 degrees at the set point for a consistent release.",
    },
    "Follow-Through": {
        "high": "Solid follow-through — keep that relaxed wrist flick.",
        "mid": "Your follow-through is cutting short — snap the wrist and freeze.",
        "low": "Extend your wrist fully and hold — reach into the cookie jar.",
    },
    "Release Point": {
        "high": "Great timing on the release — high arc gives a shooter's touch.",
        "mid": "Release at the peak of your jump for maximum arc.",
        "low": "You're releasing too early — wait until you reach the top.",
    },
    "Stance": {
        "high": "Strong foundation — your lower body is set up well for power.",
        "mid": "Feet shoulder-width apart with your shooting foot slightly ahead.",
        "low": "Widen your base a bit — you're losing balance on the release.",
    },
}


def _get_label(score: int | float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Needs Work"
    return "Poor"


def _get_tip(category: str, score: int) -> str:
    tips = TIPS.get(category, TIPS["Elbow Angle"])
    if score >= 80:
        return tips["high"]
    if score >= 60:
        return tips["mid"]
    return tips["low"]


def _elbow_angle_score(avg_angle: float) -> int:
    """Score based on distance from ideal 90-degree elbow angle."""
    if avg_angle == 0:
        return 50
    deviation = abs(avg_angle - 90)
    return max(0, int(100 - deviation * 2))


def _stance_score(avg_knee_angle: float) -> int:
    """Score based on knee angle within ideal 110-130 range."""
    if avg_knee_angle == 0:
        return 50
    if 110 <= avg_knee_angle <= 130:
        return 95
    if avg_knee_angle < 110:
        deviation = 110 - avg_knee_angle
    else:
        deviation = avg_knee_angle - 130
    return max(0, int(95 - deviation * 2))


def compute_clip_metrics(frames: list) -> dict:
    """Compute average elbow and knee angles from pose keypoint frames.

    *frames* is a list of 33-element landmark arrays (each landmark = [x, y, z]).
    """
    import numpy as np

    SHOULDER, ELBOW, WRIST = 11, 13, 15
    HIP, KNEE, ANKLE = 23, 25, 27

    def angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba, bc = a - b, c - b
        denom = np.linalg.norm(ba) * np.linalg.norm(bc)
        if denom == 0:
            return 0.0
        cos_val = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_val)))

    elbow_angles = []
    knee_angles = []
    for f in frames:
        elbow_angles.append(angle(f[SHOULDER], f[ELBOW], f[WRIST]))
        knee_angles.append(angle(f[HIP], f[KNEE], f[ANKLE]))

    return {
        "avg_elbow_angle": float(np.mean(elbow_angles)) if elbow_angles else 0,
        "avg_knee_angle": float(np.mean(knee_angles)) if knee_angles else 0,
        "frames_analyzed": len(frames),
    }


def summarize_session_metrics(clip_results: list[dict]) -> dict:
    """Weighted-average metrics across all clips."""
    total_frames = sum(r["metrics"]["frames_analyzed"] for r in clip_results)
    if total_frames == 0:
        return {
            "total_clips": len(clip_results),
            "total_frames_analyzed": 0,
            "weighted_avg_elbow_angle": 0,
            "weighted_avg_knee_angle": 0,
        }

    elbow_sum = sum(
        r["metrics"]["avg_elbow_angle"] * r["metrics"]["frames_analyzed"]
        for r in clip_results
    )
    knee_sum = sum(
        r["metrics"]["avg_knee_angle"] * r["metrics"]["frames_analyzed"]
        for r in clip_results
    )
    return {
        "total_clips": len(clip_results),
        "total_frames_analyzed": total_frames,
        "weighted_avg_elbow_angle": elbow_sum / total_frames,
        "weighted_avg_knee_angle": knee_sum / total_frames,
    }


def build_analysis_result(
    final_text: str,
    session_metrics: dict,
    clip_results: list[dict],
    input_type: str,
) -> dict:
    """Build the final analysis result dict from Gemini output and metrics.

    Uses hybrid scoring: 40% MediaPipe metrics + 60% Gemini vision scores
    for measurable categories, 100% Gemini for vision-only categories.
    """
    gemini_scores = extract_gemini_scores(final_text)
    coach_summary = extract_coach_summary(final_text)

    avg_elbow = session_metrics.get("weighted_avg_elbow_angle", 0)
    avg_knee = session_metrics.get("weighted_avg_knee_angle", 0)

    # MediaPipe-based scores
    mp_elbow = _elbow_angle_score(avg_elbow)
    mp_stance = _stance_score(avg_knee)

    # Gemini-based scores (default 70 if not parsed)
    g_elbow = gemini_scores.get("elbow_angle_score", 70)
    g_follow = gemini_scores.get("follow_through_score", 70)
    g_release = gemini_scores.get("release_point_score", 70)
    g_stance = gemini_scores.get("stance_score", 70)

    # Blend: measurable categories = 0.4 mediapipe + 0.6 gemini
    elbow_score = int(0.4 * mp_elbow + 0.6 * g_elbow)
    follow_score = g_follow          # purely vision-based
    release_score = g_release        # purely vision-based
    stance_score = int(0.4 * mp_stance + 0.6 * g_stance)

    # Extract per-category feedback from the final Gemini text
    elbow_fb = extract_section_feedback(final_text, "Upper Body Mechanics")
    follow_fb = extract_section_feedback(final_text, "Timing and Coordination")
    release_fb = extract_section_feedback(final_text, "Visual and Spatial Factors")
    stance_fb = extract_section_feedback(final_text, "Lower Body Mechanics")

    categories = [
        {
            "name": "Elbow Angle",
            "score": elbow_score,
            "label": _get_label(elbow_score),
            "tip": _get_tip("Elbow Angle", elbow_score),
            "feedback": elbow_fb,
        },
        {
            "name": "Follow-Through",
            "score": follow_score,
            "label": _get_label(follow_score),
            "tip": _get_tip("Follow-Through", follow_score),
            "feedback": follow_fb,
        },
        {
            "name": "Release Point",
            "score": release_score,
            "label": _get_label(release_score),
            "tip": _get_tip("Release Point", release_score),
            "feedback": release_fb,
        },
        {
            "name": "Stance",
            "score": stance_score,
            "label": _get_label(stance_score),
            "tip": _get_tip("Stance", stance_score),
            "feedback": stance_fb,
        },
    ]

    overall = round(sum(c["score"] * WEIGHTS[c["name"]] for c in categories))

    clips_out = [
        {
            "clip_index": r["clip_index"],
            "time_range": r["time_range"],
            "metrics": r["metrics"],
            "feedback": r["feedback"],
        }
        for r in clip_results
    ]

    return {
        "overallScore": overall,
        "overallLabel": _get_label(overall),
        "categories": categories,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputType": input_type,
        "coachSummary": coach_summary or None,
        "clips": clips_out,
    }
