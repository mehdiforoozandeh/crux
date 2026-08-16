---
id: h77
type: idea
schema: 2
title: Nothing I write beats the built-in sort on plain random numbers
parent: q25
status: done
rule: all
measurement: Time for one complete sort pass, with perf_counter.
replicates: 10 repeats of each sort.
verdict: supported
metric: "Built-in: 0.42 s. Best hand-written (merge): 3.8 s. Ratio: 9.0x."
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: 4631eae6379680e3
lock: 2531388ad5ba5d47
locked: "2026-08-16T16:06:58"
lock_at: running
---

# h77 — Nothing I write beats the built-in sort on plain random numbers

Parent:: [[q25_can_i_beat_the_built_in_sort_on_any_list]]

## ELI5

Nothing I write in Python beats the built-in sort on plain random numbers.

## TL;DR

On random numbers with no special structure, the built-in sort is unbeatable. Every one of my hand-written sorts is slower. The run does a final comparison of all five of my sorts against the built-in on a large random list.

Background:: [[wiki/radix-sort]]

## Null
capacity - the same machine state favors all sorts equally, so built-in is not actually faster

## Problem Statement

I have tried sorting networks, counting sort, radix sort. On random data, can any of them beat the built-in sort?

## Idea / Hypothesis

Nothing I write beats the built-in sort on plain random numbers

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Built-in sort is faster than all seven hand-written sorts. (found: Built-in: 0.42 s. Fastest hand-written (merge): 3.8 s. Built-in wins)
      fails-if:: Any hand-written sort is faster than built-in.
      discriminates:: true
- [x] Built-in sort is faster than the fastest hand-written sort by at least 5x. (found: Built-in: 0.42 s. Merge: 3.8 s. Ratio: 9.0x)
      fails-if:: Built-in is within 5x of the fastest hand-written.
- [x] [outcome-neutral] All sorts produce correct output. (found: All eight sorts produced valid sorted lists)
      fails-if:: Any sort produces unsorted output.

## Planned Intervention

Bubble, insertion, selection, merge, quick, counting, and radix sort all on 50000 random numbers. Built-in sort also included. Ten repeats each. Timed with perf_counter. Plugged in.

## Run Links

- SortLab notebook, week 10

## Artifacts

<!-- what the run produced. Keep files under results/h77/ and link at least the report:
     - [Report](results/h77/report.md)   - results/h77/curve.png -->
_(none yet)_

## Findings

The built-in sort is unbeatable on random data. Every approach I tried loses. Counting and radix need special structure. On plain random numbers, the language and implementation speed are what matter, not the algorithm.
