# Experimental design and decisiveness

Research brief for **crux** (research-management tool: tree of Questions → falsifiable
Hypotheses → pre-registered verifiables → derived verdict).

**Question driving the research:** what makes an experiment capable of *decisively*
answering the question it was run for, versus leaving a partial or ambiguous answer?

**The failure crux is trying to prevent:** after a run, some verifiables pass and some
fail, and the researcher has no decisive answer.

---

## 0. The headline result

The literature has a direct, well-developed answer to the crux failure mode, and it is
not "be more rigorous". It is three specific structural moves, all of which are made
**before** the run:

1. **Rank the checks.** Not all verifiables are equal. Clinical trial practice groups
   endpoints into a *hierarchy* — primary (decides the verdict), secondary (supports),
   exploratory (generates the next question). A flat, unranked set of checks is a
   guaranteed generator of the "3 of 5 passed, now what?" outcome, because no
   pass/fail pattern maps to a verdict.
   → FDA, *Multiple Endpoints in Clinical Trials* (2022).

2. **Separate the checks that test the hypothesis from the checks that test the
   experiment.** The Registered Reports literature calls the second class
   **outcome-neutral tests** — positive controls, manipulation checks, sanity checks,
   floor/ceiling checks. Their defining property: they must pass *whatever the
   hypothesis turns out to be*, and their failure invalidates the run rather than
   refuting the hypothesis. Mixing these two classes into one flat list is precisely
   what turns a clean "the assay didn't work" into a muddy "partial support".
   → PLOS Comp Bio, *Ten simple rules for writing a Registered Report* (2022);
   Scientific Reports / Royal Society RR policies.

3. **Pre-write the interpretation of every outcome pattern**, not just the predicted
   one. Tom Stafford's practitioner checklist states it as a question:
   *will you be able to interpret all possible results that aren't in line with your
   predictions?* Registered Report design tables have a literal column for
   "interpretation given different outcomes". If a pattern has no pre-written reading,
   it will produce an ambiguous verdict on arrival.
   → https://tomstafford.github.io/psy-checklist/

Everything else below elaborates, qualifies, or supplies the deterministic checks.

---

## 1. Core DoE principles that bear on decisiveness

### 1.1 The Fisherian triad: randomization, replication, blocking

Montgomery's *Design and Analysis of Experiments* and Box–Hunter–Hunter's *Statistics
for Experimenters* both organize the field around three principles. The division of
labour matters for decisiveness:

| Principle | What it buys | Failure → what kind of ambiguity |
|---|---|---|
| **Randomization** | Removes *bias*; averages out lurking variables so they cannot be confounded with the treatment | A result you cannot attribute — "the effect is real but might be the batch/order/machine" |
| **Replication** | Gives an *estimate of experimental error*, without which no significance statement is possible | You cannot tell signal from noise at all — no verdict is derivable |
| **Blocking** | Removes *known nuisance variance*, raising precision | Underpowered by noise; true effect drowned |

Key asymmetry: **randomization protects validity, replication and blocking protect
precision.** A design can be unbiased and still undecisive (too noisy), or precise and
still uninterpretable (confounded). Both must be checked.
- JMP, *Key Principles of Experimental Design*:
  https://www.jmp.com/en/statistics-knowledge-portal/design-of-experiments/key-design-of-experiments-concepts/key-principles-of-experimental-design
- Nature Sci Rep (2020) argues that for preclinical work only two designs are worth
  general use — completely randomized and randomized block:
  https://www.nature.com/articles/s41598-020-74538-3

### 1.2 Controls, and specifically the two kinds

- **Negative control** (no-treatment / vehicle / A/A arm / random-baseline): establishes
  the noise floor. Answers "would I have seen this even with nothing happening?" In A/B
  testing this is the **A/A test**, run explicitly to measure the false-positive rate of
  the pipeline itself. In ML ablations the analogue is a **random / shuffled baseline**
  (e.g. random retrieval instead of learned retrieval).
- **Positive control**: establishes that the apparatus *can* detect the effect if it is
  there. This is the concept regulators call **assay sensitivity** — a property of the
  *trial*, defined as its ability to distinguish an effective from an ineffective
  treatment. Without assay sensitivity a trial **is not internally valid** and a null
  result is uninformative rather than negative.
  → ICH E10, *Choice of Control Group in Clinical Trials*;
  https://en.wikipedia.org/wiki/Assay_sensitivity

**This is the single most load-bearing idea for crux.** A negative result is decisive
only if a positive control passed. Without one, "hypothesis false" and "experiment
broken" are observationally identical — the canonical ambiguous outcome.

