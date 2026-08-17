---
type: wiki
title: Measuring program speed
summary: Measuring how fast a program runs requires careful timing and multiple test runs.
category: overview
sources: raw/club-talk-timing-basics.txt, raw/teacher-note-fair-comparisons.txt
---

# Measuring program speed

Program speed is not obvious from reading code. It must be measured by running the program and recording the time it takes.

## Background

When you want to know how fast a program runs, you measure the time it starts and the time it finishes, then find the difference. This sounds simple, but it is harder than it seems. The computer's timer has limited precision—it may jump by small amounts or take large steps rather than measuring smoothly. Background tasks (like checking email or updating files) can slow down your program for unpredictable moments. The first run of a program often takes longer because the computer has to load it into memory. If you time only one run, random delays might make your answer wrong. That is why careful timing uses multiple test runs and reports the middle value, not just one result. Temperature matters too: if the computer gets hot, it may slow itself down to cool off. Fair measurement means running your program many times under controlled conditions and using statistics to summarize what you find. This is why [[wall-clock-time]] alone is not enough—understanding what the numbers mean requires knowing how they were measured.

## See also

Related:: [[wall-clock-time]], [[python-sorting-overview]]
