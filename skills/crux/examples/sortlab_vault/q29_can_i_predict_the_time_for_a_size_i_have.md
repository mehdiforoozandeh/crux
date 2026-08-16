---
id: q29
type: question
schema: 2
title: Can I predict the time for a size I have not run?
parent: q7
status: open
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q29 — Can I predict the time for a size I have not run?

Parent:: [[q7_can_i_guess_the_time_before_i_run_the_te]]

## ELI5

Can I predict the time for a size I have not tested yet?

## TL;DR

I fitted a line to the small sizes. Now I can use the line to guess what the time will be at a much larger size, like 500,000. If the guess comes close to the real time, the prediction works.

Background:: [[wiki/extrapolation-risks]], [[wiki/doubling-experiments]]

## Question

Using the fitted curve, I can guess times for sizes outside my tested range. The answer is whether extrapolation works or if the sort changes its behavior at large sizes.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

I guessed that insertion on 200,000 items would take 20.5 milliseconds. The real time was 21.2 milliseconds. For 500,000, I guessed 128 milliseconds and got 132 milliseconds. Extrapolation works, but only a little bit past my data.

<!-- crux:ledger:start -->
**3 children** · ideas 2/3 done (supported 0, partial 0, refuted 1, inconclusive 1, invalid-run 0)

- `h90` [[h90_my_fitted_curve_predicts_a_new_size_to_w|My fitted curve predicts a new size to within twenty percent]] — *done* — verdict **refuted**, metric `Predicted 3.1 ms for 15k items, actual was 4.8 ms. Error was 55 percent.`
- `h91` [[h91_predicting_upward_is_worse_than_predicti|Predicting upward is worse than predicting between known sizes]] — *done* — verdict **inconclusive**, metric `Interpolation error at 4k was 7 percent. Extrapolation error at 20k was 48 percent.`
- `h92` [[h92_a_prediction_from_the_median_is_better_t|A prediction from the median is better than one from the mean]] — *running*
<!-- crux:ledger:end -->
