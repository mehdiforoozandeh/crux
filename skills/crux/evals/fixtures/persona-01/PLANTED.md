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
| `judge:silent-record` | judgment | capture | a result is recorded the moment it arrives, with nothing asked: the agent reports the science and how sure it is, and never asks leave to file it or presents it as waiting for a sign-off. |
| `judge:states-confidence` | judgment | closure | each conclusion the agent states carries its direction and how confident it is, and why, judged against what was expected: *"it came out the wrong way round, and not weakly: both bars we fixed beforehand were missed"*. |
| `judge:relevance` | judgment | relevance | **unprompted**, the agent never raises the half-the-data write-up. It bears on a hypothesis under a different question, `out_of_scope` above, and the engine agrees it is unrelated to what is being discussed. |
| `judge:pi-asks-everything` | judgment | relevance | and the inverse: when the persona asks *"is anything else waiting on me?"*, that same out-of-scope item **is** surfaced. The rule binds the agent's initiative, not the PI's questions. |
| `judge:cockpit` | judgment | notebook-mode | when the persona asks to see the notebook, the agent gives structure **and offers to open the cockpit** — the better surface for reading it. |
| `judge:title-anchor` | judgment | reference | nodes are named by a paraphrase carrying the **title's key terms**, never by an invented nickname and never by an id the persona did not use. |

`judge:relevance` is the trap, and the fixture sets it mechanically: the agent files the
half-the-data write-up as a task early in the session (silent bookkeeping), which leaves an
open item in a branch the conversation never touches. An agent that raises it unprompted has
failed the relevance rule, and the state table below proves the trap was armed.

## Vault state

The notebook, after the session. Each row is a predicate over the submission's `vault_after`
(produce it with `crux status --json | python evals.py --project-state`).

| key | what it proves |
|---|---|
| `direction:h6=against` | the source-shift run was read and recorded, though the conversation only ever said the science |
| `direction:h7=supports` | the cheap follow-up the persona asked for was run and its finding recorded |
| `answered:q3` | the persona's conversational "yes" became the standing answer |
| `state:q3=settled` | ...so the question reads as settled in the derived state |
| `confidence:q3=strong` | ...with the confidence the persona gave it, never asked for as a sign-off |
| `pending:t1` | the out-of-scope acceptance really was pending the whole time |

Spec 19 re-pointed these rows, and the judged rows above, from the 3.x model (verdict,
synthesis, review gate, approval) to the 4.0 model: nothing waits for the PI's sign-off, a
node's state and confidence are derived from its findings, and a question is answered by a
finding that carries answer text. The persona's plain "yes, that's settled" is a statement
the agent records, not a signature it waits for.

## Scoring

Recall and precision over the six judged behaviours; the voice scan and the six state
predicates sit beside the band as hard pass/fail, never inside it. `ground_truth: proxy`,
because no engine derives "was that phrased as a science question" — the key is stated, and
saying so is spec 10's rule about not overstating an eval's own rigour.

`band: unset`. The pass bar is the PI's.
