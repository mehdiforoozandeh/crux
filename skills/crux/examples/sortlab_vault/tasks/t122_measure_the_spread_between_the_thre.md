---
id: t122
type: task
title: Measure the spread between the three slow sorts at one size
category: benchmarking
parent: 
blocked_by: t101, t78
refs: q8
hypothesis_refs: "h21:refuted"
status: done
created: "2026-08-16T16:07:28"
updated: "2026-08-16T16:08:00"
accepted: "2026-08-16T16:08:00"
---

# t122 — Measure the spread between the three slow sorts at one size

Refs:: [[q8_which_of_the_three_slow_sorts_is_least_s\|q8]]

## Why

Measures the actual time gap between the three slow sorts to see if they are close or far apart.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t122.csv

## Evidence

The three sorts were more different than I expected. At ten thousand items, the fastest was more than twice as fast as the slowest.
