---
id: t127
type: task
title: Repeat merge and quick sort thirty times and compare the spread
category: benchmarking
parent: 
blocked_by: t101
refs: q9
hypothesis_refs: "h24:inconclusive"
status: done
created: "2026-08-16T16:07:29"
updated: "2026-08-16T16:08:01"
accepted: "2026-08-16T16:08:01"
---

# t127 — Repeat merge and quick sort thirty times and compare the spread

Refs:: [[q9_does_merge_sort_beat_the_quick_sort_i_wr\|q9]]

## Why

Runs both fast sorts many times to see which one is more consistent from run to run.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t127.csv

## Evidence

Both sorts jittered run to run. Quick seemed worse on big lists but I did not collect enough data to say for sure.
