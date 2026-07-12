---
type: wiki
title: SimCLR
summary: Foundational contrastive framework using strong augmentations, a projection head, and the InfoNCE/NT-Xent loss to pull augmented views of the same image together in embedding space.
category: method
sources: raw/chen2020_simclr.pdf
created: 2026-07-11
updated: 2026-07-11
---

# SimCLR

SimCLR shows a large-batch, augmentation-heavy contrastive objective — no memory bank, no specialized architecture — can match a supervised ResNet-50 under linear evaluation (76.5% top-1, 4x-wide model), establishing the reference recipe (strong augmentation, projection head, NT-Xent) that [[moco]], DenseCL, and PixPro each modify one piece of.

## Augmentation pipeline

Two views x̃i, x̃j come from a stochastic composition t∼T: random crop+resize (with flip), color distortion (jitter or drop), and Gaussian blur — no rotation, cutout, Sobel, or noise in the final policy. Ablations (linear eval, ResNet-50) show no single augmentation suffices — crop alone lets the model nearly identify the correct pair via shared color histograms (Fig. 6) yet yields weak representations — while crop+color is the standout pair. Sweeping color-distortion strength (1/8→1, +blur) shows unsupervised accuracy rising monotonically (59.6%→64.5%) while supervised accuracy falls slightly (77.0%→75.4%): [[contrastive-learning]] needs stronger augmentation than supervised training. AutoAugment underperforms crop+strong color distortion (61.1% vs 64.5%).

## Projection head trick

Base encoder f (ResNet-50) outputs h ∈ R^2048 after average pooling; a 2-layer MLP head g (Linear→ReLU→Linear) projects to z = g(h) ∈ R^128, and the loss is computed on z, not h. Nonlinear g beats linear by +3% and no-projection by >10% (linear eval). h itself still outperforms z by >10%, since g is trained invariant to exactly the augmentations (color, rotation) a downstream task may need; auxiliary MLPs predicting the transform confirm h retains far more info than g(h) (99.3% vs 97.4% color-vs-grayscale; 67.6% vs 25.6% rotation). g(·) is discarded after pretraining; f and h feed downstream tasks.

## Large-batch negative sampling and NT-Xent

No memory bank, no explicit negative sampling: a minibatch of N images yields 2N views, and for positive pair (i,j) the other 2(N−1) in-batch views serve as negatives. NT-Xent ("normalized temperature-scaled cross entropy") is ℓ_i,j = −log[exp(sim(z_i,z_j)/τ) / Σ_{k≠i} exp(sim(z_i,z_k)/τ)], sim = cosine similarity. Batch size sweeps 256→8192 (8192 → 16,382 negatives/pair); LARS stabilizes otherwise-unstable large-batch SGD, and BatchNorm stats are aggregated globally across devices so same-device positives can't leak shortcuts. Larger batches help most at low epoch counts; the gap narrows by 1000 epochs. NT-Xent beats margin and semi-hard-mined logistic losses by a wide margin (63.9% vs 50.9-57.9% top-1) via implicit hard-negative weighting.

## Results and role as baseline

Plain ResNet-50 SimCLR reaches 69.3% top-1/89.0% top-5 linear-eval, ahead of MoCo (60.6%), PIRL (63.6%), CPCv2 (63.8%); the widest model (ResNet-50 4x, 375M params, 1000 epochs) hits 76.5% top-1. Fine-tuning on 1% of labels gives 85.8% top-5. As the field's clean contrastive baseline — global-image embeddings, in-batch negatives, projection head — it is the departure point for [[moco]]'s momentum-queue negatives and dense/pixel-level variants (DenseCL, PixPro) swapping the global embedding for per-pixel or per-region segmentation targets.

## See also

Related:: [[contrastive-learning]] [[moco]] [[densecl]] [[pixpro]] [[label-efficiency]]
