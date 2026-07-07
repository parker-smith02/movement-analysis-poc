# exp03 — cross-setup registration accuracy
_Generated 2026-07-07 13:30 UTC. SIFT features, person-masked; 7 clicked correspondence(s): ['hold_near', 'hold_top', 'reg01', 'reg02', 'reg03', 'reg04', 'reg05']. Torso scale: 219 px._

|dy| at held-out clicked probe holds, px:

         method      class    n  median   p95   max
auto-homography     re-set   84    2.02  5.04 10.66
auto-homography same-setup   21    1.90  4.09  5.86
auto-similarity     re-set   84    5.59 28.00 36.39
auto-similarity same-setup   21    1.91  4.02  5.92
 similarity-2pt     re-set 1260    6.07 27.11 65.88
 similarity-2pt same-setup  315    4.00 20.38 45.89
translation-1pt     re-set  504    7.00 27.00 35.00
translation-1pt same-setup  126    2.00  8.00 10.00

Auto-method match/inlier counts per pair (frame-0 features):

   take_a    take_b      class  n_matches  inl_sim  inl_hom
sf1-1.MOV sf1-2.MOV same-setup        836      694      717
sf1-1.MOV sf1-3.MOV same-setup        794      662      660
sf1-1.MOV sr1-1.MOV     re-set        680      261      501
sf1-1.MOV sr1-2.MOV     re-set        599      185      347
sf1-1.MOV sr1-3.MOV     re-set        456      128      233
sf1-2.MOV sf1-3.MOV same-setup        907      759      788
sf1-2.MOV sr1-1.MOV     re-set        744      274      568
sf1-2.MOV sr1-2.MOV     re-set        710      206      364
sf1-2.MOV sr1-3.MOV     re-set        521      145      238
sf1-3.MOV sr1-1.MOV     re-set        730      274      503
sf1-3.MOV sr1-2.MOV     re-set        700      188      297
sf1-3.MOV sr1-3.MOV     re-set        497      147      225
sr1-1.MOV sr1-2.MOV     re-set        629      130      294
sr1-1.MOV sr1-3.MOV     re-set        457      126      238
sr1-2.MOV sr1-3.MOV     re-set        626      277      565

## Intra-take camera drift (frame 0 → mid-take, same take)

The camera is not perfectly static within a take: takes recorded right after the tripod was handled settle/drift, untouched takes hold <1 px. Frame-0 clicks and mid-take measurements are therefore different geometries — comparisons must be frame-consistent.

     take      class  drift_px
sf1-1.MOV same-setup      0.68
sf1-2.MOV same-setup      0.75
sf1-3.MOV same-setup      0.43
sr1-1.MOV     re-set      7.21
sr1-2.MOV     re-set      2.89
sr1-3.MOV     re-set      3.60

## Re-set pairs, medians (the product's default regime)

- translation-1pt: **7.00 px** = 3.19% torso
- similarity-2pt: **6.07 px** = 2.77% torso
- auto-similarity: **5.59 px** = 2.55% torso
- auto-homography: **2.02 px** = 0.92% torso

**Pass criterion (median |dy|, re-set pairs, ≤2 px for a corrected method):** best is auto-homography at 2.02 px → FAIL

Predicted cross-setup hip-height floor with auto-homography: sqrt(2.02² registration + 3.1² pose/body) = **3.70 px ≈ 1.69% torso** (2σ ≈ 3.38%) vs the 2% bar. Prediction only — confirm by re-running the exp02 noise floor with this correction applied.

## End-to-end: relative hip-height floor over all six takes (same position, true delta zero, df=5)

- uncorrected (exp02 variant D: frame-0 anchor vs mid-take hips, so it carries each take's intra-take drift): std **6.27% torso** (2σ 12.55%)
- homography-corrected (mid-take features, all takes in sr1-1.MOV coordinates, zero taps): std **6.17% torso** (2σ 12.33%)

vs the 2% criterion-1 bar. Includes the climber's off-plane parallax (real product error). Per-take values (D/torso): uncorrected ['-0.127', '0.026', '-0.026', '0.042', '0.031', '-0.018'], corrected ['-0.111', '0.048', '0.007', '0.042', '0.053', '0.022'].
