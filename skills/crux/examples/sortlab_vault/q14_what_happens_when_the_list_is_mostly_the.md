---
id: q14
type: question
schema: 2
title: What happens when the list is mostly the same value?
parent: q2
status: resolved
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:07:13"
---

# q14 — What happens when the list is mostly the same value?

Parent:: [[q2_does_the_shape_of_the_list_change_which_]]

## ELI5

When most of the list is the same value, what happens?

## TL;DR

If 90 percent of the items are the same number, the sort has to deal with ties. Some sorts handle ties well, others do extra work. I made a list that is mostly zeros and ran all five sorts on it.

Background:: [[wiki/duplicate-heavy-input]], [[wiki/three-way-partition]]

## Question

A list with many duplicates is different from random. Bubble sort does not see duplicates as special. But merge and quick might have tricks. The answer is whether ties make a sort faster or slower.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On a list with 90 percent the same value, insertion took 4.8 milliseconds, slower than on random. Bubble took 38 milliseconds, about the same. Merge and quick were about the same speed as on random data. Duplicates do not help much.

<!-- crux:ledger:start -->
**3 children** · open 0, leaning 1, settled 2, parked 0 · 1 finding(s) on this question

- `h39` [[h39_my_quick_sort_slows_down_when_most_items|My quick sort slows down when most items are equal]] — *settled · strong*
- `h40` [[h40_bubble_sort_is_unaffected_by_duplicate_v|Bubble sort is unaffected by duplicate values]] — *settled · strong*
- `h41` [[h41_a_three_way_split_fixes_my_quick_sort_on|A three-way split fixes my quick sort on duplicate-heavy lists]] — *leaning · moderate*
- `f91` finding (strong) [[f91_what_the_shape_of_the_list_settled|What the shape of the list settled]]
<!-- crux:ledger:end -->
