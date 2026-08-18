---
id: q34
type: question
schema: 2
title: Does the doubling ratio settle down at big sizes?
parent: q15
status: resolved
stale: true
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:07:14"
synthesis: s5
---

# q34 — Does the doubling ratio settle down at big sizes?

Parent:: [[q15_if_i_double_the_list_does_the_time_doubl]]

## ELI5

Does the doubling pattern stay the same at big sizes?

## TL;DR

For small sizes, doubling the list roughly quadruples insertion's time. But at very large sizes, the pattern might break. I want to know if the pattern is stable all the way to a million items.

Background:: [[wiki/doubling-experiments]], [[wiki/average-case-analysis]]

## Question

The growth rate should be consistent if the theory is right. But at very large sizes, memory or cache effects might change the pattern. The answer tells me if O(n squared) holds for all sizes.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

From 1,000 to 100,000 items, insertion quadruples every time I double. From 100,000 to 1,000,000, it still quadruples, about 4.1 times. The pattern holds all the way up. The growth rate is stable.

<!-- crux:ledger:start -->
**2 children** · ideas 2/2 done (supported 1, partial 0, refuted 0, inconclusive 1, invalid-run 0)

- `h105` [[h105_the_doubling_ratio_settles_above_one_hun|The doubling ratio settles above one hundred thousand items]] — *done* — verdict **inconclusive**, metric `Ratios: 1k to 2k was 3.8. 10k to 20k was 4.1. 500k to 1M was 4.2.`
- `h106` [[h106_the_measured_ratio_is_closer_to_four_tha|The measured ratio is closer to four than to two for insertion sort]] — *done* — verdict **supported**, metric `Doubling ratio averaged 4.1 across four size pairs from 10k to 1M.`
<!-- crux:ledger:end -->
