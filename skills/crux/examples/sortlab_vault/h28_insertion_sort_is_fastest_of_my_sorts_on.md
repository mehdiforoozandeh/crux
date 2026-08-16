---
id: h28
type: idea
schema: 2
title: Insertion sort is fastest of my sorts on an already sorted list
parent: q11
status: done
rule: all
measurement: Time in milliseconds to sort each list, taken by the counter clock.
replicates: 30 repeats at each of 6 sizes
verdict: refuted
metric: Insertion 0.23 ms vs bubble-with-exit 0.18 ms at n=10000
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:32"
null_hash: da71841bdcf08213
lock: 32a6f1981760ccd1
locked: "2026-08-16T16:06:47"
lock_at: running
---

# h28 — Insertion sort is fastest of my sorts on an already sorted list

Parent:: [[q11_what_happens_on_a_list_that_is_already_s]]

## ELI5

Insertion was not the fastest sort when the list was already in order.

## TL;DR

I thought insertion sort would rank first on an already-sorted list because it skips extra work. Instead bubble with an early-exit beat it handily. The early-exit condition matters more than I expected.

Background:: [[wiki/sorted-input]]

## Null
selection - I only timed the shapes where the early exit was already going to help

## Problem Statement

After the stopwatch crisis I wanted to know which sort was best for each list shape. Sorted lists seemed like they would favour insertion most.

## Idea / Hypothesis

Insertion sort is fastest of my sorts on an already sorted list

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Insertion sort finished faster than selection sort on the sorted list. (found: Insertion 0.23 ms vs bubble-with-exit 0.18 ms at n=10000)
      fails-if:: Selection kept pace with insertion or beat it on sorted input.
      discriminates:: true
- [ ] Bubble with early exit tied with or beat insertion on sorted input.
      fails-if:: Insertion stayed faster than bubble-with-early-exit across all sizes.
- [x] [outcome-neutral] All three sorts produced lists in order. (found: All three outputs were correct, sorted copies of the input)
      fails-if:: The output list was not sorted or was not a rearrangement of input.

## Planned Intervention

Three sorts on a list of ten thousand items already in ascending order. Thirty repeats at each size from one thousand up to one hundred thousand. Used the counter clock, discarded the first run.

## Run Links

- SortLab notebook, week 5

## Artifacts

<!-- what the run produced. Keep files under results/h28/ and link at least the report:
     - [Report](results/h28/report.md)   - results/h28/curve.png -->
_(none yet)_

## Findings

Bubble with an early-exit condition was fastest on the sorted list. Insertion came second. The early-exit meant bubble stopped as soon as it saw the list was in order, making it almost as fast as the check that triggered it.
