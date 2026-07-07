# Lab decisions log

Cross-cutting decisions that came out of the experiments, recorded so they
aren't re-litigated. Append-only; each entry states the decision, the date, the
evidence, and what it does/doesn't commit. Experiment detail lives in the
`results/<experiment>/findings*.md` files referenced.

---

## D1 — Insight units: RELATIVE (fraction of torso length). 2026-07-07

**Decision.** The product reports position/scale metrics as a fraction of the
climber's own **torso length** (shoulder-center to hip-center), normalized
**once per attempt** (per-take median), e.g. "your hips peaked ~8% of torso
higher on the send." Absolute centimeters are **not** the shipping unit.
Closes Test 2's absolute-cm-vs-relative decision point.

**Evidence (four independent reasons, any one sufficient; together decisive):**

1. **Morphology-invariance.** A fraction of torso means the same proportional
   thing for a tall and a short climber, with no per-user calibration step.
2. **Outdoor-forcing.** On real rock there is no known scale reference, so
   absolute cm is unrecoverable there; relative units work identically on
   plywood and granite, which the board→outdoor path requires.
3. **Perspective non-uniformity.** A single pixels→cm factor is wrong by
   geometry on an oblique/overhung wall (perspective foreshortening makes
   scale vary across the frame). exp03 confirmed the effect is large enough
   that registering two views needed a full **homography** — a similarity
   (uniform scale + rotation) was insufficient (8 px vs 2 px residual). See
   [results/exp03-registration/findings.md](results/exp03-registration/findings.md).
4. **Noise-floor viability.** The measurement floor for a hip-height delta is
   ~1.6% of torso (1σ) → **2σ ≈ 3.3% of torso** (≈ ~1.6 cm on a ~50 cm torso).
   The insights the product wants to make (~8 cm ≈ 16% of torso) clear that by
   ~5×. See [results/exp02-noise-floor/findings-hold-anchor.md](results/exp02-noise-floor/findings-hold-anchor.md).

**What this commits.** Insight language, the metrics layer's output units, and
confidence/ranking are all built on relative units. Minimum honestly-reportable
difference for a hip-height delta = **2σ ≈ 3.3% torso**; deltas below it are
reported as "no measurable difference" (a valid result per the honesty
principles). Ranking = observed delta ÷ this floor.

**What it does NOT commit.** Absolute cm is not forbidden — it's deferred. If it
is ever wanted (most likely on a standardized board), the correct method is a
**homography onto the known hold grid** (accurate cm anywhere on the wall), not
a single clicked scale factor. `footage/exp02/calibration.json` was
deliberately left as an unfilled template: Criterion 2 (do single-scale methods
agree ≤5%?) was not run because it cannot change this decision and the
perspective geometry already implies the methods will disagree. See the
handoff note in [results/exp02-noise-floor/](results/exp02-noise-floor/).

---

## D2 — Cross-attempt coordinate frame: automatic background homography registration. 2026-07-07

**Decision.** To compare two attempts, register them into one wall-fixed
coordinate frame by **automatic background feature matching** (SIFT/ORB
features on the wall with the climber masked out → RANSAC homography). This is
the Layer-1 coordinate backbone for all cross-attempt position metrics.

**Evidence.** exp03, on tripod-re-set takes: homography registers the wall
plane to **~2 px (≈1% torso), matching the same-camera control (~1.9 px)** —
i.e. as accurate as not moving the camera, and ground-truth-limited (the
registration's own error is ~0.7 px). Translation-only (20 px at distance) and
similarity/two-tap schemes (8 px) fail because tripod re-sets change
perspective. See [results/exp03-registration/findings.md](results/exp03-registration/findings.md).

**Consequences.**
- **Registration subsumes anchoring for diff mode.** Once two attempts share a
  frame, the hip-height difference is a direct coordinate subtraction — **zero
  user taps**. A clicked anchor is only needed to phrase a *single* attempt
  against a named wall landmark ("hips above the start hold"), not for the
  attempt-vs-attempt deltas that are the product's core.
- Works identically outdoors (rock texture is ideal for feature matching) and
  stays inside the legal guardrail (user's own footage only).
- **Static-hold repetition overstates the pipeline's noise floor**: its spread
  is dominated by *body reproduction* (the climber not re-holding a position to
  the cm), which is product **signal** (the diagnosis-mode "beta settled?"
  metric), not measurement error. The measurement floor (D1) is ~1.6% torso;
  the raw static spread (3–6%) is mostly the climber.

**Open / caveats.**
- Intra-take camera drift: takes filmed right after handling the tripod drift
  2.9–7.2 px over the first seconds (mount settling / phone EIS); untouched
  takes hold <1 px. → **Filming guidance: pause a beat after touching the
  phone**; register at the analysis frame rather than assuming a clip is rigid.
- Static-reset repeatability estimates rest on df=2 (3 takes). More
  static-reset takes (and a few phone-removed-and-reseated takes — the product's
  real perturbation) would firm up the numbers, though registration already
  clears the bar.
