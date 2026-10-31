---
name: storify
description: >-
  Write one crux anchor (a question and everything under it, or one hypothesis after its
  run) as a short private paper: a PDF of at most 4 pages in the Springer Nature article
  template, read only by the PI. Every number is a LaTeX macro that a stdlib build reads
  from the vault's result files, and `crux story --verify` proves that the paper still
  matches them. Use when a crux user wants a written account of their results. Triggers:
  storify, "write this up", "a short paper on q…", "write up the experiment", "a paper
  version of this", crux paper, crux write-up.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
---

# storify — a short private paper from a subtree

One anchor gives one paper. The anchor is a question with its subtree, or one hypothesis
after its run. A hypothesis anchor gives a shorter paper; its motivation comes from the
parent question. The only reader is the PI, alone. The paper is prezit's paper arc, written
as prose for one reader instead of slides for a room.

## Files

Start from `assets/`. The worked example `examples/q1_story/` is built on
`skills/crux/examples/scaling_vault` question q1. Read its `story_src.tex` and
`build_story.py` before you draft.

```
<vault>/stories/<anchor-id>/
  story_src.tex      you write this; it holds the two build tokens
  build_story.py     stdlib only; reads the result files and writes story.tex
  story.tex          BUILT; never edit it by hand
  story.pdf          from `latexmk -pdf story.tex`
  sn-jnl.cls, sn-mathphys-num.bst   copied from assets/, so the folder compiles alone
  references.bib     optional; only sources the vault already holds
```

## Workflow

1. **Harvest.** Run `crux story <anchor> --json` from inside the vault. It is the same
   harvest as `crux deck`.
2. **Read end to end.** Read every report under `results/<hid>/`, every finding, the
   anchor's own findings (its answer) if it has any, and the wiki pages the anchor and its ancestors link.
   Read the project's own rules (`CLAUDE.md`, `AGENTS.md`) for a mandatory decomposition or
   a significance threshold. Inventory every number you need and the file that holds it.
   Done when each claim you will make has a result file behind it. For a hypothesis
   anchor, also read the hypothesis's own file: the harvest omits its problem statement.
3. **State the scope and draft.** Tell the PI the scope in one line ("a short paper on
   <the anchor's title>, from <what was run>"). Then draft at once. Do not ask
   questions first: the PI is the only reader, and they redirect the draft after they read
   it. Copy `assets/` into `<vault>/stories/<anchor-id>/` and write `story_src.tex` and the
   REDUCE block of `build_story.py`.
4. **Build.** `python3 build_story.py`. It finds the vault by walking up to the folder that
   holds `META.md` (or takes the vault path as its first argument).
5. **Compile.** `latexmk -pdf story.tex` in the story folder. When `latexmk` is missing,
   stop here: tell the PI the folder is ready, and that `latexmk -pdf story.tex` compiles it,
   or that they can upload the whole folder to Overleaf.
6. **Check.** Run `crux story --verify story.tex --strict` and `crux story --lint story.tex`
   from inside the vault, and fix the source until both exit 0. Lint reads `story.log` for
   the page count, so compile before you lint.
7. **Read the PDF.** Render each page (`pdftoppm -r 80 -png story.pdf p`) and look at it.
   Check that every figure renders, nothing overflows the margin, no label collides with
   another, and every technical term is glossed on first use. Then give the PI the path to
   `story.pdf`.
8. **Refine on request.** Make each change the PI asks for as a small local edit, rebuild,
   recompile, and check again.
9. **Re-read later.** When the PI returns to a story, rerun `build_story.py` and recompile.
   Then re-read the prose around every number that moved. The build fixes the value; only
   you can fix the sentence that interprets it ("the gain is significant" can become false
   after a correct rebuild). `crux validate --check=decks` reports a stale story.

## The arc

Four sections, with these exact titles, in this order. The lint fails any other top-level
`\section`. Use `\paragraph{...}` or `\subsection` inside a section as you need.

| section | job | numbers |
|---|---|---|
| abstract | 3–4 sentences: the question, the design, the answer with its main number and its uncertainty, the main limitation | the headline result only |
| `Motivation and background` | why the question matters, what is known, what was missing; end on the question in one sentence | none of this study's results |
| `Methods` | the design as a schematic, the arms by plain name, the outcome measure with its decomposition, the significance criterion, what was pre-registered | design constants only |
| `Results and discussion` | one paragraph per claim, each with its figure panel; the negative results | the measured values, each with its uncertainty |
| `Conclusion` | the answer, the limitations, then the next-step options | restated only; none new |

The conclusion lists the next-step options. Each option gives its cost and what it would
teach. Give no ranking and no recommendation, because the PI chooses.

**Readings, not verdicts.** State the answer as settled only when the anchor is settled
(a strong Finding on it). Otherwise write what the results suggest, and say what would settle it.

**A hypothesis anchor.** Take the motivation from the parent question's own text, not from
its current answer: that answer can give away the results of later experiments. When a later
experiment under the same parent qualifies this result, name it in the conclusion as a
limitation, in words, without its numbers. Before you list the next-step options, read the
parent's other hypotheses and drop every option that was already run. A parent's settled
answer does not make this one result settled.

## Length

- At most **1,200 words** of body text. The abstract and the title count. Figures, tables,
  captions, TikZ and pgfplots code, and the references do not.
- At most **4 PDF pages** in total, references included.
- Cut words before you cut a negative result or an uncertainty.

## Voice

The paper reads like a short journal article written for one expert.

- **The correct term, glossed on first use.** Write the term the field uses (null
  hypothesis, confound, pre-registration, 95% confidence interval, standard deviation,
  statistically significant, limitations), never a homemade stand-in for it ("the boring
  explanation", "rules locked", "within noise", "spread"). A term past what a science
  undergraduate easily follows gets a gloss of 10 words or fewer in the same sentence where
  it first appears: "pre-registered (fixed in writing before any run)". The lint fails the
  known stand-ins.
- **No node ids and no crux vocabulary, anywhere in the PDF**: title, abstract, body,
  captions, axis labels and TikZ labels. Name an experiment by what it tested, not by its
  id. Write the science, not the bookkeeping: say "pre-registered threshold", never
  "verifiable"; say "the result", never "the verdict". The lint does not read TikZ or
  pgfplots code, so check the labels in figures yourself.
- **Plain names** for arms, axes and checks: "the data arm, a smaller convolutional network
  on twice the data", not an arm code. A plain name stays technical; it is never simplified.
- **Quantify, then interpret, then caveat.** "The data arm led by +3.3 points (95% CI 1.9
  to 4.7), because …, but each arm ran at its own cost."
- **Keep the negatives.** A result that did not hold stays in the paper, with its number.
- **Show the significance criterion** in Methods, and show the 95% confidence interval or
  the standard deviation across seeds with every compared value. Label a difference that
  fails the criterion by what it fails: "not statistically significant (the interval
  includes zero)".
