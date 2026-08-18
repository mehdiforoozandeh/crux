---
id: t140
type: task
title: Find where merge sort overtakes insertion sort
category: benchmarking
parent: 
blocked_by: t101, t84
refs: q16
hypothesis_refs: "h47:refuted"
status: done
created: "2026-08-16T16:07:30"
updated: "2026-08-16T16:08:03"
accepted: "2026-08-16T16:08:03"
---

# t140 — Find where merge sort overtakes insertion sort

Refs:: [[q16_where_does_merge_sort_overtake_insertion\|q16]]

## Why

I had to find where merge becomes faster than insertion sort.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t140.csv

## Evidence

Merge taking over insertion below one thousand items was refuted. The crossover actually happened between two and five thousand items. I measured it at three thousand two hundred.
