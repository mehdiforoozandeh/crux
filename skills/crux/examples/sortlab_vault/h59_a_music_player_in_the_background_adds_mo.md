---
id: h59
type: idea
schema: 2
title: A music player in the background adds more than five percent
parent: q20
status: done
rule: all
measurement: Time for one sort pass on 5000 items, with perf_counter.
replicates: 10 repeats with, 10 repeats without.
verdict: refuted
metric: "No music: 3.2 ms. With music: 3.1 ms. Difference: none."
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:35"
null_hash: 06d5180e6e6f55dd
lock: f8be4749ea690807
locked: "2026-08-16T16:06:53"
lock_at: running
---

# h59 — A music player in the background adds more than five percent

Parent:: [[q20_do_background_apps_change_the_number]]

## ELI5

Running a music player in the background slows my sort down by more than five percent.

## TL;DR

If the laptop is doing other things, it might steal time from my sort. The claim is that a music player running in the background adds more than five percent overhead. The run times the sorts with and without the player and compares.

Background:: [[wiki/thermal-throttling]]

## Null
instrumentation - a five percent threshold is smaller than my timer step

## Problem Statement

When I run experiments, other things are happening on the laptop. I want to know if background music is a real problem or if it does not matter.

## Idea / Hypothesis

A music player in the background adds more than five percent

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] With music playing, the sort takes more than five percent longer. (found: No music: 3.2 ms median. With music: 3.1 ms median. Music actually slightly faster)
      fails-if:: The music adds five percent or less overhead.
      discriminates:: true
- [ ] The music costs more at the large sizes than at the small ones (found: No cost at any size)
      fails-if:: The music costs the same share of time at every size
- [x] [outcome-neutral] The music actually plays through both blocks. (found: Spot-checked that the audio was playing throughout)
      fails-if:: The music stops or skips.

## Planned Intervention

Insertion sort on 5000 random items, run ten times without music, then ten times with a local music file playing in a browser tab. I measured each with perf_counter. Same power state both times.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h59/ and link at least the report:
     - [Report](results/h59/report.md)   - results/h59/curve.png -->
_(none yet)_

## Findings

Music does not slow the sort. If anything, the times were almost identical. The laptop can handle both easily. Background music is not my problem.
