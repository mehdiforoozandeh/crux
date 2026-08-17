---
type: wiki
title: Sorting in Python
summary: Python includes a built-in sorting function that is faster than most hand-written sorts.
category: overview
sources: raw/docs-note-python-list-sort.txt, raw/magazine-column-why-builtins-win.txt
---

# Sorting in Python

The Python language has a sort function already written and optimized by experts. It uses a sophisticated algorithm that adapts to the shape of your data.

## Background

Python is a programming language that includes many useful functions already built in. One of these is a sort function that arranges lists in order. This built-in sort is not just a simple algorithm—it is the result of decades of optimization by people who specialize in sorting. It uses a hybrid approach that chooses different strategies depending on how the data looks. If the data is already partially sorted, it notices this and works faster. If the data is random, it uses a method that handles random data well. Because the built-in sort is written in a compiled language (not pure Python), it runs much faster than a sort written in Python itself. This is why using [[interpreter-overhead]] is one of the reasons built-in functions often outpace hand-written code. A programmer writing a sort by hand in Python usually cannot match the speed of the built-in sort without deep expertise in optimization. The built-in sort is stable, meaning items that compare equal stay in their original order. Understanding how a built-in sort works and why it is faster teaches important lessons about software engineering.

## See also

Related:: [[interpreter-overhead]], [[sorting-algorithms-overview]]
