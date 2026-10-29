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
| `auto` | autopilot | one search per anchor — `auto check` runs the setup check on a plan (`--static` reads the plan only), `auto run` runs or continues the search, `auto status` reads a run's ledger (see **Autopilot**) |

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

## Autopilot (spec 18)

The autopilot searches one anchor question unattended against a threshold the PI fixes
before the run. The driver is `auto.py`: plain Python, no model of its own. The design is
[`.spec/18-autopilot-lean.md`](../../../.spec/18-autopilot-lean.md).

**The plan** is `auto/<anchor>/plan.md`: a `---` frontmatter of `key: value` lines, then free
text, which is the PI's guidance. An unknown field is refused, so an old spec-05 plan is refused
too, with a message that names the new fields. Old runs stay readable: their nodes are ordinary
nodes.

| field | meaning | default |
|---|---|---|
| `anchor` | the question id the run serves | required |
| `repo` | the program's git repo, absolute or relative to the vault root | required |
| `base` | the commit or ref the run starts from | required |
| `editable` | comma-separated repo paths the worker may change (a trailing `/` is a directory) | required |
| `scorer` | the frozen command, split with shlex, no shell | required |
| `objective` | `<address> <min\|max> <bar>`; the address is a dotted path to a `{"value": n}` leaf, and `<bar>` is the threshold (the plan's `bar` field) | required |
| `mode` | `climb` (always build on the best) or `explore` (ERA flat PUCT, c_puct 1.0) | `climb` |
| `budget_hours` | the run's budget, read only between attempts | `8` |
| `attempt_minutes` | one limit per attempt, worker plus scorer | `20` |
| `worker` | `<model> <effort>`, effort one of low, medium, high, xhigh, max | `opus high` |

**The scorer contract.** The scorer runs in the attempt's worktree, with `CRUX_WORKSPACE` (a
scratch directory) and `CRUX_ATTEMPT` (the attempt number) in its environment. It prints one
JSON object. A wrong candidate prints `{"passed": false, "reason": …}` and exits non-zero.
Correctness, anti-cheat and noise handling live inside the scorer; the driver does not repeat
them.

**The worker** is `claude -p --model <model> --effort <effort> --permission-mode
bypassPermissions --disallowedTools WebFetch WebSearch`, with the brief on stdin
(`CRUX_AUTO_CLAUDE` replaces `claude`). The brief carries the objective, the editable paths, the
guidance, the parent's and the best score, and the last five outcomes. The worker ends with one
git commit; its subject line is the claim and becomes the node's title.

**The seven rules.**

1. **Allowlist.** The attempt's diff against its parent may touch only `editable` paths, or the
   attempt is `discarded`.
2. **Fail, do not crash.** A crash, a timeout, no commit or a missing number is one `failed`
   attempt; the run goes on.
3. **Rejected is not broken.** `passed: false` is `rejected`, with no retry. Only a scorer that
   cannot start is retried, once.
4. **One time limit.** `attempt_minutes` covers the worker and the scorer together.
5. **Keep.** Every valid attempt is `kept`. The parent comes from PUCT over the kept attempts:
   c_puct 0 in climb, 1.0 in explore. Before any kept attempt, the parent is `base`.
6. **Setup check.** The base must score; the score must change when the first editable file
   is emptied; the worker must make a commit once; the worker command must deny the web tools.
7. **One budget.** `budget_hours` is read between attempts, so an attempt in flight finishes.
   A provider rate limit waits (`CRUX_AUTO_RATE_WAIT` seconds, default 300) and is never a
   failure.

**Recording.** Each attempt is one hypothesis under the anchor, `builds_on` its parent, with
one check: the objective strictly better than the parent's score. The driver files it, approves
its fixed null, runs it and closes it, with no model call. Kept and better is `supported`; kept
and not better is `refuted`; rejected, failed or discarded closes as invalid with the reason.
Each attempt runs in a detached worktree at `auto/<anchor>/work/<n>`; a committed attempt keeps
its commit under `refs/crux/auto/<anchor>/<n>` in the repo. No branches, and `main` is never
written.

**The ledger** `auto/<anchor>/ledger.jsonl` is the whole run state: one `setup` line, one
`attempt` line per attempt (`n`, `id`, `parent`, `commit`, `score`, `status`, `reason`,
`seconds`), and one `stop` line (`budget`, `max_attempts`, `setup` or `crash`). A second `run`
continues from it. Worker logs go to `auto/<anchor>/logs/`.

**Verbs**, each with `--json`:

- `crux auto check <plan> [--static]` runs the setup check of rule 6 and prints the baseline.
  `--static` reads the plan alone and starts nothing.
- `crux auto run <plan> [--max-attempts N]` runs or continues the search until the budget.
- `crux auto status [<qid>]` reads the ledger: best, attempts, attempts per hour, and the stop.
  The cockpit's Autopilot tab shows the same payload.

On Fir, `bash examples/autopilot/run-fir.sh <bench>` submits one benchmark as a SLURM job.

## Engine version stamp

`init` records `engine_version` in `.crux.yaml`. On every run against an existing vault,
the engine compares that stamp to its own version; on a mismatch it prints a loud drift
warning and re-stamps (so the change lands as a `git` diff — an auditable record that the
engine moved under a fixed vault). Verdicts depend on both your ticks *and* the engine, so
the version travels with the vault in version control.
