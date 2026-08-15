# When can ONE experiment validly settle SEVERAL hypotheses separately?

Research notes for the crux tree model (Questions → atomic falsifiable Hypotheses; one
experiment MAY test several hypotheses only if it can tell their answers apart).

The headline finding: **"separability" is not one property. It is three independent
properties that must all hold**, and the literature keeps them in three different
subfields, which is why practitioners routinely satisfy one and think they are done.

| Axis | Question it answers | Fails when | Literature |
|---|---|---|---|
| **A. Identification** | Can the design attribute the signal to hypothesis *i* alone? | aliasing / confounding / non-orthogonality | DoE (Box-Hunter-Hunter, Montgomery, NIST) |
| **B. Calibration** | Is each answer's error rate still what it claims, given we asked *m* questions? | multiplicity | FWER/FDR literature, FDA multiple-endpoints |
| **C. Independence of failure** | Can all *m* answers be wrong for one shared reason? | shared nuisance / common-mode failure | batch effects, reliability engineering, ML reproducibility |

A design can be perfectly orthogonal (A ✓) and still need a Bonferroni correction (B),
and still have every answer destroyed by one preprocessing bug (C). **Axis C is the
strongest argument against bundling** and is the one no statistical adjustment fixes.

---

## 1. Factorial and fractional factorial designs

### 1.1 Why a single factorial experiment can answer several questions at once

Fisher's 1926 argument: vary several factors simultaneously in a balanced pattern and
every observation contributes to every effect estimate. This is **hidden replication** —
each data point is used in the estimate of each main effect, so a 2^k factorial estimates
*k* main effects each with the precision of a *full*-sized two-group comparison. For two
factors at two levels this is a ~50% precision gain over one-factor-at-a-time (OFAT) for
the same runs; the gap widens with more factors. Three factors at two levels: OFAT needs
16 runs to match what a factorial does in 8. And factorial designs are **the only way to
discover interactions**, at no extra cost (Fisher 1935).

- https://management.curiouscatblog.net/2011/05/25/one-factor-at-a-time-ofat-versus-factorial-designs/
- https://www.6sigma.us/six-sigma-in-focus/ofat-one-factor-at-a-time/
- https://asq.org/quality-resources/design-of-experiments
- https://statisticsbyjim.com/basics/factorial-design/

So the pro-bundling case is strong and quantitative. Bundling is not a compromise; done
right it is *more* powerful per unit cost than separate experiments.

### 1.2 The exact condition for separability: orthogonality

The formal statement, for a linear model `y = Xβ + ε` where the columns of `X` encode the
factors/contrasts under test:

> **A design D is orthogonal if `X'X` is diagonal.**
> Parameter estimates are uncorrelated **if and only if** `X'X` is diagonal — that is, if
> the columns of `X` are mutually orthogonal.

Operational equivalents for a two-level design:

- **Column dot product = 0.** Any two design columns (coded −1/+1) have inner product zero.
- **Balance.** Every level of factor A appears equally often with every level of factor B.
  "A designed experiment is orthogonal if the effects of any factor balance out (sum to
  zero) across the effects of the other factors."
- **The payoff, stated by Minitab:** "Orthogonality guarantees that the effect of one
  factor or interaction can be estimated separately from the effect of any other factor
  or interaction."

Sources:
- https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/basics/orthogonal-designs/
- https://www.biostat.jhsph.edu/~iruczins/teaching/140.751/notes/ch8.pdf
- https://qualityamerica.com/LSS-Knowledge-Center/designedexperiments/orthogonality.php
- https://www.itl.nist.gov/div898/handbook/pri/section3/pri334.htm (properly chosen
  fractional factorials are both "balanced" and "orthogonal")

Two consequences that matter for a rule engine:

1. **Orthogonality is relative to a model.** `X` must contain a column for every effect you
   are willing to entertain. A design orthogonal for a main-effects-only model is *not*
   separable if a two-factor interaction is real but omitted from `X` — the interaction's
   signal lands on some main-effect estimate. Separability is therefore always
   *conditional on a declared assumption set*, never absolute. This is the single most
   important conceptual point in section 1.
2. **Unbalanced or missing data destroys orthogonality.** Once cells are unequal, `X'X` is
   no longer diagonal, effect estimates become correlated, and sums of squares depend on
   the order terms enter the model (the Type I vs Type III SS problem). A run with dropped
   observations silently loses separability it was designed to have.
   - https://docs.tibco.com/pub/stat/14.0.0/doc/html/UsersGuide/GUID-365C8B12-32C5-4B26-BCAC-E1CD9E882AAE.html

### 1.3 Confounding and aliasing in fractional factorials

A fractional factorial runs "only an adequately chosen fraction of the treatment
combinations required for the complete factorial." The price is exact and computable.

- **Generator.** A new factor is assigned to a product of existing columns, e.g. `3 = 12`.
- **Defining relation.** Multiply through: `I = 123`. The full set of such "words" defines
  the design.
