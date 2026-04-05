"""Gemini vision analysis — uploads video clips for AI coaching feedback.

Uses the google-genai SDK to send actual video to Gemini for visual analysis,
producing structured coaching feedback and numeric scores.
"""

import json
import mimetypes
import os
import re
import time

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Detailed coaching rubric for Gemini analysis
ANALYSIS_CATEGORIES = {
    "upper_body": {
        "title": "Upper Body Mechanics",
        "items": [
            "Elbow alignment: ideal about 90 degrees at release and aligned with the shooting shoulder",
            "Shoulder rotation: shoulders squared versus open toward the basket",
            "Wrist and finger position: follow-through, flick, and likely backspin generation",
            "Arm extension: full follow-through versus cutting the motion short",
            "Hand placement: ball on fingertips versus resting too much on the palm",
        ],
    },
    "lower_body": {
        "title": "Lower Body Mechanics",
        "items": [
            "Knee bend: about 110 to 130 degrees at jump initiation",
            "Hip flexion: use of legs and core for power generation",
            "Foot placement: shoulder-width stance with toes aligned to target",
            "Balance: even weight distribution before jump",
            "Jump mechanics: smooth vertical motion without leaning or twisting",
        ],
    },
    "timing_coordination": {
        "title": "Timing and Coordination",
        "items": [
            "Leg-to-arm transfer: synchronized flow from legs to core to arms",
            "Release timing: release around the peak of the jump",
            "Shot rhythm: repeatable pre-shot routine and smooth motion",
            "Recovery and follow-through timing: readiness for the next move or rebound",
        ],
    },
    "visual_spatial": {
        "title": "Visual and Spatial Factors",
        "items": [
            "Head position: eyes on target instead of the ball",
            "Tracking consistency: stable line of sight to the basket",
            "Body orientation: torso facing the basket without over-rotation",
            "Shot arc: ideal 45 to 55 degree trajectory if visible",
        ],
    },
    "common_issues": {
        "title": "Common Issues to Detect",
        "items": [
            "Arm flare or elbow drop",
            "Knees too shallow or overbent",
            "Early or late release",
            "Off-balance foot placement",
            "Poor follow-through such as wrist collapse",
        ],
    },
    "drills": {
        "title": "Drills and Corrections Suggestions",
        "items": [
            "Form shooting close to the basket",
            "Elbow and hand alignment drills",
            "Jump timing and leg strength exercises",
            "Repetition tracking and consistency drills",
        ],
    },
}


def _build_category_rubric() -> str:
    lines: list[str] = []
    for category in ANALYSIS_CATEGORIES.values():
        lines.append(f'{category["title"]}:')
        for item in category["items"]:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).strip()


def _get_client():
    """Lazily create the google-genai client."""
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def analyze_clip_with_gemini(video_path: str, metrics: dict) -> str:
    """Upload a clip to Gemini and get per-clip coaching feedback with scores.

    Returns the raw text response from Gemini.
    """
    if not GEMINI_API_KEY:
        return ""

    client = _get_client()
    mime_type = mimetypes.guess_type(video_path)[0] or "video/mp4"

    with open(video_path, "rb") as f:
        uploaded = client.files.upload(
            file=f,
            config={
                "display_name": os.path.basename(video_path),
                "mime_type": mime_type,
            },
        )

    # Wait for Gemini to finish processing the file (exponential backoff)
    state = getattr(uploaded.state, "value", uploaded.state)
    poll_wait = 0.5
    while state != "ACTIVE":
        if state == "FAILED":
            raise RuntimeError(f"Gemini file processing failed: {uploaded.error}")
        time.sleep(poll_wait)
        poll_wait = min(poll_wait * 1.5, 3.0)
        uploaded = client.files.get(name=uploaded.name)
        state = getattr(uploaded.state, "value", uploaded.state)

    rubric = _build_category_rubric()

    prompt = f"""You are an elite basketball shooting coach.

Metrics from pose analysis:
{metrics}

Analyze the player's form using both the video and metrics.

Evaluation rubric — cover each category:
{rubric}

For each category, provide strengths, issues, and corrections.
If something cannot be determined reliably from this clip, say so explicitly.

IMPORTANT: At the end, provide numeric scores (0-100) in a JSON block:
```json
{{
  "elbow_angle_score": <0-100>,
  "follow_through_score": <0-100>,
  "release_point_score": <0-100>,
  "stance_score": <0-100>
}}
```

Use this structure:
Clip Summary:
Upper Body Mechanics:
Strengths:
Issues:
Corrections:
Lower Body Mechanics:
Strengths:
Issues:
Corrections:
Timing and Coordination:
Strengths:
Issues:
Corrections:

Scores:
```json
{{...}}
```
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[uploaded, prompt],
    )
    return response.text or ""


def build_final_analysis(clip_results: list[dict], session_metrics: dict) -> str:
    """Build a unified final coaching report from all clips.

    Returns the raw text response from Gemini.
    """
    if not GEMINI_API_KEY:
        return ""

    client = _get_client()
    rubric = _build_category_rubric()

    clip_notes: list[str] = []
    for r in clip_results:
        clip_notes.append(
            f"Clip {r['clip_index'] + 1} ({r['time_range']})\n"
            f"Metrics: {r['metrics']}\n"
            f"Clip feedback:\n{r['feedback']}"
        )

    prompt = f"""You are an elite basketball shooting coach.

Create one unified final report for the full shooting session.

Evaluation rubric — cover each category:
{rubric}

Session-level metrics:
{session_metrics}

Per-clip observations:
{chr(10).join(clip_notes)}

Return one consolidated report with strengths, issues, and corrections for each category.

IMPORTANT: Provide a brief 2-3 sentence overall coach summary.

IMPORTANT: Provide final numeric scores (0-100) in a JSON block:
```json
{{
  "elbow_angle_score": <0-100>,
  "follow_through_score": <0-100>,
  "release_point_score": <0-100>,
  "stance_score": <0-100>
}}
```

Use this structure:
Overall Summary:
Upper Body Mechanics:
Strengths:
Issues:
Corrections:
Lower Body Mechanics:
Strengths:
Issues:
Corrections:
Timing and Coordination:
Strengths:
Issues:
Corrections:

Coach Summary:

Scores:
```json
{{...}}
```
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text or ""


def extract_gemini_scores(text: str) -> dict[str, int]:
    """Extract JSON scores block from Gemini response text."""
    pattern = r"```json\s*(\{[^`]+\})\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {}


def extract_coach_summary(text: str) -> str:
    """Extract the coach summary section from final analysis text."""
    match = re.search(
        r"Coach Summary:\s*\n(.*?)(?:\n\s*\n|\nScores:|\Z)",
        text,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return ""


def extract_section_feedback(text: str, section_name: str) -> dict:
    """Extract strengths/issues/corrections for a named section.

    Returns {"strengths": [...], "issues": [...], "corrections": [...]}.
    """
    pattern = (
        rf"{re.escape(section_name)}:.*?"
        r"Strengths:\s*\n(.*?)"
        r"Issues:\s*\n(.*?)"
        r"Corrections:\s*\n(.*?)"
        r"(?=\n[A-Z]|\Z)"
    )
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return {"strengths": [], "issues": [], "corrections": []}

    def parse_bullets(block: str) -> list[str]:
        lines = []
        for line in block.strip().split("\n"):
            line = line.strip().lstrip("- ").strip()
            if line and not line.endswith(":"):
                lines.append(line)
        return lines

    return {
        "strengths": parse_bullets(match.group(1)),
        "issues": parse_bullets(match.group(2)),
        "corrections": parse_bullets(match.group(3)),
    }
