---
id: t151
type: task
title: Run the harness during a video call
category: benchmarking
parent: 
blocked_by: t101
refs: q20
hypothesis_refs: "h60:invalid-run, h61:supported"
status: done
created: "2026-08-16T16:07:32"
updated: "2026-08-16T16:08:04"
accepted: "2026-08-16T16:08:04"
---

# t151 — Run the harness during a video call

Refs:: [[q20_do_background_apps_change_the_number\|q20]]

## Why

I ran my sort during a video call to see if performance dropped sharply.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t151.csv

## Evidence

This run was invalid-run. The video froze mid-test and locked the whole laptop. Background load changes the median less than the mean was supported before the freeze.
