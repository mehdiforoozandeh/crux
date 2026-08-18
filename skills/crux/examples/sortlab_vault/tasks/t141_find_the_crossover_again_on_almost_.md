---
id: t141
type: task
title: Find the crossover again on almost-sorted lists
category: benchmarking
parent: 
blocked_by: t101, t51
refs: q16
hypothesis_refs: "h48:supported"
status: done
created: "2026-08-16T16:07:30"
updated: "2026-08-16T16:08:03"
accepted: "2026-08-16T16:08:03"
---

# t141 — Find the crossover again on almost-sorted lists

Refs:: [[q16_where_does_merge_sort_overtake_insertion\|q16]]

## Why

I wanted to see if the crossover point moves for nearly-sorted data.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t141.csv

## Evidence

This result was supported. On almost-sorted lists, merge took over insertion much earlier. The crossover dropped from three thousand to around five hundred items.
