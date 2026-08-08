# Spec 11 — prezit: presentations from a subtree

**Label:** `prezit` · **Status:** ☐ todo
**Depends on:** [06 node economy](06-node-economy.md) (the `--json` CLI convention)
**Enriched by:** [07 RD layer](07-rd-layer.md) (the methods source) · [03 LLM wiki](03-llm-wiki.md) (the intro source)

## Goal

Turn one anchor node and everything under it into a minimal, professional, self-contained
HTML slide deck — the "here's what we found this week" update a research group gives
internally — where **every number on a slide is an address into the vault, not a photocopy of
one**, and a checker can prove it still matches.

## Motivation

### A crux vault already contains a paper

The narrative for the talk is already written; it is just spread across node prose, findings,
syntheses, wiki pages and report artifacts. Presenting it today means re-reading all of it and
hand-assembling a deck. That is what produced the reference deck (§ Reference implementation),
over a long session — and the result was good precisely because a fixed method was followed.
That method is reproducible. It should not be re-derived by every agent that gets asked.

### The recurring-presentation problem is what makes it a tool and not a prompt

A one-off deck is a chore. The real cost is that the *same subtree gets presented repeatedly* —
group meeting, committee update, collaborator sync — as it evolves. Every re-presentation is
where hand-transcribed numbers rot: the report gets re-run, the slide does not know it exists
downstream of anything, and a stale value is presented as current. A number on a slide looks
equally true whether it is fresh or eight versions old.

This is the same failure the whole vault exists to prevent, one layer out.

### Evidence

