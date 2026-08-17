---
id: q20
type: question
schema: 2
title: Do background apps change the number?
parent: q4
status: open
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q20 — Do background apps change the number?

Parent:: [[q4_is_my_stopwatch_telling_me_the_truth]]

## ELI5

Do background apps make the sort slower?

## TL;DR

If a web browser is running in the background, the laptop has to split its attention. The sort might take longer because the processor is busy with something else. I tested with the browser closed and then open.

Background:: [[wiki/background-load]], [[wiki/thermal-throttling]]

## Question

My laptop is old and has limited processor power. When I have other things running, does the sort take longer? The answer tells me how much control I need to keep over the environment.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On 10,000 random items, insertion took 5.2 milliseconds with nothing else running and 6.8 milliseconds with the browser open on a video call. The call slowed it down, but not by a huge amount. I try to close big apps before testing now.

<!-- crux:ledger:start -->
**4 children** · ideas 3/3 done (supported 1, partial 0, refuted 1, inconclusive 0, invalid-run 1) · sub-questions 0/1 resolved

- `h59` [[h59_a_music_player_in_the_background_adds_mo|A music player in the background adds more than five percent]] — *done* — verdict **refuted**, metric `No music: 3.2 ms. With music: 3.1 ms. Difference: none.`
- `h60` [[h60_a_video_call_in_the_background_doubles_m|A video call in the background doubles my slowest runs]] — *done* — verdict **invalid-run**, metric `Cannot compute; one of the four runs was void.`
- `h61` [[h61_background_load_changes_the_median_less_|Background load changes the median less than the mean]] — *done* — verdict **supported**, metric `Mean without load: 3.1 ms. Mean with load: 3.4 ms. Median: both 3.0 ms.`
- `q32` _(Q)_ [[q32_does_closing_the_browser_change_the_numb|Does closing the browser change the number?]] — *open*
<!-- crux:ledger:end -->
