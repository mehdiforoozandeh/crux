---
id: s4
type: synthesis
title: Why the built-in sort wins
approved: "2026-08-16T16:07:12"
created: "2026-08-16T16:07:12"
updated: "2026-08-16T16:07:12"
---

# Synthesis — Why the built-in sort wins

Related:: [[q23_is_the_built_in_sort_written_in_a_faster]], [[q33_does_the_built_in_sort_notice_runs_that_]]

## Headline conclusions

The built-in sort is not running the same kind of code I wrote. A bare Python loop that only counts is slower than the entire built-in sort. The built-in sort is fastest when the input is one long sorted run, and it speeds up on lists made of a few long sorted runs. It notices when data is already in order.

## Cross-run table

| hypothesis | what I measured | verdict |
|---|---|---|
| The built-in sort is not running my kind of Python code | Counter loop slower than the whole sort | supported |
| A Python loop that only counts is slower than the whole built-in sort | Counting loop: 2.3 ms, sort: 0.8 ms | supported |
| Most of my sort's time goes on comparing, not on moving | Comparison count was lower than expected | refuted |
| The built-in sort is fastest when the list is one long run | 0.1 ms on fully sorted 1000 items | supported |
| The built-in sort speeds up on a list made of a few long runs | Multiple runs: 0.5 ms | supported |
| Breaking the runs up removes the built-in sort's advantage | Mixed results, hard to conclude | inconclusive |

## Implications for next batch

The built-in sort is written in C and compiled, not interpreted like my Python code. It also adapts to the data it sees. I need to measure my code's footprint separately from the language's overhead to make a fair comparison.
