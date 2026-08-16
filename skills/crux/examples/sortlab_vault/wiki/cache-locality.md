---
type: wiki
title: Cache locality
summary: The CPU is much faster at reading data that is close together in memory than data scattered all over the place.
category: concept
sources: raw/magazine-column-laptops-throttle.txt
---

# Cache locality

Modern CPUs cache data from memory locally. Code that uses nearby data runs faster.

## Background

A CPU processes data very fast, but reading from the laptop's main memory is slow by comparison. To bridge this gap, CPUs have caches: small, fast memory that sits between the processor and main memory. The cache guesses what data you will need next and loads it early. If your code reads data that is close together in memory, the cache can hold it all and feed it to the CPU fast. If your code jumps all over memory, the cache misses and has to fetch from slow main memory. This makes a huge difference in speed. A piece of code might run twice as fast just because the data is organized differently, even though the algorithm is the same. This is why memory layout matters for [[measuring-program-speed]]. When you test different algorithms, you might be measuring cache effects as much as algorithm speed. Sorting is particularly sensitive to cache effects because it reads and writes the same array over and over. Data that is already in the cache stays fast; data that is not gets slowed down.

## See also

Related:: [[benchmarking-practice-overview]], [[memory-allocation]]
