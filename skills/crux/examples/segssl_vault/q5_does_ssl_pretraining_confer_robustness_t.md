---
id: q5
type: question
title: Does SSL pretraining confer robustness to domain shift at segmentation time (Cityscapes → ACDC, clear → fog/night/rain/snow)?
parent: root
status: open
stale: true
created: "2026-07-11T19:38:55"
updated: "2026-07-11T19:38:55"
---

# q5 — Does SSL pretraining confer robustness to domain shift at segmentation time (Cityscapes → ACDC, clear → fog/night/rain/snow)?

Parent:: [[segssl_label_efficient_segmentation]]

## Question

SegSSL encoders are pretrained on unlabeled clear-weather data and fine-tuned for segmentation only on Cityscapes (clear); this question asks whether the SSL pretext itself — independent of any weather-specific augmentation — leaves the encoder more robust when the frozen fine-tuned model is evaluated zero-shot on ACDC's adverse-weather splits. The three SSL families in the program (MIM, self-distillation, dense contrastive — see [[wiki/masked-image-modeling]], [[wiki/self-distillation]], [[wiki/contrastive-learning]]) make different bets about which invariances transfer, so each is tested as its own hypothesis against a shared supervised-ImageNet-1k+UPerNet baseline.

## Answer so far

_(interpretation — written by the PI/agent; auto-flagged stale when new evidence lands)_

<!-- crux:ledger:start -->
**3 children** · ideas 1/3 done (supported 0, partial 0, refuted 1, inconclusive 0)

- `h13` [[h13_mae_pretraining_reduces_the_cityscapes_a|MAE pretraining reduces the Cityscapes→ACDC mIoU drop vs. the supervised baseline]] — *done* — verdict **refuted**, metric `+0.4 mIoU ACDC-mean (ns); −0.5 mIoU ACDC-night vs. supervised`
- `h14` [[h14_dinov2_self_distillation_confers_stronge|DINOv2 self-distillation confers stronger Cityscapes→ACDC robustness than MoCo/MAE]] — *running*
- `h15` [[h15_dense_contrastive_densecl_pixpro_segment|Dense contrastive (DenseCL/PixPro) + Segmenter decoder improves ACDC robustness]] — *idea*
<!-- crux:ledger:end -->
