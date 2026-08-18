---
type: wiki
title: Seeded randomness
summary: Using a fixed seed to make a random list the same every time you create it, so tests are repeatable.
category: method
sources: raw/teacher-note-fair-comparisons.txt
---

# Seeded randomness

Real randomness is different each run and makes it hard to compare results. A seeded random generator produces the same list every time.

## Background

If an input generator creates a random list using true randomness, the list is different each time. This makes it hard to compare two algorithms fairly, because they are not solving the same problem. Algorithm A got one random list, Algorithm B got a different random list, and they might perform differently just because of the data, not because of the algorithm. To fix this, input generators use a seed: a fixed starting number. If you give the random generator the same seed every time, it produces the same random-looking sequence. The sequence is predictable once you know the seed, but it still has the randomness properties needed for testing. Two algorithms can now solve the exact same random list, so any time difference is due to the algorithm, not the data. Seeds are usually small numbers like 42 or 12345. Reporting the seed with your results lets someone else regenerate the exact same test data you used. This is part of making [[measuring-program-speed]] results reproducible and comparable.

## See also

Related:: [[benchmarking-practice-overview]], [[input-generators]]
