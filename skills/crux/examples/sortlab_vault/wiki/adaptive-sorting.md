---
type: wiki
title: Adaptive sorting
summary: An adaptive algorithm changes its behavior based on the structure of the input, like whether data is already partially sorted.
category: concept
sources: raw/handout-ch10-stability-and-space.txt, raw/docs-note-python-list-sort.txt
---

# Adaptive sorting

Some algorithms naturally speed up when input is already partially sorted. These are called adaptive algorithms.

## Background

Most sorting algorithms perform about the same on random data and on partially sorted data. But some algorithms adapt to the structure they find. Insertion sort is adaptive: if data is nearly sorted, each item is close to where it belongs, and insertion sort finishes quickly. On random data, insertion sort is slow. Bubble sort with early-exit is adaptive: if the data is sorted, it finishes after one pass instead of many. The built-in sort in Python, [[timsort]], is adaptive: it detects runs of sorted data and uses them to speed up the merge process. Adaptive algorithms are useful when you encounter partially sorted data in practice. Real-world data often has structure: timestamps in nearly chronological order, names in mostly alphabetical order, web logs from similar sessions grouped together. Adaptive algorithms exploit this structure. Analyzing adaptive algorithms is harder because the time depends on the input structure, not just the size. You cannot describe adaptive algorithm performance with a single Big-O. Instead, you describe it in terms of the number of runs or the amount of disorder. This is why understanding the data is important: the same algorithm might be fast or slow depending on what you feed it.

## See also

Related:: [[algorithm-analysis-overview]], [[run-detection]]
