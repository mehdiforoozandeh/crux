# Research: keeping a research tree anchored to its top question

Four read-only web-research agents, 2026-10-31. Failure studied: over a long project, sub-questions
and hypotheses pile up, each finding opens new questions, and the work drifts from the top question.

## What crux already covers

- Expectation stated before evidence (`--expect`); never loosen a threshold after the result.
- Null and verifiables; checks hash-locked at `running`, drift flag on later edits (anti-HARKing).
- crux-prerun: "is there a plausible outcome from which we would conclude nothing?" — value of
  information at the level of one hypothesis.
- Five untested hypotheses per question is the cap.

## The gap

No node records how its answer bears on its parent's answer, and nothing re-asks whether a
branch still serves the root. Value of information is checked against the hypothesis, never
against the parent question.

## Sources and the rules kept

| Rule | Sources (primary unless marked) |
|---|---|
| A node states which answer of its parent it could change | Value of information (secondary: https://www.tandfonline.com/doi/full/10.1080/01621459.2018.1562932); Heilmeier Catechism "who cares / what are the exams" https://www.darpa.mil/about/heilmeier-catechism; Hamming "You and Your Research" 1986 https://www.cs.virginia.edu/~robins/YouAndYourResearch.pdf; NIH specific aims https://www.niaid.nih.gov/node/20672 |
| Re-read the root-to-node path before opening or proposing | Arike et al. 2025, goal drift in LM agents grows with context; restating the goal mitigates, arXiv 2505.02709; Google AI co-scientist goal-parsing supervisor and proximity check (blog, 2025) |
| A tangent goes to a parking list, not the tree; an auxiliary question carries its exit | Alon 2009 "How to choose a good scientific problem" (cooling-off); Pólya 1945 auxiliary problem; PhD rabbit-hole advice (secondary) |
| An exploratory result is a lead: it yields a sharper hypothesis or a ruled-out direction, never the parent's answer | de Groot 1969 (2014 reprint) https://www.ejwagenmakers.com/inpress/DeGroot1956_TA.pdf; Nosek et al. PNAS 2018; Tukey 1980 (secondary); Box 1976 (secondary); Google Deep Learning Tuning Playbook |
| Review a line for progress; allow a pivot that rewrites the parent | Lakatos progressive vs degenerating programmes (SEP https://plato.stanford.edu/entries/lakatos/); Box iterative loop |

## Rejected as heavy machinery or redundant

MECE issue trees (hard to keep across a deep tree; Minto secondary only), Elo hypothesis
tournaments and multi-agent debate (co-scientist, Robin), full registered reports for every
node, Alon's feasibility-interest Pareto ranking, goal-question-metric (redundant with the
bears-on rule), theory-of-change full-chain audits.

## Tension to respect

Platt and Hamming push narrow (one important problem, exclude fast). Chamberlin and Alon allow
plurality and wandering, which sometimes finds the better question. Resolution: gate what
becomes a committed node, not informal exploration. Every framework above assumes a fixed top
question; science sometimes needs a finding to rewrite the parent, so the rules must permit a
pivot and not only prune.
