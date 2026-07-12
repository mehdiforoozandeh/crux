---
type: wiki
title: Self-Distillation (SSL)
summary: SSL family where a student network matches a momentum-averaged teacher's output on differently augmented views with no explicit negatives, spanning DINO, DINOv2, and (in its masked-patch form) iBOT.
category: concept
sources: raw/caron2021_dino.pdf, raw/oquab2023_dinov2.pdf, raw/zhou2021_ibot.pdf
created: 2026-07-11
updated: 2026-07-11
---

# Self-Distillation (SSL)

A student network gθs and a teacher network gθt share one architecture but different weights; the student minimizes cross-entropy H(Pt,Ps) = −Pt·log Ps between softmax'd K-dim outputs on augmented views, with gradients flowing only through the student via stop-gradient on the teacher — [[dino]]'s framing, reused verbatim by [[dinov2]] and [[ibot]].

## Teacher as EMA, not a fixed target

Unlike classic knowledge distillation, there is no pretrained teacher a priori: it is built from the student's own past iterations. [[dino]] tests copying student weights in (fails to converge), freezing the teacher for an epoch (works surprisingly well), and an exponential moving average θt ← λθt + (1−λ)θs with λ on a cosine schedule 0.996→1 (best). This differs from momentum encoders in contrastive setups, which substitute for a memory queue; here the EMA teacher performs Polyak-Ruppert-style ensembling, consistently outperforming the student and supplying it higher-quality targets throughout training (Mean Teacher-like). Softmax temperatures differ per network (student τs=0.1; teacher τt warmed 0.04→0.07), giving the teacher a sharper, more confident target distribution.

## Centering and sharpening jointly prevent collapse

With no contrastive loss, clustering constraint, predictor, or batch norm, [[dino]] shows collapse is avoided by exactly two operations on the teacher output: centering adds an EMA bias c to teacher logits (c ← mc + (1−m)·batch-mean(gθt)), which stops one dimension dominating but pushes toward the uniform distribution; sharpening (low τt) has the opposite tendency. Neither alone suffices, but combined with a momentum teacher they balance out. Ablations isolate the momentum encoder as the critical component: removing it collapses k-NN accuracy to 0.1% even with Sinkhorn-Knopp normalization added back; removing multi-crop drops k-NN from 72.8% to 67.9%; swapping cross-entropy for MSE drops it to 52.6%.

## Why attention maps become segmentation-relevant

Because the loss never uses labels, negatives, or a pixel-reconstruction target, the [CLS] token's last-block self-attention is free to encode whichever structure minimizes cross-view distillation error — empirically, object boundaries. Thresholding to keep 60% of attention mass yields Jaccard similarity of 44.7-45.9% (DINO ViT-S/8) against PASCAL VOC12 masks vs. 21.8-23.7% for an identically-trained supervised ViT; different heads localize different objects, surviving occlusion. [[ibot]] extends the same EMA-teacher mechanism to patch tokens (an "online tokenizer" replacing [[beit]]'s frozen dVAE), and [[dinov2]] sums both the image-level and iBOT patch-level losses, so the segmentation-relevant signal SegSSL exploits comes from a single shared teacher-student objective, not a task-specific head.

## See also

Related:: [[dino]] [[dinov2]] [[ibot]] [[overview]] [[vision-transformer]] [[masked-image-modeling]] [[beit]] [[contrastive-learning]] [[segmentation-decoders]]
