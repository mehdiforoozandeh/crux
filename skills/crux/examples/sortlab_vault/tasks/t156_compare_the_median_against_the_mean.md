---
id: t156
type: task
title: Compare the median against the mean over thirty repeats
category: benchmarking
parent: 
blocked_by: t101, t66
refs: q35, q4
hypothesis_refs: "h107:supported, h9:refuted"
status: done
created: "2026-08-16T16:07:32"
updated: "2026-08-16T16:08:05"
accepted: "2026-08-16T16:08:05"
---

# t156 — Compare the median against the mean over thirty repeats

Refs:: [[q35_is_the_median_of_repeats_steadier_than_t\|q35]], [[q4_is_my_stopwatch_telling_me_the_truth\|q4]]

## Why

I compared median and mean to find which statistic is more reliable.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t156.csv

## Evidence

Median moving less than mean was supported. Over thirty runs, median varied by two percent; mean varied by five point three percent. A single run being enough was refuted.
