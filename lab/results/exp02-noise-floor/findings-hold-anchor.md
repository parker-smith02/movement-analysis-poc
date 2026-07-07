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

For contrast, the movement-peak **px** measurement itself is repeatable:
12.3 px pooled ≈ **2.6 %** of the movement group's median torso (equivalently
2.72 % when normalized by one torso shared within each move). But every
honest per-take denominator inherits the amplification: per-frame ratio
10.5 %, per-take median ratio **9.1 %**. (Correction 2026-07-07: an earlier
version of this paragraph attributed 2.72 % to per-take normalization — that
figure used a shared within-move denominator, which the product does not have
across camera setups.) The denominator error × |D|/torso term, i.e. the
anchor distance, dominates all ratio forms.

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
   DONE and pre-registered 2026-07-07 (criterion 1 restated in the script
   docstring before the near-anchor data exists). Measured on the top-row
   anchor it changes little by itself (static-reset 8.04 % → 8.15 %, movement
   10.5 % → 9.1 %) — as expected, since torso error × |D|/torso dominates
   both forms at this anchor distance. It is kept because it is the form the
   product would ship (one scale per attempt) and it removes per-frame
   foreshortening noise once the amplification term shrinks.
3. More static-reset takes. All static-reset stds here sit on **df = 2**; a
   pass/fail read at the 2 % bar deserves df ≥ 5 before the units decision is
   final.

Calibration (criterion 2) remains unevaluated — `calibration.json` in
progress, feeds the absolute-cm question only.

---

# run 3 — near-hip anchor: the lever-arm hypothesis is confirmed, floor halved, still ~3 %

_Generated 2026-07-07. Anchor re-clicked to a near-hip working-zone hold
(`run3-near-anchor/anchors-near.json`), per-take median relative form (the
form pre-registered in run 2 before these clicks existed). Frozen in
`run3-near-anchor/`._

## What moving the anchor did (measured)

| quantity | top-row anchor (run 2) | near-hip anchor (run 3) |
|---|---|---|
| static-reset D/torso (df 2) | 8.15 % | **3.18 %** |
| static-reset std_D_px | 9.8 px | **7.0 px** |
| movement peaks D/torso (df 12) | 9.1 % | **3.63 %** |
| anchor→hip distance, static (in torsos) | ~2.6 | **~0.03** |

**The amplification mechanism is confirmed and removed.** With the anchor
essentially at hip height (|D|/torso = 0.02–0.04 on the static-reset takes),
the ratio floor (3.18 %) now equals the px floor (std_D_px 7.0 px ÷ 220 px
torso = 3.17 %) — the torso-error × |D|/torso term that inflated run 2 to 8 %
has collapsed. corr(|D|, torso) is still −0.99 but |D| is now tiny, so it no
longer matters. The relative floor roughly halved on both static and movement.

## Why it still doesn't clear 2 %, and what the residual is

The remaining floor is **camera-re-set rotation/scale residual**, and this run
isolates it cleanly. On the same clean-ankle static-reset takes:

- ankle-anchored (variant B, body-fixed): **3.1 px**
- hold-anchored (variant D, world-fixed): **7.0 px**

The ankle is a *body*-fixed anchor: when the tripod is re-set and the camera
rotates slightly, hips and ankle shift together and the difference survives.
The hold is *world*-fixed, so that same camera rotation shows up as noise a
single-point (translation-only) anchor cannot remove. The 7.0 px on
static-reset is therefore a direct measurement of the tripod-re-set residual —
exactly the thing "don't move the camera between attempts" filming guidance
eliminates. (Movement's 3.63 % is slightly worse than static's 3.18 % because
some moves still peak up to ~0.9 torso from the anchor — see per-move
|Dpeak|/torso in the diagnostics; move5/move6 with the closest anchors are the
tightest.)

## What this means for the units decision

The honest floor with a good world-fixed anchor is **~3.2 % (static, df 2) to
3.6 % (movement, df 12) of torso length**, i.e. a minimum honestly-reportable
hip-height difference of **2σ ≈ 6–7 % of torso ≈ ~3.5 cm** for a ~50 cm torso.
The headline insights the product wants to make ("hips 8 cm higher" ≈ 16 % of
torso) sit comfortably above this — **>2σ with margin** — so relative units
are viable for the target insights even though the aspirational 2 % bar was
not met. Two regimes to state explicitly in the product:

- **Within one camera setup** (tripod untouched — the core compare-attempts
  case, backed by filming guidance): no cross-setup residual; variant A alone
  is enough and the floor is tighter.
- **Across camera setups / sessions**: ~3.2 % floor with a near anchor. To go
  below 2 % here needs a **two-point anchor** (correct scale + rotation, not
  just translation) — the last cheap engineering lever.

## Open items before the units decision is final

1. **df = 2 on static-reset.** The 3.18 % rests on 3 takes; movement's 3.63 %
   (df 12) is the more trustworthy number and agrees. Still worth ≥ 5
   static-reset takes for a firm pass/fail.
2. **Two-point anchor** — the one remaining lever to clear 2 % across setups.
   Second click per take on a well-separated wall feature; recover a similarity
   transform (scale + rotation + translation) instead of translation-only.
3. Calibration (criterion 2) still unevaluated — feeds absolute-cm only.
