"""Click points on a video frame to measure pixel distances (calibration aid).

Opens one frame of a clip, lets you click points, and prints full-resolution
pixel coordinates plus the distance between each consecutive pair. Use it to
measure the two calibration references for exp02:
  - head-top and floor points of the standing climber  -> person_extent
  - two hold centers a known distance apart            -> hold_pair
Paste the printed coordinates into footage/exp02/calibration.json.

Usage:
    uv run lab/pick_points.py footage/exp02/calibration.mov [--frame 30]

Keys: left-click = add point, u = undo last, q/ESC = finish and print.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

import metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clip", type=Path)
    parser.add_argument("--frame", type=int, default=0)
    parser.add_argument("--display-height", type=int, default=1000,
                        help="window height on screen (coords stay full-res)")
    args = parser.parse_args()

    cap = cv2.VideoCapture(str(args.clip))
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        print(f"cannot read frame {args.frame} from {args.clip}")
        return 1

    h, w = frame.shape[:2]
    scale = min(1.0, args.display_height / h)
    disp_size = (int(w * scale), int(h * scale))
    points: list[tuple[int, int]] = []

    def redraw() -> None:
        canvas = cv2.resize(frame, disp_size)
        for i, (px, py) in enumerate(points):
            dp = (int(px * scale), int(py * scale))
            cv2.circle(canvas, dp, 6, (0, 0, 255), -1)
            cv2.putText(canvas, str(i + 1), (dp[0] + 8, dp[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow("pick_points", canvas)

    def on_mouse(event: int, x: int, y: int, *_ignored) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((int(x / scale), int(y / scale)))
            redraw()

    cv2.namedWindow("pick_points")
    cv2.setMouseCallback("pick_points", on_mouse)
    redraw()
    print(f"{args.clip.name} frame {args.frame} ({w}x{h}); "
          "click points, u = undo, q/ESC = finish")

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("u") and points:
            points.pop()
            redraw()
    cv2.destroyAllWindows()

    for i, p in enumerate(points):
        print(f"point {i + 1}: [{p[0]}, {p[1]}]")
    for i in range(len(points) - 1):
        d = metrics.distance(points[i], points[i + 1])
        print(f"distance {i + 1}->{i + 2}: {d:.1f} px")
    return 0


if __name__ == "__main__":
    sys.exit(main())
