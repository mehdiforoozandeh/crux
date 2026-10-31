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
**3 children** · open 0, leaning 2, settled 1, parked 0 · 1 finding(s) on this question

- `h97` [[h97_the_clock_i_started_with_jumps_backwards|The clock I started with jumps backwards sometimes]] — *leaning · moderate*
- `h98` [[h98_the_counter_clock_has_a_finer_step_than_|The counter clock has a finer step than the wall clock]] — *settled · strong*
- `h99` [[h99_swapping_clocks_changed_my_early_numbers|Swapping clocks changed my early numbers by more than a percent]] — *leaning · moderate*
- `f93` finding (strong) [[f93_what_the_timer_study_settled|What the timer study settled]]
<!-- crux:ledger:end -->
