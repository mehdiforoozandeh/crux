---
type: wiki
title: Overview — more data, or a better model?
summary: The question this vault exists to settle, the two levers it compares, and the confound that makes a naive comparison worthless.
category: overview
sources: raw/kaplan2020_scaling_laws.pdf, raw/hoffmann2022_chinchilla.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Overview — more data, or a better model?

A team with a fixed budget can spend it on collecting and training on more data, or on a
larger and better-designed model. Practitioners answer this by intuition far more often
than by measurement, and the published record is not much help: papers report the
comparison that flattered whichever lever they were selling.

## The two levers

**Data scale.** Generalisation error falls as a power law in training set size across
every domain that has been measured ([[scaling-laws]], [[data-vs-model-scaling]]). The
exponent is small, so the returns are real but expensive.

**Model scale and design.** Error also falls as a power law in parameter count, and
architecture families differ in where their curves sit ([[resnet]],
[[vision-transformer]], [[efficientnet]]).

## Why the naive comparison is worthless

The two levers are not independent. Training on twice the data, holding everything else
equal, also *costs* roughly twice the compute. A comparison that lets one arm spend more
is not a comparison between data and models at all — it is a comparison between a large
budget and a small one ([[compute-budget]], [[controlled-comparison]]).

This is not a hypothetical failure mode. [[compute-optimal-training]] is the record of a
whole subfield getting it wrong for two years: models were built far larger than their
compute budgets justified, because the scaling work everyone was reading had held the
wrong thing fixed.

## What this programme holds fixed

Encoder family, evaluation protocol ([[held-out-evaluation]]), and seed count
([[seeds-and-variance]]) are fixed. Data volume and model capacity are the only
variables, and every comparison is run twice: once at equal data, once at equal compute.
Where those two disagree, the disagreement is the result.
