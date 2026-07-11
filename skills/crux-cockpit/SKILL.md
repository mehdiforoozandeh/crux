---
name: crux-cockpit
description: >-
  Launch and manage the crux cockpit — the read-only browser GUI over a crux research
  vault (`crux serve`). This skill runs it beginning to finish: locate the vault, start
  the server fresh on localhost, verify it actually serves, and hand the user one
  clickable URL — plus status / stop / restart, and a setup-or-demo path when no vault
  exists yet. Works wherever the agent runs: local machine, VS Code Remote-SSH (drives
  the port forward itself via `code --openExternal`), or a plain SSH terminal (hands the
  user the exact `ssh -L` tunnel command). Use when a crux user wants to see their vault in a browser.
  Triggers: "open the cockpit", "launch the crux GUI", "show me the tree in a browser",
  "serve the vault", "is the cockpit running", "stop the cockpit", "restart the
  cockpit", crux gui, crux cockpit.
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
manage the server's lifecycle. The user should never have to touch a terminal **on the
machine you run on** — the one thing you can't do for them is start a local `ssh -L`
tunnel (plain-SSH contexts only; see **Local vs remote**).

The engine rides in the **crux** skill: `ENGINE = <crux skill>/scaffold/crux.py`.

## Ground rules (load-bearing)

- **Never report an unverified URL.** Before telling the user the cockpit is up, both `/`
  and `/snapshot.json` must have answered 200 from *your* curl. A URL you haven't verified
  does not leave your mouth.
