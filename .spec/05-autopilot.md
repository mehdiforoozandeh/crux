# Spec 05 — Autopilot: crux run unattended

**Label:** `autopilot` · **Status:** ◐ in progress
**Supersedes:** the former spec 04 (ERA: empirical program search), merged in below
**Superseded in part by:** [09 specialized agents](09-specialized-agents.md) (the Proposer/Closer split)
**Depends on:** [06 node economy](06-node-economy.md) · [08 taskhub](08-taskhub.md) ·
[09 specialized agents](09-specialized-agents.md) · [15 evidence semantics](15-evidence-semantics.md)

> **Unparked 2026-09-16**, and renamed from `autoresearch`. The deferral of 2026-08-15 said
> this must not be built until [15](15-evidence-semantics.md) and
> [09](09-specialized-agents.md) shipped — 15 to stop a loop banking a partial answer as a
> result, 09 to stop it grading its own homework. Both shipped in v0.6.0. The name changed
> because `autoresearch` now belongs to a much better-known repository, and because crux
> already owns the **cockpit**: autopilot completes that metaphor and states the leash by
> itself — the pilot in command is always the human.

## Goal

Run one anchor question unattended, against a goal and a bar the PI fixes **before** the
loop starts, so that a question well suited to brute-force search — reproducing a paper's
numbers, sweeping a space, hunting a better method — can be pursued overnight without
turn-taking, and read back in the morning as ordinary crux: questions, hypotheses, checks,
verdicts, artifacts.

**The PI's required acts reduce to three, and none of them is mid-run.**

| When | What |
|---|---|
| Before | approve the flight plan |
| After | answer the anchor question, if it is answered |
| After | merge what they want into `main` |

## What it is not

Not an autonomous scientist. The loop cannot change its objective, its bar, its checks, or
its anchor. It searches inside a frame the PI built, and every result it records is derived
from that frame rather than argued for.

## Design

### 1 · The tree is the search state

The three published systems this draws on all keep a flat pool of programs plus a scalar.
Crux already has a structure that carries more: the subtree under the anchor **is** the
population, each hypothesis is one candidate, its pre-registered verifiables are the bar,
and `supported`/`refuted` is Karpathy's keep-or-discard made explicit and auditable.

Three things follow that no flat pool can do:

- **`invalid-run` separates a broken tool from a wrong idea.** ERA scores a crash and a
  null result identically at `-1e9` and abandons the node. Crux retries a crash and keeps
  the hypothesis alive.
- **A refuted sibling carries a written reason.** Spec 09 requires a failure scenario on
  every check, written before the run. A refuted attempt can therefore tell the next worker
  *what broke and where*, in words. Every surveyed system keeps a failure only as a low
  number. This is the cheapest advantage the design has.
- **Replicates are a methodology slot**, so noise is handled at the bar rather than by
  hoping.

### 2 · Selection — one rule, two settings

**Flat PUCT over the island's attempts**, the rule ERA vendors as `futs.py`: rank score plus
an exploration bonus that decays with visits, with ancestor visits back-propagated so an
over-mined lineage cools. One rule and not two, because Karpathy's greedy climb is exactly
this rule at zero exploration — a special case, not a rival.

The PI picks a **setting** at setup, by the shape of the problem rather than by citation:

| | Climb | Explore |
|---|---|---|
| exploration | none — always branch from the best | on |
| islands | one | two to five |
| attempts in flight | one | one per island |
| output | the best | a diverse portfolio |
| **fits** | a smooth landscape where gains accumulate: reproducing a stated number, tuning, closing a known gap | a rugged landscape where several approaches are plausible: "is there a better method", architecture or algorithm search |
| **fails** | when the best is a dead end — every remaining attempt digs one hole | when the budget is small; breadth needs attempts to pay for itself |

A run may be moved from Climb to Explore mid-flight, because the tree state is the search
state and nothing needs converting.

### 3 · Islands are sub-questions

AlphaEvolve keeps parallel populations that occasionally exchange solutions. Crux draws
those already: a sub-question under the anchor partitions the approach space. *Does the
optimizer explain the gap? Does the data pipeline?*

- Islands are named at setup and may be opened by the loop up to a declared cap.
- Opening one is safe **because the objective, bar and checks are frozen**. A new island is
  another angle on a fixed target, so it cannot drift into a new direction.
- Migration is a brief slot: a worker may be shown another island's best, at a low rate.
  Without it the islands never learn from each other; with too much they collapse into one.

**MAP-Elites is deliberately not adopted.** It needs behaviour descriptors written per
problem, and nobody will write them for a one-off reproduction.

### 4 · Attempts are flat siblings

