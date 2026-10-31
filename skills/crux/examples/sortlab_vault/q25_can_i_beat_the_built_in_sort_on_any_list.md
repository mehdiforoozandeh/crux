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
**5 children** · open 1, leaning 2, settled 2, parked 0

- `h75` [[h75_counting_sort_beats_the_built_in_sort_on|Counting sort beats the built-in sort on small whole numbers]] — *leaning · moderate*
- `h76` [[h76_radix_sort_beats_the_built_in_sort_on_fi|Radix sort beats the built-in sort on fixed-width numbers]] — *leaning · weak*
- `h77` [[h77_nothing_i_write_beats_the_built_in_sort_|Nothing I write beats the built-in sort on plain random numbers]] — *settled · strong*
- `h78` [[h78_counting_sort_loses_once_the_number_rang|Counting sort loses once the number range gets wide]] — *settled · strong*
- `h79` [[h79_a_bucket_sort_beats_the_built_in_sort_on|A bucket sort beats the built-in sort on evenly spread numbers]] — *open*
<!-- crux:ledger:end -->
