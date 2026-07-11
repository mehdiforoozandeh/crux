# PRD: crux GUI v1 — a read-only browser cockpit

- **Kind:** feature
- **Roadmap:** Epic 1 — Graphical UI for crux (`ui`). Advances items **#2** (Engine JSON API), **#3** (interactive tree/graph view), **#5** (review-gate inbox), and the *read half* of **#4** (node detail). Deliberately **not** #6 (packaging) or the *edit half* of #4.

## Problem / motivation

Today the only way to *see* a crux vault is the CLI's text tree or opening the folder in
Obsidian. Neither is a good home for a research program: the CLI can't show the whole
constellation at a glance, and Obsidian pulls in a heavy third-party app whose generic
graph knows nothing about crux's semantics (verdicts, the review gate, the evidence
ledger). A PI who wants to *look at where the program stands* — which questions are
answered, which hypotheses are running, what's waiting on their decision — has no
crux-native, dependency-light way to do it.

We want a standalone visual cockpit over the vault that is **independent of Obsidian**,
makes the crux-specific structure legible, and stays true to crux's ethos: stdlib engine,
zero-install, plain-markdown source of truth.

## Design decision

A **local browser app the engine serves itself** — a new `crux serve` verb boots Python's
stdlib HTTP server, opens `http://127.0.0.1:<port>` in the browser, and renders a
**read-only two-pane cockpit** over the current vault:

- **Left pane — the crux tree.** A deterministic **hierarchical graph**: root = project;
  Questions branch from the root and nest; Hypotheses (`idea` nodes) are leaves; synthesis
  nodes link across questions with distinct edges. Status-colored. **Zoom / pan**,
  **collapse/expand** any question's subtree, and a **search box** that filters/highlights
  and jumps to a node — so a program that grows to hundreds of nodes stays navigable.
- **Right pane — contextual.** On open it shows the **review queue** (questions the engine
  has flagged as awaiting a decision). Clicking any node in the tree swaps the pane to that
  node's **detail** (read-only); a persistent `Review (N)` control jumps back to the queue.
- **Live.** The pane and tree **auto-refresh** as the vault changes on disk (the agent
  writing in the terminal), so the cockpit always reflects reality without a manual reload.
  The deterministic layout keeps node positions **stable** across refreshes.

