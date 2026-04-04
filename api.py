import os
import random
import tempfile
from datetime import datetime, timezone

import cv2
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pipeline import PoseTracker

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Load the pose tracker once at startup so we don't reload the model on every request.
tracker = PoseTracker()

# ---------------------------------------------------------------------------
# Mock scoring (temporary — will be replaced with real scoring logic later)
# ---------------------------------------------------------------------------

TIPS_BY_CATEGORY = {
    "Elbow Angle": [
        "Keep your elbow at 90\u00b0 at the set point for a consistent release.",
        "Your elbow is drifting outward \u2014 tuck it under the ball.",
        "Great elbow alignment \u2014 maintain that L-shape on every shot.",
    ],
    "Follow-Through": [
        "Extend your wrist fully and hold \u2014 reach into the cookie jar.",
        "Your follow-through is cutting short \u2014 snap the wrist and freeze.",
        "Solid follow-through \u2014 keep that relaxed wrist flick.",
    ],
    "Release Point": [
        "Release at the peak of your jump for maximum arc.",
        "You're releasing too early \u2014 wait until you reach the top.",
        "Great timing on the release \u2014 that high arc gives you a shooter's touch.",
    ],
    "Stance": [
        "Feet shoulder-width apart with your shooting foot slightly ahead.",
        "Widen your base a bit \u2014 you're losing balance on the release.",
        "Strong foundation \u2014 your lower body is set up well for power.",
    ],
}

WEIGHTS = {
    "Elbow Angle": 0.3,
    "Follow-Through": 0.25,
    "Release Point": 0.25,
    "Stance": 0.2,
}

CATEGORY_NAMES = ["Elbow Angle", "Follow-Through", "Release Point", "Stance"]


def _get_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Needs Work"
    return "Poor"


def generate_mock_analysis(input_type: str) -> dict:
    categories = []
    for name in CATEGORY_NAMES:
        score = random.randint(60, 95)
        categories.append({
            "name": name,
            "score": score,
            "label": _get_label(score),
            "tip": random.choice(TIPS_BY_CATEGORY[name]),
        })

    overall_score = round(sum(c["score"] * WEIGHTS[c["name"]] for c in categories))

    return {
        "overallScore": overall_score,
        "overallLabel": _get_label(overall_score),
        "categories": categories,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputType": input_type,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(file: UploadFile):
    # Validate that the file looks like a video
    content_type = file.content_type or ""
    if not content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video.")

    # Save the uploaded file to a temp location so OpenCV can read it
    suffix = os.path.splitext(file.filename or "video.webm")[1] or ".webm"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(await file.read())
        tmp.close()

        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not read video file.")

        frame_count = 0
        poses_detected = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Sample every 3rd frame to keep processing fast
            if frame_count % 3 != 0:
                continue

            landmarks = tracker.process(frame)
            if landmarks is not None:
                poses_detected += 1

        cap.release()

        if frame_count == 0:
            raise HTTPException(status_code=400, detail="Video file is empty.")

        if poses_detected == 0:
            raise HTTPException(
                status_code=422,
                detail="No person detected in the video. Make sure you are visible in the frame.",
            )

        print(f"Processed {frame_count} frames, detected pose in {poses_detected} sampled frames.")

        # For now, return mock scores. Real scoring logic will replace this later.
        input_type = "upload"  # default; frontend sends this info too
        result = generate_mock_analysis(input_type)
        return result

    finally:
        os.unlink(tmp.name)
