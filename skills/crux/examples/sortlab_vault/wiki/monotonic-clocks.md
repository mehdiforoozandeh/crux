---
type: wiki
title: Monotonic clocks
summary: A monotonic clock never runs backwards and measures elapsed time reliably, unlike system clocks that can jump.
category: concept
sources: raw/docs-note-python-clocks.txt
---

# Monotonic clocks

Monotonic clocks are designed for timing: they advance steadily and never jump backwards, making them perfect for measuring elapsed time.

## Background

Computers have multiple clocks. The system clock (also called wall-clock time) shows the current time of day. It can be adjusted by the operating system or by time-sync software. If you measure a program using the system clock and the system clock is adjusted during your measurement, the elapsed time is wrong. A monotonic clock is different. It measures elapsed time since an arbitrary starting point (like when the computer booted). It is never adjusted. It always advances. This makes it perfect for measuring how long a program takes. If you measure from when the clock says 1000 microseconds to when it says 2000 microseconds, the elapsed time was exactly 1000 microseconds, regardless of what happens to the system clock. Programming languages and operating systems provide monotonic clocks for this reason. Python has `time.perf_counter()` (performance counter). JavaScript has `performance.now()`. C has `clock_gettime()` with the `CLOCK_MONOTONIC` option. Using a monotonic clock instead of the system clock eliminates a source of measurement error. Combined with running many trials and measuring with high-resolution timers, monotonic clocks enable reliable benchmarking. [[measuring-program-speed]] requires attention to these details, which is why benchmarking is harder than it seems.

## See also

Related:: [[measuring-program-speed]], [[perf-counter]]
