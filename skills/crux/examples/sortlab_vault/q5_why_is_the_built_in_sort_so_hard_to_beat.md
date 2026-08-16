---
id: q5
type: question
schema: 2
title: Why is the built-in sort so hard to beat?
parent: root
status: open
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:20"
---

# q5 — Why is the built-in sort so hard to beat?

Parent:: [[sortlab]]

## ELI5

Why does the built-in sort beat everything I wrote?

## TL;DR

I raced my five sorts against Python's sort on dozens of lists. The built-in sort won every time, often by a huge margin. It is faster on random lists, on sorted lists, on everything. I want to know why it is so hard to beat.

Background:: [[wiki/timsort]], [[wiki/python-sorting-overview]]

## Question

The built-in sort is way faster than mine. On ten thousand random items, mine took 2 milliseconds and the built-in took 0.4 milliseconds. Why is it so much better? Is it the language, or a smarter method, or both?

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

The built-in sort beats all five of my sorts at every size I tested, from 1,000 to 1,000,000 items. It even beats them on lists that are already sorted. On a sorted list of 100,000 items, my insertion sort took 1.2 milliseconds but the built-in took 0.06 milliseconds.

<!-- crux:ledger:start -->
**6 children** · ideas 2/3 done (supported 1, partial 0, refuted 1, inconclusive 0, invalid-run 0) · sub-questions 1/3 resolved

- `h10` [[h10_the_built_in_sort_beats_my_best_sort_at_|The built-in sort beats my best sort at every size]] — *done* — verdict **supported**, metric `Merge sort: 18 ms at 100k. Built-in sort: 2 ms at 100k. Ratio: 9 times faster.`
- `h11` [[h11_the_gap_to_the_built_in_sort_shrinks_as_|The gap to the built-in sort shrinks as the list grows]] — *done* — verdict **refuted**, metric `At 1k: built-in 0.2 ms, merge 0.8 ms, ratio 4x. At 1m: built-in 2.5 ms, merge 22 ms, ratio 8.8x.`
- `h12` [[h12_i_can_close_the_gap_by_translating_my_me|I can close the gap by translating my merge sort line by line]] — *running*
- `q23` _(Q)_ [[q23_is_the_built_in_sort_written_in_a_faster|Is the built-in sort written in a faster language?]] — *resolved*
- `q24` _(Q)_ [[q24_does_the_built_in_sort_use_a_smarter_met|Does the built-in sort use a smarter method?]] — *review*
- `q25` _(Q)_ [[q25_can_i_beat_the_built_in_sort_on_any_list|Can I beat the built-in sort on any list at all?]] — *open*
<!-- crux:ledger:end -->