- **Alias structure.** Multiply the defining relation by each effect to read off what is
  inseparable. For `2^(3-1)` with `I = 123`: `{1 = 23, 2 = 13, 3 = 12}`.
- **What you actually estimate.** NIST states it bluntly: "Our computation of c₃ is in fact
  a computation of c₃ + c₁₂." You get a **sum**, not a component. "Confounding means we
  have lost the ability to estimate some effects and/or interactions."
- **Aliasing vs confounding.** Used near-synonymously in the fractional-factorial
  literature; strictly, *confounding* is the general phenomenon of two effects being
  inseparable (also used for effects deliberately confounded with **blocks**), *aliasing*
  is the specific structural pattern induced by the defining relation.
- **The rescue assumption:** the **sparsity of effects** principle — a system is usually
  dominated by a few factors and low-order effects, so the aliased high-order term is
  assumed negligible. Related principles: **hierarchy** (lower-order effects likelier
  active) and **heredity** (an interaction is likelier active if its parent main effects
  are). Separability in a fraction is *purchased with these assumptions*, and if they fail
  the answer is silently wrong.

Sources:
- https://www.itl.nist.gov/div898/handbook/pri/section3/pri3343.htm
- https://www.itl.nist.gov/div898/handbook/pri/section3/pri334.htm
- https://link.springer.com/rwe/10.1007/978-3-319-11259-6_33-1
- https://arxiv.org/pdf/1510.05248 (Design of Experiments for Screening)

### 1.4 Design resolution — the exact ledger of what separates from what

> **Definition (NIST):** "The length of the shortest word in the defining relation is
> called the resolution of the design."

General rule: **in a resolution-R design, an effect of order *k* is aliased with effects of
order R − k and higher.**

| Resolution | What is aliased | What you may claim |
|---|---|---|
| **III** | "Main effects are confounded (aliased) with two-factor interactions." | Main effects **only if** all two-factor interactions are negligible. Screening only. |
| **IV** | "No main effects are aliased with two-factor interactions, but two-factor interactions are aliased with each other." | Main effects cleanly (aliased only with 3-factor+). Two-factor interactions **not** separable from each other — you get sums like `AB + CD`. |
| **V** | "No main effect or two-factor interaction is aliased with any other main effect or two-factor interaction, but two-factor interactions are aliased with three-factor interactions." | Main effects **and** all two-factor interactions separately. |

Sources:
- https://www.itl.nist.gov/div898/handbook/pri/section3/pri3344.htm
- https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/what-is-design-resolution/
- https://learnche.org/pid/design-analysis-experiments/fractional-factorial-designs/design-resolution
- https://online.stat.psu.edu/stat503/lesson/8/8.1
- https://www.jmp.com/en/statistics-knowledge-portal/design-of-experiments/screening-designs/fractional-factorial-designs

**Direct translation to a crux rule.** Resolution is exactly a machine-checkable statement
of *which bundled hypotheses get their own answer*:

- Hypotheses that are all about **single-factor main effects** → Resolution IV or higher.
- Hypotheses where any is about a **specific two-factor interaction** ("X only helps when
  Y is on") → Resolution V required. A Res IV design will hand back `AB + CD` and both
  interaction hypotheses share one number — **not separable**.
- Resolution III bundles are legitimate **screening** — they narrow the question set — but
  each answer must be recorded as provisional and conditional on effect sparsity, not as a
  settled verdict.

**De-aliasing by follow-up (fold-over).** A Resolution III design can be augmented with a
second fraction (sign-reversed) to break the main-effect/two-factor-interaction aliases.
This is the sanctioned way to *recover* separability sequentially rather than pay for it
up front, and it maps naturally onto a research tree that iterates.

**Projection property.** A resolution-R fraction, projected onto any subset of R − 1
factors, is a full factorial (with replication) in those factors. So if screening finds
only a few active factors, the same data already contains a clean, separable full
factorial in them. This is why "screen wide, then project" is the standard strategy.

---

## 2. Orthogonal contrasts

A **contrast** among *t* treatment means is `L = Σ cᵢ ȳᵢ` with `Σ cᵢ = 0`. Two contrasts
`c` and `d` are **orthogonal** when, in addition:

- equal replication: `Σᵢ cᵢ dᵢ = 0`
- unequal replication `nᵢ`: `Σᵢ (cᵢ dᵢ / nᵢ) = 0`

At most **t − 1** mutually orthogonal contrasts exist for *t* treatments — the degrees of
freedom of the treatment effect. A complete orthogonal set **partitions the treatment sum
of squares additively**: the contrast SS add up exactly to the treatment SS. That additive
decomposition *is* the mathematical meaning of "each hypothesis got its own share of the
evidence, with no double counting."

> "If two contrasts are orthogonal, then the tests for the hypotheses are independent of
> one another, meaning the results of one test have no impact on the results of the other
> test."

Sources:
- https://www.southampton.ac.uk/~cpd/anovas/datasets/Orthogonal%20contrasts.htm
- https://online.stat.psu.edu/stat505/lesson/8/8.6
- https://www.unh.edu/halelab/ANFS933/Readings/Topic4_Reading.pdf
- https://online.stat.psu.edu/stat502/lesson/2/2.5
- https://arxiv.org/pdf/1807.10451 (Schad et al., contrast coding tutorial — how contrasts
  encode *specific* hypotheses, and how non-orthogonal coding makes coefficients
  uninterpretable in isolation)

