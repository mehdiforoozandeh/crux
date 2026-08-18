---
id: t157
type: task
title: Time the built-in sort against my best sort at every size
category: benchmarking
parent: 
blocked_by: t101
refs: q5
hypothesis_refs: "h10:supported, h11:refuted"
status: done
created: "2026-08-16T16:07:32"
updated: "2026-08-16T16:07:56"
---

# t157 — Time the built-in sort against my best sort at every size

Refs:: [[q5_why_is_the_built_in_sort_so_hard_to_beat\|q5]]

## Why

I timed the built-in sort to see if I could beat it.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t157.csv

## Evidence

The built-in beating my best sort at every size was supported. Even at one million items, it was twice as fast. The gap shrinking as lists grow was refuted; the ratio stayed constant.
