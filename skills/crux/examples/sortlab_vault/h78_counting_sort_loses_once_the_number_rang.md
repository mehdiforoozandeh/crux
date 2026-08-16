---
id: h78
type: idea
schema: 2
title: Counting sort loses once the number range gets wide
parent: q25
status: done
rule: all
measurement: Time for one complete sort pass, with perf_counter.
replicates: 10 repeats at each range.
verdict: supported
metric: "Range 0-10000: counting 0.21 s, built-in 0.82 s. Range 0-1M: counting 1.8 s, built-in 0.88 s."
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: fb579f6c34b5644c
lock: 5560515c6b5fcfd7
locked: "2026-08-16T16:06:58"
lock_at: running
---

# h78 — Counting sort loses once the number range gets wide

Parent:: [[q25_can_i_beat_the_built_in_sort_on_any_list]]

## ELI5

Counting sort becomes slower than the built-in sort once the range of numbers gets too wide.

## TL;DR

Counting sort is O(n + k) where k is the range. When k is huge, that k term dominates. The claim is that a very wide range makes counting sort slower than the built-in. The run tests counting sort with small and wide number ranges.

Background:: [[wiki/counting-sort]]

## Null
capacity - both sorts adapt equally; the range does not favor one over the other

## Problem Statement

Counting sort worked great on 0 to 1000. But what if the range is wider? Does it become slower?

## Idea / Hypothesis

Counting sort loses once the number range gets wide

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Counting sort wins on range 0-10000 but loses on range 0-1000000. (found: Range 0-10000: counting 0.21 s, built-in 0.82 s. Counting wins. Range 0-1M: counting 1.8 s, built-in 0.88 s. Built-in wins)
      fails-if:: Counting sort wins on both ranges or loses on both.
      discriminates:: true
- [x] On the wide range, built-in is at least 1.5x faster than counting sort. (found: Built-in: 0.88 s. Counting: 1.8 s. Ratio: 2.0x)
      fails-if:: Built-in is within 1.5x of counting on the wide range.
- [x] [outcome-neutral] Both sorts produce correct output at both ranges. (found: All outputs were correctly sorted)
      fails-if:: Either sort fails.

## Planned Intervention

Counting sort and built-in sort on 100000 numbers. First test: range 0 to 10000. Second test: range 0 to 1000000. Ten repeats each. Timed with perf_counter. Plugged in.

## Run Links

- SortLab notebook, week 10

## Artifacts

<!-- what the run produced. Keep files under results/h78/ and link at least the report:
     - [Report](results/h78/report.md)   - results/h78/curve.png -->
_(none yet)_

## Findings

Range size is the turning point. Counting sort wins on small ranges but loses on large ones. The k term in O(n + k) eventually dominates. There is a sweet spot for counting sort, and beyond it the built-in sort wins again.
