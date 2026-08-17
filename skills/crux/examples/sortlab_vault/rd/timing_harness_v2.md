---
type: rd
node: q4
title: Timing harness v2
status: active
supersedes: timing_harness_v1
created: 2026-08-16T16:06:40
updated: 2026-08-16T16:06:40
---

# Timing harness v2

RD for [[q4_is_my_stopwatch_telling_me_the_truth]] — `q4`

## Context

After the timer study, I learned that the wall clock was too coarse and the first run was always slow. I needed to fix both problems. The counter clock is finer, and discarding the first run removes the warm-up effect. I also added repetition to handle the laptop's jitter.

Background:: [[wiki/perf-counter]], [[wiki/repeated-trials]], [[wiki/median-vs-mean]]

## Out of scope

This version does not adjust for CPU throttling or background load. It assumes a quiet machine and does not record how hot the laptop is.

## Design

The new harness uses time.perf_counter() instead of time.time(). It runs the sort 30 times on the same list, discards the first run, and records the time for each of the other 29. It then calculates the [[wiki/median-vs-mean]] of those 29 times and prints that. The script also prints the minimum and maximum so I can spot outliers.

## Considered options

I tried 10 repeats but that was not enough to filter the noise. I also tried averaging instead of taking the median, but one slow run would drag the average up, making the result unreliable. The counter clock is slower to read but accurate enough. I considered 100 repeats but the sort would finish before I could start watching.

## Consequences and known distortions

This harness is slower to run because it repeats. The counter clock is more accurate but adds a small overhead. All my old numbers must be re-measured with this tool. Going forward, every timing number comes from this harness and reports the median of 29 runs.

## Supersedes

_(forward-only. An active RD is never amended in place: a design change writes a NEW RD with
  `crux rd <node> "<title>" --supersedes <slug>`, and the chain is the reasoning history.
  The reverse link is generated into RD.md — never write `superseded by` into an old RD.)_
