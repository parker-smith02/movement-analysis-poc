# Test 2 — noise floor and calibration
_Generated 2026-07-06 19:39 UTC from 30 takes._

Between-take std (ddof=1) of per-take medians; the product's minimum
honestly-reportable difference is **2×std**.

       group  n_takes  n_positions  std_A_px  std_B_px  std_C_torso  std_C_pct_torso  std_B_pct_torso
static-fixed        9            3    14.238   158.686        0.434           43.427           72.993
static-reset        3            1    28.710     3.093        0.021            2.057            1.400

## Movement repeatability (peak hip height, pooled within-move)
_6 move(s), 18 takes, pooled df=10._

 n_moves  n_takes  std_Bpeak_px  df_Bpeak_px  std_Cpeak_torso  df_Cpeak_torso  std_Bpeak_pct_torso  std_Cpeak_pct_torso
       6       18       168.412           10            0.175              10               35.838               17.451

## Calibration
_calibration.json not filled in — criterion 2 not evaluated._

**Criterion 1 (σ of relative hip height, static-reset, ≤2.0% torso):** 2.06% → FAIL

## Minimum honestly reportable difference (2σ)

- Within one camera setup (variant A, static-fixed): **28.5 px**
- Across camera setups, wall-anchored (variant B, static-reset): **6.2 px**
- Across camera setups, relative (variant C, static-reset): **4.11% of torso length**

## Units decision (recommendation — final call is the developer's)

Neither unit system clears the bar — investigate the noise sources (ankle visibility? camera protocol?) before designing insight language.
