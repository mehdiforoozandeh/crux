---
type: rd
node: q4
title: Timing harness v1
status: superseded
supersedes: 
created: "2026-08-16T16:06:40"
updated: "2026-08-16T16:06:40"
---

# Timing harness v1

RD for [[q4_is_my_stopwatch_telling_me_the_truth]] — `q4`

## Context

I needed to measure how fast each sort actually runs on my school laptop. I started with the simplest approach: just record the time before and after, and print the difference. No repetition, no warm-up, no attempts to handle the laptop's jitter.

Background:: [[wiki/wall-clock-time]], [[wiki/timer-resolution]]

## Out of scope

This version does not handle the timer's resolution limits, does not discard warm-up runs, and does not repeat to filter noise.

## Design

I wrote a Python script that imports the time module and calls time.time() before the sort and after. The difference is the elapsed time in seconds. I multiply by 1000 to show milliseconds. The script reads one list from a file, sorts it once, and prints the result. The same script works for all five sorts—I just change which sort function I call.

## Considered options

I thought about running the sort a hundred times and dividing by 100, but I wanted to keep things simple first. I also considered writing to a file instead of printing, but printing was easier to debug. I chose the wall clock over a counter clock because it was the first option in the documentation.

## Consequences and known distortions

This harness fails on small lists because [[wiki/wall-clock-time]] has a coarse step—it cannot see gaps smaller than 5 milliseconds. It also counts the first run, which is usually slower due to warm-up. Every number from this harness needs to be re-measured later with a better tool.

## Supersedes

_(forward-only. An active RD is never amended in place: a design change writes a NEW RD with
  `crux rd <node> "<title>" --supersedes <slug>`, and the chain is the reasoning history.
  The reverse link is generated into RD.md — never write `superseded by` into an old RD.)_