### 1.3 Blinding

Blinding of participants, operators, and — critically — of the person who codes,
cleans, or excludes data. Wicherts et al. list non-blinded correction/coding/exclusion
*during* data collection as a distinct researcher degree of freedom (C3), separate from
non-blinded assessment. Where human blinding is impossible (ML, most simulation),
the domain-general residue is **analyst blinding**: fixing the analysis before seeing
outcome data.

### 1.4 Confounding

Two distinct meanings, both relevant:
- *Causal* confounding: a lurking variable varies with the treatment.
- *DoE* confounding (aliasing): in fractional factorial designs, effects are
  deliberately aliased with each other. A resolution-III design cannot separate main
  effects from two-factor interactions **by construction** — the ambiguity is baked into
  the design, not caused by bad luck. Choosing design resolution *is* choosing which
  questions the experiment can answer.

### 1.5 Power, sample size, effect size

- Power analysis requires an *a priori* effect size. Wicherts D6: failing to conduct a
  well-founded power analysis; D7: failing to specify the sampling plan.
- Gelman & Carlin, *Beyond Power Calculations* (2014): power is not enough. Add
  **Type S** (sign) and **Type M** (magnitude/exaggeration) error. In a noisy,
  low-power design, a statistically significant result is *systematically* exaggerated
  and can have the wrong sign. So an underpowered experiment does not merely fail to
  find things — **it actively manufactures confident wrong answers.**
  https://journals.sagepub.com/doi/10.1177/1745691614551642
- The effect size to power for must be the **SESOI** — smallest effect size of interest
  — declared in advance, from theory, prior literature, or practical decision relevance.
  Powering for "whatever the pilot showed" is circular.

### 1.6 Making a null decisive

A plain non-significant result is the classic ambiguous outcome. Two established
remedies, both requiring pre-declaration:
- **Equivalence testing / TOST** against a declared SESOI: lets you *accept* the null
  in the sense of "any effect is too small to matter". Lakens, Scheel & Isager (2018):
  https://journals.sagepub.com/doi/10.1177/2515245918770963
- **Bayes factors / interval hypotheses**: quantify evidence *for* the null rather than
  absence of evidence against it.

Rule: a hypothesis whose only stated verifiable is "p < 0.05" has no decisive negative
branch. It needs a declared SESOI and an equivalence bound.

### 1.7 Severity and risky prediction — the philosophy layer

- **Popper / Meehl**: a test is strong to the degree the prediction is *risky* — a
  narrow interval or point value the theory would not have survived by chance. Meehl's
  "crud factor": in soft sciences everything correlates with everything, so a mere
  directional prediction ("group A > group B") is a weak test whose refutation depends
  only on sample size. A **point or interval prediction** is a strong test.
  https://meehl.umn.edu/sites/meehl.umn.edu/files/files/147appraisingamending.pdf
- **Mayo**, *Statistical Inference as Severe Testing*: data support a claim only if the
  test *would probably have exposed the claim as false, had it been false*. Agreement
  between data and hypothesis is not evidence unless the procedure had a real chance of
  disagreeing.
  https://ndpr.nd.edu/reviews/statistical-inference-as-severe-testing-how-to-get-beyond-the-statistics-wars/
- **Platt**, *Strong Inference* (1964): devise **alternative** hypotheses; devise a
  crucial experiment that **excludes one or more**; run it; recycle. Decisiveness comes
  from the design being *discriminating between rivals*, not from confirming one.
  https://journals.biologists.com/jeb/article/217/8/1202/13095/Fifty-years-of-J-R-Platt-s-strong-inference

For crux, this converts to a check on the *hypothesis*, not the experiment: **a
verifiable whose predicted outcome is compatible with the leading alternative
hypothesis cannot be decisive, no matter how well the experiment is run.**

---

## 2. Named failure modes that produce ambiguous results

Grouped by where they bite. The "detectable?" column previews §5.

