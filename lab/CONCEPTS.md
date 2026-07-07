# Measurement & computer-vision concepts — project primer

A plain-language reference for the ideas the lab experiments lean on. Written
for a strong software engineer who is new to computer vision and measurement
statistics. Every concept is grounded in a number this project actually
measured, so it stays concrete. Cross-references point at the experiment that
produced each figure.

Skim the **Quick glossary** at the bottom for one-line lookups; read the
sections when you want the "why."

---

## Part 1 — Measurement, noise, and honesty

### Precision vs accuracy (random vs systematic error)

Two different ways a measurement can be wrong:

- **Systematic error (bias / accuracy):** a consistent offset. If the pipeline
  always reports hip height 3% too high, that's bias. It's the *same* every
  time.
- **Random error (noise / precision):** run-to-run jitter. Measure the exact
  same thing ten times, get ten slightly different numbers. That scatter is
  the random error.

Why the distinction is load-bearing here: **the product reports *differences*
between two attempts by the same climber.** When you subtract attempt A from
attempt B, any systematic bias present in both cancels out — if both are 3%
too high, the *difference* is unaffected. What does *not* cancel is the random
noise. So for this product, the honest error bar on a reported difference is
set almost entirely by random error. That's why every experiment measures
*repeatability* (same thing, many times) rather than absolute correctness.

### Standard deviation (σ) and the noise floor

Take many measurements of a fixed quantity. The **standard deviation** (σ,
"sigma") summarizes how spread out they are — roughly, the typical distance of
a single measurement from the average. Small σ = tight, repeatable; large σ =
noisy.

The **noise floor** (a.k.a. **measurement floor**) is that σ, expressed for
the quantity you care about. It is the smallest change that is *not* just
noise. Test 2's entire job was to measure this floor for hip height. See
[results/exp02-noise-floor/](results/exp02-noise-floor/).

> **Degrees of freedom (df):** how many independent pieces of information went
> into a σ estimate — roughly "number of takes minus the things you had to
> estimate along the way." A σ from 3 takes (df≈2) is a shaky estimate; the
> same σ from 13 takes (df≈12) is trustworthy. This is why exp02's movement
> number (df=12) is more believable than its static-reset number (df=2) even
> when they agree. **Pooled std** just means combining several small same-
> condition groups into one σ estimate with more df, without letting real
> differences *between* groups leak in.

### Why "2σ" is the reporting threshold

A single measurement lands within ±1σ of the truth about 68% of the time, and
within ±2σ about 95% of the time. So if a measured difference is smaller than
2σ, there's a real chance it's just noise pretending to be signal.

**Rule this project uses:** the *minimum honestly reportable difference is
2σ.* Anything smaller gets reported as "no measurable difference" — which,
per the honesty principles, is a legitimate and useful result, not a failure.
This is the concrete mechanism behind CLAUDE.md's "report only differences
that clear the measured noise floor."

### The subtlety that reframed everything: signal vs noise

When you hold the "same" position across several takes and the measured hip
height still varies by 3–6% of torso, that spread is **two things added
together**:

1. **Measurement error** — the pipeline's own jitter (pose + registration +
   click). This is genuine noise.
2. **Body reproduction** — you physically cannot re-hold a position to the
   centimeter. Your hips really are in slightly different places.

[exp03](results/exp03-registration/findings.md) proved these are separable:
correcting the camera perfectly left the static-hold spread essentially
unchanged (6.27% → 6.31%), because one take (sf1-1) simply had the hips held
~6 cm lower — with the tripod untouched. That's not the pipeline being wrong;
that's the climber.

**Why this matters:** body reproduction is *signal*, not noise, in the
product. It is literally the "is the beta settled? (low variance) vs still
searching (high variance)" diagnosis-mode metric. So the honest measurement
floor is component (1) alone (~1.6% torso), **not** the raw static-hold spread
(3–6%). Earlier experiments that used static-hold repetition overstated the
pipeline's noise because they bundled the climber into it.