### Three caveats a rule engine must encode

1. **Orthogonality is a property of the coefficients, chosen *a priori*.** Contrasts picked
   after seeing the means are not a priori and lose this protection entirely (the
   garden-of-forking-paths / data-dredging problem).
2. **Uncorrelated ≠ fully independent.** Orthogonal contrast *estimates* have zero
   covariance. But their *t*-tests share one pooled error variance `s²` in the denominator.
   They are independent only *conditional on* `s²`. This is the miniature, in-model version
   of shared-nuisance dependence (section 4): even a textbook-clean design has one shared
   ingredient in every answer.
3. **Non-orthogonal contrasts are still valid tests, just not separately interpretable.**
   Their SS overlap, so "how much of the effect is due to comparison 1" has no unique
   answer — the same pathology as aliasing, in contrast form.

---

## 3. Multiplicity

### 3.1 The arithmetic

Test *m* independent hypotheses each at α. The chance of at least one false positive —
the **family-wise error rate (FWER)** — is `1 − (1 − α)^m`. At α = 0.05 and m = 20 this is
about **64%**. Bundling hypotheses into one experiment does not create this problem, but it
concentrates it: the family becomes obvious and countable.

### 3.2 The procedures

| Procedure | Controls | Validity | Notes |
|---|---|---|---|
| **Bonferroni** | FWER | any dependence | test each at α/m. Simple, conservative, low power |
| **Holm** | FWER | any dependence | step-down; uniformly more powerful than Bonferroni; no reason to prefer plain Bonferroni |
| **Benjamini–Hochberg** | FDR = E[V / max(R,1)] | independence and positive dependence (PRDS) | much more power at large *m*; the standard in genomics |
| **Benjamini–Yekutieli** | FDR | arbitrary dependence | BH with a `Σ1/i` penalty |
| **Dunnett** | FWER | comparisons vs a common control | exploits the known correlation structure (~0.5) instead of assuming the worst |

FWER asks "is *any* of my claims wrong?"; FDR asks "what fraction of my claimed
discoveries are wrong?" FWER is right when each rejection is an expensive standalone
assertion; FDR is right when the output is a *ranked list for follow-up*.

Sources:
- https://www.publichealth.columbia.edu/research/population-health-methods/false-discovery-rate
- https://sites.globalhealth.duke.edu/rdac/wp-content/uploads/sites/27/2020/08/Core-Guide_Multiple-Comparisons-Part-I_01-11-18.pdf
- https://library.virginia.edu/data/articles/understanding-dunnetts-test
- https://en.wikipedia.org/wiki/Dunnett's_test
- https://arxiv.org/pdf/2108.04752 (why corrections control false positives poorly in
  practice — worth reading before treating a corrected p as a guarantee)
- https://arxiv.org/pdf/2401.11507 (the fallacy of using family-based error rates to make
  inferences about *individual* hypotheses)

### 3.3 Does one experiment testing several hypotheses require correction?

**It depends on the decision rule, not on the number of tests.** This is the crispest
finding in the whole multiplicity literature, and it comes from the FDA's *Multiple
Endpoints in Clinical Trials* guidance (final, Oct 2022):

- **"All must succeed" (co-primary endpoints, intersection–union).** "When the
  determination of effectiveness depends on success on all primary endpoints … there are
  no multiplicity issues related to primary endpoints, as there is only one path that
  leads to a successful outcome for the trial." **No adjustment.** (Note the flip side: the
  *type II* error inflates instead.)
- **"Any may succeed" (union–intersection).** Multiple chances to declare a win →
  **adjustment required**.
- **Components of a composite, examined to understand the composite.** No adjustment — the
  purpose is descriptive, not a separate claim.

Sources:
- https://www.fda.gov/media/162416/download
- https://www.fda.gov/files/drugs/published/Multiple-Endpoints-in-Clinical-Trials-Guidance-for-Industry.pdf
- https://www.federalregister.gov/documents/2022/10/21/2022-22882/multiple-endpoints-in-clinical-trials-guidance-for-industry-availability

Bender & Lange (*J Clin Epidemiol* 2001; 54:343–349) give the companion principle:
adjustment is required in **confirmatory** studies "whenever results from multiple tests
have to be combined in one final conclusion and decision," and is unnecessary in
**exploratory** studies without pre-specified hypotheses (echoing Rothman 1990, *No
adjustments are needed for multiple comparisons*, Epidemiology).

