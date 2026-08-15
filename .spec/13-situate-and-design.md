# Spec 13 — Situate and design: two agents for reading and planning

**Label:** `agents` · **Status:** ☐ todo
**Depends on:** [09 specialized agents](09-specialized-agents.md) (`crux brief`),
[15 evidence semantics](15-evidence-semantics.md) (schema the design agent checks against)

## Goal

Two agents for the two moments the PI is least served today:

- **`/situate`** — *"I have been away. Where are we on q20?"* A short, plain-language
  orientation over a subtree, composed on demand.
- **`crux-design`** — *"will this experiment leave us with partial answers?"* A design check
  run **before** the compute is spent.

Both are the judgment layer over machinery that lives elsewhere: `/situate` reads a
deterministic dossier from [09](09-specialized-agents.md)'s `crux brief`; `crux-design` checks
against the schema in [15](15-evidence-semantics.md).

---

# Part 1 — `/situate`

## Motivation

As a tree grows across months, the PI cannot re-orient by looking at it. The structure shows
what exists; it does not show *where we are*. The specific request:

> *find q20 and all of its children. Give me a one-paragraph ELI5 and a three-paragraph
> TL;DR of what q20 is, where we are on it, what is known, what is yet to be tested, and what
> our main paths forward are.*

Almost all of that is computable:

| the question | who answers |
|---|---|
| find q20 and its children | engine |
| what q20 is | the node's own ELI5 / TL;DR ([06](06-node-economy.md)) |
| where we are on it | child statuses, ticked verifiables, gate state |
| what is known | findings on `done` children |
| **what is yet to be tested** | unrun `idea` children + unticked verifiables — **engine** |
| **main paths forward** | judgment — the agent |

So the prose is a thin layer over a dossier the engine builds byte-identically.

## Design

### `crux brief` is the tool; `/situate` is the agent

Clean split, and it is the PI's ruling:

- **`crux brief <node…> --json`** — deterministic, takes one or more node ids, emits vault
  state. Never authors a sentence.
- **`crux-situate`** — an agent that (1) resolves the PI's natural-language question into a
  node id list, (2) calls `crux brief`, (3) composes the orientation.

Output is **ephemeral — chat only**. Regenerated on every call, so it can never be stale, and
the vault stays a record of science rather than of summaries.

### `crux brief` must carry two payloads

Forced, and worth stating plainly because it touches a safety mechanism.
[09](09-specialized-agents.md)'s brief deliberately **excludes** `## Problem Statement` and
the subtree — that exclusion *is* the anti-bias mechanism for `crux-verifiables`. Situate
needs the opposite: subtree, ancestry, and linked wiki pages.

```
crux brief <node…> --mode=isolated   # default — 09's bias-proof payload
crux brief <node…> --mode=situate    # subtree + ancestry + linked wiki
```

**`isolated` is the default** so that a forgotten flag degrades to over-isolation rather than
to leaked advocacy. `selftest.py` asserts that `isolated` output never contains
`## Problem Statement`.

Situate's payload reaches: the subtree, the **ancestry chain** (*"where we are"* usually needs
the parent's `## Answer so far` to make sense), and wiki pages any node in the subtree links.
Inbound citations from elsewhere in the tree were considered and left out of v1 — see *Open
questions*.

### What the output must be

Brevity, clarity, understandability — in that order. The PI's framing: as the tree grows over
months or years, situating oneself by looking at the tree stops working, and this is the
replacement. A verbose `/situate` has failed at its only job.

Shape: one paragraph ELI5, then three paragraphs TL;DR — what this is, where we are, what
remains. Plain language; no crux vocabulary the PI has not agreed to (see
[14](14-glossary.md), which is the enforcement).

---

# Part 2 — `crux-design`

## Motivation

*"A very important part of doing research is to ask the right questions. But to answer those
questions, we have to do the right experiments."* [15](15-evidence-semantics.md) supplies the
schema that makes partial answers detectable; this agent is what applies it **before** the
run.

Its central question, which is the PI's own question made checkable:

> **Is there any plausible outcome of this run from which we would conclude nothing?**
> If yes, the design is wrong — fix it before spending the compute.

## Design

### It checks all three diseases, and it is a critic before it is an author

[15](15-evidence-semantics.md) names three causes of a partial answer. `crux-design` checks
all three — a partial answer does not announce which one it has — but it **fixes only (c)**,
the run's ability to discriminate. For (a) it reports *"this is two claims"* and hands off to
`crux-critic`; for (b) *"this check does not follow from the claim"* and hands off to
`crux-verifiables`. One job, three detectors, clean handoffs.

### The slots it fills

[15](15-evidence-semantics.md) established that **presence of a declaration is machine-checkable
while its quality is not.** So the engine owns the slots and this agent owns filling them
well:

| deterministic (`validate`) | judgment (`crux-design`) |
|---|---|
| a control is declared | is it the *right* control |
| n / replicates stated | is n adequate for the claimed effect |
| the measurement is named | does it measure the construct |
| ≥1 outcome-neutral check | does it actually cover the shared failure mode |
| a combination rule is declared | is it the honest one |
| the separability model is declared | does it hold |

Output lands in `## Planned Intervention` **inside the 400-word cap**, plus the structured
fields. Overflow goes to an RD ([07](07-rd-layer.md)) — which is what 07 exists for.

### Skill or agent — agent, with one caveat

