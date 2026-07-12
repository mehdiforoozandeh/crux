---
type: wiki
title: Contrastive Learning (SSL)
summary: SSL family that learns representations by pulling augmented views of the same image together and pushing different images apart, spanning image-level (SimCLR, MoCo) and dense/pixel-level (DenseCL, PixPro) formulations.
category: concept
sources: raw/chen2020_simclr.pdf, raw/he2019_moco.pdf, raw/wang2020_densecl.pdf, raw/xie2020_pixpro.pdf
created: 2026-07-11
updated: 2026-07-11
---

# Contrastive Learning (SSL)

All four methods optimize the same InfoNCE-style objective — pull a query toward its positive key, push it away from negatives — but differ in what counts as a "key": a whole augmented view (image-level) or a matched pixel/local feature (dense).

## Image-level: instance discrimination

[[simclr]] treats each image as its own class: two augmented views (random crop+resize, color distortion, Gaussian blur) form a positive pair, and the other 2(N-1) views in the minibatch are negatives, scored with NT-Xent (normalized temperature-scaled cross-entropy, cosine similarity / τ). Its ablations show composing crop with color distortion is critical (single augmentations alone let the net cheat on color histograms), a nonlinear projection head g(·) before the loss adds +3% over linear and >10% over none, and large batches (256–8192, LARS optimizer) substitute for a memory bank. ResNet-50 (4x) reaches 76.5% top-1 linear-eval accuracy on ImageNet, a 7% relative gain over prior SOTA, and 85.8% top-5 fine-tuned on 1% of labels.

[[moco]] reframes contrastive learning as dictionary look-up and decouples dictionary size from batch size via a queue of past-minibatch keys plus a momentum-updated key encoder (θk ← mθk + (1−m)θq, best at m=0.999), avoiding the memory-bank staleness problem. With K=65536 negatives it hits 60.6% top-1 (linear eval) and, more importantly, is the first unsupervised method to outperform ImageNet-supervised pretraining on 7 of 7 detection/segmentation transfer tasks (VOC, COCO, LVIS, Cityscapes), closing the classification-vs-transfer gap that motivated the dense methods below.

## Dense/pixel-level: closing the gap with dense tasks

[[densecl]] argues image-level pretext tasks are suboptimal for per-pixel downstream tasks and adds a second, parallel dense projection head (1x1 convs) producing a feature map instead of a single vector; correspondence between two views' dense features is found by argmax cosine similarity, and a dense InfoNCE loss L_r is combined with the global loss L_q as (1−λ)L_q + λL_r (λ=0.5). Built directly on MoCo v2, it costs <1% extra compute yet gains +2.0% AP (VOC detection), +0.9% AP (COCO instance seg), +3.0% mIoU (VOC seg), +1.8% mIoU ([[cityscapes]] seg).

[[pixpro]] goes further, replacing contrastive negatives with a pixel-to-propagation consistency (PPC) loss: a pixel propagation module (PPM) smooths each pixel's feature by similarity-weighted aggregation over all same-image pixels (sharpness exponent γ=2), and an asymmetric architecture forces consistency between this propagated view and a plain momentum-encoder view (cosine loss, no negatives needed). It beats its own PixContrast (negatives-based) ablation and MoCo v2/DenseCL/InfoMin, reaching 60.2 AP (VOC, R50-C4), 41.4/40.5 mAP (COCO FPN/C4), and 77.2 mIoU (Cityscapes), and combines additively with an instance-level SimCLR-style loss for further ImageNet linear-eval gains.

## See also

Related:: [[overview]], [[moco]], [[simclr]], [[densecl]], [[pixpro]], [[masked-image-modeling]], [[self-distillation]], [[label-efficiency]], [[segmentation-decoders]]
