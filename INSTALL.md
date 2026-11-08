# Installing crux

The [README](README.md#install) gives the two install commands. This guide covers what gets
installed, the two install paths, verification, updates, removal and troubleshooting.

## Requirements

- Python 3.8 or later. The engine uses only the standard library. `crux.py` prints a clear
  error on an older interpreter.
- git. Both install paths clone from GitHub. On a fresh Mac, run `xcode-select --install`.
- Node.js, for the `npx` path only.

## What gets installed

Each skill under [`skills/`](skills) is one of the following:

| Skill | Role |
|---|---|
| `crux` | The core instructions that the agent always loads, at most 8,192 bytes. This skill also carries the engine (`scaffold/`: the Python CLI, the browser view, and the example vaults) and the `references/` files that the core points to. |
| `crux-wrap` | `/crux-wrap` shows what this session recorded. Then it asks you to accept or reject each pending item. |
| `crux-wiki`, `crux-litsearch` | The literature wiki, and the citation crawl that finds papers the wiki does not have. |
| `crux-autopilot` | Sets up an optimization run against a frozen scorer (`crux auto`). |
| `crux-cockpit` | Starts and stops the read-only browser view (`crux serve`). |
| `prezit`, `storify` | Build slides, or a short private paper, from a question and the nodes under it. |
| `crux-rd` | Writes down a design after it has settled. |
| `evolve-crux` | The workflow for a change to crux itself. |

Every other skill calls the engine inside the `crux` skill. Do not install them without
`crux`.

The subagents are under [`agents/`](agents):

- `crux-capture` records a slice of the transcript into the notebook. It never asks you
  anything.
- `crux-prerun` designs a run before compute is spent.
- `crux-situate` summarizes where a part of the project stands.
- `crux-migrate` reconstructs an existing repository as a notebook.

`crux-tests` ships with `evolve-crux` under `skills/evolve-crux/agents/`. The clone path
links each subagent as `~/.claude/agents/<name>.md`, which is where Claude Code reads
subagents. The `npx` path installs skills only, so use the clone path for the subagents.

The clone path also adds two Claude Code hooks to `~/.claude/settings.json`:

- `SessionStart` runs `crux hook session-start`. It acts only in a repository with a vault.
  The vault can be at the working directory, above it, or one level down (for example
  `./cruxvault`). The hook loads the core instructions into the session. On a new session or
  after `/clear`, it also starts at most one background capture run on Haiku. That run reads
  the transcript text that no earlier run read, and it may call only crux commands. The hook
  prints nothing, and it exits 0 on any error.
- `PostToolUse` runs `crux voice --hook`. It checks that the agent's chat uses plain
  scientific language.

The installer adds each hook once. It keeps every other key in the settings file.

## Path A: the skills CLI

```bash
npx skills add mehdiforoozandeh/crux --all
```

This path works with Claude Code, Cursor, Codex, Windsurf, Copilot CLI and other
[skills.sh](https://www.skills.sh) agents.

- Use `--all`. It selects every crux skill for every detected agent. Without `--all`, a
  plain terminal opens a picker with no skill selected. Inside an agent session, the CLI
  selects every skill.
- The default scope is the project. Skills go to `./.agents/skills` and to per-agent
  folders. Add `-g` to install for your user account (`~/.agents/skills` and your agents'
  config folders).
- Use `-a` to target one agent, for example `-a claude-code -a cursor`. Repeat the flag. The
  CLI rejects a comma-separated list.
- The install is a copy of GitHub `main` at install time. Update it with
  `npx skills update`. Remove it with `npx skills remove`.
- A project-scope install adds `.agents/`, agent folders (`.claude/`, and for some agents a
  visible `agent/` folder) and `skills-lock.json` to the repository. Commit them or add them
  to `.gitignore`.

Restart or reload the agent after you install. Claude Code finds the skills on its own.
Cursor shows them as slash commands such as `/crux`. Windsurf shows them as `@crux`
mentions. Codex lists them under `/skills`.

## Path B: clone and run `./install.sh`

```bash
git clone https://github.com/mehdiforoozandeh/crux
cd crux && ./install.sh
```

The installer links every skill under `skills/` into `~/.claude/skills` (Claude Code) and
into `~/.agents/skills` (Cursor, Codex, Windsurf and Copilot CLI).

- Keep the clone in place, because the skills are symbolic links into it. If you move the
  clone, run `./install.sh` again. If you delete the clone, the skills disappear without a
  warning.
- `SKILLS_DIR=/path/to/dir ./install.sh` installs the skills into that one folder only.
  `AGENTS_DIR=/path/to/dir` does the same for the subagents. The default is
  `~/.claude/agents`.
- Each `agents/<name>/AGENT.md` is linked as `~/.claude/agents/<name>.md`, so Claude Code
  can start each subagent by name. The installer deletes a `crux-*.md` link whose target is
  gone. It never touches a real file or a working link.
- The installer adds the two hooks above.
- You can run the installer again safely. It changes only the links it manages. If a real
  folder has the same name as a skill, the installer leaves the folder in place and reports
  it.
- Run the installer with bash (`./install.sh`). On Debian, `sh install.sh` runs dash and
  fails.

## Verify the install

`crux doctor` checks the install. It checks the Python version, the engine's modules, and
the skill and subagent links. Inside a vault, it also checks whether the vault was written
by an older engine. For each problem, it prints the command that fixes it. It writes
nothing, repairs nothing, and makes no network request.

```bash
crux doctor
```

`crux doctor` exits 0 when nothing is broken, even with warnings, so a script can call it.
It exits 1 when a check fails. `crux doctor --json` prints the report as one JSON object.

To test the engine itself, run its test suite. In a clone, run `./crux selftest`. After an
`npx` install, run `python3 <skills-dir>/crux/scaffold/crux.py selftest`. The suite runs in
seconds, needs no GPU and no model calls, and ends with `ALL GREEN`.

## Update or remove

| | Update | Remove |
|---|---|---|
| Clone path | Run `git pull` in the clone, then `./install.sh`. The installer links new skills and subagents, removes links to deleted subagents, and repairs the hooks. | Delete the skill links from the skills folders, the `crux-*.md` links from `~/.claude/agents`, and the two crux hook entries from `~/.claude/settings.json`. |
| `npx` path | `npx skills update` | `npx skills remove` |

Restart or reload your agent after either change.

### Upgrade from crux 0.x (engine 3.x)

crux 1.0.0 replaced verdicts, the review gate and synthesis nodes with findings and derived
states. A vault migrates on the first crux command that writes to it. Before the migration,
crux backs up the whole vault to `<vault>/.crux/backup-<old version>-<stamp>`. The report
goes to `<vault>/.crux/migrate-4.0-report.json`. The browser view never migrates a vault. It
shows the migration plan under a banner instead. A removed command (`review`, `approve`,
`synthesize`, `task accept` and others) prints one line that names its replacement.

## Use the engine without an agent

The engine works from a plain clone. `./crux --help` lists the commands. The root `./crux`
script forwards to `skills/crux/scaffold/crux.py`. To open the browser view over an example
vault, run:

```bash
./crux serve --dir skills/crux/examples/segssl_vault
```

## Troubleshooting

Run `crux doctor` first. It detects most of the problems below and prints the fix.

- The `npx` picker shows no skill selected. This is the default. Use `--all`, or select
  each crux skill with the space bar.
- macOS shows `git: command not found` or a dialog. The skills CLI clones with your system
  git. Install git (`xcode-select --install`) and run the command again.
- The shell prints `env: python3: No such file or directory`. The engine needs Python 3.8 or
  later on your `PATH`.
- The skills do not appear in the agent. Restart or reload the agent, because agents read
  their skills folders at startup.
- The skills stopped working after you cleaned up your disk. You probably deleted or moved
  the clone that the links point into. Clone it again, or move it back, and run
  `./install.sh`.
- The installer prints `! skip <name> — a real folder exists`. A real folder sits where the
  link should go, and the installer left it in place. Remove or rename the folder if you
  want the link there.
- `crux serve` cannot get a port. Choose one with `crux serve --port 8890`.
- crux prints `crux: not inside a crux vault`. The engine looks for the vault in the current
  directory and the directories above it. Change into the vault (for example `cruxvault/`),
  or pass `--dir` to `serve`.
- crux is not loaded at session start. Check that `~/.claude/settings.json` has a
  `SessionStart` entry that runs `crux.py hook session-start`, and run `./install.sh` again
  if it does not. Also check that the vault is at the working directory, above it, or one
  level down.
- The background capture never runs. It needs the `claude` CLI on your `PATH`, signed in.
  Its log is `<vault>/.crux/sweep.log`.
