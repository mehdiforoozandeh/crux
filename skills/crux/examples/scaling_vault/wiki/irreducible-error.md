---
type: wiki
title: Irreducible error
summary: The additive constant in a scaling fit — the part of the loss that no amount of data or capacity removes — and why it decides whether scaling is worth funding.
category: concept
sources: raw/bahri2021_explaining_scaling.pdf, raw/rosenfeld2019_error_across_scales.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Irreducible error

## The term

Scaling fits are written as a power law plus a constant. The constant is the asymptote:
the loss remaining when data and capacity are both unlimited. It reflects the entropy of
the task itself, label noise, and any mismatch between the training distribution and the
evaluation one.

## Why it matters for a scaling decision

A power law with a small exponent and a high floor is a bad investment. The visible
improvement over the range you can afford may be almost entirely the approach to a floor
that sits above the accuracy you need. Reporting an exponent without the floor makes
scaling look more attractive than it is, and this is a common presentational failure
rather than a rare one.

## Estimating it

The floor is the least well-determined parameter in the fit, because it is only
constrained by the largest scales measured, which are the fewest and noisiest points.
Rosenfeld et al. (2019) fit it jointly with the data and model exponents rather than
separately, which stabilises it. Bahri et al. (2021) give a reading of where it comes
from: in the resolution-limited regime the exponent tracks the intrinsic dimension of
the data manifold, so both the slope and the floor are properties of the dataset.

## Pre-registration note

An experiment that reports "accuracy improved by scaling data" without stating the
fitted floor has not said whether scaling further will help. The floor belongs in the
verifiables, not the discussion.
