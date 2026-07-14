# Changelog

All notable changes to crux. Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
the engine version (`ENGINE_VERSION`, stamped into every vault) bumps when the vault format or
verdict/roll-up/view logic changes.

## [Unreleased]

### Added

- **`crux serve --dir <vault>`.** Point the cockpit at any vault without `cd`-ing into
  it (resolves upward from the given directory, same as the cwd default). Powers the
  README's new zero-setup **Try it in 60 seconds** path over the bundled
  `segssl_vault` example.
- **`crux selftest`.** The engine's test suite is now a first-class verb (it forwards
  to `scaffold/selftest.py`, `--keep` included) — the post-install check is
  `./crux selftest` instead of knowing the script path.
- **Python floor.** The engine states and enforces its requirement: Python ≥ 3.8, with
  a clear message instead of a raw `SyntaxError` on older interpreters.
- **Conditional cockpit polling.** `/snapshot.json` now carries an `ETag`; the webui
  echoes it back and an unchanged vault answers `304` with no body — the ~1/s poll stops
  re-sending the full snapshot when nothing changed (matters for big vaults and battery).
- **`AGENTS.md` + `CONTRIBUTING.md`.** Repo-root orientation for coding agents (layout,
  `./crux` wrapper, the selftest/stdlib-only/read-only gates) — Codex, Cursor, and
  Copilot read `AGENTS.md` natively — plus a thin CONTRIBUTING pointing at the
  `evolve-crux` workflow.

### Fixed

- **Post-`init` hint.** `crux init` now prints `next: cd cruxvault && crux ask …` — the
  vault is created *below* the cwd, so the old hint failed with "not inside a crux
  vault" when run verbatim from where the user just ran `init`.
- **`install.sh` cross-agent + portability.** The installer now links skills into both
  `~/.claude/skills` (Claude Code) and `~/.agents/skills` (the shared dir Cursor, Codex,
  Windsurf, and Copilot CLI read); `SKILLS_DIR` still overrides to a single custom dir.
  It fails fast with a clear message under non-bash `sh` (dash), and its final output
  warns that the skills are symlinks into the clone.
- **SKILL.md paths that broke after installation.** `crux-wiki` and `crux-cockpit`
  referenced the engine via repo-root-relative paths (`skills/crux/scaffold/…`) that
  don't exist once skills are installed as siblings; both now use the
  `<crux skill>/scaffold/…` placeholder and tell the agent to install the `crux` skill
  first if the engine is missing. `evolve-crux` no longer hardcodes the maintainer's
  `~/crux` checkout.

### Docs

- **Install docs split.** README's Install section is now a two-command quick install;
  the detail (what gets installed, per-agent notes, scopes, lifecycle, troubleshooting)
  moved to a dedicated [`INSTALL.md`](INSTALL.md).
- **Install section rewritten for accuracy.** Requirements stated (Python ≥ 3.8, git,
  Node.js for the npx path); the npx command gains `--all` (without it the interactive
  picker starts with zero skills selected); all four skills are named; project-vs-global
  scope, updating (`git pull` vs `npx skills update`), uninstalling, the keep-the-clone
  warning, and the restart-your-agent step are documented.
- **Per-agent invocation notes.** README says how skills surface per agent (`/crux` in
  Cursor, `@crux` in Windsurf, `/skills` in Codex, automatic in Claude Code) and warns
  that project-scope `npx` installs drop agent dirs into the repo (`.gitignore` or
  commit deliberately).

## [0.4.0] - 2026-07-12

### Added

