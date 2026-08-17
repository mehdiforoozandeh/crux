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
synthesis: s1
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
**5 children** · ideas 5/5 done (supported 1, partial 0, refuted 3, inconclusive 1, invalid-run 0)

- `h17` [[h17_insertion_sort_is_the_fastest_of_the_thr|Insertion sort is the fastest of the three slow sorts]] — *done* — verdict **supported**, metric `Random: insertion 0.23 s, bubble 1.6 s, selection 0.91 s. Sorted: insertion 0.01 s, bubble 0.12 s.`
- `h18` [[h18_bubble_sort_is_the_slowest_of_the_three_|Bubble sort is the slowest of the three at every size]] — *done* — verdict **refuted**, metric `Bubble vs insertion: 1.62 s vs 0.34 s at 100k random. Bubble vs selection: 1.62 s vs 0.91 s.`
- `h19` [[h19_selection_sort_sits_between_the_other_tw|Selection sort sits between the other two on random lists]] — *done* — verdict **refuted**, metric `At 50k: insertion 0.12 s, selection 0.45 s, bubble 0.81 s`
- `h20` [[h20_bubble_sort_with_an_early_exit_stops_bei|Bubble sort with an early exit stops being the slowest]] — *done* — verdict **inconclusive**, metric `On sorted: regular bubble 0.81 s, early-exit bubble 0.01 s. On random: both take 1.6 s.`
- `h21` [[h21_the_three_slow_sorts_differ_by_less_than|The three slow sorts differ by less than two times]] — *done* — verdict **refuted**, metric `Random 100k: bubble 1.6 s, insertion 0.34 s, selection 0.91 s. Fastest to slowest: 4.7 times.`
<!-- crux:ledger:end -->
