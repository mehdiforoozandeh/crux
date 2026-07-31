---
type: wiki
title: Compute-optimal training
summary: For a fixed compute budget, model size and training-set size should be scaled in roughly equal proportion — a correction that showed a generation of large models had been trained on far too little data.
category: concept
sources: raw/hoffmann2022_chinchilla.pdf, raw/kaplan2020_scaling_laws.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Compute-optimal training

The single most instructive worked example of the confound this programme is built
around, and the reason every comparison here is also run at matched compute.

## The finding

Hoffmann et al. (2022) asked how a fixed compute budget should be divided between
parameters and training tokens. Across a large sweep, the answer was that the two should
be scaled in roughly equal proportion — very roughly twenty training tokens per
parameter — which was sharply at odds with prevailing practice.

The demonstration was direct rather than theoretical. Chinchilla, at 70B parameters
trained on around four times more data, outperformed Gopher at 280B parameters across a
wide evaluation suite, using the *same* training compute. The larger model was not
beaten by a better architecture. It was beaten by a better split of the same budget.

## Why the field got it wrong

The earlier guidance (Kaplan et al. 2020, in [[scaling-laws]]) recommended
scaling parameters much faster than data. The discrepancy traces to methodology — chiefly
how the learning-rate schedule was set relative to the number of training steps in the
small-scale sweeps used to fit the law. A defensible fit on a mis-specified sweep
produced a recommendation that cost the field a great deal of compute.

## The lesson this vault takes from it

Two arms of an experiment that differ in data volume almost always differ in compute as
well ([[compute-budget]]). If the data-heavy arm wins, "more data is better" and "more
compute is better" both predict that result, and the experiment has not distinguished
them. The equal-compute rerun is not a robustness check; it is the actual test
([[controlled-comparison]]).
