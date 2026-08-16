# Spec 15 — Evidence semantics: no more partial answers

**Label:** `evidence` · **Status:** ◐ in progress — 15.0–15.3 + the rulebook built (engine 1.6→1.9); `ordered` deferred by PI ruling, `crux-verifiables` waits on 09
**Depends on:** [06 node economy](06-node-economy.md) (`--json` surface)
**Paired with:** [08 taskhub](08-taskhub.md), which owns *where* experiments are stored; this
spec owns what their results **mean**
**Amends:** [09 specialized agents](09-specialized-agents.md) — `crux-verifiables` gains a job

## Goal

Make a completed experiment yield an **answer** rather than a partial one.

The PI's report, and the motivating defect: *"after you performed those experiments, you find
partial answers — some verifiables are met, some are not, so you're always left with partial
answers."* Today crux has no machinery that prevents this, and no vocabulary for what went
wrong when it happens.

## The diagnosis

A mixed result is a **symptom** with three distinct diseases. [09](09-specialized-agents.md)
supplies the key fact — *verifiables under one hypothesis are supposed to correlate; they are
consequences of the same claim, so if it is true most pass together* — which means a mixed
result is always evidence that something upstream is wrong:

| # | cause | what actually went wrong | owner |
|---|---|---|---|
| a | **compound claim** | the "hypothesis" was really two or three claims; each verifiable answered a different one | `crux-critic` ([09](09-specialized-agents.md)) |
| b | **non-entailed verifiable** | the check does not follow from the claim; it tests something adjacent | `crux-verifiables` ([09](09-specialized-agents.md)) |
| c | **the run could not discriminate** | underpowered, confounded, wrong instrument, broken apparatus | **nobody — this spec** |

The PI's ruling: the experiment-design work checks **all three**, because a partial answer
does not announce which disease it has. But the *fixes* stay where they belong — this spec
supplies the schema; [13](13-situate-and-design.md) supplies the agent that diagnoses.

## The two structural fixes

Both are deterministic schema slots, so both satisfy [09](09-specialized-agents.md)'s rule 1.
Neither re-opens the `discriminating` flag that 09 rejected — see *Rejected alternatives*.
Sources for everything below are in
[`research/research-doe-core.md`](research/research-doe-core.md) and
[`research/research-prereg-endpoints.md`](research/research-prereg-endpoints.md).

### 1. Verifiables come in two classes, and crux flattens them

Registered Reports call the second class **outcome-neutral tests** — positive controls,
manipulation checks, floor/ceiling checks. They must pass **whatever the hypothesis turns out
to be.** When one fails it invalidates the *run*, not the claim.

Regulators name the property this protects: **assay sensitivity** (ICH E10). Without a
passing positive control, *"the hypothesis is false"* and *"the apparatus is broken"* are
indistinguishable.

crux has one flat `## Verifiables` list. So a bug in shared preprocessing and a false
hypothesis produce the same-looking partial pass. **That alone manufactures partial answers**,
and the fix is structural rather than an instruction.

**Design.** Every verifiable gains a `kind`:

| kind | meaning |
|---|---|
| `hypothesis` | a consequence of the claim. Feeds the verdict. |
| `outcome-neutral` | must pass regardless. Failure ⇒ the run is invalid, and nothing about the claim is learned. |

**At least one `outcome-neutral` verifiable is required** before a hypothesis may go
`running`, or an explicit written opt-out. Some claims genuinely have no meaningful positive
control; that has to be *said*, not silently assumed.

### 2. Every hypothesis declares how its checks add up

Right now, *"two of four passed"* is an argument, settled after the results are visible. A
**combination rule**, declared before the run, makes it arithmetic.

ICH E9 §2.2.5 does not force a single primary endpoint — it offers a menu: whether an impact
on *any* variable, *some minimum number*, or *all* of them is required. All four forms are
available:

| rule | verdict |
|---|---|
| `all` | every `hypothesis` verifiable must pass |
| `m-of-n` | at least *m* of them |
| `any` | one is enough |
| `ordered` | check 1 decides; later checks are read only if earlier ones passed |

**`crux-verifiables` chooses the rule**, at the same moment it writes the checks — it is the
agent that already knows what each check is for, and it is already isolated from the advocacy
that produced the claim. The PI approves it alongside the null.

