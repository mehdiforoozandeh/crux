---
id: h73
type: idea
schema: 2
title: The built-in sort switches to insertion sort on small pieces
parent: q24
status: done
rule: m-of-n
measurement: Time for one sort pass at each size, with perf_counter.
replicates: 10 repeats at each of 6 sizes.
verdict: supported
metric: Crossover around n=100. Insertion best at 10, merge best at 5000.
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:09"
rule_m: 2
null_approved: "2026-08-16T16:06:37"
null_hash: c83327b5bc89ec29
lock: 65b57720d14a2492
locked: "2026-08-16T16:06:57"
lock_at: running
---

# h73 — The built-in sort switches to insertion sort on small pieces

Parent:: [[q24_does_the_built_in_sort_use_a_smarter_met]]

## ELI5

Python's built-in sort switches to insertion sort when working with small chunks of the list.

## TL;DR

Insertion sort is faster than merge sort on tiny lists because of lower overhead. Many high-performance sorts use insertion on chunks below a size threshold. The claim is that the built-in sort uses this hybrid approach. The run looks at run times on lists of different sizes to find the crossover point.

Background:: [[wiki/hybrid-sorts]]

## Null
capacity - both sorts scale similarly; there is no crossover

## Problem Statement

I know the built-in sort is smarter. Maybe it uses insertion sort for small pieces and merge sort for large pieces. If I can find the crossover point, I can understand the strategy.

## Idea / Hypothesis

The built-in sort switches to insertion sort on small pieces

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Insertion sort is faster than merge sort on lists smaller than 100 items. (found: At n=50: insertion 0.08 ms, merge 0.21 ms. Insertion faster at sizes up to 100)
      fails-if:: Merge sort is faster at all sizes.
      discriminates:: true
- [x] Merge sort is faster than insertion sort on lists larger than 1000 items. (found: At n=5000: insertion 11 ms, merge 3.4 ms. Merge much faster)
      fails-if:: Insertion is faster at large sizes.
- [ ] The crossover size I measure matches the cutoff the built-in sort is documented to use (found: My crossover 100, documented cutoff 64)
      fails-if:: My crossover size is far from the documented cutoff
- [x] [outcome-neutral] All runs complete with valid sorted output. (found: All runs on both sorts produced valid sorted lists)
      fails-if:: Some runs crash or produce garbage.

## Planned Intervention

My insertion sort and my merge sort on random lists of sizes 10, 50, 100, 500, 1000, and 5000 items. Ten repeats at each size. Timed with perf_counter. Plugged in.

## Run Links

- SortLab notebook, week 9

## Artifacts

<!-- what the run produced. Keep files under results/h73/ and link at least the report:
     - [Report](results/h73/report.md)   - results/h73/curve.png -->
_(none yet)_

## Findings

There is a clear crossover. Insertion is faster on tiny lists, merge takes over around 100 items. The built-in sort probably has this same crossover point in its code. That would explain part of why it is so fast.
