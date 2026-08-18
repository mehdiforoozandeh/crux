---
id: q31
type: question
schema: 2
title: Does it matter which clock function I call?
parent: q18
status: resolved
stale: true
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:07:13"
synthesis: s3
---

# q31 — Does it matter which clock function I call?

Parent:: [[q18_how_small_a_gap_can_my_timer_see]]

## ELI5

Does it matter which clock function I use?

## TL;DR

Python has several timer functions: time.time(), time.perf_counter(), and time.process_time(). They measure different things. The one I use changes the numbers I get.

Background:: [[wiki/monotonic-clocks]], [[wiki/perf-counter]]

## Question

Different clocks can measure wall time, process time, or performance time. Some can go backwards, others cannot. The answer is which one is most trustworthy for timing sorts.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

I tested all three clocks on a 10,000-item sort. time.time() varied a lot because other processes use the processor. time.perf_counter() was steady. time.process_time() only counts time this program uses, not sleep time. I switched to perf_counter().

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 1, partial 0, refuted 0, inconclusive 2, invalid-run 0)

- `h97` [[h97_the_clock_i_started_with_jumps_backwards|The clock I started with jumps backwards sometimes]] — *done* — verdict **inconclusive**, metric `Wall clock went backward 5 times in 100 reads. Counter clock went backward 0 times.`
- `h98` [[h98_the_counter_clock_has_a_finer_step_than_|The counter clock has a finer step than the wall clock]] — *done* — verdict **supported**, metric `Counter clock step was 0.001 ms. Wall clock step was 0.050 ms. Counter was 50 times finer.`
- `h99` [[h99_swapping_clocks_changed_my_early_numbers|Swapping clocks changed my early numbers by more than a percent]] — *done* — verdict **inconclusive**, metric `Wall clock: 42.3 ms. Counter clock: 41.8 ms. Difference: 1.2 percent.`
<!-- crux:ledger:end -->
