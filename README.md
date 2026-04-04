# JNKS

AI-powered basketball shooting form analyzer. Record your three-point shot via webcam or upload a video, and get instant feedback on your technique.

## How It Works

1. **Record** your shot using a webcam or upload a video file
2. **Analyze** your form with computer vision and pose estimation
3. **Get feedback** with scores and tips to improve your shot

## Tech Stack

**Frontend**
- Next.js 16 (React 19) with TypeScript
- Tailwind CSS 4
- Three.js / React Three Fiber (3D basketball model)
- Framer Motion, GSAP, Anime.js (animations)
- shadcn/ui components

**Computer Vision Pipeline**
- MediaPipe (pose landmark detection, 33-point skeleton tracking)
- YOLOv8 / Ultralytics (basketball detection with custom-trained model)
- OpenCV (video capture and frame processing)
- NumPy

## Project Structure

```
src/
  app/             # Next.js pages (landing, analyze, results)
  components/
    3d/            # Three.js basketball model and scene
    analyze/       # Webcam feed, video upload, analyze button
    landing/       # Hero section, features, how-it-works
    results/       # Score display, breakdown, tips
    layout/        # Navbar, theme provider, animated background
    ui/            # Reusable UI components (buttons, cards, etc.)
  lib/             # Utilities and mock data
  types/           # TypeScript interfaces

pipeline/          # Python CV pipeline
  detector.py      # Ball detection and tracking (YOLOv8)
  tracker.py       # Pose estimation (MediaPipe)
  storage.py       # Session recording (JSON output)
  models/          # Pre-trained model weights

capture.py         # CLI tool for real-time shot capture
visualize.py       # CLI tool for visualization and batch processing
```

## Getting Started

### Frontend

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Python Pipeline

```bash
pip install -r requirements.txt

# Webcam capture
python capture.py

# Process a video file
python capture.py --video path/to/video.mp4

# Visualize with pose overlay
python visualize.py --video path/to/video.mp4
```

## Scoring Categories

- **Elbow Angle** - Alignment of your shooting arm
- **Follow-Through** - Extension and wrist snap after release
- **Release Point** - Height and timing of the ball release
- **Stance** - Foot positioning and balance

Each category is scored 0-100 and combined into an overall score with actionable tips targeting your weakest area.
