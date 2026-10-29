# The paper arc (the default)

The paper arc runs in the order of a research paper: **motivation → method → results →
discussion**. It fits one experiment or a family of experiments presented at a lab meeting,
and it works before any `metrics.json` exists. It comes from a family of decks that a PI
approved slide by slide during an exploratory study. Everything here replaces the tree-arc
defaults in `SKILL.md`. The rest of `SKILL.md` still holds: one claim per slide, keep the
negatives, the slide contract and the technical spec.

## Files

Start from the worked example `examples/paper_deck/`, built on `scaling_vault` q1. Copy its
`deck_src.html` and `build_deck.py`, then replace the slides, the DATA reduction and the
input list.

```
<vault>/presentations/<anchor-id or study slug>/
  deck_src.html    chrome, slides and render code; <meta name="prezit-arc" content="paper">;
                   exactly one __DATA__ and one __SOURCES__ token
  build_deck.py    reads the result files, writes index.html with DATA and the manifest
  index.html       built output; never edit it by hand
```

The top comment of `deck_src.html` names the arc and the result directories the numbers come
from, and it lists every typed design constant.

## Slide roles

Mark the section on every slide in the kicker:
`<div class="kicker"><span class="sec">Results</span>(a) the harder task</div>`.

| section | slides | job | numbers |
|---|---|---|---|
| title | 1 | the question as a headline; the scope in one line | run counts only |
| motivation | 1–4 | why this experiment; what failed before, as a figure from the earlier results; the question | earlier results are allowed because they are the motivation; each comes from DATA |
| method | 2–5 | the design as schematics; the **grid of arms** (the deck's one table); the outcome measure, with its decomposition and the significance criterion; the references and controls (baselines, no-covariate twins) | design constants only |
| results | one per claim, labelled (a), (b), … | the headline states the claim; the figure proves it | at least two, from DATA |
| discussion | 2–3 | what is ruled in and ruled out; the limitations, each with its count; an **options** slide when the PI will pick the next phase from the deck | restated from results; none new |
| backup | optional, after a divider | glossary, every cell, detail moved out of the main arc | from DATA |

The options slide shows labelled options (Option A, Option B, …). Each option gives its
cost and what it would teach. Options carry no recommendation and no ranking, because the
PI chooses.

## Style rules

- **Figures over text.** Draw a schematic wherever the idea can be drawn: the design, the
  pairs that are scored, the data flow. Use a table only for a grid concept, such as the
  grid of arms or a readings grid. Keep text low. Explain the design so that a lab member
  who does not know it can follow, in the field's own terms.
- **The correct term, glossed on first use.** Write the technical term — pre-registration,
  95% confidence interval, standard deviation, statistically significant, confound,
  limitations — never a homemade stand-in ("rules locked", "the interval", "within noise",
  "spread", "Doubts"). A term past what a science undergraduate easily follows gets a gloss
  of 10 words or fewer in the same line, on the slide where it first appears: "pre-registered
  (fixed in writing before any run)". `crux deck --lint` fails the known stand-ins.
- **Speaker notes on every slide**: `<aside class="notes">` inside the section, written in
  `<p>`. Write no digits in the notes; a number goes in through a DATA-filled span. The `n`
  key shows the notes, and print puts them under each slide. `crux deck --lint` fails a
  paper-arc slide that has no notes.
- **Label every panel** (a), (b), … and divide multi-panel figures with a visible rule or
  gap. Name the model version in each chart's title or legend ("one g per track" against
  "one g across tracks"), not only in a footnote.
- **Plain names everywhere on a slide.** Write the plain name of every axis, check, arm
  and piece of work: "control fraction", not "ctlfrac"; "the encoder-decoder with a learned
  decoder", not an internal arm code; what the work does, not its task id. A plain name is
  not a simplified one: a technical term stays, glossed where it first appears. A backup
  glossary may repeat the glosses; it never replaces them.
- **The significance criterion is on the slide.** Show the 95% confidence interval, or the
  standard deviation across seeds, with every value. A difference counts only when it meets
  the criterion: its confidence interval excludes zero, or it is above 2× the larger standard
  deviation across seeds, or above whatever threshold the project sets. Label every smaller
  difference by what it fails — "not significant (CI includes zero)" or "below the noise
  floor (2× the seed standard deviation)" — and keep it on the slide. Quantify, then
  interpret, then caveat.
- **A mandatory decomposition is always shown.** When the project defines one for a metric
  (for example CRPS split into its oracle-scaled part and its scale-error part), every
  value of that metric appears with its split. Before drafting, read the project's
  instructions (`CLAUDE.md`, `AGENTS.md`, its quoting rules) for such rules.
- **Readings, not verdicts**, while the study is exploratory. A verdict slide needs an
  approved synthesis, as in the tree arc.

## Numbers come from the build, and verify checks the build

`build_deck.py` reads every number from a result file and embeds it as DATA. The render
code fills every numeral from DATA, in charts and in prose. Computed comparisons (a gap, a
swing, "N of M", "not significant") are computed in the render code and are never typed. The
build also writes the **deck-sources manifest**, which maps each file it read
(vault-relative path) to the sha256 of that file:

```html
<meta name="prezit-arc" content="paper">
<script type="application/json" id="deck-sources">__SOURCES__</script>
...
const DATA = __DATA__;
```

```python
read = []                                  # every file the build opens, via load()
def load(rel):
    p = VAULT / rel; read.append(p); return json.loads(p.read_bytes().decode("utf-8"))
# ... reduce into `data` here, never in the HTML ...
read += [HERE / "build_deck.py", HERE / "deck_src.html"]   # the build and the page too
sources = {p.relative_to(VAULT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in read}                  # POSIX paths: the same manifest on every OS
src = (HERE / "deck_src.html").read_bytes().decode("utf-8")
out = src.replace("__SOURCES__", json.dumps(sources, sort_keys=True))
out = out.replace("__DATA__", json.dumps(data, separators=(",", ":")))
(HERE / "index.html").write_bytes(out.encode("utf-8"))      # UTF-8 and "\n" everywhere
```

`crux deck --verify index.html` re-reads every manifest file and checks it:

- **missing** — the file is not in this vault: unresolvable. The deck cannot be checked
  here, for example in a worktree whose `results/` is not synced.
- **changed** — the file differs from the one the deck was built from: a mismatch. Rerun
  `build_deck.py`, then re-read the prose around every number that moved.
- **unbuilt** — `deck_src.html` still holds `__SOURCES__`: unresolvable. Verify the built
  `index.html`. `validate --check=decks` skips unbuilt source pages.
- **no manifest** — a deck that declares the paper arc and carries no manifest:
  unresolvable.

`--strict` still fails any numeral typed into slide text or notes. Mark design constants
with `data-src="literal"`. Any number that has a `metrics.json` address can also carry it
(`data-src="h1#…"`) and is checked as in the tree arc. `crux deck --refresh` does not
rebuild a paper deck: it says so, and you rerun `build_deck.py`.

## The review loop

The PI reviews the deck slide by slide, one question at a time. Answer each question
tersely, make each requested change as a small local edit, rebuild, and update the slide's
contract header when the change departs from its role above.
