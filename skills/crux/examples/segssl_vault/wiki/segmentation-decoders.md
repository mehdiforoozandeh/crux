---
type: wiki
title: Segmentation Decoder Architectures (SegFormer, Segmenter, U-Net, DeepLabv3+)
summary: Comparative page on the four decoder/head families SegSSL pairs with pretrained encoders: lightweight MLP (SegFormer), transformer mask decoder (Segmenter), convolutional encoder-decoder with skips (U-Net), and atrous-conv with decoder refinement (DeepLabv3+).
category: comparison
sources: raw/xie2021_segformer.pdf, raw/strudel2021_segmenter.pdf, raw/ronneberger2015_unet.pdf, raw/chen2018_deeplabv3plus.pdf
created: 2026-07-11
updated: 2026-07-11
---

# Segmentation Decoder Architectures (SegFormer, Segmenter, U-Net, DeepLabv3+)

All four turn encoder features into per-pixel logits, but assume opposite sources of receptive field, and only one is built on a plain [[vision-transformer]] backbone.

## Compute cost

SegFormer's All-MLP decoder unifies channel dims of the 4 encoder-stage features, upsamples each to 1/4 resolution, concatenates, fuses, and predicts. It stays tiny at every scale: 0.4M params for MiT-B0 (~10% of total), 3.3M for MiT-B5 (~4% of 81.4M). Segmenter's linear decoder is one point-wise layer; its mask-transformer variant adds only M=2 transformer layers over K class embeddings — small next to an 86M-param ViT encoder. U-Net is comparatively heavy: 23 conv layers across a symmetric path, decoder roughly matching encoder budget. DeepLabv3+'s decoder proper is light (1x1 conv reducing low-level channels to 48, two 3x3×256 refinement convs); cost sits mostly in the encoder's ASPP module (atrous rates 6/12/18 + image pooling), reaching 82.1% test mIoU on [[cityscapes]].

## Receptive-field strategy

SegFormer measures effective receptive field (ERF) directly: its hierarchical MiT encoder already produces non-local attention by Stage-4, so the MLP decoder just fuses already-global features, no dilation or pyramid pooling needed. Pairing the same decoder with a CNN encoder drops ADE20K mIoU from 48.6% to 43.1%, since CNN ERF stays small even at the deepest stage. Segmenter gets global context "at every layer" via self-attention from layer 1, so its decoder need not build context — masks are a dot product of L2-normalized patch and class embeddings. U-Net builds receptive field by depth (pool/conv), recovering localization via skip concatenation. DeepLabv3+ enlarges receptive field via atrous convolution (stride 16, rates to 18); its decoder only sharpens boundaries.

## Compatibility with a frozen/fine-tuned ViT-B/16 encoder

Segmenter is built directly on ViT/DeiT: Seg-B/16 and Seg-B†/16 use ViT-B/16 and DeiT-B/16 (86M params, 16×16 patches) with either decoder; pretraining recipe matters — mIoU jumps 45.69%→48.06% depending on ViT init. SegFormer's MLP decoder needs multi-scale {1/4, 1/8, 1/16, 1/32} features, which single-resolution ViT-B/16 doesn't supply — it's built around its own hierarchical MiT encoder. U-Net's skips need a matching-resolution CNN pyramid, and DeepLabv3+'s ASPP/decoder need an atrous-controllable stride plus a low-level conv feature; neither holds for raw ViT-B/16 tokens.

## Label-efficiency implications

SegFormer's and Segmenter's decoders add few new parameters, so more signal comes from the pretrained encoder — attractive under [[label-efficiency]] constraints. Segmenter's own ablation shows a floor: ADE20K mIoU falls 45.37%→38.31% from 20k to 4k training images, so even a lightweight decoder still needs enough fine-tuning data. U-Net is the counterpoint: its heavier decoder was validated on just 30 EM slices via elastic-deformation augmentation, showing conv inductive bias plus skips substitute for data volume with no pretraining at all.

## See also

Related:: [[vision-transformer]] [[cityscapes]] [[label-efficiency]] [[overview]]
