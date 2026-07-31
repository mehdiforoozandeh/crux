---
type: wiki
title: ResNet
summary: The residual convolutional family used here as the smaller, well-understood arm — the model whose behaviour at modest data scale is best characterised.
category: entity
sources: raw/he2015_resnet.pdf
created: 2026-07-31
updated: 2026-07-31
---

# ResNet

## What it is

He et al. (2015) introduced residual connections, which let each block learn a
correction to its input rather than a full transformation. This made networks of a depth
that had previously degraded in *training* error — not merely in generalisation —
trainable, and 152-layer models became routine.

## Role in this vault

ResNet is the reference architecture: mature, cheap, and characterised across a very
wide range of data scales, which is exactly what a scaling comparison needs from its
control arm. Its behaviour at [[imagenet]]-1k scale is about as well established as any
result in the field.

It is also the natural stand-in for "the model you already have". The practical form of
this vault's question is usually *should I collect more data for my ResNet, or move to a
bigger architecture* — so making ResNet one arm keeps the comparison recognisable.

## Scaling behaviour

Depth, width and input resolution are separable levers, and scaling them independently
gives worse returns than scaling them jointly ([[efficientnet]]). Convolutional
inductive bias makes ResNets comparatively strong in the low-data regime and
comparatively weak at very large data, which is precisely the crossover
[[vision-transformer]] exploits — and precisely why the comparison must state its data
scale.
