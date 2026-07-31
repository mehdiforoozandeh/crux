---
type: wiki
title: Held-out evaluation
summary: Test-set reuse, and the evidence that headline accuracy drops sharply on a freshly collected test set drawn the same way.
category: method
sources: raw/recht2019_imagenet_v2.pdf, raw/taori2020_robustness.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Held-out evaluation

## The reuse problem

A benchmark test set consulted repeatedly across a community stops being held out. Model
selection, hyperparameter choice and architecture search all leak information from it,
and the leak accumulates over years rather than over one project.

## The measurement

Recht et al. (2019) built a new ImageNet test set following the original collection
protocol as closely as they could reconstruct it, and evaluated a large collection of
existing models. Accuracy dropped substantially — on the order of eleven to fourteen
points. Two details make this more interesting than a simple overfitting story:

- The *ranking* of models was largely preserved. Better models on the original set were
  better on the new one.
- The authors attributed the gap primarily to a distribution shift introduced by the
  reconstruction of the collection process, rather than to adaptive overfitting.

Taori et al. (2020) extended this across many natural shifts and more than two hundred
models, and found that in-distribution accuracy predicts out-of-distribution accuracy
remarkably well — while most explicit robustness interventions offered little beyond
that, and training on larger and more diverse data did.

## What this programme does

The test split is fixed before any arm runs, and is not used for any selection decision.
Comparisons between arms use it once. Where a claim is about robustness rather than
accuracy, it is stated against a named shifted condition, not against the same split
([[distribution-shift]]).

Absolute numbers on a reused benchmark are treated as approximate; differences between
arms measured on the same split are treated as meaningful. That asymmetry is what the
Recht result licenses.
