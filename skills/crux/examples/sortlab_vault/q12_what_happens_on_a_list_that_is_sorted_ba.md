---
id: q12
type: question
schema: 2
title: What happens on a list that is sorted backwards?
parent: q2
status: resolved
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:07:13"
synthesis: s2
---

# q12 — What happens on a list that is sorted backwards?

Parent:: [[q2_does_the_shape_of_the_list_change_which_]]

## ELI5

When the list is backwards, which sort wins?

## TL;DR

A reversed list is another special case. Insertion has to move every item all the way. Bubble also has trouble, but at least it moves items one step at a time. I tested all five sorts on a 10,000-item reversed list.

Background:: [[wiki/reverse-sorted-input]]

## Question

The worst case for a slow sort is often a reversed list. I want to see how each sort handles it. The times tell me which sorts are robust and which ones break on bad input.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

Bubble took 41 milliseconds on a reversed list. Insertion took 24 milliseconds. Selection took 8.2 milliseconds, almost the same as on random. Merge took 2.2 milliseconds, hardly different. Merge is the most stable sort here.

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 2, partial 0, refuted 0, inconclusive 1, invalid-run 0)

- `h31` [[h31_a_backwards_list_is_the_worst_case_for_i|A backwards list is the worst case for insertion sort]] — *done* — verdict **supported**, metric `Sorted 0.23 ms, reversed 3.12 ms at n=10000`
- `h32` [[h32_a_backwards_list_is_the_worst_case_for_b|A backwards list is the worst case for bubble sort too]] — *done* — verdict **inconclusive**, metric `Bubble-with-exit 1.89 ms, without exit 1.94 ms at n=10000`
- `h33` [[h33_merge_sort_does_not_care_that_the_list_i|Merge sort does not care that the list is backwards]] — *done* — verdict **supported**, metric `Sorted 0.64 ms, reversed 0.63 ms, random 0.67 ms at n=10000`
<!-- crux:ledger:end -->
