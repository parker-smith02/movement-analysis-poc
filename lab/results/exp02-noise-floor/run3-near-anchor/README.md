# run 3 — hold-anchored, near-hip hold, per-take median form (2026-07-07)

Frozen auto-outputs of the third exp02 run: variant D anchored to a near-hip
working-zone hold (`anchors-near.json`, the exact clicks used), relative form
= per-take median D ÷ per-take median torso (pre-registered in run 2's commit,
before these clicks existed). Interpretation: `../findings-hold-anchor.md`,
"run 3" section.

The decisive anchor-distance test: moving the anchor from the top row
(~2.6 torso-lengths above the hips) to near hip height (~0.03 torso-lengths on
the static-reset takes) halved the relative noise floor — static-reset D/torso
8.15 % → 3.18 %, movement peaks 9.1 % → 3.63 % — confirming the amplification
mechanism. Still above the 2 % bar; residual is camera-re-set rotation/scale
(single-point anchor corrects translation only).
