---
type: wiki
title: Label-Efficient Transfer to Dense Prediction
summary: Cross-cutting evaluation axis in SegSSL measuring how few labeled masks (linear probe, few-shot, low-data fine-tuning) are needed after SSL pretraining to reach strong segmentation accuracy on ADE20K/Cityscapes/VOC.
category: concept
sources: raw/he2021_mae.pdf, raw/caron2021_dino.pdf, raw/xie2021_segformer.pdf, raw/cordts2016_cityscapes.pdf
created: 2026-07-11
updated: 2026-07-11
---

# Label-Efficient Transfer to Dense Prediction

Label efficiency is measured by freezing or lightly adapting an SSL-pretrained [[vision-transformer]] encoder and sweeping how much labeled supervision — zero (probing), a partial subset (few blocks or few images), or the full set — is needed to approach fully-supervised segmentation accuracy.

## Linear and k-NN probing (zero-label adaptation)

[[mae]] evaluates ImageNet-1K representations with linear probing (train a single linear layer on frozen features) and full end-to-end fine-tuning, finding the two protocols track *different* trends: linear-probe accuracy rises steadily with masking ratio up to a ~20-point gap between 75% and 10% masking (73.5% vs 54.6%), while fine-tuning is far less sensitive (a flat 83–85% across 40–80% masking). [[dino]] adds k-NN probing — freeze features, vote with the k=20 nearest stored training features, no hyperparameter tuning or augmentation, one pass over the downstream set — as a cheaper linear-classifier substitute; DINO ViT-B/8 reaches 80.1% linear and 78.3% k-NN on ImageNet, and MAE notes linear probing is weakly correlated with transfer to dense tasks like detection/segmentation, motivating fine-tuning-based protocols instead.

## Fraction-of-labels and partial fine-tuning

MAE's partial fine-tuning protocol (unfreezing the last *N* Transformer blocks, 0=linear probing to 24=full fine-tuning) shows accuracy jumps from 73.5% (0 blocks) to 81.0% tuning just one block, and MAE beats contrastive MoCo v3 at every partial setting once ≥1 block is tuned (2.6-point gap at 4 blocks) — evidence that MAE features are less linearly separable but stronger under light label-efficient adaptation. [[cityscapes]] offers an analogous low-data axis at the dataset level: control experiments there show a model trained on only 500 finely-annotated images matches one trained on 20,000 coarsely-annotated images, and ground-truth subsampled by a factor of 2 barely dents IoU_class (97.2%) while subsampling by 8 still retains 90.7%, both quantifying how far annotation volume/density can shrink before segmentation quality collapses.

## Target metric for segmentation decoders

SegFormer supplies the full-label mIoU ceilings SegSSL's low-data curves are read against: 51.8% on ADE20K and 84.0% on Cityscapes val for its largest MiT-B5 encoder paired with an All-MLP [[segmentation-decoders]] head, trained with standard supervision (no masking or distillation). SegSSL pairs SSL-pretrained encoders with such lightweight decoders and reports what fraction of that ceiling is reached at each label budget on ADE20K, Cityscapes, and PASCAL VOC.

## See also

Related:: [[mae]] [[dino]] [[segmentation-decoders]] [[cityscapes]] [[vision-transformer]] [[overview]]
