---
id: t150
type: task
title: Run the harness with a music player open
category: benchmarking
parent: 
blocked_by: t101, t60
refs: q20
hypothesis_refs: "h59:refuted"
status: done
created: "2026-08-16T16:07:32"
updated: "2026-08-16T16:08:04"
accepted: "2026-08-16T16:08:04"
---

# t150 — Run the harness with a music player open

Refs:: [[q20_do_background_apps_change_the_number\|q20]]

## Why

I tested if background music changed my timing numbers significantly.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t150.csv

## Evidence

Background music adding more than five percent was refuted. It added less than one percent. Timing was stable whether music played or not.
