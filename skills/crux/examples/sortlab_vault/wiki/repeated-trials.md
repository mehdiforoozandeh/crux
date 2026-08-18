---
type: wiki
title: Repeated trials
summary: Running the same code multiple times and collecting all the times to reduce random noise.
category: method
sources: raw/club-talk-benchmark-mistakes.txt
---

# Repeated trials

A single run can be fooled by random interruptions. Repeating a test many times lets you see the typical performance clearly.

## Background

When you run a program once, you get one time. But that one run might have been interrupted by a background process, or the network might have caused a pause, or the system might have done something you did not ask for. The answer you get is not reliable. If you run the test ten times, you get ten numbers. Some will be faster, some slower. The variation tells you how much the system is interfering. When you run it thirty times or fifty times, the outliers from random interruptions matter less and the true behavior of the code becomes clear. This is why benchmark researchers repeat tests. The more repeats, the less a single unlucky interruption can sway your conclusion. But there is a limit: too many repeats take too long, and the laptop hardware changes state over time, so very long test sessions can become unreliable too. Most researchers find that somewhere between five and thirty repeats is a good balance. After each repeat, the code may leave things changed in memory, which is why discarding the first run as a [[measuring-program-speed]] warm-up is a common practice.

## See also

Related:: [[measuring-program-speed]], [[median-vs-mean]]
