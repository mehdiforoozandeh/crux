---
id: h76
type: idea
schema: 2
title: Radix sort beats the built-in sort on fixed-width numbers
parent: q25
status: done
rule: all
measurement: Time for one complete sort pass, with perf_counter.
replicates: 10 repeats of each.
verdict: inconclusive
metric: "Radix: 0.34 s. Built-in: 0.82 s. Ratio: 2.4x."
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: 60d5a94393a0e1a3
lock: 01d2649cc2f34e2e
locked: "2026-08-16T16:06:58"
lock_at: running
---

# h76 — Radix sort beats the built-in sort on fixed-width numbers

Parent:: [[q25_can_i_beat_the_built_in_sort_on_any_list]]

## ELI5

Radix sort can beat the built-in sort on lists of fixed-width numbers.

## TL;DR

Radix sort is linear if the numbers have a fixed number of digits. The claim is that radix sort beats the built-in sort on a list of fixed-width numbers. The run tests both.

Background:: [[wiki/counting-sort]]

## Null
capacity - radix sort simply has more room to spend on this laptop than the built-in

## Problem Statement

Counting sort worked on a limited range. But radix sort works on any fixed-width numbers without an upper bound. Maybe radix sort can also beat the built-in on larger numbers.

## Idea / Hypothesis

Radix sort beats the built-in sort on fixed-width numbers

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Radix sort beats the built-in sort. (found: Radix: 0.34 s. Built-in: 0.82 s. But close)
      fails-if:: Built-in sort is faster or equal.
      discriminates:: true
- [-] Radix sort is at least 2x faster than built-in. (found: Radix: 0.34 s. Built-in: 0.82 s. Ratio: 2.4x. Barely over 2x)
      fails-if:: Built-in is within 2x of radix.
- [x] [outcome-neutral] Both sorts produce correct output. (found: Both radix and built-in produced valid sorted lists)
      fails-if:: Either output is wrong.

## Planned Intervention

Radix sort and built-in sort on 100000 random 32-bit integers. Ten repeats. Timed with perf_counter. Plugged in.

## Run Links

- SortLab notebook, week 10

## Artifacts

- [Report](results/h76/report.md)

## Findings

Radix sort wins, but just barely. The Python implementation is slow, and the built-in is very fast. Even a linear-time algorithm can barely beat the built-in when both are written in interpreted code versus compiled code.
