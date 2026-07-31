---
type: wiki
title: Compute budget
summary: Training compute as the quantity that must be held fixed for a data-versus-model comparison to mean anything, and how it is counted.
category: method
sources: raw/hoffmann2022_chinchilla.pdf, raw/kaplan2020_scaling_laws.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Compute budget

## What is counted

Training compute is usually reported as total floating-point operations, approximated
for a transformer as roughly six FLOPs per parameter per training token — forward and
backward passes together. The approximation is crude but stable enough to compare arms
of the same experiment, which is all that is needed here.

## Why it has to be held fixed

Data volume, epoch count and model size all move compute. An arm trained on twice the
data for the same number of epochs at the same model size costs twice as much. So the
comparison "more data versus better model" run at natural settings is confounded by
budget in the most basic way: one arm simply got more.

Holding compute fixed makes the two arms answer the question actually being asked —
*given what we can afford, where should it go* — rather than the question nobody needs
answered, which is whether spending more helps.

## How equalisation is done here

Two arms are matched by total training FLOPs. Where matching requires a partial epoch or
a non-integer step count, the arm is truncated rather than rounded up, so no arm is ever
over-budget. The equalised runs are reported alongside the equal-data runs; both are
kept, because their disagreement is the informative part ([[controlled-comparison]]).

## Caveats

FLOP-matching ignores wall-clock, memory traffic and hardware utilisation, which are the
costs a practitioner actually pays. It also ignores inference cost, which can dominate
over a deployed model's lifetime — the explicit reason LLaMA
([[transformer-language-models]]) trained past the compute-optimal point.