| # | Failure mode | Mechanism | Ambiguity produced | Detectable in a written design? |
|---|---|---|---|---|
| 1 | **Underpowering** | n too small for the SESOI | Null is uninformative; significant results are exaggerated (Type M) and may have wrong sign (Type S) | Partly — deterministic: is n stated? is a power calc / SESOI stated? |
| 2 | **No negative control** | No noise floor | Cannot rule out artifact | Deterministic: is a control arm declared? |
| 3 | **No positive control / no assay sensitivity** | Apparatus never shown to work | Null ≡ "broken experiment" | Deterministic: is a positive control declared? |
| 4 | **Confounding / aliasing** | Factor varies with treatment; or design resolution too low | Effect real but unattributable | Judgment (causal) / deterministic (design resolution) |
| 5 | **Ceiling / floor effects** | Measure saturates; no room to move | Manipulation *appears* to have no effect; correlations shrink toward zero | Judgment, but a *declared range check* is deterministic |
| 6 | **Wrong instrument / poor measurement validity** | Measure doesn't capture the construct | Result is about something else | Judgment |
| 7 | **Multiple comparisons** | Many endpoints, no alpha control | Mixed pass/fail; cherry-picking; the crux failure mode exactly | Deterministic: count endpoints; is a correction/hierarchy stated? |
| 8 | **Optional stopping / peeking** | Stop when it looks good | Type I error inflates dramatically; Simmons et al. show combined flexibility can push it past 0.6 | Deterministic: is a stopping rule stated? |
| 9 | **Simpson's paradox** | Aggregate trend reverses within subgroups | Two contradictory true answers | Deterministic: are subgroups pre-specified? Balance is a design fix |
| 10 | **Sample ratio mismatch (SRM)** | Observed split ≠ intended split | Whole result untrustworthy; randomization suspect | Deterministic post-run check; deterministic pre-check "is the intended ratio stated?" |
| 11 | **Carryover / contamination** | Previous experiment or other arm leaks in | Effect attenuated or spurious | Judgment |
| 12 | **Primacy / novelty effects** | Short-run reaction ≠ long-run behaviour | Direction flips with horizon | Deterministic: is a measurement window stated? |
| 13 | **Vague / directional-only hypothesis** | Wicherts T2 | Any outcome can be narrated as support | Judgment, LLM-checkable |
| 14 | **Flexible outcome selection** | Wicherts D3/D4: multiple ways to measure the same DV | Post hoc choice of the one that worked | Deterministic: is *the* primary measure named and singular? |
| 15 | **Flexible exclusion** | Wicherts D5/C3 | Sample defined after seeing results | Deterministic: are exclusion criteria stated pre-run? |
| 16 | **Metric/OEC misalignment** | The measured thing isn't the thing you care about | You win the test, lose the war | Judgment |
| 17 | **Hyperparameter / tuning asymmetry (ML)** | Treatment tuned harder than baseline | "Win" is a tuning artifact | Deterministic: is a tuning budget declared for *both* arms? |
| 18 | **Seed variance (ML/RL)** | Single-seed comparisons | Differences are noise; Henderson et al. show RL results flip across seed sets | Deterministic: is number of seeds/runs stated? |
| 19 | **Data leakage / train-test contamination** | Test info in training | Inflated performance, non-replicable | Judgment + some deterministic checks |
| 20 | **Regression to the mean** | Extreme-selected units drift back | Fake improvement in single-arm designs | Judgment; a control arm defuses it |
| 21 | **Demand / experimenter / placebo effects** | Expectation drives outcome | Effect real but not from the mechanism | Judgment; blinding declared is deterministic |
| 22 | **Twyman's law violation** | A too-good result taken at face value | Usually an instrumentation bug, not a discovery | Post-run; a declared "if result > X, run validity checks" rule is deterministic |

Sources for this table:
- Wicherts et al. (2016), *Degrees of Freedom in Planning, Running, Analyzing, and
  Reporting Psychological Studies: A Checklist to Avoid p-Hacking*, Frontiers in
  Psychology — the canonical 34-item list.
  https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2016.01832/full
- Simmons, Nelson & Simonsohn (2011), *False-Positive Psychology* — researcher degrees
  of freedom, optional stopping.
- Kohavi, Tang & Xu, *Trustworthy Online Controlled Experiments* (2020); and Kohavi's
  pitfalls deck:
  https://exp-platform.com/Documents/2017-05-17EmetricsControlledExperimentsPitfallsKohaviNR.pdf
- Henderson et al. (2017), *Deep Reinforcement Learning That Matters*:
  https://arxiv.org/pdf/1709.06560
- Ceiling/floor: https://en.wikipedia.org/wiki/Ceiling_effect_(statistics) ;
  PLOS ONE robustness study: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0220889
- Simpson's paradox: Kievit et al., *Simpson's paradox in psychological science: a
  practical guide*, Frontiers in Psychology (2013):
  https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00513/full ;
  SEP entry: https://plato.stanford.edu/entries/paradox-simpson/

### 2.1 The specific pathology crux is fighting

