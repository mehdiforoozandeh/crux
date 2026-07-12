---
type: wiki
title: Vision Transformer (ViT) Backbone
summary: Patch-based transformer encoder (ViT-B/16, Dosovitskiy et al. 2020) that serves as the shared backbone every SSL method in SegSSL pretrains and every decoder fine-tunes.
category: entity
sources: raw/dosovitskiy2020_vit.pdf
created: 2026-07-11
updated: 2026-07-11
---

# Vision Transformer (ViT) Backbone

ViT dispenses with convolutions entirely: an image is cut into fixed-size patches, linearly embedded, and fed as a token sequence to a standard NLP Transformer encoder, touching the image's 2D structure only at patchifying time and at resolution-change fine-tuning.

## Patch embedding and encoder mechanics

An image x ∈ R^(H×W×C) is reshaped into N flattened patches x_p ∈ R^(N×(P²·C)), with N = HW/P² also the Transformer's sequence length. A trainable linear projection E maps each patch to the model's constant latent size D (Eq. 1). A learnable `[class]` token is prepended, borrowed from BERT; its final-layer state, after LayerNorm, gives the pooled representation y = LN(z_L^0) used for classification, while the remaining N patch tokens carry the spatial signal. Standard learnable 1D position embeddings are added — hand-crafted 2D-aware schemes gave no measurable gain (Appendix D.4). The encoder is the vanilla Transformer of Vaswani et al.: L layers alternating multi-head self-attention (MSA) and a two-layer GELU MLP, LayerNorm before each block, residual connections after (Eqs. 2–3).

## Little inductive bias, large-scale pretraining

ViT has far less image-specific inductive bias than CNNs: only MLP sublayers are local and translationally equivariant; self-attention is global from the first layer. 2D neighborhood structure is injected only twice — at patchifying, and when position embeddings are 2D-interpolated for a new resolution at fine-tuning. ViT thus underperforms ResNets on ImageNet-scale data alone but overtakes BiT-ResNets once pretrained on ImageNet-21k (14M images) or JFT-300M (303M images): the largest model reaches 88.55% top-1 on ImageNet, 94.55% on CIFAR-100, and 77.63% averaged over the 19-task VTAB suite. This label-hunger is the gap self-supervised pretraining (masked-image-modeling as in [[mae]] and [[beit]], or self-distillation as in [[dino]]) targets by supplying the missing prior from unlabeled data ([[label-efficiency]]).

## ViT-B/16 as the fixed backbone

Table 1 fixes "Base": 12 layers, hidden size D=768, MLP size 3072, 12 heads, 86M params; "/16" denotes patch size P=16. ViT-B/16 sits at the small end of the paper's scaling study yet is already competitive, and it is the configuration BEiT, MAE, DINO, and iBOT standardize on for base-scale results — hence it is fixed as the single shared encoder across SegSSL: every pretraining objective and decoder is compared at identical capacity, patch size, and token count, isolating the SSL method as the only variable.

## Patch grid feeding decoders

For a 224×224 input, P=16 yields a 14×14 grid of N=196 patch tokens plus the `[class]` token — the same grid that masked-modeling objectives mask and predict over, and that, once `[class]` is dropped, dense-prediction decoders ([[segmentation-decoders]]) reshape into a spatial feature map for pixel-wise output, e.g. on [[cityscapes]].

## See also

Related:: [[overview]] [[mae]] [[beit]] [[segmentation-decoders]] [[masked-image-modeling]] [[dino]] [[ibot]] [[label-efficiency]]
