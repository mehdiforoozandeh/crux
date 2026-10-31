---
id: q18
type: question
schema: 2
title: How small a gap can my timer see?
parent: q4
status: resolved
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:07:13"
---

# q18 — How small a gap can my timer see?

Parent:: [[q4_is_my_stopwatch_telling_me_the_truth]]

## ELI5

What is the smallest time my stopwatch can measure?

## TL;DR

The timer has a resolution, the smallest tick it can see. Times smaller than that are noise. I ran an empty loop and a very fast sort to find the limit. The answer is the threshold below which I cannot trust the number.

Background:: [[wiki/timer-resolution]], [[wiki/monotonic-clocks]]

## Question

If a sort takes less than a microsecond, my timer might not see it. I need to know the minimum time I can trust. The answer is the resolution of the counter clock.

## Protocol

Run an empty loop ten million times and time it. Do this thirty times. Look at the range of times and the median. That is the noise floor.

## Answer so far

Running an empty loop of ten million iterations takes about 0.07 milliseconds. The times vary from 0.06 to 0.09 milliseconds. So I can trust times bigger than about 0.15 milliseconds. Below that, the result is just noise.

<!-- crux:ledger:start -->
**4 children** · open 0, leaning 1, settled 3, parked 0 · 1 finding(s) on this question

- `h53` [[h53_my_timer_cannot_see_a_gap_smaller_than_a|My timer cannot see a gap smaller than a millisecond]] — *leaning · moderate*
- `h54` [[h54_timing_a_list_of_one_hundred_items_is_be|Timing a list of one hundred items is below my timer's floor]] — *settled · strong*
- `h55` [[h55_timing_one_thousand_repeats_gets_me_unde|Timing one thousand repeats gets me under the floor]] — *settled · strong*
- `q31` _(Q)_ [[q31_does_it_matter_which_clock_function_i_ca|Does it matter which clock function I call?]] — *settled · strong*
- `f92` finding (strong) [[f92_what_the_timer_study_settled|What the timer study settled]]
<!-- crux:ledger:end -->
