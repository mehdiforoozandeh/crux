# crux engine — CLI reference

A self-contained Python 3 (stdlib-only) CLI that maintains a **crux vault**: a
scientific-method lab notebook of markdown nodes you can open as an Obsidian vault.
The agent drives it by default; it's equally usable by hand.

```bash
python crux.py --help          # full tour
python crux.py <verb> --help   # per-verb help
python selftest.py               # build a dummy vault and assert every invariant (no deps)
python selftest.py --keep ./demo # …and keep it so you can open ./demo in Obsidian
```

## The model

- **Project** — the root node (one per vault).
- **Question** (`q*`) — what you don't know. No verifiables of its own; **resolved by aggregating its children**. Nestable.
- **Hypothesis** (`h*`) — a falsifiable, testable leaf under a question. Has `## Verifiables` + `## Findings` + a verdict.

The tree lives in each node's `Parent:: [[…]]` wikilink (so the Obsidian graph draws it). `META.md` and `EXPERIMENTS.md` are **generated** — never hand-edit them.

## Verbs (canonical · aliases)

| verb | aliases | what it does |
|------|---------|--------------|
| `init` | start, new | bootstrap a vault here (`--from seed.md` materializes a whole tree — see **Setup**) |
| `ask` | question, q, meta | open a Question under the project or another question |
| `hypothesize` | hypothesis, idea | add a testable hypothesis under a question (register `-v` verifiables) |
| `test` | experiment, run, stage, launch | advance an idea: `idea → staged → running` (`stage`→staged, others→running) |
| `close` | record, conclude, verdict, land | derive the verdict from ticked verifiables; roll up the ledger |
| `review` | gate, decide | list questions the engine has tripped to `review` |
| `answer` | resolve, settle | resolve a question with a standing answer |
| `pursue` | branch, extend, reopen | keep a question open; optionally spawn a fresh hypothesis |
| `status` | map, tree, where, show | print the tree, or one node's ledger |
| `synthesize` | weave, rollup | optional horizontal synthesis across questions |
| `ingest` | source, add-source | register a PI-curated `raw/` source into the literature wiki |
| `serve` | gui, ui, cockpit | open the read-only browser cockpit over the vault (localhost, view-only) |
| `validate` | lint, check | run all integrity checks (tree + wiki lint, plus economy warnings) |
| `auto` | autopilot | flight plans and runs — `auto check` lints one and dry-runs its scorer (`--static` lints only), `auto brief` assembles the next attempt's brief, `auto guide` appends the PI's guidance, `auto promote` branches a recorded attempt, `auto refs` lists a run's refs (see **Autopilot**) |

Every verb except `init`, `serve` and `selftest` takes `--json`, so a caller reads a result
instead of parsing prose. `crux status --json` is the whole snapshot, `crux status q3 --json`
one node, `crux validate --json` the `{ok, checks, problems, warnings}` report.

## Node economy (v1.3)

Two budgets, both **warnings** — `crux validate` prints them and still exits 0; `--strict`
makes them fail. `--check=tree,wiki,economy,fanout` runs a subset.

- **400 words of prose per node.** Counted: `ELI5`, `TL;DR`, `Question` / `Problem Statement`
  + `Idea / Hypothesis` + `Planned Intervention`, and `Answer so far` / `Findings`.
  **Not** counted: `Verifiables`, `Run Links`, `Artifacts`, and the generated ledger — those
  are structured, they were never the bloat, and capping them would punish thoroughness.
- **5 unrun hypotheses per question.** `hypothesize` warns on the call that would breach it.

Advisory on purpose: an over-cap node's real fix is often to move detail elsewhere, and not
every destination exists yet. `--strict` is how you opt into red.

## Lifecycles

- **Hypothesis:** `idea → staged → running → done`. Can't go `running` without ≥1 verifiable.
- **Question:** `open → review → resolved`. The engine trips `open → review` automatically once every direct child is terminal (idea `done` / sub-question `resolved`). **Closing the question is always a human decision** (`answer` or `pursue`).

## Verdict (mechanical)

On `close`, the engine reads the `## Verifiables` checkboxes:
`- [x]` met · `- [ ]` unmet · `- [-]` could-not-evaluate.
**All met → `supported`** · all-or-some unmet → `refuted`/`partial` · only n/a remaining → `inconclusive`.
The engine never reads run logs — you supply the per-box judgement and a headline `--metric` string.

## A full session

