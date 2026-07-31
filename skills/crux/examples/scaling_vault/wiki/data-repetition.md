---
type: wiki
title: Data repetition and the data-constrained regime
summary: What happens when more data is not available: repeated epochs are nearly as good as fresh data for a few passes, then decay to worthless.
category: concept
sources: raw/muennighoff2023_data_constrained.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Data repetition and the data-constrained regime

## The setting

Standard scaling guidance ([[compute-optimal-training]]) assumes fresh data is available
in whatever quantity the budget justifies. Most real programmes are not in that regime —
the corpus is finite, and the question is what to do with the compute once it has been
seen once.

## The finding

Muennighoff et al. (2023) fit scaling laws under an explicit data constraint. Repeating
the training data for a small number of epochs — on the order of four — cost almost
nothing relative to training on the same volume of fresh data. Beyond that the value of
additional epochs decayed quickly, and eventually additional compute spent on repetition
bought nothing at all.

## Why it belongs in this vault

It bounds what "more data" is worth. If four epochs of a fixed corpus is nearly as good
as four times the corpus, then a data-collection programme has to beat that bar before
it justifies its cost — and a comparison that gives the data-heavy arm fresh examples
while the other arm sits idle is not measuring what it claims ([[compute-budget]]).

## Interaction with quality

Repetition amplifies whatever is wrong with the corpus. Duplicated documents effectively
receive extra epochs already, which is one route by which deduplication changes
measured scaling behaviour ([[data-quality]]).
