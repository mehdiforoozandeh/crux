---
id: h10
type: idea
title: UPerNet decoder on frozen features closes the fine-tuning gap to <=2 mIoU on ADE20K
parent: q4
status: done
verdict: partial
metric: "ADE20K mIoU (frozen UPerNet vs fine-tuned UPerNet): DINO 46.8 vs 48.2 (-1.4), DINOv2 48.5 vs 49.8 (-1.3), MoCo v3 43.6 vs 45.1 (-1.5), MAE 41.3 vs 48.1 (-6.8)"
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h10 — UPerNet decoder on frozen features closes the fine-tuning gap to <=2 mIoU on ADE20K

Parent:: [[q4_which_decoder_head_design_best_exploits_]]

## Problem Statement

Full fine-tuning is expensive at scale; if a UPerNet decoder trained on top of a frozen encoder can match fine-tuned mIoU closely, we can skip encoder fine-tuning entirely across SSL families.

## Idea / Hypothesis

UPerNet decoder on frozen features closes the fine-tuning gap to <=2 mIoU on ADE20K

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] UPerNet+frozen-encoder mIoU is within 2.0 mIoU of full fine-tuned UPerNet on ADE20K, for DINO, DINOv2, MoCo v3, and MAE backbones
- [ ] UPerNet+frozen-encoder improves >=8.0 mIoU over a linear probe on the same frozen features, for all four backbones

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 84532 (wandb: q4-upernet-frozen-sweep)

## Findings

The <=2.0 mIoU bar was met for DINO, DINOv2, and MoCo v3 but missed by 4.8 points for MAE, so only 3 of 4 backbones satisfy the first verifiable. The >=8 mIoU improvement over linear probe held for every backbone (e.g. MAE: 41.3 vs 24.1 linear probe, +17.2), confirming UPerNet's ([[wiki/segmentation-decoders]]) multi-scale fusion always helps but cannot fully compensate for MIM features' ([[wiki/masked-image-modeling]]) weak linear separability without decoder-side spatial context beyond what UPerNet provides.
