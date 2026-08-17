---
id: q3
type: question
schema: 2
title: How does the time grow when the list gets longer?
parent: root
status: open
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:20"
---

# q3 — How does the time grow when the list gets longer?

Parent:: [[sortlab]]

## ELI5

When the list gets bigger, how much slower does the sort get?

## TL;DR

I test each sort on lists that double in size, from a thousand up to a million items. A slow sort like bubble might take a thousand times longer. A fast sort like merge might take only fifty times longer. The pattern tells me how the sort scales.

Background:: [[wiki/big-o-notation]], [[wiki/growth-rate-curves]]

## Question

Doubling the list size probably makes the sort take longer. But does it take twice as long, or four times as long, or much worse? The answer is the pattern: how much slower for each doubling.

## Protocol

Test on 1,000; 2,000; 4,000; 8,000; 16,000; 32,000; 64,000; 128,000; 256,000; 512,000; 1,000,000 items. Thirty repeats each. Use median time. Random shape only.

## Answer so far

Bubble sort on 10,000 items takes about 23 milliseconds. On 20,000 it takes about 92 milliseconds. That is roughly four times longer. Merge on the same sizes: about 2.1 and 4.6 milliseconds. Merge doubles, bubble quadruples.

<!-- crux:ledger:start -->
**5 children** · ideas 1/2 done (supported 0, partial 0, refuted 1, inconclusive 0, invalid-run 0) · sub-questions 0/3 resolved

- `h6` [[h6_every_sort_i_wrote_gets_slower_in_the_sa|Every sort I wrote gets slower in the same way]] — *done* — verdict **refuted**, metric `Bubble 1 ms at 1k, 98 ms at 100k; merge 1 ms at 1k, 14 ms at 100k`
- `h7` [[h7_doubling_the_list_never_more_than_quadru|Doubling the list never more than quadruples the time]] — *idea*
- `q15` _(Q)_ [[q15_if_i_double_the_list_does_the_time_doubl|If I double the list, does the time double?]] — *open*
- `q16` _(Q)_ [[q16_where_does_merge_sort_overtake_insertion|Where does merge sort overtake insertion sort?]] — *open*
- `q17` _(Q)_ [[q17_does_the_laptop_s_memory_show_up_in_the_|Does the laptop's memory show up in the numbers?]] — *open*
<!-- crux:ledger:end -->
