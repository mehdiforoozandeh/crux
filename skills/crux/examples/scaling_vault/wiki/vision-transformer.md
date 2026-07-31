---
type: wiki
title: Vision Transformer
summary: The higher-capacity arm: weaker than convolutions at small data, stronger at large — the clearest case of a model comparison whose answer depends entirely on data scale.
category: entity
sources: raw/dosovitskiy2020_vit.pdf, raw/zhai2021_scaling_vit.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Vision Transformer

## What it is

Dosovitskiy et al. (2020) applied a standard transformer to sequences of image patches,
discarding almost all convolutional inductive bias.

## The finding that matters here

ViT *underperformed* comparable ResNets when trained on [[imagenet]]-1k alone, and
overtook them only after pretraining at much larger scale — tens of millions of images
and beyond ([[jft-300m]]). The paper is therefore not evidence that transformers are
better than convolutions; it is evidence that the question is malformed without a stated
data scale.

That is the single most useful precedent in this vault. A model comparison run at one
data scale and reported as a general result is exactly the error under investigation
here, and this is a case where the community had the counter-example in the original
paper.

## Scaling behaviour

Zhai et al. (2021) scaled ViT in both directions across several orders of magnitude of
compute, data and model size, mapping the compute-performance frontier and reaching
around 90% ImageNet top-1 with a two-billion-parameter model. They also found that at
large data, representation quality becomes bottlenecked by model size rather than by
data — the reciprocal of the low-data finding above ([[data-vs-model-scaling]]).

## Why both arms are needed

Running only ViT would confound "more data helps" with "this architecture needs data".
Running only ResNet would understate what capacity buys at scale. The crossover is the
phenomenon, so both sit in the design.
