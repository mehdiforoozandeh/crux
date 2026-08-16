# Spec 08 — Taskhub

**Label:** `taskhub` · **Status:** ◐ in progress — 2.0–2.3 shipped (PRDs 08.0–08.5)
**Depends on:** [06 node economy](06-node-economy.md)
**Amended 2026-08-14:** experiments merged into this layer — see *Experiments are tasks*.
**Paired with:** [15 evidence semantics](15-evidence-semantics.md), which owns what an
experiment's results *mean*; this spec owns where they are stored.

## Goal

A durable, project-level work layer beside the tree and the wiki: a third cockpit tab holding
everything a research program has to **do** — data prep, infrastructure, code, manuscript
figures, and the experiments themselves — maintained automatically by agents across months
and many sessions, so nothing is forgotten.

The PI should be able to *view* it and never have to *manage* it.

## The dividing line

**Science goes in the tree. Doing goes in the taskhub.**

A task is an **action**. If it is a claim about the world that could be true or false, it is a
hypothesis and belongs in the tree. If it is work someone has to do, it is a task.

Task creation normally follows the tree — we open a question, design an experiment, and then
say *"to answer this we need to do X, Y, Z."* But that is the default path, not the only one.
Manuscript work, project scaffolding, and software-engineering chores are real work with no
question attached, and they belong here too.

## Experiments are tasks

*Added 2026-08-14, replacing a proposed separate experiment layer.*

An **experiment is a task whose output is evidence.** That is the entire difference. Strip
both records down and exactly one row differs:

| | ordinary task | experiment |
|---|---|---|
| is an action | ✓ | ✓ |
| many-to-many with tree nodes | ✓ | ✓ |
| owns its refs; the node gets a computed backlink | ✓ | ✓ |
| has dependencies | ✓ | ✓ — a pilot blocks the full run |
| status, and a required output on `done` | ✓ | ✓ |
| **what the output is** | a *thing* — a dataset, code, a figure | **evidence about a hypothesis** |

Two layers with one differing field is one layer. A separate experiment store was designed
and dropped; the rationale is under *Rejected alternatives*.

### The role is computed, never stored

A task **may** declare `hypothesis_refs` — the hypotheses it produces evidence about, and
what it concluded about each. **A task that declares them is an experiment.** Nothing is
stored to say so.

This is the same move this spec already makes for `blocked`, for the same reason: *a state
you can compute is a state that cannot drift.* There is no way to have an experiment that
forgot to be marked one, or a task mislabelled as an experiment.

### The hard line, restated

The original rule was *"a task may never create direction."* That was doing double duty and
breaks the first time someone observes that a run **is** a task. Replace it with:

> **Work never creates direction. Work produces outputs — and an output that is evidence
> about a hypothesis enters the gated tier.**

The line moves from *which layer* to *which output*, and it becomes computable:

| | gating |
|---|---|
| task with no `hypothesis_refs` | act-and-report, not PI-gated. Ticking "fetched the antibody lot" sets no direction and records no result. |
| task **with** `hypothesis_refs` | completing it is a verdict input. The PI accepts what it concluded, exactly as `answer` and `pursue` are accepted today. |

The moment a task would *open a question*, it still converts to a tree node and goes through
the gate. That part is unchanged.

### `experiment` is a reserved, computed category

Category stays exactly as designed below — a tag from a per-vault declared list, rendered as
the cockpit's visual language, one colour per kind (`data-acquisition`, `hpc-setup`,
`implementation`, `visualization`, `manuscript`, …).

**`experiment` is reserved.** It cannot be typed by hand; it is assigned by the engine to any
task carrying `hypothesis_refs`. Every other category is free-form from the declared list.
Without this, the one category with gating consequences would be the one category that can
drift.

### Decomposition, and why the PI is not spammed

An experiment breaks down into sub-tasks — acquire the data, implement the arm, run it, make
the figures — through the **existing `parent` link**. No new mechanism.

**Sub-tasks do not inherit the role.** Only the parent carries `hypothesis_refs`; the
children are ordinary tasks. Two consequences, both free:

- `blocked` already sequences the whole thing — the experiment is blocked until its children
  are `done`.
- **The gate fires once, when the experiment completes — not once per sub-task.** That is what
  keeps this layer's founding promise (*view it, never manage it*) intact after the merge.

### What the merge buys

1. **One dependency graph.** *"Dedupe the accessions → blocks the pilot → blocks the full
   run"* is one chain. Under two layers that chain crosses a store boundary and needs plumbing
   in both directions.
2. **One frontier query.** *"What can I do right now"* spans chores and experiments, which is
   the question a PI actually asks. Two frontiers would need merging by hand every time.
3. **The experiment timeline is a view, not a tab** — the same records, filtered to those with
   `hypothesis_refs`, ordered by time. That is the one question the tree structurally cannot
   answer (*what did we actually run, when, and what did it conclude*), and it costs a filter
   rather than a fourth tab.

