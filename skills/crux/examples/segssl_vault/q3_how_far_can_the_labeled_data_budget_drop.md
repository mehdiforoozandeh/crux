---
id: q3
type: question
title: How far can the labeled-data budget drop (100% -> 10% -> 1%) before fine-tuned segmentation collapses, and does SSL pretraining shift that curve?
parent: root
status: resolved
stale: false
created: "2026-07-11T19:38:54"
updated: "2026-07-24T15:26:44"
---

# q3 — How far can the labeled-data budget drop (100% -> 10% -> 1%) before fine-tuned segmentation collapses, and does SSL pretraining shift that curve?

Parent:: [[segssl_label_efficient_segmentation]]

## Question

Every SegSSL pretraining family looks similar at 100% labels, but real deployments rarely have full annotation budgets. This question fine-tunes ViT-B/16 + UPerNet on Cityscapes at 100%, 10%, and 1% of labels under different pretraining inits (supervised, DINOv2, MAE, DenseCL, MoCo v3) to see whether SSL pretraining merely offsets the mIoU curve or actually reshapes where fine-tuned segmentation collapses under label scarcity. (background: [[wiki/cityscapes]], [[wiki/segmentation-decoders]])

## Answer so far

Yes — the collapse point is not fixed by data scale alone; pretraining family shifts it substantially. DINOv2 self-distillation is the clear winner: it retains 81.2% of full-label mIoU at 1% labels versus 66.2% for supervised init, and its margin over supervised grows as labels shrink (+1.3 mIoU at 100% to +12.9 mIoU at 1%), confirming self-distillation actively delays collapse rather than just adding a constant offset. MAE gives a real but shrinking edge — it beats supervised at every budget but the advantage falls to +0.7 mIoU by 1% labels and misses the pre-registered retention threshold, so MIM should be treated as a mild regularizer, not a low-label rescue plan. DenseCL's pixel-level contrastive pretext showed no low-label advantage at all, finishing at or below both supervised init and plain MoCo v3 at 1% labels, refuting the idea that dense pretext design predicts label efficiency. Recommendation: standardize on DINOv2 + UPerNet for any deployment under 10% label budget, and deprioritize dense-contrastive pretraining in the low-label track. (background: [[wiki/label-efficiency]])

<!-- crux:ledger:start -->
**3 children** · open 0, leaning 1, settled 2, parked 0 · 1 finding(s) on this question

- `h7` [[h7_dinov2_self_distillation_pretraining_fla|DINOv2 self-distillation pretraining flattens the mIoU-vs-label-budget curve on Cityscapes]] — *settled · strong*
- `h8` [[h8_mae_pretraining_narrows_but_doesn_t_prev|MAE pretraining narrows but doesn't prevent collapse at 1% labels versus supervised init]] — *leaning · weak*
- `h9` [[h9_dense_contrastive_pretraining_densecl_pr|Dense contrastive pretraining (DenseCL) preserves low-label mIoU better than global SSL]] — *settled · strong*
- `f17` finding (strong) [[f17_label_budget_dinov2_moves_the_collapse_p|Label budget — DINOv2 moves the collapse point, it doesn't just offset the curve]]
<!-- crux:ledger:end -->
