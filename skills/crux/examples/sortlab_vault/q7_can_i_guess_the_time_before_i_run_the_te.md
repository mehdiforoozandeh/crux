---
id: q7
type: question
schema: 2
title: Can I guess the time before I run the test?
parent: root
status: open
stale: false
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:20"
---

# q7 — Can I guess the time before I run the test?

Parent:: [[sortlab]]

## ELI5

Can I guess the time before I run the test?

## TL;DR

I have timed my sorts on many different sizes. I can fit a curve to the data and guess what the time will be for a size I have not tested yet. The guess might be close or might be way off. I want to know if the guess works.

Background:: [[wiki/curve-fitting-basics]]

## Question

I can plot the times on a log-log chart and fit a line. Then I can use that line to guess the time for a new size. Does the guess come true, or is it just a fantasy based on small data?

## Protocol

Fit a line to sizes 1,000 to 100,000. Then guess times for 200,000 and 500,000. Run those sizes and see if the guess is close. Close means within twenty percent.

## Answer so far

I fitted a line to the small sizes and guessed 15.3 milliseconds for merge sort on 200,000 items. The real time was 14.8 milliseconds. For 500,000, I guessed 37 milliseconds and got 38.2 milliseconds. Guessing between sizes works pretty well.

<!-- crux:ledger:start -->
**5 children** · ideas 0/2 done (supported 0, partial 0, refuted 0, inconclusive 0, invalid-run 0) · sub-questions 0/3 resolved

- `h15` [[h15_i_can_guess_a_run_time_to_within_twenty_|I can guess a run time to within twenty percent]] — *idea*
- `h16` [[h16_a_guess_from_three_sizes_is_as_good_as_a|A guess from three sizes is as good as a guess from six]] — *running*
- `q28` _(Q)_ [[q28_can_i_fit_a_curve_to_the_small_sizes|Can I fit a curve to the small sizes?]] — *open*
- `q29` _(Q)_ [[q29_can_i_predict_the_time_for_a_size_i_have|Can I predict the time for a size I have not run?]] — *open*
- `q30` _(Q)_ [[q30_can_i_predict_the_time_for_a_shape_i_hav|Can I predict the time for a shape I have not run?]] — *open*
<!-- crux:ledger:end -->
