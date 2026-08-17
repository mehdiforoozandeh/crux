---
type: wiki
title: Python next to compiled code
summary: Python code often runs fifty to one hundred times slower than equivalent C code because Python is interpreted.
category: comparison
sources: raw/magazine-column-why-builtins-win.txt
---

# Python next to compiled code

Compiled code executes directly. Interpreted code has a middleman that slows it down.

## Background

A simple loop in C runs in nanoseconds per iteration. The same loop in Python runs in microseconds because each iteration goes through the Python interpreter. This adds up fast. The ratio varies, but fifty to a hundred times slower is common for tight loops. For complex operations like sorting, where the algorithm does a lot of work, the ratio is often smaller because the algorithm work dominates. Python's built-in sort, for instance, is written in C and runs nearly as fast as C sort because the interpretation overhead is only at the call boundary, not inside the sorting loop. This is why many languages use compiled code for performance-critical libraries and only interpret the glue code. When you compare algorithms across languages, you must remember that you are measuring both the algorithm and the [[interpreter-overhead]] cost of the language. A Python sort and a C sort might have the same algorithm but very different times because of the language difference.

## See also

Related:: [[python-sorting-overview]]
