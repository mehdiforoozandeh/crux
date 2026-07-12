---
type: wiki
title: MoCo (Momentum Contrast)
summary: Contrastive learning with a queue-based memory bank and momentum-updated key encoder that decouples negative-sample count from batch size, making contrastive pretraining batch-efficient.
category: method
sources: raw/he2019_moco.pdf
created: 2026-07-11
updated: 2026-07-11
---

# MoCo (Momentum Contrast)

MoCo reframes [[contrastive-learning]] as dictionary look-up and solves it with a queue-based memory plus a momentum-updated key encoder, decoupling dictionary size from GPU-memory-bound mini-batch size.

## Queue as a large, cheap dictionary

The dictionary is a queue of encoded keys: each mini-batch's keys are enqueued and the oldest mini-batch is dequeued, so queue size K is an independent hyperparameter rather than tied to batch size N (MoCo trains with N=256 on 8 GPUs while K reaches 65536). InfoNCE drives the query q toward its positive key k+ and away from every other key in the queue: L_q = −log[exp(q·k+/τ) / Σ_{i=0}^{K} exp(q·k_i/τ)], τ=0.07. The pretext task is instance discrimination: two random 224×224 augmented views (crop, color jitter, flip, grayscale conversion) of the same image form the positive query/key pair; a ResNet backbone outputs an L2-normalized 128-D vector.

## Momentum update keeps keys consistent

Because queued keys come from many past mini-batches, back-propagating into the key encoder f_k is intractable — gradients would have to reach every queued sample. MoCo instead updates only the query encoder θ_q by SGD and evolves the key encoder as an exponential moving average: θ_k ← mθ_k + (1−m)θ_q, with only θ_q receiving gradients. A large momentum is essential: at K=4096, m=0.999 gives 59.0% linear-eval accuracy versus 55.2% at m=0.9, and m=0 (copying θ_q each step) fails to converge, since a rapidly changing key encoder produces inconsistent keys.

## vs. end-to-end and SimCLR's in-batch negatives

The paper contrasts three dictionary mechanisms. End-to-end back-propagation through both encoders — the mechanism [[simclr]] uses — ties negative count to mini-batch size; SimCLR compensates by scaling batches up to 8192 (16,382 in-batch negatives) with the LARS optimizer, whereas the largest mini-batch feasible end-to-end on 8 V100-32GB GPUs is 1024. The memory-bank mechanism stores representations of the whole dataset but updates each entry only when its sample is last visited, so keys drift out of consistency across an epoch; at matched K=65536 it scores 58.0% versus MoCo's 60.6% (2.6% lower). MoCo reaches memory-bank-scale dictionaries while keeping keys consistent, and uses shuffled BatchNorm across GPUs so batch statistics can't leak shortcut information between positive pairs.

## Downstream transfer and influence

MoCo pre-trained on ImageNet-1M or Instagram-1B surpasses ImageNet-supervised pre-training on 7 detection/segmentation tasks (PASCAL VOC, COCO detection/segmentation/keypoints/DensePose, LVIS, Cityscapes instance segmentation), with gaps up to +3.7 AP and +4.9 AP75, while lagging slightly on VOC semantic segmentation. This strength in dense downstream transfer motivated dense-pretext successors such as [[densecl]], which keep MoCo's momentum-encoder-plus-queue machinery but replace its single global image embedding with pixel- or region-level contrastive pairs.

## See also

Related:: [[contrastive-learning]] [[simclr]] [[densecl]]
