# exp03 findings — auto-registration solves the camera problem; the lab floor was measuring the climber, not the pipeline

_Generated 2026-07-07. Companion to the auto-generated `summary.md`. New to
the CV/measurement terms below (registration, homography, parallax, noise
floor, 2σ)? See the primer at [`lab/CONCEPTS.md`](../../CONCEPTS.md)._
Data: the six pos1 takes (sf1 = tripod untouched, sr1 = tripod re-set), two
known hold correspondences per take reused from the frozen exp02 anchor sets,
SIFT features with the climber masked out via the exp02 landmarks._

## Result 1 — zero-tap homography registration works; similarity does not

Median |dy| at held-out clicked probe holds, re-set pairs:

| method | median | as % torso (219 px) |
|---|---|---|
| translation-1pt (exp02 variant D) | 20.5 px | 9.4 % |
| auto-similarity (zero taps) | 8.2 px | 3.7 % |
| **auto-homography (zero taps)** | **2.23 px** | **1.02 %** |

- **Similarity fundamentally fails** (8 px): the tripod re-sets change
  *perspective*, and two views of a plane are related by a homography, not a
  similarity. This kills the "two taps" product option — it would inherit the
  same error class. It's homography or nothing, and homography needs 4+ taps
  or zero (automatic). Automatic wins.
- Translation's 20.5 px is measured at probes ~580 px from the fit point —
  vs exp02 run 3's 7 px at ~30 px distance. Same lever-arm law, now measured
  at two distances.
- The 2.23 px pooled median **narrowly misses the pre-stated 2 px bar**, but
  splits tellingly by probe: **1.14 px at the top-row hold, 4.08 px at the
  near-hip hold**. Protruding holds are poor ground truth — their apparent
  center shifts with viewpoint (the homography maps the wall *plane* exactly;
  a hold sticks out of it), and the near hold's own click/parallax error was
  also inside exp02 run 3's 7 px floor. True wall-plane registration accuracy
  is likely the ~1 px number. K=5 clicks including **flat on-plane features
  (bolt holes, plywood seams, chalk marks)** would settle it —
  `uv run lab/pick_registration_points.py`.
- Robustness: the worst pair (sr1-1↔sr1-3, biggest camera move, only 771
  features / 42 RANSAC inliers) still produced a usable homography — wall
  region aligns to a few px in `qa/warpdiff_sr1-1_sr1-3.png` (climber ghosts
  because he is off-plane; floor/mats misalign because they are off-plane;
  both expected and harmless).

## Result 2 — the end-to-end "floor" exposes a protocol limit, not a pipeline limit

Recomputing the exp02-style relative hip floor over all six takes
(same static position, so nominally true-delta-zero, df=5):

- uncorrected (per-take near anchor): std **6.27 %** torso
- homography-corrected (one coordinate frame, zero taps): std **6.31 %**

Correction changed nothing — because the spread is not camera error. The
per-take values show sf1-1 as a massive outlier (−0.127 vs ±0.04 for the
rest) **with the tripod untouched and no registration involved**: the climber
simply held the position ~6 cm lower in that take. Registration cannot and
should not "fix" that.

**Implication for how we read every noise-floor number so far:** the
static-hold-repetition protocol conflates two very different things —

1. **measurement error** (registration + pose + click): bounded by this
   experiment at roughly `sqrt(2² + 3²) ≈ 3.6 px ≈ 1.6 %` torso (2σ ≈ 3.3 %),
   where ~2 px is registration (probe-measured, likely closer to 1 px) and
   ~3 px is the pose+body-relative bound from exp02's variant B;
2. **body reproduction** (the climber cannot re-hold a position to a few cm
   across takes): 3–6 % torso in this data, dominating every static between-
   take std — exp02 run 3's 3.18 % (three takes with luckily-tight
   reproduction) and this 6.3 % (six takes including one settling-in outlier)
   are both mostly *climber*, not *pipeline*.

