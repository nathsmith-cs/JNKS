"""FastAPI server with WebSocket for real-time shot analysis.

Phone records 3-second video chunks via MediaRecorder and sends them
over WebSocket. Server processes each chunk with OpenCV (same quality
as uploaded videos). State persists across chunks.
"""

import asyncio
import base64
import json
import os
import tempfile
import time

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pipeline.tracker import PoseTracker, LANDMARK_NAMES
from pipeline.detector import BallDetector, BallTracker
from pipeline.phases import detect_phases, compute_angle_sequence
from pipeline.compare import find_best_match
from pipeline.llm import analyze_shot_with_gemini, distill_advice, text_to_speech
from pipeline.voice import create_live_session, send_audio, receive_audio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FOLLOW_THROUGH_FRAMES = 15
SHOT_MIN_FRAMES = 20
MIN_SHOT_FRAMES = 30
BALL_LOST_GRACE = 5
SHOTS_PER_BATCH = 5

REF_DIR = os.path.join(os.path.dirname(__file__), "reference")

_tracker = None
_ball_detector = None


def _get_models():
    global _tracker, _ball_detector
    if _tracker is None:
        _tracker = PoseTracker()
        _ball_detector = BallDetector()
    return _tracker, _ball_detector


def _is_shot_motion(landmark_buffer):
    valid = [lm for lm in landmark_buffer if lm is not None]
    if len(valid) < 6:
        return False
    early = valid[:len(valid) // 3]
    late = valid[2 * len(valid) // 3:]
    for side in ["left", "right"]:
        wrist_key = f"{side}_wrist"
        shoulder_key = f"{side}_shoulder"
        early_wrists = [lm[wrist_key]["y"] for lm in early if wrist_key in lm and lm[wrist_key]["visibility"] > 0.2]
        late_wrists = [lm[wrist_key]["y"] for lm in late if wrist_key in lm and lm[wrist_key]["visibility"] > 0.2]
        shoulders = [lm[shoulder_key]["y"] for lm in valid if shoulder_key in lm and lm[shoulder_key]["visibility"] > 0.2]
        if not early_wrists or not late_wrists or not shoulders:
            continue
        avg_early = sum(early_wrists) / len(early_wrists)
        avg_late = sum(late_wrists) / len(late_wrists)
        avg_shoulder = sum(shoulders) / len(shoulders)
        if (avg_early - avg_late) > 0.05 and avg_late < avg_shoulder + 0.05:
            return True
    return False


def _get_label(score):
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Needs Work"
    return "Poor"


TIPS = {
    "Elbow Angle": {
        "Excellent": "Great elbow alignment — maintain that L-shape on every shot.",
        "Good": "Your elbow is close — focus on keeping it tucked under the ball.",
        "Needs Work": "Keep your elbow at 90 degrees at the set point for a consistent release.",
        "Poor": "Your elbow is drifting outward significantly — tuck it under the ball.",
    },
    "Follow-Through": {
        "Excellent": "Solid follow-through — keep that relaxed wrist flick.",
        "Good": "Good follow-through — try holding it a beat longer.",
        "Needs Work": "Your follow-through is cutting short — snap the wrist and freeze.",
        "Poor": "Extend your wrist fully and hold — reach into the cookie jar.",
    },
    "Release Point": {
        "Excellent": "Great timing on the release — that high arc gives you a shooter's touch.",
        "Good": "Good release timing — aim to release just a hair higher.",
        "Needs Work": "You're releasing too early — wait until you reach the top.",
        "Poor": "Release at the peak of your jump for maximum arc.",
    },
    "Stance": {
        "Excellent": "Strong foundation — your lower body is set up well for power.",
        "Good": "Good base — keep feet shoulder-width apart consistently.",
        "Needs Work": "Widen your base a bit — you're losing balance on the release.",
        "Poor": "Feet shoulder-width apart with your shooting foot slightly ahead.",
    },
}

PHASE_TO_CATEGORY = {
    "set_point": "Elbow Angle",
    "follow_through": "Follow-Through",
    "release": "Release Point",
    "gather": "Stance",
}

WEIGHTS = {"Elbow Angle": 0.3, "Follow-Through": 0.25, "Release Point": 0.25, "Stance": 0.2}


def _analyze_shot(landmark_buffer, ref_path):
    phases = detect_phases(landmark_buffer)
    angles = compute_angle_sequence(landmark_buffer)
    result = {"frames": len(landmark_buffer), "phases": phases}
    if ref_path:
        match = find_best_match(landmark_buffer, ref_path)
        if match:
            result["comparison"] = {
                "best_ref": match["best_ref"],
                "score": match["best_score"],
                "phase_scores": match["analysis"]["phase_scores"],
                "angle_diffs": match["analysis"]["angle_diffs"],
            }
    return result


def _batch_report(shot_analyses):
    phase_totals = {}
    phase_counts = {}
    angle_diffs_totals = {}
    angle_diffs_counts = {}

    for shot in shot_analyses:
        comp = shot.get("comparison")
        if not comp:
            continue
        for phase, score in comp["phase_scores"].items():
            phase_totals[phase] = phase_totals.get(phase, 0) + score
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        for angle, diff in comp.get("angle_diffs", {}).items():
            angle_diffs_totals[angle] = angle_diffs_totals.get(angle, 0) + diff
            angle_diffs_counts[angle] = angle_diffs_counts.get(angle, 0) + 1

    categories = []
    for phase_key, cat_name in PHASE_TO_CATEGORY.items():
        if phase_key in phase_totals:
            score = round(phase_totals[phase_key] / phase_counts[phase_key], 1)
        else:
            score = 50.0
        label = _get_label(score)
        categories.append({"name": cat_name, "score": score, "label": label, "tip": TIPS[cat_name][label]})

    overall = round(sum(c["score"] * WEIGHTS[c["name"]] for c in categories), 1)

    worst_angles = sorted(angle_diffs_totals.items(),
                          key=lambda x: x[1] / angle_diffs_counts[x[0]], reverse=True)
    worst_joints = [{"joint": k, "avg_diff_degrees": round(v / angle_diffs_counts[k], 1)}
                    for k, v in worst_angles[:5]]

    shot_comparisons = []
    for i, shot in enumerate(shot_analyses):
        comp = shot.get("comparison")
        if comp:
            shot_comparisons.append({
                "shot": i + 1, "best_ref": comp["best_ref"],
                "score": comp["score"], "phase_scores": comp["phase_scores"],
            })

    return {
        "overallScore": overall, "overallLabel": _get_label(overall),
        "categories": categories, "worstJoints": worst_joints,
        "shotComparisons": shot_comparisons,
        "shotCount": len(shot_analyses), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def _process_frames(cap, tracker, ball_detector, state, ref_path, ws_events):
    """Process all frames in a VideoCapture. Mutates state dict. Appends events to ws_events."""
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        state["chunk_frames"] += 1
        h, w = frame.shape[:2]

        run_yolo = False
        if state["cooldown_skip"] > 0:
            state["cooldown_skip"] -= 1
            state["ball_boxes"] = []
        elif state["shot_cooldown"] > 0:
            state["ball_boxes"] = []
        elif state["confirm_frames"] > 0:
            run_yolo = True
            state["confirm_frames"] -= 1
        elif state["shot_frames"] > 0 and state["frame_number"] % 5 == 0:
            run_yolo = True
        else:
            run_yolo = True  # Run every frame when scanning

        need_pose = bool(state["ball_boxes"]) or state["shot_cooldown"] > 0

        if run_yolo:
            state["ball_boxes"] = ball_detector.detect(frame)
            if not need_pose and state["ball_boxes"]:
                state["confirm_frames"] = 3
        if need_pose or state["ball_boxes"]:
            landmarks = tracker.process(frame)
        else:
            landmarks = None

        ball_info = state["ball_tracker"].update(landmarks, state["ball_boxes"], w, h)

        if ball_info["has_ball"]:
            state["shot_frames"] += 1
            state["shot_cooldown"] = 0
            state["ball_lost"] = 0
        elif state["shot_frames"] > 0:
            state["ball_lost"] += 1
            if state["ball_lost"] <= BALL_LOST_GRACE:
                state["confirm_frames"] = max(state["confirm_frames"], 1)
            else:
                if state["shot_frames"] >= SHOT_MIN_FRAMES:
                    state["shot_cooldown"] = FOLLOW_THROUGH_FRAMES
                state["shot_frames"] = 0
                state["ball_lost"] = 0

        tracking = ball_info["has_ball"] or state["shot_frames"] > 0 or state["shot_cooldown"] > 0

        if tracking:
            state["landmarks"].append(landmarks)
            state["shot_frame_buf"].append(frame.copy())

        if not tracking and state["landmarks"]:
            print(f"\nShot ended: {len(state['landmarks'])} landmarks, {len(state['shot_frame_buf'])} frames")
            if len(state["landmarks"]) >= MIN_SHOT_FRAMES:
                # Save debug shot
                debug_dir = os.path.join(os.path.dirname(__file__), "debug_shots")
                os.makedirs(debug_dir, exist_ok=True)
                shot_path = os.path.join(debug_dir, f"shot_{time.strftime('%H-%M-%S')}.mp4")
                if state["shot_frame_buf"]:
                    sh, sw = state["shot_frame_buf"][0].shape[:2]
                    vw = cv2.VideoWriter(shot_path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (sw, sh))
                    for sf in state["shot_frame_buf"]:
                        vw.write(sf)
                    vw.release()
                    print(f"\nSaved debug shot: {shot_path} ({len(state['shot_frame_buf'])} frames)")

                analysis = _analyze_shot(state["landmarks"], ref_path)
                state["batch_shots"].append(analysis)
                ws_events.append(("shot", analysis))

            state["landmarks"] = []
            state["shot_frame_buf"] = []

        if state["shot_cooldown"] > 0:
            state["shot_cooldown"] -= 1
            if state["shot_cooldown"] == 0:
                state["cooldown_skip"] = 90

        state["frame_number"] += 1


@app.websocket("/ws/analyze")
async def ws_analyze(ws: WebSocket):
    """Receive video chunks from MediaRecorder, process with OpenCV."""
    await ws.accept()

    ref_path = os.path.join(REF_DIR, "StephCurryShots")
    tracker, ball_detector = _get_models()

    state = {
        "frame_number": 0, "shot_frames": 0, "shot_cooldown": 0,
        "ball_boxes": [], "confirm_frames": 0, "cooldown_skip": 0,
        "ball_lost": 0, "landmarks": [], "shot_frame_buf": [],
        "batch_shots": [], "ball_tracker": BallTracker(),
        "chunk_frames": 0,
    }
    shot_advices = []
    chunk_count = 0

    try:
        while True:
            data = await ws.receive_bytes()
            chunk_count += 1
            state["chunk_frames"] = 0

            # Write chunk to temp file — OpenCV needs a file path
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            cap = cv2.VideoCapture(tmp_path)
            ws_events = []

            _process_frames(cap, tracker, ball_detector, state, ref_path, ws_events)

            cap.release()
            os.unlink(tmp_path)

            # Send events for any shots detected in this chunk
            for event_type, analysis in ws_events:
                score = analysis.get("comparison", {}).get("score", 0)
                ref = analysis.get("comparison", {}).get("best_ref", "unknown")
                comp = analysis.get("comparison")

                gemini_advice = await analyze_shot_with_gemini(state["landmarks"] or [], comp)
                shot_advices.append(gemini_advice)

                await ws.send_json({
                    "type": "shot_detected",
                    "shot_number": len(state["batch_shots"]),
                    "score": score, "best_ref": ref, "advice": gemini_advice,
                    "shots_in_batch": len(state["batch_shots"]),
                    "shots_needed": SHOTS_PER_BATCH,
                })

                if len(state["batch_shots"]) >= SHOTS_PER_BATCH:
                    report = _batch_report(state["batch_shots"])
                    coaching = await distill_advice(shot_advices, report)
                    report["coaching"] = coaching

                    audio_b64 = await text_to_speech(coaching)
                    if audio_b64:
                        report["audio"] = audio_b64

                    results_path = os.path.join(os.path.dirname(__file__), "latest_results.json")
                    with open(results_path, "w") as f:
                        debug_report = {k: v for k, v in report.items() if k != "audio"}
                        json.dump(debug_report, f, indent=2)

                    global _latest_report
                    _latest_report = report

                    await ws.send_json({"type": "batch_complete", "result": report})
                    state["batch_shots"] = []
                    shot_advices = []

            print(f"\rchunk={chunk_count} frames={state['chunk_frames']} total={state['frame_number']} sf={state['shot_frames']} shots={len(state['batch_shots'])}    ", end="", flush=True)

            await ws.send_json({
                "type": "status",
                "frame": state["frame_number"],
                "tracking": state["shot_frames"] > 0 or state["shot_cooldown"] > 0,
                "shots_in_batch": len(state["batch_shots"]),
            })

    except WebSocketDisconnect:
        pass
    finally:
        if state["landmarks"] and len(state["landmarks"]) >= MIN_SHOT_FRAMES:
            analysis = _analyze_shot(state["landmarks"], ref_path)
            state["batch_shots"].append(analysis)
        if state["batch_shots"]:
            report = _batch_report(state["batch_shots"])
            results_path = os.path.join(os.path.dirname(__file__), "latest_results.json")
            with open(results_path, "w") as f:
                json.dump(report, f, indent=2)


# Store latest batch report for voice coach context
_latest_report = {}


@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket):
    await ws.accept()
    gemini_ws = await create_live_session(_latest_report)
    if not gemini_ws:
        await ws.send_json({"type": "error", "message": "Voice coach unavailable"})
        await ws.close()
        return
    await ws.send_json({"type": "ready"})

    async def forward_responses():
        try:
            while True:
                chunks = await receive_audio(gemini_ws)
                if chunks:
                    for chunk in chunks:
                        await ws.send_json({"type": "audio", "data": chunk})
                await asyncio.sleep(0.05)
        except Exception:
            pass

    response_task = asyncio.create_task(forward_responses())
    try:
        while True:
            data = await ws.receive()
            if "bytes" in data:
                pcm_b64 = base64.b64encode(data["bytes"]).decode("utf-8")
                await send_audio(gemini_ws, pcm_b64)
            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "end":
                    break
    except WebSocketDisconnect:
        pass
    finally:
        response_task.cancel()
        await gemini_ws.close()


@app.post("/api/analyze")
async def analyze_upload(
    video: UploadFile = File(...),
    reference: str = Query(default="StephCurryShots"),
):
    ref_path = os.path.join(REF_DIR, reference)
    if not os.path.isdir(ref_path):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"error": f"Reference '{reference}' not found"})

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(await video.read())
        tmp_path = tmp.name

    try:
        tracker, ball_detector = _get_models()
        state = {
            "frame_number": 0, "shot_frames": 0, "shot_cooldown": 0,
            "ball_boxes": [], "confirm_frames": 0, "cooldown_skip": 0,
            "ball_lost": 0, "landmarks": [], "shot_frame_buf": [],
            "batch_shots": [], "ball_tracker": BallTracker(),
            "chunk_frames": 0,
        }
        shot_advices = []

        cap = cv2.VideoCapture(tmp_path)
        ws_events = []
        _process_frames(cap, tracker, ball_detector, state, ref_path, ws_events)
        cap.release()

        # Flush remaining
        if state["landmarks"] and len(state["landmarks"]) >= MIN_SHOT_FRAMES:
            analysis = _analyze_shot(state["landmarks"], ref_path)
            state["batch_shots"].append(analysis)

        for shot in state["batch_shots"]:
            comp = shot.get("comparison")
            advice = await analyze_shot_with_gemini([], comp)
            shot_advices.append(advice)

        report = _batch_report(state["batch_shots"])
        coaching = await distill_advice(shot_advices, report)
        report["coaching"] = coaching

        global _latest_report
        _latest_report = report

        results_path = os.path.join(os.path.dirname(__file__), "latest_results.json")
        with open(results_path, "w") as f:
            json.dump(report, f, indent=2)

        return report
    finally:
        os.unlink(tmp_path)


@app.get("/api/references")
async def list_references():
    refs = []
    if os.path.isdir(REF_DIR):
        for name in sorted(os.listdir(REF_DIR)):
            path = os.path.join(REF_DIR, name)
            if os.path.isdir(path):
                count = len([f for f in os.listdir(path) if f.endswith(".json")])
                refs.append({"name": name, "shots": count})
    return refs


# Serve Next.js static export pages
_out_dir = os.path.join(os.path.dirname(__file__), "..", "out")
if os.path.isdir(_out_dir):
    from fastapi.responses import FileResponse

    @app.get("/analyze")
    async def serve_analyze():
        return FileResponse(os.path.join(_out_dir, "analyze.html"))

    @app.get("/results")
    async def serve_results():
        return FileResponse(os.path.join(_out_dir, "results.html"))

    # Catch-all for static assets (_next/, images, etc.)
    app.mount("/", StaticFiles(directory=_out_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
