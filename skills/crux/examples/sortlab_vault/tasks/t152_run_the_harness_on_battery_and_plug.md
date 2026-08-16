---
id: t152
type: task
title: Run the harness on battery and plugged in
category: benchmarking
parent: 
blocked_by: t101, t84
refs: q21
hypothesis_refs: "h62:supported, h63:inconclusive"
status: done
created: "2026-08-16T16:07:32"
updated: "2026-08-16T16:08:04"
accepted: "2026-08-16T16:08:04"
---

# t152 — Run the harness on battery and plugged in

Refs:: [[q21_does_running_on_battery_change_the_numbe\|q21]]

## Why

I ran the same test on battery power and while plugged in.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/h62/report.md

## Evidence

Sorting slower on battery was supported. Plugged in: ninety milliseconds. On battery: one hundred fourteen. The gap being bigger when nearly empty was inconclusive.
