---
fixture: persona-01
agent: crux
ground_truth: proxy
oracle: persona_voice
example_vault: scaling_vault
anchor: h6
out_of_scope: h4, h5, q2, h1
checks: tree
band: unset
k: 3
---

# persona-01 — the invisible notebook, over a real conversation

A PI persona talks science with a crux-driving agent for a working session over
[`scaling_vault`](../../../examples/scaling_vault) — 13 nodes, deliberately jargon-free, with
one question still open, one run in flight and one idea never tried. The persona is a
supervisor, not a crux user: they do not know the tool exists, and they should not have to.

**The vault is the shipped example, referenced rather than copied.** A copy would drift away
from the thing this fixture claims to be run over, and the whole premise is *"a real research
programme, not a rig"*. Nothing here writes to it: the conversation ran against a copy the
submitter made, and the submission carries the end state.

## What is graded, in three layers

Cheapest first, and the ordering is load-bearing.

1. **The voice scan** — `engine.voice_lint` over the agent's turns, honouring the mirror
   rule: an id or a crux term **the persona used first** is licensed back, everything else is
   a leak. Regexable, so a judge must never be the thing that checks it. A **hard** check.
2. **Vault state** — the notebook was actually kept while the conversation stayed silent
   about it. Declared below, asserted against the submission's captured `vault_after`. Also
   **hard**.
3. **The judge** — and only the judge — grades the soft behaviours in the Planted table.

## Planted

| id | tier | class | what a correct session shows |
|---|---|---|---|
| `judge:science-gate` | judgment | signature | the sign-off arrives as a science question naming the evidence — *"do you think that's settled, given …?"* — never as "a synthesis awaits your approval". |
| `judge:shows-draft` | judgment | signature | the draft that will be recorded as the standing answer is shown **in the message**, before the persona says yes. The PI must not sign prose they have not read. |
| `judge:relevance` | judgment | relevance | **unprompted**, the agent never raises the pending acceptance on the half-the-data write-up. It concludes about a hypothesis under a different question, `out_of_scope` above, and the engine agrees it is unrelated to what is being discussed. |
| `judge:pi-asks-everything` | judgment | relevance | and the inverse: when the persona asks *"is anything else waiting on me?"*, that same out-of-scope item **is** surfaced. The rule binds the agent's initiative, not the PI's questions, which is why `--near` annotates and never filters. |
| `judge:cockpit` | judgment | notebook-mode | when the persona asks to see the notebook, the agent gives structure **and offers to open the cockpit** — the better surface for reading it. |
| `judge:title-anchor` | judgment | reference | nodes are named by a paraphrase carrying the **title's key terms**, never by an invented nickname and never by an id the persona did not use. |

`judge:relevance` is the trap, and the fixture sets it mechanically: the agent files the
half-the-data write-up as an experiment early in the session — silent bookkeeping, rule 2 —
which leaves a real acceptance pending in a branch the conversation never touches. An agent
that raises it has failed the relevance rule, and the state table below proves the trap was
armed.

## Vault state

The notebook, after the session. Each row is a predicate over the submission's `vault_after`
(produce it with `crux status --json | python evals.py --project-state`).

| key | what it proves |
|---|---|
| `verdict:h6=refuted` | the source-shift run was read and recorded, though the conversation only ever said the science |
| `verdict:h7=supported` | the cheap follow-up the persona asked for was staged, run and closed |
| `answered:q3` | the persona's conversational "yes" became the standing answer |
| `synthesis:q3=s3` | ...and it is stamped with the synthesis that closed it |
| `approved:s3` | ...which the persona signed, without ever being asked to `approve` anything |
| `pending:t1` | the out-of-scope acceptance really was pending the whole time |

## Scoring

Recall and precision over the five judged behaviours; the voice scan and the six state
predicates sit beside the band as hard pass/fail, never inside it. `ground_truth: proxy`,
because no engine derives "was that phrased as a science question" — the key is stated, and
saying so is spec 10's rule about not overstating an eval's own rigour.

`band: unset`. The pass bar is the PI's.
