---
type: wiki
title: Fine-tuning
summary: The adaptation protocol held fixed across every arm — end-to-end updates on the downstream task, with the schedule specified in advance.
category: method
sources: raw/kolesnikov2019_bit.pdf, raw/raffel2019_t5.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Fine-tuning

## Definition

Adapting a pretrained model by continuing to update all of its parameters on the
downstream task, as opposed to freezing the representation and fitting only a head.

## Why the protocol is fixed here

Fine-tuning has enough freedom — learning rate, schedule length, layer-wise decay,
augmentation — to move downstream accuracy by more than the scaling effects this
programme is trying to measure. Tuning it per arm would let a scaling claim be
manufactured out of adaptation choices, and would do so invisibly.

So the protocol is specified once, before any arm runs, and applied identically. Where
that disadvantages one arm, it is recorded as a known limitation rather than repaired
after the fact.

## The known cost of that choice

Kolesnikov et al. (2019) showed that a well-chosen shared recipe transfers well across
tasks at scale, which is what makes a fixed protocol defensible. It is not free: an arm
whose optimum sits away from the shared settings will underperform its own ceiling. The
alternative — tuning per arm — costs the comparison entirely
([[controlled-comparison]]).

## Relation to the question

Because everything downstream is fixed, a difference between arms is attributable to
what was varied upstream: data volume and model capacity. That attribution is the whole
reason for the constraint.
