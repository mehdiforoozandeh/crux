---
type: wiki
title: ImageNet
summary: The 1.28M-image labelled benchmark that most scaling claims are still measured against, and its ~14M-image, ~21k-class superset.
category: dataset
sources: raw/russakovsky2014_ilsvrc.pdf
created: 2026-07-31
updated: 2026-07-31
---

# ImageNet

## The two scales

**ImageNet-1k**, the ILSVRC-2012 classification set, holds roughly 1.28 million training
images across 1000 classes with a 50,000-image validation set. It remains the default
reporting surface for vision, which is why nearly every comparison in this vault is
anchored to it.

**ImageNet-21k** is the larger superset — around 14 million images over roughly 21,000
classes — and is the smallest scale at which data-hungry architectures start behaving
well ([[vision-transformer]]).

## Why the scale matters to this question

ImageNet-1k sits in the regime where convolutional inductive bias still pays and
transformer capacity does not. A model comparison run only at 1k scale will
systematically favour [[resnet]]; the same comparison at [[jft-300m]] scale will favour
ViT. Both are correct statements about their own scale and neither is a general result.

## The validation set is not held out any more

It has been used for selection by the whole field for over a decade. Recht et al. (2019)
measured what that costs by rebuilding it ([[held-out-evaluation]]). Absolute numbers
here are treated as comparable to the literature; differences between this vault's own
arms, measured on a fixed split, carry the weight.

## Caveats

The corpus is object-centric, roughly class-balanced and photographically curated.
Deployment data is usually none of those ([[distribution-shift]]).
