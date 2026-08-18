---
id: t146
type: task
title: Compare the wall clock against the performance counter
category: benchmarking
parent: 
blocked_by: t101, t78
refs: q31
hypothesis_refs: "h97:supported, h98:supported"
status: done
created: "2026-08-16T16:07:31"
updated: "2026-08-16T16:08:04"
accepted: "2026-08-16T16:08:04"
---

# t146 — Compare the wall clock against the performance counter

Refs:: [[q31_does_it_matter_which_clock_function_i_ca\|q31]]

## Why

I needed to test if my wall clock was unreliable, as I suspected.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t146.csv

## Evidence

Both hypotheses were supported. The wall clock jumped backwards three times. The counter clock's step was one microsecond, much finer.
