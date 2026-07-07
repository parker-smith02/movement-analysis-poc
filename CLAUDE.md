# Climbing Technique Analysis — POC

## What this project is

A proof-of-concept for a climbing technique coaching app. The eventual product: a climber
projecting a single hard move films their attempts; the app compares attempts against each
other and surfaces one precise, trustworthy coaching insight (e.g. "your right shoulder rises
~6 cm toward your ear at initiation; on your closest attempt it stayed down").

**This POC does not build the app.** It answers one question: *are the measurements
trustworthy enough to coach from?* Everything else is deferred.

## Who is building this

A solo software engineer (CS degree, enterprise experience: Python, Angular, ASP.NET, AWS,
Azure, Terraform) and high-level rock climber, working on this as a side project. Target
outcome is a sustainable indie business (~$100–400K ARR), not a venture-scale company.
Optimize for shortest path to validated learning, minimal ongoing cost, and code the
developer can maintain alone.

## Product principles (carry these into every design decision)

1. **Comparison over judgment.** The core unit of analysis is one move across many attempts
   by the same climber — never an absolute technique score. Diff attempts against each
   other: failed vs. closest, failed vs. send. There is no universal "correct form" in
   climbing; self-referential comparison sidesteps that entirely.
2. **One insight, not ten.** A climber holds one cue on the wall. Rank detected differences
   by magnitude and confidence; surface the top one; demote the rest.
3. **Honesty about uncertainty.** Report only differences that clear the measured noise
   floor. Label low-confidence metrics as such. Phrase findings as observed differences
   ("your hips were 8 cm higher"), never unverifiable causal diagnoses ("you lack core
   tension"). Showing a null result ("no difference in foot timing") is a feature.
4. **Physics limits are real.** Per-limb force split with 4 contact points is statically
   indeterminate — never claim it. What IS recoverable: whole-body COM position (from
   anthropometric segment tables), COM velocity/acceleration (net force, the "power
   generation" signal), joint angles, shoulder elevation, hip position, timing. Per-limb
   force becomes determinate only at ≤2 load-bearing contacts.
5. **Audience is advanced climbers.** They understand movement; they need help seeing what
   they can't feel. No gamification, no scores, no beginner explanations.
6. **On-device compute.** All pose estimation and metric math runs locally (browser/phone).
   An LLM is used ONLY later, for interpreting extracted features (a few KB of structured
   deltas) — never for processing video. This is the cost architecture the business
   depends on. No backend in the POC. Nothing leaves the machine.

## The four POC tests (in priority order — these define done)

### Test 1 — Pose quality on real climbing footage (go/no-go)
Run pose estimation on 30–50 real clips owned by the developer: steep + vertical, good +
bad lighting, board + gym, including deliberately bad camera angles.
Measure: per-frame keypoint confidence and frame-to-frame jitter for hips and shoulders;
frames where limbs are lost to occlusion.
**Pass:** hips and shoulders tracked with stable confidence through ≥80% of frames on
reasonably-filmed clips. Failure only on badly-filmed clips is acceptable (confirms filming
guidance as a product feature). Failure on well-filmed clips = stop and rethink.

### Test 2 — Metric noise floor and calibration
(a) Repeatability: film the same static position / repeated identical movement several
times; measure variance of computed hip height when the true delta is zero. The resulting
noise floor defines the smallest difference the product may ever honestly report.
(b) Scale calibration (pixels → cm): test two methods — user-entered climber height against
measured pixel height in a calibration frame, and known hold spacing on a standardized
board (Kilter/Tension grid) visible in frame.
**Fallback if calibration is unreliable:** report relative differences ("hips 12% higher
relative to reach span") — decide which world we're in before designing insight language.

**DECIDED (2026-07-07) — see `lab/DECISIONS.md`:**
- **Units: RELATIVE** (fraction of torso length, normalized once per attempt). Reasons:
  morphology-invariance, outdoor has no scale, perspective makes a single pixels→cm factor
  wrong on an oblique wall, and the noise floor is comfortably below target insights.
  Absolute cm is deferred, not forbidden (if ever wanted, do a homography onto a known board
  hold-grid, not a single clicked scale).
- **Measurement floor: 2σ ≈ 3.3% of torso** for a hip-height delta (≈ ~1.6 cm). This is the
  minimum honestly-reportable difference; rank insights by delta ÷ floor.
- **Cross-attempt coordinate frame: automatic background homography registration** (SIFT/ORB
  on the wall, climber masked, RANSAC homography). Registers tripod re-sets to ~1% of torso —
  as good as not moving the camera. **This subsumes anchoring for diff mode: attempt-vs-
  attempt deltas need zero user taps.** A clicked anchor is only for phrasing a single attempt
  against a named wall landmark.
- Calibration (b) / `calibration.json`: left as an unfilled template on purpose — Criterion 2
  cannot change the units decision. Not a blocker.

### Test 3 — Automatic attempt alignment
Given 5–10 pairs of attempts at the same move, find the corresponding moment across them.
Candidate approaches: cross-correlation of COM velocity profiles; detecting the frame where
the reaching wrist begins accelerating toward the target.
**Fallback:** manual alignment (user scrubs both videos to move start). This test measures
product friction, not viability. This is the most novel engineering in the POC — no
off-the-shelf solution exists.

### Test 4 — Does a computed insight land with a real climber?
Take footage from 3–4 climbers stuck on a move, run the pipeline, hand-write the insight
from computed metrics, show them side-by-side footage + the delta.
**Pass:** ≥2 of 4 react along the lines of "I couldn't feel that, but I see it."
"Yeah, obviously" = metrics too shallow.

### Explicitly NOT in the POC
LLM interpretation layer (fake it by hand-writing insights), accounts, storage, payments,
mobile packaging, coach tools, user profiles, board-app data integration.

## Architecture — three pure-function layers

```
video ──► [1. pose extraction] ──► landmark timeseries
              (MediaPipe / model-specific)
landmarks ──► [2. metrics] ──► numbers (deltas, angles, velocities, timings)
              (pure functions, identical logic in Python lab and TS demo)
numbers ──► [3. insights] ──► ranked statements with confidence labels
```

Keep layers strictly separated. Layer 2 is the durable asset — it survives unchanged into
the real app. Duplicating layer 2 in Python and TypeScript is deliberate: it forces a
precise spec. Layer 3 stays hand-written/rule-based in the POC.

**Layer 1 also owns cross-attempt registration** (Test 2 result, `lab/DECISIONS.md` D2):
before metrics run, two attempts are brought into one wall-fixed coordinate frame via
automatic background homography (SIFT/ORB features on the wall, climber masked, RANSAC).
Layer 2 then works in shared wall coordinates, so position deltas are camera-independent
with no user input. Pure metric functions are unchanged by this — it is upstream plumbing.

### v1 metric set (chosen for pose-reliability, not ambition)
- Shoulder elevation (shoulder-to-ear geometry; the most detectable, validated by the
  developer's own coaching feedback)
- Hip height and lateral position at the initiation frame
- Hip distance to wall (EXPECT low confidence — depth from monocular side view is weak;
  label accordingly)
- COM trajectory + peak velocity through the move (power-generation signal)
- Timing offsets (foot weighted → hand leaves)
- Body extension/compression at the catch

COM computation uses standard anthropometric segment-mass tables.

## Tech stack (decided — do not relitigate without new evidence)

### Track A: Python lab (build FIRST, ~2–3 weekends, no UI)
- Plain scripts / notebooks. OpenCV (video I/O), MediaPipe Python (baseline pose),
  NumPy/Pandas (metrics), Matplotlib (jitter/velocity plots).
- Also run a research-grade upper-bound model (ViTPose or 4D-Humans-class 3D, PyTorch,
  rented GPU or Colab) on the same clips. If MediaPipe fails but ViTPose succeeds → product
  viable with server-side/distilled architecture. If both fail → fundamental limit found
  cheaply. This comparison is the single most valuable experiment.

### Track B: Browser demo (build ONLY after the lab validates measurements)
- Vite + React + TypeScript.
- `@mediapipe/tasks-vision` PoseLandmarker (BlazePose, 33 landmarks incl. rough z) on
  WebGPU with WASM fallback. (Alt considered and rejected: TF.js MoveNet — only 17 2D
  keypoints, insufficient hip/shoulder detail.)
- `<video>` playback + `requestVideoFrameCallback` (NOT requestAnimationFrame — need
  video-frame-accurate callbacks) + `<canvas>` overlay for skeleton/annotations.
  Two synced video/canvas pairs for side-by-side.
- No backend. Videos via file input. IndexedDB only if session persistence is wanted.
- Running in a browser tab proves the cross-platform, on-device story by construction.

### Future (context only, not POC scope)
Real app: React Native + Expo, react-native-vision-camera + native pose (Apple Vision /
ML Kit), sharing the TypeScript metrics layer verbatim. Flutter rejected: strands POC code
in Dart.

## UX decisions already made (relevant when the demo gets a UI)

- Annotations drawn ON the footage (shoulder line, COM dot + trail, direction arrows) —
  the two frames should communicate before any text is read. Skeleton overlay toggleable.
- Side-by-side playback synced to the MOVE (aligned at initiation), not to video start;
  one scrubber drives both panels.
- Three-layer insight delivery: visual frames → one-sentence finding → expandable
  explanation + cue. The cue is a short imperative ("pull down and back with the
  shoulders"), saveable.
- Two analysis modes: diff mode (vs. send or closest attempt) and, when no good reference
  exists, diagnosis mode — within-attempt failure-point analysis (COM decelerating before
  hand contact = power/timing problem; COM stalled/moving away = positioning problem),
  cross-attempt consistency (high variance = beta not settled; low variance = one constant
  element failing), and a small library of pose-detectable anti-patterns (shoulders rising
  under load, hips sagging on steep terrain, pulling before foot is weighted) — always
  framed as "pattern present," never "cause of failure."
- Attempt logging: one-tap highpoint tag per attempt (enables closest-vs-furthest diffing
  from attempt 2 onward). The project (named move + attempt history) is the app's
  organizing object.
- Filming guidance is a first-class feature: side-on for hip distance; warn on angles that
  won't support tracking. Also: **pause a beat after touching the phone before the attempt**
  (mount settling / phone stabilization drifts the view a few px for the first seconds —
  measured in exp03); tripod need not stay perfectly put between attempts since registration
  handles re-sets, but leaving it roughly in place helps.

## Board climbing context

Standardized boards (Kilter, Tension, Moon) are the likely beachhead: fixed/known wall
angle, known hold grid (useful for pixel→cm calibration in Test 2b), consistent indoor
filming, and the exact target demographic.
**Legal guardrail:** use ONLY user-provided context (user tags board type/angle, marks
holds, or holds detected via CV from the user's own footage). Do NOT scrape or use
reverse-engineered board-app APIs/databases — treat them as off-limits. Naming boards for
tagging is nominative fair use territory; no logos, no implied endorsement.

## Conventions for Claude Code sessions

- Prefer Plan mode for any session touching more than one file or starting a new
  experiment; propose the experiment design before writing code.
- Every lab experiment is a standalone script under `lab/` with a docstring stating the
  test (1/2/3/4), the hypothesis, and the pass criterion; outputs (plots, CSVs) go to
  `lab/results/<experiment-name>/`. Never overwrite prior results.
- Verify your own output: run scripts, inspect the plots/numbers, and report actual
  measured values in your summary — never report success from code compiling.
- Metrics layer: pure functions, no I/O, typed, unit-tested against hand-computed fixtures.
  Python and TS implementations must share test fixtures (JSON) to stay in lockstep.
- Do not add dependencies, backends, cloud services, or build infrastructure beyond the
  stack above without flagging the tradeoff explicitly and asking.
- Do not soften the honesty principles to make demo output more impressive: no invented
  precision, no reporting deltas below the measured noise floor, no causal claims.
- When results are ambiguous, say so plainly and propose the cheapest next experiment that
  would disambiguate.
- Raw climbing footage may contain identifiable people. Keep all clips in `footage/`
  (gitignored); never commit video, and never upload it anywhere.

## Repo layout

```
/CLAUDE.md              ← this file
/lab/                   ← Python experiments (Track A)
  /results/             ← experiment outputs, append-only
/demo/                  ← Vite+React browser demo (Track B, later)
/shared-fixtures/       ← JSON test fixtures shared by Python and TS metric tests
/footage/               ← local clips, gitignored
```

## Sequencing

1. Lab: Test 1 (pose quality) + upper-bound model comparison. ✅ done.
2. Lab: Test 2 (noise floor, calibration). → Decision point: absolute cm vs. relative units.
   ✅ done — **RELATIVE units** chosen; measurement floor 2σ ≈ 3.3% torso; registration solves
   cross-attempt alignment of coordinates. See `lab/DECISIONS.md` (D1, D2). Calibration (2b)
   deferred by design.
3. Lab: Test 3 (alignment) — timeboxed; fall back to manual alignment if it drags. ← NEXT.
   Head start: registration (D2) already shares a coordinate frame across attempts, which
   should make COM-velocity cross-correlation cleaner than on raw pixels.
4. Demo: minimal side-by-side UI as the vehicle for Test 4 with real climbers.
5. Commit/kill decision: lab numbers hold AND ≥2/4 climbers pass Test 4 → build the app.
