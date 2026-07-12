---
id: h12
type: idea
title: Linear probe on frozen encoders reaches within 5 mIoU of fine-tuning on Cityscapes
parent: q4
status: done
verdict: refuted
metric: "Cityscapes mIoU (linear probe vs full fine-tune): DINO 61.2 vs 79.4 (-18.2, 77%), MAE 52.1 vs 76.8 (-24.7, 68%), DenseCL 58.7 vs 78.1 (-19.4, 75%)"
created: "2026-07-11T19:38:55"
updated: "2026-07-11T19:38:55"
---

# h12 — Linear probe on frozen encoders reaches within 5 mIoU of fine-tuning on Cityscapes

Parent:: [[q4_which_decoder_head_design_best_exploits_]]

## Problem Statement

If a cheap linear probe were sufficient for dense prediction, it would let us skip decoder training entirely and use probe accuracy as a fast proxy for encoder quality across the SegSSL sweep ([[wiki/label-efficiency]]).

## Idea / Hypothesis

Linear probe on frozen encoders reaches within 5 mIoU of fine-tuning on Cityscapes

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Linear probe mIoU is within 5.0 mIoU of full fine-tuned UPerNet on Cityscapes, for DINO, MAE, and DenseCL backbones
- [ ] Linear probe mIoU reaches >=90% of full fine-tuned mIoU for at least one SSL family

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 83920 (wandb: q4-linearprobe-cityscapes)

## Findings

Both verifiables failed for every backbone tested — gaps ranged from 18.2 to 24.7 mIoU, far outside the 5.0 mIoU bar, and no family reached the 90% relative-performance threshold. Cityscapes' fine urban boundaries expose that frozen tokens, however strong under linear evaluation on classification benchmarks, do not carry enough spatially-precise information for a linear layer to resolve dense boundaries; probe mIoU is therefore not usable as a proxy for encoder quality on segmentation and should be dropped as a serious decoder candidate (background: [[wiki/masked-image-modeling]], [[wiki/contrastive-learning]]).
