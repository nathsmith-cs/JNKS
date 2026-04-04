import argparse
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import json

from pipeline.tracker import PoseTracker, LANDMARK_NAMES
from pipeline.detector import BallDetector, BallTracker
from pipeline.phases import detect_phases, compute_angle_sequence
from pipeline.compare import find_best_match

# Skeleton connections between tracked landmarks (by name)
SKELETON = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("left_wrist", "left_index"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("right_wrist", "right_index"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("left_ankle", "left_heel"),
    ("left_ankle", "left_foot_index"),
    ("left_heel", "left_foot_index"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("right_ankle", "right_heel"),
    ("right_ankle", "right_foot_index"),
    ("right_heel", "right_foot_index"),
]

JOINT_COLOR = (0, 255, 0)
BONE_COLOR = (0, 220, 0)
HAND_COLOR = (255, 0, 255)
BALL_COLOR = (0, 165, 255)
SHOT_COLOR = (0, 0, 255)

HAND_KEYS = {"left_wrist", "right_wrist", "left_index", "right_index"}

FOLLOW_THROUGH_FRAMES = 15
MIN_SHOT_FRAMES = 45


def draw_pose(frame, landmarks):
    h, w = frame.shape[:2]

    points = {}
    for name, lm in landmarks.items():
        if lm["visibility"] > 0.5:
            px = int(lm["x"] * w)
            py = int(lm["y"] * h)
            points[name] = (px, py)

    for a, b in SKELETON:
        if a in points and b in points:
            cv2.line(frame, points[a], points[b], BONE_COLOR, 2)

    for name, pt in points.items():
        if name in HAND_KEYS:
            cv2.circle(frame, pt, 8, HAND_COLOR, -1)
        else:
            cv2.circle(frame, pt, 5, JOINT_COLOR, -1)


def save_clip(frames, out_path, fps):
    """Write a list of frames to an mp4. Returns True if written."""
    if not frames:
        return False
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"avc1"), fps, (w, h))
    if not writer.isOpened():
        for codec in ["mp4v", "XVID"]:
            writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*codec), fps, (w, h))
            if writer.isOpened():
                break
    for f in frames:
        writer.write(f)
    writer.release()
    return True


def is_shot_motion(landmark_buffer):
    """Check if landmarks show upward wrist motion (shooting trajectory).

    Looks at the first and last third of the clip. If either wrist
    moves significantly upward relative to the shoulder, it's a shot.
    """
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

        # In normalized coords, y decreases going up.
        # Wrist should move upward (lower y) and end above or near shoulder.
        upward_motion = avg_early - avg_late
        if upward_motion > 0.05 and avg_late < avg_shoulder + 0.05:
            return True

    return False


