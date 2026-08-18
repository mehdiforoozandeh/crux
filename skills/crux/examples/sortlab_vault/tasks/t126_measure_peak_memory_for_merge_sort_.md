---
id: t126
type: task
title: Measure peak memory for merge sort and quick sort
category: benchmarking
parent: 
blocked_by: t101, t56
refs: q9
hypothesis_refs: "h23:supported"
status: done
created: "2026-08-16T16:07:28"
updated: "2026-08-16T16:08:01"
accepted: "2026-08-16T16:08:01"
---

# t126 — Measure peak memory for merge sort and quick sort

Refs:: [[q9_does_merge_sort_beat_the_quick_sort_i_wr\|q9]]

## Why

Measures how much memory merge and quick sort use so I can see if speed comes with a memory cost.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t126.csv

## Evidence

Quick sort used less memory than merge at every size. By ten thousand items, merge was using twice as much.
