---
id: t120
type: task
title: Run selection sort against insertion sort on random lists
category: benchmarking
parent: 
blocked_by: t101, t50
refs: q8
hypothesis_refs: "h19:refuted"
status: done
created: "2026-08-16T16:07:28"
updated: "2026-08-16T16:08:00"
accepted: "2026-08-16T16:08:00"
---

# t120 — Run selection sort against insertion sort on random lists

Refs:: [[q8_which_of_the_three_slow_sorts_is_least_s\|q8]]

## Why

Tests selection sort against insertion head to head to see which one wins on random lists.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t120.csv

## Evidence

Selection was not between insertion and bubble as I thought. It landed outside that range at several sizes.
