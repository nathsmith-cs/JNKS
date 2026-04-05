"""LLM integration for shot coaching. All Gemini."""

import base64
import json
import os
import httpx

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
ANALYSIS_MODEL = "gemini-3.1-pro-preview"              # video analysis (paid tier)
DISTILL_MODEL = "gemini-2.5-flash"                     # distillation (fast/cheap)
TTS_MODEL = "gemini-2.5-flash-preview-tts"     # low-latency text-to-speech


async def _call_gemini(prompt, model=DISTILL_MODEL, max_tokens=500):
    """Call Gemini and return the text response."""
    if not GEMINI_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_BASE}/{model}:generateContent?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini ({model}) error: {e}")
    return None


async def analyze_shot_with_gemini(landmark_buffer, comparison_data):
    """Get coaching advice for a single shot using the pro model."""
    prompt = _build_shot_prompt(landmark_buffer, comparison_data)
    return await _call_gemini(prompt, model=ANALYSIS_MODEL)


async def distill_to_structured(shot_advices, batch_report):
    """Distill per-shot video advice into structured JSON scores + coaching."""

    prompt = f"""You are an encouraging basketball shooting coach. A player just took {len(shot_advices)} shots.

Here is what a video analysis AI observed for each shot:
{chr(10).join(f"Shot {i+1}: {a}" for i, a in enumerate(shot_advices) if a)}

Based on what was observed, return a JSON object with your assessment.
Score each category 0-100. Be encouraging — grade relative to recreational/amateur players, NOT NBA pros. A decent recreational player with good fundamentals should score 75-85. Only give below 60 if the form is truly broken.

For each category, write a SHORT tip (1 sentence max). Be specific and reference what was actually observed.

IMPORTANT: Keep ALL text fields SHORT. The entire JSON must be under 800 tokens.

Return ONLY valid JSON, no markdown, no explanation:
{{
  "overallScore": <number 0-100>,
  "overallLabel": "<Excellent|Good|Needs Work|Poor>",
  "coaching": "<2-3 sentences max. What they do well, then one thing to fix.>",
  "categories": [
    {{"name": "Elbow Angle", "score": <0-100>, "label": "<Excellent|Good|Needs Work|Poor>", "tip": "<specific advice based on what was seen>"}},
    {{"name": "Follow-Through", "score": <0-100>, "label": "<Excellent|Good|Needs Work|Poor>", "tip": "<specific advice>"}},
    {{"name": "Release Point", "score": <0-100>, "label": "<Excellent|Good|Needs Work|Poor>", "tip": "<specific advice>"}},
    {{"name": "Stance", "score": <0-100>, "label": "<Excellent|Good|Needs Work|Poor>", "tip": "<specific advice>"}}
  ]
}}

Use these label rules: 90+ = Excellent, 75-89 = Good, 60-74 = Needs Work, below 60 = Poor."""

    result = await _call_gemini(prompt, max_tokens=4096)
    if result:
        try:
            # Strip markdown fences if present
            text = result.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()
            parsed = json.loads(text)
            # Validate required fields
            if "overallScore" in parsed and "categories" in parsed and "coaching" in parsed:
                return parsed
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Gemini JSON parse error: {e}, raw: {result[:200]}")
    return None


async def analyze_shot_video(video_path, comparison_data=None):
    """Send a single shot video clip to Gemini for visual coaching."""
    if not GEMINI_API_KEY or not video_path or not os.path.exists(video_path):
        return None

    score = comparison_data.get("score", 0) if comparison_data else 0
    phase_scores = comparison_data.get("phase_scores", {}) if comparison_data else {}
    worst_angles = comparison_data.get("angle_diffs", {}) if comparison_data else {}

    parts = [
        {"text": f"""You are an expert basketball shooting coach watching a player shoot a basketball.

Pose tracking comparison to a pro reference:
- Similarity: {score}%
- Phase scores: {json.dumps(phase_scores)}

Watch the video. Give exactly 2 sentences of coaching advice based on what you SEE.
Cover the FULL body — don't fixate on the elbow. Comment on stance, balance, release timing, follow-through, or whatever stands out most visually. Be specific and direct."""},
    ]

    with open(video_path, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode("utf-8")
    parts.append({"inline_data": {"mime_type": "video/mp4", "data": video_b64}})

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{GEMINI_BASE}/{ANALYSIS_MODEL}:generateContent?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": parts}],
                    "generationConfig": {"maxOutputTokens": 500, "temperature": 0.7},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                print(f"Gemini video error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"Gemini video error: {e}")
    return None


def _fallback_advice(batch_report):
    """Generate advice without LLM based on worst category."""
    categories = batch_report.get("categories", [])
    if not categories:
        return "Keep shooting and focus on consistent form."
    worst = min(categories, key=lambda c: c["score"])
    return f"{worst['tip']} Focus on your {worst['name'].lower()} — it's the area with the most room for improvement."


async def text_to_speech(text):
    """Convert text to speech using Gemini TTS. Returns base64-encoded WAV audio."""
    if not GEMINI_API_KEY or not text:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{GEMINI_BASE}/{TTS_MODEL}:generateContent",
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [{"parts": [{"text": f"Say in a confident coaching tone: {text}"}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": "Kore"
                                }
                            }
                        },
                    },
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                audio_b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                # Return raw PCM as base64 — frontend will decode and play
                return audio_b64
    except Exception as e:
        print(f"TTS error: {e}")
    return None


def _build_shot_prompt(landmark_buffer, comparison_data):
    """Build a text prompt describing the shot for Gemini."""
    if not comparison_data:
        return "Analyze this basketball shot and give one specific form tip."

    score = comparison_data.get("score", 0)
    phase_scores = comparison_data.get("phase_scores", {})
    angle_diffs = comparison_data.get("angle_diffs", {})
    best_ref = comparison_data.get("best_ref", "reference")

    worst_phase = min(phase_scores.items(), key=lambda x: x[1]) if phase_scores else ("unknown", 0)
    worst_angles = sorted(angle_diffs.items(), key=lambda x: x[1], reverse=True)[:3]

    return f"""Analyze this basketball shooting form compared to {best_ref}.
Overall similarity: {score}%.

Phase scores: {json.dumps(phase_scores)}
Worst phase: {worst_phase[0]} at {worst_phase[1]}%

Joints most different from reference (degrees off):
{chr(10).join(f"  {k}: {v:.1f} degrees off" for k, v in worst_angles)}

The shot had {len(landmark_buffer)} frames of tracking data.

Give ONE specific, actionable coaching tip for this shot in 1-2 sentences.
Focus on the weakest area. Be direct — say what body part to adjust and how."""
