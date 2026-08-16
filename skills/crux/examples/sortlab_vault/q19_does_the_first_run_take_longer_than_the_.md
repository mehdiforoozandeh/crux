---
id: q19
type: question
schema: 2
title: Does the first run take longer than the rest?
parent: q4
status: review
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q19 — Does the first run take longer than the rest?

Parent:: [[q4_is_my_stopwatch_telling_me_the_truth]]

## ELI5

Is the first run slower than the rest?

## TL;DR

When I run a sort for the first time, the laptop might need to load code and set things up. The first run could be much slower than the second. I ran each sort twice and compared the times.

Background:: [[wiki/warm-up-effects]], [[wiki/interpreter-overhead]]

## Question

Running a sort might trigger warm-up effects. The first run loads code into memory, or the interpreter gets faster at running Python. The answer tells me if I should always throw out the first run.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On my laptop, the first run of insertion sort on 10,000 items took 5.8 milliseconds. The second run took 5.2 milliseconds. The difference is real but not huge. I now skip the first run as a warm-up on every test.

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 1, partial 0, refuted 0, inconclusive 2, invalid-run 0)

- `h56` [[h56_the_first_run_of_a_sort_is_slower_than_t|The first run of a sort is slower than the next nine]] — *done* — verdict **supported**, metric `Bubble run 1 vs median runs 2-10: 8.3 ms vs 7.9 ms. Insertion 1 vs 2-10: 4.1 ms vs 3.8 ms.`
- `h57` [[h57_the_warm_up_cost_disappears_after_three_|The warm-up cost disappears after three runs]] — *done* — verdict **inconclusive**, metric `Bubble: run 1 = 8.4 ms, run 3 = 7.8 ms, runs 4-15 mean = 7.7 ms.`
- `h58` [[h58_warm_up_matters_more_for_small_lists_tha|Warm-up matters more for small lists than for big ones]] — *done* — verdict **inconclusive**, metric `Warm-up at 50 items is 12 percent; at 10000 items is 3 percent.`
<!-- crux:ledger:end -->