Multiple pre-registered checks with **no pre-declared aggregation rule** is a known,
named problem: the **multiplicity problem**, and its solution in regulated research is
a *pre-specified testing hierarchy*.

FDA's *Multiple Endpoints in Clinical Trials* (final guidance, Oct 2022) prescribes:
- endpoints grouped hierarchically by importance: **primary** (required for the
  conclusion), **secondary** (support / additional effects), **exploratory**;
- **co-primary** endpoints when *all* of several must succeed — note explicitly that
  co-primaries do **not** inflate Type I error, they inflate **Type II** error (i.e.
  requiring everything to pass makes the experiment harder to win, and requires more n);
- alternatively, alpha is *allocated* across endpoints, or endpoints tested in a fixed
  sequence where testing stops at the first failure (fixed-sequence / gatekeeping);
- **composite endpoints** when several outcomes should be collapsed into one.

https://www.fda.gov/media/162416/download

**Translation to crux:** every hypothesis needs a declared *combination rule* over its
verifiables. The four standard shapes are:
- **conjunctive (co-primary / AND)** — all must pass; costs power, buys a crisp verdict
- **hierarchical / gatekeeping** — ordered; stop at first failure
- **single primary + supporting** — one verifiable decides; the rest are context
- **composite** — collapse into one derived measure

Anything not in one of these shapes will produce a partial verdict.

---

## 3. Pre-flight checklists used by practitioners

### 3.1 Tom Stafford's experiment design checklist (psychology, but domain-general)
https://tomstafford.github.io/psy-checklist/

1. Did you discuss authorship with the research team?
2. Is your study adequately powered?
3. Should you include a manipulation check?
4. Does your experiment produce data that you can analyse?
5. How will you judge the size of any effect?
6. **Will you be able to interpret all possible results which aren't in line with your predictions?**
7. Do you have a plan (and consent) for storing and sharing the data?
8. Have you checked prior work on this topic?
9. How will the final result be criticised?

Plus a "common criticisms" list to pre-mortem against: failure to generalise, placebo
effect, demand effect, experimenter bias, selection and survivorship bias, regression to
the mean, common method variance, "so what?", false positive, confound.

Item 6 is the crux failure mode stated as a pre-flight question. Item 9 is a pre-mortem.

### 3.2 Minitab's pre-experiment activities (industrial DoE)
https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/basics/checklist-of-pre-experiment-activities/

1. Train everyone involved; document procedures.
2. **Validate the measurement system** — verify that the instrument reads what you
   think, both for the response and for setting the factor levels.
3. Check that all design combinations are actually feasible and safe.
4. **Perform trial runs** — assess material consistency, verify measurement, confirm
   procedures, and obtain preliminary estimates of variation.

Note (4): the *pilot run exists to estimate variance so the power calculation is real*.
This is the industrial answer to "where does the effect size for the power calc come
from".

### 3.3 Registered Reports Stage 1 criteria (the closest analogue to crux's model)

Journals with Registered Reports (Nature Sci Rep, Royal Society Open Science, PCI RR,
Taylor & Francis, Cambridge) converge on Stage 1 criteria along these lines:
- the question is important and the hypotheses are sound and plausible;
- the methodology and analysis are **capable of testing the stated hypotheses**;
- the sampling plan (power analysis / Bayesian design analysis) is adequate;
- **sufficient outcome-neutral tests are pre-specified** — positive controls, quality
  checks, manipulation checks, absence of floor and ceiling effects — to ensure the data
  *can* test the hypotheses;
- the authors have committed to a clear analysis plan and stopping rule;
- deviations must be declared; confirmatory and exploratory analyses are labelled
  separately.

The *in principle acceptance* mechanism is exactly crux's design promise: the verdict is
committed to before the data exist.
- https://www.nature.com/srep/journal-policies/registered-reports
- https://royalsocietypublishing.org/rsos/pages/registered-reports
- https://rr.peercommunityin.org/

### 3.4 The Registered Report **design table**

A table mapping each numbered question/hypothesis through to interpretation. Columns
(as used across PCI RR and journal templates):

| Question | Hypothesis | Sampling plan (power analysis) | Analysis plan | Rationale for deducibility | **Interpretation given different outcomes** | Theory that could be shown wrong |

The two rightmost columns are the anti-ambiguity machinery. crux's schema currently has
the left half. **The "interpretation given different outcomes" column is the single
highest-value addition** — it forces the researcher to pre-write the reading of the
messy patterns, not just the clean win.

