---
id: q17
type: question
schema: 2
title: Does the laptop's memory show up in the numbers?
parent: q3
status: open
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q17 — Does the laptop's memory show up in the numbers?

Parent:: [[q3_how_does_the_time_grow_when_the_list_get]]

## ELI5

Does my laptop's memory limit show up in the timing numbers?

## TL;DR

A laptop has fast memory close to the processor and slower memory further away. At some size, the list stops fitting in the fast memory and gets slower. I want to see if that jump shows up in my data.

Background:: [[wiki/cache-locality]], [[wiki/memory-allocation]]

## Question

When a list gets very large, it might not fit in the cache, and the sort has to wait for memory. This could cause a sudden slowdown. The answer tells me if this effect is real on my laptop.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

I have not seen a sudden jump in my timings yet. The slopes are smooth all the way from 1,000 to 1,000,000 items. My laptop might have enough cache, or the effect might be hidden by other variation.

<!-- crux:ledger:start -->
**3 children** · ideas 2/3 done (supported 1, partial 0, refuted 0, inconclusive 1, invalid-run 0)

- `h50` [[h50_sorting_slows_down_sharply_once_the_list|Sorting slows down sharply once the list stops fitting in cache]] — *done* — verdict **inconclusive**, metric `At n=500k: merge 2.1 sec; at n=1M: 5.8 sec (ratio 2.76)`
- `h51` [[h51_my_merge_sort_slows_down_because_it_make|My merge sort slows down because it makes new lists]] — *done* — verdict **supported**, metric `Standard merge 2.1 sec, reuse-space merge 1.7 sec at n=500k`
- `h52` [[h52_sorting_a_million_items_makes_the_laptop|Sorting a million items makes the laptop swap to disk]] — *staged*
<!-- crux:ledger:end -->
