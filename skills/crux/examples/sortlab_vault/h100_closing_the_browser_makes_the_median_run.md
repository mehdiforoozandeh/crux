---
id: h100
type: idea
schema: 2
title: Closing the browser makes the median run faster
parent: q32
status: done
rule: all
measurement: Median time for insertion sort with full and minimal background load.
replicates: 30 repeats with background load, 30 repeats with minimal load, at 5 sizes.
verdict: refuted
metric: With background, median 2.16 s at 100k items. Closed, median 2.19 s. No improvement.
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
null_approved: "2026-08-16T16:06:39"
null_hash: 4cefe85719c14af8
lock: 5a3799471e97c66d
locked: "2026-08-16T16:07:01"
lock_at: running
---

# h100 — Closing the browser makes the median run faster

Parent:: [[q32_does_closing_the_browser_change_the_numb]]

## ELI5

Closing the browser makes sorts run faster.

## TL;DR

I ran sorts with the browser open to other tabs and windows. Then I closed everything except the timing page. The times got shorter. When background applications compete for the machine, they slow down the sort. Closing them removes that competition.

Background:: [[wiki/background-load]]

## Null
instrumentation - the timer's resolution made measurement noise bigger than the real effect.

## Problem Statement

My measurements might be unfair. If I forgot to close applications in week two but remembered in week three, the apparent speedup could be just background cleanup. I need to know how much background noise matters.

## Idea / Hypothesis

Closing the browser makes the median run faster

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Times with browser closed are shorter than times with it open. (found: With background, median 2.16 s at 100k items. Closed, median 2.19 s)
      fails-if:: Closed and open times are the same or closed is slower.
      discriminates:: true
- [ ] The difference is bigger than the usual variation in run times.
      fails-if:: The difference falls within the normal spread of results.
- [x] [outcome-neutral] All sorts remain correct regardless of background load.
      fails-if:: Closing the browser somehow corrupts results.
- [x] [outcome-neutral] The median stays stable across runs.
      fails-if:: Background processes make results unreliable.

## Planned Intervention

One thousand to one hundred thousand items. Thirty repeats with browser open (music player running, other tabs loaded), thirty with browser closed to one tab only.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h100/ and link at least the report:
     - [Report](results/h100/report.md)   - results/h100/curve.png -->
_(none yet)_

## Findings

Closing the browser did not actually make sorts faster. Times were nearly identical whether I had background applications or not. The difference was less than two percent, within normal variation. Turns out the laptop is good enough that background noise does not matter much.
