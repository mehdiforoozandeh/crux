---
id: t161
type: task
title: Break the runs up and time the built-in sort again
category: benchmarking
parent: 
blocked_by: t116
refs: q33
hypothesis_refs: h104:supported
status: open
created: 2026-08-16T16:07:33
updated: 2026-08-16T16:07:33
---

# t161 — Break the runs up and time the built-in sort again

Refs:: [[q33_does_the_built_in_sort_notice_runs_that_\|q33]]

## Why

I broke those runs into smaller pieces to see if that removed the advantage.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
_(none yet)_

## Evidence

Breaking up runs was supported as removing the advantage. When runs got short, the built-in sort lost speed. It went from one millisecond to four milliseconds.

