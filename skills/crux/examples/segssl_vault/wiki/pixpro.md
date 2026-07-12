---
type: wiki
title: PixPro (Pixel-to-Propagation)
summary: Pixel-level self-supervised pretraining using a pixel-propagation module and consistency across overlapping crop regions, another dense-prediction-oriented contrastive variant alongside DenseCL.
category: method
sources: raw/xie2020_pixpro.pdf
created: 2026-07-11
updated: 2026-07-11
---

# PixPro (Pixel-to-Propagation)

PixPro replaces negative-pair contrastive matching at the pixel level with a smoothing-based consistency loss between corresponding pixels in two overlapping crops, arguing that spatial smoothness — not just spatial sensitivity — matters for dense-prediction transfer.

## From PixContrast to pixel-to-propagation consistency

The paper first builds a pixel-level analogue of instance discrimination, *PixContrast*: two augmented views are encoded (backbone + two 1x1-conv projection layers) into feature maps, pixel pairs are labeled positive/negative by warping to original-image coordinates and thresholding normalized distance at T=0.7 (Eq. 1), and an InfoNCE loss (Eq. 2, tau=0.3) attracts positives and repels negatives. This improves on instance-level [[contrastive-learning]] but negative-pair tuning at pixel granularity proves fragile. *Pixel-to-propagation consistency (PPC)*, the main proposal, drops negatives entirely: it adds spatial smoothness via a pixel propagation module (PPM) and trains only a consistency loss between positive pairs, using an asymmetric two-branch design — one branch outputs raw features, the other's output is post-processed by the PPM — so smoothing can't trivially collapse against the un-smoothed branch.

## Pixel Propagation Module and the PPC loss

For pixel i, the PPM computes a smoothed feature y_i = sum_j s(x_i,x_j)*g(x_j) over all pixels j in the same map (Eq. 3), with kernel s(x_i,x_j) = (max(cos(x_i,x_j),0))^gamma, sharpness gamma=2 by default (Eq. 4), and g(.) a stack of l=1 linear+BN+ReLU layers (l=0 gives a non-parametric PPM; l in {0,1,2} all work). One branch is a regular encoder paired with a momentum-updated counterpart (as in [[moco]]/BYOL); the PPM sits after the regular branch's output. The PPC loss maximizes cosine similarity between the momentum branch's raw feature and the PPM branch's smoothed feature for positive pairs found via PixContrast's warping rule: L_PixPro = -cos(y_i,x'_j) - cos(y_j,x'_i) (Eq. 5), no negatives involved. Removing the PPM causes collapse — the smoothed/un-smoothed asymmetry prevents it. Combined additively with an instance-level loss (L = L_PixPro + alpha*L_inst, alpha=1), ImageNet-1K linear-probe accuracy rises from 55.1% to 66.3%, with modest further detection gains.

## Overlap-region matching vs. DenseCL

Both PixPro and [[densecl]] use spatial correspondence between two crops of one image to define positive pairs for dense-prediction transfer, but differ in granularity and loss. DenseCL matches a handful of 7x7 feature-map "views" via cosine-similarity correspondence and keeps a contrastive InfoNCE loss with queue negatives (MoCo-style). PixPro matches every individual pixel via geometric warping (T=0.7) and, in its main PPC variant, drops negatives for the propagation-smoothed consistency loss; its secondary PixContrast variant, which keeps pixel-level negatives, underperforms PPC by 0.7 AP on VOC and 2.0 mAP on COCO (Table 3). PixPro also pretrains head networks (FPN, detector heads), not just the backbone, adding up to 1.2 mAP on FCOS/COCO (Table 5). At 400 epochs with ResNet-50, PixPro reaches 60.2 AP on Pascal VOC (R50-C4), 41.4/40.5 mAP on COCO (FPN/C4), and 77.2 mIoU on Cityscapes — 2.6 AP, 0.8/1.0 mAP, and 1.0 mIoU above the best prior unsupervised methods (MoCo v2, InfoMin).

## See also

Related:: [[contrastive-learning]] [[densecl]] [[moco]]