### What the floor drives in the product

The measurement floor is the resolution knob under every insight:

- **Honesty gate:** report a delta only if it clears 2σ; else "no measurable
  difference."
- **Which metrics are allowed:** a metric is headline-worthy only if its real
  climbing range is well above the floor. Hip height, shoulder elevation, COM
  peak (range ~10–20% torso) clear it comfortably. Hip-to-wall depth (real
  range ≈ the floor) does not — so it's correctly demoted to low-confidence.
- **Ranking ("one insight, not ten"):** rank differences by
  signal-to-noise = observed delta ÷ floor (how many σ above noise). Surface
  the highest. **The floor is the denominator of the product's core ranking
  function** — it both gates and orders.
- **Confidence labels** map onto σ bands: >4σ high, 2–4σ moderate, <2σ null.

Worked example with the current floor (2σ ≈ 3.3% of torso ≈ ~1.6 cm for a
~50 cm torso):

| reported difference | as % torso | vs floor | verdict |
|---|---|---|---|
| "hips 8 cm higher" | ~16% | ~5× | high confidence |
| "hips 5% higher" | 5% | ~1.5× | reportable, moderate-confidence label |
| "hips 1% higher" | 1% | below | not reportable → "no difference" |

### Relative vs absolute units, and torso normalization

**Absolute units** (centimeters) require knowing the pixels-to-cm scale, which
needs a calibration reference in frame (known climber height, or known hold
spacing). **Relative units** express everything as a fraction of the climber's
own body — this project uses **torso length** (shoulder-center to hip-center)
as the denominator.

Why relative is the default here:

- **Morphology-invariant:** "hips rose 8% of your torso" means the same
  proportional thing for a tall and a short climber. No per-person calibration.
- **No calibration step** in the product — one less thing to get wrong.
- **Forced outdoors anyway:** on real rock there's no known hold spacing, so
  cm is unrecoverable; relative units work identically on plywood and granite.

Torso is the chosen denominator because it's measurable in almost every frame
(shoulders and hips are the reliably-tracked keypoints — see Part 2) and
doesn't change with limb pose the way stature or reach do. Trade-off: forming
a ratio can *amplify* noise if the numerator is large — see the lever-arm
effect in Part 3.

---

## Part 2 — Seeing the body: pose estimation

### Landmarks / keypoints

A **pose estimation** model looks at an image and outputs the pixel location
of labelled body points — **landmarks** (a.k.a. **keypoints**): left shoulder,
right hip, left ankle, etc. This project uses MediaPipe BlazePose, which emits
33 landmarks. Everything downstream is math on these points; the raw video is
never touched again after extraction. That separation is the pipeline's Layer
1 → Layer 2 boundary.

### Confidence / visibility

Each landmark comes with a **visibility** (confidence) score, 0–1: the model's
own estimate of how sure it is. A low score means "I'm guessing." We threshold
at 0.5 — below that, the point is treated as not-usable for that frame rather
than trusted blindly. Test 1 measured how often each landmark clears this bar.

### Jitter

Even on a perfectly still subject, the detected landmark position wobbles a few
pixels frame to frame. That **jitter** is per-frame random error. Two ways it's
handled: taking the **median** over many frames of a static hold (the wobble
averages out), and, for a moving quantity like peak hip height, being careful
that "the 95th-percentile frame" isn't just the noisiest frame (a smoothed
trajectory max is more honest — a noted future refinement).

### Occlusion

When a body part is hidden — behind the torso, off-frame, or covered by a limb
— the model can't see it and either drops it (low visibility) or hallucinates a
position. This is a *per-frame* problem, and it's exactly why body-fixed
anchoring failed (Part 3).

### Why hips and shoulders are trustworthy but wrists and ankles aren't

