# Prior art: how existing systems model HYPOTHESIS vs EXPERIMENT

Research brief for the `crux` data-model redesign (splitting the fused hypothesis/experiment node).
Date: 2026-08-13.

---

## 0. The question being asked of the prior art

crux currently fuses claim + plan + pre-registered check + run links into one markdown node.
The relation we believe is real:

- one experiment → informs several hypotheses (N)
- one hypothesis → needs several experiments (pilot, full run, replication) (M)

So: **is there a prior art that carries an N:M claim↔evidence relation, and what construct does it use?**

Short answer from the survey: **yes, in exactly three places** — GrowthBook `Learning`,
the Micropublications / SEPIO evidence models, and (structurally, not semantically) the
ISA `Sample` shared-key join and W3C PROV qualified relations. Everywhere else the
relation is collapsed to 1:N containment or to free text.

---

## 1. Electronic lab notebooks (ELNs)

**Bottom line: "hypothesis" is not an entity in any ELN surveyed.** No table, no API resource, no schema
type, in Benchling, LabArchives, eLabFTW, SciNote, Chemotion, or RSpace. It lives as free text inside a
document body, or at best as a user-named custom field. The N:M relations that do exist connect
*materials* to *documents*, or *tasks* to *tasks* — never *assertions* to *evidence*.

### Benchling
Entities (top-level API paths): `/entries`, `/entry-schemas`, `/entry-templates`, `/projects`, `/folders`,
`/assay-runs`, `/assay-results`, `/assay-run-schemas`, `/assay-result-schemas`, `/result-transactions`,
`/custom-entities`, `/entity-schemas`, `/registries`, `/dna-sequences`, `/aa-sequences`, `/containers`,
`/plates`, `/requests`, `/request-schemas`, `/request-fulfillments`, `/workflow-tasks`,
`/workflow-task-groups`, `/workflow-outputs`, `/workflow-flowcharts`, `/datasets`, `/data-frames`.

- `Entry.folderId` — single string → Folder 1:N Entry.
- `Entry.entryTemplateId` — single nullable string → **one Entry Template : N Entries.** Recorded once at
  creation; provenance by reference, not a live link.
- `Entry.days[] → EntryDay.notes[] → EntryNotePart` — body content is **nested containment**, not rows.
- **`AssayResult.entryId` is a single nullable string** — "ID of the entry that this result is attached to".
  **A result cannot be attached to two entries.** Strictly 1:N. Same for `AssayRun.entryId`.
- `EntryLink` (in-body reference) carries `id` + `type`, where `type` enumerates the *target's kind*
  (`user | request | entry | protocol | workflow | custom_entity | dna_sequence | batch | container | …`),
  **not a relation label**. No supports/refutes qualifier.
- Schema fields: `isMulti` makes a field an array of references, but is *"always true for entities"* and
  *"always false for requests, results, and runs"* — only registry entities can hold multi-valued refs.
- `WorkflowTask` has `sourceTasks[]`, `nextTasks[]`, `sourceOutputs[]`, `nextOutputs[]` — a genuine N:M
  DAG, but over execution steps.
- `grep -ci hypothes` on the full OpenAPI spec: **0**.

- https://benchling.com/api/v2/openapi.yaml · https://docs.benchling.com/docs/schemas

### eLabFTW
Tables: `experiments`, `items`, `items_types`, `experiments_templates`, `experiments_categories`,
`experiments_status`, `experiments_steps`, `compounds`, `tags`/`tags2entity`, `uploads`, `*_revisions`.

`experiments` columns: `title`, `date`, `body mediumtext`, `category`, `status`, `metadata json`,
`created_from_id`, `created_from_type`. **No hypothesis column anywhere in the schema.**

Template → experiment by reference (`created_from_id` + `created_from_type`), snapshot-copied at creation.

