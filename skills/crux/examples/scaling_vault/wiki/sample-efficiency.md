---
type: wiki
title: Sample efficiency
summary: How much accuracy a marginal example buys — the quantity a data-scaling claim is really about, and the one most often reported without a matched-budget control.
category: concept
sources: raw/kaplan2020_scaling_laws.pdf, raw/sorscher2022_data_pruning.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Sample efficiency

## Definition

The accuracy gained per additional training example, at a given point on the scaling
curve. Because the curve is a power law with a small exponent, sample efficiency falls
sharply with scale: the ten-thousandth example is worth far more than the ten-millionth.

## Why it is the operational quantity

Data acquisition has a price. A programme deciding whether to collect more needs the
marginal return at *its current scale*, not the average return over the whole curve.
Papers reporting "10x data gives +N points" almost always measured that step somewhere
far from where the reader is standing.

## The interaction with capacity

Kaplan et al. (2020) observed that larger models are more sample-efficient: at a fixed
number of examples, a bigger model extracts more from them. This complicates any clean
statement that data and capacity are separate levers, and is the mechanism behind the
interaction described in [[data-vs-model-scaling]].

## Not all examples are equal

Sorscher et al. (2022) showed that the power law is a property of *randomly* sampled
data, not an inherent limit: with a good pruning metric, the scaling exponent itself can
be improved, and in principle exponential rather than power-law scaling is reachable.
Which examples you have turns out to matter as much as how many ([[data-pruning]],
[[data-quality]]).
