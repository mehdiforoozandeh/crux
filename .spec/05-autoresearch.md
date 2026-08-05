# Spec 05 — Autoresearch: autonomous experiment loops

**Label:** `autoresearch` · **Status:** ☐ todo

## Goal

Drive the crux loop with far less turn-taking — an agent that proposes the next question /
hypothesis, registers verifiables, runs experiments, reads results, and rolls up the ledger,
iterating largely unattended — while the **human-in-charge gates stay intact** (the PI still
approves running an experiment and recording a verdict, and clears the review gate).

## Work items

- ☐ **Autonomy envelope** — pin exactly which loop steps run unattended vs. still require PI
  approval (running + verdicts stay gated); a clear, auditable leash.
- ☐ **Proposer** — generate the next question / hypothesis + pre-registered verifiables from
  the current tree + wiki, prioritized by what most reduces uncertainty.
- ☐ **Runner** — launch and track experiments (local / SLURM), attach run links, detect
  completion.
- ☐ **Closer** — read results, tick verifiables, derive the verdict, roll up; surface to the
  PI at the review gate rather than self-answering.
- ☐ **Budget & stop** — per-round cost / compute caps and an explicit stopping condition so a
  loop can't run away.
- ☐ **Package as the `autoresearch` skill.**

## Supersession by spec 09

**This epic's Proposer / Runner / Closer decomposition is now the taxonomy in
[09 specialized agents](09-specialized-agents.md), and spec 09 should be built first.**

The two specs arrived at the same decomposition from opposite directions — this one from
"how do we run unattended," spec 09 from "how do we stop a single agent biasing its own
verifiables." Where they overlap, spec 09's version is more developed and supersedes:

| this spec | spec 09 equivalent |
|---|---|
| Proposer (question/hypothesis + verifiables) | split into `crux-null` + `crux-verifiables`, because one agent authoring both the target and its test reintroduces the bias |
| Closer | `crux-close`, same job |
| Runner | not yet designed in 09 — **this spec still owns it** |
| Autonomy envelope | partially settled: spec 09 puts a PI gate on the `## Null`; the rest is open |
| Budget & stop | still owned here |

What remains genuinely this epic's after 09 lands: the **Runner** (launch/track/detect on
SLURM), the **budget-and-stop** mechanics, and the **envelope** — the written statement of
which steps run unattended.

Do not build a second Proposer or Closer here.

## Open questions

- Whether "largely unattended" survives contact with the leash rule at all. The leash lists
  `ask`, `hypothesize`, `test --to running`, `close`, `answer`, and `pursue` as
  propose→approve→do. That is most of the loop. The honest version of this epic may be
  "batch the approvals" rather than "remove them."
- The stopping condition. `crux` has no notion of a research program being finished, and the
  spec-kit research (recorded in [08 taskhub](08-taskhub.md)) found that a terminal
  `converged` state is exactly the software-delivery assumption that does not transfer.
