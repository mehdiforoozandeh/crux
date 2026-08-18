---
id: t123
type: task
title: Run insertion sort against bubble sort on all five shapes
category: benchmarking
parent: 
blocked_by: t101, t53
refs: q1
hypothesis_refs: "h1:refuted"
status: done
created: "2026-08-16T16:07:28"
updated: "2026-08-16T16:08:01"
accepted: "2026-08-16T16:08:01"
---

# t123 — Run insertion sort against bubble sort on all five shapes

Refs:: [[q1_which_sort_that_i_wrote_myself_is_fastes\|q1]]

## Why

Tests insertion against bubble on all five shapes to see if one shape changes which sort wins.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/h1/report.md

## Evidence

Insertion did not beat bubble everywhere. On a reversed list, bubble with the early exit was much faster.
