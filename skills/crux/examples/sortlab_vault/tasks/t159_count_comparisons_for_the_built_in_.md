---
id: t159
type: task
title: Count comparisons for the built-in sort and my merge sort
category: benchmarking
parent: 
blocked_by: t101, t49
refs: q24
hypothesis_refs: "h74:refuted, h72:supported"
status: done
created: "2026-08-16T16:07:33"
updated: "2026-08-16T16:07:56"
---

# t159 — Count comparisons for the built-in sort and my merge sort

Refs:: [[q24_does_the_built_in_sort_use_a_smarter_met\|q24]]

## Why

I counted comparisons to understand the built-in sort's algorithm.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t159.csv

## Evidence

The built-in comparing fewer times than mine was refuted; it made more comparisons. It being not a plain merge sort was supported. It detects already-sorted stretches.