- **Wiki tab in the cockpit (Epic 1 × Epic 3).** `crux serve` grows a `Tree | Wiki`
  switcher (shown only on wiki-bearing vaults): an explorer rail with virtual category
  folders + pinned index / log / schema / sources (rail resizable via its own draggable
  divider), a **living force-directed wikilink graph** — Obsidian-like physics: it
  settles with visible ease, nodes are grab-draggable (the neighborhood tugs along and
  springs back), vault changes morph the constellation organically, and the simulation
  sleeps when idle (color = category, size = link degree, hover-highlighted
  neighborhoods, minimizable category key; the tree keeps its deterministic layout) —
  and a markdown **reader** with a backlinks-with-snippets section; `[[wiki/slug]]`
  citations in the tree's detail pane are now live and jump straight into the Wiki tab.
  Tree nodes also light up on hover with the same responsiveness as wiki nodes. Backed
  by an additive `wiki` key in `engine.snapshot()` (index only — no page bodies in the
  1s poll) and a lazy, read-only, traversal-safe `/wiki/<slug>.json` route (body +
  server-computed backlinks; reserved slugs `_index`/`_log`/`_schema` serve the
  specials). Categories get maximally-distinct colors (sorted-order assignment over a
  warm/cool-alternating palette), and a ⚛ button spreads the constellation to a
  pure-repulsion "ion" equilibrium. Wiki search also filters the rail's sources, and the crux-wiki ingest
  convention now carries the full author list in source titles — papers are findable by
  any co-author's name. One vendored static asset — `webui/vendor/motion.js` (motion.dev
  browser build, MIT) — as progressive-enhancement animation only: the UI is fully
  functional without it, the engine stays stdlib-only, and the GUI stays write-free.
  No vault-format change (`ENGINE_VERSION` stays 1.1). PRD: `docs/prd/gui-wiki-tab.md`
  (incl. post-signoff amendments).

- **`./crux`** — a root-level executable wrapper that forwards every argument to the
  engine (`skills/crux/scaffold/crux.py`), so a clone runs `./crux <verb>` directly and
  the repo front page leads with the product's name. Pure delegation; skills installers
  never see it.

- **`crux-cockpit` skill** — the GUI launcher: an agent playbook that runs `crux serve`
  beginning to finish. Locates the vault (or offers vault-setup / a disposable demo vault
  when none exists), kills any stale server for that vault (fresh-start, scoped per vault),
  launches backgrounded with `--no-open`, verifies `/` **and** `/snapshot.json` answer
  before reporting, and hands the user one clickable localhost URL — plus status / stop /
  restart. Covers local **and** remote work: on VS Code Remote-SSH the agent creates the
  port forward itself via the remote CLI (`code --openExternal` — reliable on shared/HPC
  hosts where VS Code's auto-forwarding silently degrades), with click-to-forward and the
  Ports panel as fallbacks; on a plain SSH terminal it hands the user the exact `ssh -L`
  tunnel command (incl. multi-hop `-J` for compute nodes behind a login node); and in any
  remote context it pins the port persistently (`~/.cache/crux-cockpit/`) so an
  always-fresh relaunch can't silently break an open tunnel. Playbook only: no engine
  changes (ENGINE_VERSION stays 1.1).

- **Cockpit GUI polish (Epic 1).** Every question and hypothesis now shows its short code
  (**Q10 / H13**) on the left of the node — and the **compact** node view becomes a clean
  codes-only map. An always-visible **view-only reminder** (a header "View-only" pill plus a
  pinned detail-pane footer) makes explicit that the cockpit never writes: edits go through
  the agent or the crux CLI. The server now sends `Cache-Control: no-store` on every response,
  so a plain browser reload always reflects the latest webui and vault state (no stale-cache
  surprises while iterating). Webui + `serve.py` only; ENGINE_VERSION stays 1.1.

### Fixed

- **Cockpit: detail-pane links were dead when a text size was active.** The review-queue rows
  and the Children / Related links did nothing, because the text-size control writes a
  `data-font` attribute onto the content container and the click handler's
  `closest("[data-font]")` matched that container and returned before reaching its navigation
  branch. The font check is now scoped to its own buttons, so clicking a review row or child
  link opens that node as expected.

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

[0.4.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.4.0
[0.3.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.3.0