def run():
    parser = argparse.ArgumentParser(description="Basketball shot processor")
    parser.add_argument("--video", type=str, default=None,
                        help="Path to a video file (omit to use webcam)")
    parser.add_argument("--reference", type=str, default=None,
                        help="Path to reference shots folder (e.g. pipeline/reference/StephCurryShots)")
    args = parser.parse_args()
    ref_dir = args.reference

    source = args.video if args.video else 0
    is_live = not args.video
    cap = cv2.VideoCapture(source)

    if is_live:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        video_fps = None  # determined from actual capture rate
    else:
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30

    if not cap.isOpened():
        print(f"Error: cannot open {'video file' if args.video else 'camera'}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if args.video else 0

    if args.video:
        base = os.path.splitext(os.path.basename(args.video))[0]
        out_dir = os.path.join("output", base)
    else:
        base = "live"
        out_dir = None  # created per batch
    batch_num = 0

    tracker = PoseTracker()
    ball_detector = BallDetector()
    ball_tracker = BallTracker()

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

    SHOTS_PER_BATCH = 5

    shot_buffer = []
    landmark_buffer = []
    shot_count = 0
    batch_shots = 0
    clips_saved = 0
    running = True

    def new_batch():
        nonlocal out_dir, batch_num, batch_shots, shot_count
        if is_live:
            from datetime import datetime
            batch_num += 1
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            out_dir = os.path.join("output", f"session_{ts}")
            os.makedirs(out_dir, exist_ok=True)
            batch_shots = 0
            shot_count = 0
            print(f"\nNew batch: {out_dir}/")
        elif out_dir:
            os.makedirs(out_dir, exist_ok=True)

    def build_supercut():
        if not out_dir:
            return
        import glob
        clip_files = sorted(glob.glob(os.path.join(out_dir, "shot_*.mp4")))
        if not clip_files:
            return
        supercut_path = os.path.join(out_dir, "supercut.mp4")
        sc_writer = None
        total_sc_frames = 0
        for cf in clip_files:
            clip_cap = cv2.VideoCapture(cf)
            while True:
                ret_c, f_c = clip_cap.read()
                if not ret_c:
                    break
                if sc_writer is None:
                    ch, cw = f_c.shape[:2]
                    sc_writer = cv2.VideoWriter(supercut_path, cv2.VideoWriter_fourcc(*"avc1"), video_fps or 30, (cw, ch))
                    if not sc_writer.isOpened():
                        for codec in ["mp4v", "XVID"]:
                            sc_writer = cv2.VideoWriter(supercut_path, cv2.VideoWriter_fourcc(*codec), video_fps or 30, (cw, ch))
                            if sc_writer.isOpened():
                                break
                sc_writer.write(f_c)
                total_sc_frames += 1
            clip_cap.release()
        if sc_writer:
            sc_writer.release()
            print(f"Supercut: {supercut_path} ({total_sc_frames} frames)")

    def shutdown(signum=None, frame=None):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if not is_live:
        new_batch()

    print("Processing...")

    save_lock = threading.Lock()

    def _print_batch_report():
        """Print summary of all shots in the current batch."""
        import glob as g
        json_files = sorted(g.glob(os.path.join(out_dir, "shot_*.json")))
        if not json_files:
            return
        print(f"\n{'='*60}")
        print(f"BATCH REPORT — {out_dir}")
        print(f"{'='*60}")
        scores = []
        for jf in json_files:
            with open(jf) as f:
                data = json.load(f)
            name = os.path.basename(jf).replace(".json", "")
            comp = data.get("comparison")
            if comp:
                scores.append(comp["score"])
                print(f"  {name}: {comp['score']}% similar to {comp['best_ref']}")
                for phase, s in comp["phase_scores"].items():
                    print(f"    {phase}: {s}%")
            else:
                print(f"  {name}: no comparison data")
        if scores:
            avg = sum(scores) / len(scores)
            print(f"\n  Average similarity: {avg:.1f}%")
            print(f"  Best shot: {max(scores):.1f}%")
            print(f"  Worst shot: {min(scores):.1f}%")
        print(f"{'='*60}\n")

    def flush_shot():
        nonlocal shot_buffer, landmark_buffer, shot_count, clips_saved, batch_shots
        if len(shot_buffer) < MIN_SHOT_FRAMES or not is_shot_motion(landmark_buffer):
            shot_buffer = []
            landmark_buffer = []
            return
        if is_live and batch_shots == 0:
            new_batch()
        from datetime import datetime
        shot_count += 1
        frames_to_save = shot_buffer
        landmarks_to_save = landmark_buffer
        shot_buffer = []
        landmark_buffer = []
        ts = datetime.now().strftime("%H-%M-%S")
        clip_path = os.path.join(out_dir, f"shot_{ts}.mp4")
        data_path = os.path.join(out_dir, f"shot_{ts}.json")
        frame_count = len(frames_to_save)
        clips_saved += 1
        batch_shots += 1
        do_supercut = is_live and batch_shots >= SHOTS_PER_BATCH

        def _save():
            save_clip(frames_to_save, clip_path, video_fps or 30)
            # Compute and save analysis data
            phases = detect_phases(landmarks_to_save)
            angles = compute_angle_sequence(landmarks_to_save)
            shot_data = {
                "frames": frame_count,
                "phases": phases,
                "angles": angles,
                "landmarks": landmarks_to_save,
            }
            # Run comparison against reference if provided
            if ref_dir:
                match = find_best_match(landmarks_to_save, ref_dir)
                if match:
                    shot_data["comparison"] = {
                        "best_ref": match["best_ref"],
                        "score": match["best_score"],
                        "phase_scores": match["analysis"]["phase_scores"],
                        "angle_diffs": match["analysis"]["angle_diffs"],
                        "all_scores": match["all_scores"],
                    }
            with open(data_path, "w") as f:
                json.dump(shot_data, f)
            score_str = ""
            if ref_dir and shot_data.get("comparison"):
                c = shot_data["comparison"]
                score_str = f"  |  similarity: {c['score']}% (vs {c['best_ref']})"
            print(f"\nSaved {clip_path} ({frame_count} frames)  |  batch: {batch_shots}/{SHOTS_PER_BATCH}{score_str}")
            if do_supercut:
                with save_lock:
                    build_supercut()
                    _print_batch_report()

        threading.Thread(target=_save, daemon=True).start()
        if do_supercut:
            batch_shots = 0

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

        # Run YOLO and pose in parallel when both are needed
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
            # Ball disappeared mid-shot — grace period
            ball_lost_frames += 1
            if ball_lost_frames <= BALL_LOST_GRACE:
                # Keep the shot alive, run YOLO next frame to recheck
                confirm_frames = max(confirm_frames, 1)
            else:
                # Grace expired — shot is over
                if shot_frames >= SHOT_MIN_FRAMES:
                    shot_cooldown = FOLLOW_THROUGH_FRAMES
                shot_frames = 0
                ball_lost_frames = 0

        tracking = ball_info["has_ball"] or shot_frames > 0 or shot_cooldown > 0

        for box in ball_boxes:
            x1, y1, x2, y2 = int(box["x1"]), int(box["y1"]), int(box["x2"]), int(box["y2"])
            cv2.rectangle(frame, (x1, y1), (x2, y2), BALL_COLOR, 2)

        if tracking and landmarks:
            draw_pose(frame, landmarks)
            label = "SHOT" if ball_info["has_ball"] else "FOLLOW-THROUGH"
            cv2.putText(frame, label, (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, SHOT_COLOR, 3)

        if tracking:
            shot_buffer.append(frame.copy())
            landmark_buffer.append(landmarks)
        elif shot_buffer:
            flush_shot()

        if shot_cooldown > 0:
            shot_cooldown -= 1
            if shot_cooldown == 0:
                cooldown_skip = int((video_fps or 30) * 3)

        frame_number += 1
        fps_count += 1

        now = time.monotonic()
        elapsed = now - fps_timer
        if elapsed >= 1.0:
            fps = fps_count / elapsed
            if video_fps is None:
                video_fps = fps  # lock in actual capture rate for live
            wall = now - start_time
            video_time = frame_number / video_fps if video_fps else 0
            ratio = video_time / wall if wall > 0 else 0
            if total_frames:
                pct = frame_number / total_frames * 100
                bar = int(pct / 2)
                print(f"\r[{'=' * bar}{' ' * (50 - bar)}] {pct:.0f}%  |  FPS: {fps:.1f}  |  {ratio:.1f}x realtime  |  shots: {clips_saved}", end="", flush=True)
            else:
                print(f"FPS: {fps:.1f}  |  {ratio:.1f}x realtime  |  shots: {clips_saved}")
            fps_count = 0
            fps_timer = now

    # Flush any remaining shot
    if shot_buffer:
        flush_shot()

    # Wait for background saves to finish
    with save_lock:
        pass
    # Small delay to let final save threads complete
    time.sleep(0.5)

    # Build final supercut for incomplete live batch or video files
    if batch_shots > 0 and is_live:
        build_supercut()
        if ref_dir:
            _print_batch_report()
    elif not is_live and clips_saved > 0:
        build_supercut()
        if ref_dir:
            _print_batch_report()

    total_wall = time.monotonic() - start_time
    total_video = frame_number / (video_fps or 30) if frame_number else 0
    cap.release()
    tracker.close()

    print(f"\n{clips_saved} shots captured")
    print(f"Processed {total_video:.1f}s of video in {total_wall:.1f}s ({total_video / total_wall:.1f}x realtime)")


if __name__ == "__main__":
    run()