[07](07-rd-layer.md) argues an RD writer must be a *skill* because the design lives in the
conversation. [09](09-specialized-agents.md) argues `crux-verifiables` must be an *agent*
because isolation is the mechanism. Experiment design sits with the second: the cold input is
concrete — hypothesis, approved null, verifiables, available data and compute — and the same
bias applies, since whoever argued for the hypothesis will design a run that flatters it.

**The caveat, and it is real:** what compute is available, what the cluster queue looks like,
what was tried last month. A cold agent re-derives these badly. Fix: they go in the brief, not
in the prompt — the same discipline [09](09-specialized-agents.md) already imposes. What the
brief cannot supply is an open question below.

### Domain-general vocabulary

Control, replicate, randomize, confound, effect size, blinding, positive control, stopping
rule. The research confirmed the decisiveness layer is domain-general — an A/A test is a
negative control, seeds are replication, a held-out set is blinding — while what is
domain-specific is the *list* of nuisance factors, the statistical model, the randomization
unit and the ethics gate. **So: the schema is slots; the agent fills them per domain.**

A per-vault methodology dialect (the way `wiki_schema.md` declares per-vault categories) was
considered and **parked** — it complicates the first version for a benefit nobody has needed
yet.

## Decisions

| decision | rationale |
|---|---|
| `crux brief` is the deterministic tool; `/situate` is the agent on top | PI ruling; keeps the assertable part assertable |
| `brief` gains modes, default `isolated` | 09's exclusion is a safety mechanism; a forgotten flag must fail safe |
| situate output is ephemeral | cannot go stale; the vault records science, not summaries |
| situate reads subtree + ancestry + linked wiki | "where we are" needs the parent's answer-so-far |
| brevity is situate's acceptance criterion, not a preference | a verbose situate has failed at its only job |
| `crux-design` detects all three diseases, fixes one | partial answers do not announce their cause; but the fixes belong to existing owners |
| `crux-design` is an agent, not a skill | concrete cold input; and the designer must not be the advocate |
| environment facts go in the brief, never the prompt | the parent's bias would otherwise leak through the one channel it controls |
| domain-general vocabulary; schema as slots | the decisiveness layer is genuinely universal; the nuisance list is not |
| per-vault methodology dialect parked | complexity now, benefit later |

## Rejected alternatives

- **Naming the situate agent `/brief`.** `crux brief` is taken by
  [09](09-specialized-agents.md) with the opposite contract — deterministic and
  exclusion-based. Two things with one name, one of them a safety mechanism, is how safety
  mechanisms get bypassed.
- **`/debrief` as a separate skill.** One verb covers it.
- **Situate writing back into the question's `## TL;DR`.** Tempting — 06 created that field —
  but it makes an ephemeral summary durable and stale, and it means reading a node silently
  rewrites it.
- **A generated `SITUATION.md`.** Another generated index that drifts from truth.
- **Situate having no engine verb** (reading `/snapshot.json` directly). Cheapest, but the
  payload stops being assertable in `selftest.py`.
- **`crux-design` owning claim-splitting and verifiable-authoring outright.** That is
  `crux-critic` and `crux-verifiables`; absorbing them violates
  [09](09-specialized-agents.md)'s one-job rule and rebuilds the bias problem those two exist
  to solve.
- **A guided end-to-end design conversation** (claim → null → verifiables → methodology as one
  flow). Folds 09's two isolated agents into one conversational surface and loses the
  isolation that is their entire mechanism.

## Open questions

- Whether `/situate` should accept no argument at all, meaning *"where does the whole program
  stand"*. The PI scoped `crux brief` to explicit node ids, but the come-back-after-months
  case is exactly the whole-vault case.
- How situate resolves a natural-language question to node ids, and what it does when the
  resolution is ambiguous. Resolving to the wrong subtree produces a confident, wrong
  orientation — the worst failure this agent has.
- Whether inbound citations (*"h44 under q13 depends on this answer"*) belong in the situate
  payload. High value for orientation; unbounded in size.
- What `crux-design` needs about the compute environment that the brief cannot deterministically
  supply, and where that comes from without re-opening the prompt as a bias channel.
- Whether `crux-design` runs at `hypothesize` time, at `test` time, or on demand. Design should
  precede the run, but a hypothesis may sit as an `idea` for months before anyone runs it.
- Whether the per-vault methodology dialect ever gets unparked.

## Work items

- ☐ `crux brief <node…> --json --mode=isolated|situate`; ancestry + linked wiki in situate mode
- ☐ `selftest.py` assert: `isolated` output never contains `## Problem Statement`
- ☐ `crux-situate` agent definition — resolve ids, call brief, compose; ephemeral output
- ☐ Brevity constraint on situate output, written as a checkable bound
- ☐ `crux-design` agent definition — three detectors, handoffs, fills the
  [15](15-evidence-semantics.md) slots
- ☐ The three-disease taxonomy and the separability rulebook sentence into the crux skill
- ☐ `## Planned Intervention` discipline + structured methodology fields

## Acceptance criteria

- `crux brief q20 --mode=situate --json` is byte-identical across runs and contains no text
  authored by a calling agent.
- `crux brief q20 --json` with no mode flag excludes `## Problem Statement`.
- Situate mode contains q20's subtree, its ancestry chain, and its linked wiki pages.
- `/situate q20` returns one ELI5 paragraph and three TL;DR paragraphs, and writes nothing to
  the vault.
- `crux-design` given a hypothesis with no outcome-neutral verifiable reports it, and names the
  shared failure mode that is uncovered.
- `crux-design` given a compound claim reports it as cause (a) and hands off rather than
  redesigning the run.
- `selftest.py` passes with a grown assert count.
