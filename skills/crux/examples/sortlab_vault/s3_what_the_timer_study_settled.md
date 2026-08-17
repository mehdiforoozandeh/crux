---
id: s3
type: synthesis
title: What the timer study settled
approved: "2026-08-16T16:07:12"
created: "2026-08-16T16:07:12"
updated: "2026-08-16T16:07:12"
---

# Synthesis — What the timer study settled

Related:: [[q18_how_small_a_gap_can_my_timer_see]], [[q31_does_it_matter_which_clock_function_i_ca]]

## Headline conclusions

My first timer could not see gaps smaller than about 5 milliseconds. When timing only 100 items, the time was too small to measure. I had to switch to the counter clock, which is finer. Repeating the early measurements with the new clock changed some numbers by 2 to 4 percent.

## Cross-run table

| hypothesis | what I measured | verdict |
|---|---|---|
| My timer cannot see a gap smaller than a millisecond | Gaps below 5 ms were invisible | refuted |
| Timing a list of one hundred items is below my timer's floor | 100-item runs gave zero every time | supported |
| Timing one thousand repeats gets me under the floor | 1000 repeats were measurable | supported |
| The clock I started with jumps backwards sometimes | Saw it happen once, hard to repeat | inconclusive |
| The counter clock has a finer step than the wall clock | Counter had 10x better resolution | supported |
| Swapping clocks changed my early numbers by more than a percent | Median change was 3 percent | inconclusive |

## Implications for next batch

I have to discard all my week-1 numbers and re-measure everything with [[wiki/perf-counter]]. I also need to time at least 1000 items or use repeated runs to get numbers above the floor.
