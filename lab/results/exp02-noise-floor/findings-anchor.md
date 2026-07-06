# exp02 — first real-footage run: the ankle anchor is the bottleneck, not the hips

_Generated 2026-07-06. Companion to the auto-generated `summary.md`. Overlay
QA on four diagnostic clips explains why variants B/C (ankle-anchored hip
height) blow up while variant A (hips vs. a fixed frame reference) stays tight._

## What the numbers say

- Variant **A** (hip above frame bottom) between-take std, pooled within
  position: **14.2 px** (static-fixed), **28.7 px** (static-reset). Hips are
  tracked stably — consistent with Test 1.
- Variant **C** (hip ÷ torso, ankle-anchored) between-take std:
  **static-reset pos1 = 2.06 %** torso (2σ ≈ 4.1 %) — essentially at the 2 %
  target — but **static-fixed = 43 %**, and movement peak-C pooled = 17 %.
- The paradox (static-**fixed** worse than static-**reset**) is not about the
  camera. static-reset was a single extended position (pos1) with clean ankles
  (95–100 % of frames both-ankles ≥ 0.5). static-fixed pooled in pos2/pos3,
  compressed overhang positions where MediaPipe **loses the lower legs**.

## Ankle visibility drives the whole effect

| clip | position | both-ankles ≥0.5 | hipB median | verdict |
|------|----------|------------------|-------------|---------|
| sf1-3 | extended, static | 96 % | 51 px | ankle anchor valid |
| sf2-1 | compressed on 45° | **1.6 %** | 94 px (garbage) | lower legs collapsed to hip level |
| m3-1 | heel hook | 100 % | **−32 px** | pose correct, metric invalid (foot hooked high) |
| m2-1 | reaching, foot pushing off | 9.8 % | 938 px (garbage) | lower legs lost / occluded |

## Three distinct failure modes (all visible in the overlays)

1. **Compressed-pose collapse (sf2, sf3).** On the steep wall with knees tucked,
   the lower legs are foreshortened; MediaPipe places both ankles up at hip
   level (ankleY ≈ hipY). hip-above-ankle → ~0. This is a *pose-model* failure
   on exactly the body positions hard climbing produces.
2. **Heel-hook semantic break (m3).** Pose is tracked correctly, but with a foot
   hooked at hip height the ankle **midpoint** is no longer a floor-anchored
   reference, so hip-above-ankle goes negative. A metric-definition problem, not
   a tracking one.
3. **Reaching/occlusion (m2, m5).** Extended reaches with the generating foot
   pushing off out of clean view → ankles lost entirely (vis 0.00, m5 had 0
   usable ankle frames on 2 of 3 takes).

## Conclusion

The hip measurement is trustworthy (variant A). The **ankle midpoint is the
wrong wall anchor** on a mobile-class model over real climbing positions — it is
the least-reliable keypoint (Test 1) and is semantically wrong for hooks. So the
absolute-vs-relative units question is **not yet answerable**: the relative unit
we tested (C) inherits the ankle's noise.

## Cheapest next experiment

Re-anchor to a **fixed hold in frame** instead of the climber's ankle. A marked
hold does not occlude, does not foreshorten, and is visible head-on — it is a
true wall-fixed reference. calibration.json already captures hold pixel
coordinates; the extension is to locate one reference hold per clip (or per
camera setup) and recompute hip height above it. Secondary: gate B/C on a
minimum usable-ankle-frame count so a 9-frame median is never treated as equal
to a 700-frame one. See IDEAS.md hold-anchor note.
