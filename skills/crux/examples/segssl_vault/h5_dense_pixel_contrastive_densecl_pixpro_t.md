---
id: h5
type: idea
title: Dense-pixel contrastive (DenseCL/PixPro) transfers best to dense prediction
parent: q2
status: done
verdict: refuted
metric: -2.6 mIoU ADE20K vs iBOT (DenseCL, UPerNet)
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h5 — Dense-pixel contrastive (DenseCL/PixPro) transfers best to dense prediction

Parent:: [[q2_which_ssl_objective_family_contrastive_v]]

## Problem Statement

Test whether dense/pixel-level contrastive pretext tasks (DenseCL, PixPro), which explicitly optimize spatial correspondence, transfer better to dense prediction than instance-level contrastive, MIM, or self-distillation objectives, since their pretext task appears most aligned with the downstream task (background: [[wiki/densecl]], [[wiki/pixpro]], [[wiki/contrastive-learning]]).

## Idea / Hypothesis

Dense-pixel contrastive (DenseCL/PixPro) transfers best to dense prediction

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] DenseCL+UPerNet ADE20K mIoU >= iBOT+UPerNet ADE20K mIoU
- [ ] DenseCL+UPerNet ADE20K mIoU >= MAE+UPerNet ADE20K mIoU + 1.0
- [ ] DenseCL+UPerNet Cityscapes->ACDC domain-shift mIoU >= DINO+UPerNet domain-shift mIoU - 1.0

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 84391

## Findings

Despite optimizing pixel/region-level correspondence directly, DenseCL and PixPro underperformed iBOT by 2.6 mIoU on ADE20K (47.0 vs 49.6) and even trailed MAE (48.1). Under Cityscapes->ACDC domain shift the gap widened further (DenseCL 38.2 vs iBOT 42.0, PixPro 37.9), suggesting dense contrastive objectives overfit to ImageNet's object-centric layout rather than learning weather/appearance-robust features. None of the three pre-registered bars were met.
