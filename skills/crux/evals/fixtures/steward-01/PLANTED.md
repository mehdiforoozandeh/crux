---
fixture: steward-01
agent: crux-auto-steward
ground_truth: proxy
oracle: stated_key
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# steward-01 — one island stalled, one starving, and the correct call known by construction

A steward is handed one run brief and writes one proposal. This fixture is that brief's island
table and ledger tail, plus the key a correct proposal has to hit.

The run holds two islands and the record says two different things about them. `q1.1` has had
six attempts and its best score has not moved in the last four — it is **stalled**. `q1.2` is
open and has had one attempt in the whole run — it is **starving**, and the round-robin keeps
landing elsewhere. Both facts are readable off the table and the ledger with no judgment at
all, which is what makes the key statable: the guidance a correct proposal writes names the
stalled island, and nothing in the brief supports opening a third island while a second one
sits unused.

No vault is read. The oracle is `stated_key`, the brief is carried in this file, and the hard
half of the score is the engine validating the submitted proposal exactly as the driver would.

## Planted

| id | tier | class | what a correct proposal must carry |
|---|---|---|---|
| `names-the-stalled-island` | requirement | filter | the guidance names `q1.1` — six attempts, best flat across the last four, which is the one thing in the brief that says the search is stuck |
| `does-not-open-a-third` | requirement | filter | no `island` key: the run already holds an island with one attempt, so a third would starve two rather than one, and the brief carries no angle the open islands cannot reach |
| `guidance-is-standing` | requirement | filter | the guidance outlasts one attempt — a rule the tenth worker can still apply, not a single change for the next one to make |
| `guidance-under-cap` | requirement | economy | the guidance fits the 400-word prose cap, and a proposed island title would fit 15 words |
| `no-fourth-key` | requirement | filter | exactly the two schema keys and no more; the objective, the bar, the checks and the budget are frozen and unreachable by wording |

## The ledger

The brief the agent was given, in the shape the engine assembles it. It is reproduced here so
the fixture is self-contained: nothing outside this file is read, and the anchor's problem
statement, every attempt's diff and all findings prose are absent by design.

```
# Steward brief — q1  (auto/q1/plan.md)

## Goal
Raise held-out accuracy on the small-molecule panel without growing the model.

## Objective
address: obj.score · direction: max · bar: 0.84

## Islands
- q1.1 — Does the optimiser schedule explain the gap? · best h7 = 0.812 · stall 4 · 6 attempt(s)
- q1.2 — Does the readout explain the gap? · best h9 = 0.769 · stall 0 · 1 attempt(s)

## Budget
- attempts: 7 of 12 used, 5 remaining
- hours: 1 of 6 used, 5 remaining
- model_calls: 8 of 20 used, 12 remaining

## The PI's guidance
- [2026-09-14] PI: report the seed count with every score.

## Earlier steward guidance
No steward guidance yet.

## Ledger
- 2026-09-16T09:02:11Z closed {"hid": "h4", "island": "q1.1", "score": 0.806}
- 2026-09-16T10:41:55Z closed {"hid": "h5", "island": "q1.1", "score": 0.809}
- 2026-09-16T12:18:03Z closed {"hid": "h6", "island": "q1.2", "score": 0.769}
- 2026-09-16T14:05:37Z closed {"hid": "h7", "island": "q1.1", "score": 0.812}
- 2026-09-16T15:52:20Z closed {"hid": "h8", "island": "q1.1", "score": 0.811}
- 2026-09-16T17:30:44Z closed {"hid": "h9", "island": "q1.1", "score": 0.810}
- 2026-09-16T19:08:12Z stall  {"island": "q1.1", "stall": 4}

## Output
One JSON object with keys guidance, island — at most one of each, at least one present.
```

## What this proxy does **not** measure

Whether the advice would **help** — only that it names the stalled island, and that the
proposal validates.

Four of the five rows are structural. The fifth reads one island id off a table. Nothing here
can tell advice that fixes the search from advice that merely points at the right island: a
proposal naming `q1.1` and then recommending something useless scores 1.0. Whether the steward
earns its place at all is a question only a real run answers, and this fixture is not that run.

## Reading the eval

The discrimination is the second row. A steward that reaches for a new island whenever a score
goes flat spends the run's remaining attempts on a third front while the second one starves —
so *not* proposing an island is the answer here, and an eval that could not fail an
island-happy steward would measure nothing.

The hard half sits beside the band: `auto_steward_proposal` validates the submitted object
exactly as the driver would.

`band: unset`. The pass bar is the PI's.
