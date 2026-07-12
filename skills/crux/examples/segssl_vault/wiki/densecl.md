---
type: wiki
title: DenseCL
summary: Extends contrastive pretraining from single global image vectors to dense, pixel/region-level correspondence matching, directly targeting representations useful for dense prediction tasks like segmentation.
category: method
sources: raw/wang2020_densecl.pdf
created: 2026-07-11
updated: 2026-07-11
---

# DenseCL

DenseCL replaces the single global feature vector used by [[moco]]-style [[contrastive-learning]] with a dense grid of local feature vectors, turning the pretext task into pixel-level dictionary lookup instead of whole-image instance discrimination.

## Dense projection head

Built on top of MoCo-v2 as baseline, DenseCL adds a second projection head in parallel to the existing global head. The global head does global pooling + a two-layer MLP to output one 128-D vector per view. The dense head instead removes the pooling and replaces the MLP with two 1x1 convolution layers, so it keeps spatial structure and outputs a grid of dense feature vectors Θ ∈ R^(S×S×128) (default grid S=7, matching the 7x7 stride-32 backbone feature map for a 224x224 crop). The dense head has the same parameter count as the global head, and the two are trained end-to-end jointly.

## Dense correspondence and pairwise loss

For two augmented views of an image, backbone feature maps F1 and F2 are downsampled to S×S and compared via a cosine similarity matrix Δ ∈ R^(S²×S²); each of the S² feature vectors in view 1 is matched to its argmax-similarity partner in view 2 (Eq. 4), giving positive key t+ for each query r. The dense contrastive loss L_r is InfoNCE applied per grid cell and averaged over all S² positions, using pooled features from other images as negatives (dictionary size 65536, momentum 0.999, temperature 0.2). Total loss is L = (1-λ)L_q + λL_r with λ=0.5 balancing the global (L_q) and dense terms — chosen because pure dense training (λ=1.0) is unstable at initialization: with no reliable features yet, correspondence is noisy (a "chicken-and-egg" problem), so the global term or a λ warm-up is needed to bootstrap training.

## Ablations and results

Grid size matters: AP rises from 54.6 (S=1) to 56.7 (S=7) and plateaus beyond S=7. Matching by backbone features F (not by the dense-head output Θ) gives the best correspondence (56.7 vs 56.0 AP for random matching). Training overhead is under 1% (1'46" vs 1'45" per COCO epoch vs MoCo-v2). Over MoCo-v2, COCO-pretrained DenseCL gains +2.0% AP on PASCAL VOC detection, +1.1% AP / +0.9% AP (box/mask) on COCO, +3.0% mIoU on VOC segmentation, and +1.8% mIoU on [[cityscapes]] segmentation — evidence that dense correspondence pretraining transfers better to [[segmentation-decoders]] than image-level objectives, a theme later echoed by [[pixpro]] and relevant to [[label-efficiency]] under limited fine-tuning data.

## See also

Related:: [[contrastive-learning]] [[pixpro]] [[label-efficiency]] [[moco]] [[cityscapes]] [[segmentation-decoders]]
