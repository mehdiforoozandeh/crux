---
id: q2
type: question
title: Which SSL objective family (contrastive vs masked-image-modeling vs self-distillation) transfers best to dense prediction?
parent: root
status: resolved
stale: false
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# q2 — Which SSL objective family (contrastive vs masked-image-modeling vs self-distillation) transfers best to dense prediction?

Parent:: [[segssl_label_efficient_segmentation]]

## Question

SegSSL pretrains ViT-B/16 encoders under three SSL families — contrastive (MoCo v3, DenseCL, PixPro), masked-image-modeling (MAE, BEiT), and self-distillation (DINO, iBOT) — then transfers to dense prediction via UPerNet (and lighter linear-probe/MLP heads) on ADE20K, Cityscapes, and VOC2012, plus a Cityscapes->ACDC domain-shift split (background: [[wiki/contrastive-learning]], [[wiki/self-distillation]]). Question 2 asks whether the pretext task itself predicts downstream dense-prediction quality, and specifically whether pixel/region-aligned pretext tasks (dense contrastive) have any inherent advantage over more global objectives (self-distillation, MIM).

## Answer so far

Self-distillation is the clear winner for dense-prediction transfer: iBOT/DINO pretraining beat both the best masked-image-modeling method (MAE, +1.5 mIoU ADE20K) and the best contrastive method (DenseCL, +2.6 mIoU ADE20K) with a UPerNet decoder, and the margin held under Cityscapes->ACDC domain shift (H1, supported). The intuitive bet that pixel-level contrastive objectives would transfer best because their pretext task is already "dense" was wrong — DenseCL/PixPro trailed iBOT everywhere and degraded worst under domain shift, so we're deprioritizing further dense-contrastive investment (H2, refuted). MAE is a viable fallback but only under full fine-tuning with an expressive decoder: it comes within 1.5-1.9 mIoU of iBOT on ADE20K and Cityscapes->ACDC, but collapses to a 9.4 mIoU gap under frozen linear probing, so it's unsuitable for light-decoder or feature-frozen settings (H3, partial). Net: standardize the SegSSL default pretraining recipe on iBOT/DINO (self-distillation) for dense-prediction downstream tasks, keep MAE as a fallback only when full fine-tuning budget is available, and shelve dense contrastive objectives (DenseCL/PixPro) for this program (see [[wiki/ibot]]).

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 1, partial 1, refuted 1, inconclusive 0)

- `h4` [[h4_self_distillation_ibot_dino_transfers_be|Self-distillation (iBOT/DINO) transfers best to dense prediction under UPerNet]] — *done* — verdict **supported**, metric `+2.6 mIoU ADE20K, +1.5 mIoU Cityscapes (iBOT vs best rival family, UPerNet)`
- `h5` [[h5_dense_pixel_contrastive_densecl_pixpro_t|Dense-pixel contrastive (DenseCL/PixPro) transfers best to dense prediction]] — *done* — verdict **refuted**, metric `-2.6 mIoU ADE20K vs iBOT (DenseCL, UPerNet)`
- `h6` [[h6_mae_mim_matches_self_distillation_only_u|MAE (MIM) matches self-distillation only under full fine-tuning, not linear probe]] — *done* — verdict **partial**, metric `-1.5 UPerNet / -9.4 linear-probe mIoU gap (MAE vs iBOT)`
<!-- crux:ledger:end -->
