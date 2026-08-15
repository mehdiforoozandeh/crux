---
name: prezit
description: >-
  Turn one crux anchor node and everything under it into a minimal, professional,
  self-contained HTML slide deck — the "here's what we found" update a research group gives —
  where every number on a slide is an address into the vault, not a photocopy of one, and
  `crux deck --verify` can prove it still matches. Drives the engine's `crux deck` verbs
  (--json harvest, --verify, --refresh, --lint), fills the shipped template, and runs the
  refinement loop with the PI. Use when a crux user wants slides from their vault. Triggers:
  "make a deck from q…", "present this subtree", "slides for the group meeting", "update my
  deck", prezit, crux presentation, crux slides.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
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
| `assets/deck.html` | this skill's template | all chrome: palette, fade, keyboard nav, progress, DOM-derived count |
| the deck's prose + charts | **you, the agent** | narrative selection, the hero figures, the bullets |
| `crux deck --verify/--refresh/--lint` | engine | proves numbers match; repairs values; checks the slide contract |

You never retype the chrome (copy the template), and you never let the engine author a
sentence — selection and phrasing are your whole job.

## The mapping — what each crux object becomes

| crux object | role in the deck |
|---|---|
| ancestors of the anchor (root → parent) | grand motivation — the line of reasoning |
| wiki pages linked from anchor + ancestors | background for the intro |
| sibling questions | the map of the larger problem |
| **the anchor question** | the question slide; its `## Protocol` → the "rules locked up front" note |
| child hypotheses | the bridge from question to method |
| RD pages (once the RD layer exists; `rd` is empty until then) | methods |
| verifiables + ticks + findings | the results claims, and the honest negatives |
| `results/<hid>/` artifacts | the figures |
| approved synthesis | the verdict / next-steps slide — dropped when none is approved |
| child states (idea/staged vs done) | scope — executed vs parked |

Shorthand: intro = wiki, methods = design (not implementation legwork), results = tree.

## Workflow

1. **Harvest.** `crux deck <anchor> --json` from inside the vault. On a large vault you may
   delegate the initial sweep to a read-only search subagent — it returns paths and
   structure only.
2. **Read end to end.** Every linked report under `results/<hid>/`, every finding, the
   approved synthesis. Inventory the figures and the `metrics.json` addresses.
3. **Agree the arc with the PI before drafting.** Structured questions, each with a
   recommended default: single arc vs mini-arc per sub-question; redesign figures from
   `metrics.json` vs reuse; which 1–3 findings get a slide. Trivia (output path, framework)
   is stated, not asked.
4. **Draft.** Copy `assets/deck.html` to `<vault>/presentations/<anchor-id>/index.html` and
   fill the stubs. Study `examples/q1_scaling_deck.html` — it is the worked example, built
   on `skills/crux/examples/scaling_vault` q1, verify-green and lint-clean.
5. **Check.** `crux deck --verify <deck> --strict` and `crux deck --lint <deck>` until both
   are green. Then the manual pass: open from `file://`, walk every slide at 16:9, confirm
   nothing collides with the fixed footer and in-SVG text is room-legible.
6. **Refine with the PI.** Deck-building is a refinement loop by nature — "split that
   slide", "drop that model everywhere", "enlarge the figures" each must be a small local
   edit. That is why this is a skill, not a fire-and-forget agent.
7. **Re-presenting later:** `crux deck --refresh <deck>`, then **re-read the prose around
   every changed number** — refresh fixes values; only a human fixes the sentence that
   interprets them ("clears the floor by +0.05" can be silently falsified by a correct
   refresh). `validate --check=decks` reports stale decks from the vault side.

## The addressing contract (non-negotiable)

Every number the vault owns carries **both** the cached value it renders and the address it
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
- **Dual register**: a plain-language lead a non-specialist grasps in one read, backed by
  exact numbers a specialist can check.
- **Quantify → interpret → caveat.** Not "more data helps" but "+3.3 points, CI clear of
  zero — because the extra data lands where the model was thinnest — but at 1.4× the
  compute."
- **Show uncertainty**; a gap smaller than the SE is not a gap.
- **Bullets are conclusions, not axis descriptions.**
- **Numbers by role (D5):** motivation slides carry none; method slides carry addressed
  definitional constants only; result slides carry at least two addressed numbers; the
  verdict slide introduces none of its own.
- **"Rules locked before results":** surface the anchor's `## Protocol` when it has one.
- No background, related-work, or future-work slide unless asked.

## The slide contract

Every `<section class="slide">` carries a comment header: **job / source / numbers / cut**
(plus claim/shape where relevant). It is the override surface — the user's request wins
over every default, and when you deviate you **update the slide's contract header to
match**, so the deviation is a deliberate call rather than drift. `crux deck --lint` enforces the headers
and the 7-content-unit budget; footer overlap and projector fit stay on your manual
checklist.

## Technical spec (already encoded in the template — do not regress it)

One self-contained HTML file: no CDN, no framework, no build step, opens by double-click
from `file://` and survives being emailed. Fade-only transitions with
`prefers-reduced-motion` honored; keyboard nav (`→ ← space Home End`); thin progress bar;
slide counter derived from the DOM; print stylesheet gives page-per-slide PDF via the
browser. Color is semantic — one color per arm, defined once as CSS variables, reused
identically across chart, legend and bullets. In-SVG fonts are sized for a projector
(~1.5× laptop taste); chart height is capped in `vh` so a figure never crowds out its
caption bullets.
