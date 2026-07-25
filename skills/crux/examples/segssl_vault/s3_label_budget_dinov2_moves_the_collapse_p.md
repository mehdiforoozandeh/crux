---
id: s3
type: synthesis
title: Label budget — DINOv2 moves the collapse point, it doesn't just offset the curve
approved: "2026-07-24T15:26:44"
created: "2026-07-24T15:26:44"
updated: "2026-07-24T15:26:44"
---

# Synthesis — Label budget — DINOv2 moves the collapse point, it doesn't just offset the curve

Related:: [[q3_how_far_can_the_labeled_data_budget_drop]]

## Headline conclusions

- **The collapse point is a function of pretraining, not only data scale.** DINOv2 retains 81.2% of full-label mIoU at 1% labels vs 66.2% for supervised init.
- **The margin grows as labels shrink** (+1.3 mIoU at 100% → +12.9 at 1%) — the signature of delayed collapse rather than a constant offset.
- **MAE is a mild regularizer, not a rescue.** Its edge decays to +0.7 mIoU at 1% and missed the retention bar; DenseCL showed no low-label advantage at all.

## Cross-run table

| id | hypothesis | verdict | headline metric |
|----|------------|---------|-----------------|
| `h7` | [[h7_dinov2_self_distillation_pretraining_fla\|DINOv2 self-distillation pretraining flattens the mIoU-vs-label-budget curve on Cityscapes]] | **supported** | 65.3 mIoU at 1% labels (DINOv2, +12.9 vs supervised, 81.2% retention) |
| `h8` | [[h8_mae_pretraining_narrows_but_doesn_t_prev\|MAE pretraining narrows but doesn't prevent collapse at 1% labels versus supervised init]] | **partial** | 53.1 mIoU at 1% labels (MAE, +0.7 vs supervised, 65.9% retention) |
| `h9` | [[h9_dense_contrastive_pretraining_densecl_pr\|Dense contrastive pretraining (DenseCL) preserves low-label mIoU better than global SSL]] | **refuted** | 51.8 mIoU at 1% labels (DenseCL, -0.6 vs supervised, 64.7% retention) |

## Implications for next batch

Standardize on DINOv2 + UPerNet for any deployment under a 10% label budget. Drop dense-contrastive pretraining from the low-label track entirely.