Also from *Ten simple rules for writing a Registered Report* (PLOS Comp Bio 2022,
https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1010571):
- Rule 5: *Map from research question through to interpretation* — number each question
  (Q1, Q2…) and hypothesis (H1, H2…) and tag every analysis with the corresponding
  suffix, so every prediction is visibly tested and every analysis is visibly tied to a
  prediction. **This is a graph-completeness check crux can run deterministically:
  no orphan verifiables, no untested hypotheses.**
- Rule 6: *Specify what you'll do and what you won't do* — including the *order* of
  exclusion criteria, and explicit statements of analyses you will not run.
- Rule 9: keep confirmatory and exploratory results structurally distinct.

### 3.5 PREPARE (planning guidelines, animal research — but the structure generalizes)
Smith et al. (2018), *Lab Animals*:
https://journals.sagepub.com/doi/full/10.1177/0023677217724823 and
https://norecopa.no/PREPARE

Notable because it is explicitly a **planning** guideline, not a reporting one. Its
stated motivation: better reporting cannot improve work already done — quality has to be
designed in beforehand. Three areas: formulation of the study, dialogue between
scientists and the facility, and quality control of components.

### 3.6 The ML Reproducibility Checklist (Pineau et al., NeurIPS)
https://www.cs.mcgill.ca/~jpineau/ReproducibilityChecklist.pdf ;
report: https://arxiv.org/abs/2003.12206 (JMLR 22:164)

For all reported results: mathematical setting/algorithm/model described; source code
and dependencies; computing infrastructure; average runtime or energy cost; number of
parameters; validation performance corresponding to each reported test result; a clear
definition of the evaluation measure.

For results involving multiple experiments: **the exact number of training and
evaluation runs**; the bounds for each hyperparameter; the hyperparameter configurations
for best-performing models; **the range of hyperparameters considered and the method
used to select the best ones**.

Note what these are: nearly all are *presence-of-a-declared-value* checks — exactly the
class crux can enforce deterministically.

---

## 4. Domain-general vs domain-specific

This is the section that matters most for crux's positioning. The finding is
encouraging: **the decisiveness-critical layer is almost entirely domain-general; what
is domain-specific is the *implementation*, not the *principle*.**

### 4.1 Fully domain-general (same principle, different clothes)

| Principle | Wet lab | ML ablation | Field trial | A/B test |
|---|---|---|---|---|
| **Comparison against a control** | vehicle / untreated | baseline model, ablated variant | untreated plots | control bucket |
| **Negative control** | no-template control | random/shuffled baseline, random retrieval | buffer plots | **A/A test** |
| **Positive control (assay sensitivity)** | known-active compound | known-good method reproduces published number | reference cultivar | known-win experiment replays |
| **Randomization** | randomize cage/bench order | randomize seeds, data order, GPU assignment | randomize plot assignment | hash-based user bucketing |
| **Replication** | biological replicates | **multiple seeds** | plots/blocks | sample size |
| **Blocking** | batch, day, litter | dataset, task, hardware | field, soil type | platform, country, day-of-week |
| **Blinding** | blinded scoring | held-out test set untouched until the end | blinded assessors | pre-registered metric |
| **Power / n** | animals per group | seeds × tasks | plots | users × duration |
| **Pre-declared primary endpoint** | primary readout | the headline metric | yield | the OEC |
| **Stopping rule** | fixed n | fixed compute budget | fixed season | fixed duration, no peeking |
| **Effect size / SESOI** | fold-change threshold | points of accuracy worth caring about | bushels/acre | % lift worth shipping |
| **Multiplicity control** | Bonferroni/FDR across readouts | across benchmarks/tasks | across traits | across metrics and segments |

Also fully general:
- Severity / risky prediction (Mayo, Meehl, Popper).
- Strong inference: name rival hypotheses; design to exclude (Platt).
- Interpretation of every outcome pattern pre-written.
- Ceiling/floor effects — general, because *any* bounded measure saturates: accuracy at
  99.8% on a saturated benchmark is the ML ceiling effect, and it is the same pathology
  as a questionnaire everyone maxes out.
- Simpson's paradox — arises whenever results are aggregated over heterogeneous units.
- Measurement validity — does the measure capture the construct? Universal question.

### 4.2 Genuinely domain-specific

- **Ethics / regulatory gates**: IRB, IACUC, informed consent, 3Rs, ICH/GCP. Only apply
  to human/animal work.
- **Blinding of participants** is impossible in ML and most simulation; *analyst*
  blinding is the general residue.
