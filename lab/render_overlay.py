"""Render skeleton overlays for eyeball QA of Test 1 extractions.

Draws the extracted landmarks back onto the source video with per-keypoint
confidence coloring (green >= 0.7, yellow 0.5-0.7, red < 0.5; core keypoints
drawn larger). The numbers in summary.csv can look fine while the skeleton is
locked onto a belayer — watching one overlay per clip catches that.

Usage:
    uv run lab/render_overlay.py                    # all extracted clips
    uv run lab/render_overlay.py clip.mp4           # specific clip(s)
    uv run lab/render_overlay.py --model mediapipe  # which extraction to draw

Output: lab/results/exp01-pose-quality/overlays/<clip>_<model>_overlay.mp4
(video files are gitignored repo-wide; overlays never leave the machine).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

from pose_schema import CORE_KEYPOINTS, N_LANDMARKS, landmarks_csv_path, read_landmarks

ROOT = Path(__file__).parent.parent
FOOTAGE_DIR = ROOT / "footage"
RESULTS_DIR = Path(__file__).parent / "results" / "exp01-pose-quality"
LANDMARKS_DIR = RESULTS_DIR / "landmarks"
OVERLAYS_DIR = RESULTS_DIR / "overlays"

# BlazePose 33-landmark skeleton (subset: body, no face mesh edges)
CONNECTIONS = [
    (11, 12),                      # shoulders
    (11, 13), (13, 15),            # left arm
    (12, 14), (14, 16),            # right arm
    (11, 23), (12, 24), (23, 24),  # torso
    (23, 25), (25, 27), (27, 31),  # left leg
    (24, 26), (26, 28), (28, 32),  # right leg
    (7, 11), (8, 12),              # ear-shoulder (shoulder-elevation cue)
]
CORE_IDXS = set(CORE_KEYPOINTS.values())


def vis_color(vis: float) -> tuple[int, int, int]:  # BGR
    if np.isnan(vis) or vis < 0.5:
        return (0, 0, 255)      # red
    if vis < 0.7:
        return (0, 220, 255)    # yellow
    return (0, 220, 0)          # green


def render_clip(
    clip_path: Path,
    model_tag: str,
    landmarks_dir: Path = LANDMARKS_DIR,
    overlays_dir: Path = OVERLAYS_DIR,
) -> Path:
    csv_path = landmarks_csv_path(landmarks_dir, clip_path, model_tag)
    if not csv_path.exists():
        raise FileNotFoundError(f"no extraction for {clip_path.name}: {csv_path}")
    df, meta = read_landmarks(csv_path)

    cap = cv2.VideoCapture(str(clip_path))
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {clip_path}")

    overlays_dir.mkdir(parents=True, exist_ok=True)
    out_path = overlays_dir / f"{clip_path.stem}_{model_tag}_overlay.mp4"
    w, h, fps = meta["width"], meta["height"], meta["fps"]
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    scale = max(1.0, h / 1080)  # keep line widths sensible on 4K clips

    xs = np.column_stack([df[f"lm{i:02d}_x"].to_numpy() for i in range(N_LANDMARKS)])
    ys = np.column_stack([df[f"lm{i:02d}_y"].to_numpy() for i in range(N_LANDMARKS)])
    vs = np.column_stack([df[f"lm{i:02d}_vis"].to_numpy() for i in range(N_LANDMARKS)])
    detected = df["detected"].to_numpy()

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok or frame_idx >= len(df):
            break
        if detected[frame_idx]:
            px = xs[frame_idx] * w
            py = ys[frame_idx] * h
            for a, b in CONNECTIONS:
                if np.isnan(px[a]) or np.isnan(px[b]):
                    continue
                cv2.line(frame, (int(px[a]), int(py[a])), (int(px[b]), int(py[b])),
                         (255, 200, 100), max(1, int(2 * scale)))
            for i in range(N_LANDMARKS):
                if np.isnan(px[i]):
                    continue
                r = int((7 if i in CORE_IDXS else 3) * scale)
                cv2.circle(frame, (int(px[i]), int(py[i])), r,
                           vis_color(vs[frame_idx, i]), -1)
        label = f"f{frame_idx}" + ("" if detected[frame_idx] else "  NO POSE")
        cv2.putText(frame, label, (10, int(30 * scale)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8 * scale, (255, 255, 255), max(1, int(2 * scale)))
        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clips", nargs="*", type=Path)
    parser.add_argument("--model", default="mediapipe")
    parser.add_argument("--landmarks-dir", type=Path, default=LANDMARKS_DIR,
                        help="where the landmark CSVs live (default: exp01 pool)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="overlay output dir (default: overlays/ next to landmarks)")
    args = parser.parse_args()

    out_dir = args.out_dir or args.landmarks_dir.parent / "overlays"

    if args.clips:
        clips = args.clips
    else:
        # every clip in footage/ that has an extraction for this model
        clips = [
            p for p in sorted(FOOTAGE_DIR.rglob("*"))
            if p.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}
            and landmarks_csv_path(args.landmarks_dir, p, args.model).exists()
        ]
    if not clips:
        print("nothing to render — extract landmarks first")
        return 1

    for clip in clips:
        print(f"rendering: {clip.name} [{args.model}] ...", flush=True)
        out = render_clip(clip, args.model, args.landmarks_dir, out_dir)
        print(f"  -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
