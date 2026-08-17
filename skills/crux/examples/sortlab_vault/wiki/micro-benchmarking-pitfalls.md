---
type: wiki
title: Micro-benchmark pitfalls
summary: Six traps that catch people when they try to time code and six ways to avoid each one.
category: concept
sources: raw/club-talk-benchmark-mistakes.txt, raw/teacher-note-fair-comparisons.txt
---

# Micro-benchmark pitfalls

Measuring fast code is harder than writing it. Six mistakes are nearly universal, but each one is fixable.

## Background

Micro-benchmarking is the craft of timing small, fast pieces of code. It is hard because the hardware is full of invisible features designed to make typical programs faster, and these features interfere with measurement in unexpected ways. The first pitfall is trusting a single run. The fix is [[repeated-trials]]. The second pitfall is the timer itself being too slow or jumping backwards. The fix is using the right timer for the job. The third pitfall is not letting the code warm up, which matters for languages that compile code as it runs. The fourth pitfall is background tasks interfering, which is why you should close other applications and measure in isolation. The fifth pitfall is the compiler or runtime optimizing the code in a way that does not reflect real usage, like deleting code that does nothing. The sixth pitfall is extrapolating far beyond your data, like measuring up to 10,000 items and guessing what would happen at 10 million. Each trap has a standard defense, but they all require thinking before you start. Rushing into a benchmark without a plan guarantees mistakes.

## See also

Related:: [[measuring-program-speed]]
