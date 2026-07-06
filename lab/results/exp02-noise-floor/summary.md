# Test 2 — noise floor and calibration
_Generated 2026-07-06 20:58 UTC from 30 takes._

Between-take std (ddof=1) of per-take medians; the product's minimum
honestly-reportable difference is **2×std**.

       group  n_takes  n_positions  std_A_px  std_B_px  std_C_torso  std_D_px  std_D_torso  std_C_pct_torso  std_D_pct_torso  std_B_pct_torso
static-fixed        9            3    14.238    16.677        0.074       NaN          NaN            7.414              NaN            7.671
static-reset        3            1    28.710     3.093        0.021       NaN          NaN            2.057              NaN            1.400

## Data quality
- Reference-hold anchors (variant D): 0/30 takes; missing: sf1-1.MOV, sf1-2.MOV, sf1-3.MOV, sr1-1.MOV, sr1-2.MOV, sr1-3.MOV, sf2-1.MOV, sf2-2.MOV, sf2-3.MOV, sf3-1.MOV, sf3-2.MOV, sf3-3.MOV, m1-1.MOV, m1-2.MOV, m1-3.MOV, m2-1.MOV, m2-2.MOV, m2-3.MOV, m3-1.MOV, m3-2.MOV, m3-3.MOV, m4-1.MOV, m4-2.MOV, m4-3.MOV, m5-1.MOV, m5-2.MOV, m5-3.MOV, m6-1.MOV, m6-2.MOV, m6-3.MOV
- Ankle-gated takes (B/C = NaN; <30 usable-ankle frames or <50% of core frames): 14/30 — sf2-1.MOV, sf2-2.MOV, sf2-3.MOV, sf3-1.MOV, sf3-2.MOV, sf3-3.MOV, m1-2.MOV, m2-1.MOV, m2-2.MOV, m2-3.MOV, m5-1.MOV, m5-2.MOV, m5-3.MOV, m6-1.MOV

## Movement repeatability (peak hip height, pooled within-move)
_6 move(s), 18 takes, pooled df=6._

 n_moves  n_takes  std_Bpeak_px  df_Bpeak_px  std_Cpeak_torso  df_Cpeak_torso  std_Dpeak_px  df_Dpeak_px  std_Dpeak_torso  df_Dpeak_torso  std_Bpeak_pct_torso  std_Cpeak_pct_torso  std_Dpeak_pct_torso
       6       18       142.656            6            0.170               6           NaN            0              NaN               0               30.357               17.033                  NaN

## Calibration
_calibration.json not filled in — criterion 2 not evaluated._

**Criterion 1:** not evaluable — variant D needs reference-hold anchors on ≥2 static-reset takes (run: uv run lab/pick_anchors.py).

## Minimum honestly reportable difference (2σ)

- Within one camera setup (variant A, static-fixed): **28.5 px**
- Across camera setups, ankle-anchored (variant B, static-reset, gated): **6.2 px**
- Across camera setups, ankle-anchored relative (variant C, static-reset, gated): **4.11% of torso length**

## Units decision (recommendation — final call is the developer's)

_Not enough data for a units recommendation yet — variant D needs reference-hold anchors (uv run lab/pick_anchors.py)._
