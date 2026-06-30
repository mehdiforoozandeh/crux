---
name: crux
description: >-
  An agentic research companion — a scientific-method lab notebook for navigating
  large research programs. Organize work as a tree of Questions (what we don't know)
  and falsifiable Hypotheses (testable leaves), each with pre-registered verifiables
  and findings; a deterministic engine rolls results up into per-question answers,
  trips a human review gate, and regenerates an Obsidian-graphable META + experiments
  registry. Use when the user wants to run a research program rigorously: open/track
  research questions, design experiments as problem-statement → hypothesis → verifiables
  → findings, synthesize results, and update the open questions. Triggers: crux,
  "open a research question", "lab notebook", "hypothesis/experiment tracking",
  "design an experiment", "what should we try next", "research notebook", scientific
  method, meta-questions, Obsidian research vault.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  notice: "Bundled engine is original MIT work; no third-party code."
---

# crux — an agentic research companion

`crux` turns a research program into a **scientific-method lab notebook**: a tree of
**Questions** (what we don't know) and **Hypotheses** (falsifiable, testable leaves),
rooted at a **Project**. A deterministic engine (`scaffold/`, a Python CLI) does the
bookkeeping — IDs, the `Parent::` tree, validators, the evidence-ledger roll-up, the
review gate, and regenerating `META.md` + `EXPERIMENTS.md`. The vault is plain markdown,
openable in Obsidian (graph mode shows the question/hypothesis tree).

You (the Agent) operate the engine on the researcher's behalf. The engine never judges;
**you** supply the science and the researcher (the **PI**) makes the calls.

## When to use this

The user is running a research program and wants it tracked rigorously: opening research
questions, designing experiments as problem → hypothesis → verifiables → findings,
recording results, deciding when a question is answered, and updating what's still open.
Not for one-off tasks with no hypothesis, and not for launching the runs themselves
(crux *records* runs; your training/job harness launches them).

## The model

- **Project** — the root node, one per vault.
- **Question** (`q*`) — has **no verifiables of its own**; it is resolved by **aggregating
  its children's findings**. Questions nest (a question's parent can be another question).
- **Hypothesis** (`h*`) — a falsifiable leaf under a question, with `## Verifiables`
  (pre-registered checks) and `## Findings`. The only thing actually tested by runs.

A hypothesis's `## Findings` can spawn **new** child questions — that's the loop reopening.
The tree is the `Parent:: [[…]]` wikilink in each file; `META.md`/`EXPERIMENTS.md` are
generated views (never hand-edit).

**Lifecycles**
- Hypothesis: `idea → staged → running → done`. Verdict is **derived on close** from the
  verifiable checkboxes: all `- [x]` → `supported`; any unmet → `refuted`/`partial`;
  only `- [-]` (couldn't-evaluate) remaining → `inconclusive`.
- Question: `open → review → resolved`. The engine trips `open → review` automatically
  once every direct child is terminal. **Closing it is always the PI's call.**

## Three roles — and the leash

- **Engine (○ deterministic).** Bookkeeping only — never judges, never reads run logs.
- **Agent (◆ judgment, drafts).** You: phrase questions, write hypotheses + verifiables,
  turn run results into a per-box verdict + headline metric, draft interpretations.
- **PI (◆ judgment, decides).** The human: which questions matter, which hypotheses are
  worth a run, the verifiable bar, and the close/reopen call.

**Leash rule** — how much you do before checking with the PI:
- **○ + `test`** (mechanical / evidence-grounded): act, then report.
- **◆ that set direction or write a verdict** (`ask`, `hypothesize`, `close`, `answer`,
  `pursue`): **propose → PI confirms → then write**.
- **`review` gate**: always the PI's. Surface it; never self-close a question.

## The verbs

Run them via the engine CLI (see `scaffold/README.md`). `◆` = you draft + PI confirms; `○` = act-and-report.

| verb | aliases | role | what it does |
|------|---------|------|--------------|
| `init` | start, new | ○ | bootstrap a vault |
| `ask` | question, q, meta | ◆ | open a Question under the project or another question |
| `hypothesize` | hypothesis, idea | ◆ | add a hypothesis under a question — **register `-v` verifiables** |
| `test` | experiment, run, stage, launch | ○ | `idea → staged → running`, attach a run link |
| `close` | record, conclude, verdict, land | ◆ | derive verdict from verifiables + write findings → roll up |
| `review` | gate, decide | ○ | list questions awaiting the PI's decision |
| `answer` | resolve, settle | ◆ | PI resolves a question with a standing answer |
| `pursue` | branch, extend, reopen | ◆ | keep a question open; optionally spawn a fresh hypothesis |
| `status` | map, tree, where, show | ○ | print the tree / a node's ledger |
| `synthesize` | weave, rollup | ◆ | optional horizontal synthesis across questions |
| `validate` | lint, check | ○ | integrity checks |

## How you run a session

You are a conversational front-end to the engine. Translate the PI's natural language into
the right verb, **propose** the concrete node, get a yes, **then** run the command. Keep the
science explicit and falsifiable.

> **PI:** I think JEPA pretraining could help.
> **You:** That's a *Question* (no single verifiable). Open it under the project as
> *"Can JEPA pretraining improve CANDI?"* — yes?
> **PI:** yes
> **You:** → `crux ask "Can JEPA pretraining improve CANDI?"` (`q1`). First hypothesis under it?
> **PI:** masked-token beats masked-stem.
> **You:** Verifiable bar — I'd set *imp-Spearman ≥ +0.01 vs the stem baseline on held-out*. Good, or tighter?
> **PI:** good
> **You:** → `crux hypothesize "masked-token beats masked-stem" -p q1 -v "imp-Spearman ≥ +0.01 vs stem"`

**Granularity:** per-node confirm by default; when the PI says "draft me the next N," batch-propose a
sub-tree (a question + several hypotheses + verifiables) and let them approve/edit it as one block.

**Closing a case:** read the run results, tick each verifiable in the idea's `## Verifiables`
(`- [x]`/`- [ ]`/`- [-]`), write a one-paragraph `## Findings`, then `crux close h1 -m "<metric>"`.
The engine derives the verdict and rolls it up.

**At a `review` gate:** present the question's ledger and your read of the evidence, then let the PI
choose `answer` (resolve) or `pursue` (keep digging). Never decide for them.

## Guardrails

- **Pre-register verifiables.** A hypothesis isn't testable until its `## Verifiables` state a metric +
  baseline + threshold. The engine refuses to mark an idea `running` with none.
- **Never hand-edit generated content** — `META.md`, `EXPERIMENTS.md`, or the `<!-- crux:ledger -->`
  block inside a question. Run a verb and let the engine regenerate. You *do* write the question's
  `## Answer so far` prose (above the ledger) and the idea's `## Findings`.
- **The engine is domain-agnostic.** It never parses logs/metrics — you supply the per-box verdict and
  a headline metric string. This is what keeps crux reusable across projects.
- **One parent per node** (it's a tree). Use extra `[[links]]` for "see also" — they show in the graph
  but don't affect roll-up.

## Running the engine

```bash
cd <vault>                       # or anywhere under it; the engine finds .crux.yaml upward
python <skill>/scaffold/crux.py <verb> [...]   # --help on every verb
```
A vault is created by `init` and contains: the project node, `q*`/`h*` node files, optional
`synthesis_*`, the generated `META.md` + `EXPERIMENTS.md`, and `.crux.yaml` (config + ID counters).

**Validate the install:** `python scaffold/selftest.py` builds a dummy vault and asserts every
invariant (roll-up, gate, idempotency, integrity, CLI help) — no GPU/tokens/SLURM. Add `--keep ./demo`
to keep the vault and open it in Obsidian.

## `scaffold/`
`crux.py` (CLI) · `engine.py` (model, validators, ledger, gate, transitions) · `render.py`
(generated views) · `templates/` (node skeletons — editable) · `selftest.py` · `README.md` (CLI reference).
