# Spec 01 — Graphical UI for crux

**Label:** `ui` · **Status:** ◐ in progress

## Goal

A graphical interface over the crux vault (natively it is CLI + markdown / Obsidian),
so a PI can drive the whole loop — browse the tree, open questions, tick verifiables,
close cases, and clear the review gate — without the terminal.

## Delivered

GUI v1 shipped as `crux serve` + `engine.snapshot` + the `webui/` frontend: a
read-only cockpit. Editing and packaging remain open.

## Work items

- ☑ **Decide stack & architecture** — Obsidian plugin vs standalone web app vs desktop
  (Tauri/Electron); short ADR capturing the choice and why.
  *(GUI v1 PRD chose a stdlib-served local web app — [`docs/prd/gui-v1.md`](../docs/prd/gui-v1.md).)*
- ☑ **Engine JSON API** — the engine emits machine-readable vault state (tree, ledgers,
  gate queue) so any UI consumes one stable interface instead of re-parsing markdown.
  *(`engine.snapshot` → `/snapshot.json`.)*
- ☑ **Interactive tree / graph view** — the Question→Hypothesis constellation,
  status-colored and navigable; the visual heart of the product.
  *(the `crux serve` cockpit tree: pan / zoom / collapse / search / re-orient.)*
- ◐ **Node detail + edit** — create/edit Questions & Hypotheses, tick verifiables, write
  findings; all writes go through the engine (never hand-edit generated content).
  *(Read-only detail shipped in GUI v1; v0.5 added fully-rendered markdown, linked evidence
  artifacts, and an in-pane report reader with figures —
  [`docs/prd/v0.5-cockpit-evidence.md`](../docs/prd/v0.5-cockpit-evidence.md). Editing is
  still a deliberate non-goal — mutations stay in the agent/CLI.)*
- ◐ **Review-gate inbox** — surface questions in `review`, with `answer` / `pursue` actions
  for the PI. *(The queue is surfaced read-only; `answer` / `pursue` still run via the
  agent/CLI.)*
- ◐ **Package & ship** — build + distribute (plugin release / hosted app / desktop bundle
  per the stack decision). *(Launch/lifecycle UX ships as the `crux-cockpit` skill — locate
  vault → fresh server → verified URL → stop/restart; plugin/desktop packaging still open.)*

## Incoming work from other specs

Three later specs add surface to the cockpit and should be built against it rather than
alongside it:

- **[06 node economy](06-node-economy.md)** — the detail pane must lead with a node's
  `## ELI5` / `## TL;DR` and collapse the rest. Today `_node_json` sets a question's
  `detail` to the *entire* `## Question` section, which is why a 5,700-word node is
  unreadable in the pane.
- **[07 RD layer](07-rd-layer.md)** — RDs need a reader. Reuse the wiki tab's markdown
  reader rather than building a third one.
- **[08 taskhub](08-taskhub.md)** — a third tab beside Tree and Wiki, with status filters.

## Open questions

- Whether editing ever moves into the cockpit, or stays permanently agent/CLI-only. The
  current answer is "deliberate non-goal," but the review-gate inbox is the case that
  most strains it — clearing a gate is two clicks and a sentence.
- Packaging target. Unresolved since the v1 PRD.
