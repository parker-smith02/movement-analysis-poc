# Test 2 — noise floor & units decision (CLOSED 2026-07-07)

Test 2 asked: are the measurements trustworthy enough to coach from, and in
what units? **Answer: yes, in RELATIVE units.** The full decision and evidence
are in [`lab/DECISIONS.md`](../../DECISIONS.md) (D1 units, D2 registration).
New to the CV/stats terms? See [`lab/CONCEPTS.md`](../../CONCEPTS.md).

## What's here

- `summary.md`, `*.csv`, `plots/` — current auto-outputs (variant D, near-hip
  anchor, per-take relative form).
- `findings-anchor.md` — run 1: why the ankle anchor was rejected.
- `findings-hold-anchor.md` — runs 2 & 3: hold anchor, the lever-arm effect,
  the near-anchor floor.
- `run1-ankle-anchor/`, `run2-toprow-anchor/`, `run3-near-anchor/` — frozen
  per-run snapshots (append-only convention).
- The registration experiment that clinched the units decision lives in the
  sibling folder [`../exp03-registration/`](../exp03-registration/).

## Headline numbers

- Hips track stably (variant A between-take std ~14 px).
- Hip-height measurement floor: **2σ ≈ 3.3% of torso** (~1.6 cm). Target
  insights (~8 cm ≈ 16% torso) clear it ~5×.
- Cross-attempt camera differences are removed by automatic homography
  registration to ~1% of torso (exp03), so no anchor tap is needed for
  attempt-vs-attempt diffs.
- The 3–6% spread seen when repeating a "static" hold is mostly the climber not
  re-holding identically (product **signal**), not pipeline noise.

## Deliberately left undone

`../../../footage/exp02/calibration.json` is an unfilled template on purpose:
Criterion 2 (do single-scale pixels→cm methods agree?) cannot change the
relative-units decision, and the oblique-wall perspective already implies they
won't. Absolute cm, if ever wanted, = homography onto a known board hold-grid.

## Next

Test 3 — automatic attempt alignment. Registration (D2) already shares a
coordinate frame across attempts, which should help COM-velocity
cross-correlation.