The engine requires `idea parent must be a question`, so a hypothesis cannot hold a child.
That constraint is kept, and it is right: the tree answers *what we do not know and what we
tested*, not *what we tried in what order*. Two attempts at "does momentum close the gap"
are siblings whether one followed the other or not.

Lineage lives in three places that already fit it:

- **git ancestry** — an attempt's commit is a child of its parent's commit;
- **`builds_on:`** on the idea node — the bandit's parent link and the cockpit's edge;
- **the island's `## Answer so far`** — the current best and its score.

**Rejected: a sub-question per advance.** Depth would track iteration count, a night would
produce a chain hundreds deep, and each question would need resolving — a gate backlog
manufactured out of bookkeeping.

**Rejected: a finding as parent.** A finding is evidence, not a question. Making it a parent
would put search order into the science tree, which is git's job and the taskhub's job.

### 5 · Three roles, three lifetimes

No agent lives longer than one step. The vault and git are the only memory.

| role | kind | sees | lifetime |
|---|---|---|---|
| **driver** | plain Python, no model | vault state | the whole run |
| **worker** | fresh agent per attempt | its brief only | minutes |
| **steward** | fresh agent, periodic, Explore only | the ledger only | minutes |

**Rejected: an LLM orchestrator.** After a few hundred attempts its context is full, so it
forgets or compacts; the loop's memory becomes chat history rather than the vault; and it is
the one agent that has seen everything, which is the bias spec 09 exists to prevent.

The **driver** owns everything deterministic: selection, budget, id allocation, worktrees
and references, launching runs, ticking from metrics, deriving verdicts, moving the island
pointer, regenerating the index files, resume.

The **steward** is the judgment an orchestrator would supply, without the context: is the
search stalled, is an island starving, should the guidance change. It may edit guidance
inside the plan's limits. It may never widen the plan and never merge.

### 6 · The attempt lifecycle

The worker does **not** live through the run. A four-hour job would otherwise hold an agent
open for four hours and let its context rot.

1. **driver** — select parent (PUCT, with a virtual visit if more than one is in flight),
   reserve the node id centrally, cut a worktree from the parent's commit.
2. **worker** (fresh, short) — read the brief, propose the claim, write the code, file the
   hypothesis, commit, exit.
3. **driver** — run the frozen scorer, read the number from its output, write
   `results/<hid>/metrics.json`, check the manifests.
4. **`crux-close`** (fresh, short, unchanged from spec 09) — read the output, draft the
   ticks and the findings.
5. **driver** — derive the verdict, close, move the pointer, save the reference, drop the
   worktree.

Only steps 2 and 4 call a model. This is what makes waiting free, and it separates the two
concurrency knobs the survey found in ShinkaEvolve: how many attempts are being *drafted*
(model-bound) and how many are *executing* (compute-bound).

### 7 · Parallelism

- **Across islands: always safe.** Separate sub-questions, separate worktrees.
- **Within an island: allowed, and it costs information.** Every attempt started before its
  sibling reports is one less observation guiding the next choice. Above one per island the
  virtual-visit rule is required, which counts a pending attempt as if it had reported.
- **Never parallel:** node id allocation and index regeneration. Both are driver-only,
  serialized behind a lock. These are the two collision risks, and refusing to parallelise
  them is the whole fix.

Defaults: one attempt at a time in Climb, one per island in Explore.

### 8 · Git

The tree of attempts and the git graph are the same shape, so one holds the other.

| visible branch | what it is |
|---|---|
| `main` | **only the PI merges here.** The loop never touches it. |
| run branch | cut at setup; every write the loop makes lands under it |
| island branch | one per sub-question, each with its own worktree |
| island-best | a pointer moved when an attempt closes `supported` and improves the score |

An **attempt is a commit under `refs/crux/auto/<qid>/<hid>`**, not a branch. A git reference
is a label pointing at a commit; labels outside `refs/heads/` are just as permanent and
reachable but stay out of branch listings. DVC reached the same conclusion from experience:
it keeps trials as commits linked to their base and promotes one to a real branch only when
a human keeps it, precisely because a branch per trial does not survive hundreds of trials.
`crux auto promote <hid>` performs that promotion.

**Island best is a pointer, never a union.** Two supported siblings are never git-merged
into each other. Recombination happens only through the next worker's brief.

A refuted or invalid attempt keeps its reference and its node. The record is the point.

### 9 · The flight plan

One file on the run branch. The driver reads only this. Everything the loop does later
traces to something the PI approved here. `crux auto check` validates it, and dry-runs the
scorer on the current code, before anything starts.

**The science**

