# Formal machinery against ambiguous / post-hoc-rationalized results

Research brief for crux design (pre-registered "verifiables" → deterministic verdict).
Compiled 2026-08-13. All claims sourced; URLs inline.

---

## 0. The one-paragraph answer

Two different fields solved two different halves of the problem, and they did **not**
converge on the same machinery.

- **Clinical trials** solved *"which check decides?"* They designate a **primary
  endpoint family** and a **pre-specified testing order**. The verdict is a function
  of a distinguished subset of checks. Everything else is descriptive. Mixed results
  are not *interpreted* — they are made *impossible to be ambiguous* by fixing the
  decision rule in advance.
- **Registered Reports** solved *"what does each outcome mean?"* They require a
  mandatory **Design Table** whose last column is literally
  `Interpretation given to different outcomes`, filled in before data collection.

Crucially, **neither field enumerates the power set of check outcomes.** Trials write a
*rule* over patterns (`all` / `any` / `m-of-n` / `ordered-until-first-failure`).
Registered Reports write interpretations *per hypothesis row*, not per combination.
Enumerating combinations is nowhere considered practical, and where people tried
(economics pre-analysis plans), it is the documented failure mode.

---

## 1. Clinical trial endpoint design

### 1.1 The rule: generally one primary variable

ICH E9 §2.2.2 (*Primary and Secondary Variables*), verbatim:

> "The primary variable ('target' variable, primary endpoint) should be the variable
> capable of providing the most clinically relevant and convincing evidence directly
> related to the primary objective of the trial. **There should generally be only one
> primary variable.**"

and

> "The primary variable should generally be the one used when estimating the sample
> size."

