# Changelog

All notable changes to crux are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/); the engine version
(`ENGINE_VERSION` in `engine.py`) is bumped only when vault format or
verdict/roll-up/view logic changes.

## [Unreleased]

- **`crux serve` — a read-only browser cockpit.** New `serve` verb boots a stdlib
  HTTP server bound to `127.0.0.1` on an auto-selected free port (`--port` to pin;
  `--open`/`--no-open`), prints one clickable `http://localhost:<port>` URL, and opens
  context-aware across plain terminal / VS Code / Remote-SSH (VS Code port-forwarding +
  Simple Browser hint; no browser spawned on a remote). Serves a no-build static frontend
  (`webui/`): a deterministic hierarchical crux-tree (root → Questions → Hypotheses,
  status-colored, zoom/pan/collapse/search, synthesis nodes on dashed edges) plus a
  contextual right pane (review queue by default, node detail on click), live-refreshing
  from `/snapshot.json` (~1s poll) with stable node positions. View-only: the GUI performs
  no writes. Delivers ROADMAP Epic 1 #3, #5, and the read half of #4. (stdlib-only engine;
  no vault-format change.)
- **Engine JSON API (`engine.snapshot`).** New read-only `snapshot(vault) -> dict`
  — the single machine-readable view of a vault (`engine_version`, `project`,
  `nodes`, `tree`, `queue`), serialized as `/snapshot.json`. Pure-read, stdlib-only,
  additive (no vault-format change). Delivers ROADMAP Epic 1 #2 and is the data
  contract the GUI consumes. (`ledger_block` and `snapshot` now share one
  `ledger_counts` roll-up so their numbers cannot drift.)
