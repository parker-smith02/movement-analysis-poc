"""Batch-click the reference hold for exp02 variant D (Test 2).

Variant D anchors hip height to a WORLD-fixed point — one distinctive hold
clicked in every take — after the ankle midpoint failed as an anchor (see
lab/results/exp02-noise-floor/findings-anchor.md). The camera is static per
take, so a single clicked pixel coordinate per take is a valid anchor; no
tracking needed. Clicking per take (not per camera setup) is deliberate:
click repeatability is real product noise (the user taps the hold in each
clip) and must enter the measured noise floor.

Loops over the analysis takes in footage/exp02/takes.csv that don't yet have
an entry in footage/exp02/anchors.json, shows one frame of each, and records
the clicked full-resolution pixel coordinate. Click the SAME physical hold in
every clip. Saves after every clip, so quitting midway is safe; re-running
resumes at the missing entries.

Usage:
    uv run lab/pick_anchors.py                       # all missing takes
    uv run lab/pick_anchors.py --redo sf1-1.MOV ...  # re-click specific takes
    uv run lab/pick_anchors.py --frame 30            # click a later frame

Keys: left-click = place/move the marker, ENTER/SPACE = confirm and advance,
u = clear marker, s = skip (hold not visible; recorded as null),
q/ESC = quit (progress saved).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import pandas as pd

ROOT = Path(__file__).parent.parent
DEFAULT_TAKES_DIR = ROOT / "footage" / "exp02"
ANALYSIS_GROUPS = ("static-fixed", "static-reset", "movement")

WINDOW = "pick_anchors"


def read_frame(clip: Path, frame_idx: int):
    cap = cv2.VideoCapture(str(clip))
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def load_anchors(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {
        "hold_comment": "purple on top row",
        "anchors": {},
    }


def save_anchors(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def pick_one(clip: Path, frame_idx: int, display_height: int,
             progress: str) -> tuple[str, list[int] | None]:
    """Show one frame; return ("set", [x, y]) | ("skip", None) | ("quit", None)."""
    frame = read_frame(clip, frame_idx)
    if frame is None:
        print(f"  cannot read frame {frame_idx} from {clip.name} — skipping "
              "(no entry written)")
        return "unreadable", None

    h, w = frame.shape[:2]
    scale = min(1.0, display_height / h)
    disp_size = (int(w * scale), int(h * scale))
    clicked: list[tuple[int, int]] = []

    def redraw() -> None:
        canvas = cv2.resize(frame, disp_size)
        header = f"{progress}  {clip.name}  (click hold | u undo | s skip | q quit)"
        cv2.putText(canvas, header, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 2)
        if clicked:
            px, py = clicked[-1]
            dp = (int(px * scale), int(py * scale))
            cv2.drawMarker(canvas, dp, (0, 0, 255), cv2.MARKER_CROSS, 24, 2)
            cv2.putText(canvas, "ENTER/SPACE = confirm (re-click to adjust)",
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow(WINDOW, canvas)

    def on_mouse(event: int, x: int, y: int, *_ignored) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked.append((int(x / scale), int(y / scale)))
            redraw()

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)
    redraw()

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            return "quit", None
        if key == ord("s"):
            return "skip", None
        if key == ord("u") and clicked:
            clicked.clear()
            redraw()
        # clicks move the marker; Enter or Space confirms it
        if clicked and key in (13, 10, ord(" ")):
            x, y = clicked[-1]
            return "set", [x, y]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--takes-dir", type=Path, default=DEFAULT_TAKES_DIR)
    parser.add_argument("--frame", type=int, default=0,
                        help="frame index to show for each clip")
    parser.add_argument("--display-height", type=int, default=1000,
                        help="window height on screen (coords stay full-res)")
    parser.add_argument("--redo", nargs="*", default=[],
                        help="re-click these filenames even if already set")
    args = parser.parse_args()

    takes_path = args.takes_dir / "takes.csv"
    anchors_path = args.takes_dir / "anchors.json"
    if not takes_path.exists():
        print(f"missing {takes_path} — set up exp02 first")
        return 1

    takes = pd.read_csv(takes_path)
    filenames = takes[takes["group"].isin(ANALYSIS_GROUPS)]["filename"].tolist()
    data = load_anchors(anchors_path)
    anchors = data["anchors"]

    todo = [f for f in filenames if f in args.redo or f not in anchors]
    if not todo:
        print(f"all {len(filenames)} takes already have anchor entries in "
              f"{anchors_path.name} (use --redo <filename> to re-click)")
        return 0
    print(f"{len(todo)} take(s) to click; click the SAME physical hold in "
          "each, then ENTER/SPACE to confirm.")

    for i, filename in enumerate(todo):
        action, px = pick_one(args.takes_dir / filename, args.frame,
                              args.display_height, f"[{i + 1}/{len(todo)}]")
        if action == "quit":
            break
        if action == "unreadable":
            continue
        anchors[filename] = ({"frame": args.frame, "px": px}
                             if action == "set" else None)
        save_anchors(anchors_path, data)
        print(f"  {filename}: {anchors[filename] or 'skipped (null)'}")
    cv2.destroyAllWindows()

    n_set = sum(1 for f in filenames if anchors.get(f))
    n_null = sum(1 for f in filenames if f in anchors and anchors[f] is None)
    print(f"\n{anchors_path.name}: {n_set} anchored, {n_null} skipped, "
          f"{len(filenames) - n_set - n_null} missing (of {len(filenames)} takes)")
    if data["hold_comment"].startswith("FILL IN"):
        print("remember to fill in hold_comment (which hold you clicked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
