"""Layer 1: video -> landmark timeseries, MediaPipe PoseLandmarker (heavy), VIDEO mode.

Part of Test 1 (pose quality go/no-go). This script only extracts and stores raw
landmarks per pose_schema.py; all metrics live in exp01_pose_quality.py.

Usage:
    uv run lab/extract_pose_mediapipe.py            # all clips in footage/
    uv run lab/extract_pose_mediapipe.py clip.mp4   # specific clip(s)
    uv run lab/extract_pose_mediapipe.py --force    # re-extract existing

Output: lab/results/exp01-pose-quality/landmarks/<clip>_mediapipe.csv (+ .meta.json)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from pose_schema import (
    ClipMeta,
    empty_row,
    landmarks_csv_path,
    write_landmarks,
)

ROOT = Path(__file__).parent.parent
FOOTAGE_DIR = ROOT / "footage"
MODEL_PATH = Path(__file__).parent / "models" / "pose_landmarker_heavy.task"
OUT_DIR = Path(__file__).parent / "results" / "exp01-pose-quality" / "landmarks"
MODEL_TAG = "mediapipe"
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}


def make_landmarker() -> vision.PoseLandmarker:
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        output_segmentation_masks=False,
    )
    return vision.PoseLandmarker.create_from_options(options)


def extract_clip(clip_path: Path, landmarker: vision.PoseLandmarker) -> Path:
    cap = cv2.VideoCapture(str(clip_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {clip_path}")

    # Ask OpenCV to apply phone rotation metadata; record what it reports.
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    rotation_meta = cap.get(cv2.CAP_PROP_ORIENTATION_META)

    fps = cap.get(cv2.CAP_PROP_FPS)
    notes = ""
    if not fps or fps <= 0 or fps > 240:
        notes = f"suspicious fps={fps}, assuming 30"
        fps = 30.0

    rows: list[dict] = []
    width = height = 0
    frame_idx = 0
    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break
        if frame_idx == 0:
            height, width = frame_bgr.shape[:2]

        # MediaPipe VIDEO mode requires strictly increasing integer timestamps.
        t_ms = round(frame_idx * 1000.0 / fps)
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(mp_image, t_ms)

        row = empty_row(frame_idx, t_ms)
        if result.pose_landmarks:
            row["detected"] = 1
            for i, lm in enumerate(result.pose_landmarks[0]):
                row[f"lm{i:02d}_x"] = lm.x
                row[f"lm{i:02d}_y"] = lm.y
                row[f"lm{i:02d}_z"] = lm.z
                row[f"lm{i:02d}_vis"] = lm.visibility
                row[f"lm{i:02d}_presence"] = lm.presence
        rows.append(row)
        frame_idx += 1

    cap.release()
    if frame_idx == 0:
        raise RuntimeError(f"no frames decoded from {clip_path}")

    meta = ClipMeta(
        filename=clip_path.name,
        model="mediapipe_pose_landmarker_heavy",
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_idx,
        rotation_meta=rotation_meta,
        extracted_at=datetime.now(timezone.utc).isoformat(),
        notes=notes,
    )
    return write_landmarks(OUT_DIR, clip_path, MODEL_TAG, rows, meta)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clips", nargs="*", type=Path,
                        help="specific clips (default: all in footage/)")
    parser.add_argument("--force", action="store_true",
                        help="re-extract clips that already have a landmarks CSV")
    args = parser.parse_args()

    clips = args.clips or sorted(
        p for p in FOOTAGE_DIR.iterdir()
        if p.suffix.lower() in VIDEO_EXTS
    )
    if not clips:
        print(f"no clips found in {FOOTAGE_DIR} — drop videos there first")
        return 1

    landmarker = None
    for clip in clips:
        out_csv = landmarks_csv_path(OUT_DIR, clip, MODEL_TAG)
        if out_csv.exists() and not args.force:
            print(f"skip (exists): {out_csv.name}")
            continue
        # A fresh landmarker per clip: VIDEO-mode timestamps must be
        # monotonic within a landmarker's lifetime, and tracking state
        # must not leak between clips.
        landmarker = make_landmarker()
        print(f"extracting: {clip.name} ...", flush=True)
        path = extract_clip(clip, landmarker)
        landmarker.close()
        print(f"  -> {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
