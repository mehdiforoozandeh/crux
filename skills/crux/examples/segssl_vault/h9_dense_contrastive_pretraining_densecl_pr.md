---
id: h9
type: idea
title: Dense contrastive pretraining (DenseCL) preserves low-label mIoU better than global SSL
parent: q3
status: done
verdict: refuted
metric: 51.8 mIoU at 1% labels (DenseCL, -0.6 vs supervised, 64.7% retention)
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h9 — Dense contrastive pretraining (DenseCL) preserves low-label mIoU better than global SSL

Parent:: [[q3_how_far_can_the_labeled_data_budget_drop]]

## Problem Statement

Test whether DenseCL's pixel-level contrastive pretext, which should transfer more directly to dense prediction, gives Cityscapes segmentation extra robustness at extreme low-label budgets (1%) versus global contrastive and supervised init. (background: [[wiki/densecl]], [[wiki/contrastive-learning]])

## Idea / Hypothesis

Dense contrastive pretraining (DenseCL) preserves low-label mIoU better than global SSL

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] DenseCL init mIoU >= DINOv2 init mIoU at 10% labels
- [ ] DenseCL 1%-label retention rate >= supervised 1%-label retention rate
- [ ] DenseCL beats MoCo v3 by >=2.0 mIoU at 1% labels

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 84527, wandb seg-ssl/label-budget-densecl

## Findings

DenseCL-pretrained ViT-B/16 + UPerNet underperforms DINOv2 at 10% labels (70.9 vs 76.8 mIoU), and its 1%-label retention (64.7%) is no better than the supervised baseline (66.2%) -- it actually finishes marginally below supervised at 1% (51.8 vs 52.4 mIoU) and trails plain MoCo v3 (52.6 mIoU at 1%). The pixel-level pretext objective conferred no measurable low-label robustness advantage over global contrastive or supervised init; none of the three pre-registered bars were met. See [[wiki/moco]] for the global contrastive baseline DenseCL is compared against.
