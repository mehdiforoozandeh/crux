---
id: h30
type: idea
schema: 2
title: Selection sort takes the same time sorted or not
parent: q11
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median reported.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Sorted 1.82 ms, random 1.85 ms at n=10000
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:33"
null_hash: 19b971a0121b77e0
lock: 939fa337bbe3cddb
locked: "2026-08-16T16:06:48"
lock_at: running
---

# h30 — Selection sort takes the same time sorted or not

Parent:: [[q11_what_happens_on_a_list_that_is_already_s]]

## ELI5

Selection sort takes the same time whether the list is sorted or random.

## TL;DR

Selection sort spent the same time on a sorted list as on a random one. Selection has to scan for the smallest item in each pass no matter what, so it cannot exploit pre-existing order.

Background:: [[wiki/sorted-input]]

## Null
selection - one list shape was not actually any different

## Problem Statement

I was curious whether any sort would be blind to list order. Selection sort's algorithm finds the minimum in each pass, which should not depend on order.

## Idea / Hypothesis

Selection sort takes the same time sorted or not

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Selection time on sorted and random lists differed by less than five percent. (found: Sorted 1.82 ms, random 1.85 ms at n=10000)
      fails-if:: Sorted input was more than ten percent faster than random.
      discriminates:: true
- [x] Selection time scaled quadratically with list size on both shapes.
      fails-if:: Time did not quadruple when size doubled.
- [x] [outcome-neutral] Both output lists were correctly sorted. (found: Both outputs correct and identical)
      fails-if:: Either output was not in order.
- [x] [outcome-neutral] The two input lists were truly different shapes. (found: One was random, one was pre-sorted, verified by checking order)
      fails-if:: Both input lists happened to be sorted or nearly so.

## Planned Intervention

Selection sort on sorted and random lists of ten thousand items each. Thirty repeats from one thousand to one hundred thousand. Counter clock.

## Run Links

- SortLab notebook, week 5

## Artifacts

- [Report](results/h30/report.md)

## Findings

Selection sort took essentially the same time on sorted and random lists. The algorithm cannot skip the scan for the minimum in each pass, so list order did not matter. Time scaled quadratically in both cases.
