---
id: t143
type: task
title: Compare my merge sort against an in-place version
category: benchmarking
parent: 
blocked_by: t101, t75
refs: q17
hypothesis_refs: "h51:supported"
status: done
created: "2026-08-16T16:07:31"
updated: "2026-08-16T16:08:03"
accepted: "2026-08-16T16:08:03"
---

# t143 — Compare my merge sort against an in-place version

Refs:: [[q17_does_the_laptop_s_memory_show_up_in_the_\|q17]]

## Why

I wondered if my merge sort was slow because of making new lists.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t143.csv

## Evidence

This result was supported. Rewriting merge to reuse memory sped it up by thirty percent. Creating new lists every time does add real cost.
