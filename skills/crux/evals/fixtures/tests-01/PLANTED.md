---
fixture: tests-01
agent: crux-tests
ground_truth: proxy
oracle: stated_key
verify: distinct_expected
wrong_values: hi + 1, 46, swaps
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# tests-01 — test the requirement, not the code

`vault/requirement.md` states five boundaries for `clamp(value, lo, hi)`. `vault/broken/clamp.py`
implements it **wrong**, twice. `crux-tests` never reads that file — seeing the implementation
is what turns a test of the requirement into a description of the code — and the eval is
whether the tests it writes aim at the boundaries the requirement states.

## Demoted from ground truth — read this before trusting the number

Spec 10 calls this fixture *"the strongest available"* ground truth, on the strength of one
oracle: **the generated tests must fail against the non-compliant implementation.** Checking
that means **executing model-written Python**, inside a suite whose hard rules are stdlib-only
and hermetic. That is parked (**P2**), and until it is unparked this fixture is a **proxy** and
is registered as one. It measures whether the agent *aimed* at the requirement, not whether its
tests *run*: a test with a syntax error scores full marks here.

## Planted

| id | tier | class | the boundary, and what the requirement says |
|---|---|---|---|
| `req1:in-range` | boundary | pass-through | `lo <= value <= hi` returns `value` unchanged |
| `req2:below` | boundary | clamp-low | `value < lo` returns `lo` |
| `req3:above` | boundary | clamp-high | `value > hi` returns `hi` — and the implementation returns one more than that |
| `req4:refuses` | boundary | must-refuse | `lo > hi` raises `ValueError`; the implementation silently reorders them instead |
| `req5:degenerate` | boundary | empty-case | `lo == hi` is legal and every input returns that one value |

## The anti-tautology check, at the value level

`wrong_values` lists what the broken implementation actually does. Certification asserts **no
key row expects any of them** — because a key that could be satisfied by describing the code
*is* a description of the code, which is the exact failure the `tdd` rule spec 10 quotes exists
to name. It is also what makes this proxy worth running at all without executing anything.

## What this proxy does **not** measure

Whether the tests are syntactically valid, whether they run, and whether they actually fail
against `broken/clamp.py`. All three need execution. See **P2**.
