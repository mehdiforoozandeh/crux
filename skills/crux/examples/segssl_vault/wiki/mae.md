---
type: wiki
title: Masked Autoencoders (MAE)
summary: Asymmetric encoder-decoder that reconstructs heavily masked (75%) image patches in pixel space, yielding strong ViT initializations for dense prediction with minimal labeled fine-tuning.
category: method
sources: raw/he2021_mae.pdf
created: 2026-07-11
updated: 2026-07-11
---

# Masked Autoencoders (MAE)

MAE masks a very high proportion of random image patches and trains a [[vision-transformer]] to reconstruct their raw pixels, treating [[masked-image-modeling]] as a denoising task made hard enough by masking ratio alone, with no augmentation and no tokenizer required.

## Masking and asymmetric encoder-decoder

An image is divided into regular non-overlapping patches (as in ViT); a random subset is sampled without replacement (uniform "random sampling", no center bias) and removed. The encoder is a standard ViT applied only to the visible patches (e.g., 25% at the default 75% ratio) — no mask tokens enter it, so it never sees a corrupted-looking input. The full token set (encoded visible patches + shared learned mask tokens, positional embeddings re-added to all) then goes to a lightweight decoder — a separate, narrower, shallower Transformer stack (default: 8 blocks, 512-d, <10% of encoder FLOPs per token) — which reconstructs the complete image. The decoder is discarded after pre-training; only the encoder is kept for recognition, decoupling its design from downstream needs. Skipping mask tokens in the encoder cuts training FLOPs by 3.3x, gives 2.8-4.1x wall-clock speedup, and improves accuracy versus an encoder that processes them.

## Masking ratio and reconstruction target

75% masking is optimal for both fine-tuning (84.9%) and linear probing (73.5%) on ImageNet-1K with ViT-L/16, far higher than BERT's typical 15% or prior vision masking work's 20-50%. Linear probing rises steadily to 75% then drops sharply (~20-point gap between 75% and 10% masking), while fine-tuning stays robust across 40-80%. Loss is MSE computed only on masked patches (computing it over all pixels costs ~0.5% accuracy). Per-patch normalized pixels as the target slightly beat unnormalized pixels (84.9% vs 84.5% fine-tuning); a token-based target (BEiT's DALLE dVAE) is no better than normalized pixels and adds a costly extra pretraining stage. Random sampling beats block-wise or grid-wise masking because it tolerates the highest usable ratio.

## Transfer to segmentation under label scarcity

MAE (ViT-Huge, IN1K only) reaches 87.8% ImageNet top-1 fine-tuned, best among IN1K-only methods. On ADE20K segmentation (UperNet), MAE beats supervised IN1K pretraining by 3.7 mIoU for ViT-L (53.6 vs 49.9) and matches/beats token-based BEiT (53.3) and contrastive MoCo v3 (53.3), despite no extra data. On COCO, gains over supervised pretraining grow with model size — +2.4 AP^box at ViT-B, +4.0 at ViT-L — showing the pixel-reconstruction pretext scales with capacity and transfers disproportionately well to dense prediction relative to linear-probe classification, aligning with [[label-efficiency]] goals when only fine-tuning-scale labels are available.

## See also

Related:: [[vision-transformer]] [[masked-image-modeling]] [[label-efficiency]] [[beit]] [[dino]] [[moco]] [[segmentation-decoders]]
