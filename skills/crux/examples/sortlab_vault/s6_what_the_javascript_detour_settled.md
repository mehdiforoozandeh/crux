---
id: s6
type: synthesis
title: What the JavaScript detour settled
approved: "2026-08-16T16:07:13"
created: "2026-08-16T16:07:12"
updated: "2026-08-16T16:07:13"
---

# Synthesis — What the JavaScript detour settled

Related:: [[q26_does_the_same_method_rank_the_same_way_i]]

## Headline conclusions

The five sorts do not rank the same way in JavaScript as in Python. Each language ranked them differently. JavaScript runs faster overall. One comparison run had to be thrown out because the two sides got different lists, so the built-in-sort comparison is incomplete.

## Cross-run table

| hypothesis | what I measured | verdict |
|---|---|---|
| The five sorts rank the same in JavaScript as in Python | Python: insertion first, quick last. JavaScript: quick first, insertion third. | refuted |
| The same sort is faster in JavaScript than in Python | Insertion: Python 4.2 ms, JavaScript 1.8 ms | supported |
| The built-in sort wins in JavaScript too | Different lists generated, run is void | invalid-run |

## Implications for next batch

Language matters more than I thought. JavaScript's JIT compiler makes code run faster but changes which algorithm performs best. I need to redo the built-in-sort test with matching lists and report that this run taught nothing.