Test 1's central finding: hips and shoulders track with stable confidence
through ~97–100% of frames on well-filmed clips, while wrists and ankles are
low-confidence roughly half the time. Hips/shoulders are large, central, rarely
fully hidden, and move smoothly; hands and feet are small, fast, often pressed
against holds or occluded by the body. **The v1 metric set was deliberately
chosen to lean on the reliable keypoints** — this isn't a limitation to fix,
it's a design constraint honored.

### The depth (z) caveat

BlazePose also outputs a rough **z** (toward/away-from-camera) per landmark.
Depth from a single side-on camera is fundamentally weak — you're inferring a
3D quantity the camera didn't really capture. So hip-to-wall distance (a pure
depth measurement) is expected to be low-confidence and is labelled as such,
never reported as a headline. (See the foreshortening feasibility note in
IDEAS.md for the full reasoning.)

---

## Part 3 — Placing the body on the wall: coordinate frames & anchoring

### Image coordinates vs wall coordinates

A landmark's position is in **image coordinates** — pixels from the top-left of
the frame. But "hips 8 cm higher" is a claim about position *on the wall*, not
in the photo. If the camera moved between attempts, the same wall position
lands at different image coordinates. So a raw image-coordinate comparison
conflates "the climber moved" with "the camera moved." **Anchoring** is the
job of removing the camera so a comparison is about the climber.

### The three anchor classes

To measure hip *height*, you need a reference that is fixed relative to the
thing you're measuring against. Three options, by what the reference is fixed
to:

- **Camera-fixed** (e.g. the bottom edge of the frame — "variant A"): valid
  *only* while the tripod is untouched. Within one session it's fine
  ([exp02](results/exp02-noise-floor/) measured 14 px between-take σ with a
  fixed camera). Useless the moment the camera moves.
- **Body-fixed** (e.g. the ankle midpoint — "variant B"): moves *with* the
  climber, so it cancels camera motion automatically. But it depends on a
  keypoint being reliable, and [it failed three ways](results/exp02-noise-floor/findings-anchor.md):
  compressed poses collapse the lower legs, heel hooks put the ankle *above*
  the hip (the geometry inverts), and reaches occlude the feet entirely. A
  body-fixed anchor inherits every weakness of its keypoint.
- **World-fixed** (a hold or wall feature — "variant D"): fixed to the wall,
  so it survives camera re-sets *and* every body position, with no semantic
  failure modes. This is the durable one. In the POC it was a clicked hold;
  the real product gets it automatically via registration (Part 4).

### The lever-arm effect (anchor-distance amplification)

A subtle trap the experiments surfaced. When you express hip height *relative*
to torso as `(anchor_y − hip_y) / torso`, any error in the denominator (torso)
gets amplified in proportion to how large the numerator is. If the anchor sits
far from the hips, the numerator is big, and small torso wobble swings the
ratio a lot.

Measured directly: with the anchor on a top-row hold ~2.6 torso-lengths above
the hips, the relative floor was **8.15%**; moving the anchor to hip height
(~0.03 torso-lengths away) dropped it to **3.18%** — [same pipeline, same
takes, just a shorter lever](results/exp02-noise-floor/findings-hold-anchor.md).
Practical rule: **anchor near the thing you're measuring.**

---

## Part 4 — Aligning two videos: registration

**Registration** is the general solution to the anchoring problem: instead of
one reference point, compute the full geometric mapping between two camera
views of the same scene, and use it to convert both into one shared coordinate
system. Then any comparison is automatically camera-free.
[exp03](results/exp03-registration/findings.md) built and measured this.

### Feature detection & matching

To find the mapping automatically, you need corresponding points between the
two frames — without anyone clicking them.

- A **feature detector** (this project uses **SIFT** — Scale-Invariant Feature
  Transform; **ORB** is a faster fallback) finds hundreds-to-thousands of
  distinctive little image patches (hold edges, chalk marks, wood grain) and,
  for each, computes a **descriptor**: a compact numeric fingerprint of the
  local texture that stays stable if the patch is rotated, scaled, or shifted.
