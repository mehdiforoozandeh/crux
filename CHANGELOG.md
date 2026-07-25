# Changelog

All notable changes to crux. Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
the engine version (`ENGINE_VERSION`, stamped into every vault) bumps when the vault format or
verdict/roll-up/view logic changes.

## [Unreleased]

### Fixed

- **`crux selftest` failed on every machine that isn't the author's.** A v0.5.0 assert
  probed a hardcoded `/Users/<author>/crux` path to check that `detect_install` recognises a
  git checkout — so it tested the *runner's* filesystem, not the function. Green on one Mac,
  `PASSED 321/322` and exit 1 on any Linux or Windows box, which made v0.5.0's own
  advertised post-install check fail for new users. The test now builds a throwaway checkout
  in a temp dir (a `.git` directory is all `detect_install` needs — no git binary, no
  subprocess) and normalises through `realpath`, since macOS hands out temp dirs under
  `/var`, itself a symlink to `/private/var`. **The shipped `update.py` was never wrong** —
  only its test. Reported against v0.5.0 on RHEL 9 / Python 3.11.
- **`crux serve` could stall for seconds before printing its URL.** The stdlib's
  `HTTPServer.server_bind()` does a reverse-DNS lookup (`socket.getfqdn`) purely to fill in a
  `server_name` crux never reads — and it sits between the bind and the banner. Instant on a
  normal machine, >30s on a host with slow or absent DNS (a locked-down cluster node, an
  offline laptop, GitHub's macOS runners). The cockpit now binds without it.
- **crux crashed on a Windows console the moment it printed a glyph.** crux writes UTF-8
  (verdict glyphs, the banner's arrow, the drift warning's ⚠, vault text); a cp1252 console
  raises `UnicodeEncodeError` on the first one and takes the command with it — `crux serve`
  died right after the drift warning, before it could print the URL, and `crux --help` failed
  outright. The CLI now states the encoding it writes in.
- **The selftest harness assumed one platform's text conventions**: every text open now pins
  UTF-8 (Windows read UTF-8 vault files as cp1252 and died before the first check), fixtures
  are written with `newline=""` so they are byte-identical everywhere (Windows turned `\n`
  into `\r\n` and changed a file's sha256 under the source-registry test), and the
  `XDG_CACHE_HOME` assert builds its expected path with `os.path.join` instead of hardcoding
  POSIX separators.
- Added coverage for the symlink resolution `install.sh` depends on (skills symlinked into a
  clone must resolve to the clone, not the link) and for a copied/npx install — neither had a
  test.

### Added

- **CI.** `.github/workflows/selftest.yml` runs `./crux selftest` on ubuntu + macOS across
  Python 3.9/3.11/3.13, plus 3.8 on ubuntu-22.04 (the floor the README advertises), with a
  non-blocking informational Windows job. The repo had no CI, which is why the above shipped.

## [0.5.0] - 2026-07-25

### Added

- **Evidence artifacts.** A hypothesis now points at what its run actually produced: files
  live under `results/<hid>/` in the vault and are linked from a new `## Artifacts` section
  (`[label](path)` or a bare path). `crux validate` errors when a results directory holds
  files but no `.md` report is linked, when a linked path doesn't resolve, or when a path
  escapes the vault; `crux close` only warns, so a hypothesis with no files still closes.
  A hypothesis that has a report shows an **Open report** button under its badges, and the
  cockpit renders it **in the detail pane** — headings, tables, code, and **figures inline**
  (click one to open it full size) — served by a new read-only `GET /file/<path>` route
  (extension allowlist, no traversal, no dot-segments). Symlinking `results/<hid>/` at the
  run directory in your experiment repo is the supported way to keep files where they land.
- **A question closes on an approved synthesis.** `crux answer` now refuses a question that
  has no synthesis node approved by the PI: `crux synthesize "…" --for q3` drafts it,
  `crux approve s1` is the human signature (timestamped, idempotent), and `answer` then
  resolves the question and records `synthesis: s1` on it. Questions resolved by an earlier
  engine are grandfathered — the gate applies to new closes only. **ENGINE_VERSION 1.1 → 1.2.**
- **Markdown is rendered everywhere in the cockpit.** Problem statements, findings, answers
  and goals used to print their markdown source verbatim in the detail pane; they now go
  through the renderer (which gained images and relative-link resolution) — the same one the
  wiki reader uses.
- **Full-screen panels.** Either side of the cockpit can take the whole window, in the Tree
  tab and the Wiki tab: a `⛶` control on each panel, `[` / `]` to maximize, `Esc` to restore.
  Persisted.
- **Focus one question.** Double-click a node (or press `f`, or use the toolbar button on a
  selection) and every branch off its ancestor path folds away — the spine from the root
  stays for orientation, the question's own subtree stays open. A breadcrumb over the tree
  shows the path, with clickable ancestors to widen focus and `✕` / `Esc` to clear.
- **Update check — it tells you, it never installs.** `crux` reports once a day when a newer
  release exists and hands over the exact command for *your* install (`git -C <root> pull
  --ff-only` for a clone, resolved through `install.sh`'s symlinks; `npx skills update` for a
  copied one), plus "ask your agent to update crux" — the `crux` skill now documents the
  preflight an agent must run first. crux deliberately does **not** update itself: a vault
  records the engine version its verdicts were produced under, and that should change because
  someone decided so, not because a background thread did. At most one request per 24h, in a
  background thread with a 1.5s timeout, printed **from a cache** on stderr so no command's
  output waits on the network and stdout stays clean for agents parsing it.
  `CRUX_NO_UPDATE_CHECK=1` disables the whole thing, chip included. The cockpit shows the same
  state as a topbar chip, read from that cache — `serve` never makes a network request. A new
  `CRUX_VERSION` constant carries the release version, separate from the vault-format
  `ENGINE_VERSION`.
- **The living tree.** Every node is spring-anchored to its deterministic layout position,
  so you can drag one (or watch a refresh reshape the tree) and it always glides home —
  entrants fly out of their parent, and the tree comes to rest perfectly still.
  Plus a new **radial view** (toolbar toggle, persisted): the project at the centre,
  questions and hypotheses on depth rings; the orientation toggle applies to the tidy
  view only. Reduced-motion renders the exact static tree as before. Hardened for
  Safari/WebKit (which re-rasterizes SVG text on every repaint): radial spokes are
  trimmed to the pill rims, per-frame writes touch only elements that visibly moved
  (measured 14→60fps on a radial drag), and mass relayouts — a view switch on a big
  vault — glide label-less, the text returning at settle (20→58fps at ~90 nodes).
  (PRD: [`docs/prd/gui-living-tree.md`](docs/prd/gui-living-tree.md).)
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

### Changed

- **The colour key is the engine's whole vocabulary.** `inconclusive`, `idea` and `staged`
  were painted on nodes but missing from the legend — `inconclusive` verdicts had no colour
  to look up at all. All ten states are now listed, and a selftest derives the expected set
  from the engine's own constants so the two can't drift apart again.
- **The browser tab names the project** — `crux cockpit: <project>` instead of `crux cockpit`,
  so several open cockpits stay tellable apart.
- **A roomier search box** — 290px, up from a fixed 230px, with a shorter placeholder
  (`Search nodes · ↵ jump`) that fits inside it. It is bounded, not greedy: it never grows
  to swallow the toolbar. Below 1400px the view controls drop to icons (tooltips kept) so
  the box keeps its width on a laptop screen.
- **The tree rests completely still.** The idle "breathing" motion is gone, and the physics
  loop now *stops* once everything is on its anchor instead of animating forever — an idle
  cockpit costs zero animation frames. Drag, fly-home, and relayout glides are unchanged.
- **The bundled `segssl_vault` example** demonstrates the v0.5 model: h1 carries a real
  report (with an SVG chart, a PNG figure, and a CSV) under `results/h1/`, and each resolved
  question carries the approved synthesis that closed it.

### Fixed

- **`crux test --run` kept only the first run link.** The insert point was decided by a
  whole-body `_(none yet)_` probe, so the moment a second section shipped with a placeholder
  of its own (`## Artifacts`), every later run link was silently discarded — no error, and
  the CLI still printed success. Appending is now scoped to the named section, so links
  accumulate in the order they were recorded. (Caught by the v0.5 review pass; regression
  test added.)
- **Artifacts are served under a restrictive CSP.** An SVG is the one allowlisted type that
  is also a *document*: navigate straight to one and its `<script>` would run in the
  cockpit's own origin, where `/snapshot.json` — the whole vault — is same-origin readable.
  `/file/` responses now carry `default-src 'none'; … sandbox` plus `nosniff`, which
  neuters that without affecting `<img>` rendering. Files are also streamed rather than read
  into memory whole.
- **The update check re-hit the network on every command.** Its 24h window was only stamped
  by a *successful* fetch, on a daemon thread that a short-lived command killed on exit — so
  the stamp was never written, the notice never appeared, and every invocation fired another
  abandoned request. The window is now claimed before the request goes out, the worker is no
  longer a daemon, and cache writes are atomic (`os.replace`) so two concurrent crux
  processes can't leave a torn file behind.
- **Artifacts the cockpit can't serve are shown, not linked.** A recorded `.bin`/`.ckpt`
  used to render as a download link that could only ever 404; the servable extension set now
  lives in one place (`engine.SERVABLE_EXT`, keyed to `serve.FILE_TYPES`) and the UI marks
  anything outside it as inert.
- **`CRUX_NO_UPDATE_CHECK=1` now silences the cockpit chip too**, not just the CLI line.
- **The Review button did nothing while a report was open**, and a manual branch-expand while
  focused was undone by the next poll (focus now folds only nodes that *arrive* while it is
  active). The focus button's contextual label also refreshes when the selection is dropped.
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

[0.5.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.5.0
[0.4.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.4.0
[0.3.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.3.0
