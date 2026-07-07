# Test 2 — noise floor and calibration
_Generated 2026-07-06 21:11 UTC from 30 takes._

Between-take std (ddof=1) of per-take medians; the product's minimum
honestly-reportable difference is **2×std**.

       group  n_takes  n_positions  std_A_px  std_B_px  std_C_torso  std_D_px  std_D_torso  std_C_pct_torso  std_D_pct_torso  std_B_pct_torso
static-fixed        9            3    14.238    16.677        0.074    15.350        0.116            7.414           11.626            7.671
static-reset        3            1    28.710     3.093        0.021     9.754        0.080            2.057            8.037            1.400

## Data quality
- Reference-hold anchors (variant D): 30/30 takes
- Ankle-gated takes (B/C = NaN; <30 usable-ankle frames or <50% of core frames): 14/30 — sf2-1.MOV, sf2-2.MOV, sf2-3.MOV, sf3-1.MOV, sf3-2.MOV, sf3-3.MOV, m1-2.MOV, m2-1.MOV, m2-2.MOV, m2-3.MOV, m5-1.MOV, m5-2.MOV, m5-3.MOV, m6-1.MOV
- static-fixed cross-check: std_D 15.4 px vs std_A 14.2 px — the camera is untouched within this group, so the difference isolates anchor-click noise.

## Movement repeatability (peak hip height, pooled within-move)
_6 move(s), 18 takes, pooled df=6._

 n_moves  n_takes  std_Bpeak_px  df_Bpeak_px  std_Cpeak_torso  df_Cpeak_torso  std_Dpeak_px  df_Dpeak_px  std_Dpeak_torso  df_Dpeak_torso  std_Bpeak_pct_torso  std_Cpeak_pct_torso  std_Dpeak_pct_torso
       6       18       142.656            6            0.170               6        12.260           12            0.105              12               30.357               17.033               10.489

## Calibration
_calibration.json not filled in — criterion 2 not evaluated._

**Criterion 1 (σ of relative hip height, hold-anchored D/torso, static-reset, ≤2.0% torso):** 8.04% → FAIL _(ankle-anchored C on the same takes, for comparison: 2.06%)_

## Minimum honestly reportable difference (2σ)

- Within one camera setup (variant A, static-fixed): **28.5 px**
- Across camera setups, hold-anchored (variant D, static-reset): **19.5 px**
- Across camera setups, hold-anchored relative (D/torso, static-reset): **16.07% of torso length**
- Across camera setups, ankle-anchored (variant B, static-reset, gated): **6.2 px**
- Across camera setups, ankle-anchored relative (variant C, static-reset, gated): **4.11% of torso length**

## Units decision (recommendation — final call is the developer's)

Neither unit system clears the bar even with a world-fixed anchor — investigate the remaining noise sources (anchor-click repeatability? camera rotation/scale between re-sets? hip tracking itself?) before designing insight language.