- https://pubmed.ncbi.nlm.nih.gov/11297884/
- https://www.sciencedirect.com/science/article/abs/pii/S0895435600003140
- https://onlinelibrary.wiley.com/doi/10.1002/bimj.70148 (Hoffmann 2026, a unifying guiding
  principle for when to adjust)
- https://www.sciencedirect.com/science/article/pii/S0895435625000216

### 3.4 Hierarchical / gatekeeping procedures — directly relevant to a hypothesis tree

Because crux's model is literally a tree of Questions over Hypotheses, the right
multiplicity machinery is **tree-structured gatekeeping**, built on the **closed testing
principle**, which controls FWER in the strong sense while letting families be tested in a
predefined sequence — each family "gatekeeps" the next. Secondary hypotheses are tested
only if the primary gate is passed. This is how a structured hypothesis tree gets both
per-hypothesis answers *and* a defensible overall error rate.

- https://users.iems.northwestern.edu/~ajit/papers/39)%20Tree%20gatekeeping.pdf
- https://arxiv.org/pdf/1812.00250 (graphical framework for hierarchically structured
  hypothesis families)
- https://multxpert.com/w

### 3.5 Does multiplicity change what "separable" means?

**No — and this distinction should be enforced in the tool.**

- **Separability (axis A) is about identification/estimability:** can the design attribute
  an effect to hypothesis *i* alone? It is a property of the *design matrix*.
- **Multiplicity (axis B) is about calibration:** given that we looked *m* times, is each
  answer's stated confidence honest? It is a property of the *decision rule*.

They are orthogonal concerns. Perfectly separable hypotheses still need a multiplicity
policy; a single unseparable hypothesis needs none. What multiplicity *does* change is the
**strength** of each separate answer, and it makes the count *m* a pre-registration
obligation: fix the hypothesis list before the run, or `m` is unknowable and no correction
is valid.

---

## 4. Shared nuisance / common-mode failure — the strongest argument against bundling

### 4.1 The concept, imported from reliability engineering

> A **common cause failure** is "a dependent failure in which two or more component fault
> states exist simultaneously, or within a short time interval, and are a direct result of
> a shared cause." **Common-mode failure** is the subset where components "fail in the same
> way for the same reason."
>
> "In theory, ultra reliability can be achieved for any system by providing sufficient
> redundant or spare components. In practice, common cause failures can disable all the
> back-up components so that the system fails. Elements which should fail independently
> are under some circumstances dependent."

- https://ntrs.nasa.gov/api/citations/20160005837/downloads/20160005837.pdf
- https://www.sciencedirect.com/topics/engineering/common-mode-failure
- https://accendoreliability.com/common-mode-failures/

The analogy is exact. *m* hypotheses bundled into one run look like *m* independent
verdicts, but they are *m* redundant channels sharing a substrate. One shared defect
flips all of them together, and — critically — **the failure is invisible from inside the
experiment**, because every arm is affected.

### 4.2 The statistical form

Write `y = Xβ + Zu + ε`, where `u` is a shared nuisance (batch, seed, pipeline version) and
`Z` its incidence. Two regimes, with different damage:

**(a) The nuisance VARIES across arms and correlates with the design (`X'Z ≠ 0`).**
Classic confounding — an *identification* failure. The nuisance steals signal from
specific effects. Batch effects are the canonical case: measurements "are affected by
laboratory conditions, reagent lots and personnel differences," and the problem becomes
critical "when batch effects are correlated with an outcome of interest and lead to
incorrect conclusions" (Leek et al., *Nature Reviews Genetics* 2010).
- https://www.nature.com/articles/nrg2825

**(b) The nuisance is CONSTANT across all arms (one seed, one dataset, one preprocessing
implementation, one operator).** Within-experiment contrasts may be perfectly internally
valid — the constant cancels. But **every answer is conditional on a single draw of that
nuisance, whose effective sample size is 1 and whose error is never estimated**. This is a
*generalization* failure, not an identification failure, and it is the sneakier of the two
because the design audit passes: `X'X` is diagonal, resolution is V, everything looks
separable. All *m* answers still fail together if the shared element is wrong.

**Distinguishing (a) from (b) is the key diagnostic**, and both must be checked.

### 4.3 The canonical shared elements

| Shared element | Failure mode | Detection / mitigation |
|---|---|---|
| One batch / run / plate / day | batch effect confounded with condition | block on batch, randomize assignment within batch, replicate across batches |
| One preprocessing pipeline | a bug shifts every downstream answer identically | independent re-implementation; end-to-end positive controls; version pinning + audit |
| One random seed | run-to-run variance masquerades as effect | ≥3–5 seeds per configuration, report variance |
| One shared control arm | all comparisons correlated (ρ ≈ 0.5) | Dunnett; or replicate the control |
| One dataset / one train-test split | overfitting to that split; all claims co-vary | multiple splits, held-out second dataset |
| One codebase / one metric implementation | a metric bug flips every verdict the same way | reference implementation, held-out sanity task |
| One operator / one instrument | systematic drift | rotate, randomize run order |