The cost is exact and must be stated when the rule is chosen: `all` over two checks at 80%
power each gives **64% joint power**, and thresholds may not be loosened to compensate.

The verdict becomes a **total function** of the pass/fail vector. That is the property that
kills partial answers: there is no vector with no verdict.

### 3. Two verdict states crux lacks

- **`invalid run`** — an `outcome-neutral` verifiable failed. Not a refutation, not a
  support; the experiment tells us nothing and must be re-run. Without this state a broken
  apparatus is silently read as evidence.
- **`inconclusive`** — the combination rule was not met and not clearly failed (`m-of-n` with
  m−1 passes, or `ordered` stopping early). Bayesian dual-criterion designs pre-specify
  go / **consider** / no-go precisely so that "mixed" is a *declared* outcome with a defined
  next action rather than an escape hatch.

`inconclusive` is the risk in this spec: it can become the drawer everything ambiguous gets
swept into. Mitigation is that it is *derived*, never chosen — you cannot mark a hypothesis
inconclusive, only arrive there.

### 4. The lock, which is the only part that has ever worked

The negative result from the literature is blunt: **bare pre-registration largely does not
work.** No measurable reduction in positive results, and 46% of pre-registered hypotheses
simply vanish from the published paper. **Registered Reports do work** — 44% positive results
against 96% in the standard literature. The active ingredient is *enforced commitment*, not
the document.

crux can enforce what a journal cannot. When a hypothesis goes `running`, the engine
**content-hashes the verifiables, their kinds, and the combination rule.** Any later edit is
detected and surfaced as a **drift flag** on the node, in `validate`, and in the cockpit.

Edits are *flagged, not refused*. Research legitimately discovers that a check was wrong, and
refusing the edit only produces a laundered duplicate hypothesis. A loud, permanent flag is
both honest and harder to ignore.

### 5. Enforce the verdict where it is read, not only where it is computed

**PLATO** is the cautionary case, and it is the sharpest thing the research surfaced: an
18,624-patient trial with a correct endpoint hierarchy hit its stop at endpoint 6 (stroke,
p=0.22) — and the authors published endpoints 7–10 as findings anyway. **The rule failed at
narration time, not computation time.**

So the derived verdict must be rendered wherever the hypothesis is read — the node, `META.md`,
the cockpit, `--json` — and the prose must not be able to quietly contradict it. Offering four
combination rules is only safe under this constraint.

## The separability condition

*The PI's rule, and the answer to "when may one experiment test several hypotheses?"*

> **One experiment may test several hypotheses if and only if it can tell their answers
> apart.**

The literature splits this into three properties that are kept in three different fields,
which is why people satisfy one and stop. Full treatment in
[`research/research-separability.md`](research/research-separability.md).

1. **Identification.** A design separates effects only when each hypothesis is turned by its
   own independently varied knob. Fractional designs buy runs by giving this up — what you
   compute as `c₃` may really be `c₃ + c₁₂`. Design **resolution** is a machine-readable
   ledger of what is separable: Res III aliases main effects with two-factor interactions
   (screening only), Res IV separates main effects but confounds interactions in pairs, Res V
   separates both. Rule: **resolution must exceed the order of the highest-order effect any
   bundled hypothesis is about.** And separability is always *conditional on a declared model*
   — never absolute.
2. **Calibration.** Multiplicity does **not** change what separable means — identification is
   a property of the design matrix, multiplicity is a property of the decision rule. FDA's
   2022 guidance gives the crisp version: *all must succeed* → no adjustment; *any may
   succeed* → adjustment required. Note this maps exactly onto the combination rules above.
3. **Independent failure — the strongest argument against bundling.** Two regimes. A nuisance
   *correlated* with the design (batch effects) breaks identification outright. A nuisance
   *constant* across all arms — one seed, one preprocessing path, one shared control — passes
   every design audit and yet leaves every answer conditional on a sample of size one. A
   shared control alone induces ρ≈0.5.

**The rescue, and it closes the loop with §1:** outcome-neutral checks are the *dual* of
common-mode failure — a detector for exactly the shared element that would sink everything at
once. **Sharing them across bundled hypotheses is the fix, not the flaw:** they convert silent
correlated wrongness into a run-invalidating signal. Separability breaks when a shared element
has no covering check, or when the "neutral" check can only pass if one of the bundled
hypotheses is true.

