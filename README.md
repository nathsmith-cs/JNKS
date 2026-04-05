# JNKS

AI-powered basketball shooting form analyzer. Record your three-point shot via webcam or upload a video, and get instant feedback comparing your form to pro players like Steph Curry and Klay Thompson.

## How It Works

1. **Record** your shot using a webcam (live analysis) or upload a video file
2. **Detect** shots automatically using YOLOv8 ball tracking + MediaPipe pose estimation
3. **Compare** your form against pro reference shots across 4 phases (gather, set point, release, follow-through)
4. **Score** with Gemini AI vision analysis blended with pose metrics
5. **Coach** with TTS voice feedback and personalized tips

## Tech Stack

**Frontend**
- Next.js 16 (React 19) with TypeScript
- Tailwind CSS 4, shadcn/ui components
- Three.js / React Three Fiber (3D basketball model)
- Framer Motion, GSAP, Anime.js (animations)

**Computer Vision Pipeline**
- MediaPipe (33-point pose landmark detection)
- YOLOv8 / Ultralytics (basketball detection with custom `basketball.pt` model)
- OpenCV (video capture and frame processing)

**AI Coaching**
- Gemini Pro (per-shot video analysis)
- Gemini Flash (structured scoring distillation)
- Gemini TTS (voice coaching audio)

## Prerequisites

- **Node.js** 18+
- **Python** 3.8+
- **ngrok** (tunnels the backend so your phone can connect)
  ```bash
  brew install ngrok
  ngrok config add-authtoken YOUR_TOKEN
  ```

## Getting Started

### 1. Clone and install

```bash
git clone https://github.com/nathsmith-cs/JNKS.git
cd JNKS
npm install
```

### 2. Set up the Python backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r pipeline/requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Run

```bash
./start.sh
```

This will:
- Start an ngrok tunnel on port 8000
- Build the frontend with the ngrok URL baked in
- Start the FastAPI backend (serves both the API and the static frontend)
- Print the URL to open on your phone

**Access:**
- Phone/remote: the ngrok URL printed by the script
- Local: `http://localhost:8000`

Press `Ctrl+C` to stop everything.

### Manual start (without ngrok)

If you only need local access:

```bash
source venv/bin/activate
npm run build
python3 -m pipeline.server
```

Then open `http://localhost:8000`.

## Project Structure

```
src/
  app/              # Next.js pages (landing, analyze, results)
  components/
    3d/             # Three.js basketball scene
    analyze/        # Webcam feed, video upload, analyze button
    landing/        # Hero, features, how-it-works sections
    results/        # Score display, breakdown, tips
    layout/         # Navbar, theme, animated background
    ui/             # Reusable UI (buttons, cards, progress, etc.)
  lib/              # Utilities, API helpers, workout storage
  types/            # TypeScript interfaces

pipeline/           # Python CV + AI pipeline
  server.py         # FastAPI server (REST + WebSocket)
  detector.py       # YOLOv8 ball detection
  tracker.py        # MediaPipe pose estimation (real-time)
  pose_extract.py   # MediaPipe pose extraction (batch/video mode)
  phases.py         # Shot phase detection (gather, set point, release, follow-through)
  compare.py        # Shot comparison against pro references
  angles.py         # Joint angle computation
  scoring.py        # Hybrid scoring (MediaPipe metrics + Gemini vision)
  gemini_vision.py  # Gemini video analysis per clip
  llm.py            # Gemini text generation, TTS
  voice.py          # Gemini Live voice coaching session
  video.py          # Video conversion and splitting (ffmpeg)
  models/           # Pre-trained weights (basketball.pt, pose_landmarker_lite.task)
  reference/        # Pro player reference shots (JSON pose data)

start.sh            # One-command startup (ngrok + build + backend)
```

## Scoring Categories

| Category | Description |
|----------|-------------|
| **Elbow Angle** | Shooting arm alignment at the set point |
| **Follow-Through** | Wrist extension and snap after release |
| **Release Point** | Height and timing of the ball release |
| **Stance** | Foot positioning, knee bend, and balance |

Each category is scored 0-100. The overall score is a weighted average with Gemini AI coaching tailored to your weakest area.

## Live Camera Flow

The webcam streams 1.5-second video chunks over WebSocket. The server processes each chunk with OpenCV, detects shots via ball tracking + pose estimation, and after every 5 shots:

1. Sends per-shot video to Gemini Pro for visual coaching
2. Distills all observations into structured scores via Gemini Flash
3. Generates TTS audio of the coaching advice
4. Sends results back to the client
