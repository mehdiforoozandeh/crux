---
id: t155
type: task
title: Look at the slowest run in every set of thirty
category: benchmarking
parent: 
blocked_by: t101, t75
refs: q22, q35
hypothesis_refs: "h67:refuted, h108:invalid-run"
status: done
created: "2026-08-16T16:07:32"
updated: "2026-08-16T16:08:05"
accepted: "2026-08-16T16:08:05"
---

# t155 — Look at the slowest run in every set of thirty

Refs:: [[q22_how_many_repeats_do_i_need_before_the_nu\|q22]], [[q35_is_the_median_of_repeats_steadier_than_t\|q35]]

## Why

I looked at the slowest run in each batch of thirty to understand outliers.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t155.csv

## Evidence

The slowest being always an outlier was refuted. Most were just on the high end of normal spread. Removing the three slowest was invalid-run because I changed the rule after seeing results.
