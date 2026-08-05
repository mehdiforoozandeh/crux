# Spec 04 — ERA: empirical program search

**Label:** `era` · **Status:** ☐ todo

## Goal

A sibling that evolves whole programs toward a **scalar objective** (Google's ERA / Flat UCB
Tree Search) — an LLM writes and rewrites complete candidate programs, a sandbox scores each,
and a flat PUCT bandit (FUTS) keeps a diverse population and picks what to improve next.

Where crux *organizes* a research program, ERA *optimizes* the cases inside it: point it at a
hypothesis with a measurable bar and it searches for a program that clears it, escaping local
optima and returning a portfolio of winners.

## Work items

- ☐ **ERA ↔ crux contract** — how a hypothesis's verifiable / metric becomes an ERA scalar
  objective + sandboxed scorer, and how results return as `## Findings` + a headline metric.
- ☐ **Search loop** — the `generate_fn` / `execute_fn` interface, sandboxed scoring, and the
  FUTS / flat-UCB bandit over a program population (exploration vs. exploitation).
- ☐ **Portfolio output** — return a *diverse* set of high-scoring programs (not just the
  argmax) with scores + lineage, so the PI can choose.
- ☐ **Wire into the loop** — launch a search from a `running` hypothesis; record the winning
  program + metric back through `crux close`; running and the verdict stay under the PI's OK.
- ☐ **Package as the `era` skill.**

## Interaction with the verifiable design in spec 09

[09 specialized agents](09-specialized-agents.md) changes what a verifiable is: each one now
carries a stated failure scenario, and at least one must discriminate against a declared
`## Null`. That has a direct consequence here — **the ERA scalar objective must be derived
from a null-discriminating verifiable, not from any verifiable.**

Optimizing against a non-discriminating check is the machine-scale version of the bias
problem spec 09 exists to prevent: a search loop pointed at a bar the hypothesis was always
going to clear will find a program that clears it and teach you nothing. This constraint
belongs in the ERA ↔ crux contract when it gets written.

## Open questions

- Whether the sandbox is crux's problem at all, or whether ERA assumes one is supplied.
  The engine is stdlib-only and domain-agnostic by design; a scorer that executes candidate
  programs is neither.
- How lineage is recorded in the vault without every ERA generation becoming a node.
