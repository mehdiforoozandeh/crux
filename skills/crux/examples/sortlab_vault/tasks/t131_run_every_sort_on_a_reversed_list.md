---
id: t131
type: task
title: Run every sort on a reversed list
category: benchmarking
parent: 
blocked_by: t101, t75
refs: q12
hypothesis_refs: "h31:supported, h32:inconclusive"
status: done
created: "2026-08-16T16:07:29"
updated: "2026-08-16T16:08:02"
accepted: "2026-08-16T16:08:02"
---

# t131 — Run every sort on a reversed list

Refs:: [[q12_what_happens_on_a_list_that_is_sorted_ba\|q12]]

## Why

Tests all five sorts on a reversed list, which is the worst case for some algorithms.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t131.csv

## Evidence

Insertion sort was extremely slow on a reversed list, ten times slower than on random. Bubble's behavior was less clear.
