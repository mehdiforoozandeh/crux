---
type: wiki
title: DINO (Self-Distillation with No Labels)
summary: Student-teacher self-distillation with a momentum teacher plus centering/sharpening that trains ViT to produce emergent, segmentation-friendly attention maps without labels or negatives.
category: method
sources: raw/caron2021_dino.pdf
created: 2026-07-11
updated: 2026-07-11
---

# DINO (Self-Distillation with No Labels)

DINO trains a student to match a momentum teacher's output distribution over K dimensions with cross-entropy — no negative pairs, no contrastive loss, no predictor — yet the resulting ViT [[vision-transformer]] attention maps segment objects with zero segmentation supervision.

## Teacher-student self-distillation

Both networks share architecture g = h∘f (backbone f, 3-layer MLP head h with ℓ2-normalization and weight-normalized final layer, K-dim output) but different parameters θs, θt, each outputting a softmax distribution with its own temperature (τs = 0.1; τt warmed from 0.04 to 0.07 over 30 epochs); the student minimizes H(Pt, Ps) = −Pt·log Ps. The teacher is not given a priori but built from past student iterations. Copying student weights into it fails to converge; freezing it for an epoch works surprisingly well; best is an EMA (momentum encoder) with λ on a cosine schedule from 0.996 to 1. Unlike momentum encoders in contrastive setups (a substitute for a memory queue), DINO's teacher acts like Polyak-Ruppert ensembling / Mean Teacher [[self-distillation]], outperforming the student throughout training and guiding it with higher-quality targets. Gradients flow only through the student via stop-gradient on the teacher.

## Multi-crop augmentation

From one image, DINO builds a set V of views: 2 global crops at 224² covering >50% of the image, plus several local crops at 96² covering <50%. All crops pass through the student; only global views pass through the teacher, forcing local-to-global correspondence. The loss sums H(Pt(x), Ps(x′)) over global x and all x′ ≠ x in V. Ablations show both multi-crop and momentum are required — dropping momentum collapses k-NN to 0.1%; dropping multi-crop drops it from 72.8% to 67.9%.

## Centering and sharpening to avoid collapse

No contrastive loss, clustering constraint, predictor, or batch norm is used. Centering adds an EMA-updated bias c to the teacher output (c ← mc + (1−m)·batch-mean of gθt(x)), stopping any one dimension from dominating but pushing toward uniform; sharpening (low τt) has the opposite tendency. Together they balance out and suffice to prevent collapse given a momentum teacher; centering depends only on first-order batch statistics, so it stays robust across batch sizes.

## Emergent segmentation

Self-attention from the [CLS] token in the last block's heads, thresholded to keep 60% of the mass, gives Jaccard similarity vs. ground truth on PASCAL VOC12 of 44.7-45.9% for DINO ViT-S/8, vs. 21.8-23.7% for an identically-architected supervised ViT — this only emerges from self-distillation, not supervised training or convnets, and different heads localize different objects even under occlusion. DINO reaches 78.3% top-1 k-NN and 80.1% linear on ImageNet with ViT-B/8; on DAVIS-2017 video segmentation via nearest-neighbor propagation of frozen features it hits 71.4 (J&F)m, rivaling methods built for dense/video tasks.

## See also

Related:: [[self-distillation]] [[vision-transformer]] [[dinov2]] [[moco]] [[simclr]] [[contrastive-learning]] [[ibot]] [[segmentation-decoders]]
