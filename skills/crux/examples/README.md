# Example vaults

Four committed reference vaults. All open directly in the cockpit — run `crux serve`
(or `../../../../crux serve` from inside a vault) and you get the full two-tab
experience: the question/hypothesis **Tree** and, where a wiki exists, the living
**Wiki** graph + reader.

All four are stamped engine **4.0** (crux 1.0.0). Each was written under an older engine
and converted by the engine's own migration, never by hand: every recorded verdict became a
**finding** with a direction and a confidence, every approved synthesis became a strong
finding on its question, and each node's state (open · leaning · settled · parked) is now
derived from its findings. The tables below give the result.

Start with `scaling_vault/` if you want to see what crux is for; `sortlab_vault/` if you
want a whole finished project you can read without knowing any field; `segssl_vault/` if
you want to see how large one gets.

> **Not here: the agent-eval fixtures.** Spec 10's planted-defect vaults live under
> `skills/crux/evals/fixtures/`, deliberately outside this directory. They are
> `crux validate`-**red by construction** — being wrong in a stated, hand-authored way is
> their entire purpose. Gate 3 of the `evolve-crux` gate walks *this* directory to ask
> "did anything break", and a tree of deliberately-broken vaults would make that answer
> unreadable. These four stay the gate's targets; the fixtures are never one.

## `demo_vault/` — the minimal fixture

The synthetic vault the docs and the validation gate reference: one small question
tree plus a 3-page wiki (JEPA / masked modeling / FiLM). Handy as a
smoke-test target and as the smallest complete example of every crux concept.

## `scaling_vault/` — the gentlest first read

**More data, or a better model?** — 13 nodes, deliberately small and deliberately
jargon-free, so the shape of a crux vault is legible before you know anything about
the field it sits in.

- **Tree:** 3 questions, 7 hypotheses, 7 findings. `q1` carries the point: one
  hypothesis is *supported* with strong confidence, and the answer still contradicts it —
  because the winning arm had twice the compute, and the two hypotheses that test for
  exactly that come back *mixed* (weak) and *against* (strong). Two questions are settled
  by a strong answer. `q3` stays open, with one experiment running and one idea untested.
- **Wiki:** 24 pages across 6 categories (scaling laws, compute-optimal training, data
  quality and pruning, the two model families under comparison, the corpora the prior
  results were measured on), interlinked by 72 wikilinks, with 18 citations from tree
  nodes into `[[wiki/…]]` pages.
- **Sources:** 22 open-access arXiv papers, sha256-registered in `wiki/.sources.tsv`.
  Every arXiv id was checked against the arXiv API before the page citing it was
  written.

Same deal on the PDFs as below — `raw/` ships empty; `./fetch_sources.sh` pulls them.
The research programme is a plausible fixture: the numbers are invented for
demonstration, and the wiki's literature claims trace to the cited papers.

This is the vault the README's animation is showing.

## `segssl_vault/` — a realistic research program

A full-scale example of what a lived-in crux vault looks like: **SegSSL —
label-efficient semantic segmentation via self-supervised pretraining**.

- **Tree:** 5 research questions and 16 hypotheses, 18 findings — 4 questions settled by
  a strong answer, 1 still open (one experiment running, one idea untested). Hypothesis
  findings span supports (4, strong), against (5, strong) and mixed (5, weak), converted
  from verdicts that pre-registered verifiables derived; `META.md` and `EXPERIMENTS.md`
  show each node's state and confidence.
- **Wiki:** 17 agent-compiled literature pages across 6 categories (methods like MAE /
  DINO / iBOT, concepts like masked-image-modeling / label-efficiency, a decoder
  comparison, the Cityscapes dataset page, and an overview hub), interlinked by 83
  wikilinks — content genuinely compiled from the 15 papers below, not lorem ipsum.
- **Cross-links:** tree nodes cite `[[wiki/…]]` pages (59 citations), so the two
  cockpit tabs behave as one connected instrument. The flow rule holds: the wiki never
  cites the tree.
- **Sources:** 15 open-access arXiv papers, sha256-registered in `wiki/.sources.tsv`
  with full author lists in their titles (search the wiki tab by any co-author).

### The PDFs are fetched, not committed

arXiv's default license doesn't permit third-party redistribution, so `raw/` ships
empty. Everything in the cockpit works without the PDFs. To pull the actual papers
(86 MB) and make `crux validate` findings-free:

```bash
cd segssl_vault && ./fetch_sources.sh
```

Until then, `crux validate` reports the expected "registered but missing" /
"cites missing source" findings for the 15 sources — that's the linter doing its job.

### Provenance

This vault was generated as a realistic *fixture* by a multi-agent build (question
designers, paper curators, per-page wiki writers reading the real PDFs), then
validated with `crux validate`. The research program is plausible but fictional: the
experiment numbers (mIoU figures, run links) are invented for demonstration; the
wiki's literature claims trace to the cited papers.

## `sortlab_vault/` — a whole project, start to finish

**SortLab** — a high-school student times five sorting programs they wrote by hand against
the one already built into the language, and learns that measuring is harder than sorting.
The largest example here, and the only one a reader with no field at all can follow end to
end: every sentence is about a laptop, a stopwatch and a list of numbers.

- **Tree:** 35 questions and 108 hypotheses, with 154 findings: 57 nodes settled, 59
  leaning and 27 open. 87 findings came from the closed hypotheses' verdicts (supports 40,
  against 24, mixed 19, and 4 **no answer yet** from the four invalid runs, all control
  failures), 57 from accepted experiment conclusions (moderate, linked to the task output),
  and 10 from approved syntheses. The migration listed 2 experiments whose own conclusion
  disagrees with their hypothesis's verdict (`h97`, `h104`).
- **Taskhub:** 200 tasks — 156 done, 21 on the frontier, 13 computed `blocked`, 10 dropped;
  45 of them experiments, whose outputs are evidence on findings.
- **Wiki:** 60 background pages compiled from 15 invented sources (class handouts, a computer
  club talk, a school magazine column). Neutral, encyclopedic, and — by the flow rule — they
  never mention this project or a single one of its results.
- **RD:** 4 design documents, including a superseded `timing_harness_v1` whose successor is
  the record of what the timer study changed.

### `crux validate` reports exactly two problems, and that is the point

`h9` and `h65` each had a verifiable edited **after** the run was locked: a threshold
loosened from ten percent to five, and a check about the *mean* reworded to *median*. Both
edits really happened, both nodes say so in plain words under `## Problem Statement`, and
crux flags them permanently. Reverting the edits to get a green lint would un-flag drift
that occurred — exactly the dishonesty the mechanism exists to prevent. Zero warnings.

The `selftest` pins all of this (counts, the two named DRIFT ids, zero warnings, and
`refresh()` as a no-op) so the fixture cannot rot silently.

### Provenance

Generated as a *fixture* by a multi-agent build driving the real CLI of engine 3.5 for every
verb it had — `init`, `ask`, `hypothesize`, `approve-null`, `test`, `close`, `synthesize`,
`approve`, `answer`, `rd`, `ingest`, the task verbs and `glossary` — and then converted to
4.0 by the engine's migration. Every verdict was the engine's own derivation from ticked
verifiables, and every finding is the migration's mapping of one; none was written by hand.
The project is fictional and the timings are invented, but nothing about the bookkeeping is
painted on.
