---
type: wiki
title: Transfer learning
summary: Pretrain once at scale, adapt many times — the setting in which a data-versus-model question is usually asked, and where pretraining scale dominates.
category: concept
sources: raw/kolesnikov2019_bit.pdf, raw/raffel2019_t5.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Transfer learning

## The pattern

A model is trained once on a large general corpus and then adapted to a specific task
with far less data. This is the setting in which the data-versus-model question actually
arises in practice, because the pretraining corpus and the model are chosen together and
paid for once.

## What scale buys

Kolesnikov et al. (2019) scaled pretraining data and model size together and reported
that a simple recipe, applied at sufficient scale, transferred strongly across a wide
range of downstream tasks with very few task-specific adjustments. Their headline
practical finding was that most of the tuning complexity the field had accumulated
downstream became unnecessary once pretraining was large enough — capacity and data had
to grow together for the effect to appear ([[data-vs-model-scaling]]).

Raffel et al. (2019) made the same argument in text by reducing every task to one
format, which turns "does this transfer" into a question that can be asked uniformly
rather than task by task.

## Why it complicates the comparison

Downstream accuracy is a function of pretraining data, pretraining compute, model
capacity and adaptation protocol. A result reported only as a downstream number does not
say which of those moved. This vault fixes the adaptation protocol ([[fine-tuning]]) so
the remaining variation is attributable.
