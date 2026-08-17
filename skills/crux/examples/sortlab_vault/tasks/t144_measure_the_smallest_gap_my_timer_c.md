---
id: t144
type: task
title: Measure the smallest gap my timer can see
category: benchmarking
parent: 
blocked_by: t101, t54
refs: q18
hypothesis_refs: "h53:refuted, h54:supported"
status: done
created: "2026-08-16T16:07:31"
updated: "2026-08-16T16:08:03"
accepted: "2026-08-16T16:08:03"
---

# t144 — Measure the smallest gap my timer can see

Refs:: [[q18_how_small_a_gap_can_my_timer_see\|q18]]

## Why

I needed to find the smallest time gap my timer could reliably measure.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t144.csv

## Evidence

My timer seeing gaps only as large as milliseconds was refuted. It could measure microseconds. But timing one hundred items was supported as below the floor.