```bash
python crux.py init "My project" --goal "..."
python crux.py ask "Can X improve Y?"
python crux.py hypothesize "A beats B" -p q1 -v "metric ≥ +0.01 vs baseline" -v "no regression on Z"
python crux.py launch h1 --run "job 4012"
# …tick the boxes in h1_*.md (the agent or you), then:
python crux.py close h1 -m "metric +0.012" -f "A wins decisively."
python crux.py review            # → q1 awaits a decision
python crux.py answer q1 -t "A is the load-bearing change."
```

## Setup — `init --from` a seed outline

Standing up a vault node-by-node is tedious. Instead the agent drafts one **seed
outline** (from your docs, your existing repo, or a conversation), you edit/approve it,
and the engine materializes the whole vault in one atomic step:

```bash
python crux.py init --from seed.md --dir cruxvault
```

The seed is an **indented-bullet outline** — indent (2 spaces) = nesting, a type prefix
per line. It's parsed deterministically (stdlib) and fully validated *before* any file is
written, so a malformed seed leaves nothing behind.

```
- Project: CANDI — self-supervised epigenome imputation & denoising
  - Q: Can JEPA improve CANDI?
    - Q: Does a predictive latent help imputation?
      - H: JEPA pretraining beats supervised init      # open idea (not yet run)
        - v: imputation Spearman ≥ +0.01 vs baseline   # a verifiable
        - v: no calibration regression
      - H: [tested] contrastive aux loss lifts peak AUROC   # reconstruct finished work
        - v: [x] peak AUROC ≥ +0.02 (found: 0.71 → 0.74)   # tick = met; (…) = evidence
        - v: [ ] no train-time slowdown
        - finding: net win on peaks; ~15% slower per step.
```

Node kinds and where they may sit (mirrors the model — the parser enforces it):

| prefix | node | parent must be | notes |
|--------|------|----------------|-------|
| `Project:` | project root | — (exactly one, at top) | `TITLE — GOAL` (em-dash or `--` splits goal) |
| `Q:` | question | Project or another `Q` | nests arbitrarily deep |
| `H:` | hypothesis | a `Q` | prefix `[tested]` to reconstruct already-run work |
| `v:` | verifiable | an `H` | optional `[x]`/`[ ]`/`[-]` tick + trailing `(evidence)` |
| `finding:` | finding line | an `H` | one-line narrative for a `[tested]` hypothesis |
| `problem:` | problem statement | an `H` | optional; why it's worth testing |

For a **`[tested]`** hypothesis the engine ticks the verifiables as written, records the
finding, and **closes it** — deriving the verdict *mechanically* from the ticks (`[x]`
met · `[ ]` unmet · `[-]` n/a). It never invents a verdict; you supply the ticks. Fresh
(un-`[tested]`) hypotheses land as open `idea`s to run through the normal flow.

## Autopilot (05.0)

A **flight plan** is the standing contract for an automated search under one anchor question.
It lives at `auto/<qid>/plan.md` — outside the node tree, so it is never itself a node — and
it is an ordinary crux document: flat frontmatter (`anchor`, `mode`, `baseline`, the budgets,
the `frozen`/`writable` paths, the combination `rule`, …) followed by five sections.

| section | what it holds |
|---------|---------------|
| `## Goal` | what the search is for, in prose |
| `## Objective` | three lines — `address::` (a dotted key path into `results/<hid>/metrics.json`), `direction::` (`min` or `max`), `bar::` (a number) |
| `## Null` | the boring explanation every attempt has to rule out — one line |
| `## Verifiables` | the checks every attempt inherits, in the **node format** (`- [ ]`, `[outcome-neutral]`, `fails-if::`, `discriminates::`) and read by the same parser |
| `## Guidance` | the PI's standing instructions to workers — **append-only** |

- `crux auto check <plan>` validates the whole plan and lists every problem at once.
- `crux auto brief <hid>` assembles the brief for the next attempt built on `<hid>`; `--lint`
  prints that brief plus each of the six checks and exits non-zero on a failure.
- `crux auto guide <plan> --author <name> "<text>"` appends one line to `## Guidance`, stamped
  with the time and the author. Nothing else in the file moves, and no entry is ever edited.
- `builds_on: <hid>` on an idea node records which attempt it was branched from.
  `crux hypothesize --builds-on <hid>` writes it, and `crux validate` reports a missing
  target, a target that is not a hypothesis, a target under another question, and a cycle.
  A node without the field validates exactly as before.

**Nothing in 05.0 starts a process.** These verbs read the plan and the vault and stop; the
git layer, the driver loop and the worker agents are later slices.

## Autopilot (05.1) — the git and workspace layer