1. anchor question · 2. goal, in one falsifiable sentence · 3. the objective: which number,
where it is addressed in the metrics file, and which direction is better · 4. the success
bar · 5. abort conditions · 6. the null, PI-approved (`crux-null`) · 7. the inherited
checks, their kinds and combination rule (`crux-verifiables`), including at least one
outcome-neutral control · 8. replicates per attempt.

**The machinery**

9. mode · 10. islands and the island cap · 11. the scorer command and the paths it owns
(these become frozen) · 12. the run command · 13. writable roots · 14. budget · 15.
parallelism, total and per island · 16. retries before an attempt is called invalid · 17.
workspace retention · 18. steward on/off and interval · 19. the guidance text workers read ·
20. the agent command template and its failover list.

**The baseline.** Setup ends by scoring the current code and recording it. Both reference
systems need a starting point with a score; without one the bandit has nothing to rank
against. Terminal hypotheses already under the anchor are adopted as further starting
observations.

**The objective must come from a check that discriminates against the null.** Optimizing a
bar the hypothesis was always going to clear is the machine-scale form of the bias spec 09
exists to prevent: the search will clear it, thousands of times, at cost, and teach nothing.
This is the single most important line in the plan.

### 10 · Guardrails, all deterministic

- **The scorer is frozen and the driver runs it.** The metric is read from the command's
  output, never from a file the worker last touched. A 2026 benchmark of ML-engineering
  agents found tampering with the evaluator in about half of unguarded episodes, and found
  that making the evaluator unwritable removed it. Weco's CLI independently uses the
  read-from-stdout form. A worker commit touching a frozen path closes the attempt
  `invalid-run`.
- **One workspace per attempt, named by its id**, so two attempts cannot produce the same
  path. Weco reached the same rule: key output by a stable candidate id, never a step
  number, because attempts finish out of order.
- **A manifest over the declared shared roots** — path, size, modification time — recorded
  before the run and re-checked after. Any change outside the workspace closes the attempt
  `invalid-run`. This is what catches writes to a shared scratch or dataset directory that
  git cannot see.
- **A worker may add outcome-neutral controls; it may never add, remove or weaken a
  claim-directed check.** Safe by construction: a control can only invalidate a run, never
  validate one, so a worker can only ever raise its own bar. This is why the usual
  prohibition on an agent writing its own bar does not apply here.
- **Sandboxing is the project's, not crux's.** The engine is standard-library-only and
  domain-agnostic; a scorer that executes candidate programs is neither. Crux defines the
  contract and records the run. Containment belongs in the run command.

### 11 · Stops

Four, each reported by name.

- **success** — the objective crossed the bar *and* the attempt closed `supported`, which
  already requires the control to pass. The winning attempt is then **re-run at different
  seeds** before success is declared. A winner's score comes off one evaluation, and a lucky
  seed is the likeliest way an overnight run hands back a false result.
- **budget** — attempts, wall clock, or model calls; any one ends the run. A compute cap in
  GPU-hours or job time is a fourth axis where the runner can measure it. Money is not an
  axis: under subscription authentication there is no price per call to count.
- **abort** — invalid runs in a row over a threshold, the scorer itself failing, or repeated
  frozen-path violations.
- **stall** — no improvement in N attempts. **Self-escalates once**: Climb widens
  exploration, Explore asks the steward to revise the guidance. A second stall ends the run.

**Rejected: a `converged` stop.** Research has no finish line, and the loop judging for
itself that nothing is left to learn is exactly the claim it is not entitled to make. A
success stop is legal for the opposite reason: the bar was *pre-registered*, so the loop is
reporting a crossing rather than forming an opinion.

A provider rate limit **fails over and retries** with a cooldown and re-probe, as the ERA
skill already does. It is the likeliest overnight interruption and must never cost a night.

### 12 · Verdicts, and the leash

**Ruling (PI, 2026-09-16).** Inside an approved autopilot run, an attempt closes on its
derived verdict with no per-attempt signature.

This is a change to how the leash reads, and it is written into `skills/crux/SKILL.md`
explicitly rather than left implied. The justification is spec 15: verdict derivation became
a total function of the check kinds, the combination rule, and the pass/fail vector. A
verdict stopped being a judgment and became arithmetic. **What the PI signs is the bar**,
and in an autopilot run the bar is signed once, in the flight plan, and inherited by every
attempt. The signature moved earlier; it did not disappear.

Outside an autopilot run, nothing changes.

Still the PI's, inside a run: `answer`, and merging into `main`.

### 13 · The brief

