---
type: wiki
title: Data scaling versus model scaling
summary: Which lever pays more depends on which is currently binding — and the honest answer is usually 'the one you have been starving', which is why the comparison has to be made at a fixed budget.
category: comparison
sources: raw/sun2017_revisiting_data.pdf, raw/zhai2021_scaling_vit.pdf, raw/hoffmann2022_chinchilla.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Data scaling versus model scaling

## The case for data

Sun et al. (2017) trained on [[jft-300m]] — 300 million weakly labelled images, some two
orders of magnitude beyond [[imagenet]]-1k — and found representation quality increasing
roughly logarithmically with data volume, with no plateau at the scales they could
reach. The headline reading, widely repeated, was that data is the binding constraint
and models are not.

## The case for capacity

The same paper contains the qualification that is usually dropped: the gains require
model capacity to grow alongside the data. Zhai et al. (2021), scaling
[[vision-transformer]]s across several orders of magnitude in both directions, found the
same interaction from the other side — at large data, representation quality becomes
bottlenecked by model size, and scaling data alone stops paying.

## Why the question is ill-posed as usually asked

Neither lever has an answer independent of the other, and neither has an answer
independent of budget. "Does more data beat a better model" is only well-formed once the
budget is fixed and stated ([[compute-budget]]). Asked that way, the answer becomes an
empirical split rather than a slogan — which is exactly what
[[compute-optimal-training]] produced.

## The practical reading

Whichever resource has been starved pays the higher marginal return. Groups that
over-collect data and under-size models conclude models don't matter; groups that do the
reverse conclude data doesn't. Both conclusions are artefacts of the starting point, and
both are reported as general findings. Which is why this programme fixes a budget
before it compares anything ([[overview]]).
