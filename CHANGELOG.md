# Changelog

All notable changes to crux. Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
the engine version (`ENGINE_VERSION`, stamped into every vault) bumps when the vault format or
verdict/roll-up/view logic changes.

## [Unreleased]

## [0.3.0] - 2026-07-11

Two headline additions — a **browser GUI** (Epic 1) and a **literature wiki** (Epic 3).

### Added

- **`crux serve` — a read-only browser cockpit (Epic 1, GUI v1).** A new `serve` verb boots a
  stdlib HTTP server on `127.0.0.1` (auto-selected free port; `--port` / `--open` / `--no-open`),
  prints one clickable `http://localhost:<port>` URL, and opens context-aware across a plain
  terminal / VS Code / Remote-SSH. It serves a no-build vanilla-JS frontend (`webui/`): a
  deterministic, status-colored crux-tree you can pan, zoom (mouse **and** trackpad), collapse /
  expand, search-to-jump, and re-orient (left-right ↔ top-down), in a full-text (default) or
  compact node view, with a **focus-open** mode that collapses every settled question in one
  click; plus a contextual right pane — the review queue by default, a read-only node detail on
  click — with an adjustable text size. Dark (default) and light Obsidian-like themes, each
  concept a unique status color. It live-refreshes from `/snapshot.json` (~1s poll) with stable
  node positions and performs **no writes** — every mutation still goes through the agent/CLI.
  Delivers Epic 1 #2 and #3, and the read halves of #4 and #5.
- **Engine JSON API — `engine.snapshot(vault) -> dict`**, served at `/snapshot.json`: the single
  machine-readable view of a vault (`engine_version`, `project`, `nodes`, `tree`, `queue`).
  Pure-read, stdlib-only, additive. `ledger_block` and `snapshot` share one `ledger_counts`
  roll-up so their numbers cannot drift. (Epic 1 #2.)
- **Literature wiki (Epic 3).** A PI-curated literature layer beside the question / hypothesis
  tree, instantiating Karpathy's LLM-wiki pattern: immutable sources under `raw/`, agent-compiled
  pages under `wiki/`, a new `crux ingest` verb (records source sha256, appends a greppable
  `wiki/log.md` line), an engine-generated `WIKI.md` index, and structural wiki lint folded into
  `crux validate` (broken / flow links, orphans, missing frontmatter, uncompiled or missing
  sources, source-hash drift). Knowledge flows one way — literature → wiki → tree; a project's own
  findings never enter the wiki. New sibling skill **crux-wiki** carries the agent-side
  conventions (compile / query / semantic lint).

### Changed

- `ENGINE_VERSION` → **1.1** — additive only (the wiki's `WIKI.md` / `raw/` layout and the
  read-only snapshot API). Pre-wiki vaults load unchanged and stand up the wiki lazily on first
  ingest; no migration required. `crux validate` now also runs the wiki structural lint.

[0.3.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.3.0
