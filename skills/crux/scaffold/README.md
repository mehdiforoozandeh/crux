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
| `auto` | autopilot | flight plans and runs — `auto check` lints one and dry-runs its scorer (`--static` lints only), `auto approve` is the PI's signature on a plan, `auto run` drives an approved plan unattended, `auto status` reads a run's state, `auto brief` assembles the next attempt's brief, `auto guide` appends the PI's guidance, `auto promote` branches a recorded attempt, `auto refs` lists a run's refs (see **Autopilot**) |

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

## Autopilot (05.2) — the driver loop

05.2 adds the loop: `crux auto run` drives an approved flight plan unattended until one of four
stops, and resumes a run it finds on disk. It writes the vault, and it writes it **uncommitted** —
the loop makes no commit on any branch, and `main` is never written.

**Approval is a hash, not a flag.** `crux auto approve <plan>` stamps `approved:` and
`approved_hash:` into the plan's frontmatter — the PI's signature on the plan, and an agent never
runs it without their yes. The hash covers the whole plan **except** the content of `## Guidance`
and the fields `approved`, `approved_hash` and `updated`, so `crux auto guide` leaves an approval
standing and any other edit clears it. Approving twice is idempotent: the first timestamp is the
record. Approval is not a `crux auto check` problem, so every 05.0 and 05.1 plan lints as before.

**`crux auto run <plan> [--max-attempts N]`** refuses — before it writes a byte, reserves an id or
creates a ref — a plan `auto check` reports a problem on, a plan setting `steward: true`, a plan
that is not approved, a plan edited after its approval, a run that has already stopped, and a run
whose driver is still alive. There is no `--resume`: a vault that already holds
`auto/<qid>/state.json` reconciles and continues. `--max-attempts` only tightens `budget_attempts`.

**`crux auto status [<qid>]`** renders `state.json` and stops there — it starts no process, takes
no lock and creates nothing, not even `auto/`.

**One attempt.** The driver picks a parent by PUCT, reserves the id, cuts a worktree at the
parent's commit, and runs the plan's `agent:` command once per try: no shell, `{brief}` replaced in
any argument, nothing on its stdin, and seven variables added to the environment — `CRUX_ATTEMPT`,
`CRUX_WORKSPACE`, `CRUX_WORKTREE`, `CRUX_BRIEF`, `CRUX_PROPOSAL`, `CRUX_SEED` and `CRUX_RUN` (the
plan's run command, which the worker invokes and the driver never does). The worker returns a
commit in its worktree and a JSON object at `CRUX_PROPOSAL`, in the workspace rather than the
worktree, so it cannot land in the commit. Its schema is closed:

```
{"claim": "<the prose that becomes the node's ## Idea / Hypothesis>",
 "controls": [{"text": "<a metric comparison>", "fails_if": "<the world where it fails>"}]}
```

`controls` is optional, and the driver tags every entry `[outcome-neutral]` itself — there is no
field in which a worker can express a claim-directed check.

**The four acts.** The driver, never the worker, writes the vault, and it files each attempt at its
reserved id through four engine acts the plan's approval covers: `hypothesize` (the plan's null,
combination rule and checks copied verbatim, the claim as `## Idea / Hypothesis`, the title its
first sentence capped at 15 words), `approve-null`, `test --to running`, and `close`. The verdict
comes from the unchanged verdict rule; the driver supplies ticks and never a verdict token.
`skills/crux/SKILL.md` carries the ruling that puts these four inside the plan's signature.

**Ticks come from the metrics.** A verifiable whose text begins `<key.path> <op> <number>` — after
its `[kind]` tag and any `(found: …)` note are set aside — is graded from the attempt's metrics.
`<op>` is one of `<=` `<` `>=` `>` `==` `!=`, with `≤` `≥` `≠` accepted as spellings of `<=` `>=`
`!=`. True ticks `[x]`, false `[ ]`, and an address that does not resolve — or no metrics document
at all — ticks `[-]`, which on an outcome-neutral check already derives `invalid-run`. A ticked
line gains the existing `(found: <value>)` note, which the hash lock already excludes from the
commitment, so neither tick nor note raises drift. In this slice **every check in a plan must be a
metric comparison**: `auto check` refuses the rest under a new problem slug `check-grammar`, before
any compute is spent.

**What a run leaves on disk.** `auto/<qid>/state.json` is rewritten whole after every event,
through a temporary file and one rename, so it is never half a document; `auto/<qid>/ledger.jsonl`
is one JSON object per line, appended and never rewritten. Both are written only under 05.1's vault
lock, in the same critical section as the write they describe, so `META.md` can never be torn by
two attempts finishing at once. The ledger's event vocabulary is a closed list of seventeen, and
the driver refuses to write any other: `run-opened`, `attempt-reserved`, `worker-started`,
`worker-done`, `worker-failed`, `node-filed`, `scored`, `violation`, `retry`, `closed`, `confirm`,
`island-best`, `stall`, `escalated`, `abandoned`, `resumed`, `stop`.

**Five phases, and resume trusts the disk.** An attempt is in exactly one phase, recorded before
the work it names, and each phase leaves durable evidence:

| phase | the evidence on disk |
|-------|----------------------|
| `reserved` | an entry in `auto/<qid>/reserved.json` |
| `drafted` | a worktree exists for the id |
| `committed` | `refs/crux/auto/<qid>/<hid>` resolves and the node is in the vault |
| `scored` | `results/<hid>/metrics.json` exists |
| `closed` | the node carries a verdict and retention has run |

Resume reconciles `state.json` against those five facts rather than trusting it, because the kill
may have landed between the fact and the write: a worktree with a commit and no ref is recorded and
carries on, a ref with no metrics is scored, metrics with no verdict are ticked and closed, a
verdict whose later steps did not finish has them finished — never a second close — and a reserved
id with no worktree, or a worktree with no commit, is set `abandoned` and never handed out again. A
worker still alive from the killed driver is waited for first. `CRUX_AUTO_CRASH_AT=<phase>` makes
the driver kill itself the instant that phase is first recorded; it exists for the test suite, and
it has no use in a real run.

**The four stops.**

- **`success`** — an attempt closed `supported`, its objective crossed the bar by the plan's
  direction, and a confirmation passed. The confirmation re-scores **the same commit** at
  `replicates` seeds, `CRUX_SEED=1..N`, none of them the attempt's own seed `0`, writing under
  `results/<hid>/confirm/<seed>/metrics.json` so the attempt's own `metrics.json` stays the
  byte-exact object the scorer printed. A seed that misses does not touch the verdict: the
  confirmation failed, and the run continues.
- **`budget`** — `budget_attempts` attempts closed, `budget_hours` of the driver's own wall clock
  (summed across resumes, so a night spent dead is not charged), or `budget_model_calls` worker
  invocations. Any one axis ends the run, and the axis is named.
- **`abort`** — `abort_invalid_runs` attempts closing `invalid-run` in a row, or the scorer failing
  on the base commit at run open, which is checked in a throwaway worktree before any id is
  reserved.
- **`stall`** — no improvement of an island's best score over `stall_attempts` closed attempts. It
  escalates **once** per run: Climb raises the effective `c_puct` to the Explore value, recorded in
  `state.json` so selection stays reproducible from the file, and Explore sets `steward_requested`
  for a later slice to act on. A second stall ends the run.

**The island-best pointer.** An attempt that closes `supported` and strictly improves its island's
best score (the baseline's score to begin with) moves `crux/auto/<qid>/island/<i>` to its commit by
compare-and-swap. Those pointers, 05.1's `open_run` branch creation and `auto promote` are the only
`refs/heads/` writes the driver makes.

**What is retried, and what is not.** `retries:` covers the failures that are the machine's: a
worker that cannot start, exits non-zero, produces no commit, or leaves a missing or unparseable
proposal or no claim; a claim over the 400-word prose cap; and a scorer that exits non-zero, times
out or prints no JSON object. Each retry re-runs the same step in the same worktree, is logged, and
counts a model call when it re-runs the worker; exhausted, the attempt closes `invalid-run` with a
deterministic finding naming the failure. Three failures are **never** retried, being the worker's
act rather than the machine's: a commit touching a frozen path, a change under a declared shared
root outside every attempt workspace, and a proposal carrying a key outside `{claim, controls}` or
a malformed control (not a `{text, fails_if}` object, its own `[kind]` tag, not a metric
comparison, or a repeated failure scenario). Each of the three closes `invalid-run` at once. An
over-cap claim is refused rather than truncated, because a truncated claim files a node whose claim
is not what the attempt tested. A scorer whose output parses but whose objective does not resolve
is not retried either — the document exists, and the ticks decide.

**One task per run.** At the stop the driver files one task naming the run's best closed attempt
and its derived verdict, then marks it done with that node as the output, so it lands in
`crux task review` beside the merge decision the PI makes in the morning. A run that closed no
attempt files an ordinary done task instead. An `abort` stop, and any attempt that exhausted its
retries, each file one open task, which puts the exception in the frontier. Every task the driver
files carries the category `autopilot`, which it declares the ordinary way when the vault does not
already list it.

**What 05.2 does not do.** No agents: the `agent:` command is run as a subprocess exactly as
written, once per try, and a stub script stands in for it. No steward — `steward: true` is refused
— and no new islands. No cockpit, and no setup skill. No prose checks, and no new verdict path.
**No commits**: vault writes stay uncommitted in the checkout that holds the vault, the run branch
receives no commits, and `main` is never written, checked out or merged. No report link — the
driver writes `results/<hid>/metrics.json` but links no report under `## Artifacts`, so `validate`'s
existing "files but no report" problem fires on attempt nodes, as it already does on the 05.0 and
05.1 fixtures. `crux auto check`'s own output is unchanged; the approval state is read by
`auto run` and `auto status`.

## Engine version stamp

`init` records `engine_version` in `.crux.yaml`. On every run against an existing vault,
the engine compares that stamp to its own version; on a mismatch it prints a loud drift
warning and re-stamps (so the change lands as a `git` diff — an auditable record that the
engine moved under a fixed vault). Verdicts depend on both your ticks *and* the engine, so
the version travels with the vault in version control.
