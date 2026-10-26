# Spec 18 — Lean autopilot

- **Kind:** refactor (rebuild)  - **Spec:** replaces the engine design of [05](05-autopilot.md); keeps its goal and its leash.
- **Status:** draft for PI approval, 2026-10-26.

## Problem

The autopilot of spec 05 does not crash any more, but it is too heavy to use.

- **Slow.** The last real run (q1, 2026-09-23) closed 3 attempts in 6 h. A worker took 40–100 min, a score took about 9 min, and the confirmation seeds took 12–16 min more.
- **Large.** It has about 5,800 lines of engine code, 36 plan fields, 3 agents and 8 subcommands. The steward, the islands and the parallel settings never acted in a real run.
- **Hard to debug.** A failure can come from any of 15 guardrails, 7 state files or 5 resume phases.

## Goal

One confident run, from start to end, with no crash, that improves the metric on each of four real benchmarks. The run is lean, fast and easy to set up, and its guardrails are clear.

## The benchmarks are the acceptance test

They are on branch `autopilot-lean`, in `examples/autopilot/`. Each one has a scorer that does its own correctness and anti-cheat checks, measured on Fir.

| Benchmark | Mode | Objective | Baseline → bar | Scorer time |
|---|---|---|---|---|
| memesuite-lite | climb | `seconds`, min | 6.02 s → 1.62 s (PR #21) | ~2 min, CPU |
| nanogpt-shakespeare | climb | `val_loss`, min | 1.387 → 1.36 (known improvement) | ~4 min, 3g GPU slice |
| circle-packing | explore | `sum_radii`, max | 2.5414 → 2.63598 (record) | <1 s, CPU |
| m4-weekly | explore | `val_owa`, min | 1.000 → 0.739 (best Weekly method) | ~10 s, CPU |

## Design

### What the user writes: the plan

The plan has about 10 fields. Each field has a default, except the ones marked *required*.

| Field | Meaning |
|---|---|
| `anchor` *required* | The question this run serves. |
| `repo`, `base` *required* | The program repo and the commit the run starts from. |
| `editable` *required* | The paths the worker may change. Every other path is frozen. |
| `scorer` *required* | The command that prints one JSON object (see the contract below). |
| `objective` *required* | The address in the JSON, the direction, and the bar. |
| `mode` | `climb` (default) or `explore`. |
| `budget_hours` | Default 8. |
| `attempt_minutes` | One limit for each attempt: worker plus scorer. Default 20. |
| `worker` | The model and the effort. The engine builds the command; the user does not write it. |
| `guidance` | Free text from the PI: priors, analogies, dead ends. |

### The scorer contract

The scorer is a frozen command. It reads the candidate from `CRUX_WORKSPACE`. It prints one JSON object. It exits 0 when the candidate is valid. It exits non-zero, with `{"passed": false, "reason": …}`, when the candidate is wrong. Correctness tests, equivalence to a reference, anti-cheat checks and repeats against noise all live inside the scorer. The engine does not repeat them.

### The engine: seven rules

1. **Allowlist.** After the worker exits, `git diff --name-only` against `base` must touch only `editable` paths. Any other change discards the attempt.
2. **Fail, do not crash.** A worker or scorer crash, a timeout, or a missing number is one failed attempt. The run continues.
3. **Rejected is not broken.** A scorer that says `passed: false` rejects the candidate once, with no retry. Only a scorer that cannot start (for example, a missing file or a killed node) is a machine fault and gets one retry.
4. **One time limit per attempt.** `attempt_minutes` covers the worker and the scorer together.
5. **Keep or drop.** Every valid attempt is kept with its score. Climb always builds on the best score so far, which is Karpathy's keep-or-reset. Explore picks the parent from all valid attempts with ERA's flat PUCT rule, on one island.
6. **Setup check.** Before the first attempt, the engine scores the base, then scores it again with one small change to an editable file. It also runs the worker command once. It refuses to start if the score does not respond or if the worker cannot write and commit.
7. **One budget.** `budget_hours` is checked only between attempts, so an attempt in flight always finishes. A provider rate limit means wait. It never counts as a failure.

**Workers have no web access.** The worker command denies the web tools. It still reaches the model API.

### Recording: crux stays crux

Each attempt is one hypothesis node under the anchor. Its check is the objective against its parent's score. The driver files it and closes it with the derived verdict. No model call is needed for this, so the closer agent goes. The PI still answers the anchor and still merges into `main`.

### Where it runs

The driver runs inside one Fir SLURM job. It calls the scorer directly on that node, and the worker runs there too. The cockpit and `crux auto status` read the vault, so the PI can watch from the laptop.

### Removed

The steward agent, the closer agent, islands, `island_cap`, parallel workers and the shared-root manifest, the vault lock and id reservation, the approval hash, confirmation seeds, the stall rule, abort after N invalid runs, the model-call budget, agent failover and the probe settings, the run branch and the island branches, `promote` and `refs`, retention, and brief lint.

## Scope

This change does not alter the crux tree, verdict derivation, the leash ruling of spec 05 §12, or the cockpit beyond what the removed parts force.

## Acceptance criteria

- [ ] Each of the four benchmarks runs from start to end on Fir with no driver crash. (manual: one run each)
- [ ] Each run improves its objective over its baseline, beyond the scorer's stated noise. (manual)
- [ ] Each climb run finishes at least 3 attempts per hour. Each explore run finishes at least 6 attempts per hour. (manual, from the ledger)
- [ ] A plan for any benchmark fits in 10 fields or fewer. (selftest)
- [ ] Rules 1–7 each have a failing-then-passing selftest assert. (selftest)
- [ ] A worker with web tools enabled is refused at setup. (selftest)
- [ ] The autopilot code is under 1,500 lines, against about 5,800 today. (`wc -l`)
- [ ] `./crux selftest` is green. Existing vaults still load. An old plan file is refused with a message that names the new fields. (selftest)

## Backward-compat / migration

Old autopilot runs stay readable, because they are ordinary nodes in the vault. Old plan files are refused, not migrated. The vault format does not change, so `ENGINE_VERSION` stays unless the build proves otherwise.

## Open questions for the PI

1. Is 20 minutes right as the default `attempt_minutes`?
2. Are the throughput bars right: 3 attempts per hour for climb and 6 for explore?
3. Is 1,500 lines the right size target?
4. Should an attempt that does not beat its parent still become a node? The proposal says yes, as a refuted hypothesis, so the next worker can see what failed.
