# Installing crux — the full guide

The [README's Install section](README.md#install) gets you running in two commands; this
is the detail behind it — what gets installed, per-agent notes, scopes, updating,
uninstalling, and troubleshooting.

## What gets installed

Four skills under [`skills/`](skills), plus the engine they share:

| Skill | Role |
|---|---|
| **`crux`** | the core lab-notebook skill — carries the engine (`scaffold/`: Python CLI, cockpit server, webui, example vaults) |
| **`crux-wiki`** | the literature wiki (PI-curated sources → agent-compiled knowledge base) |
| **`crux-cockpit`** | launches and manages the read-only browser GUI (`crux serve`) |
| **`evolve-crux`** | the contribute-to-crux workflow (ideate → build → validate → ship) |

`crux-wiki` and `crux-cockpit` drive the engine that ships inside the `crux` skill —
**don't install them without it**.

Plus the **specialized agent roster** under [`agents/`](agents) — the spec-09 subagents
(`crux-critic`, `crux-null`, `crux-verifiables`, `crux-close`, `crux-audit`,
`crux-migrate`, `crux-tests`, `crux-glossary`, `crux-situate`, `crux-design`). The clone
path installs them as `<name>.md` symlinks in `~/.claude/agents`, the flat layout Claude
Code reads subagents from. The npx path installs skills only; agents currently ship via
Path B.

## Requirements

- **Python ≥ 3.8** — the engine is stdlib-only, no packages. (`crux.py` checks and says
  so plainly on older interpreters.)
- **git** — both install paths clone from GitHub. Fresh macOS: `xcode-select --install`.
- **Node.js** — only for the `npx` path.

## Path A — the skills CLI (any skills.sh-compatible agent)

```bash
npx skills add mehdiforoozandeh/crux --all
```

Works with Claude Code, Cursor, Codex, Windsurf, Copilot CLI, and the rest of the
[skills.sh](https://www.skills.sh) ecosystem. Notes:

- **`--all` matters.** It selects all four skills for all detected agents,
  non-interactively. Without it, a plain terminal opens a picker with **zero skills
  pre-selected**; inside an agent session the CLI auto-selects everything.
- **Scope.** Default is **project** scope — skills land in `./.agents/skills` of the
  current directory, plus per-agent dirs. Add `-g` for a user-wide install
  (`~/.agents/skills` + your agents' config dirs).
- **Target one agent** with `-a` (e.g. `-a claude-code -a cursor`; repeat the flag —
  comma lists are rejected).
- **Installs are a frozen copy** of GitHub `main` at install time — update with
  `npx skills update`, remove with `npx skills remove`.
- **Project tidiness.** A project-scope install drops `.agents/`, agent dirs
  (`.claude/`, for some agents a non-hidden `agent/` folder), and `skills-lock.json`
  into the repo — commit them deliberately or add them to `.gitignore`.

**Invoking the skills afterward** varies by agent: Claude Code picks them up
automatically; Cursor exposes them as `/crux`-style slash commands; Windsurf as
`@crux` mentions; Codex via `/skills`. Restart / reload the agent first.

## Path B — clone + `./install.sh`

```bash
git clone https://github.com/mehdiforoozandeh/crux
cd crux && ./install.sh
```

The installer symlinks every skill under `skills/` into **both**
`~/.claude/skills` (Claude Code) and `~/.agents/skills` (the shared dir Cursor, Codex,
Windsurf, and Copilot CLI read). Notes:

- **Keep the clone in place** — the skills are symlinks into it. If you move the clone,
  re-run `./install.sh`; if you delete it, the skills silently vanish.
- **Custom target:** `SKILLS_DIR=/path/to/dir ./install.sh` installs skills into exactly
  that one dir instead; `AGENTS_DIR=/path/to/dir` does the same for the agent roster
  (default `~/.claude/agents`).
- **Agents too:** every `agents/<name>/AGENT.md` is symlinked as
  `~/.claude/agents/<name>.md`, so Claude Code can spawn the crux subagents by name.
- Safe and idempotent: it only creates/refreshes symlinks it manages; a real
  (non-symlink) folder of the same name is left untouched and reported.
- Requires bash (`./install.sh`, not `sh install.sh` — Debian's `sh` is dash).

## Verify the install

**`crux doctor`** is the fast answer to "is this thing wired up?" — it checks the Python
version, that the engine's own modules are all present, that the skill and agent symlinks
resolve to a live clone, and (when you run it inside a vault) whether the vault's engine
stamp has drifted or has structural sections a newer engine expects. Every line that is
not `ok` prints the exact command that fixes it. Nothing is written, nothing is repaired,
and no network request is made.

```bash
crux doctor
```

It exits `0` when there is nothing broken — warnings alone still exit `0`, so it is safe
in a script — and `1` when a check fails. `crux doctor --json` gives the same report as
one JSON object.

For the deeper check that the engine itself is correct, run the test suite — from a
clone: `./crux selftest`; from a skills-CLI install:
`python3 <skills-dir>/crux/scaffold/crux.py selftest`. Either way the engine's full test
suite runs in seconds — no GPU, no tokens — and ends `ALL GREEN`.

## Updating · uninstalling

| | Update | Uninstall |
|---|---|---|
| **Clone path** | `git pull` in the clone — the symlinks stay live | delete the skill symlinks from the skills dirs and the `crux-*.md` symlinks from `~/.claude/agents` |
| **npx path** | `npx skills update` | `npx skills remove` |

Restart / reload your agent after either.

## Using the engine without an agent

Everything works from a bare clone: `./crux --help` for the verb tour (the root wrapper
forwards to `skills/crux/scaffold/crux.py`), and the cockpit over the bundled example:

```bash
./crux serve --dir skills/crux/examples/segssl_vault
```

## Troubleshooting

**Run `crux doctor` first** — it detects most of the list below and prints the fix.

- **The npx picker shows nothing selected** — that's the default; use `--all` (or
  space-toggle the four skills).
- **`git: command not found` / a GUI dialog pops on macOS** — the skills CLI clones via
  your system git; install it (`xcode-select --install`) and re-run.
- **`env: python3: No such file or directory`** — the engine needs Python ≥ 3.8 on PATH.
- **Skills don't show up in the agent** — restart / reload the agent; skills dirs are
  read at startup.
- **Skills stopped working after tidying disk** — you likely deleted or moved the clone
  the symlinks point into; re-clone (or move it back) and re-run `./install.sh`.
- **`! skip <name> — a real folder exists`** — install.sh found a non-symlink folder at
  the destination and left it untouched; remove or rename it if you want the managed
  symlink there.
- **`crux serve` port is busy** — pin another: `crux serve --port 8890`.
- **`crux: not inside a crux vault`** — the engine resolves the vault upward from the
  current directory; `cd` into the vault (e.g. `cruxvault/`) or pass `--dir` to `serve`.
