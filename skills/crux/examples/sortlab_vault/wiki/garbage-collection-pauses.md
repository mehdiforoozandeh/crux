---
type: wiki
title: Garbage-collection pauses
summary: Languages that automatically clean up memory can suddenly pause code to sweep away garbage, making some runs much slower.
category: concept
sources: raw/docs-note-python-list-sort.txt
---

# Garbage-collection pauses

Automatic memory management is convenient but unpredictable. The system may stop your code mid-run to throw away data you are done with.

## Background

Some languages like Python and JavaScript manage memory automatically. When you create objects, the language gives you memory. When you stop using them, the language is supposed to free that memory so it can be reused. But the language does not know exactly when you are done with an object, so it waits and watches. At some point, usually when memory is getting full, the language runs a garbage collector. This walks through all memory, marks the objects still in use, and deletes the rest. This can take milliseconds or more, and it pauses your code while it happens. In a benchmark, garbage collection can hit suddenly and make one run much slower than the others. This is frustrating because the slowness is not caused by your code but by the language. The fix is to run garbage collection before you start timing, or to run enough tests that the garbage collection happens equally often in all of them. Some benchmarkers even disable automatic garbage collection and run it by hand at specific times, but that is advanced. Understanding that garbage collection happens and watching for its effects is the first step.

## See also

Related:: [[benchmarking-practice-overview]], [[cache-locality]]