The browser gets its data from a single new engine read function, **`snapshot(vault) ->
dict`**, serialized as JSON at `/snapshot.json`. This is the one machine-readable contract
the UI consumes (delivering Roadmap #2 as a real, testable artifact) — the frontend never
re-parses markdown.

**Frontend is no-build**: static HTML/CSS + vanilla JS, with at most a *single vendored
JS file* for graph layout (a static asset, not a Python dependency). The **engine stays
stdlib-only**; `serve.py` imports stdlib only.

### Opening the cockpit — seamless across three contexts

crux is driven from different homes; the cockpit must open with near-zero friction in each:

1. **Agent = CLI in a plain terminal** → open the system browser (Safari/Chrome/…).
2. **Agent = CLI in the VS Code integrated terminal** (incl. **Remote-SSH**, e.g. Compute
   Canada) → the server runs where the CLI runs; VS Code **auto-forwards** the listening
   localhost port and offers to open it, and the printed URL opens VS Code's **Simple Browser**.
3. **Agent = VS Code extension** (Claude Code / Cursor / Copilot) → same as (2): open the
   URL in the Simple Browser.

One robust path that degrades gracefully everywhere:

- **Bind `127.0.0.1` on an auto-selected free port** (default `8787`, increment if busy;
  `--port` to pin). Binding localhost is exactly what VS Code's automatic port-forwarding
  picks up, so the Remote-SSH case "just works" without extra config.
- **Always print one prominent, clickable URL** (`http://localhost:<port>`) + `Ctrl-C to
  stop`. This is the universal entry point: plain terminals and VS Code both linkify
  localhost URLs, and it never fails — no context is left at a "now what?" moment.
- **Context-aware auto-open.** Detect VS Code via `TERM_PROGRAM=vscode` and remote via
  `SSH_CONNECTION` / `VSCODE_IPC_HOOK_CLI`:
  - plain local terminal → call `webbrowser.open()` (system browser);
  - VS Code / remote → **do not** spawn a browser (no display on a remote; VS Code handles
    it better), and print a one-line hint: *"VS Code will offer to open this forwarded port
    — accept it, or Ctrl/Cmd-click the URL → Open in Simple Browser."*
  - `--open` forces auto-open; `--no-open` suppresses it.

A naive "always `webbrowser.open()`" is rejected precisely because it fails silently on a
remote — the printed URL + VS Code forwarding is what makes it seamless there.

**Main alternatives rejected:**

| Rejected | Why |
|---|---|
| Obsidian plugin / complement Obsidian | The stated goal is *independence* from Obsidian, not extending it. |
| Desktop app (Tauri / Electron) | Drags in an npm/Rust toolchain + per-OS build/sign/notarize. `crux serve` stays install-free and keeps the stdlib ethos. (Obsidian, Logseq, Zettlr are *all* Electron — the served-browser route is the genuinely lighter shape.) |
| Write-enabled cockpit (tick/close/answer in the GUI) | Keeps a *single* mutation path — the agent — so the GUI has **zero** write code, no confirm dialogs, and no concurrency with the agent. All creating/editing/deciding stays in agent conversation. |
| Agent/chat panel inside the GUI | Chat belongs in the CLI agent (Claude Code / whatever the user runs). The GUI is a pure human cockpit. |
| Server-rendered HTML, no JSON layer | The JSON snapshot is a testable contract, makes auto-refresh a clean re-fetch, and *is* Roadmap #2. |
| Force-directed / organic constellation | Its physics re-lays-out on every auto-refresh, making nodes jump around — disorienting in a cockpit you watch. Deterministic hierarchical layout keeps positions stable. |

## Scope

**In v1:**
- `snapshot(vault)` engine read function + `/snapshot.json`.
- `crux serve` CLI verb (localhost-only, opens browser, serves static UI + snapshot + live-update channel).
- Read-only two-pane cockpit: hierarchical status-colored crux tree (zoom/pan/collapse/search) + contextual right pane (review queue by default, node detail on select).
- Node detail for each type (question: detail, "Answer so far", ledger roll-up, children; hypothesis: problem, verifiables as read-only tri-state, verdict + metric, findings; synthesis: related questions).
- Live auto-refresh on vault change.

**Explicitly NOT in v1 (non-goals):**
- **No writes of any kind** — no create/edit/delete, no ticking verifiables, no recording verdicts, no clearing the gate. Every mutation goes through the agent/CLI.
- **No agent/chat** in the GUI.
- **No force-directed/organic layout** — deterministic hierarchical only.
- **No auth, no multi-user, no remote hosting** — binds `127.0.0.1`, single local user.
- **No packaging** as a desktop bundle or Obsidian plugin (Roadmap #6 is later).
- **Fine visual styling & interaction polish** are deferred to post-v1 iteration; v1 nails the strategy and the skeleton, then we refine how it looks and behaves.
- Other epics (marketing animation, LLM wiki) are untouched.

## Proposed defaults (iterate post-v1; here so the build has a target)

- **Status color language.** Question: `open` neutral · `review` highlighted/attention · `resolved` green-muted. Hypothesis: `idea` grey · `staged` blue · `running` blue+animated · `done` colored by verdict — `supported` green, `partial` amber, `refuted` red, `inconclusive` slate. Project root: anchor style. Synthesis: distinct shape (e.g. diamond) with dashed edges.
- **Right-pane review queue.** One row per question in `review`, showing id · title · a one-line ledger summary (e.g. "3 children · 2 supported, 1 refuted"); click → that question's detail.
- **Auto-refresh mechanism.** Server watches the vault dir (stdlib mtime poll); browser gets updates via Server-Sent Events or a short snapshot poll (~1s). Implementation's call; requirement is "updates within ~1–2s, positions stable."

## Acceptance criteria

**Automatable → new asserts in `skills/crux/scaffold/selftest.py`:**
- [ ] `engine.snapshot(v)` returns a dict whose top-level keys are exactly `{engine_version, project, nodes, tree, queue}`.
- [ ] `snapshot` is **JSON-serializable** — `json.dumps(snapshot(v))` succeeds and round-trips.
- [ ] The `tree` nesting **exactly matches parent links**: every node is reachable from the root once, and each node's children match `v.children[id]` in order.
- [ ] `snapshot(v)["queue"]` equals the ids of questions with status `review`, i.e. equals `cmd_review` output.
- [ ] Each `idea` node in the snapshot carries `status`, and (when `done`) a `verdict` ∈ `VERDICTS` and `metric` consistent with its frontmatter / `derive_verdict`.
- [ ] Each `question` node carries a `ledger` with counts matching `ledger_block` (ideas done, supported/partial/refuted/inconclusive, sub-questions resolved).
- [ ] `snapshot` is **pure read** — calling it does not modify the vault on disk (byte-for-byte identical files before/after).
- [ ] **Stdlib-only:** `serve.py` (and `engine.snapshot`) import only Python stdlib modules.
- [ ] `crux serve` binds `127.0.0.1` and selects a **free port** (a busy default falls back to the next free port); `--port` pins it.
- [ ] On start it prints exactly one `http://localhost:<port>` line to stdout (assert the URL string appears).
- [ ] The **context-detection helper** returns the right mode for faked env combos — plain / `TERM_PROGRAM=vscode` / remote (`SSH_CONNECTION`) — without spawning a browser.
- [ ] `--no-open` suppresses any `webbrowser` call (assert the open hook is not invoked).

**Manual → checklist walked in `validate`:**
- [ ] `crux serve` inside a vault opens a browser showing the crux tree (root → Questions → Hypotheses), status-colored, with synthesis links. *(manual)*
- [ ] Default right pane is the review queue listing exactly the questions awaiting a decision; clicking a queue row opens that question's detail. *(manual)*
- [ ] Clicking any tree node opens its read-only detail on the right; `Review (N)` returns to the queue. *(manual)*
- [ ] Tree supports zoom, pan, collapse/expand of a question's subtree, and search-to-jump. *(manual)*
- [ ] Mutating the vault via CLI/agent updates the GUI within ~1–2s with **no manual reload** and **stable node positions**. *(manual)*
- [ ] The GUI performs **no writes** — observed by running against a read-only copy / confirming zero vault mutation during a session. *(manual)*

## Backward-compat / migration

**None required.** This change is purely **additive**: a new read-only `snapshot` function,
a new `serve` verb, and new static assets. It does **not** touch vault format, verdict
derivation, roll-up, or the generated views. Therefore `ENGINE_VERSION` stays `1.0` and
existing vaults load and render unchanged.

## Build sequencing (informative, not part of the gate)

Natural two-stage landing, honoring "tests-first": **(1)** `snapshot` + its selftest asserts
(fully automatable, green before any UI exists), then **(2)** `crux serve` + the frontend
(manual-checklist criteria). May ship as one PR or two; the PRD's acceptance criteria are
the same either way.
