# Roadmap

In-repo backlog for `crux`. Epics group related work; checklists are the concrete
issues under each. Status: ☐ todo · ◐ in progress · ☑ done.

---

## Epic 1 — Graphical UI for crux  `ui`

**Goal:** a graphical interface over the crux vault (today it's CLI + markdown / Obsidian),
so a PI can drive the whole loop — browse the tree, open questions, tick verifiables,
close cases, and clear the review gate — without the terminal.

- ☑ **Decide stack & architecture** — Obsidian plugin vs standalone web app vs desktop (Tauri/Electron); write a short ADR capturing the choice and why. *(GUI v1 PRD chose a stdlib-served local web app — [`docs/prd/gui-v1.md`](docs/prd/gui-v1.md).)*
- ☑ **Engine JSON API** — have the engine emit machine-readable vault state (tree, ledgers, gate queue) so any UI consumes one stable interface instead of re-parsing markdown. *(`engine.snapshot` → `/snapshot.json`.)*
- ☑ **Interactive tree / graph view** — render the Question→Hypothesis constellation, status-colored, navigable; the visual heart of the product. *(the `crux serve` cockpit tree: pan / zoom / collapse / search / re-orient.)*
- ◐ **Node detail + edit** — create/edit Questions & Hypotheses, tick verifiables, write findings; all writes go through the engine (never hand-edit generated content). *(read-only detail shipped in GUI v1; editing is a deliberate v1 non-goal — mutations stay in the agent/CLI.)*
- ◐ **Review-gate inbox** — surface questions in `review`, with `answer` / `pursue` actions for the PI. *(the queue is surfaced read-only; `answer` / `pursue` still run via the agent/CLI.)*
- ◐ **Package & ship** — build + distribute (plugin release / hosted app / desktop bundle per the stack decision). *(Launch/lifecycle UX ships as the `crux-cockpit` skill — locate vault → fresh server → verified URL → stop/restart; plugin/desktop packaging still open.)*

*GUI v1 delivered as `crux serve` + `engine.snapshot` + the `webui/` frontend (read-only cockpit; editing and packaging remain).*

## Epic 2 — Marketing animation + README hero  `marketing`

**Goal:** a short programmatic (Remotion / React-video) explainer that shows what crux does,
rendered to video + GIF and embedded as the hero on the README and the repo's social preview.

- ☐ **Storyboard the explainer** (~30–60s) — narrative: open a Question → propose a Hypothesis → register verifiables → land a finding → roll up the ledger → answer the question; carry the Southern-Cross / navigation motif throughout.
- ☐ **Scaffold the Remotion project** (React/TypeScript) under `marketing/`.
- ☐ **Build the animation scenes** from the storyboard.
- ☐ **Render & optimize** — export MP4 + an optimized GIF/webp sized for README and web.
- ☐ **Embed the hero** — add to README top, and set the repo's GitHub social-preview image.

## Epic 3 — LLM wiki  `wiki`

**Goal:** a **literature** layer in the vault — a living, interlinked knowledge base of *prior*
knowledge (background, definitions, methods, SOTA, baselines, references) that the agent
compiles from PI-curated immutable sources and draws on, cross-linked with the crux-tree so
questions and hypotheses can cite and build on what's known. Knowledge flows **one way**:
literature → wiki → tree; a project's own findings never enter the wiki (this keeps provenance
clean and prevents the self-ingestion failure mode). Instantiates Karpathy's LLM-wiki pattern.

- ☑ **Define the wiki page** — `type: wiki` pages under `wiki/` (concept-slug filenames), parentless and outside the roll-up tree, linked via `[[wikilinks]]`; immutable sources under `raw/`.
- ☑ **Agent reads the wiki for context** — `WIKI.md` index + pages consulted when proposing questions/hypotheses; tree nodes may cite `[[wiki/page]]` (the crux-wiki skill).
- ☑ **Agent compiles the wiki from literature** — `crux ingest` registers a source; the agent compiles/updates pages that cite `raw/`. *(Amended: knowledge comes from curated literature, not from distilling the project's own findings — findings never enter the wiki.)*
- ☑ **Index & render** — engine-generated `WIKI.md` at the vault root (pages by category + source registry), byte-stable, without polluting the question/hypothesis tree; structural lint via `crux validate`.
- ☑ **Browse the wiki in the cockpit** — a `Wiki` tab in `crux serve`: explorer rail (virtual category folders + pinned index/log/schema/sources) + deterministic force-directed link graph (color = category, size = degree) + markdown reader with backlinks; `[[wiki/…]]` citations in the tree's detail pane jump straight into it. *(PRD: [`docs/prd/gui-wiki-tab.md`](docs/prd/gui-wiki-tab.md); `wiki` snapshot key + `/wiki/<slug>.json`.)*

*Delivered as the `crux-wiki` skill + engine `ingest`/`WIKI.md`/wiki-lint (ENGINE_VERSION 1.1).*

## Epic 4 — ERA: empirical program search  `era`

**Goal:** a sibling that evolves whole programs toward a **scalar objective** (Google's ERA /
Flat UCB Tree Search) — an LLM writes and rewrites complete candidate programs, a sandbox scores
each, and a flat PUCT bandit (FUTS) keeps a diverse population and picks what to improve next.
Where crux *organizes* a research program, ERA *optimizes* the cases inside it: point it at a
hypothesis with a measurable bar and it searches for a program that clears it, escaping local
optima and returning a portfolio of winners.

- ☐ **ERA ↔ crux contract** — how a hypothesis's verifiable / metric becomes an ERA scalar objective + sandboxed scorer, and how results return as `## Findings` + a headline metric.
- ☐ **Search loop** — the `generate_fn` / `execute_fn` interface, sandboxed scoring, and the FUTS / flat-UCB bandit over a program population (exploration vs. exploitation).
- ☐ **Portfolio output** — return a *diverse* set of high-scoring programs (not just the argmax) with scores + lineage, so the PI can choose.
- ☐ **Wire into the loop** — launch a search from a `running` hypothesis; record the winning program + metric back through `crux close`; running and the verdict stay under the PI's OK.
- ☐ **Package as the `era` skill.**

## Epic 5 — Autoresearch: autonomous experiment loops  `autoresearch`

**Goal:** drive the crux loop with far less turn-taking — an agent that proposes the next
question / hypothesis, registers verifiables, runs experiments, reads results, and rolls up the
ledger, iterating largely unattended — while the **human-in-charge gates stay intact** (the PI
still approves running an experiment and recording a verdict, and clears the review gate).

- ☐ **Autonomy envelope** — pin exactly which loop steps run unattended vs. still require PI approval (running + verdicts stay gated); a clear, auditable leash.
- ☐ **Proposer** — generate the next question / hypothesis + pre-registered verifiables from the current tree + wiki, prioritized by what most reduces uncertainty.
- ☐ **Runner** — launch and track experiments (local / SLURM), attach run links, detect completion.
- ☐ **Closer** — read results, tick verifiables, derive the verdict, roll up; surface to the PI at the review gate rather than self-answering.
- ☐ **Budget & stop** — per-round cost / compute caps and an explicit stopping condition so a loop can't run away.
- ☐ **Package as the `autoresearch` skill.**

---

> Mirroring to GitHub Issues later: each epic → one `epic`-labeled issue with the checklist
> as sub-issues (labels `ui` / `marketing` / `wiki` / `era` / `autoresearch`). This file stays the high-level source of truth.
