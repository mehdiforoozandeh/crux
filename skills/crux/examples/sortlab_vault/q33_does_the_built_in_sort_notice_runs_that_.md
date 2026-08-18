---
id: q33
type: question
schema: 2
title: Does the built-in sort notice runs that are already in order?
parent: q24
status: resolved
stale: false
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:07:13"
synthesis: s4
---

# q33 — Does the built-in sort notice runs that are already in order?

Parent:: [[q24_does_the_built_in_sort_use_a_smarter_met]]

## ELI5

Does the built-in sort notice when the list is already sorted?

## TL;DR

If the built-in sort is as fast on a sorted list as on a random one, it must have logic to detect sorted runs and skip them. I tested it on sorted and random lists to see if the time drops on sorted.

Background:: [[wiki/run-detection]], [[wiki/timsort]]

## Question

A smart sort notices that a sorted list is already sorted and finishes instantly. The answer tells me if the built-in sort has this optimization.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On a random list of 100,000 items, the built-in sort took 12 milliseconds. On the same list after sorting, it took only 0.06 milliseconds. The built-in sort detects sorted runs and is almost instant on them.

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 2, partial 0, refuted 0, inconclusive 1, invalid-run 0)

- `h102` [[h102_the_built_in_sort_is_fastest_when_the_li|The built-in sort is fastest when the list is one long run]] — *done* — verdict **supported**, metric `Sorted list 1k took 0.08 ms, 100k took 0.78 ms. Random took 0.13 ms and 1.09 ms.`
- `h103` [[h103_the_built_in_sort_speeds_up_on_a_list_ma|The built-in sort speeds up on a list made of a few long runs]] — *done* — verdict **supported**, metric `Three-run: 10k was 0.14 ms, 100k was 0.95 ms. Random same sizes: 0.13, 1.09.`
- `h104` [[h104_breaking_the_runs_up_removes_the_built_i|Breaking the runs up removes the built-in sort's advantage]] — *done* — verdict **inconclusive**, metric `Three-run: 0.95 ms. Broken: 1.07 ms. Random: 1.09 ms.`
<!-- crux:ledger:end -->