- **Matching** pairs up features between two frames by finding descriptors that
  are numerically closest. A climbing wall is ideal for this — it's saturated
  with high-contrast, unique, rigid texture.
- **Lowe's ratio test** throws out ambiguous matches: keep a match only if the
  best candidate is clearly better than the second-best (best distance <
  0.75 × second-best). This kills matches where a feature could plausibly pair
  with several look-alikes.

Because the climber holds a similar position in every static take, we **mask
out the climber** (using the pose landmarks) before detecting features — so the
mapping is fit to the *wall*, not contaminated by the body.

### RANSAC (fitting a model despite wrong matches)

Even after the ratio test, some matches are wrong. **RANSAC** (RANdom SAmple
Consensus) fits a transform robustly: repeatedly pick a minimal random subset
of matches, fit a candidate transform, count how many *other* matches agree
with it ("inliers"), and keep the transform with the most inliers. Wrong
matches never gather consensus, so they're ignored. In exp03 even the hardest
pair (biggest camera move, only ~42 inliers) yielded a usable transform.

### The three transform families — and why only one works

A transform is a formula mapping points in frame A to frame B. They differ in
how much freedom (degrees of freedom, DOF) they have:

| transform | DOF | can represent | exp03 residual on camera re-sets |
|---|---|---|---|
| **translation** | 2 | shift only | 20.5 px — fails |
| **similarity** | 4 | shift + rotate + uniform scale | 8.2 px — fails |
| **homography** | 8 | full perspective of a plane | **2.23 px — works** |

