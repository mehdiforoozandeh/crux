---
type: wiki
title: Interpreter overhead
summary: The cost of the language interpreter or runtime environment, which executes your code line by line or translates it on the fly.
category: concept
sources: raw/magazine-column-why-builtins-win.txt
---

# Interpreter overhead

Interpreted languages like Python have overhead compared to compiled languages. Every line of code must go through the interpreter.

## Background

When you write code in Python or JavaScript, the interpreter reads your code line by line and executes it. This interpretation process adds overhead. The interpreter has to decode each instruction, look up variables, manage memory, and call built-in functions. This all takes time that is not part of the algorithm itself. Compiled languages like C or C++ translate code to machine instructions once, before it runs. Then it just runs the raw machine instructions, with much less overhead. This is one reason compiled code is often faster than interpreted code. The overhead is fixed per operation, so small, tight loops in interpreted languages can be surprisingly slow compared to the same loops in compiled languages. When you benchmark a sorting algorithm in Python and then in C, some of the speed difference comes from better algorithms or better memory use in C, but some comes from the interpreter overhead. Understanding this difference is important when comparing across languages.

## See also

Related:: [[python-sorting-overview]], [[python-vs-c-speed]]