- **URL only — never pop a browser.** Always launch with `--no-open` and deliver the URL
  as a clickable link. The user opens it when ready. **One carve-out:** in VS Code
  Remote-SSH the sanctioned way to create the port forward *is* an open call
  (`code --openExternal` — see the ladder below); there, opening the user's browser is
  the mechanism, not a discourtesy.
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
VAULT="$(cd <vault> && pwd -P)"   # -P: physical path — a symlinked route must hash/match identically
VID="$(python3 -c 'import hashlib,sys;print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])' "$VAULT")"
for pid in $(pgrep -f 'crux\.py (serve|gui|ui|cockpit)'); do
  cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"
  case "$cwd" in "$VAULT"|"$VAULT"/*) kill "$pid" ;; esac
done
```

(The pgrep pattern can also match a wrapper shell — e.g. a `zsh -c … crux.py serve …`
parent. Its cwd is the same vault, so the loop kills it too; that's correct, it dies
with its child. `kill` is asynchronous: if you're about to relaunch on a **pinned** port,
first wait until `lsof -nP -iTCP:<port> -sTCP:LISTEN` returns nothing — a still-dying
listener makes the pinned relaunch fail with "cannot bind".)

(**No `lsof` on the box?** Minimal cluster images sometimes lack it — and `lsof: command
not found` exits non-zero, which reads exactly like "no match / port free". Never let a
missing tool pass a check. Stdlib substitutes: a port is free iff
`python3 -c 'import socket;socket.socket().bind(("127.0.0.1",<port>))'` succeeds, and on
Linux a PID's cwd is `readlink /proc/<pid>/cwd`.)

**4 — Launch, backgrounded, log captured.** Run from inside the vault so the engine
resolves it; never block your shell on the server. **Remote? Pin first** — if any SSH
marker is set, derive `$PORT` from the pin block *below* before launching, and append
`--port "$PORT"` to this line:

```bash
LOG="${TMPDIR:-/tmp}/crux-cockpit-$VID.log"
cd "$VAULT" && nohup python3 "$ENGINE" serve --no-open >"$LOG" 2>&1 &   # remote: + --port "$PORT"
```

(If your harness has a native run-in-background facility, prefer it — same command, same
captured log. And if shell state doesn't persist between your commands, re-derive
`$VAULT`/`$LOG`/`$URL` in each call rather than assuming the variables survive.)

**Running remotely?** (any SSH marker in your env — see **Local vs remote** below.) Pin
the port with `--port`, and make the pin outlive your session — an auto-picked port
drifts on an always-fresh relaunch (8787 → 8789), silently breaking a tunnel or forward
the user already has open, and "remember it in conversation" dies with the session:

```bash
PIN="$HOME/.cache/crux-cockpit/$VID.port"   # $VID from step 3
mkdir -p "${PIN%/*}"
PORT="$(cat "$PIN" 2>/dev/null)"
if [ -z "$PORT" ]; then
  PORT=8787
  while lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do PORT=$((PORT+1)); done
  echo "$PORT" >"$PIN"
fi
```

Launch with `--port "$PORT"`. If a *recorded* pin is busy at launch even after the step-3
kill loop, a foreign process took it: re-pick, update the pin file, and tell the user
their tunnel/forward target changed. Local launches keep auto-pick — no pin file.

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
when you're done"). **First classify the context** (next section): on a local machine the
URL is the whole story; in any remote context your curl proved the server is up *on the
remote* — the report must also carry whatever gets the user's **local** browser to it.

## Local vs remote — where the browser lives

The server always binds `127.0.0.1` **on the machine you're running on**. Step 6 proves
it's serving *there*; whether the **user's browser** can reach it is a separate question.
Classify from your environment before reporting:

SSH markers = any of `$SSH_CONNECTION`, `$SSH_CLIENT`, `$SSH_TTY`. VS Code markers =
`$TERM_PROGRAM` = `vscode` or `$VSCODE_IPC_HOOK_CLI` set.

| your env | context | what reaches the user |
|---|---|---|
| **none** of the SSH markers set | **local** — your machine is their machine | the URL, as-is |
| SSH markers **plus** VS Code markers | **VS Code Remote-SSH** | same URL, once the port is forwarded — you drive the forward (below) |
| SSH markers, **no** VS Code markers | **plain SSH terminal** | nothing yet — they must open a tunnel; you hand them the command |

- **Local** — report the URL; done.
- **VS Code Remote-SSH** — **create the forward yourself; never rely on auto-forwarding.**
  It degrades silently, especially on shared hosts (HPC login nodes): once >20 ports have
  ever auto-forwarded, VS Code flips `remote.autoForwardPortsSource` to `hybrid` and stops
  detecting; ports already listening when VS Code connected are never auto-forwarded; and
  your launch writes the banner to a log file, so the output-watcher never sees the URL.
  The ladder, in order:

  1. **Drive it from the remote CLI** (zero user action):

     ```bash
     [ -n "$VSCODE_IPC_HOOK_CLI" ] && command -v code >/dev/null && code --openExternal "$URL"
     ```

     This asks the VS Code **client** to open the URL; the client creates the port
     forward itself and opens the user's local default browser — it works even with
     auto-forwarding disabled. (`"$BROWSER" "$URL"` is the same mechanism — VS Code
     points `$BROWSER` at a helper that calls `--openExternal`.) Tell the user what
     happened: "your browser just opened the cockpit; the port is forwarded." You cannot
     confirm the forward from the remote side, so ask once — "did it open?". A failed
     guard counts the same as a "no". VS Code *forks* (Cursor, Windsurf, …) set the same
     env markers and ship the same remote CLI under their own binary name — if `code`
     isn't on PATH, try the fork's name (`cursor`, `windsurf`) with the same
     `--openExternal` flag before leaving this rung.
  2. **Cmd/Ctrl-click in the integrated terminal.** First `echo "$URL"` in the terminal
     so a *terminal-rendered* link exists — a localhost URL clicked in the terminal
     forwards on the fly (`remote.forwardOnOpen`, default on). **A URL clicked in a
     chat/webview panel does NOT forward** — it opens the local browser on an unforwarded
     port and fails. Say this explicitly; it is the classic trap.
  3. **Manual forward**: **Ports** panel (the tab next to TERMINAL — or Cmd/Ctrl+Shift+P →
     *Ports: Focus on Ports View*) → **Forward a Port** → `<port>`.
  4. The filled-in `ssh -L` one-liner (always included anyway — see below).

  Move down a rung whenever the current rung's guard fails or the user says it didn't
  work — and deliver rungs 2–4 together in one message, not one at a time.
- **Plain SSH** — the tunnel must be started **from their local machine**; you cannot
  create it from the remote side. Give them the exact command, filled in:

  ```bash
  ssh -L <port>:localhost:<port> <user>@<host>    # run on your LOCAL machine; keep it open
  ```

  then the same `http://localhost:<port>` works in their local browser. Fill `<user>` from
  `whoami` and `<host>` from `hostname -f`; if that's not the name they actually SSH to
  (common on clusters), field 3 of `$SSH_CONNECTION` is the server IP — or simply ask
  "what do you type to connect here?". **But when the typed name ≠ this machine, don't
  put it after `-L`.** Two cluster cases: you're on a compute node behind a login node,
  or the typed name is a round-robin alias (`cedar.computecanada.ca`-style) that may land
  the tunnel on a *different* login node than the one running the server. Either way,
  jump through the typed name and pin the far end to *this* host:
  `ssh -J <typed-name> -L <port>:localhost:<port> $(hostname -f)`. Two things to say out
  loud: run it **locally**, and keep that terminal open while browsing.
  (serve's own banner prints a VS Code-flavoured forwarding hint even here — your tunnel
  instructions supersede it; don't relay it.)

In any remote context, word the report so *verified* and *reachable* aren't conflated:
"serving on the remote and verified there; it opens in your browser once the
forward/tunnel is up."

**When the markers lie.** tmux/screen can strip or *preserve stale* env (`$SSH_*` gone, or
a `$VSCODE_IPC_HOOK_CLI` left over from an earlier VS Code session); mosh sets no SSH vars
at all. Concrete probes when the table's answer smells wrong: `$SSH_CLIENT` often survives
where `$SSH_CONNECTION` didn't; `$TMUX` set means the env may predate the current
connection; `who am i` shows the connecting host for SSH logins. When still unsure, ask
one question — "are you SSH'd into this machine?" — and classify from the answer. And
because a stale VS Code marker misroutes a plain-SSH user, **every remote report includes
the filled-in `ssh -L` one-liner as the last-resort fallback**, even in VS Code mode.

**Other editors and agents — nothing above may leak into the local flow.** Everything
remote-specific (pin files, the forwarding ladder, tunnel commands, opening a browser) is
gated on the env markers. In their absence — Claude Code desktop, Codex, Cursor or Copilot
on the user's own machine, any plain local terminal — the flow is exactly the local one:
auto-picked port, no pin file, report the verified URL, never open a browser. VS Code
forks over SSH (Cursor, Windsurf) set the same markers and carry the same remote-CLI
mechanism under their own binary name; each ladder rung degrades to the next if a fork
lacks a piece.

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
- **Zombie from a crashed session** holding a port → the step-3 kill loop clears it; on
  local (auto-pick) launches a survivor you *shouldn't* kill (another vault's server) never
  blocks a new launch. On **pinned remote** launches it does block — that's the step-4
  re-pick rule: new port, update the pin file, tell the user the forward/tunnel target
  changed.
