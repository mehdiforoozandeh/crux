# `.spec/` — the crux backlog

One spec document per epic. Replaces the former single-file `ROADMAP.md`, which
grew past what one file could carry once epics started accumulating design
rationale rather than just checklists.

**Status legend:** ☐ todo · ◐ in progress · ☑ done

| # | Spec | Label | Status |
|---|------|-------|--------|
| 01 | [Graphical UI for crux](01-gui-cockpit.md) | `ui` | ◐ |
| 02 | [Marketing animation + README hero](02-marketing.md) | `marketing` | ☐ |
| 03 | [LLM wiki](03-llm-wiki.md) | `wiki` | ◐ |
| 04 | [ERA: empirical program search](04-era.md) | `era` | ☐ |
| 05 | [Autoresearch: autonomous experiment loops](05-autoresearch.md) | `autoresearch` | ☐ |
| 06 | [Node economy](06-node-economy.md) | `economy` | ☐ |
| 07 | [RD layer](07-rd-layer.md) | `rd` | ☐ |
| 08 | [Taskhub](08-taskhub.md) | `taskhub` | ☐ |
| 09 | [Specialized agents](09-specialized-agents.md) | `agents` | ☐ |
| 10 | [Agent evals](10-agent-evals.md) | `evals` | ☐ |
| 11 | [prezit: presentations from a subtree](11-prezit.md) | `prezit` | ☐ |

## Dependency order

Specs 06–10 came out of one design session and are ordered by what unblocks what:

```
06 node economy ──┬──> 07 RD layer ──┐
                  └──> 08 taskhub ───┼──> 09 specialized agents ──> 10 agent evals
                                     │
                            (09 also needs 06's --json CLI surface)
```

11 sits outside that chain. It needs 06's `--json` convention and is *enriched* by 07 (RD
pages become the methods slides) and 03 (wiki pages become the intro), but blocks on neither —
it ships reading methodology from the hypothesis node and its linked report, and picks up RDs
for free when 07 lands.

06 ships first because the 400-word cap is what forces 07 and 08 to exist. Building
the overflow channels before the thing that overflows is backwards.

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
