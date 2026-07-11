---
name: crux-cockpit
description: >-
  Launch and manage the crux cockpit — the read-only browser GUI over a crux research
  vault (`crux serve`). This skill runs it beginning to finish: locate the vault, start
  the server fresh on localhost, verify it actually serves, and hand the user one
  clickable URL — plus status / stop / restart, and a setup-or-demo path when no vault
  exists yet. Use when a crux user wants to see their vault in a browser. Triggers:
  "open the cockpit", "launch the crux GUI", "show me the tree in a browser", "serve
  the vault", "is the cockpit running", "stop the cockpit", "restart the cockpit",
  crux gui, crux cockpit.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  requires: "the crux skill (drives its engine at skills/crux/scaffold/)"
  notice: "Playbook only — operates the bundled crux engine's `serve` verb; no engine changes, no third-party code."
---

# crux-cockpit — launch the crux GUI, beginning to finish

The **cockpit** is crux's read-only browser GUI: `crux serve` boots a stdlib HTTP server
on `127.0.0.1`, serves the `webui/` frontend, and exposes the vault as `/snapshot.json`
(status-colored tree — pan / zoom / collapse / search / re-orient — plus the review queue
and node detail; live-refreshing, zero writes). The engine does the serving; **you (the
agent) do the operating**: find the vault, launch clean, verify, hand over one URL, and
manage the server's lifecycle. The user should never have to touch a terminal for any of it.

The engine rides in the **crux** skill: `ENGINE = <crux skill>/scaffold/crux.py`.

## Ground rules (load-bearing)

- **Never report an unverified URL.** Before telling the user the cockpit is up, both `/`
  and `/snapshot.json` must have answered 200 from *your* curl. A URL you haven't verified
  does not leave your mouth.
- **URL only — never pop a browser.** Always launch with `--no-open` and deliver the URL
  as a clickable link. The user opens it when ready.
- **Always fresh, per vault.** A launch first kills any cockpit already serving *that
  vault* — and never touches cockpits serving *other* vaults (several can coexist on
  different ports).
- **The cockpit is read-only.** No route writes; every mutation stays in the agent/CLI.
  Never present it as an editor.
- **Surface engine-drift warnings.** If the launch log warns that the vault was stamped by
  a different engine version, relay that warning to the user verbatim.

## Launch protocol

**1 — Locate the vault.** The nearest directory at-or-above cwd containing `.crux.yaml`.
If the user named a vault, use that. If more than one vault is plausible in the project,
ask which — don't guess.

**2 — No vault anywhere?** Offer two paths and let the user pick:
- **Set up a real vault** — hand off to the **crux** skill's setup interview (seed outline
  → approve → `init --from`), then come back here.
- **A disposable demo vault** — so they can explore the GUI in seconds:
  `python3 <crux skill>/scaffold/selftest.py --keep <tmpdir>/crux-demo-vault`
  (build it *outside* their repo, e.g. under `$TMPDIR`, and say clearly that it's
  throwaway sample data).

**3 — Kill stale servers for this vault** (fresh-start rule, scoped by process cwd):

```bash
VAULT="$(cd <vault> && pwd)"
for pid in $(pgrep -f 'crux\.py (serve|gui|ui|cockpit)'); do
  cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"
  case "$cwd" in "$VAULT"|"$VAULT"/*) kill "$pid" ;; esac
done
```

(The pgrep pattern can also match a wrapper shell — e.g. a `zsh -c … crux.py serve …`
parent. Its cwd is the same vault, so the loop kills it too; that's correct, it dies
with its child.)

**4 — Launch, backgrounded, log captured.** Run from inside the vault so the engine
resolves it; never block your shell on the server:

```bash
LOG="${TMPDIR:-/tmp}/crux-cockpit-$(basename "$VAULT").log"
cd "$VAULT" && nohup python3 "$ENGINE" serve --no-open >"$LOG" 2>&1 &
```

(If your harness has a native run-in-background facility, prefer it — same command, same
captured log. And if shell state doesn't persist between your commands, re-derive
`$VAULT`/`$LOG`/`$URL` in each call rather than assuming the variables survive.)

**5 — Parse the URL from the banner.** The server prints exactly one line carrying it
(`crux cockpit (read-only) → http://localhost:<port>`; port auto-picked from 8787, or pin
one with `--port`). Poll the log rather than racing it:

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  URL="$(grep -o 'http://localhost:[0-9]*' "$LOG" | head -1)"
  [ -n "$URL" ] && break; sleep 0.5
done
```

(No URL after ~5s → the server died on startup; see **Failure modes**.)

**6 — Verify before reporting.** Both routes, from your own shell:

```bash
curl -fsS "$URL/" >/dev/null
curl -fsS "$URL/snapshot.json" | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(d["project"]["title"], "·", len(d["nodes"]), "nodes")'
```

If either fails: read `$LOG`, diagnose, fix, re-verify. Do **not** hand over the URL on a
failed check.

**7 — Report.** One message: the clickable URL, which vault it serves (project title +
node count from step 6), that it's read-only, and how to end it ("say *stop the cockpit*
when you're done"). If the banner carried a VS Code / Remote-SSH port-forwarding hint
(it appears automatically in those contexts), relay it.

## Status · stop · restart

- **Status** ("is the cockpit running?") — enumerate `pgrep -f 'crux\.py (serve|gui|ui|cockpit)'`;
  for each PID report its vault (cwd via `lsof -a -p <pid> -d cwd -Fn`) and port
  (`lsof -a -p <pid> -iTCP -sTCP:LISTEN -P`), and confirm the URL still answers before
  calling it alive. Count only PIDs that actually hold a LISTEN port — a wrapper shell can
  match the pattern while listening on nothing. No servers → say so plainly.
- **Stop** ("stop/close the cockpit") — kill that vault's PID(s) (step-3 loop), then confirm:
  process gone (`kill -0 <pid>` fails) and port freed
  (`lsof -nP -iTCP:<port> -sTCP:LISTEN` returns nothing). Report it stopped. If servers for
  several vaults are running and the user didn't say which, ask.
- **Restart** — just run the launch protocol; the fresh-start rule *is* the restart.

## Failure modes worth knowing

- **Banner never appears / process exits immediately** → read `$LOG`: a `crux: error:` line
  means the vault didn't resolve (wrong dir) or a pinned `--port` was busy. Fix and relaunch.
- **URL answers but `/snapshot.json` 500s** → the vault is structurally broken; run
  `python3 "$ENGINE" validate` in the vault and surface the findings.
- **Zombie from a crashed session** holding a port → the step-3 kill loop clears it; ports
  are auto-picked, so a survivor you *shouldn't* kill (another vault's server) never blocks
  a new launch.
