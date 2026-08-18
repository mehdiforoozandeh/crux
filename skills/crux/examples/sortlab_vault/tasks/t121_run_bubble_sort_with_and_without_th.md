---
id: t121
type: task
title: Run bubble sort with and without the early exit
category: benchmarking
parent: 
blocked_by: t101
refs: q8
hypothesis_refs: "h20:inconclusive"
status: done
created: "2026-08-16T16:07:28"
updated: "2026-08-16T16:08:00"
accepted: "2026-08-16T16:08:00"
---

# t121 — Run bubble sort with and without the early exit

Refs:: [[q8_which_of_the_three_slow_sorts_is_least_s\|q8]]

## Why

Tests whether the early exit optimization actually helps bubble sort beat the other two slow sorts.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t121.csv

## Evidence

The early exit sometimes helped bubble but not always. The results were too noisy to say whether it truly fixed things.
