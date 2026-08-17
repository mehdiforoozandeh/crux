# `.spec/` — the crux backlog

One spec document per epic. Replaces the former single-file `ROADMAP.md`, which
grew past what one file could carry once epics started accumulating design
rationale rather than just checklists.

**Status legend:** ☐ todo · ◐ in progress · ☑ done · ⏸ deferred (designed, deliberately not
being built — do not implement)

| # | Spec | Label | Status |
|---|------|-------|--------|
| 01 | [Graphical UI for crux](01-gui-cockpit.md) | `ui` | ☑ |
| 02 | [Marketing animation + README hero](02-marketing.md) | `marketing` | ☑ |
| 03 | [LLM wiki](03-llm-wiki.md) | `wiki` | ☑ |
| 05 | [Autoresearch: autonomous loops](05-autoresearch.md) | `autoresearch` | ⏸ |
| 06 | [Node economy](06-node-economy.md) | `economy` | ☑ |
| 07 | [RD layer](07-rd-layer.md) | `rd` | ☑ |
| 08 | [Taskhub — incl. experiments](08-taskhub.md) | `taskhub` | ☐ |
| 09 | [Specialized agents](09-specialized-agents.md) | `agents` | ☑ |
| 10 | [Agent evals](10-agent-evals.md) | `evals` | ☐ |
| 11 | [prezit: presentations from a subtree](11-prezit.md) | `prezit` | ☑ |
| 12 | [Cockpit craft: interaction & performance](12-cockpit-craft.md) | `ui` | ☐ |
| 13 | [Situate and design](13-situate-and-design.md) | `agents` | ☐ |
| 14 | [Project glossary](14-glossary.md) | `glossary` | ☐ |
| 15 | [Evidence semantics](15-evidence-semantics.md) | `evidence` | ◐ |

Numbers are permanent identifiers, not positions — a merged or dropped spec leaves its number
retired rather than renumbering the rest and breaking every cross-reference. **04 (ERA) is
retired**: it merged into [05](05-autoresearch.md), because both were unattended loops needing
the same runner, budget cap and autonomy envelope. **Both are deferred** — see below.

## What to build, and what not to

**Eight specs are `☐ todo`: 07, 08, 09, 10, 12, 13, 14, 15.** They are the work.
(11 landed 2026-08-15: engine 1.4's `crux deck` verbs + the `prezit` skill.)

**Do not implement 05.** ERA and the outer autoresearch loop are `⏸ deferred` — designed, kept,
deliberately unbuilt. Unattended loops are the riskiest thing crux could add, and they must not
be built before the machinery that makes them safe exists: [15](15-evidence-semantics.md) is
what stops a loop banking a partial answer as a result, and [09](09-specialized-agents.md) is
what stops it grading its own homework.

01, 02, 03, 06, 07, 11 and 12 are `☑ done` and are reference material, not work.

## Dependency order

Specs 06–10 came out of one design session and are ordered by what unblocks what:

```
06 node economy ──┬──> 07 RD layer ──┐
                  └──> 08 taskhub ───┼──> 09 specialized agents ──> 10 agent evals
                                     │              │
                            (09 also needs 06's     └──> 13 situate & design
                             --json CLI surface)    └──> 14 glossary

15 evidence semantics ──> 08 (experiments) and ──> 13 (crux-design)
```

11 sits outside that chain. It needs 06's `--json` convention and is *enriched* by 07 (RD
pages become the methods slides) and 03 (wiki pages become the intro), but blocks on neither —
it ships reading methodology from the hypothesis node and its linked report, and picks up RDs
for free when 07 lands.

06 ships first because the 400-word cap is what forces 07 and 08 to exist. Building
the overflow channels before the thing that overflows is backwards.

12 sits outside everything — a set of independently shippable cockpit defects, split from 01
so they do not wait on 01's unresolved packaging and editability questions.

13 and 14 are both downstream of 09: they add to its agent roster and reuse its brief and its
context-isolation architecture. 15 is upstream of both 08 and 13 — it defines what an
experiment's results *mean*, which 08 stores and 13's `crux-design` checks against.

## The 2026-08-14 session

Specs 12–15 and the amendment to 08 came from one design session, with five research
subagents. Two things it settled that touch existing specs:

- **Experiments merged into the taskhub** ([08](08-taskhub.md)). An experiment is a task whose
  output is evidence — one differing field, therefore one layer. This replaced a proposed
  separate experiment layer and sharpened 08's hard line from *"a task may never create
  direction"* to *"work never creates direction; an output that is evidence enters the gated
  tier."*
- **Synthesis nodes were proposed and dropped** — the engine has had them since v0.5
  (`type: synthesis`, `crux synthesize` / `approve`, and a question resolves only on an
  approved one). The real gap was that zero have ever been written, which is
  [06](06-node-economy.md)'s finding, not a missing feature.

Marketing items from the same session (local-first positioning, science-YouTuber outreach)
went to `~/crux-marketing` per the standing rule that launch work lives there.

## `research/`

Background compiled for the specs above, kept because it is expensive to re-derive and each
document records sources with URLs:

| file | for |
|---|---|
| [`perf-cockpit-candi.md`](research/perf-cockpit-candi.md) | 12 — measured bottlenecks on the 113-node CANDI vault, including three suspects cleared with evidence |
| [`research-beautifui.md`](research/research-beautifui.md) | 12 — what `beautifului.dev` actually is, and the little that transfers |
| [`research-doe-core.md`](research/research-doe-core.md) | 15 — design of experiments; outcome-neutral tests; assay sensitivity |
| [`research-prereg-endpoints.md`](research/research-prereg-endpoints.md) | 15 — ICH E9 endpoint rules; why bare pre-registration fails and Registered Reports work; PLATO |
| [`research-separability.md`](research/research-separability.md) | 15 — when one experiment can settle several hypotheses separately |
| [`research-prior-art-experiment-model.md`](research/research-prior-art-experiment-model.md) | 08, 15 — 25-system survey of how ELNs, ML trackers, A/B platforms and provenance ontologies model hypothesis vs experiment |

## Document shape

Each spec carries: **Goal** · **Motivation** (evidence, where there is any) ·
**Design** · **Decisions** (settled calls + why) · **Rejected alternatives** ·
**Open questions** · **Work items** · **Acceptance criteria**.

The *Rejected alternatives* section is not decoration. Half the cost of this kind of
work is re-litigating a call someone already made and didn't write down. If a spec
records only what we chose, the next person re-derives why — expensively.

## Relationship to `evolve-crux`

A spec here is the **backlog** entry: what and why. The `evolve-crux` skill turns one
into a **PRD** (acceptance criteria that become selftest asserts), then through the
validation gate to a PR. A spec is not itself a PRD — it is upstream of one, and one
spec typically becomes several.
