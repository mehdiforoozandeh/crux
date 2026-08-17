---
id: t128
type: task
title: Run my quick sort on an already sorted list
category: benchmarking
parent: 
blocked_by: t101, t84
refs: q10
hypothesis_refs: "h25:supported, h26:supported"
status: done
created: "2026-08-16T16:07:29"
updated: "2026-08-16T16:08:01"
accepted: "2026-08-16T16:08:01"
---

# t128 — Run my quick sort on an already sorted list

Refs:: [[q10_does_my_quick_sort_break_on_a_list_that_\|q10]]

## Why

Tests quick sort on an already sorted list because that is the worst case for the algorithm.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t128.csv

## Evidence

On an already sorted list, quick sort was hopeless. By ten thousand items, it hit the recursion limit and crashed.
