# Spec 19 — Background memory

- **Kind:** redesign (tree model, capture, skill layout)  - **Spec:** replaces the closure model of [15](15-evidence-semantics.md) and the leash of the main skill; changes [08](08-taskhub.md), [09](09-specialized-agents.md), [13](13-situate-and-design.md), [14](14-glossary.md), [18](18-autopilot-lean.md).
- **Status:** approved by the PI, 2026-10-31. Decisions were made one by one; the record is below.
- **Release:** v1.0.0, `ENGINE_VERSION` 4.0.

## Problem

The tree is a good idea with the wrong user experience.

- **The PI must fill it.** A question or hypothesis enters the tree only when the PI states it in a form crux accepts. Most automatic records land in the taskhub, not in the tree.
- **Closure is a hard gate.** Each hypothesis needs pre-registered thresholds and a combination rule, and each close needs the PI. Exploratory work has no threshold, and a hard threshold is often arbitrary. The PI must talk to crux about every node.
- **Too many parts.** Ten agents, a review gate, a synthesis that the PI signs, and a 36 KB skill (over its own 34,000-byte cap) that loads only when triggered. Because it is not always loaded, background capture does not happen.

## Goal

The tree is the long-term memory of a project, organized by the scientific method: the questions we asked, the hypotheses we made, what we found, the evidence for it, and how confident we are. It fills itself in the background from the PI's conversations with agents. The PI never has to think about how to fill it. Crux is lean, cheap and silent by default.

## Decisions

| # | Decision | Ruling |
|---|---|---|
| 1 | Tree vs taskhub | **Knowledge vs work.** The tree holds what we want to know and what we learned. The taskhub holds what we do. A task links to the node it serves. A task's output enters the tree only as evidence on a Finding. |
| 2 | How capture runs | The agent records inline, guided by the always-on core. A capture subagent catches what was missed, on two triggers only: `/crux-wrap` and a catch-up sweep at session start. No periodic background work. |
| 3 | Catch-up sweep | Reads only transcript text not yet swept, on a small model, with a hard token cap. It never asks the PI anything: confident items are written, uncertain items wait for the next `/crux-wrap`. `crux init` installs it for every harness whose transcripts it can read; Claude Code first. |
| 4 | Visibility | Silent by default. Evidence is always recorded. In ideation, questions and hypotheses are opened automatically. `/crux-wrap` shows what this session recorded, then asks accept/reject questions for the remaining candidates. |
| 5 | Node types | **Question / Hypothesis / Finding.** Synthesis is removed. A Question can hold Findings directly (exploratory work) or through Hypotheses. |
| 6 | Conclusion form | A Finding records a **direction** (supports · against · mixed · no answer yet), a **confidence** (strong · moderate · weak), one sentence of why, and evidence links. Questions and Hypotheses both carry a confidence: how confidently was this answered. |
| 7 | Expectation, null, verifiables | Before evidence, a Hypothesis always states an **expectation**. A **null** and **verifiables** are added when they can be defined. At closure the agent judges the evidence against all three and sets the confidence. A null that is not ruled out caps confidence at weak, like a non-significant p-value. A near miss on a threshold lowers confidence. The checks inform the judgment; they do not compute it. |
| 8 | Closing | **No close step.** A node's state is derived from its Findings: open (none), leaning (weak or moderate), settled (strong), or parked (the agent parks a node the conversation dropped). The PI corrects in plain words. |
| 9 | Agents | **capture** (new), **pre-run** (merges design, null and verifiables: drafts the expectation, null and checks, and confirms some outcome would change the confidence), **situate**, **migrate**. Removed: close, critic, audit, glossary. `crux-tests` moves to evolve-crux, since it builds crux, not research. |
| 10 | Always-on core | About 8 KB. In Claude Code a SessionStart hook injects it when the repo has a vault. Elsewhere `crux init` adds a one-line pointer to it in `AGENTS.md`. |
| 11 | Existing vaults | Automatic migration with a backup, on first load. |
| 12 | Version | `ENGINE_VERSION` 3.5 → 4.0, release tag v1.0.0. |

## Design

### The always-on core

`skills/crux/SKILL.md` becomes the core, at most 8,192 bytes. It holds only what runs in the background, plus a router. It contains:

1. **Capture rules.** What counts as a question, a hypothesis, a finding and evidence in a conversation; when to open a node silently; that evidence is always recorded.
2. **The tree/taskhub boundary** (decision 1), with one example of each side.
3. **Closure judgment** (decision 7): how expectation, null and verifiables set confidence.
4. **Voice.** The invisible notebook of [16](16-science-voice.md): no ids, verbs or crux terms reach the PI's chat. This stays inline because a miss is silent.
5. **Router.** One line per specialist skill or agent, with its trigger: crux-wiki, crux-litsearch, crux-autopilot, crux-cockpit, prezit, storify, crux-rd, evolve-crux, and the four agents.

