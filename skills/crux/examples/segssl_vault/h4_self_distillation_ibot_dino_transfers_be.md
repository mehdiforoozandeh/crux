---
id: h4
type: idea
title: Self-distillation (iBOT/DINO) transfers best to dense prediction under UPerNet
parent: q2
status: done
verdict: supported
metric: +2.6 mIoU ADE20K, +1.5 mIoU Cityscapes (iBOT vs best rival family, UPerNet)
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h4 — Self-distillation (iBOT/DINO) transfers best to dense prediction under UPerNet

Parent:: [[q2_which_ssl_objective_family_contrastive_v]]

## Problem Statement

Determine whether self-distillation pretraining (DINO/iBOT) yields dense-prediction transfer that beats contrastive and MIM pretraining once decoder capacity is held fixed at UPerNet (background: [[wiki/self-distillation]], [[wiki/dino]], [[wiki/ibot]]).

## Idea / Hypothesis

Self-distillation (iBOT/DINO) transfers best to dense prediction under UPerNet

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] iBOT+UPerNet ADE20K mIoU >= MAE+UPerNet ADE20K mIoU + 1.0
- [x] iBOT+UPerNet ADE20K mIoU >= DenseCL+UPerNet ADE20K mIoU + 2.0
- [x] iBOT+UPerNet Cityscapes mIoU >= supervised ImageNet-1k baseline + UPerNet Cityscapes mIoU + 1.0

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 84213

## Findings

iBOT/DINO self-distillation beat the best MIM method (MAE) by 1.5 mIoU (49.6 vs 48.1) and the best contrastive method (DenseCL) by 2.6 mIoU (49.6 vs 47.0) on ADE20K with UPerNet, and the advantage held on Cityscapes (80.6 vs 79.1 supervised baseline, +1.5). All three pre-registered bars were met. We attribute the gain to iBOT's patch-level distillation producing more spatially-grouped semantic features than instance-level contrastive objectives or raw pixel reconstruction.