**Preprocessing bugs — the worst documented case.** Baggerly & Coombes' forensic
bioinformatics work on the Duke/Potti chemosensitivity signatures found "off-by-one" gene
lists from a header-row mismatch and label swaps of "sensitive"/"resistant" that made
predictions backwards. A *single shared data-handling defect* invalidated a family of
results at once; papers were retracted in 2011 and clinical trials halted. The tell: every
downstream conclusion was wrong in a *correlated* way, and none of the internal comparisons
revealed it.
- https://arxiv.org/pdf/1010.1092
- https://www.csescienceeditor.org/article/forensic-bioinformatics-investigating-reproducibility-of-results/
- https://academic.oup.com/bib/article/24/6/bbad375/7326135 (five pillars of computational
  reproducibility)

**Random seeds — the ML case.** Henderson et al., *Deep Reinforcement Learning that
Matters* (AAAI 2018): on HalfCheetah, "it is possible to get learning curves that do not
fall within the same distribution at all, just by averaging different runs with the same
hyperparameters, but different random seeds." One seed proves nothing; run-to-run variance
is indistinguishable from the effect under test.
- https://arxiv.org/pdf/1709.06560
- https://ar5iv.labs.arxiv.org/html/1806.08295 (Colas et al., *How Many Random Seeds?* —
  statistical power analysis for RL)

**Shared control — a quantified, unavoidable dependence.** When *m* treatments are each
compared to one control, "if the control mean is unusually high or low by chance, all
comparisons are affected simultaneously," giving correlation ≈ 0.5 with equal *n*.
Dunnett's test exists precisely to model this correlation instead of ignoring it. Note
what this means: **a shared control makes hypotheses non-independent even in an otherwise
flawless design.** They remain *separable* (each estimand is identified) but their errors
are correlated — the answers are jointly, not individually, calibrated.
- https://library.virginia.edu/data/articles/understanding-dunnetts-test

### 4.4 The evidential consequence

*m* hypotheses passing together in one run is **much weaker** than *m* hypotheses passing
in *m* independent runs, because the effective number of independent tests is less than
*m*. A shared nuisance produces **correlated verdicts** — correlated false positives *or*
correlated false negatives. It is the reason bundling should be a deliberate, recorded
decision rather than a default.

### 4.5 Mitigations (Fisher's three, plus two modern ones)

1. **Blocking.** Make the nuisance a factor in the design so it is *orthogonal* to the
   effects of interest instead of confounded with them. Blocking converts a threat into an
   estimable term. (Note: in fractional designs, blocks themselves consume alias capacity —
   effects are deliberately confounded with blocks.)
2. **Randomization.** For nuisances you cannot name or block, randomize assignment and run
   order so their expected correlation with the design is zero.
3. **Replication.** Replicate the *shared element itself* — multiple seeds, multiple
   batches, multiple splits, two independent implementations. This converts a common-mode
   constant into a random effect whose variance can be estimated. This is the only
   mitigation that helps regime (b).
4. **Independent re-derivation** of anything shared and computational (the Baggerly lesson).
5. **Outcome-neutral checks** — see section 4.6, which is where this gets interesting.

### 4.6 Outcome-neutral checks: where separability breaks — or is rescued

A parallel line of work distinguishes two classes of check inside an experiment:

- **Hypothesis-directed checks** — the tests whose outcome *is* the answer to some Hᵢ.
- **Outcome-neutral checks** — positive controls, manipulation checks, sanity tasks,
  known-answer probes. These must pass **regardless of which hypothesis is true**. Their
  failure does not refute anything; it **invalidates the run**.

My material supports this framing strongly and, I think, resolves the bundling question.
The DoE and reliability literatures contain the same idea under different names — positive
and negative controls, "known-truth" spike-ins, instrument calibration standards — and
Leek et al.'s recommended use of negative-control probes to estimate batch structure is
exactly an outcome-neutral check.

**The key structural claim: outcome-neutral checks and common-mode failures are dual.**
A shared outcome-neutral check is precisely a *detector* for the shared nuisance that
would otherwise cause common-mode failure. So sharing them is not the problem — sharing
them is the *fix*, provided the check is sensitive to the shared element:

- **Separability is RESCUED** when the bundled hypotheses share outcome-neutral checks that
  are **sensitive to every shared element** and are **evaluated before** any hypothesis
  verdict is read. A positive control that exercises the same preprocessing pipeline, the
  same batch, the same control arm, and the same metric code turns an invisible common-mode
  failure into a visible, run-invalidating one. The *m* verdicts then fail *safe* (all
  marked invalid) rather than fail *silently* (all marked wrong-but-confident). Note this
  does not restore independence — it restores *detectability*, which is what a research
  notebook actually needs.
