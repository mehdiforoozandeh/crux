---
id: q8
type: question
schema: 2
title: Which of the three slow sorts is least slow?
parent: q1
status: resolved
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:07:13"
---

# q8 — Which of the three slow sorts is least slow?

Parent:: [[q1_which_sort_that_i_wrote_myself_is_fastes]]

## ELI5

Of bubble, insertion, and selection, which is least slow?

## TL;DR

These three sorts are all slow, but one is less slow than the others. I timed all three on a thousand-item random list and measured each thirty times. The one with the shortest median time wins.

Background:: [[wiki/bubble-sort]], [[wiki/insertion-sort]], [[wiki/selection-sort]]

## Question

Bubble, insertion, and selection all have a bad time complexity. But on a real laptop with a real thousand items, one of them might still be faster than the others. The answer is which one.

## Protocol

1,000 random items. Thirty repeats. Counter clock. Median time wins. Skip the first run as warm-up.

## Answer so far

Insertion took 5.2 milliseconds. Bubble with an early exit took 6.1 milliseconds. Selection took 8.1 milliseconds. Insertion is the clear winner here. But on a nearly sorted list, the gap might close up.

<!-- crux:ledger:start -->
**5 children** · open 0, leaning 3, settled 2, parked 0 · 1 finding(s) on this question

- `h17` [[h17_insertion_sort_is_the_fastest_of_the_thr|Insertion sort is the fastest of the three slow sorts]] — *leaning · moderate*
- `h18` [[h18_bubble_sort_is_the_slowest_of_the_three_|Bubble sort is the slowest of the three at every size]] — *settled · strong*
- `h19` [[h19_selection_sort_sits_between_the_other_tw|Selection sort sits between the other two on random lists]] — *leaning · moderate*
- `h20` [[h20_bubble_sort_with_an_early_exit_stops_bei|Bubble sort with an early exit stops being the slowest]] — *leaning · moderate*
- `h21` [[h21_the_three_slow_sorts_differ_by_less_than|The three slow sorts differ by less than two times]] — *settled · strong*
- `f88` finding (strong) [[f88_what_the_three_slow_sorts_settled|What the three slow sorts settled]]
<!-- crux:ledger:end -->
