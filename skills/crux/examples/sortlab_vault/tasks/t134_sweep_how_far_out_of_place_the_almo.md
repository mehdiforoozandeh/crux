---
id: t134
type: task
title: Sweep how far out of place the almost-sorted list is
category: benchmarking
parent: 
blocked_by: t101, t78
refs: q13
hypothesis_refs: "h37:inconclusive, h38:refuted"
status: done
created: "2026-08-16T16:07:29"
updated: "2026-08-16T16:08:02"
accepted: "2026-08-16T16:08:02"
---

# t134 — Sweep how far out of place the almost-sorted list is

Refs:: [[q13_what_happens_when_the_list_is_almost_sor\|q13]]

## Why

Slowly shuffles the almost-sorted list to find the point where it stops being an advantage.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/h37/report.md

## Evidence

Even with ten percent of the list out of place, insertion sort was faster than random. The threshold where it broke was somewhere higher.
