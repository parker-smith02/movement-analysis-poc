# Feature ideas / use cases log

Product-level ideas captured during POC work, to keep in mind as implementation
deepens. Not commitments. Every idea must eventually survive the CLAUDE.md
honesty principles: observed differences only, nothing below the noise floor,
no unverifiable causal claims, physics limits respected.

Entry format: date, idea, what it could tell the climber, measurability notes
(which pipeline pieces it needs, expected confidence), status.

---

## 2026-07-06 — Hip/shoulder position at the latch moment

**Idea:** report the position of hips and shoulders at the exact frame the
reaching hand latches the target hold, compared across attempts.

**What it could tell the climber:**

1. **Deadpoint timing.** At a well-timed deadpoint the latch lands at the apex
   of the hip/COM arc (momentarily weightless). Hips still rising, or already
   dropping, at latch = mistimed. Cross-attempt diff: "on the send your hips
   were at their apex at latch; on the fails they had already dropped ~X% of
   torso length."
2. **Post-latch swing prediction.** Lateral hip offset from the remaining
   contact points at latch predicts the pendulum the latching hand must absorb.
   Explains the classic "I caught it but couldn't hold it" — the latch wasn't
   the failure, the position at latch made holding it impossible. Maps to
   diagnosis mode: positioning problem, not contact-strength problem.
3. **Reach economy / extension state.** Shoulder-to-hold distance at latch as a
   fraction of extended reach: latching at ~full extension on a bad hold is
   low-percentage; the usual fix is hips traveling further before the throw.
   Relative units by design (fits the units decision from Test 2).
4. **Shoulder elevation at latch.** Shrugged/elevated shoulder at the catch =
   poor scapular position, weaker latch (the developer's own validated coaching
   cue, applied at the single most loaded instant).
5. **Hips-to-wall at latch (steep terrain).** Hips sagged away from the wall at
   latch = more outward load on the latching hand. NOTE: depth from monocular
   side view — expect low confidence, label accordingly (CLAUDE.md v1 caveat).

**Measurability notes:**
- Position-at-a-frame is the pipeline's strongest regime (Test 1: hips/shoulders
  97-100% tracked; Test 2 measures the noise floor for exactly these deltas).
- Latch-moment detection is the hard part: candidate signal = reaching wrist
  deceleration to near-zero at the hold. Wrists are the weak keypoints (~50%
  low-confidence in Test 1) → POC fallback: user taps/scrubs to tag the latch
  frame; automate later.