The reference deck carries 36 hand-typed numbers in one forest plot alone, none of them
checkable. Meanwhile [§7 of the playbook](#reference-implementation) lists *"numbers on a slide
with no traceable source"* as an anti-pattern. The tool that automates the deck has to close
that gap or it automates the anti-pattern.

## The mapping — what each crux object becomes

Internalize this before touching a slide. Everything downstream is applying it.

| crux object | role in the deck |
|---|---|
| ancestors of the anchor (root → parent) | grand motivation — the line of reasoning, how we got here |
| wiki pages linked from the anchor + ancestors | background for the intro — where the field is |
| sibling questions | the map of the larger problem the anchor sits inside |
| **the anchor question** | the question slide, and its pre-registered protocol → the "rules locked up front" note |
| child hypotheses | the bridge from question to method — each a testable claim |
| RD pages ([07](07-rd-layer.md)) linked from the anchor/children | **methods** — estimand, design, evaluation, notation |
| verifiables + ticks + findings | the results claims, and the honest negatives |
| `results/<hid>/` artifacts | the figures |
| approved synthesis (`s*`) | the verdict / next-steps slide |
| child states (idea/staged vs done) | scope — executed vs parked ("we only ran the first batch") |

The user's own shorthand for this was *intro = wiki, methods = tasks, results = tree*. The
methods slot is **RD, not taskhub** — taskhub ([08](08-taskhub.md)) holds implementation
legwork ("prep the cohort", "fix the runner"), which never appears in a paper's Methods
section. Methodology, high-level design, data, evaluation, modelling and notation are exactly
what 07 exists to hold.

## Design

### 1. Selector — one anchor, always

```bash
crux deck q20            # the deck is about q20 and its descendants
```

The **body** of the deck is the anchor and everything under it. The **intro** is built from
the anchor's ancestors and the wiki pages they link. The anchor is usually a question; a
hypothesis anchor is legal and produces a shorter deck (no lineage-of-children slide).

No time-window or multi-anchor selector. One deck tells one story; "what happened this week"
is answered by choosing the anchor whose subtree moved. (Rejected alternative below.)

### 2. Three-way split (rule 1 of [09](09-specialized-agents.md))

| part | who | what |
|---|---|---|
| `crux deck <anchor> --json` | **engine** | the entire story material, assembled deterministically |
| `assets/deck.html` | **skill template** | chrome: CSS, palette tokens, fade transitions, keyboard nav, progress bar, DOM-derived slide count |
| the deck's prose + charts | **agent** | narrative selection, the 1–2 hero figures, the bullets |
| `crux deck --verify` | **engine** | proves every number still matches the vault |

The reference deck is ~90% boilerplate. The agent should never retype it, and never author a
sentence of the harvest.

### 3. prezit is a **skill**, not an agent

Rule 5 of [09](09-specialized-agents.md): *a reusable prompt that needs main-conversation
context is a Skill.* Deck-building is a refinement loop by nature — the reference deck went
through "explain that before adding it", "split the method slide in two", "enlarge the
figures", "drop that model everywhere", "cut a slide". Every one of those needs the
conversation. A fire-and-forget agent produces a deck nobody wants to edit.

The one part that *is* agent-shaped is the initial vault sweep on a large vault, which may be
delegated to a read-only search subagent — it only needs to return paths and structure.

### 4. The payload — `crux deck <anchor> --json`

Assembled from vault state only; no text authored by the calling agent. Reuses the primitives
behind `snapshot()` (`engine.py`).

```jsonc
{
  "engine_version": "…",
  "anchor":   { "id","type","title","status","question","protocol","answer_so_far" },
  "lineage":  [ { "id","title","status","answer_so_far" } ],   // root → parent, in order
  "siblings": [ { "id","title","status" } ],
  "children": [ { "id","type","title","state","verdict","metric",
                  "verifiables": [ { "text","tick","found","failure_scenario" } ],
                  "findings","artifacts": [ { "label","path","kind" } ] } ],  // recursive
  "wiki":     [ { "slug","title","path" } ],   // linked from anchor + ancestors
  "rd":       [ { "slug","title","path" } ],   // empty until 07 lands
  "synthesis":{ "id","approved","text" } | null,
  "scope":    { "executed": n, "parked": n, "by_state": {…} },
  "figures":  [ { "hid","path","ext","bytes","caption" } ],  // every file under results/<hid>/
  "metrics":  [ { "addr","value","ci","n","unit" } ]         // every resolvable address, see §5
}
```

**Deterministic**: same vault state → byte-identical output. No timestamp in the payload; the
generation stamp belongs in the rendered deck, not the audit surface.

### 5. The traceability contract — the load-bearing part

#### 5a. `results/<hid>/metrics.json`

A new **optional** convention, required only for values that appear on a chart or as a numeral
in slide prose. Nested JSON; every leaf is an object:

```json
{
  "task_a": {
    "delta":     { "value": 3.3,  "ci": [1.9, 4.7], "n": 3, "unit": "points" },
    "data_arm":  { "value": 49.6, "n": 3, "unit": "accuracy" },
    "model_arm": { "value": 46.3, "n": 3, "unit": "accuracy" }
  }
}
```

Required leaf key: `value`. Optional: `ci`, `se`, `n`, `unit`. Anything else is carried through
untouched. The PI (or the run harness) writes this file; crux never computes it.

#### 5b. Addresses

Address form is `<hid>#<dotted.key.path>` — vault-relative by construction, short enough to
sit inline:

```
h1#task_a.delta   →   results/h1/metrics.json  ·  key path  task_a.delta
```

#### 5c. Both the address and the value live in the deck

A deck must open by double-click and survive being emailed, so it cannot fetch anything at
render time. Therefore each datum carries **the cached value it renders and the address it
came from**:

```js
// chart data
const ARMS = [
  { src:'h1#task_a.delta',        v: 3.3, lo: 1.9, hi: 4.7 },
  { src:'h2#equal_compute.delta', v:-4.6, lo:-6.0, hi:-3.2 },
];
```

```html
<!-- a numeral in prose -->
clears its own pre-registered bar of 2.0 points by
<span data-src="h1#task_a.delta">+3.3</span>
```

The cached value is the render; the address is the audit trail. Neither alone is sufficient.

#### 5d. `crux deck --verify <path-to-deck>`

Walks every `src` / `data-src` in the file, resolves it against the vault, compares. Reports
three buckets and exits non-zero on the first:

| bucket | meaning | exit |
|---|---|---|
| **mismatch** | address resolves, value differs | fail |
| **unresolvable** | no such hypothesis, file, or key path | fail |
| **derived** | `data-derived="h59#a,h59#b"` — a computed display value; its named inputs are checked, the result is not recomputed | pass, listed |
| **unsourced** | a numeral with no address | pass; fails under `--strict` |

**Implementation note, found while building the reference deck:** a chart's tick labels, value
labels and axis text are *generated* from its data array and are already covered by that
array's `src` entries. `--verify` must therefore scan the **source** for `src:` and `data-src`,
not the rendered DOM — scanning rendered text reports every chart numeral as unsourced. The
same applies to definitional prose constants that are conventions rather than vault values
("the 95% interval"); `--strict` needs an explicit escape (`data-src="literal"`) for those or
it will be unusable.

#### 5e. `crux deck --refresh <path-to-deck>`

Rewrites the cached `v`/`lo`/`hi` and the text inside `data-src` spans from current vault
values. Touches nothing else — prose, structure and charts are left alone. This is the
mechanical repair path that makes re-presenting the same subtree next month cheap instead of a
retype.

**`--refresh` must warn loudly**, listing each slide whose numbers moved, because prose that
*interprets* a number ("clears the floor by +0.05") can be silently falsified by a correct
refresh. Refresh fixes values; only a human can fix the sentence around them.

### 6. The narrative skeleton — and the slide contract

The template ships the spine as commented stubs. **Each stub carries a contract in its comment
header**: the slide's job, its vault source, its number policy, its shape rule, and what gets
cut first when it is full.

**Everything in this section is a default.** The user's request wins over any of it — different
slides, different order, different depth, different look. The contracts exist so that a
deviation is a deliberate call the agent records, rather than drift; when the user asks for
something else, the agent changes the slide and updates its contract header to match.

#### The spine

| # | slide | role | units | grows? |
|---|---|---|---|---|
| 1 | Title | the question as a headline + scope line | 3 | no |
| 2 | Lineage | root idea → what is settled → why the anchor is the honest next step | 4 | no |
| 3 | The question | concrete scenario, then the 1–2 precise sub-questions, then scope | 4 | no |
| 4a | Method · data & target | what goes in, what exactly is predicted | 4 | no |
| 4b | Method · design & scoring | how the claim was made falsifiable, how a verdict is reached | 4 | no |
| 5…n | Results | one claim each: a hero figure + mechanism + caveat | ≤7 | **yes** |
| n+1 | Verdict | what closes, what opens — dropped when there is no approved synthesis | 4 | no |

No background, related-work, or future-work slide unless asked.

#### The six defaults the contracts encode

**D1 — deck length is elastic.** No slide cap. The discipline is not brevity by count; it is
that **every slide states one claim, and a slide whose claim cannot be written in a sentence
does not exist.** A cap would force cramming as often as cutting.

**D2 — only the results section grows.** Lineage is always three chain nodes whatever the
ancestor depth (deep ancestry compresses into the middle node; it never adds a fourth box and
never spills to a second slide). The question is always one slide. Method is always two.
*Evidence earns length; setup does not* — motivation and method are where audience patience is
spent and where bloat is least defensible.

**D2b — one result slide per claim**, not per hypothesis and not per figure. A claim is a
sentence that could be false. Two figures may share a slide when they evidence one claim; one
figure may split across two slides when it carries two. Per-hypothesis is how the elastic deck
degenerates back into the talk this format exists to prevent; per-figure inverts the
dependency and lets the story be shaped by whichever plots happen to exist.

**D3 — depth budget: 7 content units per slide, hard.** A content unit is one visual block: a
chain node, a bullet, a table, a callout, a chart, a legend, a note, a prose lead. At most one
**heavy** unit — chart or table — per column. Vertical fit verified at 16:9 afterwards.
Countable, therefore lintable, unlike "looks about right".

**D4 — register by role.** Serif prose leads on narrative slides (title, question, verdict);
sans boxes and tables on structural slides (lineage, method); figure-first with sans bullets on
results. The typeface tells the audience what kind of slide they are looking at before they
read a word.

**D5 — numbers by role.** Motivation slides carry **none** — a number before the method is
stated is unearned, and it is the most quoted and least examined thing in any talk. Method
slides carry **definitional constants only** (n, seeds, splits). Result slides carry **at least
two addressed numbers, or they are not results.** The verdict slide may restate numbers already
addressed on a result slide and introduces none of its own.

D5 has a structural payoff: it makes "is this slide doing its job" checkable rather than a
matter of taste, and it is what forced verdicts off the method slide in the reference deck.

### 7. Content rules the skill enforces

- **One figure = one claim.** A 10-panel figure contributes the single panel that tells the
  story, rebuilt on its own.
- **Keep the negatives.** An honest "this did not work, and here is the number" is often the
  most valuable slide. Never spun, never dropped.
- **Dual register.** A plain-language lead a non-specialist grasps in one read, backed by exact
  numbers a specialist can check.
- **Quantify → interpret → caveat.** Not *"more data helps"* but *"+3.3 points, CI clear of
  zero — because the extra data lands where the model was thinnest — but at 1.4× the compute."*
- **Show uncertainty**, so a delta cannot be oversold; a gap smaller than the SE is not a gap.
- **Bullets are conclusions, not axis descriptions.**
- **"Rules locked before results"** — surface the pre-registered protocol when the anchor has
  one. It is what tells the audience nothing was decided after seeing a number.

### 8. Visual + technical spec

- **One self-contained HTML file.** No CDN, no framework, no build step. Opens by double-click.
- Light "paper" background, one restrained accent, generous whitespace, minimal chrome.
  **Fade-only** transitions. Keyboard nav (`→ ← space Home End`), thin progress bar, slide
  counter derived from the DOM.
- **Color is semantic**: one color per arm, reused identically across chart, legend and
  bullets; defined once as CSS variables.
- **Figures are inline SVG**, re-derived from `metrics.json`, not embedded matplotlib PNGs.
  A PNG that must appear is base64-embedded.
- **Room-legible**: in-SVG fonts ~1.5× what looks right on a laptop; result figures full-width
  (a two-column figure+text layout shrinks the chart ~40%); chart `max-height` capped in `vh`
  so a tall figure never crowds out its caption bullets; vertical fit checked at 16:9.
- **Built for editing**: one `<section class="slide">` per slide with a comment header, chart
  data in arrays at the top of each chart function, semantic classes (`.pts`, `.chartbox`,
  `.dtable`, `.target`). "Split this slide", "remove that model everywhere", "drop slide 7"
  must each be a small local edit.
- `prefers-reduced-motion` disables the fade.

### 9. Output location

```
<vault>/presentations/<anchor-id>/index.html
```

The deck lives **in** the vault but is **derived**, not evidence: it is not linked from any
`## Artifacts` block (that block is for what a run produced). `validate` gains a selectable
`--check=decks` that runs `--verify` over every deck under `presentations/` and reports
mismatches as warnings.

### 10. The skill

```
skills/prezit/
  SKILL.md
  assets/deck.html          # the template
  examples/                 # a reference deck built from examples/scaling_vault
```

Workflow the skill spells out: harvest (`crux deck --json`) → read the linked reports end to
end and inventory the figures → **agree the arc with the PI before drafting** (structured
questions with recommended defaults: single arc vs mini-arc per sub-question; redesign figures
vs reuse; which 1–3 findings get a slide) → draft → `--verify` → refine.

Trivia (output path, framework) is stated, not asked.

## Decisions

| decision | rationale |
|---|---|
| skill, not agent | rule 5 — deck-building is a refinement loop that needs the conversation |
| **D1** deck length elastic, no slide cap | a cap forces cramming as often as cutting; the real guard is one claim per slide |
| **D2** only results grow with the subtree | evidence earns length, setup does not — motivation is where bloat is least defensible |
| **D2b** one result slide per claim | per-hypothesis degenerates into the talk this format prevents; per-figure lets available plots dictate the story |
| **D3** 7 content units per slide, one heavy per column | countable, therefore lintable; it is what caught the overloaded method slide |
| **D4** register by slide role | the typeface signals what kind of slide this is before a word is read |
| **D5** numbers by slide role (none / definitional / ≥2) | makes "is this slide doing its job" checkable; forced verdicts off the method slide |
| every slide carries a contract in its comment header | it is the override surface — without it, "make mine different" has nothing to push against |
| one anchor, no time window | one deck tells one story; the weekly-meeting case is served by choosing the anchor whose subtree moved |
| body = anchor + descendants, intro = ancestors + wiki | matches how a paper motivates: zoom out, then zoom in |
| methods come from RD (07), not taskhub (08) | taskhub is implementation legwork; a paper's Methods section is design, data, evaluation, notation — which is what 07 holds |
| ships **before** 07; `rd` field empty until then | the report artifact is an adequate methods source today, and 07 is picked up for free later |
| deck carries **both** cached value and address | self-containment (email, double-click, no fetch) and traceability are both non-negotiable; neither alone gives both |
| `metrics.json` is optional, required only for charted/quoted numbers | forcing it everywhere would block adoption on vaults that have prose reports and nothing else |
| crux never computes `metrics.json` | rule: the engine is domain-agnostic and never parses logs or metrics |
| `--verify` is a separate invocation, not part of generation | a deck is edited by hand for weeks after generation; verification must be runnable at any point, including in `validate` |
| `--refresh` warns per-slide | a correct value refresh can silently falsify the sentence around it |
| template ships in the skill | the chrome is boilerplate; retyping it per deck is where drift and ugliness enter |
| deck is derived, not an evidence artifact | `## Artifacts` means "what the run produced" |
| inline SVG, not embedded PNG | the brief is "minimal and beautiful"; and an SVG re-derived from `metrics.json` is verifiable, a PNG is not |

## Rejected alternatives

- **prezit as a one-shot agent.** Fails rule 5. The reference deck needed five rounds of
  human-driven surgery; an agent that cannot see the conversation cannot do any of them.
- **A `--since 7d` / multi-anchor selector.** A week of work is often three unrelated
  subtrees, and three subtrees is three stories. Producing one deck from them either invents a
  narrative that does not exist or degrades into a status report — which is what `crux status`
  and the cockpit already are.
- **A slide framework** (reveal.js, Marp, Slidev). Every one needs a build step or a CDN,
  which breaks "opens by double-click and survives being emailed" — the property that makes a
  deck usable by a PI who is not going to run `npm install` before a group meeting.
- **Generating `.pptx`.** Loses inline SVG, the fade discipline, and the address/value
  contract. Kept as an open question for export, not as the primary format.
- **Live data fetch in the deck** (resolve addresses at render time). Cleanest traceability,
  and unusable: `file://` + CORS, and the deck stops working the moment it leaves the vault.
- **Regenerating the whole deck on every change.** This is the spec-kit `tasks.md` mistake
  ([08](08-taskhub.md) §1) applied to slides: regeneration destroys the hand-tuned narrative,
  which is the only part with real value. Hence `--refresh` touches values only.
- **Letting `crux deck` write slide prose.** The engine never judges. Selection and phrasing
  are the whole job the agent is there for.
- **A numeric cap on slides** (D1). Same reasoning as the verifiables cap in
  [09](09-specialized-agents.md): arbitrary, and it truncates instead of sharpening. Worse, a
  cap makes cramming the path of least resistance — the agent keeps the slide and shrinks the
  type, which is the projector-legibility failure §8 exists to prevent. "One claim per slide,
  stated in one sentence or the slide doesn't exist" is the real limiter.
- **Budgeting slide depth in words** (D3). Directly targets wordiness, which is the actual sin
  — but a table and a chart each cost near-zero words while dominating the slide, so the metric
  misses the real crowding. Content units catch both.
- **Requiring an addressed number on every slide** (D5). Maximises `--verify` coverage and
  makes the whole deck evidence-bound. Rejected because it manufactures numbers for slides
  whose job is framing, and a number on the motivation slide is the one nobody checks.

## Open questions

- **Who writes `metrics.json`?** Options: the run harness by convention; the agent at close
  time from the report; a `crux close --metrics <path>` flag that registers and validates it.
  Leaning toward the flag, so the file has a declared shape at the moment evidence is recorded.
- **Derived numbers.** `data-derived` checks that the inputs are current but cannot check the
  arithmetic. Is an allowlist of operations (ratio, difference, percent) worth the complexity,
  or is "inputs current, result unverified" honest enough?
- **One-panel extraction.** When the only artifact is a 10-panel PNG and there is no
  `metrics.json`, how does the agent rebuild one panel? Re-run the plotting code, read the
  underlying table, or fall back to embedding the crop and marking it unsourced?
- **Speaker notes.** Worth a `<aside class="notes">` + presenter view, or scope creep?
- **PDF export.** Print stylesheet (each slide a page) is nearly free; a real export verb is
  not.
- **Theming.** One palette, or a `--theme` that reads tokens from `.crux.yaml` so a lab can
  brand its decks?
- **Anchors with no children yet.** Should `crux deck` refuse, or emit a 3-slide "here is the
  question we are about to answer" deck? (A proposal deck is a real use case.)

## Work items

- ☐ `crux deck <anchor> --json` — deterministic payload assembly (aliases: `prezit`, `present`, `slides`)
- ☐ `results/<hid>/metrics.json` convention — schema, loader, address resolver (`<hid>#<dotted.path>`)
- ☐ `crux deck --verify <deck>` — buckets, exit codes, `--strict`
- ☐ `crux deck --refresh <deck>` — value rewrite + per-slide change warning
- ☐ `validate --check=decks` — verify every deck under `presentations/`
- ☑ `assets/11-prezit-reference.html` — worked example / template (chrome, palette tokens, slide
  stubs with contract headers, both chart-function scaffolds, addressing wired through)
- ☐ Promote it to `skills/prezit/assets/deck.html` when the skill is written
- ☐ Contract-header lint: every `<section class="slide">` has job / source / numbers / cut, and
  no slide exceeds 7 content units
- ☐ `skills/prezit/SKILL.md` — the mapping, the arc, the content rules, the refinement loop
- ☐ Reference deck built from `examples/scaling_vault`, shipped in `skills/prezit/examples/`
- ☐ `metrics.json` fixtures in the demo vault so selftest has something to resolve against
- ☐ `selftest.py` coverage (below)
- ☐ `ENGINE_VERSION` bump + migration proof (vaults with no `presentations/` and no
  `metrics.json` must load unchanged)

## Acceptance criteria

- `crux deck q1 --json` on the demo vault is **byte-identical across runs** and contains no
  text authored by a calling agent.
- The payload's `lineage` is ordered root → parent, and `children` is the full recursive
  subtree of the anchor.
- `rd` is present and empty on a vault with no RD layer; the command does not fail.
- A deck whose cached value has been edited to disagree with `metrics.json` **fails**
  `--verify` with a non-zero exit and names the address.
- An address pointing at a missing hypothesis, missing file, or missing key path fails
  `--verify` as *unresolvable*, distinctly from *mismatch*.
- `--verify --strict` fails on a numeral carrying no address; plain `--verify` passes it.
- After changing a value in `metrics.json`, `--refresh` updates the deck, `--verify` passes,
  and the refresh output names the slides whose numbers changed.
- `--refresh` leaves all non-numeric bytes of the deck unchanged (diff is values only).
- The generated deck loads from `file://` with no network requests and no console errors.
- Slide count in the deck's counter is derived from the DOM (delete a `<section>`, count drops).
- No slide exceeds 7 content units, and no slide's last element overlaps the fixed footer.
- Motivation slides (title, lineage, question) contain zero addressed numbers; every result
  slide contains at least two (D5).
- `--verify` reports zero unsourced numerals on the reference deck despite its charts rendering
  ~40 numerals, because it scans source `src:` / `data-src` rather than rendered SVG text.
- `validate --check=decks` reports a stale deck as a warning, not an error, and `validate`
  without the check ignores `presentations/` entirely.
- An existing pre-11 vault passes `validate --strict` with no migration.
- `selftest.py` passes with a grown assert count.

## Reference implementation

**[`assets/11-prezit-reference.html`](assets/11-prezit-reference.html)** — the worked example,
built on the anchor `q1` of `skills/crux/examples/scaling_vault`. Read it alongside this
document; it is the template the skill copies.

It demonstrates: the 8-slide spine with a contract header on every slide, both reusable chart
functions (a forest plot with intervals and a grouped bar chart), the full addressing contract
(12 chart addresses, 8 prose `data-src` spans, 1 `data-derived` — one live example per verify
bucket), fade-only transitions, keyboard nav, and a DOM-derived slide count. Verified at
1440×810: loads from `file://` with no network requests and no console errors, no slide
overflows, nothing collides with the fixed chrome.

`q1` was chosen as the anchor because its three hypotheses closed **supported / partial /
refuted** — so the negative result gets a slide, which is the honest-reporting rule the format
cares most about.

The deck this spec was distilled from lives in a private vault and does not ship. Every number in
this spec and in the reference deck is synthetic demo data for `examples/scaling_vault`, which is
committed here and public. **No real research result enters this repo — not in a spec, not in an
example, not in a comment.**
