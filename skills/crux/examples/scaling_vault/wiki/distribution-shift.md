---
type: wiki
title: Distribution shift
summary: An advantage measured in-distribution need not survive a change of source — and in-distribution accuracy turns out to predict robustness better than most interventions designed for it.
category: concept
sources: raw/taori2020_robustness.pdf, raw/recht2019_imagenet_v2.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Distribution shift

## The setting

Training and deployment data are drawn from different distributions: different
collection process, different source, different time. Every claim in this vault is
measured in-distribution first, and in-distribution results are not evidence about
shifted ones.

## The empirical picture

Taori et al. (2020) evaluated more than two hundred models across a range of *natural*
distribution shifts — not synthetic corruptions — and found two things that are easy to
state and hard to accept:

- In-distribution accuracy predicts out-of-distribution accuracy strongly and
  consistently. Most of what looks like robustness is just being a better model.
- Most interventions explicitly designed to improve robustness offered little beyond
  that trend. Training on substantially larger and more diverse data was among the few
  that did.

Recht et al. (2019) attributed the ImageNet test-set gap primarily to a shift introduced
by re-running the collection process, which suggests that even a faithful reconstruction
of a data pipeline produces a measurable shift ([[held-out-evaluation]]).

## Why it is a separate question here

Because the second finding above means a data-scaling advantage *might* transfer to
shifted conditions and might not, and the in-distribution result cannot settle it. That
makes it a question to open rather than a paragraph to add — with its own bars, fixed
before the shifted evaluation runs.
