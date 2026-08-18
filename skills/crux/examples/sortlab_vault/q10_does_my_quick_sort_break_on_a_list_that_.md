---
id: q10
type: question
schema: 2
title: Does my quick sort break on a list that is already sorted?
parent: q1
status: open
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:20"
---

# q10 — Does my quick sort break on a list that is already sorted?

Parent:: [[q1_which_sort_that_i_wrote_myself_is_fastes]]

## ELI5

Does my quick sort break on a sorted list?

## TL;DR

Quick sort picks a pivot and splits the list there. If the list is already sorted, picking the first item as the pivot is a disaster. The sort might be so slow that it times out. I want to know if my quick sort has this problem.

Background:: [[wiki/pivot-choice]], [[wiki/recursion-depth]]

## Question

Quick sort can be very slow on a sorted list if I pick a bad pivot. I chose the first element, which is a bad choice for a sorted list. Does my implementation fall into the trap, or does something save it?

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On a sorted list of 10,000 items, my quick sort took 18 milliseconds, much slower than the 2.4 milliseconds on random items. It is not as bad as bubble, but it is definitely hurting. I have not optimized the pivot choice yet.

<!-- crux:ledger:start -->
**3 children** · ideas 2/3 done (supported 2, partial 0, refuted 0, inconclusive 0, invalid-run 0)

- `h25` [[h25_my_quick_sort_takes_far_longer_on_an_alr|My quick sort takes far longer on an already sorted list]] — *done* — verdict **supported**, metric `At 20k: random 6 ms, sorted 45 ms (7.5 times slower), reversed 47 ms.`
- `h26` [[h26_my_quick_sort_hits_the_recursion_limit_a|My quick sort hits the recursion limit at ten thousand sorted items]] — *done* — verdict **supported**, metric `Quick sort fails at exactly 10000 sorted items with RecursionError.`
- `h27` [[h27_picking_the_middle_item_as_the_pivot_fix|Picking the middle item as the pivot fixes the sorted-list blow-up]] — *running*
<!-- crux:ledger:end -->
