---
id: q25
type: question
schema: 2
title: Can I beat the built-in sort on any list at all?
parent: q5
status: open
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q25 — Can I beat the built-in sort on any list at all?

Parent:: [[q5_why_is_the_built_in_sort_so_hard_to_beat]]

## ELI5

Can I beat the built-in sort on any kind of list at all?

## TL;DR

The built-in sort wins on random, sorted, and nearly sorted lists. Is there any special case where one of my sorts beats it? Maybe on a list of only a few numbers?

Background:: [[wiki/counting-sort]], [[wiki/radix-sort]]

## Question

The built-in sort is very good at everything. Is there any input where one of my sorts is faster? The answer might be no, or it might be a very special case that does not matter.

## Protocol

Test on a list of integers from 0 to 100 shuffled randomly. Also test on a list with only zeros and ones. Use 100,000 items. Thirty repeats. Report the median.

## Answer so far

I tried merge sort on a list of mostly small integers. Still lost to the built-in sort. I have not yet tried a counting sort or radix sort, which are designed for small integer ranges. Maybe those could win.

<!-- crux:ledger:start -->
**5 children** · ideas 4/5 done (supported 3, partial 0, refuted 0, inconclusive 1, invalid-run 0)

- `h75` [[h75_counting_sort_beats_the_built_in_sort_on|Counting sort beats the built-in sort on small whole numbers]] — *done* — verdict **supported**, metric `Counting sort: 0.18 s. Built-in: 0.81 s. Ratio: 4.5x.`
- `h76` [[h76_radix_sort_beats_the_built_in_sort_on_fi|Radix sort beats the built-in sort on fixed-width numbers]] — *done* — verdict **inconclusive**, metric `Radix: 0.34 s. Built-in: 0.82 s. Ratio: 2.4x.`
- `h77` [[h77_nothing_i_write_beats_the_built_in_sort_|Nothing I write beats the built-in sort on plain random numbers]] — *done* — verdict **supported**, metric `Built-in: 0.42 s. Best hand-written (merge): 3.8 s. Ratio: 9.0x.`
- `h78` [[h78_counting_sort_loses_once_the_number_rang|Counting sort loses once the number range gets wide]] — *done* — verdict **supported**, metric `Range 0-10000: counting 0.21 s, built-in 0.82 s. Range 0-1M: counting 1.8 s, built-in 0.88 s.`
- `h79` [[h79_a_bucket_sort_beats_the_built_in_sort_on|A bucket sort beats the built-in sort on evenly spread numbers]] — *running*
<!-- crux:ledger:end -->
