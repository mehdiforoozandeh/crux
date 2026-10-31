---
name: prezit
description: >-
  Turn one crux anchor node and everything under it into a minimal, professional,
  self-contained HTML slide deck — the "here's what we found" update a research group gives —
  where every number on a slide traces to the vault — a hashed result file or a metrics
  address — and `crux deck --verify` can prove it still matches. Drives the engine's `crux
  deck` verbs (--json harvest, --verify, --refresh, --lint), fills the shipped template or
  build, and runs the refinement loop with the PI. Two arcs: the paper arc (default:
  motivation → method → results → discussion) and the tree arc (built from the crux tree).
  Use when a crux user wants slides from their vault. Triggers: "make a deck from q…",
  "present this subtree", "slides for the group meeting", "a deck for the lab meeting",
  "update my deck", prezit, crux presentation, crux slides.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.2"
  spec: ".spec/11-prezit.md"
---

# prezit — presentations from a subtree

One anchor, one story. The **body** of the deck is the anchor and everything under it; the
**intro** is built from the anchor's ancestors and the wiki pages they link. A hypothesis
anchor is legal and yields a shorter deck. No time-window, no multi-anchor: "what happened
this week" is answered by choosing the anchor whose subtree moved.

## The three-way split (who does what)

| part | who | what |
|---|---|---|
| `crux deck <anchor> --json` | engine | the entire story material, assembled deterministically |
| `assets/deck.html`, `examples/paper_deck/` | this skill's template and paper-arc build | all chrome: palette, fade, keyboard nav, progress, DOM-derived count, speaker notes |
| the deck's prose + charts | **you, the agent** | narrative selection, the hero figures, the bullets |
| `crux deck --verify/--refresh/--lint` | engine | proves numbers and sources match; repairs addressed values; checks the slide contract |

You never retype the chrome (copy the template), and you never let the engine author a
sentence — selection and phrasing are your whole job.

## Two arcs — the paper arc is the default

| arc | shape | numbers proved by | start from |
|---|---|---|---|
| **paper arc** (default) | motivation → method → results → discussion | `build_deck.py` embeds result files as DATA and records each file's sha256; `--verify` re-reads them | `examples/paper_deck/` |
| **tree arc** (the PI picks it) | title → lineage → question → method → results → answer, built from the tree as mapped below | `metrics.json` addresses, each checked by `--verify` | `assets/deck.html`, `examples/q1_scaling_deck.html` |

For the paper arc, read [`references/paper-arc.md`](references/paper-arc.md) before
drafting: its slide roles, style rules and build replace the tree-arc defaults below (the
mapping, numbers by role, no future-work slide). Everything else in this file applies to
both arcs.

## The mapping — what each crux object becomes (tree arc)

| crux object | role in the deck |
|---|---|
| ancestors of the anchor (root → parent) | grand motivation — the line of reasoning |
| wiki pages linked from anchor + ancestors | background for the intro |
| sibling questions | the map of the larger problem |
| **the anchor question** | the question slide; its `## Protocol` → the pre-registration note (rules fixed before any run) |
| child hypotheses | the bridge from question to method |
| RD pages (once the RD layer exists; `rd` is empty until then) | methods |
| findings (direction, confidence, why, evidence) + verifiables | the results claims, and the honest negatives |
| `results/<hid>/` artifacts | the figures |
| the anchor's own finding (its answer and confidence) | the answer / next-steps slide — dropped unless the anchor is settled (a strong Finding on it) |
| child states (open · leaning · settled · parked) | scope — executed vs open vs parked |

Shorthand: intro = wiki, methods = design (not implementation legwork), results = tree.

## Workflow

1. **Harvest.** `crux deck <anchor> --json` from inside the vault. On a large vault you may
   delegate the initial sweep to a read-only search subagent — it returns paths and
   structure only.
2. **Read end to end.** Every linked report under `results/<hid>/`, every finding, the
   anchor's own findings (its answer). Inventory the figures and the `metrics.json` addresses.
3. **Agree the arc with the PI before drafting.** Structured questions, each with a
   recommended default: paper arc (default) vs tree arc (offer it for a vault update built
   from a resolved subtree whose numbers carry `metrics.json` addresses); single arc vs
   mini-arc per sub-question; redesign figures from the result files vs reuse; which 1–3
   findings get a slide. Trivia (output path, framework)
   is stated, not asked.
4. **Draft.** Paper arc: copy `examples/paper_deck/deck_src.html` and `build_deck.py` to
   `<vault>/presentations/<anchor-id>/`, write the slides and the DATA reduction, and run
   the build. Tree arc: copy `assets/deck.html` to `<vault>/presentations/<anchor-id>/index.html`
   and fill the stubs (worked example: `examples/q1_scaling_deck.html`). Both worked
   examples are built on `skills/crux/examples/scaling_vault` q1, verify-green and lint-clean.
5. **Check.** `crux deck --verify <deck> --strict` and `crux deck --lint <deck>` until both
   are green (for the paper arc, `<deck>` is the built `index.html`). Then the manual pass: open from `file://`, walk every slide at 16:9, confirm
   nothing collides with the fixed footer and in-SVG text is room-legible.
6. **Refine with the PI.** Deck-building is a refinement loop by nature — "split that
   slide", "drop that model everywhere", "enlarge the figures" each must be a small local
   edit. That is why this is a skill, not a fire-and-forget agent.