Three authors, three lifetimes. **The engine assembles the facts** — a pure read, byte-stable,
as `crux brief` already is. **We write the standing instructions** once, in
`agents/crux-auto-worker/AGENT.md`, changed by pull request. **The PI writes the guidance**,
appended with a timestamp and author, never overwritten — so a ledger reader can see which
guidance was in force for which attempts.

| in | out |
|---|---|
| goal, objective, direction, current best | this conversation |
| the island question | the anchor's `## Problem Statement` — where the advocacy lives |
| parent attempt: claim, diff, score, findings | other islands, beyond the migration slot |
| inspirations: strong attempts with diffs; **refuted siblings with their failure scenarios** | raw run logs of other attempts |
| the inherited null, checks, combination rule | write access outside its worktree and workspace |
| the PI's guidance | |
| budget remaining on every axis | |

The worker **does** see the exact numeric bar. Every surveyed system tells its agent the
metric, and it cannot do the job otherwise. Secrecy is not the protection; the frozen scorer
and the outcome-neutral control are.

**Six deterministic checks on the assembled brief**, because "complete, succinct, informative"
has to be code rather than opinion:

1. a declared schema with required slots — assembly fails loudly on a missing or empty one,
   the same instinct as `brief` refusing an unknown mode rather than defaulting;
2. a budget **per section**, so twelve inspiration diffs cannot crowd out the objective;
   overflow is cut by a declared rule and the brief says that something was cut;
3. byte-stability, so two briefs diff to exactly what changed in the vault;
4. leakage assertions — the excluded column above is tested, not trusted;
5. every number resolves to a live vault address, reusing the contract behind
   `crux deck --verify`, so a stale "current best" is impossible;
6. `crux auto brief <hid> --lint` prints exactly what a worker will see, before any spend.

