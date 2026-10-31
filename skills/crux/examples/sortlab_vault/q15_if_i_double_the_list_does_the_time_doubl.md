---
id: q15
type: question
schema: 2
title: If I double the list, does the time double?
parent: q3
status: open
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:20"
---

# q15 — If I double the list, does the time double?

Parent:: [[q3_how_does_the_time_grow_when_the_list_get]]

## ELI5

When I double the list size, does the time double?

## TL;DR

Insertion on 1,000 items takes maybe 0.5 milliseconds. On 2,000 items, it might take 2 milliseconds, which is four times longer. I want to see the pattern for each sort: does the time double or quadruple or worse?

Background:: [[wiki/doubling-experiments]], [[wiki/big-o-notation]]

## Question

Each sort should have a pattern for how it scales. Insertion might quadruple when I double the size. Merge might only double. The pattern is called the growth rate and it predicts what happens at huge sizes.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

Insertion on 1,000 items takes 0.5 milliseconds, on 2,000 it takes 2.1 milliseconds, on 4,000 it takes 8.8 milliseconds. That is roughly four times each time I double. Insertion quadruples.

<!-- crux:ledger:start -->
**6 children** · open 2, leaning 1, settled 3, parked 0

- `h42` [[h42_doubling_the_list_doubles_the_time_for_m|Doubling the list doubles the time for merge sort]] — *settled · strong*
- `h43` [[h43_doubling_the_list_quadruples_the_time_fo|Doubling the list quadruples the time for insertion sort]] — *settled · strong*
- `h44` [[h44_the_doubling_ratio_for_bubble_sort_is_cl|The doubling ratio for bubble sort is close to four]] — *leaning · moderate*
- `h45` [[h45_the_built_in_sort_doubles_a_little_more_|The built-in sort doubles a little more than twice]] — *open*
- `h46` [[h46_the_doubling_ratio_is_the_same_on_batter|The doubling ratio is the same on battery and plugged in]] — *open*
- `q34` _(Q)_ [[q34_does_the_doubling_ratio_settle_down_at_b|Does the doubling ratio settle down at big sizes?]] — *settled · strong*
<!-- crux:ledger:end -->
