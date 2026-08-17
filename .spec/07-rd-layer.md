# Spec 07 — RD layer

**Label:** `rd` · **Status:** ☑ done (engine 1.5, 2026-08-15)
**Depends on:** [06 node economy](06-node-economy.md)

## Goal

A place for the design detail that the 400-word node cap displaces: **Requirements
Documents**. One RD per node that earns one, living in the vault, linked from the node,
outside the roll-up tree.

An RD is where design detail goes **to be readable, not to hide**. The node's TL;DR must
stand alone: a reader who never opens the RD still knows what is being asked and what would
settle it.

## Motivation

q21 is 5,725 words. Strip its work items (→ taskhub) and its amendment log (→ git), and what
remains is a genuine design document: the estimand `I(y ; c | x)` and its variational bound,
a three-rung probe ladder with fixed architectures, capacity and width certificates, a
negative-control design, a partial-pooling scheme with a stated distortion, and an
attenuation-reporting rule across three output formats.

None of that is wrong. It is simply not a *question*, and cramming it into `## Question` is
what makes the node unreadable and the cockpit useless.

## Design

### Structure — copy the wiki layer

The wiki layer ([03](03-llm-wiki.md)) already solved this exact shape and is proven in this
codebase. Do not invent a second pattern.

| wiki | RD |
|---|---|
| `wiki/<slug>.md`, `type: wiki` | `rd/<slug>.md`, `type: rd` |
| parentless, outside the roll-up | parentless, outside the roll-up |
| linked from nodes via `[[wikilinks]]` | linked from its node via `[[wikilinks]]` |
| generated `WIKI.md` index | generated `RD.md` index |
| structural lint in `validate` | structural lint in `validate` |
| `Wiki` tab, markdown reader + backlinks | reuse that reader — do not build a third |

New verb: `crux rd <node> "<title>"` — creates the file and writes the backlink into the
node. An RD belongs to exactly one node, though it may cite others.

**One *active* RD per node** — superseded ones accumulate and are kept; the chain is the
record. *(Amended on build, PI ruling D11: the original text said "one RD per node maximum",
which cannot be reconciled with a `draft → active → superseded` chain. The rejected
alternative below — "multiple RDs per node" — is still rejected: you cannot have two live
designs, only one live one and a history.)*

**The backlink is WRITTEN into the node file** (`RD:: [[rd/<slug>]]`, beside `Parent::`), not
computed. Spec 08's task work-graph uses the opposite convention, and that split is
deliberate (PI ruling, 2026-08-15): **tree-lineage links are written**, following the
`Parent::` idiom the vault has used since v0.1, because an RD belongs to exactly one node and
travels with it; **the taskhub's work-graph stays computed**, because a task may touch many
nodes and is re-derived. Two layers, two idioms. [08](08-taskhub.md) carries the mirror-image
sentence — neither spec should be edited to match the other's convention.

### Template

Base it on **`evolve-crux`'s own PRD skeleton**, which is already in the project's voice and
already ties acceptance criteria to selftest asserts — not on anything from skills.sh.

Sections:

- **Context** — what forced this design
- **Out of scope** — an explicit fence *(see Borrowed, below)*
- **Design** — the substance
- **Considered options** — alternatives with why each lost
- **Consequences and known distortions** — what this design gets wrong on purpose
- **Supersedes / superseded by** — the chain

### Status lifecycle

`draft → active → superseded`. **An active RD is never amended in place.** A design change
writes a new RD that supersedes the old one, and the chain is the reasoning history.

This is the direct fix for q21's 18 `AMENDED` markers, which exist because the body was
treated as the only durable record.

### When a node earns an RD

Without an explicit filter, every node grows one. An RD is warranted when **at least one** of:

- the node's design would exceed the 400-word prose cap on its own
- the design makes a choice that a reader would otherwise re-litigate (a rejected alternative
  worth recording)
- the design carries a known distortion that must travel with every result

Explicitly not warranted: a hypothesis whose design *is* its verifiables.

### `crux-rd` is a **skill**, not an agent

It fails the zero-context test. `crux-migrate`, `crux-close`, `crux-audit` and `crux-critic`
all take a concrete cold input — a repo path, a hypothesis id plus a results directory, a
vault, a draft. An RD writer does not: the design being written up lives in the conversation
that just happened with the PI. From a cold start it would either restate the node or
re-derive the design badly.

