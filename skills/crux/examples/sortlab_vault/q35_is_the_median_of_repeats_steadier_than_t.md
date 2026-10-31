---
id: q35
type: question
schema: 2
title: Is the median of repeats steadier than the mean?
parent: q22
status: review
stale: true
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:06:22"
---

# q35 — Is the median of repeats steadier than the mean?

Parent:: [[q22_how_many_repeats_do_i_need_before_the_nu]]

## ELI5

Does taking the middle value of several runs give steadier answers than using the average.

## TL;DR

When I run the same sort ten times, do the middle values from those ten runs change less than the averages would? If the median is steadier, I should use it for all my timing numbers going forward.

Background:: [[wiki/median-vs-mean]], [[wiki/outlier-trimming]]

## Question

I noticed my numbers jitter around. Some runs are faster and some slower, even with the same list. I need to know whether to report the average or the middle value. The median should filter out extreme results better, but I should test this.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

I ran the three slow sorts repeatedly and looked at both the average and the middle value. The median did turn out to be less jumpy than the mean. When one run was much slower—maybe I looked at the screen wrong, or the laptop did something else—the mean got dragged up, but the median barely moved. I'm now confident the median is my better tool.

<!-- crux:ledger:start -->
**2 children** · open 1, leaning 0, settled 1, parked 0

- `h107` [[h107_the_median_of_thirty_repeats_moves_less_|The median of thirty repeats moves less than the mean]] — *settled · strong*
- `h108` [[h108_throwing_away_the_slowest_three_runs_is_|Throwing away the slowest three runs is as good as the median]] — *open*
<!-- crux:ledger:end -->
