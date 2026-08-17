---
id: t135
type: task
title: Run every sort on a duplicate-heavy list
category: benchmarking
parent: 
blocked_by: t101, t65
refs: q14
hypothesis_refs: "h39:supported, h40:refuted"
status: done
created: "2026-08-16T16:07:30"
updated: "2026-08-16T16:08:02"
accepted: "2026-08-16T16:08:02"
---

# t135 — Run every sort on a duplicate-heavy list

Refs:: [[q14_what_happens_when_the_list_is_mostly_the\|q14]]

## Why

Tests all five sorts on a list with many duplicate values to see which ones handle repeats well.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t135.csv

## Evidence

Quick sort slowed down badly when many values were the same. Bubble sort was also affected but not as badly.