- **Separability BREAKS** when a shared element has **no** outcome-neutral check covering
  it. Then the bundle has an undetectable single point of failure, and the *m* answers are
  really one answer wearing *m* hats. The absence of a covering check is the machine-
  checkable red flag.
- **Separability also BREAKS in a subtler way** when an outcome-neutral check is *not*
  outcome-neutral — i.e. it can only pass if one of the bundled hypotheses is true. Then
  the check is a hypothesis-directed test in disguise, and using it as a run-validity gate
  makes every other verdict conditional on that hypothesis. This is a real and easy mistake
  when one bundled hypothesis concerns the very manipulation the others rely on ("does the
  intervention do anything at all?" is a hypothesis; "did the intervention get applied?" is
  a manipulation check — bundling them collapses the distinction).

**Rule form.** For each shared element *s* in a bundle, require an outcome-neutral check
`c(s)` that (i) would fail if *s* were defective, (ii) has a pre-declared pass criterion,
(iii) is logically independent of every Hᵢ's truth value, and (iv) gates the run: if `c(s)`
fails, *all* bundled hypotheses return **invalid**, not **refuted**. Uncovered shared
elements must be listed as common-mode risks attached to every hypothesis in the bundle.

---

## 5. Practical guidance from experienced experimentalists

### 5.1 The named tradeoff: efficiency vs. interpretability

Sometimes stated as **resolution vs. run size**, or in the DoE workflow as **screening →
characterization → optimization**. More runs and higher resolution buy cleaner attribution;
fewer runs buy speed at the cost of aliasing. Fractional factorials are the explicit
purchase of interpretability with assumptions rather than with runs.

- Screening designs are for "when you have many factors to consider," typically at
  Resolution III, where interactions are "assumed an order of magnitude less important"
  than main effects.
- Plackett–Burman designs push this further (run counts in multiples of 4) at Resolution
  III with complex partial aliasing.
- Supersaturated designs go past *k* > *n*, relying entirely on effect sparsity; selected
  by E(s²)-optimality, which literally measures "the nonorthogonality between pairs of
  factor columns."
- https://www.itl.nist.gov/div898/handbook/pri/section3/pri3346.htm
- https://arxiv.org/pdf/1510.05248
- https://arxiv.org/pdf/2210.13943 (D- and A-optimal screening designs)

### 5.2 Sequential experimentation is the standard advice

NIST: "Even when the experimental goal is to eventually fit a response surface model, the
first experiment should be a screening design when there are many factors to consider."
Box's associated budgeting heuristic: spend roughly a quarter of the experimental budget
on the first experiment, keeping resources for the follow-ups the first will demand.

Practical implication for crux: a **bundle is an appropriate first move** (broad, cheap,
low-resolution, provisional answers), followed by **narrow, high-resolution experiments**
on the few hypotheses that survive. Bundling and atomicity are not in conflict if the tree
records *which stage* an answer came from and how provisional it is.

### 5.3 ML ablation practice

- **Ceteris paribus.** A valid ablation isolates a single change with everything else fixed:
  identical seeds/initialization/shuffling, identical hyperparameters, identical data and
  splits, identical evaluation protocol.
- **Seeds.** Report variance across multiple seeds; a floor of ~3 seeds per configuration
  before a removal counts as validated.
- **OFAT ablations cannot disambiguate main effects from interactions.** "A standard
  one-factor-at-a-time ablation is the cheapest design, but it cannot disambiguate main
  effects from two-factor interactions" — if components interact, use a factorial.
- **The failure this prevents.** Lipton & Steinhardt, *Troubling Trends in Machine Learning
  Scholarship*, name "failure to identify the sources of empirical gains" as a core
  pathology: "too frequently, authors propose many tweaks absent proper ablation studies,
  obscuring the source of empirical gains." That sentence is the ML-native statement of
  non-separability.
- https://arxiv.org/abs/1807.03341
- https://www.emergentmind.com/topics/controlled-ablation-study
- https://arxiv.org/pdf/2006.05990 (Andrychowicz et al., *What Matters in On-Policy RL?* —
  a large-scale, properly factorial ablation)

---

## 6. The checkable separability condition

### 6.1 Statement

> **A single experiment E validly settles hypotheses H₁…H_m separately if and only if each
> Hᵢ has (1) its own estimand, (2) its own comparison in the design, (3) its own declared
> assumptions, (4) its own failure mode, and (5) its own calibrated decision rule.**

### 6.2 The five checks, in machine-applicable form

**C1 — DISTINCT ESTIMAND.** Each Hᵢ maps to a distinct, pre-registered quantity θᵢ (a
contrast, coefficient, or effect) and a decision rule that reads θᵢ *alone*. If two
hypotheses map to the same θ, they are one hypothesis and must be merged. If Hᵢ's decision
rule references Hⱼ's outcome, they are a compound hypothesis (or need explicit gatekeeping).

