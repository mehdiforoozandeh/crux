# Roadmap

In-repo backlog for `crux`. Epics group related work; checklists are the concrete
issues under each. Status: ☐ todo · ◐ in progress · ☑ done.

---

## Epic 1 — Graphical UI for crux  `ui`

**Goal:** a graphical interface over the crux vault (today it's CLI + markdown / Obsidian),
so a PI can drive the whole loop — browse the tree, open questions, tick verifiables,
close cases, and clear the review gate — without the terminal.

- ☐ **Decide stack & architecture** — Obsidian plugin vs standalone web app vs desktop (Tauri/Electron); write a short ADR capturing the choice and why.
- ☐ **Engine JSON API** — have the engine emit machine-readable vault state (tree, ledgers, gate queue) so any UI consumes one stable interface instead of re-parsing markdown.
- ☐ **Interactive tree / graph view** — render the Question→Hypothesis constellation, status-colored, navigable; the visual heart of the product.
- ☐ **Node detail + edit** — create/edit Questions & Hypotheses, tick verifiables, write findings; all writes go through the engine (never hand-edit generated content).
- ☐ **Review-gate inbox** — surface questions in `review`, with `answer` / `pursue` actions for the PI.
- ☐ **Package & ship** — build + distribute (plugin release / hosted app / desktop bundle per the stack decision).

## Epic 2 — Marketing animation + README hero  `marketing`

**Goal:** a short programmatic (Remotion / React-video) explainer that shows what crux does,
rendered to video + GIF and embedded as the hero on the README and the repo's social preview.

- ☐ **Storyboard the explainer** (~30–60s) — narrative: open a Question → propose a Hypothesis → register verifiables → land a finding → roll up the ledger → answer the question; carry the Southern-Cross / navigation motif throughout.
- ☐ **Scaffold the Remotion project** (React/TypeScript) under `marketing/`.
- ☐ **Build the animation scenes** from the storyboard.
- ☐ **Render & optimize** — export MP4 + an optimized GIF/webp sized for README and web.
- ☐ **Embed the hero** — add to README top, and set the repo's GitHub social-preview image.

## Epic 3 — LLM wiki  `wiki`

**Goal:** a wiki layer in the vault — a living, interlinked knowledge base the agent maintains
and draws on (background, definitions, methods, prior findings, references), cross-linked with
the crux-tree so questions and hypotheses can cite and build on accumulated knowledge.
*(Early — scope to firm up.)*

- ☐ **Define the wiki note** — its node type / area in the vault and how it links to Questions & Hypotheses (`[[wikilinks]]`, Obsidian-graphable like the rest).
- ☐ **Agent reads the wiki for context** — pull relevant wiki notes when proposing questions/hypotheses, so work builds on what's known.
- ☐ **Agent writes the wiki** — distil durable knowledge out of findings into wiki notes (promote one-off findings into reusable background).
- ☐ **Index & render** — a wiki index (and/or surface in `META.md`) without polluting the question/hypothesis tree.

---

> Mirroring to GitHub Issues later: each epic → one `epic`-labeled issue with the checklist
> as sub-issues (labels `ui` / `marketing` / `wiki`). This file stays the high-level source of truth.
