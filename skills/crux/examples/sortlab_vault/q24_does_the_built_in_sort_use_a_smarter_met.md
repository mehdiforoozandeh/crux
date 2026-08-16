---
id: q24
type: question
schema: 2
title: Does the built-in sort use a smarter method?
parent: q5
status: review
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q24 — Does the built-in sort use a smarter method?

Parent:: [[q5_why_is_the_built_in_sort_so_hard_to_beat]]

## ELI5

Does the built-in sort use a smarter algorithm?

## TL;DR

The built-in sort might use an algorithm like timsort that adapts to the input. My quick sort does not adapt. If the input is nearly sorted, timsort notices and runs very fast. That is probably why it wins.

Background:: [[wiki/timsort]], [[wiki/hybrid-sorts]]

## Question

I want to know if the built-in sort is smarter about detecting the shape of the list. The answer is whether it has tricks that my sorts do not use.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On a sorted list of 100,000 items, the built-in sort took 0.06 milliseconds but my merge sort took 2.0 milliseconds. The built-in sort must be noticing that the list is sorted. That is smarter than my sorts.

<!-- crux:ledger:start -->
**4 children** · ideas 3/3 done (supported 2, partial 0, refuted 1, inconclusive 0, invalid-run 0) · sub-questions 1/1 resolved

- `h72` [[h72_the_built_in_sort_is_not_a_plain_merge_s|The built-in sort is not a plain merge sort]] — *done* — verdict **supported**, metric `Built-in on sorted: 0.0082 s. On random: 0.81 s. Merge: both around 6.7 s.`
- `h73` [[h73_the_built_in_sort_switches_to_insertion_|The built-in sort switches to insertion sort on small pieces]] — *done* — verdict **supported**, metric `Crossover around n=100. Insertion best at 10, merge best at 5000.`
- `h74` [[h74_the_built_in_sort_compares_fewer_times_t|The built-in sort compares fewer times than my merge sort]] — *done* — verdict **refuted**, metric `Merge sort: 6.8 megacomps per second. Built-in: 18 megacomps per second.`
- `q33` _(Q)_ [[q33_does_the_built_in_sort_notice_runs_that_|Does the built-in sort notice runs that are already in order?]] — *resolved*
<!-- crux:ledger:end -->
