---
id: h53
type: idea
schema: 2
title: My timer cannot see a gap smaller than a millisecond
parent: q18
status: done
rule: all
measurement: Time reported by the counter, compared to known duration.
replicates: 10 repetitions of one second, then timing empty loops
verdict: refuted
metric: Timer step roughly 1.0 millisecond; one-second sleep 1.000-1.003 sec
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:35"
null_hash: 566634ca5d6be66d
lock: d933b842b88ac1c7
locked: "2026-08-16T16:06:52"
lock_at: running
---

# h53 — My timer cannot see a gap smaller than a millisecond

Parent:: [[q18_how_small_a_gap_can_my_timer_see]]

## ELI5

My timer cannot see a time gap smaller than a millisecond.

## TL;DR

The timer has a granularity of about one millisecond. Gaps smaller than this get reported as zero. This was the first big problem I discovered, and it made the early measurements unreliable.

Background:: [[wiki/monotonic-clocks]]

## Null
instrumentation - the timer step was exactly as large as I feared

## Problem Statement

In week two, I timed small sorts and got results that did not make sense. I discovered the timer's resolution was too coarse to measure fast code.

## Idea / Hypothesis

My timer cannot see a gap smaller than a millisecond

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] One-second sleep was reported as exactly one second or close to it. (found: Timer step roughly 1.0 millisecond; one-second sleep 1.000-1.003 sec)
      fails-if:: Sleep time varied wildly, suggesting clock issues.
      discriminates:: true
- [ ] Operations taking less than one millisecond reported as zero or nearly zero.
      fails-if:: Tiny operations had measurable times above one hundred microseconds.
- [x] [outcome-neutral] The timer did not jump backwards during a run. (found: Clock was monotonic, never went backwards)
      fails-if:: Time went backwards, indicating a broken clock.

## Planned Intervention

Time a known one-second sleep ten times with the original clock. Measure gaps below one millisecond by timing ten thousand operations.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h53/ and link at least the report:
     - [Report](results/h53/report.md)   - results/h53/curve.png -->
_(none yet)_

## Findings

The timer's resolution was about one millisecond. This meant gaps smaller than that got rounded away. The original clock was also not always monotonic. Switching to the counter clock fixed both problems.
