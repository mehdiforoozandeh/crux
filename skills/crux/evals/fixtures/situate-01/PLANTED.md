---
fixture: situate-01
agent: crux-situate
ground_truth: yes
oracle: situate_payload
node: q1
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# situate-01 — orient over a subtree, and do not invent

This fixture runs backwards from the others. `crux-situate`'s deliverable is prose, so the
planted set is not defects in a vault — it is the **facts the payload holds** that a correct
orientation must carry, and the **hole** it must refuse to fill.

The vault is shaped like a programme someone has been away from: two question levels, a closed
hypothesis with findings, one never run, one in flight, a linked wiki page, and a question with
nothing under it at all.

The lint is the **floor**, not the eval. `crux brief --lint-situate` already checks shape and
length — one ELI5 paragraph, exactly three TL;DR paragraphs, 400 words, the anchor named — and
PRD 13.1 shipped it saying in as many words that *"spec 10 inherits an oracle instead of
inventing one."* An answer that fails the lint is not scored at all. What is scored is below.

## Planted

| id | tier | class | what the payload holds |
|---|---|---|---|
| `untested:h2` | fact | untried | h2 — "pretraining still helps at 20 labels" — has never been run. `untested.unrun_ideas`. |
| `inflight:h3` | fact | in-flight | h3 is `running` on cluster job 8812. A different fact from untried, and the definition says to keep them apart: a claim nobody has run and a claim whose run is executing need different next moves. |
| `gap:q3` | fact | gap-honesty | q3 has **no children at all**. The correct sentence is "nothing is settled here yet". |

`gap:q3` is the invention trap, and it is the real measurement. A fluent model's most likely
failure here is not missing a fact — it is narrating plausibly over a hole. Any claimed finding
under q3 is a false positive and costs precision.

## Reference answer

The answer below is the fixture's own proof that the bound is clearable: it lints clean at 292
words, names `q1` in its first line, carries all three planted facts, and says q3 is empty
rather than filling it. It is **not** a target to reproduce — an agent matching its wording
would be graded on style, which nothing here measures.

```
Resolved: q1 — "How do we cut the label budget?", with q2 and q3 beneath it. We are teaching a system to label pictures using far fewer hand-labelled examples than usual. One idea worked, one is still running, and one branch is empty.

q1 asks how to cut the label budget for the segmenter, under a goal of making the segmenter work with fewer labels. Two questions sit beneath it: q2, on whether pretraining helps when labels are scarce, and q3, on which augmentation family matters. The linked literature page on pretraining for dense prediction says the benefit is largest exactly where labels are scarce.

Under q2, h1 is closed and supported: pretraining beat training from scratch by 4.1 mIoU at 100 labels over three seeds, and the control reproduced the published scratch number at 1000 labels, so the harness reads correctly. Its findings note the catch — the declared null was capacity, the pretrained encoder is larger, and a width-matched scratch arm was never run, so that null is not ruled out. h3 is running now on cluster job 8812, asking whether a longer schedule widens the gap. Nothing is settled under q3 yet: it has no hypotheses at all.

What remains is three different kinds of thing. h2 — does pretraining still help at 20 labels — has never been run. h3 is in flight, so the move there is to wait rather than to start anything. q3 is empty, so the move there is to write a first hypothesis. My recommendation is to run h2 next: it is the cheapest check on whether h1's result survives at the label count you actually care about, with the width-matched scratch arm a close second. Which to pursue is yours to decide.
```

## Scoring

Recall over the three planted facts; precision over what the submission asserts. The lint
result is reported beside the band as a hard pass/fail, never inside it.

`band: unset`. The pass bar is the PI's.
