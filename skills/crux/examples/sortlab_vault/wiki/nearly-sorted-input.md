---
type: wiki
title: Nearly-sorted input
summary: A test list where most items are in order but a few are out of place, like real data after one round of mixing.
category: dataset
sources: raw/docs-note-python-list-sort.txt
---

# Nearly-sorted input

Nearly sorted input is closer to real data than purely random or sorted input. Some algorithms have special speed for it.

## Background

Real data is rarely purely random. It often starts somewhat sorted and then gets shuffled a little. A list from a database query might be mostly sorted by a timestamp with a few recent additions out of place. A list of names might be mostly alphabetical with a few new entries. Nearly sorted input resembles this real scenario. Some algorithms, like insertion sort and Python's built-in sort, have special code to detect runs of already-sorted data and handle them fast. When you test these algorithms with nearly sorted input, they perform much better than they do with random input. This is not because the algorithm is bad at random input but because it is optimized for the common case where data has some natural structure. Testing with nearly sorted input shows these optimizations at work. A good [[measuring-program-speed]] suite includes this case to reflect real-world patterns.

## See also

Related:: [[benchmarking-practice-overview]], [[duplicate-heavy-input]]
