---
id: q28
type: question
schema: 2
title: Can I fit a curve to the small sizes?
parent: q7
status: open
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q28 — Can I fit a curve to the small sizes?

Parent:: [[q7_can_i_guess_the_time_before_i_run_the_te]]

## ELI5

Can I fit a curve to my small-size data?

## TL;DR

I have times for insertion sort from 1,000 to 100,000 items. I can fit a line on a log-log chart and see if it makes sense. A good fit means I can predict times for new sizes.

Background:: [[wiki/curve-fitting-basics]], [[wiki/growth-rate-curves]]

## Question

Fitting a curve tells me the growth rate of the sort. If the data is noisy, the fit might be useless. The answer is whether a line makes sense for my data.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

I plotted insertion on a log-log chart from 1,000 to 100,000 items. The points line up very well, almost perfectly linear. The slope is about 2, which matches the theory that insertion is O(n squared).

<!-- crux:ledger:start -->
**4 children** · ideas 3/4 done (supported 1, partial 0, refuted 1, inconclusive 1, invalid-run 0)

- `h86` [[h86_a_straight_line_fits_my_insertion_sort_t|A straight line fits my insertion sort times on a log-log chart]] — *done* — verdict **supported**, metric `Times were 0.12 ms at 1k, 0.49 at 3k, 1.93 at 10k; log-log line fit with slope 1.98.`
- `h87` [[h87_the_slope_of_that_line_is_close_to_two|The slope of that line is close to two]] — *done* — verdict **inconclusive**, metric `Fitted slope was 1.98 with 95 percent confidence interval 1.84 to 2.12.`
- `h88` [[h88_the_slope_for_merge_sort_is_close_to_one|The slope for merge sort is close to one]] — *done* — verdict **refuted**, metric `Merge sort slope was 1.12; times were 0.24 ms at 1k, 2.18 at 10k.`
- `h89` [[h89_three_sizes_give_the_same_slope_as_six_s|Three sizes give the same slope as six sizes]] — *staged*
<!-- crux:ledger:end -->
