---
id: h8
type: idea
title: MAE pretraining narrows but doesn't prevent collapse at 1% labels versus supervised init
parent: q3
status: done
verdict: partial
metric: 53.1 mIoU at 1% labels (MAE, +0.7 vs supervised, 65.9% retention)
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h8 — MAE pretraining narrows but doesn't prevent collapse at 1% labels versus supervised init

Parent:: [[q3_how_far_can_the_labeled_data_budget_drop]]

## Problem Statement

Test whether MAE's masked-image-modeling pretraining preserves segmentation quality as the labeled-data budget shrinks from 100% to 1%, or whether its benefit is concentrated at high-label budgets. (background: [[wiki/mae]], [[wiki/masked-image-modeling]])

## Idea / Hypothesis

MAE pretraining narrows but doesn't prevent collapse at 1% labels versus supervised init

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] MAE init mIoU >= supervised init + 3.0 mIoU at 10% labels
- [ ] MAE init retains >=75% of its own 100%-label mIoU at 1% labels
- [ ] MAE init beats supervised init by >=0.5 mIoU at every budget (100%/10%/1%)

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 84519, wandb seg-ssl/label-budget-mae

## Findings

MAE-pretrained ViT-B/16 + UPerNet beats supervised init at every budget (80.6 vs 79.1 at 100%, 73.5 vs 71.2 at 10%, 53.1 vs 52.4 at 1%), so the weakest bar holds. But the margin shrinks to +0.7 mIoU at 1% labels and MAE retains only 65.9% of its full-data mIoU, missing both the 10%-margin bar (+2.3 vs the required +3.0) and the 1%-retention bar (65.9% vs required 75%) -- MAE needs substantial fine-tuning data to express its representation quality. (compare [[wiki/label-efficiency]])
