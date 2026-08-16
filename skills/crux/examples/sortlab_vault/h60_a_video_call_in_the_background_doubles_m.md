---
id: h60
type: idea
schema: 2
title: A video call in the background doubles my slowest runs
parent: q20
status: done
rule: all
measurement: Time for one sort pass on 10000 items, with perf_counter.
replicates: 10 repeats with call, 10 repeats without.
verdict: invalid-run
metric: Cannot compute; one of the four runs was void.
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:36"
null_hash: 49fd03dca7be6533
lock: 1a4199a97e00e990
locked: "2026-08-16T16:06:54"
lock_at: running
---

# h60 — A video call in the background doubles my slowest runs

Parent:: [[q20_do_background_apps_change_the_number]]

## ELI5

A video call running while I time a sort makes it much slower or breaks the timing completely.

## TL;DR

Video calls use a lot of CPU and network. If one runs during a timing run, it could stall the sort or cause so much jitter that the measurement is meaningless. The run tries to time sorts while a video call is happening and checks whether the measurements are still valid.

Background:: [[wiki/background-load]]

## Null
instrumentation - the video call is a coincidental stall that affects just one run

## Problem Statement

I often have video calls during the school day. If I am timing sorts and a call starts, the laptop might freeze or the measurements might become garbage.

## Idea / Hypothesis

A video call in the background doubles my slowest runs

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] With a video call, the median time is more than double the no-call median (found: Call median 2.3 times the no-call median)
      fails-if:: The call causes less than double the time
      discriminates:: true
- [ ] The slowest run with the call is more than double the slowest run without (found: Run void; nothing to compare)
      fails-if:: The slowest run with the call is under double the no-call slowest
- [ ] [outcome-neutral] The sorted output is a valid sorted list in all cases. (found: One run with the call had the sort abort mid-way. The run is invalid)
      fails-if:: The output is not sorted or not a permutation of the input.
- [x] [outcome-neutral] The video call stays open the whole time. (found: The call stayed open but one attempt stalled so badly that it crashed)
      fails-if:: The call drops or pauses.

## Planned Intervention

Insertion sort on 10000 items, timed with perf_counter. Ten runs with no call, ten runs with a video call (to a friend) happening in the background. The call was left open for the whole run.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h60/ and link at least the report:
     - [Report](results/h60/report.md)   - results/h60/curve.png -->
_(none yet)_

## Findings

The experiment broke. A video call on this laptop is too much. One run crashed partway through. The laptop got hot and the measurements are not trustworthy. I am not running any timing tests during a call again.