**C2 — IDENTIFIABILITY (no aliasing).** The design must contain, for each Hᵢ, at least one
comparison that varies what Hᵢ is about while holding constant — or balancing over —
everything the other hypotheses are about.
- Formal: `X'X` non-singular, and ideally diagonal (orthogonal), over the model space you
  entertain.
- Two-level shorthand: **no two hypotheses may share a design column, and no hypothesis's
  column may equal a product of columns you also care about.**
- Fractional shorthand: **the design's resolution must exceed the order of the highest-order
  effect any bundled hypothesis is about.** Main-effect bundles need Res ≥ IV; any
  interaction hypothesis needs Res ≥ V.
- **Automatic fail:** a factor a hypothesis is about is never varied in E.
- **Automatic fail:** the realized (not planned) design is unbalanced enough that the
  factor is confounded with block, batch, or run order.

**C3 — ASSUMPTION LEDGER.** Where separation is bought with assumptions rather than runs
(effect sparsity, "no three-way interactions", "the aliased term is negligible"), those
assumptions are recorded *on the answer*, and the answer is marked provisional. Resolution
is the standard name for the price paid: Res III answers are screening verdicts, not
settled ones.

**C4 — INDEPENDENT FAILURE (the common-mode check).** Enumerate the shared elements of E:
batch/run, dataset, split, seed, preprocessing pipeline, codebase, metric implementation,
control arm, operator, instrument. For each shared element *s*, one of the following must
hold:
  (a) *s* is **blocked** — represented in the design and orthogonal to every θᵢ; or
  (b) *s* is **replicated** — ≥ 2 (preferably ≥ 3) independent instances, so its
      contribution is estimable rather than constant; or
  (c) *s* is **covered by an outcome-neutral check** `c(s)` — a positive control /
      manipulation check that would fail if *s* were defective, whose pass criterion is
      pre-declared, whose result is logically independent of every Hᵢ's truth value, and
      whose failure marks **all** bundled hypotheses **invalid** (not refuted); or
  (d) *s* is **recorded as an unmitigated common-mode risk attached to every Hᵢ in the
      bundle**, with the bundle's joint evidential weight discounted accordingly.
Additionally: **no outcome-neutral check may be one whose pass depends on some Hᵢ being
true.** If it is, it is a hypothesis in disguise and every other verdict silently
conditions on it.

**C5 — CALIBRATED DECISION.** The hypothesis list and count *m* are fixed before the run.
The family and target error rate are declared, and:
  - decision rule "**all must hold**" (intersection–union) → no α adjustment needed;
  - decision rule "**any may hold**" (union–intersection) → FWER control (Holm ≥ Bonferroni;
    Dunnett if the comparisons share a control);
  - the bundle is an **exploratory screen producing a ranked follow-up list** → FDR (BH);
  - hierarchically ordered families in a Question/Hypothesis tree → **closed-testing /
    gatekeeping**, testing families in sequence.

**C6 — POWER PER HYPOTHESIS (practical, not formal).** Each Hᵢ must have enough runs to be
answerable on its own. A bundle that leaves every hypothesis underpowered yields *m*
"inconclusive"s, not *m* answers, and burns the experiment.

**C7 — POST-HOC INDEPENDENCE AUDIT.** After the run, each Hᵢ must have its own evidence
trace: you can state Hᵢ's verdict without referring to Hⱼ's verdict. **If hypothetically
flipping Hⱼ's answer would change Hᵢ's answer, they were not separable.**

### 6.3 The veto list (fast negative screen)

Refuse or downgrade the bundle if any of these hold:
1. Two hypotheses resolve to the same design column / same estimand → **aliased**.
2. A hypothesis's factor is never varied → **not estimable**.
3. Any hypothesis concerns an interaction and the design is Resolution < V → **aliased**.
4. The design is unbalanced such that a factor is confounded with batch, block, or run
   order → **confounded**.
5. A shared element (seed, split, pipeline, control) is neither blocked, nor replicated,
   nor covered by an outcome-neutral check → **common-mode risk**; internal contrasts may
   still be valid but no absolute or generalization claim is separable.
6. One hypothesis's decision rule reads another's outcome → **compound**; merge or gatekeep.
7. The hypothesis list was not fixed before the run → *m* is unknown; **no valid
   calibration** is possible.
8. An outcome-neutral check can only pass if one bundled hypothesis is true → **the gate is
   not neutral**; all other verdicts are conditional on it.

### 6.4 The three-line version for a rulebook

1. **Different lever.** Each hypothesis must be turned by a different, independently varied
   knob in the design — its own column, not shared and not a product of others.
2. **Different failure.** No single shared ingredient may be able to flip all the answers
   at once undetected; block it, replicate it, catch it with an outcome-neutral control, or
   log it as a risk on every hypothesis in the bundle.
3. **Different verdict.** Each hypothesis must carry its own pre-registered estimand,
   threshold, and multiplicity-aware decision rule, and must be statable without reference
   to the others.

---

## Source list

