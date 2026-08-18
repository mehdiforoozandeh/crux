---
type: wiki
title: Warm-up effects
summary: The first run of code is often much slower than the second and third because the system is not ready yet.
category: concept
sources: raw/club-talk-timing-basics.txt
---

# Warm-up effects

Modern systems prepare code for speed as it runs. The first test does much of that preparation, making it unrepresentative.

## Background

When you write code and run it, the system does many things before the code actually executes. It loads the file, parses it, allocates memory, and in languages like Python or JavaScript, it may translate the code to a faster form. This setup work happens once. The second time you run the code, all that preparation is already done, and the code runs faster. This difference is called the warm-up effect. A good [[measuring-program-speed]] practice is to run the code at least once before you start timing, and throw away that first time. Then run it again for real. This is especially important in languages that use just-in-time compilation, which speeds up code as it learns how you use it. In statically compiled languages like C, warm-up matters less but still shows up when memory caches are cold. The rule is simple: run at least one test before you start counting. Some people run ten dummy loops before they turn on the timer. This ensures that [[repeated-trials]] are all measuring the warm, ready system, not a mix of a cold start and later runs.

## See also

Related:: [[benchmarking-practice-overview]], [[background-load]]
