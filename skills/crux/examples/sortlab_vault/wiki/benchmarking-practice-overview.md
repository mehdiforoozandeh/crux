---
type: wiki
title: Benchmarking practice
summary: Benchmarking is the practice of timing and comparing programs under controlled, realistic conditions.
category: overview
sources: raw/club-talk-benchmark-mistakes.txt, raw/teacher-note-fair-comparisons.txt
---

# Benchmarking practice

A benchmark is a fair test that compares how fast different programs or algorithms run. Doing this fairly requires controlling many factors.

## Background

Benchmarking means writing code to measure and compare the speed of different algorithms or approaches. A good benchmark is fair: it gives each algorithm the same hardware, the same data, and the same conditions. But achieving fairness is tricky. The first run of any program takes longer because the computer must load it and prepare memory. Experienced benchmarkers discard the first run or two as warm-up, then measure the rest. Other factors matter too. If your computer is running other programs—a video call, a file download, a background scan—these can steal time from your benchmark. Thermal effects matter: if the computer gets hot, it slows itself down. The data you test with matters enormously. Random data behaves differently from data that is already sorted or nearly sorted. Some algorithms notice patterns in data and speed up. Others do not. A good benchmark tries different data shapes to see if an algorithm adapts. [[warm-up-effects]] are one reason that a single benchmark run tells you almost nothing. Dozens of identical runs, with results reported as a median or average, give a more trustworthy answer. Professional benchmarking is as much about experimental design as it is about timing.

## See also

Related:: [[warm-up-effects]], [[javascript-sorting-overview]]