This was confirmed independently — mattpocock's `to-spec` skill exists for exactly this job
and describes itself as *"no interview, just synthesis of what you've already discussed."*
It ships `disable-model-invocation: true`, so it only fires when explicitly invoked. `crux-rd`
should do the same: the PI decides when a design has settled enough to write up.

*(`to-spec` is installed and tracked in `mehdiforoozandeh/skills` → `external-skills.txt` as
a reference implementation.)*

## Borrowed, and from where

| borrowed | source | why |
|---|---|---|
| immutability + supersession | `wshobson/agents@architecture-decision-records` (12.6K installs) — *"don't change accepted ADRs, write new ones to supersede them"* | direct fix for in-place amendment |
| an explicit write-vs-skip filter | same | ADRs have one; without it every node grows an RD |
| `Considered options` + "why this option won" | same | research reasoning lives in the rejected branch — q21 already records "two designs were considered and rejected" |
| `Out of scope` as a first-class field | `mattpocock/skills@to-spec` | q21's *"SCOPE FENCE — ABSOLUTE, binding on q21 and every child"* is exactly this, currently buried in prose |
| `disable-model-invocation: true` | same | the PI decides when a design is settled |

## Rejected alternatives

- **Installing an off-the-shelf spec skill.** Five registry searches; every spec/PRD-shaped
  skill is under 800 installs (`ghaida/intent@specify` at 752 is the best, most under 200).
  Only the ADR skill has real adoption at 12.6K, and ADR is *decision*-shaped — Decision
  Drivers, Considered Options, Consequences. An RD for h59 needs a probe ladder and an
  estimand, not "why we picked Postgres." Borrow the mechanics, not the field list.
- **`crux-rd` as an agent.** Fails rule 4 (assume zero context) and rule 5 (reusable prompts
  needing main-conversation context are skills).
- **RDs inside the roll-up tree.** They are documents, not evidence. Nothing about an RD
  should trip a review gate or move a verdict.
- **Multiple RDs per node.** Invites the same accretion in a new location. One node, one
  active RD, supersession for change.

## Open questions — both settled 2026-08-15

- **Cockpit surface → its own tab, reusing an extracted reader.** Sharing the Wiki tab behind
  a filter was cheaper and conceptually wrong: that tab's whole design rests on the one-way
  flow rule (literature in, project findings never), and an RD is the project's own design
  reasoning. The spec's *"reuse that reader — do not build a third"* is honoured by
  extracting the reader first and re-basing the wiki tab onto it; there is no shared reader
  today, only a wiki-shaped one. (PRD 07.3.)
- **An RD may attach to a question or a hypothesis.** q21 — a question — is the motivating
  case, so refusing questions would have excluded the node that forced the feature. The
  counter-argument is real but is a *skill* rule, not an engine refusal: crux's house style
  is to say the number out loud and let the PI decide, exactly as fan-out back-pressure does.
  The project root and syntheses do not carry RDs.

## Work items

- ☑ `rd/` directory, `type: rd` frontmatter, `templates/rd.md` from the evolve-crux PRD shape
- ☑ `crux rd <node> "<title>"` verb — creates + backlinks
- ☑ Generated `RD.md` index
- ☑ Structural lint in `validate --check=rd`: link resolves, the two ownership records agree,
  one active RD per node, supersession chain resolves and is acyclic
- ⛔ **~~superseded RDs are not edited~~ — retired on build (PI ruling D7).** The engine has no
  memory of a file's previous bytes, and the only mechanism available was a second
  engine-owned hash registry the spec never budgeted for. `git log -p rd/<slug>.md` is the
  audit trail instead — the same call [06](06-node-economy.md) §3 made when it sent decision
  history to git. Immutability is now a discipline the `crux-rd` skill teaches, not an
  invariant the engine enforces; that cost is recorded here so it is not rediscovered.
- ☐ Snapshot key + cockpit reader (reuse the wiki reader) — PRD 07.3, builds last
- ☑ `crux-rd` skill with `disable-model-invocation: true`
- ☑ The write-vs-skip filter, written into the skill

## Acceptance criteria

- `crux rd h59 "…"` creates `rd/<slug>.md` and a resolving backlink in `h59`.
- An RD does not appear in the roll-up, does not affect `ledger_counts`, and does not trip
  the review gate.
- `validate` errors on a dangling RD link, on two active RDs for one node, and on a cycle in
  the supersession chain.
- Moving q21's design into an RD brings q21 under the 400-word cap without losing content.
- `selftest.py` passes with a grown assert count.
