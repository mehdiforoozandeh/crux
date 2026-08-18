---
id: q22
type: question
schema: 2
title: How many repeats do I need before the number settles?
parent: q4
status: open
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q22 — How many repeats do I need before the number settles?

Parent:: [[q4_is_my_stopwatch_telling_me_the_truth]]

## ELI5

How many times do I need to run the test before the numbers settle?

## TL;DR

Each run of a sort gives a slightly different time because of noise and variation. If I run the sort only twice, the median might be luck. If I run it thirty times, the median is more stable. I want to know how many is enough.

Background:: [[wiki/repeated-trials]], [[wiki/outlier-trimming]]

## Question

More runs mean a more stable answer, but testing takes time. At some point, running more does not help. The answer is the minimum number of runs where the results stop changing much.

## Protocol

Run insertion on 10,000 items one, two, five, ten, and thirty times. Compare the median each time. If thirty is not much different from ten, then ten is enough.

## Answer so far

With one run, the time was 5.4 milliseconds, which could be an outlier. With two runs, the median was 5.2 milliseconds. With ten runs, it was 5.1 milliseconds. With thirty runs, it was still 5.1 milliseconds. Ten looks like enough.

<!-- crux:ledger:start -->
**5 children** · ideas 4/4 done (supported 0, partial 0, refuted 2, inconclusive 2, invalid-run 0) · sub-questions 0/1 resolved

- `h65` [[h65_ten_repeats_are_enough_for_the_numbers_t|Ten repeats are enough for the numbers to settle]] — *done* — verdict **refuted**, metric `Bubble 10-run median: 5.2 ms. 30-run median: 5.1 ms. Insertion: 3.1 vs 3.0 ms.`
- `h66` [[h66_thirty_repeats_bring_the_spread_under_fi|Thirty repeats bring the spread under five percent]] — *done* — verdict **inconclusive**, metric `Bubble IQR: 4.7 percent of median. Insertion: 4.2 percent.`
- `h67` [[h67_the_slowest_run_in_thirty_is_always_an_o|The slowest run in thirty is always an outlier]] — *done* — verdict **refuted**, metric `Max 3.4 ms is 3.75 standard deviations above mean of 3.1 ms.`
- `h68` [[h68_repeats_help_more_than_making_the_list_b|Repeats help more than making the list bigger]] — *done* — verdict **inconclusive**, metric `1000 items 30x IQR: 5 percent of median. 10000 items 3x IQR: 6 percent of median.`
- `q35` _(Q)_ [[q35_is_the_median_of_repeats_steadier_than_t|Is the median of repeats steadier than the mean?]] — *review*
<!-- crux:ledger:end -->
