---
id: q4
type: question
schema: 2
title: Is my stopwatch telling me the truth?
parent: root
status: open
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:40"
---

# q4 — Is my stopwatch telling me the truth?

Parent:: [[sortlab]]
RD:: [[rd/timing_harness_v2]] — Timing harness v2

## ELI5

Is my stopwatch giving me true answers?

## TL;DR

The clock I use has limits. It might not see times smaller than a certain amount. It might even jump backwards. If the sort is too fast, the clock cannot measure it right. I need to find out if my numbers are real.

Background:: [[wiki/measuring-program-speed]], [[wiki/timer-resolution]]

## Question

My timer might be lying. It might not have enough precision, or the system clock might jump. I need to know if my times are trustworthy before I compare sorts.

## Protocol

Use Python's time.perf_counter(). Check if it ever goes backwards. Run an empty loop and time it. Skip the first run as warm-up. Take thirty repeats and look at the spread.

## Answer so far

The counter clock does not go backwards on my laptop. An empty loop of ten thousand iterations takes about 0.07 milliseconds. So my timer can see times that small. But when I ran the first test, numbers varied wildly, so I started throwing out the first run.

<!-- crux:ledger:start -->
**7 children** · ideas 2/2 done (supported 1, partial 0, refuted 1, inconclusive 0, invalid-run 0) · sub-questions 1/5 resolved

- `h8` [[h8_my_first_timing_numbers_were_wrong_by_mo|My first timing numbers were wrong by more than ten percent]] — *done* — verdict **supported**, metric `Old timer: 15 ms median. New timer: 8 ms median. Difference: 7 ms (half the time was not measured.)`
- `h9` [[h9_a_single_run_is_enough_if_the_list_is_bi|A single run is enough if the list is big]] — *done* — verdict **refuted**, metric `Single runs at 100k: 12, 13, 16, 11 ms. Median of 30 runs: 12.8 ms.`
- `q18` _(Q)_ [[q18_how_small_a_gap_can_my_timer_see|How small a gap can my timer see?]] — *resolved*
- `q19` _(Q)_ [[q19_does_the_first_run_take_longer_than_the_|Does the first run take longer than the rest?]] — *review*
- `q20` _(Q)_ [[q20_do_background_apps_change_the_number|Do background apps change the number?]] — *open*
- `q21` _(Q)_ [[q21_does_running_on_battery_change_the_numbe|Does running on battery change the number?]] — *review*
- `q22` _(Q)_ [[q22_how_many_repeats_do_i_need_before_the_nu|How many repeats do I need before the number settles?]] — *open*
<!-- crux:ledger:end -->
