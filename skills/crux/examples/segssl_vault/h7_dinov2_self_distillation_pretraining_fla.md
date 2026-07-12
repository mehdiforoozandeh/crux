---
id: h7
type: idea
title: DINOv2 self-distillation pretraining flattens the mIoU-vs-label-budget curve on Cityscapes
parent: q3
status: done
verdict: supported
metric: 65.3 mIoU at 1% labels (DINOv2, +12.9 vs supervised, 81.2% retention)
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h7 — DINOv2 self-distillation pretraining flattens the mIoU-vs-label-budget curve on Cityscapes

Parent:: [[q3_how_far_can_the_labeled_data_budget_drop]]

## Problem Statement

Test whether self-distillation SSL (DINOv2) meaningfully shifts the label-efficiency collapse curve, rather than just adding a constant mIoU offset over supervised init. (background: [[wiki/dinov2]], [[wiki/self-distillation]])

## Idea / Hypothesis

DINOv2 self-distillation pretraining flattens the mIoU-vs-label-budget curve on Cityscapes

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] DINOv2 init UPerNet mIoU at 10% labels >= supervised init + 4.0 mIoU on Cityscapes
- [x] DINOv2 init retains >=80% of its own 100%-label mIoU at 1% labels (supervised must retain <70%)
- [x] The DINOv2-vs-supervised mIoU gap widens (not shrinks) going from 10% to 1% labels

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 84512, wandb seg-ssl/label-budget-dinov2

## Findings

DINOv2-pretrained ViT-B/16 + UPerNet scores 80.4 mIoU at 100% labels, 76.8 at 10% (-3.6), and 65.3 at 1% (-15.1), retaining 81.2% of full-data performance versus 66.2% for the supervised-init baseline over the same drop. The DINOv2-vs-supervised gap widens from +1.3 mIoU at 100% to +5.6 at 10% to +12.9 at 1%, showing self-distillation actively delays collapse rather than adding a fixed offset. All three pre-registered bars were met. DINOv2 builds directly on the [[wiki/dino]] self-distillation lineage.
