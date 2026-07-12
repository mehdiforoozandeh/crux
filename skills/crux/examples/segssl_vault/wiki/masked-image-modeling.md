---
type: wiki
title: Masked Image Modeling (MIM)
summary: SSL family that masks patches and trains a model to reconstruct pixels (MAE), discrete tokens (BEiT), or online-teacher targets (iBOT), producing encoders with strong localized/dense feature sensitivity.
category: concept
sources: raw/he2021_mae.pdf, raw/bao2021_beit.pdf, raw/zhou2021_ibot.pdf
created: 2026-07-11
updated: 2026-07-11
---

# Masked Image Modeling (MIM)

All three methods split an image into a 14x14 grid of patches, hide a subset, and train the network to predict something about the hidden patches from the visible ones — the difference between them is entirely in what "something" means.

## Shared mechanics, divergent targets

[[mae]] masks 75% of patches (much higher than BERT's ~15%) and feeds only the visible 25% into a ViT encoder; a lightweight asymmetric decoder (8 blocks, 512-dim, <10% of encoder FLOPs) then takes encoded patches plus mask tokens and regresses normalized pixel values, with MSE loss computed only on masked positions. [[beit]] instead predicts discrete visual tokens from a fixed vocabulary of 8192, produced by a DALL-E dVAE tokenizer pretrained separately on 250M images; it uses blockwise masking (~40% of patches) and frames the objective as a two-stage VAE ELBO (tokenizer first, then masked prediction). [[ibot]] replaces both a hand-designed pixel loss and an offline tokenizer with an *online* one: a teacher network (EMA of the student, DINO-style self-distillation on the [CLS] token) supplies soft target distributions for masked patch tokens, so the tokenizer is learned jointly with the backbone rather than pretrained beforehand.

## Why the target space matters for density

BEiT's ablation shows tokenization is the key ingredient, not just masking: replacing token prediction with raw pixel regression drops ImageNet from 82.86% to 81.04% and ADE20K mIoU from 44.65 to 41.38. But iBOT argues BEiT's offline dVAE tokenizer still "encapsulates mostly low-level details," while its own online tokenizer captures part-level semantics — patches for "headlight" or "dog's ear" cluster together in iBOT visualizations. This shows up starkly on dense tasks with a *linear* segmentation head on ADE20K: iBOT reaches 38.3 mIoU vs. BEiT's 27.4, meaning BEiT's patch tokens alone carry little local semantic content even though its global [CLS]-level classification is competitive. MAE sidesteps the tokenizer question entirely — it found dVAE tokens give accuracy statistically indistinguishable from normalized pixels (Table 7) — and instead pushes locality into the decoder design: a deep decoder is needed for good linear probing because reconstruction is a lower-semantic-level task than recognition.

All three transfer disproportionately well to dense prediction relative to supervised pretraining: MAE ViT-L reaches 53.3 AP-box on COCO (vs. 49.3 supervised) and 53.6 mIoU on ADE20K; iBOT ViT-S reaches 49.4 AP-box (vs. 46.2 supervised). The common driver is that masked reconstruction is inherently a per-patch, spatially localized objective, forcing every patch's representation to carry usable local signal rather than collapsing to a single global descriptor.

## See also

Related:: [[overview]] [[vision-transformer]] [[dino]] [[self-distillation]] [[contrastive-learning]] [[segmentation-decoders]]
