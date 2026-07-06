"""Layer 2 metrics: pure functions over pose landmarks. THE durable asset.

Rules for this module (per CLAUDE.md):
- Pure functions only: no I/O, no pandas, no model objects. Plain floats and
  (x, y) tuples in, floats out. Nothing here may import from layer 1 or 3.
- Every function is specified precisely enough to port to TypeScript verbatim;
  the two implementations stay in lockstep via shared-fixtures/metrics.json.
- Unit-agnostic: coordinates in = units out (pass pixels, get pixels; pass
  normalized, get normalized). Unit conversion is the caller's job.

Coordinate convention: image coordinates, y increases DOWNWARD (as produced by
MediaPipe/ViTPose). "Height" therefore means (reference_y - y), with the
reference typically the bottom edge of the frame.

Degenerate inputs (zero-length references) return NaN rather than raising:
downstream layers must treat NaN as "not computable" and drop the metric.
"""

from __future__ import annotations

import math

Point = tuple[float, float]


def midpoint(a: Point, b: Point) -> Point:
    """Point halfway between a and b."""
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def distance(a: Point, b: Point) -> float:
    """Euclidean distance between a and b."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def height_above(y: float, reference_y: float) -> float:
    """Vertical height of y above reference_y in y-down image coordinates.

    Positive when y is visually ABOVE the reference. Typical reference:
    the frame's bottom edge (image height in px, or 1.0 normalized).
    """
    return reference_y - y


def hip_center(left_hip: Point, right_hip: Point) -> Point:
    """Midpoint of the two hip landmarks (BlazePose 23, 24)."""
    return midpoint(left_hip, right_hip)


def shoulder_center(left_shoulder: Point, right_shoulder: Point) -> Point:
    """Midpoint of the two shoulder landmarks (BlazePose 11, 12)."""
    return midpoint(left_shoulder, right_shoulder)


def hip_height(left_hip: Point, right_hip: Point, reference_y: float) -> float:
    """Height of the hip center above reference_y (y-down convention)."""
    return height_above(hip_center(left_hip, right_hip)[1], reference_y)


def torso_length(
    left_shoulder: Point,
    right_shoulder: Point,
    left_hip: Point,
    right_hip: Point,
) -> float:
    """Distance from shoulder center to hip center.

    The default morphology-relative denominator: unlike stature or reach it
    is measurable in nearly every frame (Test 1: hips/shoulders are the
    reliably-tracked keypoints) and is invariant to limb pose.
    """
    return distance(
        shoulder_center(left_shoulder, right_shoulder),
        hip_center(left_hip, right_hip),
    )


def relative_to(value: float, reference: float) -> float:
    """value as a fraction of reference; NaN if reference is 0."""
    if reference == 0.0:
        return math.nan
    return value / reference


def cm_per_px(known_cm: float, measured_px: float) -> float:
    """Scale factor from a known real-world length and its pixel length.

    Serves both calibration methods identically: known climber height vs
    clicked head-to-floor pixel extent, and known hold spacing vs clicked
    hold-to-hold pixel distance. NaN if measured_px is 0.
    """
    if measured_px == 0.0:
        return math.nan
    return known_cm / measured_px
