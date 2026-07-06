# exp02 run 2 — hold anchor (variant D): the anchor works, the top-row hold and the ratio form are now the bottlenecks

_Generated 2026-07-06. Companion to the regenerated `summary.md` (run 2) and
sequel to `findings-anchor.md` (run 1, frozen in `run1-ankle-anchor/`).
Anchors: one click per take on the purple top-row hold (`anchors.json`,
30/30 takes). Overlay QA on sr1-1/2/3 confirms the clicks landed on the same
hold and shows visibly large perspective differences between tripod re-sets,
especially sr1-3._

## What the hold anchor fixed (measured)

- **Camera re-set translation is absorbed.** static-reset between-take std:
  variant A (frame-anchored) 28.7 px → variant D (hold-anchored) **9.8 px**.
- **Movement repeatability is rescued on exactly the takes the ankle lost.**
  Peak hip height pooled within-move: variant B 142.7 px on df 6 (half the
  takes gated) → variant D **12.3 px on df 12** (all 18 takes usable,
  including the heel-hook move m3, where B was semantically broken, and the
  occluded-feet moves m2/m5).
- Click repeatability is a minor term: static-fixed cross-check std_D
  15.4 px vs std_A 14.2 px with the camera untouched (≈ 5–6 px of click noise
  in quadrature, small against the re-set residual).

## What still fails, and why

**Criterion 1 (per-frame D/torso, static-reset, ≤ 2 % torso): 8.04 % → FAIL.**
Two separable causes, both measured:

1. **The ratio construction doubles the noise.** std_D_px = 9.8 px is
   **4.4 %** of the ~220 px torso; the D/torso ratio is **8.0 %**. The anchor
   hold sits ~2.6 torso-lengths above the hips, so torso-length variation
   between re-sets (217.3 → 220.9 → 223.8 px, ± 1.5 % — apparent length
   changes with perspective) is amplified by |D|/torso. Measured
   corr(|D|, torso) = **−0.90** across the three re-sets: the errors
   anti-correlate, so dividing makes it worse, not better. (Constructing the
   ratio per-frame vs per-take-median makes no difference: 8.04 % vs 8.15 %.)
2. **The remaining 4.4 % is geometry residual on a long lever arm.** A
   single-point anchor corrects translation only. The overlay QA shows real
   rotation/scale/perspective differences between re-sets, and the top-row
   hold is ~575 px from the hips, so ~1–2 % scale or ~1° roll moves D by
   ~6–12 px. Body re-positioning is bounded by variant C on the same takes
   (clean ankles, body-anchored): 2.06 % ≈ 4.5 px — so roughly half of D's
   9.8 px is the camera chain, not the climber.

For contrast, the same movement-peak data normalized ONCE per take
(peak D_px ÷ take-median torso) pools to **2.72 % torso (df 12)** vs 10.5 %
for the per-frame ratio form — the ratio form, not the anchor, is the bigger
lever there.

## Conclusion

The world-fixed anchor concept is validated: it absorbs camera re-sets,
survives every body position, and has no semantic failure modes. The units
decision is still open, but the remaining noise is now attributable to two
specific, cheap-to-attack choices — anchor placement and normalization form —
not to pose quality (hips held at ~14 px all along).

## Cheapest next experiments (in order)

1. **Re-click the anchor onto a hold near the working zone** (hip/chest
   height, near the climber) — minutes with
   `uv run lab/pick_anchors.py --redo <files>`. Geometry residual scales with
   anchor→hip distance; cutting the lever from ~575 px to ~150 px predicts
   std_D_px ≈ 3–5 px ≈ 1.5–2 % torso. If the prediction holds, the hypothesis
   is confirmed and the floor is at the bar; if not, the residual is
   rotation-dominated and two-point anchoring (scale+rotation correction) is
   next.
2. **Normalize once per take, not per frame**: report D_px ÷ take-median
   torso as the relative form (and peak-D_px ÷ take-median torso for moves).
   Already supported by this run's numbers (8.0 % → 4.4 % static,
   10.5 % → 2.7 % movement). Requires a small metric-definition change —
   decide before the next run so criterion 1 is stated up front, not fitted
   to the data.
3. More static-reset takes. All static-reset stds here sit on **df = 2**; a
   pass/fail read at the 2 % bar deserves df ≥ 5 before the units decision is
   final.

Calibration (criterion 2) remains unevaluated — `calibration.json` in
progress, feeds the absolute-cm question only.
