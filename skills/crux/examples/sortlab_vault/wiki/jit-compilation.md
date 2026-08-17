---
type: wiki
title: Just-in-time compiling
summary: Translating code from a slower interpreted form to a faster machine-like form while the program runs, learning from patterns.
category: concept
sources: raw/docs-note-js-array-sort.txt
---

# Just-in-time compiling

Some languages compile code as it runs. The more it runs, the more optimized it becomes.

## Background

JavaScript engines and modern Python implementations use just-in-time compilation. When code is first executed, it runs in an interpreter. But when the same code runs many times, the engine recognizes this and compiles it to a faster form on the fly. The compiled version runs much faster. This is why [[repeated-trials]] is so important in JavaScript benchmarking: the first run is interpreted and slow, but runs two and three are compiled and fast. The difference can be ten times. The compilation process also watches how code actually runs and makes guesses about optimization. If a function is always called with a certain type of object, the engine might optimize for that type. If a loop always runs the same number of times, the engine might unroll it. These optimizations make sense for the common case but can fail if the code behaves differently later. Understanding just-in-time compilation is essential for benchmarking in JavaScript and newer Python versions, because the first run tells you nothing about real performance.

## See also

Related:: [[javascript-sorting-overview]], [[python-vs-javascript]]