- The latch frame is also a strong cross-attempt alignment anchor — feeds
  directly into Test 3 design (possibly better than "move initiation" for some
  moves, since it's sharply defined even when the setup varies).
- 1, 2, 4 are 2D side-on measurable with current landmarks; 3 needs a reach
  reference (calibration frame or per-climber reach estimate); 5 is the known
  low-confidence depth case.

---

## 2026-07-06 — Wall-anchored reference frame (anchoring) — POC and product

**Origin:** exp02 first real-footage run. Hip tracking is stable (variant A
between-take std 14 px within a fixed camera), but anchoring hip height to the
**ankle midpoint** failed three ways: compressed poses collapse the lower legs
(ankles drawn at hip level), heel hooks put the ankle above the hip (semantic
break), and reaches occlude the feet entirely. See
`lab/results/exp02-noise-floor/findings-anchor.md`.

**What anchoring is:** every absolute *position* metric (hip height, lateral
hip position) needs a reference fixed relative to the WALL so "hips 8% higher"
means higher on the wall, not higher in the camera frame. Three reference
classes: camera-fixed (frame edge — valid only while the tripod is untouched),
body-fixed (ankle — rejected above), world-fixed (hold / rock feature — the
durable one).

**How much the product actually needs it (three softenings):**
1. Many v1 metrics are anchor-free: shoulder-to-ear, joint angles,
   extension/compression, timing offsets, COM velocity/acceleration
   (frame-differenced). Only absolute-position metrics need an anchor.
2. Within one session, the camera frame IS a valid anchor (variant A, 14 px).
   Filming guidance ("tripod, don't move it between attempts") covers the core
   compare-attempts use case. World anchor is for cross-session comparison and
   camera bumps.
3. The anchor need not be "a hold" — it needs to be a trackable, wall-fixed
   image point.

**Outdoor answer:** rock is the EASY case for CV anchoring — texture (crystals,
chalk, lichen, cracks) is dense, rigid, static: ideal for feature matching.
Product-grade solution = background registration: match background features
between two clips (ORB/SIFT-class, on-device-capable), estimate the view
mapping, align coordinate systems wholesale. Subsumes "pick a hold"; identical
on plywood and granite; also absorbs small camera shifts. Fallback that always
works: user taps one distinctive point per camera setup (fits the board
beachhead: bright distinct holds; and the legal guardrail: user-provided
context only).

**Scale consequence:** outdoors there is no known hold spacing → no pixel→cm →
relative units are not just preferred there, they are FORCED. Aligns with the
existing relative-units preference and the board→outdoor path.

**POC implementation (variant D, cheap):** camera is static per take, so no
tracking needed — one clicked reference-hold pixel coordinate per take
(refined from "per camera setup": static-reset requires per-take clicks
anyway, and click repeatability is real product noise that belongs in the
measured floor); recompute hip height above it; also gate ankle-based
variants on a minimum usable-ankle-frame count (30 frames / 50% of core
frames — gated 14 of 30 takes). Status: implemented AND run 2026-07-06
(`lab/pick_anchors.py` + variant D in `lab/exp02_noise_floor.py`). Result:
anchor concept validated — camera re-set translation absorbed (28.7 → 9.8 px)
and movement-peak repeatability rescued on all 18 takes (142.7 → 12.3 px,
including heel hooks) — but run-2 criterion 1 still failed (8 % torso) because
the clicked hold was ~2.6 torso-lengths from the hips and the /torso ratio
amplifies that lever arm. Run 3 (2026-07-07) re-clicked a near-hip hold: the
amplification collapsed as predicted (ratio floor now equals px floor) and the
relative floor roughly halved — static-reset D/torso 8.15 % → **3.18 %**,
movement peaks 9.1 % → **3.63 %**. Still above the aspirational 2 % bar; the
residual is now isolated as camera-re-set rotation/scale (world-fixed hold
7.0 px vs body-fixed ankle 3.1 px on the same clean static-reset takes — a
single-point anchor corrects translation only). **Net product read:** with a
near anchor the honest floor is ~3–3.6 % torso, so 2σ ≈ ~3.5 cm; the target
insights (~8 cm ≈ 16 % torso) clear that with margin, so relative units are
viable. Two regimes to ship: within-camera-setup (tripod untouched → tighter,
variant A suffices) and cross-setup (~3.2 %, needs a two-point anchor to beat
2 %). See `lab/results/exp02-noise-floor/findings-hold-anchor.md` run-3
section. Remaining before a final call: more static-reset takes (df=2) and,
if cross-setup <2 % is wanted, a two-point (scale+rotation) anchor.

**exp03 update (2026-07-07): the background-registration idea above is now
measured and it wins.** Zero-tap SIFT+RANSAC homography registers re-set
takes to ~1–2 px on the wall plane (probe-evaluated); similarity (and hence
any 2-tap scheme) fails at ~8 px because tripod re-sets change perspective;
translation-only fails at distance (20 px at a 580 px lever). Two
consequences: (a) **registration subsumes anchoring for diff mode** — once
two attempts share a coordinate frame, attempt-vs-attempt deltas need no
anchor tap at all; the clicked hold survives only for "position vs wall
landmark" language. (b) The static-hold lab floors (3.18 %, 6.3 %) are
dominated by the climber's own position reproduction, not the pipeline —
measurement error is ~1.6 % torso (2σ ≈ 3.3 %), and body reproduction is
signal in the product. See `lab/results/exp03-registration/findings.md`.

---

## 2026-07-06 — Hip-to-wall depth from limb foreshortening (feasibility note)

**Idea:** estimate hip-to-wall depth (the known low-confidence metric) from the
foreshortening of leg segments — apparent pixel length vs. known true length
encodes each segment's out-of-plane tilt, chained ankle→knee→hip from a
feet-on-wall anchor.

**Verdict: legitimate physics, but stays low-confidence — not a headline metric.**
The foreshortening ℓ ≈ s·L·cosθ genuinely encodes out-of-plane angle (this is how
monocular-3D methods work), but recovering hip depth specifically stacks four
problems: (1) cos θ sign ambiguity — can't tell "knee toward wall" from "away";
(2) per-person true segment length isn't actually known (anthropometric ratios
have wide variance; calibration-frame lengths are themselves foreshortened);
(3) worst-case noise sensitivity — cos θ is flat near fronto-parallel (the common
pose), and the leverage case lands on knees/ankles, the least-reliable keypoints
from Test 1; (4) error compounds along the 2-segment chain, and real perspective
on an overhang breaks the clean weak-perspective model.

**Cheapest next step when depth returns:** don't hand-build a foreshortening
estimator — MediaPipe already outputs a learned per-landmark z doing the
better version of this. Extend the exp02 noise floor to the z-axis and measure
whether z is repeatable across static-reset takes relative to the ~10–15 cm
sag signal. Expectation: z too noisy on a mobile-class model → "not from this
pipeline," found cheaply.

**Real upgrade path (if depth becomes a priority):** a dedicated monocular-3D /
SMPL model (4D-Humans class — the Test 1 ViTPose-style upper bound), which
estimates a constrained 3D body mesh with the biomechanical priors built in.
Still never as trustworthy as an in-plane vertical measurement. Related: the
head-on-vs-side-on filming decision determines whether depth is recoverable at
all (head-on forfeits it entirely).
