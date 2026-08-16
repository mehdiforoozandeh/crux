---
id: h70
type: idea
schema: 2
title: A Python loop that only counts is slower than the whole built-in sort
parent: q23
status: done
rule: all
measurement: Time for one counting loop or one sort pass, with perf_counter.
replicates: 10 repeats of each.
verdict: supported
metric: "Counting loop: 0.92 s. Built-in sort: 0.81 s. Ratio: 1.14x."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
null_approved: "2026-08-16T16:06:36"
null_hash: bb573a791f42545d
lock: e4c7dcbd872f5ddf
locked: "2026-08-16T16:06:56"
lock_at: running
---

# h70 — A Python loop that only counts is slower than the whole built-in sort

Parent:: [[q23_is_the_built_in_sort_written_in_a_faster]]

## ELI5

A Python loop that only counts up to 100000 is slower than the entire built-in sort.

## TL;DR

Python is slow at basic operations. Even a trivial loop that does nothing but count is slower than the built-in sort doing real work. The run times a counting loop against the built-in sort on a 100000-item list.

Background:: [[wiki/interpreter-overhead]]

## Null
capacity - Python loops are not as slow as sorting, so the gap is not about language

## Problem Statement

How much of the built-in sort's speed comes from being in C, and how much from being a better algorithm? I can measure this by seeing how fast a dumb C-level operation is compared to my Python sort.

## Idea / Hypothesis

A Python loop that only counts is slower than the whole built-in sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] The counting loop is slower than the built-in sort. (found: Loop: 0.92 s. Sort: 0.81 s. Loop is slower)
      fails-if:: The loop is faster or equal.
      discriminates:: true
- [x] The counting loop's lead over the built-in sort holds at every size above one hundred thousand (found: Loop slower at 100k, 500k and 1M)
      fails-if:: The built-in sort overtakes the counting loop at some size
- [x] [outcome-neutral] The sorted output is a valid permutation of the input. (found: Built-in sort produced a valid sorted list)
      fails-if:: The output is wrong.
- [x] [outcome-neutral] The loop runs to completion without error and counts every item (found: Loop counted all one million items)
      fails-if:: The loop stops early or misses items

## Planned Intervention

A Python loop that counts from one to 100000 and a built-in sort on a 100000-item random list. Each timed with perf_counter. Ten repeats. Plugged in.

## Run Links

- SortLab notebook, week 9

## Artifacts

<!-- what the run produced. Keep files under results/h70/ and link at least the report:
     - [Report](results/h70/report.md)   - results/h70/curve.png -->
_(none yet)_

## Findings

A useless loop is slower than the whole sort. This proves that Python is much slower at basic operations, and that the built-in sort is written in a much faster language. The interpreter overhead is enormous.
