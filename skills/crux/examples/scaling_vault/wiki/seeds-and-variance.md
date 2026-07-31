---
type: wiki
title: Seeds and run-to-run variance
summary: How large a difference has to be before it means anything, and why a single-seed comparison at these effect sizes is uninterpretable.
category: method
sources: raw/rosenfeld2019_error_across_scales.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Seeds and run-to-run variance

## The problem of scale

Scaling effects at an affordable experiment size are small — often a couple of accuracy
points. Run-to-run variance from initialisation, data order and nondeterministic kernels
is frequently of the same order. A single run per arm therefore cannot distinguish a
real effect from noise, however carefully everything else was controlled.

## Practice here

Every arm runs three seeds. The pre-registered bar is that the effect holds in *all
three*, not that it holds on the mean. This is a deliberately blunt rule: means can be
carried by one outlier, and a bar that a single lucky run can clear is not a bar.

Three is a compromise between statistical honesty and the compute this programme has.
It is enough to catch a sign flip and not enough to estimate a variance, and it is
recorded as such rather than presented as a power analysis.

## Interaction with the fitting problem

Rosenfeld et al. (2019) fit error across scales rather than at a single point, which
averages over some of this noise and is more robust than comparing two isolated runs.
Where a claim here is about a *curve* rather than a point, the curve is fitted across
scales for that reason.

## Pre-registration note

The seed count and the all-three rule are fixed before the first run. Adding seeds after
seeing a near-miss is the most tempting and least defensible move available in this
programme, and it is precisely what the ticked-box mechanism exists to prevent.
