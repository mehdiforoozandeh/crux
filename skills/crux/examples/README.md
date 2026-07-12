# Example vaults

Two committed reference vaults. Both open directly in the cockpit — run `crux serve`
(or `../../../../crux serve` from inside a vault) and you get the full two-tab
experience: the question/hypothesis **Tree** and, where a wiki exists, the living
**Wiki** graph + reader.

## `demo_vault/` — the minimal fixture

The synthetic vault the docs and the validation gate reference: one small question
tree plus a 3-page wiki (JEPA / masked modeling / FiLM). Handy as a
smoke-test target and as the smallest complete example of every crux concept.

## `segssl_vault/` — a realistic research program

A full-scale example of what a lived-in crux vault looks like: **SegSSL —
label-efficient semantic segmentation via self-supervised pretraining**.

- **Tree:** 5 research questions × 3 hypotheses each — 4 questions resolved with PI
  answers, 1 still open (one experiment running, one idea untested). Verdicts span
  supported / partial / refuted, all mechanically derived from pre-registered
  verifiables; the evidence ledgers, `META.md`, and `EXPERIMENTS.md` roll up from them.
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
