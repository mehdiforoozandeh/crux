---
id: q1
type: question
title: Does self-supervised pretraining beat supervised ImageNet pretraining for downstream segmentation transfer (same encoder, same decoder, full labels)?
parent: root
status: resolved
stale: false
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# q1 — Does self-supervised pretraining beat supervised ImageNet pretraining for downstream segmentation transfer (same encoder, same decoder, full labels)?

Parent:: [[segssl_label_efficient_segmentation]]

## Question

SegSSL's foundational question: before comparing SSL families or decoders against one another, we test whether SSL pretraining is worth adopting at all versus the field-standard supervised ImageNet-1k init, holding encoder (ViT-B/16), decoder, and label budget (full) fixed. One representative method per SSL family is pitted against a supervised-pretrained baseline with an identical decoder: self-distillation (iBOT) and masked-image-modeling (MAE) under UPerNet on ADE20K and Cityscapes, and dense contrastive (DenseCL) under a Segmenter head on Pascal VOC 2012 (background: [[wiki/self-distillation]], [[wiki/masked-image-modeling]], [[wiki/contrastive-learning]]).

## Answer so far

Self-supervised pretraining does not uniformly beat supervised ImageNet init under matched encoder/decoder/full-label conditions — the win is family- and benchmark-dependent. Self-distillation (iBOT) is a clean, consistent winner with UPerNet, beating supervised init by +3.3 mIoU on ADE20K (49.6 vs 46.3) and +1.5 mIoU on Cityscapes (80.6 vs 79.1) across all three seeds, so it becomes the default SegSSL pretraining choice (H1, supported). Masked-image-modeling (MAE) only partially replicates this: it beats supervised under full fine-tuning (+1.8 mIoU ADE20K, 48.1 vs 46.3) but its frozen linear-probe features trail supervised by 6.7 mIoU (24.1 vs 30.8) and its Cityscapes margin misses the pre-registered +2.0 bar, so MAE's gain is a fine-tuning-only effect, not a general encoder-quality win (H2, partial). Dense contrastive pretraining (DenseCL) is refuted: with a Segmenter head it underperforms supervised init on Pascal VOC 2012 (-1.3 mIoU, -2.6 boundary-mIoU) and only marginally edges it on ADE20K (+0.7, below bar), so dense-correspondence objectives are deprioritized for full-label transfer (H3, refuted). Net: adopt SSL pretraining, but standardize on self-distillation (iBOT/DINO) rather than treating all SSL families as interchangeably better than supervised init.

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 1, partial 1, refuted 1, inconclusive 0)

- `h1` [[h1_ibot_upernet_beats_supervised_imagenet_i|iBOT+UPerNet beats supervised ImageNet init on ADE20K and Cityscapes under full FT]] — *done* — verdict **supported**, metric `+3.3 mIoU ADE20K, +1.5 mIoU Cityscapes (iBOT vs supervised, UPerNet, full FT)`
- `h2` [[h2_mae_beats_supervised_init_only_under_ful|MAE beats supervised init only under full fine-tuning, not frozen linear-probe transfer]] — *done* — verdict **partial**, metric `+1.8 mIoU ADE20K (full FT); -6.7 mIoU frozen linear-probe vs supervised`
- `h3` [[h3_densecl_dense_contrastive_pretraining_be|DenseCL dense-contrastive pretraining beats supervised init on VOC2012 transfer]] — *done* — verdict **refuted**, metric `-1.3 mIoU, -2.6 boundary-mIoU VOC2012 (DenseCL vs supervised, Segmenter)`
<!-- crux:ledger:end -->
