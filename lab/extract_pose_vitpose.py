"""Layer 1: video -> landmark timeseries, ViTPose (research-grade upper bound).

Part of Test 1. ViTPose is a measuring instrument, not a candidate product
architecture: it exists to disambiguate a MediaPipe failure ("footage is
fundamentally untrackable" vs "a better model tracks it, so a lightweight
on-device path is worth pursuing"). Runs locally — footage never leaves the
machine; only model weights are downloaded (Hugging Face cache).

Pipeline per frame: RT-DETR person detection -> highest-score person box ->
ViTPose top-down pose on that box -> 17 COCO keypoints + scores, mapped onto
the shared 33-landmark schema (pose_schema.py) with NaN for BlazePose-only
landmarks, keypoint score in the `vis` columns. exp01_pose_quality.py and
render_overlay.py then work on it unchanged.

Usage:
    uv run lab/extract_pose_vitpose.py             # all clips in footage/
    uv run lab/extract_pose_vitpose.py clip.mp4    # specific clip(s)
    uv run lab/extract_pose_vitpose.py --force     # re-extract existing

Output: lab/results/exp01-pose-quality/landmarks/<clip>_vitpose.csv (+ .meta.json)
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import torch
from transformers import (
    AutoProcessor,
    RTDetrForObjectDetection,
    VitPoseForPoseEstimation,
)

from pose_schema import (
    COCO_TO_BLAZEPOSE,
    ClipMeta,
    empty_row,
    landmarks_csv_path,
    write_landmarks,
)

ROOT = Path(__file__).parent.parent
FOOTAGE_DIR = ROOT / "footage"
OUT_DIR = Path(__file__).parent / "results" / "exp01-pose-quality" / "landmarks"
MODEL_TAG = "vitpose"
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}

DETECTOR_ID = "PekingU/rtdetr_r50vd_coco_o365"
# vitpose-base-simple: no MoE dataset_index plumbing, COCO-trained.
# Swap via --pose-model for larger variants if the upper bound needs raising.
POSE_MODEL_ID = "usyd-community/vitpose-base-simple"
PERSON_LABEL = 0
DETECTION_THRESHOLD = 0.3


def pick_device() -> torch.device:
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        print(f"using GPU: {name}")
        return torch.device("cuda")
    print("CUDA not available — running on CPU (slow but fine as a batch job)")
    return torch.device("cpu")


class VitPosePipeline:
    def __init__(self, pose_model_id: str, device: torch.device):
        self.device = device
        self.pose_model_id = pose_model_id
        self.det_processor = AutoProcessor.from_pretrained(DETECTOR_ID)
        self.det_model = RTDetrForObjectDetection.from_pretrained(DETECTOR_ID).to(device)
        self.pose_processor = AutoProcessor.from_pretrained(pose_model_id)
        self.pose_model = VitPoseForPoseEstimation.from_pretrained(pose_model_id).to(device)
        self.det_model.eval()
        self.pose_model.eval()

    @torch.no_grad()
    def __call__(self, rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
        """rgb HxWx3 -> (keypoints_px (17,2), scores (17,)) or None if no person."""
        h, w = rgb.shape[:2]
        det_inputs = self.det_processor(images=rgb, return_tensors="pt").to(self.device)
        det_out = self.det_model(**det_inputs)
        det = self.det_processor.post_process_object_detection(
            det_out,
            target_sizes=torch.tensor([(h, w)]),
            threshold=DETECTION_THRESHOLD,
        )[0]
        person_mask = det["labels"] == PERSON_LABEL
        if not bool(person_mask.any()):
            return None
        boxes = det["boxes"][person_mask]
        scores = det["scores"][person_mask]
        # Highest-score person. Multi-person scenes (belayers) can steal the
        # box — overlay QA catches that; noted in manifest, not solved here.
        best = boxes[scores.argmax()].cpu().numpy()
        # xyxy -> coco xywh
        box_xywh = np.array(
            [[best[0], best[1], best[2] - best[0], best[3] - best[1]]],
            dtype=np.float32,
        )
        pose_inputs = self.pose_processor(
            rgb, boxes=[box_xywh], return_tensors="pt"
        ).to(self.device)
        pose_out = self.pose_model(**pose_inputs)
        pose = self.pose_processor.post_process_pose_estimation(
            pose_out, boxes=[box_xywh]
        )[0][0]
        return pose["keypoints"].cpu().numpy(), pose["scores"].cpu().numpy()


def extract_clip(clip_path: Path, pipeline: VitPosePipeline) -> Path:
    cap = cv2.VideoCapture(str(clip_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {clip_path}")
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
    t0 = time.time()
    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break
        if frame_idx == 0:
            height, width = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        row = empty_row(frame_idx, round(frame_idx * 1000.0 / fps))
        result = pipeline(rgb)
        if result is not None:
            keypoints, scores = result
            row["detected"] = 1
            for coco_i, blaze_i in COCO_TO_BLAZEPOSE.items():
                row[f"lm{blaze_i:02d}_x"] = float(keypoints[coco_i, 0]) / width
                row[f"lm{blaze_i:02d}_y"] = float(keypoints[coco_i, 1]) / height
                # z stays NaN (2D model); score goes in vis, presence stays NaN
                row[f"lm{blaze_i:02d}_vis"] = float(np.clip(scores[coco_i], 0.0, 1.0))
        rows.append(row)
        frame_idx += 1
        if frame_idx % 50 == 0:
            rate = frame_idx / (time.time() - t0)
            print(f"  frame {frame_idx} ({rate:.1f} fps)", flush=True)

    cap.release()
    if frame_idx == 0:
        raise RuntimeError(f"no frames decoded from {clip_path}")

    meta = ClipMeta(
        filename=clip_path.name,
        model=f"vitpose:{pipeline.pose_model_id}",
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
    parser.add_argument("clips", nargs="*", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--pose-model", default=POSE_MODEL_ID)
    args = parser.parse_args()

    clips = args.clips or sorted(
        p for p in FOOTAGE_DIR.iterdir() if p.suffix.lower() in VIDEO_EXTS
    )
    if not clips:
        print(f"no clips found in {FOOTAGE_DIR} — drop videos there first")
        return 1

    device = pick_device()
    pipeline = VitPosePipeline(args.pose_model, device)
    for clip in clips:
        out_csv = landmarks_csv_path(OUT_DIR, clip, MODEL_TAG)
        if out_csv.exists() and not args.force:
            print(f"skip (exists): {out_csv.name}")
            continue
        print(f"extracting: {clip.name} ...", flush=True)
        path = extract_clip(clip, pipeline)
        print(f"  -> {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
