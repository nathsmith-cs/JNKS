"""FastAPI server with WebSocket for real-time shot analysis.

Phone streams frames over WebSocket, server runs the pipeline,
pushes back results when a batch of 5 shots is complete.
"""

import asyncio
import base64
import json
import os
import time

import cv2
import numpy as np
import tempfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware

from pipeline.tracker import PoseTracker, LANDMARK_NAMES
from pipeline.detector import BallDetector, BallTracker
from pipeline.phases import detect_phases, compute_angle_sequence
from pipeline.compare import find_best_match
from pipeline.llm import analyze_shot_with_gemini, distill_advice, text_to_speech
from pipeline.voice import create_live_session, send_audio, receive_audio
from pipeline.video import convert_video, split_video
from pipeline.pose_extract import extract_keypoints, keypoints_to_named
from pipeline.gemini_vision import analyze_clip_with_gemini, build_final_analysis
from pipeline.scoring import (
    compute_clip_metrics,
    summarize_session_metrics,
    build_analysis_result,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FOLLOW_THROUGH_FRAMES = 15
SHOT_MIN_FRAMES = 20
MIN_SHOT_FRAMES = 45
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
    """Analyze a single shot and return comparison data."""
    phases = detect_phases(landmark_buffer)
    angles = compute_angle_sequence(landmark_buffer)
    result = {
        "frames": len(landmark_buffer),
        "phases": phases,
    }
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
    """Build the frontend-compatible result from a batch of shot analyses."""
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
        categories.append({
            "name": cat_name,
            "score": score,
            "label": label,
            "tip": TIPS[cat_name][label],
        })

    overall = round(sum(c["score"] * WEIGHTS[c["name"]] for c in categories), 1)

    worst_angles = sorted(angle_diffs_totals.items(),
                          key=lambda x: x[1] / angle_diffs_counts[x[0]],
                          reverse=True)
    worst_joints = [{"joint": k, "avg_diff_degrees": round(v / angle_diffs_counts[k], 1)}
                    for k, v in worst_angles[:5]]

    return {
        "overallScore": overall,
        "overallLabel": _get_label(overall),
        "categories": categories,
        "worstJoints": worst_joints,
        "shotCount": len(shot_analyses),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


async def _finalize_batch(ws: WebSocket, batch_shots, shot_advices):
    """Build batch report, distill coaching, generate TTS, and send to client."""
    report = _batch_report(batch_shots)

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

    try:
        await ws.send_json({
            "type": "batch_complete",
            "result": report,
        })
    except Exception:
        pass


@app.websocket("/ws/analyze")
async def ws_analyze(ws: WebSocket):
    await ws.accept()

    ref_name = "StephCurryShots"
    ref_path = os.path.join(REF_DIR, ref_name)

    tracker, ball_detector = _get_models()
    ball_tracker = BallTracker()

    frame_number = 0
    shot_frames_count = 0
    shot_cooldown = 0
    ball_boxes = []
    confirm_frames = 0
    cooldown_skip = 0
    ball_lost_frames = 0

    shot_buffer = []
    landmark_buffer = []
    batch_shots = []
    shot_advices = []
    batch_finalizing = False  # guard against double-finalization

    try:
        # Wait for config message (optional)
        # Client can send {"type": "config", "reference": "KevinDurantShots"}

        while True:
            data = await ws.receive_bytes()

            # Decode JPEG frame from client
            arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            h, w = frame.shape[:2]

            # Detection logic (same as process.py)
            run_yolo = False
            if cooldown_skip > 0:
                cooldown_skip -= 1
                ball_boxes = []
            elif shot_cooldown > 0:
                ball_boxes = []
            elif confirm_frames > 0:
                run_yolo = True
                confirm_frames -= 1
            elif shot_frames_count > 0 and frame_number % 10 == 0:
                run_yolo = True
            elif shot_frames_count == 0 and frame_number % 5 == 0:
                run_yolo = True

            need_pose = bool(ball_boxes) or shot_cooldown > 0

            if run_yolo:
                ball_boxes = ball_detector.detect(frame)
                if not need_pose and ball_boxes:
                    confirm_frames = 3
            if need_pose or ball_boxes:
                landmarks = tracker.process(frame)
            else:
                landmarks = None

            ball_info = ball_tracker.update(landmarks, ball_boxes, w, h)

            if ball_info["has_ball"]:
                shot_frames_count += 1
                shot_cooldown = 0
                ball_lost_frames = 0
            elif shot_frames_count > 0:
                ball_lost_frames += 1
                if ball_lost_frames <= BALL_LOST_GRACE:
                    confirm_frames = max(confirm_frames, 1)
                else:
                    if shot_frames_count >= SHOT_MIN_FRAMES:
                        shot_cooldown = FOLLOW_THROUGH_FRAMES
                    shot_frames_count = 0
                    ball_lost_frames = 0

            tracking = ball_info["has_ball"] or shot_frames_count > 0 or shot_cooldown > 0

            if tracking:
                landmark_buffer.append(landmarks)

            if not tracking and landmark_buffer:
                # Shot ended — analyze if valid
                if len(landmark_buffer) >= MIN_SHOT_FRAMES and _is_shot_motion(landmark_buffer):
                    analysis = _analyze_shot(landmark_buffer, ref_path)
                    batch_shots.append(analysis)

                    score = analysis.get("comparison", {}).get("score", 0)
                    ref = analysis.get("comparison", {}).get("best_ref", "unknown")
                    comp = analysis.get("comparison")

                    # Send shot detected event immediately (don't wait for Gemini)
                    shot_number = len(batch_shots)
                    await ws.send_json({
                        "type": "shot_detected",
                        "shot_number": shot_number,
                        "score": score,
                        "best_ref": ref,
                        "advice": None,
                        "shots_in_batch": shot_number,
                        "shots_needed": SHOTS_PER_BATCH,
                    })

                    # O8: Fire-and-forget Gemini advice so the frame loop
                    # keeps processing while LLM responds (~3-5s).
                    async def _get_advice_and_maybe_batch(
                        lm_buf, comp_data, shot_num,
                    ):
                        nonlocal batch_finalizing
                        gemini_advice = await analyze_shot_with_gemini(lm_buf, comp_data)
                        shot_advices.append(gemini_advice)

                        # Send advice as a follow-up message
                        try:
                            await ws.send_json({
                                "type": "shot_advice",
                                "shot_number": shot_num,
                                "advice": gemini_advice,
                            })
                        except Exception:
                            pass

                        # Check if batch is now complete (guard against double-finalize)
                        if (
                            not batch_finalizing
                            and len(batch_shots) >= SHOTS_PER_BATCH
                            and len(shot_advices) >= SHOTS_PER_BATCH
                        ):
                            batch_finalizing = True
                            await _finalize_batch(ws, batch_shots, shot_advices)
                            batch_shots.clear()
                            shot_advices.clear()
                            batch_finalizing = False

                    asyncio.create_task(
                        _get_advice_and_maybe_batch(landmark_buffer, comp, shot_number)
                    )

                landmark_buffer = []

            if shot_cooldown > 0:
                shot_cooldown -= 1
                if shot_cooldown == 0:
                    cooldown_skip = 90

            # Send status every 30 frames
            if frame_number % 30 == 0:
                await ws.send_json({
                    "type": "status",
                    "frame": frame_number,
                    "tracking": tracking,
                    "shots_in_batch": len(batch_shots),
                })

            frame_number += 1

    except WebSocketDisconnect:
        pass
    finally:
        tracker.close()
        # Analyze any remaining shot
        if landmark_buffer and len(landmark_buffer) >= MIN_SHOT_FRAMES and _is_shot_motion(landmark_buffer):
            analysis = _analyze_shot(landmark_buffer, ref_path)
            batch_shots.append(analysis)
        if batch_shots:
            report = _batch_report(batch_shots)
            results_path = os.path.join(os.path.dirname(__file__), "latest_results.json")
            with open(results_path, "w") as f:
                json.dump(report, f, indent=2)


# Store latest batch report for voice coach context
_latest_report = {}


@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket):
    """Voice coach WebSocket. Frontend sends audio only when voice is detected.

    Protocol:
    - Client sends: raw bytes (PCM 16-bit 16kHz) when voice detected
    - Client sends: JSON {"type": "end"} to close
    - Server sends: JSON {"type": "audio", "data": "<base64 pcm 24kHz>"}
    - Server sends: JSON {"type": "ready"} when Gemini session is up
    """
    await ws.accept()

    gemini_ws = await create_live_session(_latest_report)
    if not gemini_ws:
        await ws.send_json({"type": "error", "message": "Voice coach unavailable (no API key or connection failed)"})
        await ws.close()
        return

    await ws.send_json({"type": "ready"})

    async def forward_responses():
        """Forward Gemini audio responses back to the client."""
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
                # Raw PCM audio from client — forward to Gemini
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


def _process_single_clip(idx: int, clip: str, max_clip_sec: int) -> dict:
    """Process a single clip: pose extraction + metrics + Gemini vision.

    This runs in a thread so multiple clips can be processed concurrently.
    """
    frames = extract_keypoints(clip)
    metrics = compute_clip_metrics(frames)
    feedback = analyze_clip_with_gemini(clip, metrics)

    start_sec = idx * max_clip_sec
    end_sec = start_sec + max_clip_sec
    return {
        "clip_index": idx,
        "clip_path": clip,
        "time_range": f"{start_sec:.1f}s-{end_sec:.1f}s",
        "metrics": metrics,
        "feedback": feedback,
        "raw_keypoints": frames,  # kept for reference comparison (O5)
    }


@app.post("/api/analyze")
async def analyze_upload(
    video: UploadFile = File(...),
    reference: str = Query(default="StephCurryShots"),
    input_type: str = Query(default="upload"),
):
    """Upload a video file for analysis.

    Uses Gemini vision analysis with hybrid scoring:
    - Video is converted to mp4, split into clips
    - Each clip gets MediaPipe pose extraction + Gemini vision analysis
    - Final scores blend 40% MediaPipe metrics with 60% Gemini vision scores

    Optimizations applied:
    - O1: Clips processed in parallel via asyncio.to_thread
    - O2: ffmpeg splits launched concurrently
    - O5: Reuses pose keypoints for reference comparison (no second video pass)
    - O7: Smart remux for H.264 inputs
    """
    suffix = os.path.splitext(video.filename or "video.mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await video.read())
        tmp_path = tmp.name

    try:
        # Stage 2+3: convert → split (splits run concurrently via Popen)
        video_path = convert_video(tmp_path)
        clips = split_video(video_path)
        max_clip_sec = 5

        # Stage 4+5 (O1): Process all clips in parallel threads.
        # Each thread does pose extraction + Gemini vision independently.
        clip_futures = [
            asyncio.to_thread(_process_single_clip, idx, clip, max_clip_sec)
            for idx, clip in enumerate(clips)
        ]
        clip_results: list[dict] = list(await asyncio.gather(*clip_futures))

        # Sort by clip_index (gather preserves order, but be explicit)
        clip_results.sort(key=lambda r: r["clip_index"])

        # Stage 6+7: Final analysis and scoring
        session_metrics = summarize_session_metrics(clip_results)
        final_text = await asyncio.to_thread(
            build_final_analysis, clip_results, session_metrics
        )
        result = build_analysis_result(final_text, session_metrics, clip_results, input_type)

        # O5: Reference comparison using already-extracted keypoints
        # (no second video pass — convert index-based keypoints to named dicts)
        ref_path = os.path.join(REF_DIR, reference)
        if os.path.isdir(ref_path):
            all_named_landmarks: list[dict | None] = []
            for cr in clip_results:
                all_named_landmarks.extend(keypoints_to_named(cr["raw_keypoints"]))

            valid_landmarks = [lm for lm in all_named_landmarks if lm is not None]
            if valid_landmarks:
                match = find_best_match(valid_landmarks, ref_path)
                if match:
                    angle_diffs = match["analysis"].get("angle_diffs", {})
                    worst_angles = sorted(
                        angle_diffs.items(), key=lambda x: x[1], reverse=True
                    )
                    result["worstJoints"] = [
                        {"joint": k, "avg_diff_degrees": round(v, 1)}
                        for k, v in worst_angles[:5]
                    ]

        # Strip raw_keypoints from the response (internal use only)
        for cr in clip_results:
            cr.pop("raw_keypoints", None)

        # Stage 9: Distill coaching advice
        coaching = await distill_advice(
            [r["feedback"] for r in clip_results],
            result,
        )
        if coaching:
            result["coaching"] = coaching

        global _latest_report
        _latest_report = result

        results_path = os.path.join(os.path.dirname(__file__), "latest_results.json")
        with open(results_path, "w") as f:
            debug_report = {k: v for k, v in result.items() if k != "audio"}
            json.dump(debug_report, f, indent=2)

        return result

    except FileNotFoundError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"error": str(e)})
    except ValueError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"error": str(e)})
    finally:
        if os.path.exists(tmp_path):
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
