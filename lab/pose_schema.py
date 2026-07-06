"""Shared landmark-timeseries schema for all pose extractors.

Contract: every extractor (MediaPipe, ViTPose, ...) writes one CSV per clip with
columns  frame, t_ms, detected, lm{00..32}_{x,y,z,vis,presence}  in BlazePose
33-landmark index order, coordinates normalized to image width/height, plus a
sidecar JSON with clip metadata. Models with fewer keypoints (e.g. COCO-17)
map their keypoints onto the matching BlazePose indices and leave the rest NaN.
The analysis layer reads this schema and never touches video or models.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

N_LANDMARKS = 33
FIELDS = ("x", "y", "z", "vis", "presence")

# BlazePose landmark indices used by Test 1 analysis
NOSE = 0
SHOULDER_L, SHOULDER_R = 11, 12
ELBOW_L, ELBOW_R = 13, 14
WRIST_L, WRIST_R = 15, 16
HIP_L, HIP_R = 23, 24
KNEE_L, KNEE_R = 25, 26
ANKLE_L, ANKLE_R = 27, 28
EAR_L, EAR_R = 7, 8

CORE_KEYPOINTS = {  # the pass-criterion set
    "shoulder_l": SHOULDER_L,
    "shoulder_r": SHOULDER_R,
    "hip_l": HIP_L,
    "hip_r": HIP_R,
}
LIMB_KEYPOINTS = {  # the occlusion-measure set
    "wrist_l": WRIST_L,
    "wrist_r": WRIST_R,
    "ankle_l": ANKLE_L,
    "ankle_r": ANKLE_R,
}

# COCO-17 keypoint index -> BlazePose landmark index (for ViTPose-class models)
COCO_TO_BLAZEPOSE = {
    0: NOSE,
    1: 2,   # left_eye  -> left eye
    2: 5,   # right_eye -> right eye
    3: EAR_L,
    4: EAR_R,
    5: SHOULDER_L,
    6: SHOULDER_R,
    7: ELBOW_L,
    8: ELBOW_R,
    9: WRIST_L,
    10: WRIST_R,
    11: HIP_L,
    12: HIP_R,
    13: KNEE_L,
    14: KNEE_R,
    15: ANKLE_L,
    16: ANKLE_R,
}


def landmark_columns() -> list[str]:
    return [
        f"lm{i:02d}_{f}" for i in range(N_LANDMARKS) for f in FIELDS
    ]


def empty_row(frame: int, t_ms: int) -> dict:
    """Row for a frame where no pose was detected (all landmark fields NaN)."""
    row: dict = {"frame": frame, "t_ms": t_ms, "detected": 0}
    for col in landmark_columns():
        row[col] = np.nan
    return row


@dataclass
class ClipMeta:
    filename: str
    model: str
    width: int
    height: int
    fps: float
    frame_count: int
    rotation_meta: float | None
    extracted_at: str
    notes: str = ""


def landmarks_csv_path(out_dir: Path, clip_path: Path, model_tag: str) -> Path:
    return out_dir / f"{clip_path.stem}_{model_tag}.csv"


def write_landmarks(
    out_dir: Path, clip_path: Path, model_tag: str, rows: list[dict], meta: ClipMeta
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = landmarks_csv_path(out_dir, clip_path, model_tag)
    df = pd.DataFrame(rows, columns=["frame", "t_ms", "detected", *landmark_columns()])
    df.to_csv(csv_path, index=False)
    csv_path.with_suffix(".meta.json").write_text(json.dumps(asdict(meta), indent=2))
    return csv_path


def read_landmarks(csv_path: Path) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(csv_path)
    meta = json.loads(csv_path.with_suffix(".meta.json").read_text())
    return df, meta
