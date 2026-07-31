---
type: wiki
title: Controlled comparison
summary: The discipline of changing one thing: what has to be held fixed for a data-versus-model result to license the conclusion it states.
category: method
sources: raw/hoffmann2022_chinchilla.pdf, raw/recht2019_imagenet_v2.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Controlled comparison

## The failure mode

A result reads "more data won". The data-heavy arm also trained longer, on a bigger
budget, with a schedule tuned for its own scale. Every one of those differences predicts
the same outcome. The experiment distinguishes none of them, but the sentence in the
abstract asserts one.

This is the single most common defect in scaling claims, and it is rarely deliberate.
It arises because the natural way to run the two arms — each at its own best settings —
is exactly the way that confounds them.

## What must be fixed

- **Compute.** The dominant confound, and the one that produced the
  [[compute-optimal-training]] correction. See [[compute-budget]].
- **Architecture family and evaluation protocol.** Otherwise a data result is partly an
  architecture result.
- **Data preparation.** Identical filtering and deduplication across arms
  ([[data-quality]]); no pruning in either ([[data-pruning]]).
- **Seed count and selection rule.** Fixed in advance ([[seeds-and-variance]]).
- **The test set.** Fixed before any arm is run, and not consulted between arms
  ([[held-out-evaluation]]).

## Two runs, not one

Where a variable cannot be held fixed without distorting the question — data volume
being the obvious case — the comparison is run twice, once at equal data and once at
equal compute. Agreement strengthens the claim. Disagreement *is* the finding, and it is
the more likely outcome.

## Why pre-registration does the work

Every item above is listed in [[overview]] as a condition of this programme, and every
one is cheap to fix beforehand and impossible to fix afterwards. Once the
numbers exist, any choice among them can be justified, and the justification will feel
principled from the inside. Writing the bars down before the run is the only mechanism
that survives contact with a result you want.
