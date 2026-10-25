# The lab arc

The lab arc is the deck a lab meeting gets for one experiment or a family of experiments:
**motivation → method → results → discussion**. It comes from a family of decks a PI approved
slide by slide, for an exploratory study whose readings had no verdict and no `metrics.json`
yet. Everything here overrides the tree-arc defaults in `SKILL.md`; the rest of `SKILL.md`
(one claim per slide, keep the negatives, the slide contract, the technical spec) still holds.

## Files

```
<vault>/presentations/<anchor-id or study slug>/
  deck_src.html    chrome + slides + render code, with exactly one __DATA__ token
  build_deck.py    reads the result files and writes index.html
  index.html       built; never edited by hand
```

Copy `assets/deck.html` to `deck_src.html` and replace its slide spine with the roles below.
The top comment of `deck_src.html` names the arc (`arc: lab`), every result directory the
numbers come from, and every typed design constant.

## Slide roles

Mark the section on every slide in the kicker:
`<div class="kicker"><span class="sec">Results</span>(a) the depth law</div>`.

| section | slides | job | numbers |
|---|---|---|---|
| title | 1 | the question as a headline; the scope in one line | run counts only |
| motivation | 1–4 | why this experiment; what failed before, as a figure from the earlier results; the question | earlier results are allowed: they are the motivation; each comes from DATA |
| method | 2–5 | the design as schematics; the **grid of arms** (the deck's one table); what is scored, with its decomposition and the noise rule; the references and controls (baselines, no-covariate twins) | design constants only |
| results | one per claim, labelled (a), (b), … | the headline states the claim; the figure proves it | at least two, from DATA |
| discussion | 2–3 | what is ruled in and ruled out; the doubts, each with its count; an **options** slide when the PI will pick the next phase from the deck | restated from results; none new |
| backup | optional, after a divider | glossary, every cell, detail moved out of the main arc | from DATA |

The options slide lists labelled options (Option 1, Option 2, …), each with its cost and
what it would teach. Options carry no recommendation and no ranking; the PI chooses.

## Style rules

- **Figures over text.** Draw a schematic wherever the idea can be drawn: the design, the
  pairs that are scored, the data flow. A table appears only for a grid concept (the grid
  of arms, a readings grid). Keep text low, and write explanations basic enough for a lab
  member who does not know the design.
- **Speaker notes on every slide**: `<aside class="notes">` inside the section, written in
  `<p>`. The `n` key shows them; print puts them under each slide. Notes carry the detail
  the slide leaves out.
- **Label every panel** (a), (b), … and divide multi-panel figures with a visible rule or
  gap. Name the model version in each chart's title or legend ("one g per track" against
  "one g across tracks"), not only in a footnote.
- **Plain names everywhere on a slide.** Write the plain name for every axis, check, arm and
  piece of work: "control fraction", not "ctlfrac"; "the encoder-decoder with a learned
  decoder", not an internal arm code; what the work does, not its task id. A term the deck
  needs goes in a backup glossary.
- **The noise rule is on the slide.** Show the seed spread with every value. A gap counts
  only when it is above 2× the larger seed spread; label every smaller gap "within noise"
  and keep it on the slide. Quantify, then interpret, then caveat.
- **A mandatory decomposition is always shown.** When the project defines one for a metric
  (for example CRPS split into its oracle-scaled part and its scale-error part), every value
  of that metric appears with its split. Read the project's instructions (`CLAUDE.md`,
  `AGENTS.md`, its quoting rules) for such rules before drafting.
- **Readings, not verdicts**, while the study is exploratory. A verdict slide needs an
  approved synthesis, exactly as in the tree arc.

## Numbers come from the build script

An exploratory study has no `metrics.json` addresses, so `crux deck --verify` has nothing to
prove. The build script takes its place: every number on a slide is read from a result file
by `build_deck.py` and embedded as DATA, and the render code fills every numeral, in charts
and in prose, from DATA. The only typed numbers are design constants, listed in the top
comment.

```python
"""Rebuild index.html from deck_src.html by embedding the numbers as DATA.
Inputs: <every result file read below, one line each, with what it holds>."""
import csv, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
R = HERE.parent.parent / "results" / "<hid or study>"
tsv = lambda p: list(csv.DictReader(open(p), delimiter="\t"))
data = {"fit": [[r["arm"], float(r["crps"]), float(r["oracle_scaled"]), float(r["scale_error"])]
                for r in tsv(R / "fit_table.tsv")]}          # reduce here, never in the HTML
src = (HERE / "deck_src.html").read_text()
assert src.count("__DATA__") == 1
(HERE / "index.html").write_text(src.replace("__DATA__", json.dumps(data, separators=(",", ":"))))
```

In `deck_src.html`: `const DATA = __DATA__;`. A computed comparison (a gap, a ratio, an
"N of M") is computed in the render code from DATA, never typed. After any result file
changes, rebuild, then re-read the prose around every number that moved.

When the vault does carry addresses for some numbers, address those as in `SKILL.md` and
keep `--verify` green; the build script covers the rest. `crux deck --lint` applies to every
lab deck: each slide keeps its contract header (job, source, numbers, cut).

## The review loop

The PI reviews the deck slide by slide, one question at a time. Answer each question
tersely, make each requested change as a small local edit, rebuild, and update the slide's
contract header when the change departs from its role above.
