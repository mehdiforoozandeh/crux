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
  - **Tree interaction layer rewritten** so the cockpit is actually usable: node selection,
    the ± collapse/expand toggle, drag-to-pan, wheel/​button zoom, and search-to-jump now work.
    The tree previously went dead because a `setPointerCapture` on every pointerdown retargeted
    the follow-up `click` to the `<svg>` (so `e.target.closest('.node')` was always null). Pan is
    now a distinct gesture (a real drag threshold, `window`-scoped move/up, no pointer capture),
    pan/zoom are `requestAnimationFrame`-coalesced, synthesis nodes sit beside their related
    questions (short dashed edges instead of danglers), and a fit/zoom control cluster was added.
    Guarded by four new `selftest` asserts (asset serving, frontend pure-read, issue-#1 regression).
  - **Visual/UX pass (post-v1 polish).** Two explicit Obsidian-like themes — near-black dark
    (default) and light — with a persisted ☀/☾ toggle; the real Crux logo (Southern Cross mark
    + gold wordmark) in the top bar and the `engine v…` meta dropped; per-kind node styling
    (colorless pill root, squared questions, soft-pill hypotheses with verdict glyphs ✓/✕/◐ and
    tri-state verifiable dots, diamond syntheses) so the tree reads without the key; the legend
    rebuilt as a grouped color key whose chips are click-to-spotlight filters; trackpad-first
    zoom (two-finger scroll and pinch, separately tuned); text selection suppressed on the
    canvas (no more select-all while panning); and the initial auto-fit retries until the tab
    is actually visible (a background-tab open used to load mis-fitted).
  - **Layout & node views (round 2).** Two selectable tree orientations — left-to-right and
    top-down — with a toolbar toggle (persisted), backed by a rewritten tidy-tree layout that
    handles variable node sizes in either axis. A **full-text node view is now the default**
    (mindmap.io-style): each box grows to fit its whole title, word-wrapped up to 4 lines, so
    questions and hypotheses are readable without clicking; a compact one-line view remains one
    toggle away. Node kinds are now unmistakable by size *and* shape *and* font — the project
    root is a colorless pill carrying the Crux mark, questions are the largest boxes, hypotheses
    the smallest. A **focus button** collapses every non-open question in one click, so a large
    program shows only what still needs work. The legend dropped the synthesis chip and is laid
    out as two aligned rows (questions / hypotheses). Added a Crux favicon (was a default "L").
  - **Round 3 — motion, splitter, labels, synthesis gone.** Toolbar buttons now show a text
    label beside the icon (Left-right / Top-down · Full text / Compact · Focus). Synthesis nodes
    are no longer drawn in the cockpit at all (they still exist in the vault/snapshot). The
    tree ⇔ detail boundary is a **draggable splitter** (double-click to reset; width persists).
    A **fluid-motion pass**: relayouts (collapse/expand, focus, orientation, density) now animate
    — surviving nodes glide to their new positions while edges stay attached — and programmatic
    camera moves (fit, centre-on-jump, the zoom buttons) ease instead of snapping, while drag and
    wheel stay 1:1. Added detail-pane content fade-in and hover/press micro-transitions across the
    chrome, plus a smooth theme cross-fade. All motion is gated on `prefers-reduced-motion` and
    falls back to correct final state in a hidden/background tab (rAF paused).
  - **Round 4 — chrome placement.** The orientation / density / focus controls moved out of the
    canvas into the top bar beside the search box. The color-key legend is smaller and now
    **dismissable** — an × collapses it to a small "Key" button (state persists) so it never
    blocks the tree. The zoom in/out/fit buttons are ~30% smaller, with the fit glyph enlarged
    relative to its button.
  - **Round 5 — kind legibility + slimmer bar.** Questions and hypotheses are now obviously
    different in full-text mode: questions are sharp-cornered "container" boxes with a bold left
    accent stripe, a heavier border and larger bold text; hypotheses are lighter, thinner pills
    (fully rounded) with smaller dimmer text and their verdict glyph. Fixed the Review button
    wrapping onto two lines (nowrap, no shrink). Slimmed the whole top bar (less padding, 28px
    controls).
- **Engine JSON API (`engine.snapshot`).** New read-only `snapshot(vault) -> dict`
  — the single machine-readable view of a vault (`engine_version`, `project`,
  `nodes`, `tree`, `queue`), serialized as `/snapshot.json`. Pure-read, stdlib-only,
  additive (no vault-format change). Delivers ROADMAP Epic 1 #2 and is the data
  contract the GUI consumes. (`ledger_block` and `snapshot` now share one
  `ledger_counts` roll-up so their numbers cannot drift.)