Source: [ICH E9, Statistical Principles for Clinical Trials (1998)](https://database.ich.org/sites/default/files/E9_Guideline.pdf), p. 5.

FDA's 2022 final guidance states the mechanism plainly:

> "When there is a single prespecified primary endpoint, there are no
> multiple-endpoint-related multiplicity issues in the determination that the study
> achieves its objective."

Source: [FDA, *Multiple Endpoints in Clinical Trials* (final, Oct 2022)](https://www.fda.gov/media/162416/download), §III.A.1, p. 7.

### 1.2 WHY exactly one — the problem it solves

**Type I error inflation.** FDA §II.C quantifies it: with a single endpoint at
two-sided α = 0.05, there is a 97.5% chance of correctly *not* finding a favourable
effect when none exists. With two independent endpoints where either one alone would
declare success, that drops to ≈0.95 — "the overall Type I error rate in favor of the
drug **nearly doubles**." Three independent endpoints → ≈7%. **Ten independent
endpoints → ≈22%.**

The deeper point (from the Giens round-table paper, below):

> "even under the (null) hypothesis that the treatment has no effect on any of the
> endpoints, if enough tests are conducted, it is possible to find one that makes it
> possible to erroneously conclude that there is a treatment benefit. To avoid this
> inflation … the conventional solution is to make the decision based on one single
> test, by predefining a primary endpoint, **which should be the sole basis of the
> decision-making process**. After analysis of the trial, it would therefore be
> impossible to select false positive results obtained by chance as proof of a
> treatment benefit."

Source: Laporte et al., [*What usage and what hierarchical order for secondary endpoints?*](https://arxiv.org/pdf/2409.14770) (Giens round table 2), pp. 3–4.

That last sentence is the crux-relevant one. **The primary endpoint is not primarily a
statistical device — it is an anti-cherry-picking device.** It removes the *degrees of
freedom at verdict time*, not just the alpha.

### 1.3 The three-tier hierarchy and what each tier may claim

FDA §III.A:

| Tier | Role | Multiplicity treatment | Can it support a claim? |
|---|---|---|---|
| **Primary family** | "establish the effect(s) of the drug and will be the basis for concluding that the study meets its objective" | Strict α control | Yes — approval |
| **Secondary family** | "provide useful description to support the primary endpoint(s) and/or demonstrate additional clinically important effects" | Must be in the Type I error control plan; **only testable after primary success** | Yes, but only conditionally |
| **Exploratory** | "endpoints for research purposes or for new hypotheses generation" | "do not need multiplicity adjustment **because they are generally not used to support conclusions**" | No |

FDA is explicit on the gating:

> "Positive results on the secondary endpoints can be interpretable **if there is first
> a demonstration of a treatment effect on the primary endpoint family**."

ICH E9 §2.2.2 on secondaries: "The number of secondary variables should be limited and
should be related to the limited number of questions to be answered in the trial."

### 1.4 Co-primary endpoints: what happens when you require ALL

Co-primary = success requires demonstrating an effect on **every** listed endpoint
(intersection–union test). The trade is exact and well characterised:

- **No Type I inflation.** FDA §III.A.1: "there are no multiplicity issues related to
  primary endpoints, as there is **only one path that leads to a successful outcome**
  for the trial."
- **Type II error explodes.** FDA §III.B: two independent endpoints each powered at 80%
  → joint power ≈ **64%**, i.e. a 36% chance of missing a real effect. To keep 80%
  overall you must power each at ~90%.
- **You may not buy the power back with alpha.** FDA §III.C.1, verbatim:

  > "There have been suggestions that the statistical testing criteria for each
  > co-primary endpoint could be increased (e.g., testing at an α of 0.06 or 0.07) …
  > **Increasing α for each co-primary endpoint is not acceptable** because doing so may
  > undermine the ability to interpret a treatment effect on each disease aspect
  > considered critical."

- **Ceiling on count.** FDA: "unless clinically very important, the use of **more than
  two co-primary endpoints should be carefully considered because of the loss of
  power**."

Concrete cost. A review of co-primary designs
([Sozu et al. / Hamasaki et al., PMC6135538](https://pmc.ncbi.nlm.nih.gov/articles/PMC6135538/)):
for two endpoints at standardized effect 0.2 with **zero** correlation, a fixed design
needs **516/group**; with near-perfect correlation (ρ=0.99), **409/group**. The
Tarenflurbil Alzheimer's trial was sized at **1,600 participants** to satisfy two
co-primaries (cognition + function). Correlation between endpoints is usually unknown
and unreported, so planners routinely under-size.

**Takeaway for crux: requiring ALL checks to pass is the safest rule against false
positives and the most expensive rule against false negatives.** It converts every
weak check into a veto.

### 1.5 Rules on changing endpoints after the fact

This is the strictest machinery in the whole review.

**ICH E9 §2.2.2:**
> "**Redefinition of the primary variable after unblinding will almost always be
> unacceptable**, since the biases this introduces are difficult to assess."

**ICH E9 §5.1 (Prespecification of the Analysis):**
> "The plan … should be reviewed and possibly updated as a result of the blind review of
> the data and **should be finalised before breaking the blind**. Formal records should
> be kept of when the statistical analysis plan was finalised as well as when the blind
> was subsequently broken. … **Only results from analyses envisaged in the protocol
> (including amendments) can be regarded as confirmatory.**"

**FDA (Multiple Endpoints), §II.C:**
> "**The statistical analysis plan should not be changed after unmasking of treatment
> assignments and performing statistical analyses.**"

**When change IS legitimate** (Evans, *When and How Can Endpoints Be Changed after
Initiation of a Randomized Clinical Trial?*,
[PMC1852589](https://pmc.ncbi.nlm.nih.gov/articles/PMC1852589/)):
- The decision must be **independent of the trial's own data** — driven by external
  results, better biomarkers, evolving medical knowledge, or changed regulation.
- Decision-makers must not have seen interim data; the paper recommends an *external*
  advisory committee, explicitly **not** the DMC that reviewed interim results.
- Must be formalised: protocol amendment + updated SAP + registry update.
- Publications must state the change, the reason, the decision procedure, and the
  potential bias.

**How often it is violated.** Outcome switching is endemic:
- 130/389 trials (33%) changed at least one primary outcome between registration and
  publication; those changes **overestimated effect size by 16%** relative to trials
  without a change — [JAMA Netw Open / PMC6646984](https://pmc.ncbi.nlm.nih.gov/articles/PMC6646984/).
- 31.7% (28,229/89,204) of registered studies had a primary-outcome change —
  [PMC4032105](https://pmc.ncbi.nlm.nih.gov/articles/PMC4032105/).
- Protocol-vs-publication discrepancies of 62% (Danish cohort) and 40% (Canadian
  cohort) are cited in Evans (above).
- Ben Goldacre's **COMPare** project systematically audited and wrote correction letters
  for switched outcomes — [Wikipedia: Outcome switching](https://en.wikipedia.org/wiki/Outcome_switching).

**Design implication for crux: the ability to edit verifiables after seeing results is
the single most-abused affordance in the whole institutional apparatus.** Every field
that has this problem responds with *timestamping + amendment record + a hard rule that
only pre-registered analyses are confirmatory.*

---

## 2. Pre-registration and Registered Reports

### 2.1 What must be specified in advance

**AsPredicted** (8 questions, ~30 min): hypotheses; dependent/outcome variable(s); how
many observations; conditions/manipulations; the analysis; data exclusions; outlier
handling; anything else. Deliberately minimal — generates a timestamped document, held
private or public at the author's discretion.
[AsPredicted](https://aspredicted.org/) · [COS: choosing a template](https://www.cos.io/blog/choosing-preregistration-template-guide-for-researchers)

**OSF Preregistration template**: same fields but with sample-size *justification*,
detailed inference criteria, and explicit statements of exploratory vs confirmatory
scope.

**ClinicalTrials.gov (FDAAA 801 / Final Rule)**: registration within 21 days of first
enrolment; required data elements include primary and secondary **outcome measures each
with a time frame**; a **Primary Completion Date**; results due within 12 months of that
date. Registry records the full revision history, which is what makes outcome-switching
audits like COMPare possible at all.
[FDAAA issues](https://register.clinicaltrials.gov/prs/html/fdaaa-issues.html)

**Registered Reports Stage 1** adds two requirements that ordinary preregistration lacks:

1. **Outcome-neutral criteria / positive controls.** From the Nature Ecology & Evolution
   Stage 1 template: "Provide full descriptions of any **outcome-neutral criteria and
   positive controls**. These quality checks might include the absence of floor or
   ceiling effects in data distributions, positive controls, or other quality checks
   that are **orthogonal to the experimental hypotheses**." Manuscripts that fail to
   specify these generally do not get in-principle acceptance.
2. **A mandatory Design Table** — see §3.1 below.

Sources: [Nature Ecol Evol Stage 1 template](https://www.nature.com/documents/np-nee-template-stage1.pdf) ·
[Chambers & Tzavella, *The past, present and future of Registered Reports*, Nat Hum Behav 2022](https://www.nature.com/articles/s41562-021-01193-7)

### 2.2 Does it actually work?

**Yes, at the level of what gets published — dramatically.**

Scheel, Schijen & Lakens (2021), *An Excess of Positive Results*: comparing 71 published
Registered Reports with 152 hypothesis-testing studies from the standard psychology
literature:

> **96% positive results in the standard literature vs 44% in Registered Reports.**

Source: [AMPPS 2021, 10.1177/25152459211007467](https://journals.sagepub.com/doi/10.1177/25152459211007467)

Roughly 60% of hypotheses in RRs go unsupported, against an estimated 5–20% null-finding
rate in the conventional literature.
[Nature news coverage, 2018](https://www.nature.com/articles/d41586-018-07118-1)

**Ambiguous, at the level of ordinary (non-RR) preregistration.**

- *Preregistration in practice* (van den Akker et al., Psych Sci 2023): preregistered
  studies did **not** show a lower proportion of positive results, smaller effect sizes,
  or fewer statistical errors than non-preregistered studies. Hypotheses 1–3 all
  unsupported. [PubMed 37950113](https://pubmed.ncbi.nlm.nih.gov/37950113/)
- *Selective Hypothesis Reporting* (van den Akker et al., AMPPS 2023): of 2,119
  preregistered hypotheses, **46.1% were missing** from the paper's intro/methods and
  **46.6% of hypothesis results were missing** from the results section. Preregistration
  alone did not prevent selective reporting.
  [10.1177/25152459231187988](https://journals.sagepub.com/doi/10.1177/25152459231187988)

**The mechanism that works is the publication commitment (RR), not the document
(preregistration).** That is the sharpest empirical result in this whole area.

### 2.3 Documented failure modes of preregistration itself

1. **Vagueness / insufficient constraint.** Bakker et al., *Ensuring the quality and
   specificity of preregistrations* (PLOS Biology 2020): "Some preregistrations were so
   ambiguous that it was hard to make sense of the planned research." Inter-coder
   agreement on *how many hypotheses a preregistration contained* was **14%**. The
   structured (Prereg Challenge) format constrained researcher degrees of freedom better
   than the unstructured format, but **neither eliminated them**.
   [PLOS Biol 3000937](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3000937)

2. **Near-universal deviation, mostly undisclosed.** Claesen et al., *Comparing dream to
   reality* (R Soc Open Sci 2021): of 27 studies carrying the Preregistered badge in
   *Psychological Science*, **only 2 had no deviations**; **9 disclosed none of their
   deviations**; only 1 disclosed all. Mean 1.84 deviations per study, mostly on sample
   size, exclusions, and analysis. Notably the authors judge most deviations *not* to be
   questionable practice — they are normal research contact with reality.
   [PMC8548785](https://pmc.ncbi.nlm.nih.gov/articles/PMC8548785/)

3. **Deviations are not intrinsically bad — and treating them as violations is itself an
   error.** Lakens, *When and How to Deviate From a Preregistration* (Collabra 2024):
   deviations "can both reduce **and increase** the severity of a test, as well as
   increase the validity of inferences." He gives five legitimate triggers: unforeseen
   events, errors in the preregistration, missing information, violated untested
   assumptions, falsified auxiliary hypotheses.
   [Collabra 117094](https://online.ucpress.edu/collabra/article/10/1/117094/200749/When-and-How-to-Deviate-From-a-Preregistration) ·
   reporting templates in Willroth & Atherton, *Best Laid Plans* (AMPPS 2024),
   [10.1177/25152459231213802](https://journals.sagepub.com/doi/10.1177/25152459231213802)

4. **It doesn't fix the actual problem (theory).** Szollosi & Donkin and colleagues argue
   preregistration "is not scientifically useful either in tests of bad or in tests of
   good theories … because it focuses on the reduction of **superficial** flexibilities."
   The real source of unfalsifiability is flexible theory, not flexible analysis.
   [Szollosi & Donkin, Perspect Psychol Sci 2021](https://journals.sagepub.com/doi/full/10.1177/1745691620966796)

5. **Severity, not compliance, is the actual goal.** Mayo's error-statistical severity
   requirement is the best philosophical grounding for preregistration (Lakens 2019),
   but Rubin (2025) argues preregistration does not by itself improve transparent
   evaluation of severity, particularly once deviations are allowed.
   [Lakens, conceptual analysis](https://phil-stat-wars.com/wp-content/uploads/2022/09/lakens_the-value-of-registered-reports-for-psychological-science-a-conceptual-analysis2.pdf) ·
   [Rubin, arXiv 2408.12347](https://arxiv.org/pdf/2408.12347)

---

## 3. Pre-specified decision rules — does anyone enumerate outcome patterns?

**Short answer: yes, but as a *rule* or a *per-hypothesis row*, never as a full
combination table.**

### 3.1 Registered Reports: the Design Table (the closest thing to "pre-written readings")

The Nature Ecology & Evolution Stage 1 template makes a Design Table **mandatory**, with
**prescribed columns**:

| Question | Hypothesis | Sampling plan (e.g. power analysis) | Analysis Plan | **Interpretation given to different outcomes** |
|---|---|---|---|---|

Accompanying instructions, verbatim from the template:

> "The description of hypotheses **must commit to interpretation of all potential data
> patterns** (those that are predicted and those that would run counter to predictions).
> You cannot interpret lack of evidence (e.g. a p>0.05 in a t-test) for the existence of
> an effect in null hypothesis significance testing as evidence for the absence of an
> effect. To be able to interpret data patterns other than the predicted effect … you
> must commit to using Bayesian inferential methods or frequentist equivalence testing."

and

> "If your analysis strategy will depend on the results (e.g. normal vs. non-normal
> distribution) then specify the contingencies for making different choices, i.e.
> **IF-THEN statements**."

Source: [Nature Ecol Evol Stage 1 template](https://www.nature.com/documents/np-nee-template-stage1.pdf), Table 1.

**Two things matter here for crux:**
- One row per **research question / hypothesis**, not per combination of checks. The
  granularity of "pre-written interpretation" is *the hypothesis*, not *the outcome
  vector*.
- The requirement is enforced by making it a **reviewable artifact**. Reviewers use the
  table to verify every prediction is testable and every outcome interpretable. It is
  gate machinery, not documentation.

### 3.2 Clinical trials: rules over patterns, not enumerations

ICH E9 §2.2.5 (*Multiple Primary Variables*) — the single most directly relevant
sentence in the regulatory corpus:

> "The planned manner of interpretation of this type of evidence should be carefully
> spelled out. **It should be clear whether an impact on any of the variables, some
> minimum number of them, or all of them, would be considered necessary to achieve the
> trial objectives.**"

That is the whole design space, stated as three options: **any / m-of-n / all**. Not an
enumeration — a **quantifier**.

The **hierarchical (fixed-sequence) test procedure** is the fourth option: order the
endpoints in the protocol; test in order; **stop at the first non-significant test**.
Everything below the stop is descriptive only.

> "an effect will be considered to have been demonstrated for all endpoints obtaining a
> p < 0.05 **until the first endpoint for which p > 0.05** in the order of the
> hierarchy."
> — Laporte et al. §5

This is a **prefix rule**: the verdict is `length of the leading run of passes`. It is
deterministic, needs no combination table, and is the only method that lets one trial
claim several distinct benefits without alpha inflation.

FDA endorses the family: Bonferroni / Holm / Hochberg (unordered), fixed-sequence,
graphical methods (Bretz et al. 2009), mixture gatekeeping (Dmitrienko et al. 2008).

### 3.3 Bayesian designs: three-valued verdicts

**BOP2-DC** (Zhao et al., *Pharm Stat* 2023) is the cleanest existing model of a
non-binary pre-specified verdict. Two posterior-probability thresholds — one against a
*lower reference value* (statistical significance), one against a *clinically meaningful
value* — yield **three mutually exclusive, pre-specified decisions**:

- **Go** — both thresholds exceeded
- **No-go** — both missed
- **Consider** — otherwise (i.e., statistically but not clinically significant, or vice
  versa) → "further investigation considering totality of evidence"

Sources: [Pharm Stat 10.1002/pst.2296](https://onlinelibrary.wiley.com/doi/10.1002/pst.2296) ·
[arXiv 2112.10880](https://arxiv.org/pdf/2112.10880)

**This is the strongest precedent for a tool wanting a principled "mixed" verdict:
"mixed" is a legitimate *pre-declared* third state, not a failure to decide.** The
important property is that the boundary is set *before* seeing data, and "consider"
carries a defined next action (more evidence), not a rhetorical escape hatch.

### 3.4 Is exhaustive enumeration considered practical? No.

Economics is where people actually tried to write exhaustive pre-analysis plans, and it
is where the cost is documented.

- Olken, *Promises and Perils of Pre-Analysis Plans* (JEP 29(3), 2015) — the canonical
  cost/benefit treatment. PAPs must pre-specify variables, cleaning, specifications,
  functional form, estimator, fixed effects, standard-error treatment. The perils:
  enormous authoring cost, mechanical reporting, and suppression of legitimate
  exploration. [AEA](https://www.aeaweb.org/articles?id=10.1257/jep.29.3.61)
- Ofosu & Posner, *Pre-Analysis Plans: An Early Stocktaking* (*Perspectives on Politics*,
  2021): 195 PAPs from AEA and EGAP registries, plus 93 with resulting papers. Finding:
  **significant variation in the extent to which PAPs accomplish their goals**; the
  community championed PAPs "without any evidence that PAPs actually bolster the
  credibility of research"; adherence to registered specifications varies widely.
  [Cambridge Core](https://www.cambridge.org/core/journals/perspectives-on-politics/article/preanalysis-plans-an-early-stocktaking/94E7FAE76001C45A04E8F5E272C773CE)

**No framework anywhere in this literature requires enumerating what every
*combination* of outcomes would mean.** The consensus tools are quantifiers (`all`,
`any`, `m-of-n`), orderings (hierarchy), and per-hypothesis interpretation rows.

---

## 4. How fields actually handle genuinely mixed results

### 4.1 The dominant answer really is "you should have designed it so this can't happen"

The hierarchical procedure makes "3 of 5 hit" undefined by construction: the verdict is
the leading run, full stop.

> "No conclusions can be drawn before the 1st non-conclusive test (p < 0.05), even with a
> p value < 0.05, because it would constitute a fishing approach…"
> "After the 1st non-significant test, results **can only be descriptive**."
> — Laporte et al., §4 and Recommendation 6.3

### 4.2 The canonical cautionary tale: PLATO

PLATO (ticagrelor vs clopidogrel, n=18,624) pre-specified a 10-step hierarchy. Results
in order: 1 (primary) ✓, 2 ✓, 3 ✓, 4 ✓, 5 ✓, **6 stroke p = 0.22 ✗ — STOP**, 7
all-cause mortality p<0.001, 8 p=0.045, 9 p<0.001, 10 p<0.01.

Per the pre-specified rule, endpoints 7–10 are descriptive only. **They were published
and highlighted anyway — particularly total mortality — "even when the risk of erroneous
conclusion was no longer controlled."** The round table treats PLATO as the reason the
topic needed a round table at all.

Source: Laporte et al., [arXiv 2409.14770](https://arxiv.org/pdf/2409.14770), pp. 8–9.

**This is precisely the crux failure mode, observed in the wild in a 18,624-patient
trial: a deterministic rule existed, produced a stop, and the humans narrated past it.**
The lesson is not "write a better rule" — it is that the rule must be **enforced at
report-render time**, not left to author discipline.

### 4.3 Where "m-of-n" IS legitimate: bake it into the check definition

The field's actual answer to "3 of 5 endpoints hit" is: **make 3-of-5 the definition of
a single endpoint, decided before the trial.**

FDA §III.C.4 (Multi-Component Endpoints):

> "a positive response for an individual subject might be defined as a certain degree of
> improvement in two specific aspects of a disease along with improvement in **at least
> three out of five** additional disease features, as in the American College of
> Rheumatology (ACR) scoring system for rheumatoid arthritis."

**ACR20**, the standard RA endpoint, is exactly this: ≥20% improvement in *both* tender
and swollen joint counts **AND** ≥20% improvement in **≥3 of 5** of {patient pain,
patient global, physician global, HAQ-DI function, CRP}.
[ACR response criteria](https://www.quanticate.com/blog/acr-response-criteria)

FDA's caveat: multi-component endpoints are efficient only "if the treatment effects on
the different components are generally trending in the same direction within a subject.
Study power can be adversely affected … if there is **limited concordance** among the
endpoints."

**So: `m-of-n` is fully legitimate machinery — but it must be declared as the rule, at
design time, with `m` and `n` fixed. It is never a post-hoc reading of a tally.**

### 4.4 Composite endpoints, and what they hide

Composite endpoints (e.g. CV death + MI + stroke) avoid multiplicity by definition — one
variable, one test. ICH E9 §2.2.3 endorses them with a pre-defined combining algorithm.

But the known pathology is exactly "mixed results, hidden":

> "**more than one third of published trials using a primary composite outcome with a
> mortality component showed an overall significant result, although the single mortality
> endpoint did not.** A positive composite endpoint may camouflage a negative individual
> outcome or dilute the effect of the treatment on mortality."
> — [Re-Thinking Composite Endpoints, PMC4275445](https://pmc.ncbi.nlm.nih.gov/articles/PMC4275445/)

FDA §III.C.3 concedes it directly: the composite "will not be a reasonable indicator of
the effect on all of the components … if the clinical importance of different components
is substantially different and the treatment effect is chiefly on the least important
event," and a more important component may even be *harmed*. Hence: "**The examination
of the components is always necessary.**"

**Design implication: a rolled-up verdict must never be the only thing surfaced. FDA
requires component-level reporting alongside the composite verdict, always.**

### 4.5 Modern alternatives that grade rather than dichotomize

**Hierarchical composite endpoints / win ratio / DOOR (Desirability of Outcome
Ranking).** Rank component outcomes by clinical importance, compare patients pairwise
through the ordered hierarchy, and report a win ratio or "better DOOR probability."
Gives a graded, pre-specified, mixed-outcome-tolerant estimand instead of a binary
hit/miss. Used in cardiology, critical care, infectious disease, epilepsy.

Sources: [Win ratio in critical care trials, AJRCCM](https://www.atsjournals.org/doi/full/10.1164/rccm.202309-1644CP) ·
[Analysis of ordered composite endpoints, PMC9709888](https://pmc.ncbi.nlm.nih.gov/articles/PMC9709888/) ·
[DOOR & win ratio for HCEs, Clin Infect Dis 2026](https://academic.oup.com/cid/advance-article-abstract/doi/10.1093/cid/ciaf719/8415989)

### 4.6 "Totality of evidence" — the honest escape hatch

Regulators do reserve judgment beyond the hypothesis tests. FDA §III.A: "There are also
other important factors (e.g., clinical relevance of the endpoint and estimated effect,
relevant external information) that are considered in evaluating substantial evidence of
effectiveness **beyond the results of hypothesis tests in a single trial**." But this
operates at the *program* level (multiple trials), explicitly **not** as a way to rescue
a failed primary endpoint within one trial.

---

## 5. Criticism of the primary-endpoint approach

### 5.1 It assumes one number can carry the claim

> "Although this paradigm allows for the simple control of type I error risk and
> facilitated interpretation of trial results, **it has limitations. In particular, it
> supposes that a single variable is enough to demonstrate a pertinent treatment
> effect. However, it is often too simplistic to summarise the potential benefit of a
> treatment in a single endpoint.**"
> — Laporte et al., §3

Examples where the field concedes one endpoint is not enough: COPD (EMA requires lung
function *and* symptomatic benefit), oncology (OS *and* PFS), Alzheimer's (cognition
*and* function — hence the co-primary mandate).

### 5.2 It wastes collected data and real effects

- Everything outside the primary family is, formally, **inadmissible**. Under a strict
  hierarchy, the informative-but-later endpoints "**might never get tested**" — FDA's own
  words (§III.A.2), listed as a reason to *limit* the number of secondaries.
- Correspondingly, effects that exist but sit on a secondary endpoint cannot be claimed.
  The Giens paper's motivating case: an anticoagulant that met non-inferiority on the
  primary *and* showed a real reduction in major bleeding — and the question of whether
  that second finding may be claimed at all is what the round table exists to answer.
- The general argument: "Incorporating data from multiple endpoints could provide a more
  complete understanding of intervention effects and increase statistical power … could
  potentially avert wasted research effort."
  [PMC9934779](https://pmc.ncbi.nlm.nih.gov/articles/PMC9934779/)

### 5.3 The hierarchy's ordering is a strategic gamble, and getting it wrong destroys evidence

PLATO again: stroke was placed 6th. Stroke combines ischaemic (efficacy) and haemorrhagic
(safety) events, so for an antithrombotic "the chances of obtaining a significant test
result for an endpoint combining efficacy and safety are **virtually nil**," and its
incidence was the lowest of all endpoints, so its power was worst from the outset. One
bad ordering choice detonated four downstream significant findings.

The round table's own guidance is telling: put **frequent** events early and rare-but-more-
important events late, and calculate the required N for *each* rung. Also: "**Ultimately,
the order of the hierarchy is not overly important**" — an admission that the ordering is
partly arbitrary yet fully determines what may be claimed.

### 5.4 Dichotomisation costs power

ICH E9 §2.2.7: "Because categorisation normally implies a loss of information, a
consequence will be a **loss of power** in the analysis; this should be accounted for in
the sample size calculation." Any pass/fail check inherits this.

### 5.5 Structural critique: one primary endpoint, one trial

Cardiologist James Brophy, on the FDA guidance: historically two independent RCTs were
required; now often one. He argues the single-trial standard is "**as much of a concern,
if not more**" for false positives than the multiplicity problem the guidance addresses.
[TCTMD](https://www.tctmd.com/news/more-endpoints-more-problems-fda-offers-advice-multi-endpoint-trials)

Relevance to crux: **a deterministic verdict from one hypothesis's checks is a
single-trial verdict.** Replication across hypotheses/questions is a different and
arguably stronger guarantee than tightening the rule within one.

---

## 6. Synthesis: what this implies for a "verifiables → verdict" tool

### 6.1 What the evidence supports

| Design question | What the fields did | Strength of evidence |
|---|---|---|
| Must one check be designated decisive? | Trials: **yes**, and it's the field's central anti-cherry-picking device. But it is a *decision rule*, of which "single primary" is only one option. | Strong, but note ICH E9 offers **any / m-of-n / all / ordered** as equally legitimate rules |
| Must interpretations be pre-written per outcome pattern? | RRs: **yes, per hypothesis row**, in a mandatory reviewable table. Nobody enumerates combinations. | Strong for per-hypothesis; **zero** support for combinatorial enumeration |
| Is a three-valued verdict legitimate? | Bayesian dual-criterion designs: **yes** — go / consider / no-go, thresholds fixed in advance. | Established in phase II oncology |
| Should post-hoc edits be blocked? | Universally **yes**: finalize before unblinding, timestamp, amend-with-record, only pre-registered analyses are confirmatory. | Strongest consensus in the entire review |
| Does a document alone fix ambiguity? | **No.** RRs (publication commitment) work; bare preregistration largely doesn't. | Strong — this is the key negative result |

### 6.2 The three rules a tool can offer, with their exact costs

1. **ALL must pass** (co-primary / intersection–union). No false-positive inflation, one
   path to success, but joint power = product of individual powers (80%×80% = 64%), and
   you may **not** compensate by loosening thresholds. Every weak check becomes a veto.
2. **ANY may pass** (multiple primary). Maximum sensitivity; requires explicit
   correction; 10 independent checks → ~22% false-positive rate if uncorrected.
3. **m-of-n** (multi-component / ACR20 pattern). The legitimate home for "3 of 5" — but
   `m` and `n` must be fixed at design time, and it only works when the checks are
   expected to move together.
4. **Ordered prefix** (hierarchy / gatekeeping). Verdict = length of the leading run of
   passes. Deterministic, no combination table, lets one experiment support several
   distinct claims. Cost: ordering is a strategic gamble (PLATO), and later checks may
   never be reached.

### 6.3 The three enforcement mechanisms that actually distinguish working systems

1. **Timestamp + immutability + explicit amendment record.** ICH E9's "finalised before
   breaking the blind" + "formal records of when the plan was finalised."
2. **A reviewable pre-declared artifact**, not just stored text — the RR Design Table
   works because a reviewer gates on it.
3. **Render-time enforcement of the rule.** PLATO proves that a correct deterministic
   rule, correctly evaluated, is still routinely narrated past by the authors. The stop
   must be visible in the output, not just computed.

### 6.4 The one thing the fields agree you must NOT do

Change what counts as decisive after seeing the results. Every mechanism reviewed —
ICH E9 §2.2.2/§5.1, FDA §II.C, ClinicalTrials.gov's revision history, COMPare,
AsPredicted's timestamp, RR in-principle acceptance — exists to make that specific move
detectable, costly, or impossible.

---

## Source index (primary)

- [ICH E9, *Statistical Principles for Clinical Trials* (1998)](https://database.ich.org/sites/default/files/E9_Guideline.pdf) — §2.2.2–2.2.7, §5.1, §5.5–5.7
- [FDA, *Multiple Endpoints in Clinical Trials*, final guidance (Oct 2022)](https://www.fda.gov/media/162416/download) — §II–V
- [EMA, *Guideline on multiplicity issues in clinical trials* (draft)](https://www.ema.europa.eu/en/documents/scientific-guideline/draft-guideline-multiplicity-issues-clinical-trials_en.pdf)
- [Laporte et al., *What usage and what hierarchical order for secondary endpoints?* (Giens round table)](https://arxiv.org/pdf/2409.14770) — PLATO case, hierarchy construction
- [Hamasaki/Sozu et al., *Design, data monitoring and analysis of clinical trials with co-primary endpoints: a review*](https://pmc.ncbi.nlm.nih.gov/articles/PMC6135538/)
- [Evans, *When and How Can Endpoints Be Changed after Initiation of a Randomized Clinical Trial?*](https://pmc.ncbi.nlm.nih.gov/articles/PMC1852589/)
- [Scheel, Schijen & Lakens, *An Excess of Positive Results* (AMPPS 2021)](https://journals.sagepub.com/doi/10.1177/25152459211007467)
- [Bakker et al., *Ensuring the quality and specificity of preregistrations* (PLOS Biol 2020)](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3000937)
- [Claesen et al., *Comparing dream to reality* (R Soc Open Sci 2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8548785/)
- [van den Akker et al., *Selective Hypothesis Reporting in Psychology* (AMPPS 2023)](https://journals.sagepub.com/doi/10.1177/25152459231187988)
- [van den Akker et al., *Preregistration in practice* (Psych Sci 2023)](https://pubmed.ncbi.nlm.nih.gov/37950113/)
- [Lakens, *When and How to Deviate From a Preregistration* (Collabra 2024)](https://online.ucpress.edu/collabra/article/10/1/117094/200749/When-and-How-to-Deviate-From-a-Preregistration)
- [Chambers & Tzavella, *The past, present and future of Registered Reports* (Nat Hum Behav 2022)](https://www.nature.com/articles/s41562-021-01193-7)
- [Nature Ecology & Evolution Stage 1 Registered Report template (Design Table)](https://www.nature.com/documents/np-nee-template-stage1.pdf)
- [Zhao et al., *BOP2-DC: Bayesian optimal phase II designs with dual-criterion decision making* (Pharm Stat 2023)](https://onlinelibrary.wiley.com/doi/10.1002/pst.2296)
- [Olken, *Promises and Perils of Pre-Analysis Plans* (JEP 2015)](https://www.aeaweb.org/articles?id=10.1257/jep.29.3.61)
- [Ofosu & Posner, *Pre-Analysis Plans: An Early Stocktaking* (Perspect Polit 2021)](https://www.cambridge.org/core/journals/perspectives-on-politics/article/preanalysis-plans-an-early-stocktaking/94E7FAE76001C45A04E8F5E272C773CE)
- [Szollosi & Donkin, *Arrested Theory Development* (Perspect Psychol Sci 2021)](https://journals.sagepub.com/doi/full/10.1177/1745691620966796)
- [Rubin, *Preregistration, Severity, and Deviations* (2025)](https://arxiv.org/pdf/2408.12347)
- [*Re-Thinking Composite Endpoints* (PMC4275445)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4275445/)