## Motivation

Every work item in the CANDI vault currently lives buried in node prose: *"any re-bake
motivated by h57 or h62 must deliberately include replicate cells"*, *"h59's runner now
deduplicates at the record level"*, *"the extra 13 are to be enumerated."* That is a third of
why q21 is 5,725 words — the node is doing triple duty as design doc, task list, and
changelog ([06](06-node-economy.md)).

## Design

### 1. Taskhub is a **source** artifact, never derived

This is the load-bearing decision and it is the direct lesson from spec-kit (see Prior art).
spec-kit's `tasks.md` is generated from the spec, and its documented "living spec" workflow
**regenerates it**, destroying checkbox state. That is flatly incompatible with "nothing gets
forgotten across months."

So: **the tree can trigger a task; it can never own one.** Nothing regenerates the taskhub.

### 2. Structure — a graph with a category view, not a tree

Two things get conflated and must not be:

- **Category** — `data`, `architecture`, `training-loop`, `manuscript`. These are *not*
  actions, so by the rule above they are not tasks. Category is a **tag**, drawn from a
  per-vault declared list. Precedent: `wiki_schema.md`'s "categories in use," co-evolved by
  PI and agent so pages stay consistent. Without a declared list you get `data-prep`,
  `datasets` and `data-related` as siblings after six months.
- **Decomposition** — "implement and test JEPA training" genuinely breaks into sub-actions.
  This is a real parent link.

The cockpit renders category as the top level of the tree. That is a **view**, not stored
structure.

### 3. Links: the task owns them

A task may serve many nodes — dataset prep feeds ten hypotheses. The link must be
authoritative in exactly one place or it drifts.

**The task carries its refs. Node → task is a computed backlink**, exactly as the wiki tab
already does. Consequences: many-to-many is free, and adding a task never edits a tree node.

Full traversability is the point — task ↔ node ↔ wiki page ↔ artifact ↔ code should all
resolve, so "investigate h59" can surface what was done for it, what was cited, and what it
produced.

