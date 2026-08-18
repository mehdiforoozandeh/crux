---
type: wiki
title: Timer resolution
summary: Timer resolution is the smallest time interval a computer's clock can measure, limiting measurement precision.
category: concept
sources: raw/docs-note-python-clocks.txt, raw/club-talk-timing-basics.txt
---

# Timer resolution

A timer cannot measure time more finely than its resolution. If resolution is 10 milliseconds, you cannot measure anything faster.

## Background

Every computer has a timer built in, usually part of the processor or operating system. But this timer does not measure time smoothly. It advances in steps. If the resolution is 1 millisecond, the timer value jumps by 1 millisecond between readings. If resolution is 10 milliseconds, it jumps by 10 milliseconds. This matters when measuring fast operations. If you are measuring code that runs in 5 milliseconds and your timer has 10-millisecond resolution, the timer might report 0, 10, 20, or 30 milliseconds randomly, depending on when you measure relative to when the timer ticks. The measurement is too coarse to be trustworthy. Modern computers have much finer resolution than old ones. A modern computer might have nanosecond resolution (one billionth of a second). But some timers have worse resolution than others. Operating systems have multiple clocks with different resolutions and different properties. Some clocks can run backwards (if the system clock is adjusted). Others are monotonic (they never run backwards). This is why [[monotonic-clocks]] are preferred for timing: they ensure measurements are always positive and never jump backwards. To get accurate measurements of fast operations, use the finest-resolution timer available, and run the operation many times, summing the total time.

## See also

Related:: [[measuring-program-speed]], [[monotonic-clocks]]
