# Test 1 — pose quality results
_Generated 2026-07-06 02:11 UTC from 20 clip×model runs (10 clips)._

**Pass criterion:** ≥80% of frames with all four core keypoints (L/R hip, L/R shoulder) at visibility ≥ 0.5, on clips tagged `filming=good`.

> **SMOKE RUN — 10 clip(s).** The go/no-go verdict requires the full 30–50 clip set; treat these numbers as pipeline validation only.

## filming = bad (1/2 clip-runs pass)

| clip | model | filming | frames | detection_rate | core_conf_rate_0.3 | core_conf_rate_0.5 | core_conf_rate_0.7 | jitter_shoulder_px | jitter_hip_px | limb_loss_worst | limb_loss_worst_frac | passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| french-press.mov | mediapipe_pose_landmarker_heavy | bad | 307 | 0.997 | 0.997 | 0.997 | 0.997 | 2.150 | 4.742 | wrist_r | 0.603 | True |
| french-press.mov | vitpose:usyd-community/vitpose-base-simple | bad | 307 | 1.000 | 1.000 | 0.730 | 0.254 | 1.663 | 2.274 | ankle_r | 0.547 | False |

## filming = good (18/18 clip-runs pass)

| clip | model | filming | frames | detection_rate | core_conf_rate_0.3 | core_conf_rate_0.5 | core_conf_rate_0.7 | jitter_shoulder_px | jitter_hip_px | limb_loss_worst | limb_loss_worst_frac | passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| daily.mov | mediapipe_pose_landmarker_heavy | good | 305 | 1.000 | 1.000 | 1.000 | 1.000 | 0.720 | 1.357 | wrist_l | 0.574 | True |
| daily.mov | vitpose:usyd-community/vitpose-base-simple | good | 305 | 1.000 | 1.000 | 1.000 | 0.898 | 3.111 | 3.306 | wrist_l | 0.275 | True |
| IMG_8060.mov | mediapipe_pose_landmarker_heavy | good | 648 | 0.981 | 0.981 | 0.981 | 0.981 | 11.997 | 10.513 | wrist_r | 0.489 | True |
| IMG_8060.mov | vitpose:usyd-community/vitpose-base-simple | good | 648 | 0.998 | 0.927 | 0.878 | 0.370 | 38.883 | 18.811 | wrist_r | 0.230 | True |
| IMG_9139.mov | mediapipe_pose_landmarker_heavy | good | 999 | 1.000 | 1.000 | 1.000 | 1.000 | 2.468 | 1.563 | wrist_r | 0.509 | True |
| IMG_9139.mov | vitpose:usyd-community/vitpose-base-simple | good | 999 | 1.000 | 0.998 | 0.925 | 0.668 | 44.635 | 46.576 | ankle_l | 0.269 | True |
| IMG_9184.mov | mediapipe_pose_landmarker_heavy | good | 769 | 0.966 | 0.966 | 0.966 | 0.966 | 19.287 | 27.926 | ankle_l | 0.432 | True |
| IMG_9184.mov | vitpose:usyd-community/vitpose-base-simple | good | 769 | 1.000 | 0.967 | 0.889 | 0.611 | 29.858 | 35.902 | ankle_l | 0.307 | True |
| IMG_9232.mov | mediapipe_pose_landmarker_heavy | good | 252 | 1.000 | 1.000 | 1.000 | 1.000 | 2.326 | 3.131 | ankle_r | 0.881 | True |
| IMG_9232.mov | vitpose:usyd-community/vitpose-base-simple | good | 252 | 1.000 | 1.000 | 0.976 | 0.298 | 5.503 | 5.530 | ankle_r | 0.361 | True |
| IMG_9233.mov | mediapipe_pose_landmarker_heavy | good | 624 | 1.000 | 1.000 | 1.000 | 1.000 | 3.459 | 3.364 | ankle_r | 0.529 | True |
| IMG_9233.mov | vitpose:usyd-community/vitpose-base-simple | good | 624 | 1.000 | 0.994 | 0.822 | 0.279 | 13.777 | 9.938 | ankle_r | 0.208 | True |
| low-angle-crimps.mov | mediapipe_pose_landmarker_heavy | good | 1058 | 0.978 | 0.944 | 0.936 | 0.928 | 14.820 | 20.397 | wrist_r | 0.423 | True |
| low-angle-crimps.mov | vitpose:usyd-community/vitpose-base-simple | good | 1058 | 1.000 | 0.958 | 0.954 | 0.816 | 11.618 | 31.625 | wrist_r | 0.157 | True |
| rose-bloc-comp.MOV | mediapipe_pose_landmarker_heavy | good | 1144 | 0.983 | 0.895 | 0.870 | 0.865 | 120.599 | 111.547 | wrist_l | 0.771 | True |
| rose-bloc-comp.MOV | vitpose:usyd-community/vitpose-base-simple | good | 1144 | 0.999 | 0.863 | 0.822 | 0.715 | 290.519 | 310.839 | wrist_l | 0.210 | True |
| rose-bloc-slab.MOV | mediapipe_pose_landmarker_heavy | good | 1983 | 1.000 | 1.000 | 1.000 | 1.000 | 15.129 | 5.000 | ankle_r | 0.370 | True |
| rose-bloc-slab.MOV | vitpose:usyd-community/vitpose-base-simple | good | 1983 | 1.000 | 0.996 | 0.951 | 0.674 | 60.697 | 8.427 | ankle_r | 0.083 | True |

## Cross-model agreement (core keypoints, both models confident)

| clip | models | core_disagreement_median_px | frames_compared |
|---|---|---|---|
| IMG_8060.mov | mediapipe vs vitpose | 34.370 | 599 |
| IMG_9139.mov | mediapipe vs vitpose | 19.612 | 980 |
| IMG_9184.mov | mediapipe vs vitpose | 24.388 | 725 |
| IMG_9232.mov | mediapipe vs vitpose | 22.277 | 250 |
| IMG_9233.mov | mediapipe vs vitpose | 29.595 | 593 |
| daily.mov | mediapipe vs vitpose | 32.432 | 305 |
| french-press.mov | mediapipe vs vitpose | 26.987 | 276 |
| low-angle-crimps.mov | mediapipe vs vitpose | 21.703 | 995 |
| rose-bloc-comp.MOV | mediapipe vs vitpose | 20.336 | 981 |
| rose-bloc-slab.MOV | mediapipe vs vitpose | 30.907 | 1955 |

## Verdict on well-filmed clips: all well-filmed clips PASS
