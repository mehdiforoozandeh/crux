---
type: wiki
title: DINOv2
summary: Scaled-up, curated-data successor to DINO combining self-distillation with an iBOT-style masked-patch loss to produce general-purpose, frozen-feature-ready ViT representations.
category: method
sources: raw/oquab2023_dinov2.pdf
created: 2026-07-11
updated: 2026-07-11
---

# DINOv2

DINOv2 (Oquab et al., 2023) shows self-supervised pretraining, given enough automatically curated data, yields frozen features that match or beat weakly-supervised models like OpenCLIP at both image and pixel level, with no finetuning.

## Data-curation pipeline

The bet: data quality, not just scale, unlocks general-purpose features — prior attempts to scale [[self-distillation]] past ImageNet-1k onto uncurated data dropped feature quality. DINOv2 builds LVD-142M (142M images) via a metadata-free retrieval pipeline: a 1.2B-image raw web pool is deduplicated (PCA hashing plus copy-detection against benchmark test/val sets), NSFW-filtered, and face-blurred. Curated seed sets (ImageNet-22k, ImageNet-1k, Google Landmarks, fine-grained datasets) and the uncurated pool are embedded with a self-supervised ViT-H/16; cosine similarity plus k-means clustering drives retrieval of N=4 nearest neighbors per seed image, via Faiss GPU indices across 20 nodes x 8 V100s in under two days. LVD-142M beats both ImageNet-22k and a size-matched uncurated sample on most benchmarks, including domains untouched by curation seeds (iNaturalist, Places205).

## Combined image- and patch-level loss

Training merges DINO's image-level loss with [[ibot]]'s patch-level loss under SwAV-style centering, with a student/EMA-teacher pair as in [[dino]]. The image-level term is cross-entropy between softmax'd "prototype scores" from student/teacher class tokens of different crops: L_DINO = −Σ p_t log p_s. The patch-level term masks student input patches only; student and teacher iBOT heads process masked-token and corresponding visible-token pairs, cross-entropy over masked indices i: L_iBOT = −Σ_i p_ti log p_si. Centering is DINO's EMA softmax-centering or 3-iteration Sinkhorn-Knopp normalization from SwAV. Unlike iBOT, which shares the DINO/iBOT head, DINOv2 unties them, better at scale. A KoLeo regularizer spreads ℓ2-normalized batch features by nearest-neighbor distance; a short final phase raises resolution to 518x518 for pixel-level tasks. Ablations chain these from an iBOT baseline (72.9 k-NN, ViT-L/ImageNet-22k) to full DINOv2 (82.0 k-NN).

## Efficient training and distillation

Engineering targets scale: custom FlashAttention, "sequence-packing" of variable-length crop tokens under a block-diagonal attention mask, stochastic depth that skips (not masks) dropped residuals at a 40% drop rate, and FSDP sharding with float16 gradient reduction — together ~2x faster, 1/3 the memory of iBOT's codebase. The flagship ViT-g/14 (1.1B params, 1536-dim embeddings, 24 heads) trains directly; smaller variants distill from the frozen ViT-g teacher rather than train from scratch, which wins even for ViT-L.

## Frozen backbone for dense prediction

Because the objective supervises both class and patch tokens, DINOv2 features transfer to pixel-level tasks — segmentation, monocular depth — while frozen, unlike MAE features that need supervised finetuning. Evaluated frozen across eight task families (image/fine-grained classification, retrieval, ImageNet-{A,R,Sketch}, video, segmentation, depth), it closes most of the gap to weakly-supervised features at matched FLOPs, motivating use as an off-the-shelf backbone.

## See also

Related:: [[dino]] [[ibot]] [[self-distillation]] [[label-efficiency]] [[vision-transformer]] [[masked-image-modeling]] [[mae]]
