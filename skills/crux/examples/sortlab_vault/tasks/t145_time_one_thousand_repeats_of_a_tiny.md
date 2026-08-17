---
id: t145
type: task
title: Time one thousand repeats of a tiny sort
category: benchmarking
parent: 
blocked_by: t101
refs: q18
hypothesis_refs: "h55:supported"
status: done
created: "2026-08-16T16:07:31"
updated: "2026-08-16T16:08:03"
accepted: "2026-08-16T16:08:03"
---

# t145 — Time one thousand repeats of a tiny sort

Refs:: [[q18_how_small_a_gap_can_my_timer_see\|q18]]

## Why

I tested if repeating a tiny sort one thousand times fixed the measurement.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/h55/report.md

## Evidence

This result was supported. One thousand repeats gave me numbers well above the floor. The total took about eight milliseconds to time.