**Rulebook sentence**, to go in the skill verbatim:

> One experiment settles several hypotheses separately only when each hypothesis is turned by
> its own independently varied knob — a comparison the design can attribute to it alone, at a
> resolution high enough for the kind of effect it claims — and no single shared ingredient
> (one batch, one seed, one preprocessing path, one control) could flip all the answers
> together without a pre-declared outcome-neutral check catching it and voiding the whole run;
> anything less means you ran one experiment with many labels, not many answers.

## Hypothesis is not experiment

Settled here, implemented in [08](08-taskhub.md):

- A **hypothesis** is a claim — a scientific abstraction, and it must be atomic.
- An **experiment** is an action taken to support or dispute one. It is a **task whose output
  is evidence** ([08](08-taskhub.md)).
- The relation is **many-to-many in both directions**: one run can inform several hypotheses
  (subject to separability), and one hypothesis can need several runs (pilot, then full).

The prior-art survey found this gap is structural rather than an oversight: **no ELN or ML
tracker models a claim at all** — Benchling, eLabFTW, SciNote, RSpace, MLflow, W&B, Neptune
and DVC return zero hits for "hypothesis", and Benchling's `AssayResult.entryId` is a *single*
foreign key, so a result can never serve two experiments. The systems that do model it are the
A/B platforms (GrowthBook's `Learning`, Statsig's `hypothesizedValue`) and the provenance
ontologies.

## Grandfathering — this spec is not retroactive

**Settled 2026-08-15 by PI ruling.** Every rule in this spec binds hypotheses created **at or
after** the `ENGINE_VERSION` that introduces it. Hypotheses that already exist are never
retro-checked, never re-verdicted, and never flagged.

The reason is the same one that put [06](06-node-economy.md)'s prose cap on a warn tier: a
retroactive rule puts a working vault into permanent red against a bar that did not exist when
the work was done, and bundles a migration project onto a feature. Worse here than in 06,
because the naive migration default (`kind: hypothesis` on every verifiable, rule `all`) would
**retro-flag settled nodes as refuted** — the engine would silently overturn recorded science.
That is precisely what the leash exists to prevent.

Mechanically:

- Verifiable `kind`, the combination rule, and the hash-lock are **required on creation** from
  the new version onward, and **absent-and-fine** on anything older.
- A pre-existing hypothesis keeps deriving its verdict exactly as it does today. Old vaults
  load, validate clean, and are not warned about.
- `validate` reports the boundary as information, never as a problem: *"41 hypotheses predate
  evidence semantics."*
- **No `crux migrate` path for this.** If the PI wants an old hypothesis brought up to the new
  schema, that is a scientific act — re-declaring what would settle a claim — and it goes
  through the normal PI-gated route, one node at a time. It is exactly the *scientific
  staleness* case [09](09-specialized-agents.md) warns must never be automated under cover of
  version bridging.

The version boundary is therefore permanent and visible, not a transition to be completed.

## Decisions