In the product, (2) is not noise — it is exactly the signal being reported.
The honest minimum reportable difference should be set by (1). Wall-probe
evaluation (this experiment's method) is the right instrument for (1);
static-hold repetition cannot separate the two and systematically
overstates the floor.

## Product architecture consequence (the big one)

**Registration subsumes anchoring for diff mode.** Once two attempts are in
one wall-fixed coordinate frame via automatic background homography, the
hip-height difference between attempts is a direct coordinate difference —
**no anchor tap needed at all, zero user input**. The clicked anchor is only
needed when a single attempt's position must be expressed against a wall
landmark ("hips above the start hold"), not for attempt-vs-attempt deltas —
the product's core interaction. This also aligns with the outdoor story
(rock texture is ideal for feature matching) and stays within the legal
guardrail (user's own footage only).

## Status vs the pre-stated pass criterion

Median |dy| ≤ 2 px (re-set pairs, corrected method): **2.23 px → narrow FAIL
as pooled**, 1.14 px at the clean probe → PASS-shaped. Verdict: registration
is solved to ~1 % torso pending confirmation with flat-feature probes; the
2 % criterion-1 bar is met for *measurement* error (2σ ≈ 3.3 % total incl.
pose, ≈ 2 % excl. the body-relative component the product counts as signal).

## Recommended next steps

1. Parker (5 min): `uv run lab/pick_registration_points.py` — K=5 per pos1
   take, mixing **2 flat on-plane features** with 3 spread holds; re-run
   exp03 to confirm the ~1 px registration read and get held-out
   similarity-2pt numbers for the record.
2. Fold auto-homography registration into the metrics pipeline as the
   coordinate backbone for cross-take comparison (this is Layer-1/2 plumbing;
   the pure metric functions are unchanged).
3. When next filming: a few takes with the **phone removed and re-seated**
   (the product's actual perturbation), and — for measuring body
   reproduction as its own signal — accept that static-hold repetition
   measures the climber, and use wall probes to measure the pipeline.

---

# Update — K=7 probes, the mask bug, and the intra-take drift discovery (2026-07-07, second pass)

Parker clicked 5 registration points per pos1 take (one take re-clicked after
a correspondence-order slip was caught by cross-take consistency checking).
With 7 probes the evaluation surfaced two instrumentation problems, both now
fixed in the script, and one genuinely new finding.

## Fix 1 — the person mask was eating half the wall on two takes

The mask was built from the *first detected frame's* landmark bbox. On takes
where the climber was still walking in at frame 0, the scattered landmarks
bloated the mask to **57 % of the frame** (sf1-1, sr1-3 — measured), starving
SIFT (771 features on sr1-3 vs ~2 500 elsewhere) and degrading exactly the
pairs that involved those takes. Fixed: the mask now uses each landmark's
**median position over the take**, robust to walking-in frames. Feature
counts: all takes now 1 800–2 900.

## New finding — the camera is not static *within* a take

Registering each take's frame 0 to its own middle frame (identity if truly
static):

| take | tripod | drift |
|---|---|---|
| sf1-1/2/3 | untouched | 0.4–0.8 px |
| sr1-2, sr1-3 | just re-set | 2.9, 3.6 px |
| sr1-1 | just re-set | **7.2 px** |

Takes recorded right after the tripod was handled **settle/drift several px**
over the first seconds (mount settling and/or phone stabilization); untouched
takes hold sub-pixel. Three consequences:

1. **Frame consistency is mandatory.** Frame-0 clicks vs mid-take
   measurements are different geometries. The script now evaluates probes at
   frame 0 (where the clicks live) and computes the end-to-end floor with
   mid-take homographies (where the hip medians live). Mixing them injected
   up to 34 px of phantom error in an intermediate run.
2. **exp02's static-reset floor partly measured this drift**, not cross-setup
   error: its frame-0 anchors were compared against mid-take hip medians, so
   each take carried its own 2.9–7.2 px internal drift — the same order as
   the 7 px floor itself. The cross-setup story was better than reported.
3. **Product/filming guidance:** wait a few seconds after handling the phone
   before the attempt, and/or register at the analysis frame rather than
   assuming within-clip rigidity. Cheap either way.

## Final frame-consistent numbers (K=7 probes, re-set pairs)

| method | median &#124;dy&#124; | same-setup control |
|---|---|---|
| translation-1pt | 7.00 px | 2.00 px |
| similarity-2pt (clicked, held-out) | 6.07 px | 4.00 px |
| auto-similarity | 5.59 px | 1.91 px |
| **auto-homography** | **2.02 px** | **1.90 px** |

- **Registration across tripod re-sets is now as accurate as no camera move
  at all**: 2.02 vs the 1.90 px same-setup control. The control measures the
  evaluation's own ground-truth noise (click precision + hold parallax), so
  the registration's *own* contribution is ~`sqrt(2.02² − 1.90²)` ≈
  **0.7 px** — the evaluation is ground-truth-limited, as predicted.
- The pre-stated criterion (median ≤ 2 px) reads **2.02 px → FAIL by the
  letter, by 0.02 px against a control of 1.90** — substantively met; stated
  plainly rather than rounded.
- similarity-2pt confirmed dead with real held-out data (6.07 px median,
  p95 27 px) — matching the structural argument.

## End-to-end floor, revisited

All-six-takes floor: uncorrected 6.27 %, corrected 6.17 % — still dominated
by the sf1-1 body-position outlier (present under both methods, camera
untouched; the climber, not the pipeline). Sensitivity check, clearly
labelled post-hoc: excluding sf1-1, the **corrected** floor is **1.93 %
torso (df 4)** vs uncorrected 3.08 % — the first end-to-end sighting of a
**sub-2 % cross-setup floor**, consistent with the probe-based error budget
(reg ~1–2 px ⊕ pose ~3.1 px ≈ 1.7 % torso).

## Bottom line (unchanged, strengthened)

Zero-tap homography registration reduces cross-camera error to ~1 px on the
wall plane — below the evaluation's own ground-truth resolution. The
pipeline's honest measurement floor is set by pose precision (~3 px), giving
2σ ≈ 3.3–3.4 % torso today, with the end-to-end sensitivity check touching
1.9 % (1σ). Registration is solved; the remaining lever is the pose model.