7. **Re-presenting later:** rerun `build_deck.py` (paper arc) or `crux deck --refresh <deck>`
   (tree arc), then **re-read the prose around every changed number** — refresh fixes values; only a human fixes the sentence that
   interprets them ("clears the floor by +0.05" can be silently falsified by a correct
   refresh). `validate --check=decks` reports stale decks from the vault side.

## The addressing contract (non-negotiable)

Every number on a slide traces to the vault. In the paper arc the trace is the build: the
number is read from a result file whose sha256 the deck-sources manifest records
([`references/paper-arc.md`](references/paper-arc.md)). An address, below, is the other
trace; the tree arc uses it for every number, and the paper arc may use it too.
An addressed number carries **both** the cached value it renders and the address it
came from:

```js
{ src:'h1#task_a.delta', v: 3.3, lo: 1.9, hi: 4.7 }      // chart data
```
```html
<span data-src="h1#task_a.delta">+3.3</span>              <!-- a numeral in prose -->
<span data-derived="h1#a.x,h1#b.y">7.9</span>             <!-- computed; inputs checked -->
<span data-src="literal">95%</span>                       <!-- definitional constant -->
```

- Addresses resolve as `<hid>#<dotted.key.path>` → `results/<hid>/metrics.json`. The PI or
  the run harness writes `metrics.json`; **crux never computes it, and neither do you** —
  if a number you need has no address, ask for it to be added, don't invent it.
- A chart annotation comparing two cached values (a bar gap, a delta) must be **computed at
  render** from those values, never hand-typed — a cached display string is invisible to
  `--refresh` and rots.
- Figures are **inline SVG re-derived from `metrics.json`**, not embedded matplotlib PNGs.
  A PNG that must appear is base64-embedded.
- The deck lives at `<vault>/presentations/<anchor-id>/index.html`. It is **derived, not
  evidence**: never link it under any `## Artifacts` block.

## When the only artifact is a 10-panel PNG (one-panel extraction)

One figure = one claim: contribute the single panel that tells the story, rebuilt on its
own. Fallback ladder, in order:

1. First, **re-run the plotting code** when the report links it, extracting the one panel
   as SVG.
2. **Rebuild from the underlying table or `metrics.json`** with the template's chart
   scaffolds.
3. Last resort: **embed the cropped panel base64** and mark it visibly as an unverified
   figure — never present an unaddressed chart as if it were checkable.

## Content rules

- **One claim per slide**, stated in one sentence — a slide whose claim cannot be written
  in a sentence does not exist. Deck length is elastic; only the results section grows.
- **Keep the negatives.** An honest "this did not work, and here is the number" is often
  the most valuable slide. Never spun, never dropped.
- **The correct term, glossed on first use.** Say the term the field uses — null hypothesis,
  confound, pre-registration, 95% confidence interval, standard deviation, statistically
  significant, limitations — never a homemade stand-in for it ("the boring explanation",
  "rules locked", "within noise", "spread", "Doubts"). A term past what a science
  undergraduate easily follows gets a gloss of 10 words or fewer in the same line, on the
  slide where it first appears; a backup glossary may repeat it but never replaces it. Leads
  stay short, not simplified, and exact numbers back them for a specialist. `crux deck
  --lint` fails the known stand-ins.
- **Quantify → interpret → caveat.** Not "more data helps" but "+3.3 points, CI clear of
  zero — because the extra data lands where the model was thinnest — but at 1.4× the
  compute."
- **Show uncertainty** — the 95% confidence interval or the standard error (SE); a difference
  smaller than its SE is no finding.
- **Bullets are conclusions, not axis descriptions.**
- **Plain names on slides**: no abbreviated axis labels, terse check names, internal arm
  codes or task ids; say what the thing is or does. A plain name is never a simplified one:
  a technical term stays, glossed.
- **A mandatory decomposition is always shown**: when the project's rules split a metric
  into parts, every value of that metric on a slide carries its split.
- **Numbers by role (D5, tree arc):** motivation slides carry none; method slides carry addressed
  definitional constants only; result slides carry at least two addressed numbers; the
  answer slide introduces none of its own.
- **Pre-registration** (rules fixed before any result): surface the anchor's `## Protocol`
  when it has one.
- Tree arc: no background, related-work, or future-work slide unless asked.

## The slide contract

Every `<section class="slide">` carries a comment header: **job / source / numbers / cut**
(plus claim/shape where relevant). It is the override surface — the user's request wins
over every default, and when you deviate you **update the slide's contract header to
match**, so the deviation is a deliberate call rather than drift. `crux deck --lint` enforces the headers
and the 7-content-unit budget; footer overlap and projector fit stay on your manual
checklist.

## Technical spec (already encoded in the template — do not regress it)

One self-contained HTML file (in the paper arc, the built `index.html`): no CDN, no
framework, nothing for the viewer to build, opens by double-click
from `file://` and survives being emailed. Fade-only transitions with
`prefers-reduced-motion` honored; keyboard nav (`→ ← space Home End`); thin progress bar;
slide counter derived from the DOM; print stylesheet gives page-per-slide PDF via the
browser; optional speaker notes (`<aside class="notes">` in `<p>`) toggle with `n`. Color is semantic — one color per arm, defined once as CSS variables, reused
identically across chart, legend and bullets. In-SVG fonts are sized for a projector
(~1.5× laptop taste); chart height is capped in `vh` so a figure never crowds out its
caption bullets.
