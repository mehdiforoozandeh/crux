---
type: wiki
title: Wall-clock time
summary: Wall-clock time is the real elapsed time between when a program starts and when it finishes.
category: concept
sources: raw/docs-note-python-clocks.txt
---

# Wall-clock time

Wall-clock time is simple in concept: start a timer before running your program, stop it after, and measure the difference.

## Background

Wall-clock time is what most people think of when they ask 'how fast is this program'. You run it, and it finishes after some seconds or minutes. This elapsed time is wall-clock time. It is straightforward to measure: almost all computers have a clock you can read. The challenge is that wall-clock time includes everything happening on the computer. If the computer is busy with other tasks, your program waits. If the hard drive is swapping memory to disk, your program slows down. If the computer gets hot, it might throttle itself down. If the display needs updating, that time counts too. None of these are the fault of your program, but wall-clock time includes all of them. This is why careful benchmarking isolates the program: close other applications, use a quiet time window, run on a cool computer, and repeat many times. The first run of a program is often slower than later runs because the computer must load the program and prepare memory. Reporting just wall-clock time from one run is unreliable. Reporting the median time from many runs is better. Some people prefer [[measuring-program-speed]] by counting operations (like comparisons) instead of measuring wall-clock time, because operation counts do not depend on what else the computer is doing. But wall-clock time is ultimately what users care about.

## See also

Related:: [[measuring-program-speed]], [[timer-resolution]]
