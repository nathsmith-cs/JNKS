import argparse
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import cv2

from pipeline import PoseTracker, BallDetector, BallTracker, SessionStorage


def run():
    parser = argparse.ArgumentParser(description="Basketball pose capture")
    parser.add_argument("--video", type=str, default=None,
                        help="Path to a video file (omit to use webcam)")
    args = parser.parse_args()

    source = args.video if args.video else 0
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: cannot open {'video file' if args.video else 'camera'}")
        sys.exit(1)

    if not args.video:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    tracker = PoseTracker()
    ball_detector = BallDetector()
    ball_tracker = BallTracker()
    storage = SessionStorage()

    FOLLOW_THROUGH_FRAMES = 15
    SHOT_MIN_FRAMES = 20

    frame_number = 0
    fps_count = 0
    fps_timer = time.monotonic()
    start_time = time.monotonic()
    BALL_LOST_GRACE = 5

    shot_frames = 0
    shot_cooldown = 0
    ball_boxes = []
    confirm_frames = 0
    cooldown_skip = 0
    ball_lost_frames = 0
    running = True

    def shutdown(signum=None, frame=None):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("Capturing... press 'q' in the preview window or Ctrl+C to stop.")

    while running:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp_ms = (time.monotonic() - start_time) * 1000.0

        run_yolo = False
        if cooldown_skip > 0:
            cooldown_skip -= 1
            ball_boxes = []
        elif shot_cooldown > 0:
            ball_boxes = []
        elif confirm_frames > 0:
            run_yolo = True
            confirm_frames -= 1
        elif shot_frames > 0 and frame_number % 10 == 0:
            run_yolo = True
        elif shot_frames == 0 and frame_number % 5 == 0:
            run_yolo = True
        h, w = frame.shape[:2]

        need_pose = bool(ball_boxes) or shot_cooldown > 0

        if run_yolo and need_pose:
            with ThreadPoolExecutor(max_workers=2) as ex:
                yolo_future = ex.submit(ball_detector.detect, frame)
                pose_future = ex.submit(tracker.process, frame)
                ball_boxes = yolo_future.result()
                landmarks = pose_future.result()
        elif run_yolo:
            ball_boxes = ball_detector.detect(frame)
            if ball_boxes:
                confirm_frames = 3
            landmarks = None
        elif need_pose:
            landmarks = tracker.process(frame)
        else:
            landmarks = None

        ball_info = ball_tracker.update(landmarks, ball_boxes, w, h)

        if ball_info["has_ball"]:
            shot_frames += 1
            shot_cooldown = 0
            ball_lost_frames = 0
        elif shot_frames > 0:
            ball_lost_frames += 1
            if ball_lost_frames <= BALL_LOST_GRACE:
                confirm_frames = max(confirm_frames, 1)
            else:
                if shot_frames >= SHOT_MIN_FRAMES:
                    shot_cooldown = FOLLOW_THROUGH_FRAMES
                shot_frames = 0
                ball_lost_frames = 0

        if ball_info["has_ball"] or shot_cooldown > 0:
            storage.append(frame_number, timestamp_ms, landmarks, ball_info)
            if shot_cooldown > 0:
                shot_cooldown -= 1
                if shot_cooldown == 0:
                    cooldown_skip = 90  # ~3 seconds at 30fps

        frame_number += 1
        fps_count += 1

        now = time.monotonic()
        elapsed = now - fps_timer
        if elapsed >= 1.0:
            print(f"FPS: {fps_count / elapsed:.1f}  |  frames: {frame_number}  |  shot frames captured: {storage.count}")
            fps_count = 0
            fps_timer = now

        cv2.imshow("capture", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    tracker.close()

    path = storage.save()
    if path:
        print(f"\nSession saved: {path}  ({storage.count} frames)")
    else:
        print("\nNo frames captured.")


if __name__ == "__main__":
    run()
