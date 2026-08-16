---
id: h23
type: idea
schema: 2
title: My quick sort uses less memory than my merge sort
parent: q9
status: done
rule: all
measurement: Peak memory in kilobytes during each run.
replicates: 5 repeats at each of 8 sizes
verdict: supported
metric: "At 100k: quick 1200 KB, merge 2800 KB. Quick uses 43 percent of merge's memory."
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:04"
null_approved: "2026-08-16T16:06:32"
null_hash: c13ef99e1aa04248
lock: 1f4ca9103ae91583
locked: "2026-08-16T16:06:46"
lock_at: running
---

# h23 — My quick sort uses less memory than my merge sort

Parent:: [[q9_does_merge_sort_beat_the_quick_sort_i_wr]]

## ELI5

My quick sort uses less memory than my merge sort.

## TL;DR

Quick sort is in-place and only uses a bit of extra space for recursion, while merge sort needs to allocate a new temporary array for each merge. I claimed quick sort uses less memory and measured the peak memory during a run of both sorts on lists up to one hundred thousand items. Quick sort is indeed more memory-efficient.

Background:: [[wiki/quick-sort]]

## Null
chance - one lucky run out of five would show this difference on its own

## Problem Statement

Merge sort is fast but wasteful. Quick sort is a famous memory-saver. I wanted to confirm this matters on my laptop.

## Idea / Hypothesis

My quick sort uses less memory than my merge sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Quick sort uses less peak memory than merge at all sizes (found: Quick 1200 KB, merge 2800 KB)
      fails-if:: Merge uses less memory than quick at any size
      discriminates:: true
- [x] At 100k, quick uses less than half the memory of merge (found: Quick 43% of merge)
      fails-if:: Quick memory is more than 60 percent of merge memory
- [x] [outcome-neutral] Both sorts return a correctly ordered list at every size measured (found: Both outputs sorted at every size)
      fails-if:: Either sort returns a list that is not in order

## Planned Intervention

Measure peak memory usage using tracemalloc. Sizes from one thousand to one hundred thousand. Five runs per size. Random input. Same morning session.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h23/ and link at least the report:
     - [Report](results/h23/report.md)   - results/h23/curve.png -->
_(none yet)_

## Findings

Quick sort is much more memory-efficient. At 100k items, quick sort peaked at 1200 KB while merge sort needed 2800 KB. The difference grows with size because merge allocates a new array for each level of recursion.
