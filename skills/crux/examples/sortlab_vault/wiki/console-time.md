---
type: wiki
title: The browser's console timer
summary: A browser timer for measuring how long JavaScript code takes to run in a page.
category: tool
sources: raw/docs-note-js-array-sort.txt
---

# The browser's console timer

The browser's console timer is built into JavaScript and measures wall time from a fixed point. It is precise enough for most web-based timing work.

## Background

Every modern browser provides a timer through the console object. You start it with console.time() and stop it with console.timeEnd(), which prints the elapsed time to the console. This timer measures in milliseconds and is based on the system's monotonic clock, which means it does not jump backwards. For a web developer, this is the standard tool for timing JavaScript code. It is simpler than writing your own timer, and the browser prints the result directly for you. The precision is usually good to within a few milliseconds on a school laptop. When you need more control, you can call performance.now() directly to get the raw timestamp and do the math yourself. This is useful when you want to time many runs without printing each one. The console timer is not as precise as a high-resolution counter used in low-level benchmarking, but it is more than enough for [[measuring-program-speed]] work at the JavaScript level.

## See also

Related:: [[measuring-program-speed]], [[repeated-trials]]
