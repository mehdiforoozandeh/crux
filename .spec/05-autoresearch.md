# Spec 05 — Autoresearch: autonomous loops

**Label:** `autoresearch` · **Status:** ⏸ deferred

> **Deferred 2026-08-15.** Both loops in this spec — the outer tree loop and the inner ERA
> program search merged in from the retired spec 04 — are parked. Not rejected: the design
> below stands and is worth keeping. But unattended loops are the highest-risk thing crux
> could add, and they should not be built while the things that would make them *safe* are
> still unbuilt — [15](15-evidence-semantics.md) is what stops a loop banking a partial answer
> as a result, and [09](09-specialized-agents.md) is what stops it grading its own homework.
>
> **Do not implement this spec.** Revisit once 09 and 15 have shipped.
**Supersedes:** the former spec 04 (ERA: empirical program search), merged in below
**Superseded in part by:** [09 specialized agents](09-specialized-agents.md)

## Goal

Drive crux with far less turn-taking — while the **human-in-charge gates stay intact** (the PI
still approves running an experiment and recording a verdict, and clears the review gate).

There are two loops, and they are the same machinery pointed at different scopes:

- **Outer loop — across the tree.** Propose the next question / hypothesis, register
  verifiables, run experiments, read results, roll up the ledger.
- **Inner loop — inside one hypothesis (ERA).** Given a hypothesis with a measurable bar,
  search for a program that clears it: an LLM writes and rewrites whole candidate programs, a
  sandbox scores each, and a flat PUCT bandit (FUTS) keeps a diverse population and picks what
  to improve next.

## Why these are one spec, not two

They were written separately and then kept colliding. Both are unattended loops over an
expensive resource; both need the same three things crux does not have:

| shared machinery | outer loop needs it for | inner loop (ERA) needs it for |
|---|---|---|
| **Runner** — launch / track / detect completion on local + SLURM | running an experiment | scoring each candidate program |
| **Budget & stop** — per-round cost/compute caps, explicit stopping condition | not iterating forever across the tree | not iterating forever within one hypothesis |
| **Autonomy envelope** — which steps run unattended vs. gated | verdicts and direction stay PI-gated | the verdict on the winning program stays PI-gated |

Building two runners, two budget mechanisms and two envelopes would be the mistake. The inner
loop is a *strategy the runner can execute*, not a parallel system.

The distinction that survives the merge: the outer loop moves **across** the tree and touches
direction, so it is heavily gated. The inner loop moves **within** one already-approved
hypothesis toward an already-approved bar, so once the PI has approved the run it can iterate
unattended until budget or stopping condition — which is precisely what makes ERA tractable and
the outer loop hard.

## Supersession by spec 09 — do not rebuild the Proposer or Closer

**Spec 09's Proposer / Closer decomposition is more developed and should be built first.** The
two specs reached the same decomposition from opposite directions — this one from "how do we
run unattended," 09 from "how do we stop a single agent biasing its own verifiables."

| this spec | spec 09 equivalent |
|---|---|
| Proposer (question/hypothesis + verifiables) | split into `crux-null` + `crux-verifiables`, because one agent authoring both the target and its test reintroduces the bias |
| Closer | `crux-close`, same job |
| Runner | not designed in 09 — **this spec owns it** |
| Autonomy envelope | partially settled: 09 puts a PI gate on the `## Null`; the rest is open |
| Budget & stop | **this spec owns it** |
| ERA inner loop | not in 09 — **this spec owns it** |

## The ERA ↔ crux contract

### The objective must come from a null-discriminating verifiable

[09](09-specialized-agents.md) changes what a verifiable is: each carries a stated failure
scenario, and at least one must discriminate against a declared `## Null`. That has a direct
consequence here — **the ERA scalar objective is derived from a null-discriminating verifiable,
never from just any verifiable.**

Optimizing against a non-discriminating check is the machine-scale version of the bias problem
09 exists to prevent. A search loop pointed at a bar the hypothesis was always going to clear
will find a program that clears it and teach you nothing — except now it will do so thousands
of times, at cost, and produce a portfolio of winners that are all artifacts. This is the
single most important line in the contract.

### Shape

- **Objective** — one scalar, derived from the discriminating verifiable; the sandbox scorer is
  the deterministic side, the program text is the agent side.
- **Search** — `generate_fn` / `execute_fn`, sandboxed scoring, FUTS / flat-UCB over a program
  population (exploration vs. exploitation).
- **Portfolio output** — return a *diverse* set of high scorers with scores + lineage, not the
  argmax alone, so the PI chooses.
- **Return path** — the winning program + headline metric land through `crux close`. Launching
  the search and accepting the verdict both stay under the PI's OK.

## Rejected alternatives

- **Keeping ERA as its own epic.** It duplicated the runner, the budget mechanism and the
  envelope. Merged.
- **A second Proposer or Closer here.** See the supersession table — build 09's.
- **A terminal `converged` state for the outer loop.** The spec-kit research recorded in
  [08 taskhub](08-taskhub.md) found this is exactly the software-delivery assumption that does
  not transfer: research has no finish line. A *budget* stop is legal; a *converged* stop is
  not.
- **Treating "waiting on the cluster" as a loop state.** Same call as taskhub's — it is a
  dependency, not a status.

## Open questions

- **Whether "largely unattended" survives the leash at all.** The leash lists `ask`,
  `hypothesize`, `test --to running`, `close`, `answer` and `pursue` as propose→approve→do.
  That is most of the outer loop. The honest version of this epic may be "batch the approvals"
  rather than "remove them." Note the inner loop does not have this problem — it runs entirely
  inside one already-approved hypothesis.
- **Whether the sandbox is crux's problem at all**, or whether ERA assumes one is supplied. The
  engine is stdlib-only and domain-agnostic by design; a scorer that executes candidate
  programs is neither. Leading answer: crux defines the contract and the vault records, the
  sandbox is supplied by the project.
- **How ERA lineage is recorded without every generation becoming a node.** Leading answer: the
  portfolio is an artifact under `results/<hid>/`, not a subtree.
- The stopping condition for the outer loop, given `converged` is rejected.

## Work items

- ☐ **Autonomy envelope** — pin exactly which loop steps run unattended vs. require PI
  approval, for both loops; a clear, auditable leash.
- ☐ **Runner** — launch and track experiments (local / SLURM), attach run links, detect
  completion. Serves both loops.
- ☐ **Budget & stop** — per-round cost / compute caps and an explicit stopping condition, so
  neither loop can run away.
- ☐ **ERA ↔ crux contract** — discriminating-verifiable → scalar objective + sandboxed scorer;
  results return as `## Findings` + a headline metric.
- ☐ **ERA search loop** — `generate_fn` / `execute_fn`, sandboxed scoring, FUTS bandit over the
  population.
- ☐ **Portfolio output** — diverse high scorers with scores + lineage.
- ☐ **Wire into the loop** — launch a search from a `running` hypothesis; record the winner
  through `crux close`.
- ☐ **Package as the `autoresearch` skill**, with ERA as a documented mode rather than a
  separate skill.