05.1 adds the impure half: every git, process and concurrency call an attempt needs. It is
still not the loop — nothing here selects an attempt, launches an agent or closes a verdict.
The 05.0 line above now holds for `auto brief`, `auto guide`, `auto refs` and
`auto check --static`; plain `auto check` starts exactly one process, the PI's own scorer.

**Where a run lives.** All of it is git, and none of it is `main`.

| thing | where it is |
|-------|-------------|
| the vault lock | `auto/.lock` — one per vault, carrying the holder's pid, host, time and operation |
| reserved ids | `auto/<qid>/reserved.json` — every id handed out, with its island, parent and state |
| where the run started | `refs/crux/auto/<qid>/base` |
| one attempt | `refs/crux/auto/<qid>/<hid>` — a ref, never a branch |
| the run's branch | `crux/auto/<qid>/run` |
| one island | `crux/auto/<qid>/island/<island>` |
| a promoted attempt | `crux/auto/<qid>/promoted/<hid>` |
| an attempt's worktree | `<git common dir>/crux-auto/<qid>/<hid>`, detached |
| an attempt's workspace | `<first writable root>/<hid>/` |
| an attempt's manifest | `auto/<qid>/manifests/<hid>.json` |

- **The lock** is one file for the whole vault, and it is what makes id reservation safe: two
  attempts never receive the same node id. A lock whose pid is gone on this host, or whose file
  is older than the stale window, is reclaimed once and then held by the reclaimer.
- **An id is reserved before a node exists.** It comes from the engine's counter, under the
  lock, so it can never be handed out twice; the record in `reserved.json` outlives a crash. A
  reserved id that never became a node stays reserved, and `crux validate` does not lint it.
- **Frozen paths** are the plan's `frozen:` entries plus the vault's own path, when the vault
  sits inside the repository. A commit that touches one is **reported**, naming the path.
- **The manifest** records every file under the declared `writable:` roots — path, size,
  mtime — with the attempt's own workspace left out. Re-checking it after the run reports what
  was added, removed or changed outside that workspace. Reported, not judged.
- **Retention** is `retention:` in the plan, and it governs the workspace alone: `all` keeps
  every one, `none` deletes every one, `failed` keeps a workspace whose attempt was refuted,
  invalid or never closed and deletes a supported one. The attempt's ref, its node, its
  `results/<hid>/metrics.json` and its manifest survive every setting, and no worktree is left
  behind by any of them.

**The scorer contract.** `scorer:` is the PI's own command. **Its stdout must be exactly one
JSON object** — that object is written verbatim to `results/<hid>/metrics.json`, and the plan's
`address::` has to resolve inside it to a number. stderr is free text and is read only for an
error message. The command is started with no shell and with exactly two variables added to the
environment it inherits: `CRUX_ATTEMPT` (the attempt's id) and `CRUX_WORKSPACE` (its workspace).

- `crux auto check <plan>` lints the plan as 05.0 did, then dry-runs the scorer once against the
  baseline, writing nothing. It names what failed: `repo` (no git repository encloses the vault
  and the plan sets no `repo:`), `scorer-exit` (it could not start, or exited non-zero — the
  message carries a bounded tail of its stderr), `scorer-timeout`, `scorer-output` (stdout was
  not one JSON object) or `scorer-address` (the objective did not resolve to a number).
  `--static` skips all of that and returns exactly what 05.0 returned.
- `crux auto promote <hid> [--branch <name>]` creates a branch at a recorded attempt, defaulting
  to `crux/auto/<qid>/promoted/<hid>`. No checkout, no merge. It refuses an unknown id, an
  attempt with no recorded ref, and a branch name already taken.
- `crux auto refs [<qid>]` lists the run's refs, its branches and its worktrees. Read-only — it
  creates nothing, not even `auto/`.

Two optional frontmatter fields arrive with the slice: **`repo:`** (where the repository is,
for a vault that does not sit inside it) and **`scorer_timeout:`** (seconds, default 600). A
plan carrying neither validates exactly as it did under 05.0.

**What 05.1 does not do.** No loop — nothing selects, launches, retries, budgets or resumes. No
agents. No verdict closes: a frozen-path or shared-root violation is reported, and the
`invalid-run` close belongs to the next slice. No `state.json` and no `ledger.jsonl` write. No
leash change, and no cockpit. **`main` is never written** by anything here.

## Engine version stamp

`init` records `engine_version` in `.crux.yaml`. On every run against an existing vault,
the engine compares that stamp to its own version; on a mismatch it prints a loud drift
warning and re-stamps (so the change lands as a `git` diff — an auditable record that the
engine moved under a fixed vault). Verdicts depend on both your ticks *and* the engine, so
the version travels with the vault in version control.
