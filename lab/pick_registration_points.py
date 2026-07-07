"""Click K corresponding holds per take for exp03 (registration accuracy).

Feeds exp03_registration.py: in EACH take, click the SAME K distinctive
holds IN THE SAME ORDER (order defines the correspondence). Pick holds that
are well spread across the frame — corners of the wall region plus one or
two in the working zone — so similarity/homography fits are well-conditioned
and the evaluation covers the area that matters.

Defaults to the six pos1 takes exp03 analyzes (sf1-1..3, sr1-1..3) and K=5.
Saves after every take; re-running resumes at missing takes.

Usage:
    uv run lab/pick_registration_points.py                 # missing takes
    uv run lab/pick_registration_points.py --points 6
    uv run lab/pick_registration_points.py --redo-all      # re-click all

Keys: left-click = add next point (numbered), u = remove last point,
ENTER/SPACE = confirm take (needs all K points), s = skip take,
q/ESC = quit (progress saved).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).parent.parent
TAKES_DIR = ROOT / "footage" / "exp02"
OUT_PATH = TAKES_DIR / "registration_points.json"
DEFAULT_TAKES = ["sf1-1.MOV", "sf1-2.MOV", "sf1-3.MOV",
                 "sr1-1.MOV", "sr1-2.MOV", "sr1-3.MOV"]
WINDOW = "pick_registration_points"


def read_frame(clip: Path, frame_idx: int):
    cap = cv2.VideoCapture(str(clip))
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def pick_take(clip: Path, k: int, frame_idx: int, display_height: int,
              progress: str) -> tuple[str, list[list[int]] | None]:
    frame = read_frame(clip, frame_idx)
    if frame is None:
        print(f"  cannot read frame {frame_idx} from {clip.name}")
        return "unreadable", None

    h, w = frame.shape[:2]
    scale = min(1.0, display_height / h)
    disp_size = (int(w * scale), int(h * scale))
    pts: list[list[int]] = []

    def redraw() -> None:
        canvas = cv2.resize(frame, disp_size)
        header = (f"{progress}  {clip.name}  point {min(len(pts) + 1, k)}/{k}"
                  "  (u undo | s skip | q quit)")
        cv2.putText(canvas, header, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 2)
        for i, (px, py) in enumerate(pts):
            dp = (int(px * scale), int(py * scale))
            cv2.drawMarker(canvas, dp, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
            cv2.putText(canvas, str(i + 1), (dp[0] + 8, dp[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        if len(pts) == k:
            cv2.putText(canvas, "ENTER/SPACE = confirm take", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow(WINDOW, canvas)

    def on_mouse(event: int, x: int, y: int, *_ignored) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(pts) < k:
            pts.append([int(x / scale), int(y / scale)])
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
        if key == ord("u") and pts:
            pts.pop()
            redraw()
        if len(pts) == k and key in (13, 10, ord(" ")):
            return "set", pts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--takes", nargs="*", default=DEFAULT_TAKES)
    parser.add_argument("--points", type=int, default=5)
    parser.add_argument("--frame", type=int, default=0)
    parser.add_argument("--display-height", type=int, default=1000)
    parser.add_argument("--redo-all", action="store_true")
    args = parser.parse_args()

    data = (json.loads(OUT_PATH.read_text()) if OUT_PATH.exists()
            else {"comment": "K holds per take, same holds in the same order",
                  "points_per_take": args.points, "takes": {}})
    if data.get("points_per_take") not in (None, args.points) and not args.redo_all:
        print(f"existing file has K={data['points_per_take']}; rerun with "
              f"--points {data['points_per_take']} or --redo-all")
        return 1
    data["points_per_take"] = args.points

    todo = [t for t in args.takes
            if args.redo_all or t not in data["takes"]]
    if not todo:
        print(f"all {len(args.takes)} takes present in {OUT_PATH.name} "
              "(--redo-all to re-click)")
        return 0
    print(f"{len(todo)} take(s); click the SAME {args.points} holds in the "
          "SAME ORDER in each, then ENTER/SPACE.")

    for i, take in enumerate(todo):
        action, pts = pick_take(TAKES_DIR / take, args.points, args.frame,
                                args.display_height, f"[{i + 1}/{len(todo)}]")
        if action == "quit":
            break
        if action in ("unreadable", "skip"):
            continue
        data["takes"][take] = pts
        OUT_PATH.write_text(json.dumps(data, indent=2) + "\n",
                            encoding="utf-8")
        print(f"  {take}: {pts}")
    cv2.destroyAllWindows()
    print(f"\n{OUT_PATH.name}: {len(data['takes'])}/{len(args.takes)} takes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
