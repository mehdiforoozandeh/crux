# Spec 08 — Taskhub

**Label:** `taskhub` · **Status:** ☐ todo
**Depends on:** [06 node economy](06-node-economy.md)

## Goal

A durable, project-level task layer beside the tree and the wiki: a third cockpit tab holding
the **implementation legwork** of a research program — data prep, infrastructure, code,
manuscript figures — maintained automatically by agents across months and many sessions, so
nothing is forgotten.

The PI should be able to *view* it and never have to *manage* it.

## The dividing line

**Science goes in the tree. Software and implementation go in the taskhub.**

A task is an **action**. If it is a claim about the world that could be true or false, it is a
hypothesis and belongs in the tree. If it is work someone has to do, it is a task.

Task creation normally follows the tree — we open a question, design an experiment, and then
say *"to answer this we need to do X, Y, Z."* But that is the default path, not the only one.
Manuscript work, project scaffolding, and software-engineering chores are real work with no
question attached, and they belong here too.

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

Task state is **not PI-gated**. Ticking "fetched the antibody lot" sets no direction, spends
no compute and records no scientific result, so it sits in the act-and-report tier with
`status` and `validate`. That is what makes "the PI needn't be concerned about it" legal
rather than a leash violation.

**The hard line: a task may never create direction.** The moment a task would open a question
or launch a run, it converts to a tree node and goes through the gate.

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
- `category` — from the declared list
- `parent` — optional, decomposition only
- `blocked_by` — **mandatory**, task ids or the literal `None`, so a missing edge is a visible
  omission rather than silence *(from `to-tickets`)*
- `refs` — tree nodes / wiki pages this serves
- `status` — `open` / `done` / `dropped` (`blocked` is computed)
- `output` — required when `done`; must resolve

**No file path is required.** spec-kit *rejects* a task without one; `to-tickets` says paths
go stale. For research work — cluster jobs, dataset registrations, portal fetches, manuscript
figures — `to-tickets` is right.

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

- **Taskhub as a projection of the tree.** Derived state cannot hold months of history.
- **Storing `blocked`.** Computable, therefore driftable if stored.
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
  history per-task; a single file is easier to read raw.

## Work items

- ☐ Task schema + storage layout + declared category list
- ☐ Engine: ID allocation (immutable, never renumbered), `blocked` computation, dependency
  cycle detection, `done`-requires-resolving-output check
- ☐ `crux task` verbs — add / link / done / drop, and the frontier query
- ☐ Backlink computation: node → tasks, wiki → tasks
- ☐ `TASKHUB.md` generated index, shaped for the frontier query
- ☐ Structural lint in `validate`
- ☐ Snapshot key + cockpit tab with status filters (show/hide per state)
- ☐ Skill rules: what gets in, when status changes, the "never creates direction" line

## Acceptance criteria

- A task can reference several tree nodes; each of those nodes shows it as a backlink; adding
  the task modified no node file.
- `blocked` is never stored and always agrees with the dependency graph.
- `done` with an unresolvable output ref fails `validate`.
- The frontier query returns exactly the open tasks whose blockers are all `done`.
- A dependency cycle is caught deterministically.
- Task IDs survive add / drop / re-parent without renumbering.
- `selftest.py` passes with a grown assert count.
