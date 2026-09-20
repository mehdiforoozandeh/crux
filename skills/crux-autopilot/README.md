# crux autopilot

Run one anchor question unattended, against a goal and a bar you fix **before** the loop
starts — so a question suited to brute-force search (reproducing a paper's numbers, sweeping
a space, hunting a better method) can be pursued overnight without turn-taking, and read back
in the morning as ordinary crux: questions, hypotheses, verifiables, verdicts, artifacts.

It is not an autonomous scientist. The loop cannot change its objective, its bar, its checks
or its anchor. It searches inside a frame you built.

**Your required acts are three, and none of them is mid-run.**

| when | what |
|---|---|
| before | approve the flight plan — `crux auto approve` |
| after | answer the anchor question, if it is answered |
| after | merge what you want into `main` |

## How a run works

```mermaid
%%{init: {"theme":"base", "flowchart": {"wrappingWidth": 600, "nodeSpacing": 40, "rankSpacing": 45}} }%%
flowchart TB
  classDef pi fill:#fde68a,stroke:#b45309,color:#1c1917
  classDef drv fill:#dbeafe,stroke:#1d4ed8,color:#1c1917
  classDef agt fill:#dcfce7,stroke:#15803d,color:#1c1917
  classDef bad fill:#fee2e2,stroke:#b91c1c,color:#1c1917

  subgraph SETUP["1 · Setup — a conversation with the PI, five acts, three asks and two approvals"]
    direction TB
    A0(["crux-autopilot skill — the flight plan is written here, in dialogue,<br/>and every slot it does not ask for is derived, measured, or defaulted"]):::agt
    A1["ask · the anchor question, and the goal in one falsifiable sentence"]:::pi
    A2["approve · the null, proposed by crux-null"]:::pi
    A3["derived · verifiables against that null — kinds, combination rule,<br/>and at least one outcome-neutral control (crux-verifiables)"]:::agt
    A4["derived · the objective address, read off the discriminating check<br/>— never chosen first, or the search clears a bar it was always going to clear"]:::agt
    A5["ask · direction and bar · ask · the harness: scorer, run command,<br/>frozen paths, writable roots, budget"]:::pi
    A6["measured · the baseline, from crux auto check dry-running the scorer"]:::drv
    A7["approve · crux-design's verdict on the design"]:::pi
    A0 --> A1 --> A2 --> A3 --> A4 --> A5 --> A6 --> A7
  end

  SIGN{{"crux auto approve — the PI's signature, on a hash of the plan.<br/>Spec 15 made a verdict arithmetic, so what is signed is the bar, once."}}:::pi
  A7 --> SIGN --> L1

  subgraph LOOP["2 · The run — the driver is plain Python, no model; no agent outlives one step"]
    direction TB
    L1["select the parent attempt — flat PUCT over the island's attempts<br/>(Climb is the same rule at c_puct = 0); reserve the node id under the lock;<br/>cut a worktree from the parent's commit"]:::drv
    L2["assemble the brief — engine-side and byte-stable: goal, objective, bar, current best,<br/>the island's sub-question, the parent's claim + diff + score,<br/>refuted siblings with their failure scenarios, the inherited null and checks, guidance"]:::drv
    L3["crux-auto-worker, fresh per attempt — propose the claim, change the program,<br/>file the hypothesis, commit under refs/crux/auto/qid/hid, exit"]:::agt
    L4["the driver runs the frozen scorer and parses the metric from its output,<br/>never from a file the worker touched; writes results/hid/metrics.json"]:::drv
    L5["crux-close, fresh — draft the per-verifiable ticks and the findings"]:::agt
    L6["the driver derives the verdict from kinds + combination rule + pass/fail vector,<br/>closes the node, moves island-best if the score improved, drops the worktree"]:::drv
    L1 --> L2 --> L3 --> L4 --> L5 --> L6
    G["invalid-run, not refuted — a commit touching a frozen path ·<br/>a change under a declared shared root outside the attempt's workspace (manifest diff) ·<br/>a crash past its retries. A broken tool is not a wrong idea."]:::bad
    L4 -.-> G -.-> L6
    ST["crux-auto-steward — periodic, Explore only, sees the ledger alone:<br/>stalled? starving island? revise guidance, or open one island up to island_cap"]:::agt
    ST -.->|"never widens the plan, never merges"| L2
  end

  L6 --> CHK{"stop?"}:::drv
  CHK -->|"no"| L1
  CHK -->|"yes"| STOPS

  subgraph STOPS["3 · Four stops, each reported by name"]
    direction LR
    S1["success — objective past the bar and the attempt closed supported,<br/>then re-run at different seeds before success is declared"]:::bad
    S2["budget — attempts, wall clock, or model calls"]:::bad
    S3["abort — the scorer itself failing, invalid-runs in a row, frozen-path violations"]:::bad
    S4["stall — no improvement in N; self-escalates once<br/>(Climb widens exploration, Explore asks the steward), then ends"]:::bad
  end

  STOPS --> P1

  subgraph AFTER["4 · After — what stays the PI's"]
    direction TB
    P1["answer the anchor question, if it is answered — read back as ordinary crux:<br/>hypotheses, checks, verdicts, artifacts, and a portfolio rather than one winner"]:::pi
    P2["merge into main — the loop never writes it. crux auto promote turns<br/>an attempt's ref into a branch worth keeping."]:::pi
    P1 --> P2
  end
```

