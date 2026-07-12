---
id: h1
type: idea
title: iBOT+UPerNet beats supervised ImageNet init on ADE20K and Cityscapes under full FT
parent: q1
status: done
verdict: supported
metric: +3.3 mIoU ADE20K, +1.5 mIoU Cityscapes (iBOT vs supervised, UPerNet, full FT)
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h1 — iBOT+UPerNet beats supervised ImageNet init on ADE20K and Cityscapes under full FT

Parent:: [[q1_does_self_supervised_pretraining_beat_su]]

## Problem Statement

Self-distillation ([[wiki/self-distillation]]) (DINO/iBOT-family, [[wiki/ibot]]) is claimed to learn stronger local/dense semantic features than supervised classification pretraining; we test whether that yields a segmentation-transfer win over supervised ImageNet-1k init once both use an identical ViT-B/16 encoder and UPerNet decoder ([[wiki/segmentation-decoders]]) under full fine-tuning.

## Idea / Hypothesis

iBOT+UPerNet beats supervised ImageNet init on ADE20K and Cityscapes under full FT

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] iBOT+UPerNet ADE20K val mIoU >= supervised+UPerNet ADE20K val mIoU + 2.0 (3-seed mean)
- [x] iBOT+UPerNet Cityscapes val mIoU >= supervised+UPerNet Cityscapes val mIoU + 1.0 (3-seed mean)
- [x] Gain holds in all 3 seeds (no seed regresses to or below the supervised baseline)

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 83612 (wandb segssl/q1-ibot-vs-sup)

## Findings

iBOT-pretrained ViT-B/16 beat the supervised ImageNet-1k baseline by 3.3 mIoU on ADE20K (49.6 vs 46.3) and 1.5 mIoU on Cityscapes (80.6 vs 79.1) with an identical UPerNet decoder under full fine-tuning, and the gain held across all three seeds. All three pre-registered bars were met. The result is consistent with self-distillation learning more spatially-grouped semantic features than supervised classification pretraining, and it sets iBOT/DINO as the SegSSL default.
