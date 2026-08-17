---
id: t148
type: task
title: Time ten runs in a row and look at the first one
category: benchmarking
parent: 
blocked_by: t101
refs: q19
hypothesis_refs: "h56:supported, h57:inconclusive"
status: done
created: "2026-08-16T16:07:31"
updated: "2026-08-16T16:08:04"
accepted: "2026-08-16T16:08:04"
---

# t148 — Time ten runs in a row and look at the first one

Refs:: [[q19_does_the_first_run_take_longer_than_the_\|q19]]

## Why

I wanted to understand warm-up: why the first run is always slower.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t148.csv

## Evidence

The first run being slower was supported. It took fourteen milliseconds; the next nine averaged six milliseconds. Warm-up vanishing after three runs was inconclusive.