**Rejected: automatic prompt evolution** (AlphaEvolve's meta-prompt database). It is a second
search loop stacked on the first, it makes a run irreproducible, and the steward covers most
of the gain under limits the PI approved.

### 14 · The taskhub

**The run is one task; attempts are not.** A run is planned work, so it gets a task under the
anchor referencing it, which makes it an experiment task; accepting it is the PI's existing
signature for taking in its evidence, and it pairs with the merge decision. An attempt is not
planned work — it is generated by a search and its record already exists as a hypothesis node
with a verdict, checks and artifacts. One task per attempt would duplicate that record and
put hundreds of rows in a tab meant to be read at a glance.

**The exception earns a task.** An attempt that fails repeatedly, or a stop needing
investigation, creates one task — which puts it in the frontier query, where the PI looks for
work that needs a person.

### 15 · The cockpit

A fourth tab, read-only like the rest, with two views on a rail as the Taskhub already has.

- **Live** — the score against attempt number, which is how Karpathy's loop is judged and the
  fastest read on whether this is working; what is in flight per island; the budget axes; the
  ledger.
- **Results** — the lineage from `builds_on`, and a **diverse portfolio** rather than a single
  winner. ERA returns top-k diverse deliberately, because one score is one evaluation and the
  useful output is several distinct strong approaches.

Clicking an attempt opens it in the existing detail reader. The tree tab carries a live-run
mark, or nodes appear with no explanation and it reads as a bug.

**Its data is served from its own small endpoint**, not the tree snapshot. The snapshot caches
on a vault change key — a 33x speedup measured in spec 12 — and a running loop would
invalidate it on every attempt, forcing a full tree rebuild each time. ERA validates the
shape: its entire search state is one small file rewritten after every node, which is what
makes a run inspectable mid-flight and resumable after a crash.

### 16 · The wiki

Read, never written. The wiki's direction is already fixed by its own skill: literature
informs the tree, and a project's own findings never flow back. Autopilot changes nothing.

## Decisions

| # | settled | why |
|---|---|---|
| D1 | crux-native design; the tree is the search state | reuses every layer; the review surface is the tree the PI already reads |
| D2 | one selection rule, flat PUCT; Climb is `c_puct = 0` | one code path is easier to make safe than two |
| D3 | islands are sub-questions | the one place the tree beats a flat pool |
| D4 | attempts are flat siblings; lineage in git + `builds_on:` | tree depth must track questions, not iteration count |
| D5 | driver + per-attempt worker + periodic steward | no long-lived context anywhere |
| D6 | the worker's life is short; runs happen without it | decouples thinking rate from compute rate |
| D7 | attempts are commits under a hidden ref namespace | DVC's finding: a branch per trial does not scale |
| D8 | the PI is the only one who merges into `main` | the hard line |
| D9 | the scorer is frozen; the driver runs it; the metric is read from its output | measured: ~50% tampering unguarded |
| D10 | one id-named workspace per attempt + a manifest over shared roots | git cannot see writes outside the repo |
| D11 | verdicts close without a per-attempt signature inside an approved run | spec 15 made a verdict arithmetic; the bar is what gets signed |
| D12 | four stops; success requires a confirmation run at new seeds | one evaluation is noise |
| D13 | stall self-escalates once, then ends | keeps the run free of required mid-run acts |
| D14 | new islands without asking, up to a cap | safe because the objective is frozen |
| D15 | one task per run; attempts are not tasks; exceptions are | the taskhub is for planned work and for what needs a person |
| D16 | the brief is engine-assembled and checked by code | "complete and succinct" must not be an opinion |
| D17 | a worker may add controls only | a control can only raise its own bar |
| D18 | the agent command is a configurable template with failover | preserves the agent-agnostic claim |
| D19 | impure code lives in `autopilot.py`; the engine stays pure | keeps the engine testable without a cluster |
| D20 | named autopilot; verb `crux auto`; the file is the flight plan | completes the cockpit metaphor; avoids a name collision |

## Rejected alternatives

- **A replica of Karpathy's loop beside crux** — a flat log that bypasses the tree, so
  nothing it learns is a question or a hypothesis.
- **An LLM orchestrator** — context death, and the one agent that sees everything.
- **A sub-question per advance**, and **a finding as parent** — see section 4.
- **A `converged` stop** — see section 11.
- **MAP-Elites** — see section 3.
- **Explicit code crossover.** What has worked is recombination *through the prompt*
  (AlphaEvolve's inspirations; ERA's pairing of two published methods). Splicing two lineages
  without a model mediating breaks programs.
- **Automatic prompt evolution** — see section 13.
- **A branch per attempt** — see D7.
- **Money as a budget axis** — not measurable under subscription authentication.

## Open questions

- Whether the steward earns its place, or whether guidance should only ever change by the
  PI's hand. It ships behind a switch, off in Climb, so this is answerable with evidence.
- The migration rate between islands, which has no principled default and will need tuning
  against a real run.
- Whether two concurrent runs in one vault are worth supporting. The lock makes it safe;
  nothing else recommends it.

## Work items — the PRD series

- ☑ **05.0 — the flight plan and the brief.** Engine-only, pure, no processes: schema,
  `builds_on:`, validation, PUCT arithmetic, brief assembly with the six checks, the lint
  verb. Entirely testable in selftest without a model, a GPU or a network.
- ☑ **05.1 — the git and workspace layer.** Worktrees, the reference namespace, id
  reservation, the lock, workspaces, the manifest, retention, promote.
- ☐ **05.2 — the driver loop.** Selection, the four stops, budget, retries, resume, the
  ledger, the state file. Tested end-to-end against a stub generator — tier 0.
- ☐ **05.3 — the agents.** `crux-auto-worker` and `crux-auto-steward`; the agent command
  template and failover; `crux-close` wired in unchanged; eval fixtures.
- ☐ **05.4 — the cockpit tab.** Endpoint, two views, the live mark on the tree.
- ☐ **05.5 — the setup skill.** The conversation that produces a flight plan, calling
  `crux-null`, `crux-verifiables` and `crux-design`.
- ☐ **05.6 — validation on real problems.** Tiers 1 to 3.

## Acceptance criteria

- [x] A flight plan that omits a required slot is **refused**, naming the slot.
- [x] A flight plan whose objective does not come from a null-discriminating check is refused.
- [ ] `crux auto check` fails when the scorer cannot run, when it prints no parseable number,
      or when no agent command is reachable — before any attempt starts — the two scorer
      halves are delivered by 05.1; the agent-command reachability third is 05.3's.
- [x] Two attempts never receive the same node id, under concurrency, asserted in selftest.
- [ ] An attempt that writes a frozen path closes `invalid-run`, never `refuted`.
- [ ] An attempt that changes anything under a declared shared root outside its own workspace
      closes `invalid-run`.
- [ ] A crash closes `invalid-run` only after the configured retries are exhausted.
- [x] The assembled brief contains no string from the anchor's `## Problem Statement`.
- [x] Two briefs for the same vault state are byte-identical.
- [x] Every number in a brief resolves to a live vault address.
- [ ] A run killed at any point resumes with no attempt lost and no attempt repeated.
- [ ] Success is declared only after a confirmation run at different seeds passes.
- [ ] No verdict outside an autopilot run closes without a PI signature — the existing leash
      is unchanged elsewhere, asserted in selftest.
- [ ] `main` is never written by the loop, asserted by a test that runs a full tier-0 search
      and diffs `main`.
- [x] An existing vault with no autopilot fields loads unchanged under the new engine version.