- **Specific nuisance factors and thus the blocking structure**: batch effects, plate
  edge effects, soil gradients, day-of-week, GPU non-determinism. The *existence* of
  nuisance factors is general; the *list* is domain knowledge.
- **Which statistical model is appropriate** (survival analysis, mixed effects,
  sequential testing, CUPED variance reduction).
- **Instrument validation procedures** (assay QC, calibration, SRM checks,
  instrumentation logging).
- **Unit of randomization** — patient, plot, user, session, cluster — and the
  corresponding independence assumption. General principle ("the unit of analysis must
  match the unit of randomization"), domain-specific answer.
- **Carryover/contamination mechanisms**: washout periods, spillover between plots,
  network interference between users, train-test leakage. Same abstract problem, wildly
  different remedies.

### 4.3 Implication for a domain-agnostic tool

crux can safely enforce a domain-general *skeleton* and delegate the domain-specific
*content* to the researcher or a model:

> Every hypothesis must declare: a comparison (against what?), a measurement (of what,
> with what instrument?), a sample size and its justification, a stopping rule, a
> primary verifiable, an outcome-neutral verifiable (something that must hold if the
> experiment worked at all), and a pre-written interpretation for each pass/fail
> pattern.

Every one of those slots exists in a wet lab, an ablation, a field trial, and an A/B
test. What goes *in* the slot is domain knowledge.

---

## 5. Deterministic software checks vs judgment

The key insight: most rigor guidelines are **presence-of-declaration** checks, not
**quality-of-declaration** checks. Presence is machine-checkable. This is why the ML
Reproducibility Checklist worked as a submission form — over 75% of NeurIPS submissions
included reproducibility materials after it was made mandatory (Pineau et al., JMLR
2021). A dumb structural check moved real behaviour.

Precedent for tooling: the `preregr` R package produces preregistrations as
human-readable HTML with embedded machine-readable JSON, precisely so registrations can
be harvested and validated programmatically
(https://r-packages.gitlab.io/preregr/articles/specifying_prereg_content.html).

### 5.1 Deterministic — a parser/linter can decide, no model needed

Structural / presence:
1. A **comparison/control arm** is declared (a named baseline or control condition
   exists in the design).
2. A **negative control** is declared, distinguishable from the treatment arm.
3. A **positive control or outcome-neutral check** is declared and flagged as such.
4. **n / sample size / number of runs / number of seeds** is stated as a number.
5. A **power justification or SESOI** field is non-empty.
6. The **measurement/instrument** is named (a string that names the measure).
7. A **stopping rule** is stated, and it is not "until the result is clear".
8. A **primary verifiable** is designated (exactly one, or an explicit co-primary set).
9. Every verifiable is **typed**: primary / secondary / exploratory / outcome-neutral.
10. A **combination rule** over verifiables exists (AND / hierarchy / single-primary /
    composite) — so the verdict is a total function of the pass/fail vector.
11. **Verdict coverage**: for a hypothesis with k verifiables, is every reachable
    pass/fail pattern mapped to a verdict? This is a finite enumeration — completely
    decidable. **This is the direct fix for the crux failure mode.**
12. **Count of endpoints vs multiplicity control**: if #verifiables > 1 and no
    correction/hierarchy is declared → flag.
13. **Randomization declared** (yes/no + unit).
14. **Blinding declared** (yes/no/N-A + who).
15. **Exclusion criteria** stated before the run, with an ordering.
16. **Subgroups pre-specified** if any subgroup analysis is planned (Simpson's paradox
    guard).
17. **Measurement window / duration** stated (novelty/primacy guard).
18. **Tuning/compute budget** stated symmetrically for all arms (ML guard).
19. **Graph completeness** (Registered Report Rule 5): every hypothesis has ≥1
    verifiable; every verifiable belongs to exactly one hypothesis; no orphans.
20. **Timestamp / immutability**: verifiables were written before the run — crux can
    literally prove this with content hashes and commit times. *This is a check no
    journal can perform and crux can.*
21. **Post-run drift**: were verifiables edited after the first result was recorded?
    Diffable, therefore decidable.
22. **Post-run arithmetic checks**: sample ratio mismatch (observed vs declared split),
    n actually collected vs n declared, number of runs vs number declared.

Note that 11, 20, 21 are the ones that are *natively* crux's — they need the tool's
data model, and no checklist-on-paper can enforce them.

### 5.2 Needs a model/LLM (soft, but automatable with reasonable reliability)

- Is the hypothesis **falsifiable** and **directional/quantitative** rather than vague?
  (Wicherts T2)
- Is the declared prediction **risky** — i.e. would a plausible rival hypothesis predict
  the same outcome? (Platt/Meehl — the discriminating-power check.)
- Does the named measurement **plausibly capture the construct** in the hypothesis?
- Is the declared control an **appropriate** control (does it isolate the intended
  factor)?
- Are there **obvious confounds** given the described procedure?
- Is the stated **interpretation of each outcome pattern** coherent and non-vacuous
  (vs. "if it fails we'll investigate further")?
- Is the SESOI **justified** rather than merely stated?
- Ceiling/floor risk given the described measure and expected baseline.

### 5.3 Irreducibly human

- Whether the question is worth asking; resource allocation.
- Domain-specific nuisance factors that nobody wrote down.
- Whether the effect size threshold matches real-world decision relevance.
- Whether an instrument is validated in *this* lab, on *this* material.
- Ethics.
- Whether an anomalous result is a bug or a discovery (Twyman's law adjudication).

---

## 6. Concrete recommendations for crux

Ordered by expected impact on the stated failure mode.

1. **Type every verifiable.** Minimum enum:
   `primary | secondary | exploratory | outcome-neutral`.
   Outcome-neutral failures should produce a verdict of **INVALID / inconclusive-run**,
   never "hypothesis refuted". This single change removes the largest class of
   ambiguous partial results, because it separates "the world said no" from "the
   apparatus said nothing".

2. **Require a declared verdict rule** and make the verdict a *total function* of the
   pass/fail vector. Offer the four standard shapes (all-must-pass / hierarchy /
   single-primary / composite). Refuse to accept a hypothesis whose verifiable set has
   no rule. `crux validate` should enumerate all 2^k patterns and report any pattern
   with no mapped verdict.

3. **Add an "interpretation given different outcomes" field** to the hypothesis,
   borrowed verbatim from the Registered Report design table. At minimum require a
   pre-written reading for: all-pass, all-fail, and primary-pass-with-secondary-fail.

4. **Require at least one outcome-neutral verifiable per hypothesis** (a positive
   control / sanity check / manipulation check). Justify the requirement with assay
   sensitivity: without it a null is uninformative. Allow an explicit opt-out with a
   written reason — the reason itself is the audit trail.

5. **Require a declared SESOI and a stopping rule.** These are one-line fields and they
   kill optional stopping and the uninformative null in a single stroke.

6. **Multiplicity flag**: if a hypothesis has >1 non-outcome-neutral verifiable and no
   correction or hierarchy, warn. This is literally the crux failure mode as a lint
   rule.

7. **Exploit crux's structural advantage**: verifiables are content-addressed and
   timestamped, so crux can *prove* pre-registration and *detect* post-hoc edits.
   Surface a "drift" indicator on any hypothesis whose verifiables changed after the
   first finding was recorded. No paper checklist can do this.

8. **Domain-agnostic slot, domain-specific fill.** Keep the schema at the level of
   "comparison / measurement / n / stopping rule / primary / outcome-neutral /
   interpretation table". Let the agent fill each slot with domain-appropriate content
   and let a model-based review flag confounds, ceiling risk, and rival-hypothesis
   overlap.

---

## 7. Source list

**DoE foundations**
- Fisher, R.A., *The Design of Experiments* (1935) — randomization, replication, the
  null hypothesis, the lady tasting tea.
- Box, Hunter & Hunter, *Statistics for Experimenters* (2nd ed., 2005).
- Montgomery, D.C., *Design and Analysis of Experiments* (10th ed.).
  Course notes: https://alysongwilson.github.io/ACAS/ACAS10/acasdesigncourse.pdf
- JMP statistics knowledge portal, key principles:
  https://www.jmp.com/en/statistics-knowledge-portal/design-of-experiments/key-design-of-experiments-concepts/key-principles-of-experimental-design
- Minitab pre-experiment checklist:
  https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/basics/checklist-of-pre-experiment-activities/
- Which designs are actually usable in practice (CR and RB only):
  https://www.nature.com/articles/s41598-020-74538-3

**Philosophy of decisive evidence**
- Platt, J.R., *Strong Inference*, Science (1964); 50-year retrospective:
  https://journals.biologists.com/jeb/article/217/8/1202/13095/Fifty-years-of-J-R-Platt-s-strong-inference
- Strong inference applied to systems biology:
  https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000459
- Mayo, D., *Statistical Inference as Severe Testing* (2018), review:
  https://ndpr.nd.edu/reviews/statistical-inference-as-severe-testing-how-to-get-beyond-the-statistics-wars/
  Notes on severity: https://philsci-archive.pitt.edu/1782/1/severity.notes.html
- Meehl, P., *Appraising and Amending Theories*:
  https://meehl.umn.edu/sites/meehl.umn.edu/files/files/147appraisingamending.pdf
- Wikipedia overview: https://en.wikipedia.org/wiki/Strong_inference

**Power, effect size, informative nulls**
- Gelman & Carlin, *Beyond Power Calculations: Assessing Type S and Type M Errors*
  (2014): https://journals.sagepub.com/doi/10.1177/1745691614551642
- Lakens, Scheel & Isager, *Equivalence Testing for Psychological Research: A Tutorial*
  (2018): https://journals.sagepub.com/doi/10.1177/2515245918770963
- Lakens, *Improving Your Statistical Inferences*, ch. 9 (equivalence testing):
  https://lakens.github.io/statistical_inferences/09-equivalencetest.html
- Riesthuis (2024), simulation-based power for SESOI:
  https://journals.sagepub.com/doi/10.1177/25152459241240722

**Preregistration and researcher degrees of freedom**
- Wicherts et al. (2016), 34-item checklist:
  https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2016.01832/full
- Simmons, Nelson & Simonsohn (2011), *False-Positive Psychology*.
- APS, *Research Preregistration 101*:
  https://www.psychologicalscience.org/observer/research-preregistration-101
- `preregr` machine-readable preregistrations:
  https://r-packages.gitlab.io/preregr/articles/specifying_prereg_content.html

**Registered Reports (outcome-neutral tests, design tables)**
- *Ten simple rules for writing a Registered Report*, PLOS Comp Bio (2022):
  https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1010571
- Scientific Reports RR policy:
  https://www.nature.com/srep/journal-policies/registered-reports
- Royal Society Open Science RR:
  https://royalsocietypublishing.org/rsos/pages/registered-reports
- PCI Registered Reports: https://rr.peercommunityin.org/
- Wikipedia: https://en.wikipedia.org/wiki/Registered_report

**Controls and assay sensitivity**
- ICH E10, *Choice of Control Group and Related Issues in Clinical Trials*:
  https://www.gmp-compliance.org/guidelines/gmp-guideline/ich-e10-choice-of-control-group-and-related-issues-in-clinical-trials
- Assay sensitivity: https://en.wikipedia.org/wiki/Assay_sensitivity

**Multiplicity / partial results**
- FDA, *Multiple Endpoints in Clinical Trials* (final, 2022):
  https://www.fda.gov/media/162416/download
- Federal Register notice:
  https://www.federalregister.gov/documents/2022/10/21/2022-22882/multiple-endpoints-in-clinical-trials-guidance-for-industry-availability

**Planning guidelines**
- Smith et al., *PREPARE: guidelines for planning animal research and testing*, Lab
  Animals (2018): https://journals.sagepub.com/doi/full/10.1177/0023677217724823
  and https://norecopa.no/PREPARE
- Stafford's experiment design checklist: https://tomstafford.github.io/psy-checklist/

**A/B testing**
- Kohavi, Tang & Xu, *Trustworthy Online Controlled Experiments* (CUP, 2020);
  ch.1 free: https://experimentguide.com/wp-content/uploads/TrustworthyOnlineControlledExperiments_PracticalGuideToABTesting_Chapter1.pdf
- Kohavi, pitfalls deck:
  https://exp-platform.com/Documents/2017-05-17EmetricsControlledExperimentsPitfallsKohaviNR.pdf
- Automated SRM detection and randomization validation:
  https://arxiv.org/pdf/2208.07766

**ML / computational**
- Pineau et al., *Improving Reproducibility in Machine Learning Research*, JMLR 22:164
  (2021): https://arxiv.org/abs/2003.12206
- ML Reproducibility Checklist v2.0:
  https://www.cs.mcgill.ca/~jpineau/ReproducibilityChecklist.pdf
- Henderson et al., *Deep Reinforcement Learning That Matters* (2017):
  https://arxiv.org/pdf/1709.06560
- Hyperparameter/seed confounds in RL:
  https://arxiv.org/html/2406.17523v3
- REFORMS, consensus recommendations for ML-based science:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11092361/

**Failure modes**
- Ceiling effect: https://en.wikipedia.org/wiki/Ceiling_effect_(statistics)
- Robustness under ceiling/floor:
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0220889
- Kievit et al., Simpson's paradox practical guide:
  https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00513/full
- SEP, Simpson's paradox: https://plato.stanford.edu/entries/paradox-simpson/
