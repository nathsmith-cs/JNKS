"""Voice coach via Gemini Live API.

Proxies audio between the frontend and Gemini Live WebSocket,
with shot analysis data as system context.
"""

import asyncio
import base64
import json
import os

import websockets

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LIVE_MODEL = "gemini-3.1-flash-live-preview"
GEMINI_WS = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
    f"?key={GEMINI_API_KEY}"
)


def _build_system_prompt(batch_report):
    """Build system instruction from the latest shot analysis."""
    if not batch_report:
        return "You are a basketball shooting coach. Help the player improve their form."

    overall = batch_report.get("overallScore", 0)
    categories = batch_report.get("categories", [])
    worst_joints = batch_report.get("worstJoints", [])
    coaching = batch_report.get("coaching", "")

    return f"""You are a basketball shooting coach having a real-time conversation with a player on the court.
They just took 5 shots. Here's their analysis:

Overall similarity to Steph Curry's form: {overall}%

Category scores:
{json.dumps(categories, indent=2)}

Joints most off from reference:
{json.dumps(worst_joints, indent=2)}

Summary coaching advice already given: {coaching}

Answer their follow-up questions about their form. Be concise — they're on a court, not reading an essay.
Reference their actual scores and specific body parts. If they describe a position ("like this?"),
relate it back to the angles and phases you know about.
Keep responses under 3 sentences."""


async def create_live_session(batch_report):
    """Create a Gemini Live WebSocket session with shot context.

    Returns the websocket connection, or None if not available.
    """
    if not GEMINI_API_KEY:
        return None

    try:
        ws = await websockets.connect(GEMINI_WS)
        config = {
            "config": {
                "model": f"models/{LIVE_MODEL}",
                "responseModalities": ["AUDIO"],
                "systemInstruction": {
                    "parts": [{"text": _build_system_prompt(batch_report)}]
                },
            }
        }
        await ws.send(json.dumps(config))
        # Wait for setup complete
        setup_resp = await asyncio.wait_for(ws.recv(), timeout=5)
        return ws
    except Exception as e:
        print(f"Gemini Live connect error: {e}")
        return None


async def send_audio(gemini_ws, pcm_b64):
    """Send a chunk of audio to Gemini Live."""
    msg = {
        "realtimeInput": {
            "audio": {
                "data": pcm_b64,
                "mimeType": "audio/pcm;rate=16000",
            }
        }
    }
    await gemini_ws.send(json.dumps(msg))


async def receive_audio(gemini_ws):
    """Receive next message from Gemini Live. Returns audio b64 chunks or None."""
    try:
        raw = await asyncio.wait_for(gemini_ws.recv(), timeout=0.1)
        resp = json.loads(raw)
        if "serverContent" in resp:
            sc = resp["serverContent"]
            if "modelTurn" in sc and "parts" in sc["modelTurn"]:
                chunks = []
                for part in sc["modelTurn"]["parts"]:
                    if "inlineData" in part:
                        chunks.append(part["inlineData"]["data"])
                return chunks
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        print(f"Gemini Live recv error: {e}")
    return None
