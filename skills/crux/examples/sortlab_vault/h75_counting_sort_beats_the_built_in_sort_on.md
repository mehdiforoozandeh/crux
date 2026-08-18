---
id: h75
type: idea
schema: 2
title: Counting sort beats the built-in sort on small whole numbers
parent: q25
status: done
rule: any
measurement: Time for one complete sort pass, with perf_counter.
replicates: 10 repeats of each.
verdict: supported
metric: "Counting sort: 0.18 s. Built-in: 0.81 s. Ratio: 4.5x."
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: 99094865b6325aec
lock: 81541323bb8a80b5
locked: "2026-08-16T16:06:57"
lock_at: running
---

# h75 — Counting sort beats the built-in sort on small whole numbers

Parent:: [[q25_can_i_beat_the_built_in_sort_on_any_list]]

## ELI5

Counting sort can beat the built-in sort when all the numbers are small and there are not many unique values.

## TL;DR

Counting sort is O(n + k) where k is the range. If k is small, counting sort is linear and unbeatable. The run tests counting sort against the built-in sort on lists of numbers from 0 to 1000 only.

Background:: [[wiki/radix-sort]]

## Null
capacity - the machine state favors built-in, so even counting sort cannot beat it

## Problem Statement

The built-in sort wins on random numbers. But maybe on a restricted range of small numbers, a counting sort could win.

## Idea / Hypothesis

Counting sort beats the built-in sort on small whole numbers

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Counting sort finishes faster than the built-in sort. (found: Counting: 0.18 s. Built-in: 0.81 s. Counting wins)
      fails-if:: Built-in sort is faster.
      discriminates:: true
- [ ] Counting sort is at least 2x faster than built-in. (found: Counting: 0.18 s. Built-in: 0.81 s. Ratio: 4.5x faster)
      fails-if:: Built-in is within 2x of counting sort.
- [x] [outcome-neutral] Both sorts produce correct output. (found: Both counting and built-in produced valid sorted lists)
      fails-if:: Either sort produces garbage or crashes.
- [x] [outcome-neutral] All input numbers are in the range 0 to 1000. (found: Verified: all input numbers were between 0 and 1000)
      fails-if:: Numbers are outside the expected range.

## Planned Intervention

Counting sort and built-in sort on 100000 random numbers all between 0 and 1000. Ten repeats. Timed with perf_counter. Plugged in.

## Run Links

- SortLab notebook, week 10

## Artifacts

<!-- what the run produced. Keep files under results/h75/ and link at least the report:
     - [Report](results/h75/report.md)   - results/h75/curve.png -->
_(none yet)_

## Findings

Counting sort actually works better on this task. When the numbers are limited to a small range, counting sort is much faster. The built-in sort is general-purpose, so it cannot take advantage of this special case.
