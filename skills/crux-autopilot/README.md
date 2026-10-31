# crux autopilot

Run one anchor question unattended, against an objective and a threshold you fix **before**
the run starts. A question that suits search (make this faster, lower this loss, pack these
circles tighter) runs overnight with no turn-taking, and reads back in the morning as ordinary
crux: one hypothesis per attempt, each with one finding and its confidence.

It is not an autonomous scientist. The run cannot change its objective, its threshold, its
scorer or its anchor. It searches inside a frame you built.

| when | what is yours |
|---|---|
| before | write the plan with the `crux-autopilot` skill, and start `crux auto run` |
| after | merge what you want into `main` |
| any time | correct the record in plain words; your correction wins |

## How a run works

1. **Setup check.** The driver scores the base, scores again with the first editable file
   emptied (the score must change), and runs the worker once to prove it can commit.
2. **Each attempt.** The driver picks a parent, cuts a git worktree from it, and gives the
   worker a brief. The worker (`claude -p`, no web tools) edits only the editable paths and
   makes one commit; its subject line is the claim. The driver checks the paths, runs the
   frozen scorer, files a hypothesis under the anchor with one finding computed from the score
   (no model call), and appends one line to `auto/<qid>/ledger.jsonl`.
3. **Stop.** The run stops when `budget_hours` is spent. A second `crux auto run` continues
   from the ledger.

**Climb** always builds on the best attempt so far (Karpathy's keep-or-reset). **Explore**
picks the parent from all kept attempts with the flat PUCT rule of Google's ERA, which balances
the best attempt against less-visited ones.

## How an attempt's finding is computed

The setup check scores the base 3 times; the median is the baseline and the spread is the
scorer's **noise**. A kept attempt that beats its parent by more than `min_gain` supports the
claim in its commit subject; one that does not is against it. The confidence is symmetric:
strong when the score lands past the bar, either way, by more than the noise (or `min_gain`
when the noise is 0), else moderate. A rejected, failed or discarded attempt is "no answer
yet", weak. With a deterministic scorer and no `min_gain`, any real gain counts.

## The plan

In `auto/<qid>/plan.md`: `anchor`, `repo`, `base`, `editable`, `scorer`, `objective`
(required); `mode`, `budget_hours`, `attempt_minutes`, `worker` (defaulted); `min_gain`
(optional); then your guidance as free text. See the benchmark directories under
[`examples/autopilot/`](../../examples/autopilot/) for worked plans.

## The seven rules

1. **Allowlist.** A change outside `editable` discards the attempt.
2. **Fail, do not crash.** A crash, a timeout or a missing number is one failed attempt.
3. **Rejected is not broken.** `passed: false` rejects once. Only a scorer that cannot start is
   retried, once.
4. **One time limit.** `attempt_minutes` covers the worker and the scorer.
5. **Keep.** Every valid attempt is kept with its score and can be a parent.
6. **Setup check.** No run starts unless the base scores, the score responds, and the worker
   commits with the web tools denied.
7. **One budget.** `budget_hours` is read between attempts. A rate limit waits; it is never a
   failure.

## The scorer contract

The scorer prints one JSON object. A wrong candidate exits non-zero with `"passed": false`.
Correctness tests, anti-cheat checks and repeats against noise live inside the scorer; the
driver repeats none of them.

## Verbs

- `crux auto check <plan>` runs the setup check and prints the baseline and the noise
  (`--static`: the plan alone).
- `crux auto run <plan> [--max-attempts N]` runs or continues the search.
- `crux auto status [<qid>]` reads the ledger: each attempt's score, finding, direction and
  confidence (`--json` for all fields). The cockpit's Autopilot tab (`crux serve`) shows the
  same.

`main` is never written. A committed attempt lives under `refs/crux/auto/<qid>/<n>` in your
repo. Sandboxing is your project's job: containment belongs in your scorer.

Design: [`.spec/18-autopilot-lean.md`](../../.spec/18-autopilot-lean.md).
