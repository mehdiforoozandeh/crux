---
type: wiki
title: Recursion depth
summary: Functions that call themselves use memory for each call, and calling very deeply can cause the program to crash.
category: concept
sources: raw/library-book-notes-recursion.txt
---

# Recursion depth

Every function call uses a small piece of memory called the stack. Deep recursion fills the stack and eventually breaks.

## Background

When a function calls itself recursively, each call needs to remember where it was and what values it had. The computer stores this information on the stack, a reserved area of memory. A shallow recursion, like ten levels deep, uses a small amount of stack. But deep recursion, like a thousand levels, uses a lot. There is a limit to how deep you can go before the stack runs out of memory and the program crashes with a stack overflow error. The limit depends on the operating system and the size of each call frame, but for school work it is usually a few thousand to a few million levels depending on what each function stores. This matters for sorting because some sorting algorithms are recursive. Quick sort, for example, calls itself until the list is fully sorted. If the list is very large and the algorithm keeps dividing it in a bad way, the recursion can get very deep. A poorly designed quick sort might crash on a large list. This is why some languages and libraries have special guards to prevent stack overflow in recursive code.

## See also

Related:: [[benchmarking-practice-overview]]