- **A mandatory decomposition is always shown.** When the project splits a metric into
  parts, every value of that metric appears with its split.

`% crux-allow: tree, node` in the preamble licenses a lexicon word that the field uses in
its own sense ("decision tree", "graph node", "logic gate"). Use it only for that. Never
use it for crux's own process words, and never to let a node id through (it cannot).

## Numbers

Every number in the prose, the captions and the tables comes from the build. The prose
never types a measured number.

- `build_story.py` reads each result file through `load(rel)`, which records the file. Its
  REDUCE block puts each number into `macros` and each chart's data into `tables`.
- The build writes one `\newcommand` per number (names are letters only: `\dFirstOwn`,
  never `\d1`) and one `\pgfplotstableread{...}\tblName` per table into the `% __DATA__`
  line. It writes the sha256 of every file it read into the `% crux-sources:` line.
- Format numbers in the build with `num(v, d, sign)`: decimals, a real minus sign, a plus
  sign on differences, thousands separators. The prose never formats a number.
- Compute every derived number in the build: a gap, a swing, "5 of 6 significant".
- A design constant typed in the prose is wrapped in `\lit{}`: `\lit{95}\% confidence
  interval`. List each `\lit{}` constant in the top comment of `story_src.tex`.
- `--strict` fails any other digit in the body, including captions, tables and math mode.
  Labels, references, citations, comments and TikZ/pgfplots code are exempt.
- A `thebibliography` block fails `--strict` (its years are digits). Cite with
  `\cite{key}` and a `references.bib`, and only cite a source the vault holds (its
  `wiki/.sources.tsv` or `raw/`).

When verify fails: **mismatch** means a source file changed, so rebuild and re-read the
prose around every moved number. **Unresolvable** means a file is missing (an unsynced
`results/`), or you verified `story_src.tex` (unbuilt) instead of `story.tex`.

## Figures

- **Methods: a TikZ schematic of the design.** Show the arms, what differs between them,
  what is shared, and how they are scored.
- **Results: pgfplots charts that read the build's tables**, with error bars from the
  result files (the confidence interval or the standard deviation across seeds). Draw a
  zero line on a chart of differences.
- **An existing result figure** (PNG or PDF under `results/<hid>/`) goes in with
  `\includegraphics` when it already shows the claim. Read it through `load()` in the build
  so that the manifest records its hash.
- Label the panels (a), (b) and refer to them in the prose. Use one colour per arm, defined
  once with `\definecolor` and reused in every figure.
- A caption says what the figure shows and how to read its error bars. Its numbers are
  macros, as in the prose.

## Boundaries

- Write only inside `<vault>/stories/<anchor-id>/`. Never edit a node, a result file or a
  generated file to make the paper easier to write.
- A story is derived, not evidence. Never link it under any `## Artifacts` block.
- Never hand-edit `story.tex`. Change `story_src.tex` or `build_story.py` and rebuild.
