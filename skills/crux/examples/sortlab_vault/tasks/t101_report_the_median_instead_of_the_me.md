---
id: t101
type: task
title: Report the median instead of the mean
category: benchmarking
parent: 
blocked_by: t100
refs: q4
hypothesis_refs: 
status: done
created: "2026-08-16T16:07:25"
updated: "2026-08-16T16:07:49"
---

# t101 — Report the median instead of the mean

Refs:: [[q4_is_my_stopwatch_telling_me_the_truth\|q4]]

## Why

The median ignores outliers, so one slow run from background noise does not ruin the whole measurement.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/t101_report_the_median_instea.csv

## Evidence

_(experiments only: what this run showed, in prose. The structured fact is
`hypothesis_refs` in the frontmatter; this is the narrative beside it, and the
engine never parses it.)_
