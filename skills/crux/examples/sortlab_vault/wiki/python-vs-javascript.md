---
type: wiki
title: Python next to JavaScript
summary: Python is slower per operation but JavaScript engines compile aggressively, making pure JavaScript code sometimes comparable to Python.
category: comparison
sources: raw/docs-note-js-array-sort.txt, raw/magazine-column-why-builtins-win.txt
---

# Python next to JavaScript

Both are interpreted languages, but they handle speed differently. Python is slower for most code, but the gap is complex.

## Background

Python is purely interpreted and relies on built-in C code for fast operations. JavaScript engines use just-in-time compilation, turning hot code into machine code on the fly. This makes tight JavaScript loops surprisingly fast compared to Python. However, Python's built-in operations like sorting and array access are usually faster than JavaScript because Python is heavily optimized in C. When benchmarking the same algorithm in both languages, the results depend heavily on what the code does. A loop that does simple arithmetic might be faster in JavaScript because of JIT compilation. A sort or a large array operation might be faster in Python because it is built in C. Understanding [[interpreter-overhead]] and just-in-time compilation helps explain why direct speed comparisons across languages are misleading. The language you choose affects not just the algorithm but also the entire runtime environment that executes it.

## See also

Related:: [[javascript-sorting-overview]]
