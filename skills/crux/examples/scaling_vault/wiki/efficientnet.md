---
type: wiki
title: EfficientNet and compound scaling
summary: Depth, width and resolution scale better together than separately — the model-side analogue of the compute-optimal result.
category: entity
sources: raw/tan2019_efficientnet.pdf
created: 2026-07-31
updated: 2026-07-31
---

# EfficientNet and compound scaling

## The finding

Tan & Le (2019) observed that the conventional practice of scaling one dimension of a
convolutional network — usually depth — gives diminishing returns quickly, while scaling
depth, width and input resolution together with a fixed ratio gives much better accuracy
per FLOP. They derived the ratio by a small grid search and then applied it uniformly.

## Why it belongs in this vault

It is the model-side version of the same lesson as [[compute-optimal-training]]: given a
budget, the question is not *which* resource to increase but *in what proportion*, and
answering it by intuition leaves a large factor on the table in both cases.

It also sharpens what "a better model" means here. If a capacity increase is spent
badly, the model arm underperforms for reasons that have nothing to do with the
data-versus-capacity question — so the capacity arm is scaled compound-style rather than
by depth alone, and that choice is recorded before the run
([[controlled-comparison]]).

## Caveat

The compound coefficients were found on one architecture family at one scale. Treating
them as universal constants is the same extrapolation error described in
[[scaling-laws]], and they are used here as a defensible default rather than as a law.
