# exp03 — cross-setup registration accuracy
_Generated 2026-07-07 03:14 UTC. SIFT features, person-masked; 2 clicked correspondence(s): ['hold_near', 'hold_top']. Torso scale: 219 px._

|dy| at held-out clicked probe holds, px:

         method      class  n  median   p95   max
auto-homography     re-set 24    2.23  6.10 10.20
auto-homography same-setup  6    1.86  2.65  2.86
auto-similarity     re-set 24    8.15 23.80 29.46
auto-similarity same-setup  6    1.72  2.63  2.85
translation-1pt     re-set 24   20.50 32.85 33.00
translation-1pt same-setup  6    1.00  2.00  2.00

Auto-method match/inlier counts per pair:

   take_a    take_b      class  n_matches  inl_sim  inl_hom
sf1-1.MOV sf1-2.MOV same-setup        407      333      333
sf1-1.MOV sf1-3.MOV same-setup        369      325      327
sf1-1.MOV sr1-1.MOV     re-set        292      127      205
sf1-1.MOV sr1-2.MOV     re-set        283       70      157
sf1-1.MOV sr1-3.MOV     re-set        134       31       44
sf1-2.MOV sf1-3.MOV same-setup        884      838      839
sf1-2.MOV sr1-1.MOV     re-set        817      411      631
sf1-2.MOV sr1-2.MOV     re-set        784      239      566
sf1-2.MOV sr1-3.MOV     re-set        179       47       55
sf1-3.MOV sr1-1.MOV     re-set        971      528      763
sf1-3.MOV sr1-2.MOV     re-set       1012      301      788
sf1-3.MOV sr1-3.MOV     re-set        189       49       65
sr1-1.MOV sr1-2.MOV     re-set        905      415      695
sr1-1.MOV sr1-3.MOV     re-set        141       36       42
sr1-2.MOV sr1-3.MOV     re-set        284      139      202

## Re-set pairs, medians (the product's default regime)

- translation-1pt: **20.50 px** = 9.35% torso
- auto-similarity: **8.15 px** = 3.72% torso
- auto-homography: **2.23 px** = 1.02% torso

**Pass criterion (median |dy|, re-set pairs, ≤2 px for a corrected method):** best is auto-homography at 2.23 px → FAIL

Predicted cross-setup hip-height floor with auto-homography: sqrt(2.23² registration + 3.1² pose/body) = **3.82 px ≈ 1.74% torso** (2σ ≈ 3.49%) vs the 2% bar. Prediction only — confirm by re-running the exp02 noise floor with this correction applied.

_similarity-2pt not evaluable: needs ≥3 clicked points per take → run `uv run lab/pick_registration_points.py`._

## End-to-end: relative hip-height floor over all six takes (same position, true delta zero, df=5)

- uncorrected (exp02 variant D, per-take near anchor): std **6.27% torso** (2σ 12.55%)
- homography-corrected (all takes in sr1-1.MOV coordinates, zero taps): std **6.31% torso** (2σ 12.63%)

vs the 2% criterion-1 bar. Includes the climber's off-plane parallax (real product error). Per-take values (D/torso): uncorrected ['-0.127', '0.026', '-0.026', '0.042', '0.031', '-0.018'], corrected ['-0.106', '0.051', '0.005', '0.042', '0.042', '0.063'].
