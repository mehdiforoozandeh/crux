---
id: q13
type: question
schema: 2
title: What happens when the list is almost sorted?
parent: q2
status: review
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:20"
---

# q13 — What happens when the list is almost sorted?

Parent:: [[q2_does_the_shape_of_the_list_change_which_]]

## ELI5

When the list is almost sorted, how fast is each sort?

## TL;DR

A nearly sorted list is common in real life. Maybe one percent of the items are in the wrong place. Some sorts should be very fast on this, especially insertion. I need to test all five on a nearly sorted list.

Background:: [[wiki/nearly-sorted-input]], [[wiki/run-detection]]

## Question

A list with most items in order but a few out of place should be fast for insertion but still hard for bubble. The answer is whether the nearly-sorted case is closer to random or to fully sorted.

## Protocol

Make a 10,000-item sorted list and swap one percent of the pairs. Thirty repeats. Median time. Counter clock.

## Answer so far

Insertion on nearly sorted was 1.1 milliseconds, very close to sorted time. Bubble was still slow, 37 milliseconds. Merge was 2.0 milliseconds. Insertion adapts best to the shape of the input.

<!-- crux:ledger:start -->
**5 children** · open 0, leaning 1, settled 4, parked 0

- `h34` [[h34_insertion_sort_is_nearly_as_fast_on_almo|Insertion sort is nearly as fast on almost-sorted as on sorted]] — *settled · strong*
- `h35` [[h35_merge_sort_gains_nothing_from_an_almost_|Merge sort gains nothing from an almost-sorted list]] — *settled · strong*
- `h36` [[h36_the_built_in_sort_gains_the_most_from_an|The built-in sort gains the most from an almost-sorted list]] — *settled · strong*
- `h37` [[h37_one_item_out_of_place_costs_insertion_so|One item out of place costs insertion sort almost nothing]] — *leaning · moderate*
- `h38` [[h38_ten_percent_out_of_place_is_already_as_b|Ten percent out of place is already as bad as random]] — *settled · strong*
<!-- crux:ledger:end -->
