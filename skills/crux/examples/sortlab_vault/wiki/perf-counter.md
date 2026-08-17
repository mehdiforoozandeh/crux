---
type: wiki
title: The performance counter
summary: A clock that counts time in nanoseconds and keeps steady without jumping backwards.
category: tool
sources: raw/docs-note-python-clocks.txt
---

# The performance counter

The performance counter is a system timer designed for measurement, not for wall-clock time. It runs continuously and monotonically, making it reliable for timing short code runs.

## Background

When you time a program, you need a clock that does not skip or jump backwards. The performance counter is built for exactly this job. It measures elapsed time from some arbitrary starting point, counting up in increments called ticks. The size of these ticks depends on your hardware, but they are often nanoseconds or microseconds. Unlike a wall-clock timer that corrects itself when the system date changes, the performance counter just keeps advancing. This makes it ideal for [[measuring-program-speed]]. Some languages call it different names: Python calls it perf_counter, JavaScript calls it performance.now, but they all work the same way. The key difference from other timers is that this one will never jump backwards if someone adjusts the system clock or if the network synchronizes time, and it ignores daylight saving time. This is why benchmarking tools prefer it over wall-clock time.

## See also

Related:: [[measuring-program-speed]], [[console-time]]