**This is deliberately not the idiom [07](07-rd-layer.md) uses, and neither is a drift bug.**
*Node-tree lineage is written in node files; the task graph is derived.* A written link
(`Parent::`, `Related::`, 07's `RD::`) is one-to-one, written once, effectively permanent,
**rendered by Obsidian into the graph** — which is why `Parent::` is a body line and not
merely frontmatter — and cross-checked by `validate` against frontmatter. A task backlink is
the opposite on every axis: many-to-many, churning weekly, with one source and nothing to
cross-check. Writing it would mean every `crux task add` edits N node files, which this
section forbids and which is exactly what makes many-to-many free. The discriminator is
**cardinality and churn**, not house style. Do not "fix" either layer toward the other.

### 4. What gets in

> **Would you be annoyed if this vanished next week?**

If yes, it belongs in the taskhub, however small — *"fetch antibody lot from the ENCODE
portal"* passes. If no, it is session scratch — *"re-read h59's verifiables"* — and stays in
the agent's own todo list, which may point *at* a taskhub item as its parent but never lands
in the vault.

Granularity is otherwise unbounded downward. Tasks can be fine-grained; they cannot be
ephemeral. Operational rule of thumb, from `to-tickets`: **a task should fit within a single
context window.**

Also excluded: anything that *is* a hypothesis, and anything a verifiable already covers.

### 5. Status

Four states: `open` · `done` · `dropped` · `blocked`.

- **`blocked` is computed, never stored** — derived purely from *dependency on another task*.
  A state you can compute is a state that cannot drift.
- **External blockers become tasks.** "Waiting on cluster quota" is not a blocked state, it is
  a dependency on a task called "obtain cluster quota." This keeps the rule single and fits
  "tasks are actions."
- **`done` hard-requires an output ref**, and the engine verifies it resolves. An action that
  completed almost always produced something — code at a path, a dataset, a figure — and a
  bare ticked box discards exactly the thing that makes the layer traversable.

Task state is **not PI-gated** — *unless the task carries `hypothesis_refs`*. Ticking
"fetched the antibody lot" sets no direction, spends no compute and records no scientific
result, so it sits in the act-and-report tier with `status` and `validate`. That is what
makes "the PI needn't be concerned about it" legal rather than a leash violation.

Completing an **experiment** is different: its output is a verdict input, so it is PI-gated.
See *The hard line, restated* above. Because only the parent of a decomposition carries
`hypothesis_refs`, this costs one gate per experiment, not one per sub-task.

**The hard line: work never creates direction.** The moment a task would open a question, it
converts to a tree node and goes through the gate.

### 6. Navigation

Taskhub could reach hundreds of items. The agent's access pattern is **query, not browse**.

The rule, from `to-tickets`: **work the frontier** — tasks whose blockers are complete. Plus
"what is open under q21" and "what blocks anything currently running."

The wiki already taught this lesson the hard way: its index resolved *pages* while queries
were pitched at sub-page granularity, so retrieval fell back to grep ([03](03-llm-wiki.md)).
Design the taskhub index for the queries actually made against it.

### 7. Fields

- `id` — engine-allocated, immutable, never renumbered
- `title` — imperative, verb + object
- `category` — from the declared list; `experiment` is reserved and computed
- `parent` — optional, decomposition only
- `blocked_by` — **mandatory**, task ids or the literal `None`, so a missing edge is a visible
  omission rather than silence *(from `to-tickets`)*
- `refs` — tree nodes / wiki pages this serves
- `hypothesis_refs` — optional. Hypothesis ids **plus what this task concluded about each**,
  in [15](15-evidence-semantics.md)'s verdict tokens — `supported` / `refuted` /
  `inconclusive` / `invalid-run`; `partial` is retired there and refused here.
  Present ⇒ this task is an experiment.
- `status` — `open` / `done` / `dropped` (`blocked` is computed)
- `output` — required when `done`; must resolve

**No file path is required.** spec-kit *rejects* a task without one; `to-tickets` says paths
go stale. For research work — cluster jobs, dataset registrations, portal fetches, manuscript
figures — `to-tickets` is right.

### Why `hypothesis_refs` carries a per-hypothesis conclusion

One experiment can say **different things about different hypotheses** — a pilot may conclude
`supported` for h44 and `refuted` for h45. A bare list of ids cannot record that, so the conclusion rides on the
ref itself, one line per hypothesis. This is the *only* structured place that fact exists;
without it the experiment timeline cannot be rendered and no check can be written against it.

A third record type — one file per (hypothesis, experiment) pair, carrying its own direction
and strength — was considered and deferred. See *Rejected alternatives*.

## Prior art — spec-kit (`github/spec-kit`)

Researched at the PI's direction. The pipeline is
`/speckit.constitution → specify → clarify → checklist → plan → tasks → analyze → implement → converge`,
with deterministic bash/PowerShell/Python scripts handling numbering, slugs and path
resolution, and the LLM writing all content.

### Transfers

- **The deterministic/LLM split as a shape — plus its own correction.** spec-kit scripts
  feature-directory numbering and then stops: task IDs, dependency consistency, ID uniqueness
  across appends and status transitions are all left to LLM discipline. Those are exactly the
  things that rot over months. In crux they belong in the engine.
- **Runtime resolution over materialized propagation.** spec-kit *built* constitution
  propagation into templates, removed it, and documented why: *"Materialized copies can
  drift… anything propagated is a snapshot"*, and *"a pre-filled Constitution Check can bias
  `/plan`."* Taskhub reads project rules live at generation time and never copies them into
  task files.
- **Append-only convergence with immutable IDs and `source-ref`.** Never rewrite, renumber,
  reorder or delete an existing task; append; leave the file byte-for-byte unchanged when
  there is nothing to add. Every appended task carries a ref tracing its origin — which maps
  almost one-to-one onto our `refs` field, and unlike spec-kit's version ours is
  deterministically checkable.
- **A tiny persisted pointer** (`.specify/feature.json`) as cross-session memory. Cheap and
  effective; ours would hold a set rather than a scalar.

### Do **not** copy

Recorded so this is not re-litigated:

| rejected | why |
|---|---|
| regenerating the task file from an upstream artifact | destroys state — the one thing that cannot happen |
| single-active-feature (`feature.json` holds one pointer; concurrency handled by git worktrees) | a research taskhub is inherently multi-stream |
| `[P]` file-disjointness parallelism | a build-scheduler concept; research parallelism is governed by GPU/SLURM contention and result dependency |
| the user-story spine — P1/P2/P3, MVP-first, per-group `Independent Test`, `Checkpoint` | encodes incremental shippable value, which research does not have |
| mandatory file path per task | goes stale; many research tasks have no repo path |
| test-first ordering as a universal rule | presumes you know the answer before running |
| `unrequested` as a defect class, "no speculative features" | in research, unrequested work is frequently the finding |
| the terminal `converged` state | research has no finish line |
| the bare markdown checkbox as status primitive | two states, no result, no timestamp, no provenance, mutated by LLM string replacement — the weakest single choice in their design |
| mandatory independence between work items | spec-kit forbids cross-story dependencies; one data-prep task feeding ten hypotheses is precisely our normal case |

One structural aside worth heeding: spec-kit's command prompts are 50–60% boilerplate —
~40 lines of near-identical hook-dispatch instructions per file. A live demonstration of what
happens when orchestration logic that should be code is expressed as prompt text.

## Rejected alternatives (ours)

- **A separate experiment layer.** Designed in full, then merged here. Two record types
  differing in exactly one field are one record type, and keeping them apart cost a split
  dependency graph, a split frontier query, and a boundary every "the run is also a task"
  conversation had to cross. The merge also made the gating rule *computable* rather than a
  judgment about which store something belongs in.
- **A reified link record — one file per (hypothesis, experiment) pair**, carrying its own
  direction, strength and provenance. This is the strongest signal in the prior-art survey:
  SEPIO's *evidence line*, W3C PROV's `prov:Usage` + `hadRole`, RO-Crate's `ControlAction` and
  the Micropublications SupportGraph all converged on it independently, and GrowthBook ships a
  commercial version (`supportingExperimentIds[]` / `contradictingExperimentIds[]`). It buys
  one thing the per-ref conclusion cannot: **re-grading an old run under a new criterion, or
  versioning a judgment, without editing either file.** Deferred rather than rejected — the
  benefit is real but so far hypothetical, and a third file type is a large cost to pay for
  it. Revisit the first time someone genuinely needs to re-grade. Full survey in
  [`research/research-prior-art-experiment-model.md`](research/research-prior-art-experiment-model.md).
- **Taskhub as a projection of the tree.** Derived state cannot hold months of history.
- **Storing `blocked`.** Computable, therefore driftable if stored.
- **Storing `is_experiment` as a flag, or letting `experiment` be a hand-typed category.**
  Same objection as storing `blocked`, with higher stakes: it is the one category that changes
  whether the PI gets asked.
- **Storing a separate external-blocked state with a reason string.** Considered and dropped
  — externalities become tasks instead, which keeps one rule instead of two.
- **An `active` / in-progress state.** Durable only when it means "SLURM job 4012 is running,"
  which is a run link, not a status. Dropped.
- **Free-form nesting where the agent invents category parents.** Guarantees taxonomy drift.
- **Persisting session scratch so the PI can see what the agent did.** That is the transcript's
  job; persisting it fills the vault with dead micro-items.

## Open questions

- Maximum decomposition depth, if any.
- Whether the declared category list is seeded at `init` or grows on first use with PI
  approval.
- Whether `dropped` needs a reason field.
- Storage shape: one file per task (like wiki pages) vs one `TASKS.md` with a stable grammar.
  One-file-per-task fits the "engine owns IDs, never renumbers" rule better and makes git
  history per-task; a single file is easier to read raw. **The merge pushes toward one file
  per task**: an experiment carries a methodology section and sub-tasks, which is more than a
  line in a shared file wants to hold.
- Whether an experiment may be `dropped` after producing partial evidence, and what that does
  to the hypotheses it refs.
- Whether the reified evidence-line record (see *Rejected alternatives*) ever becomes
  necessary.

## Work items

- ☑ Task schema + storage layout + declared category list, `experiment` reserved
- ☑ `hypothesis_refs` with per-hypothesis conclusion; `is_experiment` computed from it
- ☑ Engine: ID allocation (immutable, never renumbered), `blocked` computation, dependency
  cycle detection, `done`-requires-resolving-output check
- ☑ Gating split: completing a task with `hypothesis_refs` is PI-gated; without, it is not
- ☑ `crux task` verbs — add / done / drop / list / show / categories / review / accept, and the frontier query
- ☑ Backlink computation: node → tasks, wiki → tasks; hypothesis → experiments
- ☑ `TASKHUB.md` generated index, shaped for the frontier query
- ☑ Structural lint in `validate`
- ☑ Snapshot key + cockpit tab: one list, status filters, **one colour per category** as the
  visual language, and a chronological experiment view (filter to `hypothesis_refs` present)
- ☑ Skill rules: what gets in, when status changes, the "work never creates direction" line

## Acceptance criteria

- A task can reference several tree nodes; each of those nodes shows it as a backlink; adding
  the task modified no node file.
- `blocked` is never stored and always agrees with the dependency graph.
- `done` with an unresolvable output ref fails `validate`.
- The frontier query returns exactly the open tasks whose blockers are all **cleared**
  (`done` **or** `dropped` — a drop is a decision not to do the work, and leaving the
  dependent blocked forever would strand it invisibly inside this very query; the promotion
  is reported as `info`), and spans ordinary tasks and experiments in one result.
- A dependency cycle is caught deterministically.
- Task IDs survive add / drop / re-parent without renumbering.
- `is_experiment` is nowhere stored, and always equals "has `hypothesis_refs`".
- `--category=experiment` is refused; the category appears only on tasks with
  `hypothesis_refs`.
- One experiment with three sub-tasks fires **one** review gate, on the parent.
- An experiment refs two hypotheses with opposite conclusions, and both are rendered
  correctly on their nodes and in the timeline view.
- `selftest.py` passes with a grown assert count.
