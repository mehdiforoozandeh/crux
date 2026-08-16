---
id: t142
type: task
title: Sort lists that are bigger than the cache
category: benchmarking
parent: 
blocked_by: t101
refs: q17
hypothesis_refs: "h50:inconclusive"
status: done
created: "2026-08-16T16:07:30"
updated: "2026-08-16T16:08:03"
accepted: "2026-08-16T16:08:03"
---

# t142 — Sort lists that are bigger than the cache

Refs:: [[q17_does_the_laptop_s_memory_show_up_in_the_\|q17]]

## Why

I needed to see what happens when the list exceeds the processor cache.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t142.csv

## Evidence

This hypothesis was inconclusive. Some slowdown happened, but not sharply. It was gradual from eight thousand items onward. No sudden cliff.