**The key finding: eLabFTW has the N:M machinery but no way to say what an edge means.**
Every link table is *exactly two columns*:
```sql
CREATE TABLE `experiments2experiments` (
  `item_id` int UNSIGNED NOT NULL,
  `link_id` int UNSIGNED NOT NULL,
  PRIMARY KEY (`item_id`, `link_id`)
)
```
Identical shape for `experiments2items`, `items2experiments`, `items2items`,
`experiments_templates2experiments`, `experiments_templates2items`, `items_types2experiments`,
`compounds2experiments`, `containers2experiments`. All N:M, **all completely untyped** — no relation label,
no qualifier, no ordering, no timestamp. The API's `link` object exposes `type`, `category_id`,
`category_title`, `status_title`, but these are properties *of the target entity*, not of the edge.
Semantics can only be smuggled in by inventing a whole Resource Type or naming a JSON field in `metadata`
(see https://github.com/elabftw/elabftw/issues/4566).

- https://github.com/elabftw/elabftw/blob/master/src/sql/structure.sql · https://doc.elabftw.net/api/v2/

### Chemotion
Elements: `samples`, `reactions`, `wellplates`, `wells`, `screens`, `research_plans`, `collections`,
`containers`, `attachments`, `literatures`/`literals`, `elements`, `vessels`, `device_descriptions`.

- Collection ↔ element is **N:M** via one join table per type (`collections_samples`,
  `collections_reactions`, `collections_research_plans`, …).
- **`research_plans` is thin: `name`, `short_label`, `created_by`, `body jsonb`.** All structure lives in
  that JSON blob as an ordered array of typed blocks (rich text, table, image, Ketcher sketch,
  drag-dropped sample/reaction refs). So samples/reactions inside a Research Plan are **references inside
  a document blob, not rows** — not queryable joins. Its only real relational edges are
  `research_plans_screens` and `research_plans_wellplates` (both N:M).
- `research_plan_metadata` is DataCite publication metadata (`doi`, `publisher`, `related_identifier`) —
  Chemotion treats a Research Plan as a **publishable dataset, not a claim**.
- Analyses are `containers` with polymorphic `containable_type` ∈ `Sample|Reaction|Wellplate|Screen|ResearchPlan`
  plus `ancestry`/`parent_id` — 1:N containment tree; **one analysis belongs to exactly one element.**
- `literals(literature_id, element_id, element_type, category)` is **the one typed N:M edge in the whole
  schema** — `category` distinguishes citation roles. Nearest thing to a labelled relation, and it is for
  references, not hypotheses.
- `screens` has plain `varchar` columns `description`, `result`, `conditions`, `requirements` — closest to
  a pre-registered expectation, but untyped free strings.
- `grep -i hypothes` on `db/schema.rb`: **0**.

- https://github.com/ComPlat/chemotion_ELN/blob/main/db/schema.rb · https://chemotion.net/docs/eln/ui/details

### SciNote
Strict containment, expressed as nested URL paths:
`teams > projects > experiments > tasks > protocols > steps > {texts, tables, checklists, attachments}`,
and `tasks > results > {texts, tables, attachments}`.
- `results.my_module_id` is a single FK → **a result belongs to exactly one task; no sharing.**
- `protocols.my_module_id` single FK, plus `parent_id`, `protocol_type`, `nr_of_linked_children`,
  `version_number`, `previous_version_id` → **one team-level Protocol Template : N task-level copies**,
  with a live linked-children counter.
- `connections(input_id, output_id)` — N:M DAG between tasks inside one experiment.
- `experiments` has `name`, `description`, `metadata jsonb`. `grep -i hypothes`: **0**.

- https://scinote-eln.github.io/scinote-api-docs/ · https://github.com/scinote-eln/scinote-web/blob/master/db/structure.sql

### RSpace
ELN: `Folder`/`Notebook` → `Document` → `Field` → `File`. A `Form` defines `FormField`s which determine the
type and count of a Document's Fields — **one Form : N Documents**, the closest any ELN comes to a
schema'd notebook entry. A lab *could* define a Form with a "Hypothesis" FormField, but that is a
user-defined string slot, not a model entity. Inventory: `Sample`, `SubSample`, `Container`,
`SampleTemplate`, `SampleField`, `ExtraField`, `ContainerLocation`.

- https://documentation.researchspace.com/article/gvnduz7um5-api-data-model

### LabArchives
Four-level containment: **Notebook > Folder (nestable) > Page > Entry**. The API is not REST-resource-shaped
(`/api/<api_class>/<api_method>` with classes `users`, `tree_tools`, `entries`, `utilities`); folders and
pages are both `TreeNode`s. Entry types are *presentation* types (Rich Text, Plain Text, Attachment,
Heading, PubMed reference, Widget, Form, Inventory List, CSV). Linking is a hyperlink to an entry version,
not a modelled edge. **No hypothesis type and no typed relation table at all.**

- https://help.labarchives.com/hc/en-us/articles/11729082137364-Adding-and-Editing-Entries

### ELN takeaway for crux
Protocol→experiment is *by reference* everywhere (Benchling `entryTemplateId`, eLabFTW `created_from_id`,
SciNote `protocols.parent_id`), so one plan spawns many instances — the 1:N half of our problem is solved
identically across the industry. But **experiment→result is always a single foreign key**
(`AssayResult.entryId`, `results.my_module_id`), so a result can never serve two experiments. The gap crux
has identified is genuine and structural, not an oversight we are re-discovering.

---

## 2. ML experiment tracking

### MLflow
Entities (`mlflow.entities`): `Experiment(experiment_id, name, artifact_location, lifecycle_stage, tags, …)`,
`Run` = `RunInfo(run_id, experiment_id, run_name, status, …)` + `RunData(metrics, params, tags)`,
`LoggedModel(model_id, experiment_id, source_run_id, …)`, `RegisteredModel` → `ModelVersion(run_id)`,
`Dataset`/`DatasetInput`, `Trace`/`Span`, and MLflow 3 assessments `Feedback`, `Expectation`, `IssueReference`.

Cardinality:
- **Run → Experiment: strict 1:N containment.** `RunInfo.experiment_id` is a single scalar. There is
  no membership table, so N:M is structurally impossible.
- Nested runs are a *tag hack*: child carries system tag `mlflow.parentRunId` → a tree inside one experiment.
- `LoggedModel` carries both `experiment_id` and `source_run_id`; it can accrue metrics logged by *other*
  runs (evaluation runs) — the one place MLflow brushes N:M.
- `ModelVersion → run_id` 1:1; `RegisteredModel → ModelVersion` 1:N.
- `DatasetInput` on a run: the same dataset digest can appear on many runs (N:M, incidental).

Claims: **none as a typed object.** The description on Experiment and Run is the free-text system tag
`mlflow.note.content`. Assessments judge a *trace* (GenAI output quality), not a hypothesis.

- https://mlflow.org/docs/latest/ml/tracking/
- https://mlflow.org/docs/latest/api_reference/python_api/mlflow.entities.html

### Weights & Biases
Entities: Entity(team) → Project → Run; Sweep; Artifact (versioned `v0…`); Report; Registry → Collection; Automations.

Cardinality:
- Run → Project 1:N (movable, artifacts don't follow).
- `wandb.Run.group` and `wandb.Run.job_type` are **single strings** → grouping is 1:N, not N:M.
- A run belongs to at most one Sweep.
- **Tags are the genuine N:M**: `wandb.init(tags=[...])`, `run.tags += ("x",)`.
- Artifacts ↔ runs is N:M: one producing run, arbitrarily many consuming runs → lineage DAG.
- Registry Collections *link* artifact versions by reference; one version can be linked into several
  collections → N:M.

Claims: **Reports are the de facto claim layer, and they reference runs by QUERY, not by ID.**
The `wandb_workspaces.reports.v2` schema: `Report(entity, project, title, description, blocks)`;
a `PanelGrid` block holds `runsets: List[Runset]`; `Runset(entity, project, name, query, filters, groupby, order)`.
So narrative ↔ runs is many-to-many, resolved *at view time*, possibly cross-project. But: no field naming
the hypothesis, no pass/fail, no back-link from a run to the reports that cite it.

- https://docs.wandb.ai/guides/runs/grouping/
- https://docs.wandb.ai/guides/runs/tags/
- https://docs.wandb.ai/guides/reports/
- https://github.com/wandb/wandb-workspaces/blob/main/wandb_workspaces/reports/v2/interface.py

### Neptune (3.x / neptune-scale)
Entities: Project → Run, attributes in namespaces (`parameters/lr`, `sys/name`).
`Run(experiment_name=..., run_id=...)`, both mandatory.

**An Experiment is not a container — it is a NAME.** The newest run bearing that name is the
"experiment head"; earlier runs remain in the experiment's history but are no longer "an experiment".
Fetch APIs are split accordingly (fetch experiments → heads only; fetch runs → everything).

Cardinality: Run → experiment-name 1:N, fixed at creation. Forking (`fork_run_id`, `fork_step`) makes
run lineage a DAG — the strongest lineage model in this family. Reports are static snapshots over a
selected run set, versioned by publishing a draft.

Claims: none.

- https://docs.neptune.ai/about · https://docs.neptune.ai/fetch_runs · https://docs.neptune.ai/reports · https://docs.neptune.ai/forking

### DVC (+ DVCLive)
Entities: pipeline **stage** (`dvc.yaml`/`dvc.lock`) forming a DAG; params/metrics/plots files;
**experiment = custom Git refs under `.git/refs/exps`**, one or more commits based on `HEAD`, hidden from
the Git tree, not pushed by default; experiment **queue**; baseline commit.

Cardinality: experiment → baseline commit N:1. Because an experiment *is* a Git ref, it maps to exactly
one parent — multi-membership impossible. Claims: nothing; name only.

- https://doc.dvc.org/user-guide/experiment-management

### Sacred
Entities: `Experiment(name, ingredients=[...])`, Run, Ingredient, Observer, config scope, captured function.

Cardinality: Experiment → Run 1:N. **Ingredient ↔ Experiment is N:M** (an ingredient is importable by many
experiments; an experiment takes a list; ingredients nest). Observers ↔ runs N:M.
Run record: start/stop time, final config, result or error, host info, dependency versions, source files,
resources, artifacts, status. `result` is the return value of the main function — a number, not an interpretation.

- https://sacred.readthedocs.io/en/stable/experiment.html · https://sacred.readthedocs.io/en/stable/ingredients.html

### Hydra
Config group → options 1:N; a job composes one option per group; `--multirun` = cartesian product.
**Hydra has no run entity and no result store at all.** Out of scope for claims by design.

- https://hydra.cc/docs/tutorials/basic/your_first_app/config_groups/ · https://hydra.cc/docs/tutorials/basic/running_your_app/multi-run/

### Comet ML / Aim
Comet: Organization → Workspace → Project → Experiment (exactly one project; movable). Project sub-pages
include **Notes** — free-form Markdown *per project*, the only first-class prose field in this family that
sits at the grouping level rather than the run level, but unstructured and referencing nothing. Tags N:M.
Aim: `run.experiment` is a plain **string property** defaulting to `'default'` — grouping by string, no
experiment entity. Sequences keyed by name + context dict.

- https://www.comet.com/docs/v2/guides/comet-ui/experiment-management/project-pages/overview/
- https://aimstack.readthedocs.io/en/latest/understanding/concepts.html

### Verdict on this family
**None of these tools models a claim.** Every schema is run-mechanics: config in, metrics out, plus
1:N containment. N:M appears only incidentally (W&B tags and artifacts, Sacred ingredients, MLflow dataset
digests). The nearest approximations are prose escape hatches with no semantics: `mlflow.note.content`,
Comet project Notes, and W&B/Neptune/Comet Reports. W&B Reports are the most structurally interesting —
`Runset` binds narrative to an arbitrary *query* over runs, making claim↔evidence effectively N:M but
entirely untyped. Nowhere is there a falsifiable statement, a pre-registered success criterion, a verdict
field, or a back-pointer from a run to the question it was meant to answer.

---

## 3. A/B testing and feature-flag platforms — the closest prior art

This family is the only commercial software family that treats "hypothesis" as a required, named field,
and it is the only one that has independently invented the N:M claim↔evidence object.

### 3.1 GrowthBook (open source — schema read directly from source)

**`ExperimentInterface`** (`packages/shared/src/validators/experiments.ts`, ~L438):

```
id, uid, organization, project, owner, name, dateCreated, dateUpdated,
tags[], description, hypothesis (string, OPTIONAL),
variations[], phases[], status,
results ('dnf'|'won'|'lost'|'inconclusive'), winner (number), analysis (string),
releasedVariationId, linkedFeatures[], ideaSource, templateId, holdoutId,
manualLaunchChecklist, analysisSummary, customFields, ...
```
merged with **`ExperimentAnalysisSettings`**:
```
trackingKey, datasource, exposureQueryId,
goalMetrics: string[], secondaryMetrics: string[], guardrailMetrics: string[],
activationMetric, metricOverrides[], segment, queryFilter,
statsEngine, sequentialTestingEnabled, regressionAdjustmentEnabled,
decisionFrameworkSettings { decisionCriteriaId, decisionFrameworkMetricOverrides[{id, targetMDE}] }
```

Key cardinalities:
- **Metric ↔ Experiment is N:M, and the relation is ROLED.** `goalMetrics`, `secondaryMetrics`,
  `guardrailMetrics` are three arrays of metric *ids*. The same metric id can appear as a goal in one
  experiment and a guardrail in another. The role lives on the edge, not on the metric.
- **`metricOverrides[]` annotates the edge** (per-experiment `targetMDE`, window, etc.) — i.e. the
  experiment↔metric edge is reified into an object with its own attributes. Same trick as PROV qualified
  relations, arrived at independently.
- Experiment → Phase 1:N (`phases[]`, each with its own targeting/coverage/date range). A phase is the
  unit that gets analysed separately — this is how "pilot then full run" is expressed *inside* one
  experiment rather than as two experiments.
- `linkedFeatures: string[]` — Experiment ↔ Feature flag is N:M.
- `hypothesis` is a **plain optional string on the experiment**. There is no Hypothesis entity.
  (There *is* a vestigial `GeneratedHypothesisInterface { id, uuid, organization, url, hypothesis, experiment? }`
  — an AI-generated hypothesis with an optional 1:1 back-link to an experiment. Not a general claim object.)

**`ExperimentTemplateInterface`** (`experiment-template.ts`) — a reusable pre-registration:
```
templateMetadata { name, description }, type, hypothesis, description, tags, customFields,
datasource, exposureQueryId, hashAttribute,
goalMetrics[], secondaryMetrics[], guardrailMetrics[], activationMetric,
statsEngine, segment, targeting { coverage, savedGroups, prerequisites, condition }
```
**The template carries the hypothesis.** One template → many experiments (`experiment.templateId`).
So GrowthBook already has a shape where *one hypothesis statement spans several experiment runs* —
though as a template (copy-on-create), not as a live claim node.

**`DecisionCriteriaInterface`** (`packages/shared/src/enterprise/validators/decision-criteria.ts`) —
**pre-registered checks as a separate, reusable, first-class object**:
```
DecisionCriteriaCondition { match: 'all'|'any'|'none', metrics: 'goals'|'guardrails',
                            direction: 'statsigWinner'|'statsigLoser' }
DecisionCriteriaRule      { conditions: Condition[], action: 'ship'|'rollback'|'review' }
DecisionCriteriaInterface { id, organization, project, owner, name, description,
                            rules: Rule[], defaultAction }
```
One criteria object → many experiments (referenced by `decisionFrameworkSettings.decisionCriteriaId`).
Shipped presets: "Clear Signals" (all goals win, no guardrail loses) and "Do No Harm" (nothing
significantly negative). Evaluated automatically once target power / MDE / sequential threshold is met,
producing `ship-now` | `rollback-now` | `ready-for-review` | `days-left`.

**`LearningInterface`** (`packages/shared/src/validators/learnings.ts`) — **this is the N:M claim object,
and it is the single most relevant piece of prior art found in this whole survey**:
```
id, organization, owner, authors: string[],
title, text, tags: string[],
supportingExperimentIds:     string[],
contradictingExperimentIds:  string[],
projects: string[],
status: string,                 // org-configurable vocabulary (OrganizationSettings.learningStatuses)
source: 'ai' | 'manual' | 'api',   // provenance, immutable
lastRefreshedAt?: Date,         // last time checked against newly-stopped experiments
dateCreated, dateUpdated
```
- A Learning is a durable **claim** ("social proof lifts checkout on mobile") that lives *above*
  experiments and outlives any one of them.
- **Claim ↔ experiment is explicitly N:M and SIGNED**: two separate arrays, supporting and contradicting.
  Refutation is a first-class edge type, not an absence.
- **A refresh loop**: `lastRefreshedAt` + an AI check `{ stillAccurate: boolean, ... }` re-evaluates a
  saved Learning against experiments that stopped since. The claim's status is a *function of accumulated
  evidence over time*, recomputed — not written once.
- The AI suggestion schema adds `confidence: 'low'|'medium'|'high'` with an explicit rubric
  ("high = multiple experiments with large, statistically significant effects; low = suggestive but
  limited or mixed").
- `source` records whether a human, the AI, or an agent via the REST API created it.

**`IdeaInterface`** (`packages/shared/types/idea.d.ts`) — the upstream backlog node:
```
id, text, details, userId, userName, source: 'web'|'slack', organization, project, tags[],
votes[], impactScore, experimentLength, estimateParams { segment, estimate, improvement,
numVariations, userAdjustment }
```
Idea → Experiment via `experiment.ideaSource` (N:1 from the experiment side).

So GrowthBook's full chain is:
`Idea → (Template) → Experiment → phases → analysisSummary → DecisionCriteria → result → Learning ← other Experiments`.

- https://docs.growthbook.io/app/experiment-configuration
- https://docs.growthbook.io/app/experiment-decisions
- https://github.com/growthbook/growthbook/blob/main/packages/shared/src/validators/experiments.ts
- https://github.com/growthbook/growthbook/blob/main/packages/shared/src/validators/experiment-template.ts
- https://github.com/growthbook/growthbook/blob/main/packages/shared/src/validators/learnings.ts
- https://github.com/growthbook/growthbook/blob/main/packages/shared/src/enterprise/validators/decision-criteria.ts
- https://github.com/growthbook/growthbook/blob/main/packages/shared/types/idea.d.ts

### 3.2 Statsig

`POST /console/v1/experiments` request body (exact field names):
```
name (required, 3–100), id, description (≤1000),
hypothesis: string          // "A statement that will be tested by this experiment"
primaryMetrics:   [{ name, type, direction, hypothesizedValue }]
secondaryMetrics: [{ ... }]  // "might impact the analysis or final decision"
otherMetrics:     [{ ... }]  // "investigate or learn from"; no multiple-comparison correction
groups: [{ name, id, size, parameterValues, disabled, description }]
controlGroupID, launchedGroupID,
allocation (0–100), layerID, idType, targetingGateID, targetApps, tags, duration,
status: active | setup | decision_made | abandoned | archived | experiment_stopped | assignment_stopped
decisionReason: string      // "Experiment notes reported after experiment completes"
```

What is worth stealing here:
- **`hypothesizedValue` on the metric edge.** The expected effect size is stored *per (experiment, metric)
  pair*, alongside `direction`. That is a pre-registered, machine-checkable prediction attached to the
  edge, not prose in the body. This is the single cleanest "pre-registered check" field found anywhere.
- **`decisionReason` is a separate post-hoc field** distinct from `hypothesis` and from `description`.
  Prediction and verdict do not share a text box.
- **`status` includes `decision_made` and `abandoned`** as terminal states distinct from `experiment_stopped` —
  stopping the mechanics and deciding the claim are different events.
- Metric ↔ Experiment is **N:M**, confirmed by a dedicated lineage endpoint listing all experiments
  related to a given metric, returning `primaryMetrics` / `secondaryMetrics` / `otherMetrics` arrays.
- Layer ↔ Experiment is 1:N with mutual exclusion (traffic allocation partitioned within a layer).

- https://docs.statsig.com/api-reference/experiments/create-experiment
- https://docs.statsig.com/api-reference/metrics/lineage-list-experiments-related-to-metric
- https://docs.statsig.com/statsig-warehouse-native/features/experiment-options

### 3.3 Eppo

Data-plane entities (warehouse-native): **Entity** (randomization unit) → **Assignment SQL** (log of
subject × experiment × variant) → **Fact SQL** (events) → **Metric** (built on facts) → **Metric Collection**.

Control-plane entities: **Experiment / Experiment Analysis**, **Protocol**, **Experiment Report**,
**Knowledge Base**.

- **Protocol** = a named, pre-approved experiment design, reusable 1:N across experiments. Bundles:
  analysis settings (entity, assignment SQL, statistical method, default duration), **decision criteria
  (primary + guardrail metrics, rollout recommendation thresholds)**, secondary metrics, metric property
  breakouts, and team assignment. **No hypothesis field** — a Protocol is method, not claim. That split
  is deliberate and worth noting: Eppo separates *how we will decide* (reusable, team-level) from
  *what we predicted* (per-experiment).
- **Hypothesis** is a field on the experiment setup, described as: "A hypothesis for the experiment.
  You can also add this later when creating an experiment report" — i.e. deliberately deferrable.
- **Experiment Report** uses a Notion-style **page-and-block model**: multiple cards (pages) per report,
  blocks of type text / metric / image / variation. The Overview card holds **hypothesis, key takeaways,
  decision**.
- **Knowledge Base** = the central repository of experimentation learnings: every experiment with a
  *concluded* status that was not a misconfiguration, rendered as a card showing name, dates, team owner,
  **decision, primary metric impact, key takeaways**. Note this is a derived *view* over concluded
  experiments — not a separate claim entity like GrowthBook's Learning.
- **Metric Collections are COPIED, not referenced**: "the contents of the Metric Collection are copied
  together as a group when added to an experiment. Metrics can be added to or removed from this copied
  metric group without affecting the original Metric Collection 'template'." A deliberate choice to
  snapshot the analysis plan at design time so later edits to the template cannot retroactively change a
  finished experiment's pre-registration.

- https://docs.geteppo.com/data-management/
- https://docs.geteppo.com/quick-starts/analysis-integration/defining-protocols/
- https://docs.geteppo.com/experiment-analysis/configuration/
- https://docs.geteppo.com/experiment-analysis/reporting/experiment-reports/
- https://docs.geteppo.com/experiment-analysis/reporting/knowledge-base/
- https://docs.geteppo.com/data-management/organizing-metrics/collections/

### 3.4 Optimizely

Optimizely is the only vendor where **Hypothesis is the primary first-class object and the Experiment is
subordinate to it.**

In Optimizely Collaboration / program management:
- **Hypothesis** — "captures all the requirements, workflow, collaboration, data, and analysis for an
  experiment in one place". Fields at creation: **Title, Campaign, Start Date, Due Date, Workflow, Fields**
  (custom metadata). Tabs: **Brief** (structured test plan from a template, or an uploaded doc),
  **Variations**, **Experiment** (linked experiment references), **Fields**, **History** (full audit trail).
- **Brief template** → many Hypotheses (1:N). A reusable structured form for the test plan.
- **Workflow template** → many Hypotheses (1:N). Steps with due dates, forward/backward scheduling,
  "Smart Durations" that cascade date changes across dependent hypotheses.
- **Idea** — submitted through work-request forms, centralising idea intake; many Ideas feed a Hypothesis.
  Optimizely's Idea Builder gives each idea a **title, description, problem statement, hypothesis, and
  source references**.
- **Hypothesis → Experiment link**: "Click **Link Experiment** to select an experiment to link this
  hypothesis to." The Experiment tab holds *linked experiment references* (plural), so 1 Hypothesis : N
  Experiments. The docs do not confirm N:M in the other direction.
- Separately, in Feature Experimentation the *rule* itself has optional **Hypothesis** and **Test plan**
  fields, filterable and sortable from the Flags dashboard. So the hypothesis text is duplicated at the
  execution layer.

- https://support.optimizely.com/hc/en-us/articles/16504341933069-Manage-hypotheses
- https://support.optimizely.com/hc/en-us/articles/18027079344269-Get-started-with-Collaboration
- https://support.optimizely.com/hc/en-us/articles/4410283328013-The-Optimization-Methodology
- https://www.optimizely.com/product-updates/feature-management/

### 3.5 Summary of the A/B family

| System | Hypothesis is… | Reusable plan object | Pre-registered check | N:M claim↔experiment? |
|---|---|---|---|---|
| GrowthBook | optional string on Experiment; also on Template | `ExperimentTemplate` (carries hypothesis) | `DecisionCriteria` (rules→action), `targetMDE` | **Yes — `Learning` with `supportingExperimentIds[]` + `contradictingExperimentIds[]`** |
| Statsig | required-in-practice string on Experiment | Layers (traffic only) | `hypothesizedValue` + `direction` per metric edge | No — one hypothesis per experiment |
| Eppo | string on Experiment / Report Overview | `Protocol` (method only, no hypothesis); Metric Collection (copied) | Protocol decision criteria (primary + guardrail thresholds) | No — Knowledge Base is a derived view |
| Optimizely | **first-class object**, experiment subordinate | Brief template + Workflow template | Brief template fields | Partial — 1 Hypothesis : N Experiments |

---

## 4. Scientific workflow / provenance standards

### 4.1 W3C PROV (PROV-DM / PROV-O)

Core types: `prov:Entity` (a thing with fixed aspects), `prov:Activity` (something occurring over a period,
acting on entities), `prov:Agent` (bears responsibility). `prov:Plan`, `prov:Bundle`, `prov:Collection` are
**subclasses of Entity**. `prov:Role` and `prov:Location` are standalone classes.

Unqualified relations — all plain RDF object properties, hence **all N:M**; PROV-O sets no OWL cardinality
restrictions on any of them:

| Property | Domain → Range | Cardinality |
|---|---|---|
| `prov:wasGeneratedBy` | Entity → Activity | N:M (one generation *per* activity, many overall) |
| `prov:used` | Activity → Entity | N:M |
| `prov:wasInformedBy` | Activity → Activity | N:M |
| `prov:wasDerivedFrom` | Entity → Entity | N:M |
| `prov:wasAttributedTo` | Entity → Agent | N:M |
| `prov:wasAssociatedWith` | Activity → Agent | N:M |
| `prov:actedOnBehalfOf` | Agent → Agent | N:M (delegation chains) |
| `prov:wasInvalidatedBy` | Entity → Activity | N:M |
| `prov:hadMember` | Collection → Entity | 1:N per collection, N:M globally |
| `prov:wasInfluencedBy` | superproperty of all above | N:M |

**The qualification (reification) pattern — the load-bearing idea.** A binary edge carries no room for
annotation, so PROV turns the edge into a node. Three moving parts:

1. From the **subject**, a `prov:qualified*` property points at the new node:
   `prov:qualifiedUsage` (Activity → `prov:Usage`), `prov:qualifiedGeneration` (Entity → `prov:Generation`),
   `prov:qualifiedAssociation` (Activity → `prov:Association`), `prov:qualifiedDerivation`,
   `prov:qualifiedAttribution`, `prov:qualifiedCommunication`, `prov:qualifiedDelegation`,
   `prov:qualifiedInvalidation`, `prov:qualifiedInfluence` (generic).
2. From the node, an **influencer property** points at the object, one of three by influence kind:
   `prov:entity` (EntityInfluence: Usage, Derivation, Start, End, Quotation, Revision, PrimarySource),
   `prov:activity` (ActivityInfluence: Generation, Communication, Invalidation),
   `prov:agent` (AgentInfluence: Association, Attribution, Delegation).
   `prov:influencer` is the generic superproperty on `prov:Influence`.
3. The node carries **annotations**: **`prov:hadRole` (→ `prov:Role`)**, **`prov:hadPlan`** (on Association →
   `prov:Plan`), `prov:atTime` (on `prov:InstantaneousEvent` subclasses), `prov:hadActivity`,
   `prov:hadUsage`, `prov:hadGeneration` (on Derivation), `prov:atLocation`.

Spec rule: **the qualified form implies the unqualified form**; consumers should accept both. So you can
write the cheap edge and upgrade it to a node later without breaking readers — a migration property crux
should want.

**Why `prov:hadRole` matters for us.** The role lives on the qualified node, not on the entity or the agent.
The same `prov:Entity` used by two activities gets **two distinct `prov:Usage` nodes, each with its own
`prov:hadRole`** — "training set" here, "held-out set" there. Identity stays global; role stays local to the
edge. That is exactly the shape of "one experiment supports hypothesis A but is merely a pilot for
hypothesis B".

**No hypothesis concept.** PROV has nothing for a claim that can be true or false. Natural mapping: a
hypothesis is a `prov:Entity` (fixed-aspect, can be generated, revised, attributed, invalidated) — a
`prov:Plan` subtype if it prescribes what to do, otherwise a domain subclass of Entity. Refutation maps to
`prov:wasInvalidatedBy` an evaluating Activity; revision to `prov:wasRevisionOf`; evidence→hypothesis to
`prov:wasDerivedFrom`. Verdict/confidence has no home except as an attribute on the entity or the Generation.

- https://www.w3.org/TR/prov-dm/ · https://www.w3.org/TR/prov-o/#description-starting-point-terms · https://www.w3.org/TR/prov-o/#description-qualified-terms

### 4.2 RO-Crate

Base spec: `ro-crate-metadata.json` holds a JSON-LD `@graph`. The **metadata file descriptor** MUST have
`@id: "ro-crate-metadata.json"`, `@type: CreativeWork`, `conformsTo` (versioned `https://w3id.org/ro/crate/…`),
and `about` → `{"@id": "./"}` (single). The **root data entity** MUST be `@type: Dataset` with `@id` ending
in `/`, MUST have `datePublished`, SHOULD have `name`, `description`, `license`. `hasPart` → data entities
(multiple, optional). **`mentions`** → contextual entities not otherwise reachable — this is where run
Actions get attached so they are not orphaned.

**Workflow Run RO-Crate profiles** — three nested levels; root `conformsTo` names the profile URI(s):

- **Process Run Crate** (`https://w3id.org/ro/wfrun/process/0.5`): one `CreateAction` per tool execution.
  `instrument` MUST, **single** → `SoftwareApplication`. `object` MAY, multiple → inputs.
  `result` SHOULD, multiple → outputs. `agent` SHOULD, single. Plus `startTime`, `endTime`, `name`,
  `description`, `actionStatus` (`CompletedActionStatus`/`FailedActionStatus`), `error`.
- **Workflow Run Crate** (`https://w3id.org/ro/wfrun/workflow/0.5`): the workflow file MUST be
  `["File","SoftwareSourceCode","ComputationalWorkflow"]` and MUST be the root's `mainEntity` (single).
  The run's `CreateAction.instrument` MUST point at that workflow. Parameter slots are `FormalParameter`
  (`additionalType` MUST; `exampleOfWork` SHOULD link the actual data entity back to the slot).
- **Provenance Run Crate** (`https://w3id.org/ro/wfrun/provenance/0.5`): adds internal steps. Workflow
  additionally typed **`HowTo`**, with `hasPart` MUST → tools/subworkflows and `step` SHOULD → ordered
  **`HowToStep`**s (`position`; `workExample` MUST → the tool implementing the step). One `OrganizeAction`
  per engine run: `instrument` MUST → engine, `object` MUST → the `ControlAction`s, `result` MUST → the
  workflow-level `CreateAction`. Each **`ControlAction`**: `instrument` MUST → a `HowToStep`,
  `object` MUST → the step's `CreateAction`(s).

**Plan-to-runs cardinality — the clean split.** `ComputationalWorkflow` / `HowTo` / `HowToStep` are
**prospective** (one plan). `CreateAction` / `ControlAction` / `OrganizeAction` are **retrospective**
(many runs). The join is `instrument`: N runs each point their *single* `instrument` at the same plan node,
so plan→runs is 1:N read backwards, and one `HowToStep` can be executed many times (scatter/parallel) with
N `CreateAction`s under one `ControlAction`.

Cross-standard note: `instrument`/`object`/`result` are the schema.org analogues of PROV's
`used`/`wasGeneratedBy`, and `HowToStep` + `ControlAction` is **PROV's qualification pattern done in
schema.org vocabulary** — the `ControlAction` *is* a reified edge between plan-step and actual run.

- https://www.researchobject.org/ro-crate/specification/1.1/root-data-entity.html · https://www.researchobject.org/workflow-run-crate/profiles/

### 4.3 ISA model (Investigation / Study / Assay)

**Hierarchy and cardinality** (§1.1): "For each `Investigation` there may be one or more `Study` associated
with it; for each `Study` there may be one or more `Assay`." So **1 Investigation : N Studies : N Assays**,
a strict tree. Grouping is explicitly optional — the Investigation "only becomes necessary when two or more
Study objects need to be grouped."

**A Study is NOT "a unit of research with a hypothesis".** The spec's own words: "A `Study` is a central
concept containing information on the subject under study, its characteristics and any treatments applied";
and "A `Study` contains contextualising information for one or more `Assay`. Metadata about the study
design, study factors used, and study protocols are recorded in Study objects."

Study-level fields (ISA-Tab sections / ISA-JSON arrays): Identifier, Title, Description, Submission Date,
Public Release Date, **STUDY DESIGN DESCRIPTORS** (`studyDesignDescriptors`, ontology annotations, e.g.
cross-over design), **STUDY PUBLICATIONS**, **STUDY FACTORS** (`factors`: Factor Name, Factor Type — "an
independent variable manipulated by the experimentalist"), **STUDY ASSAYS**, **STUDY PROTOCOLS**,
**STUDY CONTACTS**; plus `materials{sources, samples, otherMaterials}`, `processSequence`,
`characteristicCategories`, `unitCategories`.

Study Sample file (`s_*.txt`): `Source Name` → `Protocol REF` → `Sample Name`, with `Characteristics[…]`
and `Factor Value[…]` columns. Splits (one source → many samples) and pools (many sources → one sample) are
encoded by repeating name values across rows.

**An Assay**: "a test performed either on material taken from a subject or on a whole initial subject,
producing qualitative or quantitative measurements", typed by **Measurement Type** (the endpoint),
**Technology Type**, **Technology Platform**. "each Assay file must contain assays of the same type."
Assay table: `Sample Name` (MUST be first node) → `Protocol REF` → `Extract Name` → `Labeled Extract Name`
→ `Assay Name` → `Raw Data File` / `Derived Data File`.

**Hypothesis: definitively NO.** No hypothesis field in Investigation, Study, or Assay in the abstract
model (§1.1.1–1.1.3), nor as an ISA-Tab section, nor as an ISA-JSON property. Nearest surrogates are Study
`Design Type` / `studyDesignDescriptors` and Study Factors. Free text would go in `Description` or a
`Comment[…]` column.

**The many-to-many join is `Sample Name` — a shared STRING KEY, not a pointer.** `Sample Name` terminates
the study sample table and MUST open every assay table; **the same literal value appearing in `s_study.txt`
and in N different `a_*.txt` files is what stitches one sample to N assays** (same sample measured by both
transcriptomics and metabolomics). One row per sample-per-assay in each assay file, so the study table stays
one row per sample while the join fans out. In ISA-JSON the same join is by `@id` reference. Constraint: if
both Study and Assay carry a `Factor Value`, "these must be different."

**One assay in two studies: NO.** An assay file is declared inside exactly one study block
(`Study Assay File Name`) and its Sample Names must resolve in that study's sample file. Reuse across
studies means duplicating the file. **So the tree is strict *above* the sample, and many-to-many only *at*
the sample.**

**Protocol as a reusable declared object.** STUDY PROTOCOLS declares each protocol once: `Study Protocol
Name` (the identifier), Type, Description, URI, Version, Parameters Name, Components Name/Type.
"`Protocol REF` columns MUST be used to indicate `Process` nodes, with values referencing protocols declared
in the Investigation file", optionally qualified by `Parameter Value[…]`, `Performer`, `Date`.
Cardinality: **1 declared protocol : N process nodes**, across any number of study and assay tables.

**Mapping onto question/hypothesis/experiment (the question asked):** ISA's three levels do *not* map to
question/hypothesis/experiment. The mapping is Investigation ≈ *grouping folder*, Study ≈ *experimental
system + design + factors*, Assay ≈ *measurement type applied to material*. The claim layer is simply
absent, and the level that looks like "hypothesis" (Study) is actually the sample-and-design layer.

- https://isa-specs.readthedocs.io/en/latest/isamodel.html · https://isa-specs.readthedocs.io/en/latest/isatab.html · https://isa-specs.readthedocs.io/en/latest/isajson.html · https://isa-tools.org/format/specification.html

### 4.4 Nanopublications

A nanopub is a set of RDF quads across **four named graphs**: Head [H], assertion [A], provenance [P],
publication info [I]. The Head carries **exactly one** quad each of:
`[N] rdf:type np:Nanopublication [H]`, `[N] np:hasAssertion [A] [H]`, `[N] np:hasProvenance [P] [H]`,
`[N] np:hasPublicationInfo [I] [H]`. `np:hasProvenance` and `np:hasPublicationInfo` are
`owl:FunctionalProperty`. Constraints: [N],[H],[A],[P],[I] all different; every triple sits in one of
[H],[A],[P],[I]; triples in [P] must reference [A] at least once; triples in [I] must reference [N] at
least once. **So cardinality is 1:1:1:1 — one claim per nanopub, by construction.**

The **claim** is "a small atomic unit of information", in practice one triple
(`ex:malaria ex:isTransmittedBy ex:mosquitoes`). **Evidence attaches in [P], about [A]**:
`prov:wasDerivedFrom` a dataset or an earlier assertion, `prov:hadPrimarySource` a paper/PubMed URI,
`prov:wasAttributedTo` an ORCID, `prov:wasGeneratedBy` a method or workflow. [I] holds creator, timestamp,
license, signature.

**Composition.** Nanopubs "cannot contain but only refer to other nanopublications"; **trusty URIs**
(content hashes baked into the URI, e.g. `http://purl.org/np/RAfk_zBY…`) make those references nearly as
strong as containment. Because [A] has its own URI, **any number of later nanopubs can point at that
assertion graph** → 1 assertion : N citing nanopubs, unbounded. A nanopub is **immutable**, so support
accumulates as new nanopubs, never as edits.
- **Update**: `npx:supersedes` in the **publication info** graph of the new version.
- **Retraction**: a separate nanopub whose **assertion** says `<orcid> npx:retracts <old-np-uri>`; valid
  only if signed with the same key pair as the target.
- **Index**: itself a nanopub whose assertion lists members with `npx:includesElement` (sub-indexes via
  `npx:includesSubindex`). A single index holds at most **1000** references; long collections chain via
  `npx:appendsIndex` — a linked list.

**Takeaway:** nanopubs give the *citable atomic claim* and the *immutable, append-only accumulation of
support* that crux wants for hypotheses, but no experiment structure at all. ISA gives the experiment
structure with no claim. Neither gives both.

- https://nanopub.net/guidelines/working_draft/ · https://nanopub.net/ · https://nanopub.readthedocs.io/en/latest/publishing/retraction.html · https://arxiv.org/abs/1508.04977

---

## 6. Master comparison table

| System | Claim entity? | Plan entity | Run/evidence entity | Claim ↔ evidence cardinality | Construct used for N:M | Signed edges (support vs refute)? | Pre-registered check as data? |
|---|---|---|---|---|---|---|---|
| **Benchling** | no | `EntryTemplate` (1:N Entries) | `AssayRun`, `AssayResult` | 1:N only (`AssayResult.entryId` single FK) | — | no | schema fields on `AssayResultSchema` |
| **eLabFTW** | no | `experiments_templates` (`created_from_id`) | `experiments`, `items` | N:M but **untyped** | 2-column join tables (`experiments2experiments`) | no | no |
| **SciNote** | no | `protocols` template (`parent_id`, 1:N copies) | `results` | 1:N only (`results.my_module_id` single FK) | — | no | no |
| **Chemotion** | no (`research_plans` is a `jsonb` doc) | — | `samples`, `reactions`, `containers` | 1:N (`containable_type` polymorphic) | collection joins; `literals.category` is the one typed edge | no | `screens.conditions/requirements` (free strings) |
| **RSpace** | no | `Form` → `FormField` (1:N Documents) | `Document`/`Field` | 1:N | — | no | user-defined FormField only |
| **LabArchives** | no | — | `Entry` under Notebook>Folder>Page | 1:N containment | — | no | no |
| **MLflow** | no (`mlflow.note.content` tag) | — | `Run` | 1:N (`RunInfo.experiment_id` scalar) | nested runs via `mlflow.parentRunId` tag | no | no |
| **W&B** | Report (untyped prose) | Sweep config | `Run`, `Artifact` | **N:M via `Runset.query`** (resolved at view time) | dynamic query, not IDs | no | no |
| **Neptune** | no | — | `Run` (experiment = a *name*; head = newest run) | 1:N | fork DAG (`fork_run_id`, `fork_step`) | no | no |
| **DVC** | no | `dvc.yaml` stage DAG | experiment = Git ref | N:1 to baseline commit | — | no | no |
| **Sacred** | no | `Ingredient` | `Run` | 1:N | Ingredient ↔ Experiment is N:M | no | no |
| **Hydra** | no | config group | *(none — no run entity)* | — | — | no | no |
| **GrowthBook** | **`Learning`** | `ExperimentTemplate` (carries `hypothesis`), `DecisionCriteria` | `Experiment` → `phases[]` → `analysisSummary` | **N:M** | **two arrays on the claim: `supportingExperimentIds[]`, `contradictingExperimentIds[]`** | **yes** | **`DecisionCriteria.rules[]` + `targetMDE`** |
| **Statsig** | no (`hypothesis` string) | Layer | `Experiment` | 1:1 hypothesis:experiment | — | no | **`hypothesizedValue` + `direction` per metric edge** |
| **Eppo** | no (Report Overview: hypothesis/takeaways/decision) | **`Protocol`** (method only), Metric Collection (copied) | `Experiment Analysis` | 1:1; Knowledge Base is a derived view | — | no | Protocol decision criteria |
| **Optimizely** | **`Hypothesis`** (primary object) | `Brief template`, `Workflow template` | `Experiment` (linked) | **1 Hypothesis : N Experiments** | `Link Experiment` refs on the Hypothesis | no | Brief template fields |
| **W3C PROV** | no (map to Entity/Plan) | `prov:Plan` | `prov:Activity` | N:M everywhere (no cardinality axioms) | **qualified relations: `prov:Usage`/`Generation`/`Association` + `prov:hadRole`** | via `wasInvalidatedBy` only | `prov:hadPlan` on Association |
| **RO-Crate (WRROC)** | no | `ComputationalWorkflow`/`HowTo`/`HowToStep` | `CreateAction`/`ControlAction`/`OrganizeAction` | plan 1:N runs via `instrument` | `ControlAction` = reified plan-step↔run edge | no | `FormalParameter` + `exampleOfWork` |
| **ISA-Tab** | **no hypothesis field anywhere** | `Study Protocol` (1:N `Protocol REF` nodes) | `Assay` | Investigation 1:N Study 1:N Assay (strict tree) | **`Sample Name` shared string key across assay files** | no | Study Design Descriptors, Study Factors |
| **Nanopublication** | **the assertion graph [A]** | — | provenance graph [P] | 1 claim per nanopub; **1 assertion : N citing nanopubs** | trusty-URI reference to [A]; `npx:includesElement` index (≤1000, chained) | `npx:retracts`, `npx:supersedes` | no |
| **EXPO** | `ExperimentalHypothesis` (H0/H1/alternative) | `ExperimentalDesign`, `PlanExperimentalActions` | `ExecutionOfExperiment`, `ExperimentalResults` | **part-of only** — hypothesis is *part of* experiment | none (5 relations total, no cardinality axioms) | `FactSupport H1` / `FactReject H1` as result classes | `ExperimentalGoal` |
| **LABORS / Adam** | Datalog hypothesis literals | experiment-design code | **investigation·study·cycle·trial·test·replicate** (10 levels) | tree edge + Datalog derivation | none — N:M appeared in results, unhandled | via `Prob`/`Acc` post-hoc | two-factor `test` contrast |
| **OBI / IAO** | `hypothesis textual entity` IAO:0000415, `testable hypothesis` OBI:0001908 | `plan specification` IAO:0000104, `study design` | `planned process`, assay | N:M **by omission** (no cardinality) | 3-hop chain via `objective specification` + `achieves planned objective` OBI:0000417 | no | `objective specification` IAO:0000005 |
| **SWAN** | `ResearchStatement` (Hypothesis and Claim nest) | — | cited literature | N:M | `citesAsSupportingEvidence` / `citesAsRefutingEvidence` | **yes** | no |
| **Micropublications** | **`Claim`** | `Method` (⊃ `Procedure`, `Material`) | `Data`, `Statement` | **N:M** | **SupportGraph = a DAG rooted at the Claim**; `elementOf` fans one Data node out to many claims | **yes** — `supports` (transitive), `directChallenges`/`indirectChallenges` | `supportedByMethod` |
| **SEPIO** | **`assertion`** (+ `hypothesis` SEPIO:0000432) | evidence criterion | `evidence item` | **N:M, horizontally and vertically** | **`evidence line` — a reified, first-class edge object** | **yes** — `has_supporting_evidence_line` / `has_disputing_evidence_line` / `has_inconclusive_evidence_line` | `evidence_line_strength`, `evidence_direction` |

---

## 7. What to borrow — synthesis for crux

### 7.1 The three models worth stealing from

**(a) SEPIO's reified `evidence line` — the structural answer.**
Do not put `experiments: [...]` on the hypothesis and `hypotheses: [...]` on the experiment. Introduce a
third node — call it a *bearing*, *finding*, or *evidence line* — that names one (hypothesis, experiment)
pair and carries its own attributes: **direction** (supports / disputes / inconclusive), **strength**,
the criterion it was judged against, and its own provenance. This is the only construct in the survey that
survives the awkward cases: a pilot that is merely *enabling* for hypothesis A but *disputing* for B; two
hypotheses fed by one run with different weights; re-grading an old run under a new criterion without
touching either the hypothesis or the experiment file.
It is also, independently, **PROV's `prov:hadRole` pattern** and **RO-Crate's `ControlAction`** — three
unrelated standards converged on "promote the edge to a node so it can carry a role". That convergence is
the strongest signal in this report.

**(b) GrowthBook's `Learning` — the shipped, working version of the same idea, and the closest
commercial analogue to a crux hypothesis node.**
Borrow, concretely: (i) two **signed** arrays (`supportingExperimentIds`, `contradictingExperimentIds`) —
refutation is an explicit edge type, not an absence; (ii) `source: 'ai' | 'manual' | 'api'` recorded
immutably, so agent-authored claims are distinguishable from human ones; (iii) **`lastRefreshedAt` plus a
refresh loop that re-checks a saved claim against experiments that stopped since** — the claim's standing
is a *recomputed function of accumulated evidence*, not a one-time write; (iv) a `confidence` scale with an
explicit rubric rather than a bare number.
Also borrow GrowthBook's separation of **`DecisionCriteria` into its own reusable object**
(`rules: [{conditions:[{match, metrics, direction}], action}]`, `defaultAction`) — crux's pre-registered
checks should be a named, shareable object referenced by id, not prose inside the hypothesis body.

**(c) Statsig's `hypothesizedValue` on the metric edge — the pre-registration primitive.**
The predicted effect size and direction live *per (experiment, metric) pair*, not in the hypothesis prose.
That makes the check machine-evaluable and makes "we predicted X, we got Y" a computable diff. Pair it with
Statsig's second discipline: **`hypothesis` and `decisionReason` are separate fields**, and `status` has
`decision_made` as a state distinct from `experiment_stopped`. Prediction, mechanics-stopping, and verdict
are three different events with three different homes.

**(d) RO-Crate's prospective/retrospective split (runner-up, but the cleanest naming).**
`HowTo`/`HowToStep` (the plan, written once) vs `CreateAction` (the run, N of them), joined by a single
`instrument` pointer from each run to the plan. This is the right shape for crux's "Planned Intervention"
section: the plan is a first-class node reused across pilot and full run; each run points back at it.
GrowthBook's `ExperimentTemplate` (which carries the hypothesis text!) and ISA's `Study Protocol` /
`Protocol REF` are the same pattern in two other vocabularies.

### 7.2 One thing to deliberately NOT copy

**Do not copy ISA-Tab's join-by-shared-string-name.** ISA achieves its one many-to-many (sample → many
assays) by having the literal string in a `Sample Name` cell appear in several files. It has no
referential integrity, no way to rename, no way to detect a typo, and — the fatal part — **no place to put
anything about the relationship**, because the relationship has no identity. In a git-and-markdown system
that temptation is acute: it is very cheap to write `hypothesis: H-03` as a bare string in an experiment's
front-matter and call it linked. Do not. Give the link an id and a file, or at minimum a typed, validated
reference the linter can resolve — otherwise crux inherits eLabFTW's exact failure mode, which is
**having the N:M machinery and no way to say what an edge means** (two-integer join tables with no type
column).

Secondary "do not copy", same family: **do not make the hypothesis a mere part of the experiment the way
EXPO does** (`ExperimentalHypothesis` p/o `ScientificExperiment`, five relations, no cardinality). That is
precisely crux's current fused design, and the canonical experiment ontology has it too — which explains
why it felt natural and why it still fails on the second experiment.

### 7.3 Two smaller ideas worth a look

- **Nanopublication immutability**: support accumulates as *new* records; `npx:supersedes` and
  `npx:retracts` are separate signed records rather than edits. In a git repo this is nearly free and gives
  crux an audit trail of how a hypothesis's standing changed.
- **The Robot Scientist's experiment-selection rule** (Nature 2004, never formalised into the ontology):
  hold a *set* of candidate hypotheses with probabilities, and choose the next experiment by trading
  **expected discrimination against cost** (~100× cheaper than random selection). This is the principled
  answer to crux's "what should we try next", and it is only expressible once one experiment can bear on
  several hypotheses — i.e. only after the N:M split.


---

## 5. Semantic / ontology work

### 5.1 EXPO — the ontology of scientific experiments (Soldatova & King, J R Soc Interface 3(11):795–803, 2006)

218 concepts, OWL-DL, anchored to SUMO (46 SUMO classes reused, 172 new).

Class tree (verbatim from Fig. 2): `ScientificExperiment` at the root →
`PhysicalExperiment` (→ `GalileanExp.`, `BaconianExp.`), `ComputationalExp.`;
`GalileanExp.` splits into **`Hypothesis-drivenExp.` / `Hypothesis-formingExp.`**.
Sibling top-level parts: `ExperimentalGoal` (→ `ConfirmGoal`, `InvestigateGoal`, `ExplainGoal`,
`ComputeGoal`), `ClassificationOfExperiments` (→ `One-factorExperiment`, `Two-factorExperiment`,
`Multi-factorExperiment`), `ExperimentalDesign` (→ `SubjectOfExperiment`, `ObjectOfExperiment`,
`ExperimentalEquipment`, `ExperimentalTechnology`, `ExperimentalDesignStrategy` → `NormalizationStrategy`,
`QualityControlStrategy`, `ParedComparison`…), `ExperimentalModel` (→ `TargetVariable`, `Factor` →
`FactorLevel`), `PlanExperimentalActions`, `ExperimentalHypothesis`, `ExperimentalResults`,
`AdminInfoAboutExperiment`.

Hypothesis branch: `ExperimentalHypothesis` → `RepresentationStyle` (`Text`, `Program`),
`LinguisticExpression` (`NaturalLanguage`, `ArtificialLanguage`), **`ResearchHypothesis H1`**,
**`NullHypothesis H0`**, `AlternativeHypothesis` (→ `SubjectEffect` → `TestingEffect`, `ExperimenterBias`;
`ObjectEffect`; `TimeEffect`; `ExperimentalDesignEffect`).

Results branch: `ExperimentalResults` → **`ExperimentalConclusion` (→ `FactReject H1`, `FactSupport H1`)**,
`ResultError` (→ `ErrorOfConclusion`, `FaultyComparison`, `IncompleteDataError`, `MeasurementError`,
`HypothesisAcceptanceM.` → `FalsePositive`, `FalseNegative`).

**Key negative finding.** EXPO has **no `has_hypothesis`, no `tests`, no `has_goal` object property.**
§2.2 states the design goal: "In designing EXPO we have endeavoured to use as few relations as possible."
The complete relation set is **five**: `subclass` (is-a), `instance of`, `part` (p/o), `attribute` (a/o),
`role`. Hypothesis-to-experiment is expressed **mereologically** — `ExperimentalHypothesis` is *part of*
`ScientificExperiment`, the same construct as `ExperimentalDesign` being part of it. **No cardinality
axioms are stated anywhere in the paper.** Context-dependence is carried by `role` (a human is
`SubjectOfExperiment` or `ObjectOfExperiment` by role, not by class).

So EXPO gives a hypothesis *vocabulary* (H0/H1/alternative, support/reject, false-positive/false-negative)
but leaves the N:M hypothesis↔experiment link unformalised — and in fact fuses them exactly the way crux
currently does.

- https://royalsocietypublishing.org/doi/10.1098/rsif.2006.0134 · https://europepmc.org/api/getPdf?pmcid=PMC1885356 · https://expo.sourceforge.net/

### 5.2 The Robot Scientist (Adam / Eve, Ross King) — LABORS

**LABORS** = LABoratory Ontology for Robot Scientists, "a customised version of EXPO, expressed in OWL-DL",
emitting experiment descriptions in **Datalog**. Adam produced "over 10,000 different research units in a
nested tree-like structure, **ten levels deep**", connecting 6,657,024 OD600 readings (26,495 growth curves).

**Exact level names** (Science 2009, Fig. 3a): "Each level of research unit (studies, cycles, trials, tests,
and replicates) is characterised by a specific set of properties." The ordered spine is:

**investigation · study · cycle · trial · test · replicate** → observations,

with *recursion* at the investigation and study levels supplying the remaining depth to ten.
(e.g. investigation "into automation of science" → study "of genes encoding orphan enzymes" → study
"of enzyme EC 2.6.1.39" → study "of YER152C function" → cycle 1..5 → trial "C00047 YER152C" →
test "ΔYER152C and C00047" / "WT and no C00047" → replicate 1..24.)

**Hypotheses sit at two levels** (Sparkes et al. 2010): level 1 = gene→enzyme mappings,
`encodesORFtoEC('YBR166C','1.1.1.25')`; level 2 = observational consequences *deduced* from a Prolog
metabolic model, `affects_growth('C00108','YBR166C')`. The experiment-design code consumes the model plus
a level-2 prediction and emits a plan; the **trial** pairs one metabolite with one deletant, and the
**test** is the two-factor contrast (deletant ± metabolite vs. wild type).

**The hypothesis→experiment link is NOT a named object property** — it is the tree edge plus the Datalog
derivation. Statistical attachment is post-hoc: `Prob` (Monte-Carlo estimate under random relabelling of
replicates) and `Acc` (best discrimination accuracy). Adam formulated and tested **20 hypotheses over 13
orphan enzymes; 12 confirmed at P<0.05**.

**The N:M case shows up in the results and is unhandled by the model:** three genes (YER152C, YJL060W,
YGL202W) were each hypothesised to encode 2A2OA, and *all three* were consistent with the same
observations — competing hypotheses sharing one evidence base, resolved only by a later in-vitro assay.

**Experiment selection** (the 2004 Nature paper, never lifted into the ontology): Adam's predecessor held
a **set of candidate hypotheses with probabilities** and chose experiments by trading **expected
discrimination against experiment cost** — ~3× cheaper than cheapest-first and ~100× cheaper than random,
competitive with human experimenters. This decision-theoretic layer is the single most interesting idea in
the Robot Scientist work for crux's "what should we run next" question, and it was **never formalised into
LABORS/EXPO**.

- https://www.science.org/doi/abs/10.1126/science.1165620 · https://realscience.org.uk/Adamtherobotscientist.pdf
- https://academic.oup.com/bioinformatics/article/22/14/e464/228140
- https://pmc.ncbi.nlm.nih.gov/articles/PMC2813846/ · https://www.nature.com/articles/nature02236

### 5.3 OBI / IAO
**No hypothesis-tests-experiment property.** The hypothesis is an information content entity:
`hypothesis textual entity` **IAO:0000415** ("A textual entity that expresses an assertion that is intended
to be tested"), `testable hypothesis` **OBI:0001908**. The link runs **through the plan**:
`objective specification` IAO:0000005 is *part of* a `plan specification` IAO:0000104; a `study design`
(a plan specification) is concretised and **`realizes`**'d by a `planned process`; the process
**`achieves planned objective` OBI:0000417** (inverse `objective_achieved_by` OBI:0000833) pointing at the
objective specification; data flows via **`has_specified_input` OBI:0000293** and
**`is_specified_output_of` OBI:0000299**.

So OBI reaches hypothesis→experiment in **three hops**
(`hypothesis textual entity` → `objective specification` → `planned process`/assay → data as specified
output) and imposes **no cardinality** — it is N:M by omission, not by design.

- https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0154556 · https://www.ebi.ac.uk/ols4/ontologies/obi

### 5.4 SIO, HELO, SWAN
- **SIO**: `hypothesis` SIO:000284 ("a proposed explanation for a phenomenon"); `to test a hypothesis`
  SIO:001219, modelled as a *capability*. Thin.
- **HELO** (HypothEses and Laws Ontology, Soldatova & King): attaches **probabilities** to hypotheses,
  laws and conclusions and records **the inference method that generated or updated them** — the piece
  EXPO lacks. https://github.com/larisa-soldatova/HELO · https://pmc.ncbi.nlm.nih.gov/articles/PMC3632998/
- **SWAN** (Ciccarese, Clark): Hypotheses and Claims are both `ResearchStatement`s, and they **nest** —
  "a Hypothesis in one context may be re-used as a Claim in another." Evidence relations:
  `swanco:citesAsSupportingEvidence`, `citesAsRefutingEvidence`, `citesAsDiscussesEvidence`
  (SWAN Relationships 2.0: `swanrel:referencesAsSupportiveEvidence`, …).
  https://www.w3.org/TR/hcls-swan/

### 5.5 Where N:M is explicitly handled — the two models that solve our problem

#### Micropublications (Clark, Ciccarese, Goble, J Biomed Semantics 5:28, 2014)
Classes: `Representation` ⊃ `Sentence` ⊃ `Statement` ⊃ **`Claim`**, plus `Data`, `Method`
(⊃ `Procedure`, `Material`), `Qualifier` (⊃ `Reference`, `SemanticQualifier`), `Attribution`.
A `Claim` is the single principal Statement `arguedBy` a Micropublication.

Relations: **`supports` (explicitly TRANSITIVE)**, **`challenges`** (via `directChallenges` /
`indirectChallenges` = undercutting), `qualifiedBy`, `asserts`, `quotes`, `supportedBy`,
`supportedByMethod`, `elementOf`, `hasSupportGraphElement`, `hasChallengeGraphElement`.

**The construct that handles N:M is the SupportGraph — a DAG rooted at the Claim.** A DAG, not a tree:
multiple evidence nodes converge on one claim, and one `Data` or `Method` node is `elementOf` many
micropublications, so it fans out to many claims. Transitive closure over `supports` lets you walk any
claim down to its empirical base.

- https://pmc.ncbi.nlm.nih.gov/articles/PMC4530550/ · https://arxiv.org/abs/1305.3506

#### SEPIO (Monarch / ClinGen) — the reified evidence line
Three-node axis: **`assertion` — `evidence line` — `evidence item`.**

Properties (verified in OLS4):
`has_evidence_line` SEPIO:0000006 · `has_supporting_evidence_line` SEPIO:0000007 ·
`has_disputing_evidence_line` SEPIO:0000008 · `has_inconclusive_evidence_line` SEPIO:0000009 ·
`is_evidence_line_for` SEPIO:0000427 · `has_evidence_item` SEPIO:0000084 ·
`evidence_item_for` SEPIO:0000376 · `has_evidence` SEPIO:0000189 ·
`has_supporting_evidence` SEPIO:0000440 · `has_disputing_evidence` SEPIO:0000441 ·
**`evidence_line_strength` SEPIO:0000132** · **`evidence_line_strength_score` SEPIO:0000429** ·
**`evidence_direction` SEPIO:0000183** · `evidence_has_supporting_reference` SEPIO:0000124 ·
`evidence_has_supporting_activity` SEPIO:0000085.
SEPIO also has **`hypothesis` SEPIO:0000432** — "like an assertion, can be supported by evidence… but does
not express an agent's belief."

**The `evidence line` IS the reified N:M construct**, and it is the cleanest answer found in this entire
survey. SEPIO's own framing: cardinalities on the central axis let the model expand **horizontally**
(multiple evidence lines per assertion; multiple evidence items per line) and **vertically** (an evidence
item for one assertion is itself a prior assertion). Because the line is a first-class individual, it
carries its **own strength, direction, criterion, and provenance** — so the same evidence item can feed
differently-weighted lines for different assertions.

- https://obofoundry.org/ontology/sepio.html · https://github.com/monarch-initiative/SEPIO-ontology/wiki/SEPIO-Overview · https://www.ebi.ac.uk/ols4/ontologies/sepio

### 5.6 Ontology takeaway
EXPO and LABORS give rich hypothesis *taxonomy* and a deep experiment *tree*, but link hypothesis to
experiment only by part-of / tree containment, with no cardinality and no N:M — the same fusion crux is
trying to escape. **Micropublications (SupportGraph DAG) and SEPIO (reified evidence line) are the only
two that model it explicitly, and only SEPIO attaches strength and direction to the link itself.**

---
