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
- **Custom target:** `SKILLS_DIR=/path/to/dir ./install.sh` installs into exactly that
  one dir instead.
- Safe and idempotent: it only creates/refreshes symlinks it manages; a real
  (non-symlink) folder of the same name is left untouched and reported.
- Requires bash (`./install.sh`, not `sh install.sh` — Debian's `sh` is dash).

## Verify the install

From a clone: `./crux selftest`. From a skills-CLI install:
`python3 <skills-dir>/crux/scaffold/crux.py selftest`. Either way the engine's full test
suite runs in seconds — no GPU, no tokens — and ends `ALL GREEN`.

## Updating · uninstalling

| | Update | Uninstall |
|---|---|---|
| **Clone path** | `git pull` in the clone — the symlinks stay live | delete the four symlinks from the skills dirs |
| **npx path** | `npx skills update` | `npx skills remove` |

Restart / reload your agent after either.

## Using the engine without an agent

Everything works from a bare clone: `./crux --help` for the verb tour (the root wrapper
forwards to `skills/crux/scaffold/crux.py`), and the cockpit over the bundled example:

```bash
./crux serve --dir skills/crux/examples/segssl_vault
```

## Troubleshooting

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
