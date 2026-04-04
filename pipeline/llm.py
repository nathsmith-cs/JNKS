"""LLM integration for shot coaching. All Gemini."""

import base64
import json
import os
import httpx

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
ANALYSIS_MODEL = "gemini-3.1-pro"              # best quality for per-shot analysis
DISTILL_MODEL = "gemini-3.1-flash-lite"        # cheapest, just combining existing advice
TTS_MODEL = "gemini-2.5-flash-preview-tts"     # low-latency text-to-speech


async def _call_gemini(prompt, model=DISTILL_MODEL, max_tokens=200):
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


async def distill_advice(shot_advices, batch_report):
    """Distill 5 shot advices + scores into 2 sentences."""
    overall = batch_report.get("overallScore", 0)
    categories = batch_report.get("categories", [])
    worst_joints = batch_report.get("worstJoints", [])

    prompt = f"""You are a basketball shooting coach. A player just took 5 shots.
Their overall similarity to Steph Curry's form: {overall}%.

Category scores:
{json.dumps(categories, indent=2)}

Most off joints:
{json.dumps(worst_joints, indent=2)}

Individual shot feedback from video analysis:
{chr(10).join(f"Shot {i+1}: {a}" for i, a in enumerate(shot_advices) if a)}

Based on ALL of this data, give exactly 2 sentences of coaching advice.
Focus on the single most impactful change they can make right now.
Be specific and actionable — reference the actual body part and what to change."""

    result = await _call_gemini(prompt, max_tokens=150)
    if result:
        return result
    return _fallback_advice(batch_report)


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
