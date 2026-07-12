---
type: wiki
title: BEiT
summary: BERT-style masked image modeling that predicts discrete visual tokens from a dVAE tokenizer for masked patches, an alternative masked-modeling formulation to MAE's pixel reconstruction.
category: method
sources: raw/bao2021_beit.pdf
created: 2026-07-11
updated: 2026-07-11
---

# BEiT

BEiT recasts masked image modeling as classification over a fixed 8192-entry discrete visual vocabulary — predicting token IDs for masked patches instead of reconstructing pixels — because the authors argue pixel-level regression "wastes modeling capability on short-range dependencies and high-frequency details."

## Two views and the dVAE tokenizer

Each 224x224 image has two parallel representations: a 14x14 grid of 16x16 image patches (input) and a 14x14 grid of discrete visual tokens (prediction target), produced by a discrete variational autoencoder (dVAE) with vocabulary |V|=8192, taken directly from the public DALL-E tokenizer (Ramesh et al., not trained by BEiT). The dVAE has an encoder q_phi(z|x) mapping pixels to codebook indices and a decoder p_psi(x|z) reconstructing pixels from tokens; it is trained first via Gumbel-softmax (to handle the non-differentiable discrete codes) with a uniform prior, then frozen before BEiT pretraining begins — a hard dependency the [[mae]] paper avoids entirely.

## Blockwise masking and the MIM objective

BEiT masks ~40% of patches (up to 75 of 196) via blockwise masking: repeatedly sampling a rectangular block (min. 16 patches, aspect ratio in [0.3, 1/0.3]) until the quota is met, rather than uniform-random masking. Masked patches are replaced by a shared learnable [M] embedding; a [S] token is prepended, following [[vision-transformer]] conventions. The backbone is a standard ViT-Base (12 layers, 768-d, 12 heads) matched to ViT/DeiT for fair comparison. At each masked position a softmax classifier over the encoded vector predicts the original visual token id, maximizing log p_MIM(z_i | x^M) — genuine multi-way classification, not regression. BEiT frames pretraining as two-stage variational inference: stage 1 trains the tokenizer (visual token reconstruction), stage 2 is MIM itself, jointly lower-bounding log p(x | masked x).

## Results and the token-vs-pixel ablation

Pretrained on ImageNet-1K (1.2M images, no labels) for 800 epochs (~5 days, 16 V100s). BEiT-B reaches 83.2% ImageNet top-1 fine-tuned, beating DINO-B (82.8) and matching MoCo v3-B; BEiT-L at 384px reaches 86.3%. On ADE20K (SETR-PUP decoder), BEiT-B gets 45.6 mIoU vs. 45.3 for supervised IN-1K pretraining and 44.1 for DINO; intermediate fine-tuning on labeled ImageNet pushes this to 47.7. The decisive ablation: replacing the discrete-token loss with raw-pixel regression while keeping blockwise masking drops ImageNet 82.86%→81.04% and ADE20K 44.65→41.38 mIoU — evidence that token prediction, not the masking pattern, drives the gain, and the direct counterpoint to MAE's finding that a token target is no better than normalized pixels.

## See also

Related:: [[masked-image-modeling]] [[vision-transformer]] [[mae]] [[dino]] [[moco]] [[segmentation-decoders]] [[label-efficiency]]