Engine verbs, vault setup, autopilot rules, migration and the wiki move behind pointers in `references/` or the specialist skills. The AGENTS.md size rule changes from 34,000 to 8,192 bytes; the rule's test for what stays inline is kept.

### Capture

- **Inline.** The agent writes nodes as the conversation produces them, silently.
- **`/crux-wrap`.** Runs the capture agent on this session's transcript. Shows what the session already recorded (a short list in plain words), then one `AskUserQuestion` per remaining candidate: accept or reject.
- **Catch-up sweep.** The SessionStart hook finds transcript text after the last sweep mark, and starts one background capture run only if there is any. Small model, hard token cap, no question to the PI. Uncertain items go to a pending list that the next `/crux-wrap` shows.
- **Sweep mark.** The engine stores, per transcript, the offset swept last. A transcript reader exists per harness; Claude Code JSONL is the first.

### Tree model

| Node | Holds |
|---|---|
| Question | ELI5, TL;DR, derived state and confidence, child Hypotheses and Findings. |
| Hypothesis | ELI5, TL;DR, `## Expect` (required), `## Null` (optional), `## Verifiables` (optional), derived state and confidence, child Findings. |
| Finding | Direction, confidence, why (one sentence), evidence links into `results/` or the taskhub output, and, for a Hypothesis, how the result compared with the expectation, null and verifiables. |

Roll-up: a node's state and confidence come from its Findings by a fixed engine rule. The newest Finding counts most, and a later Finding can override an earlier one. The engine never judges; the agent writes the Finding, the engine derives the state.

### What the PI loses and keeps

This reverses the main skill's "human in charge by default, fixed, not configurable" rule for the tree. Opening nodes, recording Findings and settling nodes are now the agent's, silently. Kept as the PI's: starting an autopilot run, starting any compute the PI has not asked for, merging into `main`, and every correction the PI makes in plain words, which always wins over the agent's record.

### Taskhub

Ordinary tasks are unchanged. The `crux task accept` gate on experiment tasks is removed: an experiment task's output is attached as evidence to a Finding, silently. "A task that would open a question becomes a tree node" stays.

### Autopilot

Spec 18 closes each attempt from the scorer with no model call; that stays. The driver writes the attempt's Finding mechanically: bar met → supports, else against; strong when the margin exceeds the scorer's noise, else moderate. This is the one place confidence is computed, not judged (PI ruling, 2026-10-31), because a model call per attempt would undo spec 18's speed.

### Migration (engine 4.0)

| Old | New |
|---|---|
| verdict supported / refuted | direction supports / against; confidence from the tick vector (all claim-directed checks pass → strong; one missed → moderate) |
| inconclusive | mixed, weak |
| invalid-run | no answer yet, with the run kept as evidence |
| Synthesis (approved) | Finding on its Question |
| Verifiables, Null | kept as optional sections |
| Experiment task conclusions | Findings on their hypotheses |
| review gate, `pursue`, `approve`, `answer` | removed; the verbs print a one-line pointer to the new model |

A backup of the vault is written before migration. Proof: all four example vaults (`demo`, `scaling`, `segssl`, `sortlab`) and the CANDII vault (`~/Desktop/research/libbrechteam@sfu/CANDII/cruxvault`) load, migrate and validate. CANDII is migrated on a copy, never in place, for the proof.

## Acceptance

1. `./crux selftest` is fully green, with new asserts written first for: the derived states, the confidence roll-up, the null cap, the migration table, the sweep mark, and the core size limit.
2. `wc -c skills/crux/SKILL.md` ≤ 8,192.
3. In a fresh Claude Code session in a vault repo, the core is in context without any trigger word.
4. A scripted ideation conversation produces at least one Question and one Hypothesis with an expectation, with no PI action.
5. A scripted result conversation produces a Finding with direction, confidence and an evidence link, with no PI action.
6. `/crux-wrap` lists the session's records and asks about pending candidates only.
7. The catch-up sweep runs once per session start at most, and not at all when nothing is new.
8. Migration proof on the five vaults above.
9. Stdlib only. The cockpit stays read-only and renders the new states and confidence.

## Out of scope

Transcript readers for harnesses other than Claude Code. Pruning of weak ideation nodes beyond parking. Redesign of the wiki, prezit or storify beyond renaming what they read.

## Open questions

1. **Pruning.** Silent ideation can fill the tree with weak guesses. Parking is the only remedy in this spec. Revisit after a month of use.
