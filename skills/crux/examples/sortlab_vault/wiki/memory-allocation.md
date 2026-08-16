---
type: wiki
title: Memory allocation
summary: Requesting new memory from the operating system is slow and unpredictable, adding hidden cost to code.
category: concept
sources: raw/handout-ch10-stability-and-space.txt
---

# Memory allocation

Creating arrays and objects requires memory allocation. Some allocations are fast, some are slow.

## Background

When code says I need an array or an object, the language asks the operating system for some memory. The OS has to find a free block of memory big enough, mark it as in use, and hand it back. This takes time. If the OS can grab a nearby block quickly, allocation is fast. If the OS has to search for free memory or reorganize things, allocation is slow. Inside your timing measurement, this cost adds up. Some algorithms allocate memory once at the start and reuse it. Others allocate memory repeatedly as they go. The algorithm that reuses memory will look faster because it saves allocation cost. But the allocation cost is real, so it is part of the true cost of the algorithm. When you time code, memory allocation is part of what you measure. If two implementations allocate memory differently, the timings will reflect that difference. This is why researchers sometimes pre-allocate all the memory they need before starting the timer, so they measure only the algorithm itself and not the allocation overhead.

## See also

Related:: [[benchmarking-practice-overview]], [[recursion-depth]]
