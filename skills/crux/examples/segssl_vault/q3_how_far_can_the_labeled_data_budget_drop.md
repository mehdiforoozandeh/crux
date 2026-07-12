---
id: q3
type: question
title: How far can the labeled-data budget drop (100% -> 10% -> 1%) before fine-tuned segmentation collapses, and does SSL pretraining shift that curve?
parent: root
status: resolved
stale: false
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# q3 — How far can the labeled-data budget drop (100% -> 10% -> 1%) before fine-tuned segmentation collapses, and does SSL pretraining shift that curve?

Parent:: [[segssl_label_efficient_segmentation]]

## Question

Every SegSSL pretraining family looks similar at 100% labels, but real deployments rarely have full annotation budgets. This question fine-tunes ViT-B/16 + UPerNet on Cityscapes at 100%, 10%, and 1% of labels under different pretraining inits (supervised, DINOv2, MAE, DenseCL, MoCo v3) to see whether SSL pretraining merely offsets the mIoU curve or actually reshapes where fine-tuned segmentation collapses under label scarcity. (background: [[wiki/cityscapes]], [[wiki/segmentation-decoders]])

## Answer so far

Yes — the collapse point is not fixed by data scale alone; pretraining family shifts it substantially. DINOv2 self-distillation is the clear winner: it retains 81.2% of full-label mIoU at 1% labels versus 66.2% for supervised init, and its margin over supervised grows as labels shrink (+1.3 mIoU at 100% to +12.9 mIoU at 1%), confirming self-distillation actively delays collapse rather than just adding a constant offset. MAE gives a real but shrinking edge — it beats supervised at every budget but the advantage falls to +0.7 mIoU by 1% labels and misses the pre-registered retention bar, so MIM should be treated as a mild regularizer, not a low-label rescue plan. DenseCL's pixel-level contrastive pretext showed no low-label advantage at all, finishing at or below both supervised init and plain MoCo v3 at 1% labels, refuting the idea that dense pretext design predicts label efficiency. Recommendation: standardize on DINOv2 + UPerNet for any deployment under 10% label budget, and deprioritize dense-contrastive pretraining in the low-label track. (background: [[wiki/label-efficiency]])

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 1, partial 1, refuted 1, inconclusive 0)

- `h7` [[h7_dinov2_self_distillation_pretraining_fla|DINOv2 self-distillation pretraining flattens the mIoU-vs-label-budget curve on Cityscapes]] — *done* — verdict **supported**, metric `65.3 mIoU at 1% labels (DINOv2, +12.9 vs supervised, 81.2% retention)`
- `h8` [[h8_mae_pretraining_narrows_but_doesn_t_prev|MAE pretraining narrows but doesn't prevent collapse at 1% labels versus supervised init]] — *done* — verdict **partial**, metric `53.1 mIoU at 1% labels (MAE, +0.7 vs supervised, 65.9% retention)`
- `h9` [[h9_dense_contrastive_pretraining_densecl_pr|Dense contrastive pretraining (DenseCL) preserves low-label mIoU better than global SSL]] — *done* — verdict **refuted**, metric `51.8 mIoU at 1% labels (DenseCL, -0.6 vs supervised, 64.7% retention)`
<!-- crux:ledger:end -->
