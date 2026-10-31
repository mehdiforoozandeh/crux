---
id: q1
type: question
schema: 2
title: Which sort that I wrote myself is fastest?
parent: root
status: open
stale: true
created: "2026-08-16T16:06:19"
updated: "2026-08-16T16:06:19"
---

# q1 — Which sort that I wrote myself is fastest?

Parent:: [[sortlab]]

## ELI5

Of the sorts I wrote, which one runs fastest?

## TL;DR

I wrote bubble, insertion, selection, merge, and quick sort. First I raced the three slowest ones. The best one would sort a thousand items in the least time. So far, insertion beat the other two.

Background:: [[wiki/sorting-algorithms-overview]], [[wiki/bubble-sort]]

## Question

I want to know which of the five sorts I coded runs fastest on my laptop. Reading about [[wiki/sorting-algorithms-overview]] helped me understand what each one does. The answer is the one that sorts a thousand random items in the least time.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

I timed three of them on a thousand random items. Insertion took about 5.2 milliseconds. Bubble with an early exit was not always the slowest, which surprised me. Selection took about 8.1 milliseconds. I have not timed merge and quick yet on their own.

<!-- crux:ledger:start -->
**6 children** · open 1, leaning 3, settled 2, parked 0

- `h1` [[h1_insertion_sort_beats_bubble_sort_on_ever|Insertion sort beats bubble sort on every list I test]] — *leaning · moderate*
- `h2` [[h2_selection_sort_does_the_fewest_swaps_of_|Selection sort does the fewest swaps of the three slow sorts]] — *settled · strong*
- `h3` [[h3_my_merge_sort_is_the_fastest_thing_i_wro|My merge sort is the fastest thing I wrote]] — *open*
- `q8` _(Q)_ [[q8_which_of_the_three_slow_sorts_is_least_s|Which of the three slow sorts is least slow?]] — *settled · strong*
- `q9` _(Q)_ [[q9_does_merge_sort_beat_the_quick_sort_i_wr|Does merge sort beat the quick sort I wrote?]] — *leaning · moderate*
- `q10` _(Q)_ [[q10_does_my_quick_sort_break_on_a_list_that_|Does my quick sort break on a list that is already sorted?]] — *leaning · moderate*
<!-- crux:ledger:end -->