## The parts, in one line each

- **The flight plan** — one file, `auto/<qid>/plan.md`, twenty slots plus a baseline. The
  driver reads only this, so everything the loop does later traces to something you approved.
  The `crux-autopilot` skill writes it with you in five acts; `crux auto check` validates it
  and dry-runs the scorer before anything starts.
- **The objective must come from a check that discriminates against the null.** Optimising a
  bar the hypothesis was always going to clear means the search will clear it, thousands of
  times, at cost, and teach nothing. This is the single most important line in the plan, and
  it is why the skill reads the objective address *off* a check rather than asking you for a
  number first.
- **The driver** is plain Python with no model. It owns selection, budget, id allocation,
  worktrees, launching runs, deriving verdicts and resume. It is the only thing that lives for
  the whole run.
- **The worker** is a fresh agent per attempt, alive for minutes. It sees its brief and nothing
  else, writes code, files the hypothesis and exits — so a four-hour job never holds an agent
  open, and no context anywhere rots.
- **Islands** are sub-questions under the anchor: separate angles, separate worktrees, safe to
  run in parallel. Selection inside an island is flat PUCT; *Climb* is the same rule at
  `c_puct = 0`.
- **The steward** is off by default and Explore-only. It reads the ledger, and may revise the
  guidance or open one more island up to `island_cap`. It can never widen the plan and never
  merges.

## What keeps it honest

- **The scorer is frozen and the driver runs it.** The metric is parsed from the command's
  output, never read from a file the worker last touched.
- **One workspace per attempt, named by its id**, plus a manifest over the declared shared
  roots — path, size, mtime — recorded before the run and re-checked after.
- **A breach closes the attempt `invalid-run`, never `refuted`.** A broken tool is not a wrong
  idea, so the hypothesis stays alive and the record says which happened.
- **A worker may add outcome-neutral controls; it may never add, remove or weaken a
  claim-directed check.** A control can only invalidate a run, so a worker can only ever raise
  its own bar.
- **Success is confirmed at different seeds** before it is declared. A winner's score comes off
  one evaluation, and a lucky seed is the likeliest way an overnight run hands back a false
  result.
- **`main` is never written by the loop.** Attempts live as commits under
  `refs/crux/auto/<qid>/<hid>`; `crux auto promote <hid>` turns one into a branch when you keep
  it.

Sandboxing is your project's job, not crux's: the engine is standard-library-only and
domain-agnostic, so containment belongs in your run command.

## Getting started

Ask for a flight plan in your own words — "set up a flight plan", "I want to search this" —
and the `crux-autopilot` skill takes it from there. It asks you three things, derives or
measures the rest, and stops with a path and the exact `crux auto approve` line. Writing the
plan costs you nothing: the approval stamp covers a hash of the document, so an unapproved
plan is inert and `crux auto run` refuses it.

Watch a run in the cockpit's Autopilot tab (`crux serve`): score against attempt number, what
is in flight per island, the budget axes, and the ledger.

---

Design and rationale, including the alternatives that were rejected and why:
[`.spec/05-autopilot.md`](../../.spec/05-autopilot.md).
