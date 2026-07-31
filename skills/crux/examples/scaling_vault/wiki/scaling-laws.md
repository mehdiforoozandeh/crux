---
type: wiki
title: Scaling laws
summary: Generalisation error falls as a power law in training-set size, parameter count and compute, over many orders of magnitude and across domains — with a small exponent and an additive floor.
category: concept
sources: raw/kaplan2020_scaling_laws.pdf, raw/hestness2017_scaling_predictable.pdf, raw/rosenfeld2019_error_across_scales.pdf, raw/bahri2021_explaining_scaling.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Scaling laws

The central empirical regularity behind every claim in this vault: test loss falls as a
power law in each of three quantities — dataset size, parameter count, and training
compute — when the other two are not the binding constraint.

## The empirical finding

Hestness et al. (2017) measured generalisation error against training-set size across
machine translation, language modelling, image classification and speech recognition,
and found power-law scaling in every one, with exponents clustered in a narrow band and
model size growing sublinearly with data. Kaplan et al. (2020) established the same form
for transformer language models over several orders of magnitude, and reported that
performance depends strongly on scale and only weakly on architectural details such as
depth-to-width ratio.

That second finding is what makes the question in this vault sharp. If architecture
barely matters and scale is nearly everything, then "a better model" is mostly a claim
about capacity, and the comparison collapses into how a budget is divided.

## The functional form

The usual fit is a power law plus a constant:

    L(x) ≈ A · x^(-α) + L∞

The additive term is the part that does not go away with scale
([[irreducible-error]]). Rosenfeld et al. (2019) fit a joint form in data size *and*
model size that predicts error at large scale from small-scale measurements, which is
what makes it possible to run this programme at an affordable size at all.

## Why the exponent is what it is

Bahri et al. (2021) separate scaling into distinct regimes — variance-limited, where
error falls quickly with more of whichever resource is scarce, and resolution-limited,
where the exponent is tied to the intrinsic dimension of the data manifold. The
practical consequence: a small exponent is a property of the data, not a failure of
engineering, and no amount of architecture work moves it much.

## Caveats worth pre-registering

Power laws fitted over two decades extrapolate badly to a third. Exponents are estimated
from noisy runs and are sensitive to the fitting range. And a law fitted at one data
quality does not transfer to another ([[data-quality]], [[data-pruning]]). None of which
settles the question this vault opens with ([[overview]]) — for that the budget has to be
held fixed.
