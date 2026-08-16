---
id: t125
type: task
title: Run my merge sort against my quick sort on random lists
category: benchmarking
parent: 
blocked_by: t101, t81
refs: q9
hypothesis_refs: "h22:refuted"
status: done
created: "2026-08-16T16:07:28"
updated: "2026-08-16T16:08:01"
accepted: "2026-08-16T16:08:01"
---

# t125 — Run my merge sort against my quick sort on random lists

Refs:: [[q9_does_merge_sort_beat_the_quick_sort_i_wr\|q9]]

## Why

Races my merge sort against my quick sort on random lists to find which of my fast sorts is actually faster.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/h22/report.md

## Evidence

Quick sort beat merge on random lists at sizes up to a hundred thousand. Merge never came close.
