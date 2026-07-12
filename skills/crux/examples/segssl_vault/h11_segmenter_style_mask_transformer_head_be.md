---
id: h11
type: idea
title: Segmenter-style mask-transformer head best exploits frozen DINOv2/iBOT tokens
parent: q4
status: done
verdict: supported
metric: "ADE20K mIoU: mask-transformer+frozen DINOv2 49.5 vs UPerNet+frozen DINOv2 48.5 (+1.0), vs full fine-tune 49.8 (-0.3 gap); decoder params 12M vs UPerNet's 22M (55%)"
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:55"
---

# h11 — Segmenter-style mask-transformer head best exploits frozen DINOv2/iBOT tokens

Parent:: [[q4_which_decoder_head_design_best_exploits_]]

## Problem Statement

Convolutional decoders like UPerNet may not be the right inductive bias for self-distillation ([[wiki/self-distillation]]) features, whose patch tokens already carry strong global semantic structure from teacher-student distillation; a query-based mask-transformer head might read this out more directly and cheaply.

## Idea / Hypothesis

Segmenter-style mask-transformer head best exploits frozen DINOv2/iBOT tokens

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Mask-transformer head mIoU on frozen DINOv2 >= UPerNet-on-frozen-DINOv2 mIoU on ADE20K
- [x] Mask-transformer head reaches within 1.0 mIoU of full fine-tuning on ADE20K for DINOv2
- [x] Mask-transformer decoder uses <=60% of UPerNet's decoder parameters/FLOPs

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 85110 (wandb: q4-masktransformer-dinov2)

## Findings

All three pre-registered bars were met: the mask-transformer beat UPerNet on the same frozen features, closed to within 0.3 mIoU of full fine-tuning, and did so with 55% of the parameter budget. The same pattern replicated on frozen iBOT (47.9 vs UPerNet 47.1), supporting the mechanism that query-token cross-attention exploits the semantic clustering self-distillation objectives ([[wiki/dinov2]], [[wiki/ibot]]) induce in patch tokens, something convolutional multi-scale fusion captures less directly.
