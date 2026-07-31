---
type: wiki
title: Data pruning
summary: Removing the least informative examples can improve the scaling exponent itself — evidence that the power law is a property of random sampling, not a hard limit.
category: method
sources: raw/sorscher2022_data_pruning.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Data pruning

## The claim

Sorscher et al. (2022) argued that power-law scaling in dataset size is an artefact of
sampling data randomly. With a metric that ranks examples by informativeness and prunes
the rest, the scaling *exponent* improves, and under favourable conditions exponential
rather than power-law scaling becomes reachable in theory.

## The part that is easy to misread

The benefit is not monotone and it inverts with scale. When data is scarce, keeping the
*easy* examples is better; when data is abundant, keeping the *hard* ones is. A pruning
strategy tuned at one dataset size can actively hurt at another, which makes pruning a
poor thing to hold fixed across arms of a scaling experiment.

They also demonstrated a self-supervised pruning metric requiring no labels, which
matters because label cost is often the binding constraint that made the programme
data-limited in the first place.

## Why it appears in this vault

It is the strongest available argument that "more data" and "better data" are different
levers with different economics, and that a programme measuring the first while varying
the second is measuring neither ([[data-quality]], [[sample-efficiency]]).

For this reason pruning is disabled in every arm here. It is a confound, not a
treatment — and one worth its own question later rather than a silent inclusion now.
