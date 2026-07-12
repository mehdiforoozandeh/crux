---
id: h14
type: idea
title: DINOv2 self-distillation confers stronger Cityscapes→ACDC robustness than MoCo/MAE
parent: q5
status: running
verdict: 
metric: 
created: "2026-07-11T19:38:55"
updated: "2026-07-11T19:38:55"
---

# h14 — DINOv2 self-distillation confers stronger Cityscapes→ACDC robustness than MoCo/MAE

Parent:: [[q5_does_ssl_pretraining_confer_robustness_t]]

## Problem Statement

DINO/DINOv2's multi-crop self-distillation (see [[wiki/dinov2]], [[wiki/self-distillation]]) trains local-to-global crop correspondence under strong color-jitter, grayscale, and blur augmentation. That augmentation policy overlaps substantially with the appearance perturbations in ACDC (fog, low light, rain streaks, snow glare), so self-distilled features may be more contrast- and illumination-invariant than contrastive (MoCo; see [[wiki/moco]]) or reconstruction-based (MAE) encoders, translating into better zero-shot domain-shift robustness.

## Idea / Hypothesis

DINOv2 self-distillation confers stronger Cityscapes→ACDC robustness than MoCo/MAE

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] ACDC-mean mIoU gain over the H1 MAE arm ≥ +3.0 mIoU
- [ ] ACDC-night mIoU gain over supervised baseline ≥ +4.0 mIoU
- [ ] Relative clear→ACDC-mean degradation reduced by ≥20% relative vs. supervised baseline

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 92210 (wandb seg-h5-dinov2-acdc)

## Findings

_(written by the PI/agent when the case is closed)_