**Design of experiments / factorials**
- NIST/SEMATECH e-Handbook, Fractional factorial designs — https://www.itl.nist.gov/div898/handbook/pri/section3/pri334.htm
- NIST, Confounding (aliasing) — https://www.itl.nist.gov/div898/handbook/pri/section3/pri3343.htm
- NIST, Design resolution — https://www.itl.nist.gov/div898/handbook/pri/section3/pri3344.htm
- NIST, Screening designs — https://www.itl.nist.gov/div898/handbook/pri/section3/pri3346.htm
- Penn State STAT 503, More fractional factorial designs — https://online.stat.psu.edu/stat503/lesson/8/8.1
- Minitab, What is design resolution — https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/what-is-design-resolution/
- Minitab, Orthogonal designs — https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/basics/orthogonal-designs/
- JMP, Fractional factorial designs — https://www.jmp.com/en/statistics-knowledge-portal/design-of-experiments/screening-designs/fractional-factorial-designs
- learnche, Design resolution — https://learnche.org/pid/design-analysis-experiments/fractional-factorial-designs/design-resolution
- Design of Experiments for Screening (arXiv) — https://arxiv.org/pdf/1510.05248
- Orthogonal structure in the design matrix (JHU) — https://www.biostat.jhsph.edu/~iruczins/teaching/140.751/notes/ch8.pdf
- ASQ, What is DoE — https://asq.org/quality-resources/design-of-experiments
- OFAT vs factorial — https://management.curiouscatblog.net/2011/05/25/one-factor-at-a-time-ofat-versus-factorial-designs/

**Contrasts**
- Penn State STAT 505, Orthogonal contrasts — https://online.stat.psu.edu/stat505/lesson/8/8.6
- Penn State STAT 502, Contrast analysis — https://online.stat.psu.edu/stat502/lesson/2/2.5
- UNH, Topic 4: Orthogonal contrasts — https://www.unh.edu/halelab/ANFS933/Readings/Topic4_Reading.pdf
- Southampton, Orthogonal contrasts — https://www.southampton.ac.uk/~cpd/anovas/datasets/Orthogonal%20contrasts.htm
- Schad et al., How to capitalize on a priori contrasts — https://arxiv.org/pdf/1807.10451

**Multiplicity**
- FDA, Multiple Endpoints in Clinical Trials (final, 2022) — https://www.fda.gov/media/162416/download
- Bender & Lange, Adjusting for multiple testing—when and how? — https://pubmed.ncbi.nlm.nih.gov/11297884/
- Hoffmann, When to Adjust for Multiple Testing: A Unifying Guiding Principle — https://onlinelibrary.wiley.com/doi/10.1002/bimj.70148
- Columbia, False Discovery Rate — https://www.publichealth.columbia.edu/research/population-health-methods/false-discovery-rate
- Duke Core Guide, Multiple Testing Part 1 — https://sites.globalhealth.duke.edu/rdac/wp-content/uploads/sites/27/2020/08/Core-Guide_Multiple-Comparisons-Part-I_01-11-18.pdf
- Dmitrienko & Tamhane, Tree-structured gatekeeping tests — https://users.iems.northwestern.edu/~ajit/papers/39)%20Tree%20gatekeeping.pdf
- Graphical framework for hierarchically structured hypothesis families — https://arxiv.org/pdf/1812.00250
- Why corrections provide poor control in the real world — https://arxiv.org/pdf/2108.04752
- The fallacy of family-based error rates for individual hypotheses — https://arxiv.org/pdf/2401.11507
- Dunnett's test — https://library.virginia.edu/data/articles/understanding-dunnetts-test

**Shared nuisance / common-mode**
- Leek et al., Batch effects in high-throughput data, Nat Rev Genet 2010 — https://www.nature.com/articles/nrg2825
- NASA, Common cause failures and ultra reliability — https://ntrs.nasa.gov/api/citations/20160005837/downloads/20160005837.pdf
- Common mode failure overview — https://www.sciencedirect.com/topics/engineering/common-mode-failure
- Baggerly & Coombes, Deriving chemosensitivity from cell lines (forensic bioinformatics) — https://arxiv.org/pdf/1010.1092
- Forensic Bioinformatics: Investigating Reproducibility of Results — https://www.csescienceeditor.org/article/forensic-bioinformatics-investigating-reproducibility-of-results/
- Five pillars of computational reproducibility — https://academic.oup.com/bib/article/24/6/bbad375/7326135
- Henderson et al., Deep Reinforcement Learning that Matters — https://arxiv.org/pdf/1709.06560
- Colas et al., How Many Random Seeds? — https://ar5iv.labs.arxiv.org/html/1806.08295

**ML ablation methodology**
- Lipton & Steinhardt, Troubling Trends in Machine Learning Scholarship — https://arxiv.org/abs/1807.03341
- Andrychowicz et al., What Matters in On-Policy RL? — https://arxiv.org/pdf/2006.05990
- Controlled ablation study overview — https://www.emergentmind.com/topics/controlled-ablation-study