Why translation and similarity fail: when you take the phone off the tripod and
put it back, you don't just shift and rotate the view — you change the
**perspective** (the wall's foreshortening, which corners look bigger). Only a
homography can model that. This is a *structural* result, not a tuning issue:
**it killed the "two taps" product idea**, because two clicked points can only
fix a similarity, and a similarity can't represent perspective. It's automatic
homography or nothing.

### Why the wall being planar makes this exact

A **homography** is the exact mapping between two pinhole-camera views of a
single **plane**. A climbing wall (or a flat rock face) *is* a plane, so points
on the wall map between any two camera positions perfectly — no approximation.
This is the deep reason registration works so well here and would work on
plywood and granite identically.

### Parallax (why protruding holds mislead, and why the climber ghosts)

**Parallax** is the apparent shift of objects at different depths when the
camera moves — hold your thumb up, close one eye then the other, it jumps
against the background. Consequences in this project:

- A **hold protrudes** from the wall plane, so when the camera moves, the
  hold's apparent center shifts *relative to the plane* the homography aligns.
  That shift looks like registration error but isn't the pipeline's fault —
  it's the hold not being on the plane. This is why the clicked near-hip *hold*
  showed ~4 px residual while a flatter feature showed ~1 px, and why the
  ground-truth clicks should favor **flat, on-plane features** (bolt holes,
  seams, chalk marks).
- The **climber stands ~30 cm off the wall**, so in a registered/warped frame
  the body "ghosts" (doesn't line up) while the wall snaps into place — visible
  in [qa/warpdiff](results/exp03-registration/qa/). This residual body parallax
  is small for small camera moves and is part of the honest measurement floor.

### Why registration beats anchoring

Once two attempts share a wall-fixed coordinate frame, the hip-height
difference between them is a **direct coordinate subtraction — zero user
taps.** The clicked anchor is only still needed to phrase a *single* attempt
against a wall landmark ("hips above the start hold"), not for the
attempt-vs-attempt deltas that are the product's core. So **registration
subsumes anchoring** for diff mode. It's also the same machinery that unlocks
the outdoor story (rock texture is excellent for feature matching) and stays
inside the legal guardrail (only the user's own footage).

---

## Part 5 — Putting numbers on it: the error budget

### Combining independent errors (quadrature)

Independent random errors do **not** add directly; their *variances* add, so
the combined σ is the square root of the sum of squares — **quadrature**:

```
σ_total = sqrt(σ_a² + σ_b² + ...)
```

Intuition: independent wobbles partly cancel as often as they reinforce, so the
total grows slower than a straight sum. Two 3 px errors combine to
`sqrt(9+9) ≈ 4.2 px`, not 6.

### This project's current error budget

Pulling together the measured components for a hip-height *difference*:

| component | 1σ | source |
|---|---|---|
| registration (camera alignment) | ~1–2 px | [exp03](results/exp03-registration/findings.md), probe-measured |
| pose (hip keypoint precision) | ~3.1 px | [exp02](results/exp02-noise-floor/) variant B, clean takes |
| **combined (quadrature)** | **~3.7 px ≈ 1.6% torso** | |
| **→ 2σ reporting floor** | **~3.3% torso ≈ ~1.6 cm** | (torso ~219 px in these clips; ~50 cm on a body) |

Separately, **body reproduction** (3–6% torso) is *not* in this budget — it's
the signal the product reports, per Part 1.

Reading it: the pipeline can honestly distinguish hip-height differences of
~3.3% of torso and up. The headline insights (~16% torso) sit ~5× above that.
The pose term now dominates the budget, so the next lever on the floor is pose
precision — which is what the Test 1 research-grade-model (ViTPose) comparison
could push down if it ever becomes worth it.

---

## Quick glossary

- **Accuracy / bias / systematic error** — consistent offset from truth;
  cancels in attempt-vs-attempt differences.
- **Precision / random error / noise** — run-to-run jitter; the thing the
  product's error bar is made of.
- **σ (standard deviation)** — typical scatter of repeated measurements.
- **Noise floor / measurement floor** — the σ of a metric; smallest change
  that isn't noise.
- **2σ rule** — minimum honestly reportable difference; below it → "no
  measurable difference."
- **Degrees of freedom (df)** — how well-supported a σ estimate is; more is
  more trustworthy.
- **Pooled std** — one σ estimate combining several same-condition groups
  without letting real between-group differences leak in.
- **Signal vs noise (here)** — body reproduction is signal; pipeline jitter is
  noise; static-hold spread mixes both.
- **Relative units** — measurements as a fraction of torso length;
  morphology-invariant, no calibration.
- **Landmark / keypoint** — a labelled body point (e.g. left hip) the pose
  model locates in pixels.
- **Visibility / confidence** — the model's 0–1 certainty for a landmark;
  thresholded at 0.5.
- **Jitter** — per-frame wobble of a landmark on a still subject.
- **Occlusion** — a body part hidden from the camera; breaks body-fixed
  anchors.
- **Anchoring** — fixing a reference so a comparison is about the climber, not
  the camera.
- **Camera- / body- / world-fixed anchor** — reference fixed to the frame /
  the climber / the wall respectively.
- **Lever-arm effect** — a relative-ratio's noise grows with anchor-to-hip
  distance; anchor near the measurement.
- **Registration** — computing the full mapping between two camera views of the
  same scene to share one coordinate system.
- **Feature / descriptor** — a distinctive image patch and its
  rotation/scale-stable numeric fingerprint (SIFT/ORB).
- **Matching / Lowe ratio test** — pairing features across frames, keeping only
  unambiguous matches.
- **RANSAC** — robustly fitting a transform by consensus, ignoring wrong
  matches (outliers).
- **Translation / similarity / homography** — transforms of 2 / 4 / 8 DOF;
  only the homography models perspective.
- **Homography** — exact mapping between two camera views of a *plane* (the
  wall); 8 DOF.
- **Planar assumption** — the wall is flat, which is what makes the homography
  exact.
- **Parallax** — apparent shift of objects at different depths when the camera
  moves; why protruding holds mislead and the climber ghosts.
- **Quadrature** — combining independent errors as `sqrt(Σ σ²)`.
