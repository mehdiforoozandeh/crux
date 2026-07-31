---
type: wiki
title: Transformer language models
summary: The setting where scaling laws were established most cleanly — and where inference cost has since pushed practice deliberately away from compute-optimal training.
category: entity
sources: raw/touvron2023_llama.pdf, raw/raffel2019_t5.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Transformer language models

## Why they anchor the scaling literature

Language modelling gives a single well-defined loss, effectively unlimited raw data, and
a family that scales smoothly over many orders of magnitude. That is why the cleanest
scaling results were established here first ([[scaling-laws]],
[[compute-optimal-training]]) and then exported to vision.

Raffel et al. (2019) recast every task into one text-to-text format, which made transfer
comparable across tasks rather than bespoke per task ([[transfer-learning]]).

## The training-versus-inference trade

Touvron et al. (2023) trained the LLaMA family on publicly available data and
deliberately trained *past* the compute-optimal point of
[[compute-optimal-training]] — more tokens than the training-optimal split recommends,
for smaller models. The reasoning is that compute-optimal minimises training cost, while
a deployed model pays inference cost for its whole life, and a smaller model trained
longer is cheaper to serve. LLaMA-13B outperforming a 175B-parameter model on most
benchmarks is the demonstration.

## Why this is instructive here

Two defensible optima exist because two different budgets are being optimised. Neither
is wrong; a paper reporting one without naming which budget it optimised is. The same
ambiguity is available in this vault's own question, which is why
[[compute-budget]] states what is being held fixed rather than leaving it implied.