| decision | rationale |
|---|---|
| **not retroactive — binds only nodes created at or after the new `ENGINE_VERSION`** | a retroactive rule would retro-flag settled hypotheses as refuted, i.e. the engine overturning recorded science; and it bundles a migration onto a feature |
| **no automated migration to the new schema** | bringing an old hypothesis up to it means re-declaring what would settle it — a scientific act, PI-gated, one at a time (09's staleness warning) |
| partial answers are a symptom of three diseases | they need different fixes; conflating them produces a vague agent |
| verifiables carry a `kind` | a broken apparatus and a false claim must not look alike; this is upstream and structural, not an instruction |
| ≥1 outcome-neutral verifiable required, or an explicit opt-out | assay sensitivity; and "there is no positive control here" should be *said* |
| a combination rule, declared before the run | turns "two of four passed" from an argument into arithmetic; makes the verdict a total function |
| all four rules available | each has a scenario where it is correct (PI ruling) |
| `crux-verifiables` picks the rule | it writes the checks, it knows what each is for, and it is already isolated from the advocacy |
| add `invalid run` and `inconclusive` | a run that tells us nothing and a result that does not meet its rule are different from support and refutation |
| `inconclusive` is derived, never chosen — **as a hypothesis's `verdict`** ([08](08-taskhub.md)'s experiment conclusions reuse these tokens but are *written about a run* and PI-accepted; they never write a node's verdict) | otherwise it becomes the drawer |
| hash-lock at `running`, flag drift loudly | enforced commitment is the only thing shown to work; refusal only launders the edit into a new hypothesis |
| enforce the verdict at render time | PLATO — the rule failed at narration, not computation |
| the separability condition governs bundling | the PI's rule; the research supplies the three properties it decomposes into |
| shared outcome-neutral checks are the fix for common-mode failure | they turn silent correlated wrongness into a run-invalidating signal |

## Rejected alternatives

- **Pre-writing a reading for each of the 2^k outcome patterns.** Proposed by one line of the
  research and killed by another: attempted in economics pre-analysis plans, and Olken and
  Ofosu & Posner document the failure — high authoring cost, poor adherence, no measurable
  credibility gain. Registered Reports require one interpretation *per hypothesis*, never per
  combination.
- **A mandatory single primary endpoint.** ICH E9 explicitly offers a menu instead, and a
  forced primary discards information the secondaries carry. The declared combination rule is
  the general form.
- **Doing nothing structural and fixing partial answers upstream by tightening claims alone.**
  The PI's initial instinct, and right in spirit — but "make claims atomic" is an instruction,
  and [06](06-node-economy.md) settled what instructions are worth here. §1 and §2 *are* the
  upstream fix, expressed as schema.
- **Re-opening 09's `discriminating` flag.** Not what this is. That was a per-verifiable
  annotation the verdict rule had to respect. A combination rule is a *single declaration of
  how to read the vector* — one field per hypothesis, not per verifiable — and it makes the
  verdict total rather than weighting it.
- **A separate experiment storage layer.** Merged into [08](08-taskhub.md).
- **Refusing edits to locked verifiables.** Produces a laundered duplicate hypothesis; the
  flag is more honest.

## Open questions

- Whether `ordered` should ship at all. It is the exact structure PLATO's authors ignored, and
  it is the hardest of the four to render unambiguously.
- Whether the drift flag should block `answer` on the parent question, or only warn.
- How resolution / aliasing is *declared* for a bundled experiment without dragging a full DoE
  formalism into a markdown vault. Probably a named model plus which knob each hypothesis
  owns; needs design.
- Whether `inconclusive` requires a written next action, the way [08](08-taskhub.md) requires
  an output ref on `done`.

## Work items

- ☑ `kind` on every verifiable (`hypothesis` / `outcome-neutral`); CLI `-v` gains it
- ☑ `validate`: ≥1 outcome-neutral before `running`, or a recorded opt-out
- ☑ Combination rule field on the hypothesis, closed vocabulary, PI-approved with the null
- ☑ Verdict derivation becomes a total function of (kinds, rule, pass/fail vector)
- ☑ Verdict states `invalid run` and `inconclusive`; legend, snapshot, cockpit, `META.md`
- ☑ Hash-lock verifiables + kinds + rule at `running`; drift detection and flag
- ☑ Render the derived verdict everywhere the hypothesis is read
- ◐ `crux-verifiables` amended: choose and justify the rule; state the joint-power cost — recorded into [09](09-specialized-agents.md), lands when that spec is built
- ☑ The separability rulebook sentence into the crux skill
- ☑ `ENGINE_VERSION` bump; version-boundary gating so the rules bind new nodes only
- ☑ `validate` reports the boundary as information (*"N hypotheses predate evidence
  semantics"*), never as a problem

## Acceptance criteria

- A hypothesis created at the new version cannot go `running` with no `outcome-neutral`
  verifiable and no recorded opt-out.
- **A hypothesis created before the new version is never checked against any rule in this
  spec** — no warning, no drift flag, no verdict change. Asserted against a captured
  pre-upgrade vault fixture, byte-comparing every derived verdict before and after the
  version bump.
- An old vault loads and validates **clean**, with the version boundary reported as
  information only.
- A failed `outcome-neutral` verifiable yields `invalid run`, never `refuted`.
- Every pass/fail vector maps to exactly one verdict — asserted exhaustively for a small `k`.
- Editing a verifiable, its kind, or the rule after `running` raises a drift flag in
  `validate`, on the node, and in the cockpit.
- The combination rule and the derived verdict appear in the cockpit and in `--json`.
- An `m-of-n` hypothesis with m−1 passes reports `inconclusive`, not `refuted`.
- `selftest.py` passes with a grown assert count.
