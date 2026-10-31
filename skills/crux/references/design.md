# Pre-run design: expectation, null, verifiables

*Reference for [`SKILL.md`](../SKILL.md). Read it before compute is spent on a hypothesis, or
when the PI asks how to design a run. The **crux-prerun** agent does this job cold when it is
installed; this page is the discipline it follows, for when you do it yourself.*

## The three things a run is judged against

- **Expectation** (`## Expect`, required, `crux hypothesize --expect`): the result the claim
  predicts, stated before any evidence, with a size and a threshold when one can be stated.
  "B is better" is not an expectation; "B scores at least 2 points higher on the held-out
  set, over 5 seeds" is.
- **Null** (`## Null`, optional, `--null`): the most parsimonious alternative explanation of
  the expected result. One line, at most 25 words: a family from the closed list (capacity,
  chance, leakage, selection, normalization, instrumentation), then the instance in this
  experiment. "capacity" alone is useless; "capacity — the adapter arm is also the larger
  model" can be tested against. The engine refuses a malformed null.
- **Verifiables** (`## Verifiables`, optional, `-v`, `-n`, `--fails-if`): the checks. Keep a
  check only if you can name a world where it fails and every other check passes
  (`--fails-if`). At least one outcome-neutral control (`-n`) that must pass whatever the claim
  turns out to be. One check aimed at ruling out the null (`--discriminates`).

The checks inform the closure judgment; they do not compute it (see *Closure judgment* in the
core).

## The question to ask before the compute

> **Is there any plausible outcome of this run from which we would conclude nothing?**
> If yes, the design is wrong. Fix it before spending the compute.

Walk the outcomes: expectation met with the null ruled out; met with the null standing; a
near miss; a failed control; a clear miss. Write the sentence you could say after each, and
how it would move the confidence. If one of those sentences is *"we learned nothing"*, that is
the design defect, and it is cheapest to fix now: replicates, a control, a matched arm.

**Combination rule.** With more than one claim-directed check, say how they add up before the
run: `rule: all | any | m-of-n` (`crux hypothesize --rule`). When you choose `all`, say the
cost out loud: **two checks at 80% power each give 64% joint power, and thresholds may
not be loosened to compensate.**

Before a run, a hypothesis should also carry, in frontmatter, `measurement:` (what is
measured, and with what instrument; `--measurement`) and `replicates:` (the n the claim will
rest on; `--replicates`). `crux validate` reports the gaps as information; whether the control
is the *right* control is judgment.

**The commitment is locked when the run starts.** `crux test <hid> --to running` content-hashes
the checks, their kinds and the rule. A later edit is allowed (research does discover a check
was wrong), but it raises a permanent **drift** flag on the node and in `validate`.
It blocks nothing, and the closure judgment reads it: checks edited after the run started cap the
confidence at moderate, with the edit named in the why. Say what changed and why in the node;
`git log -p <node>.md` is the diff.

## A mixed result is a symptom, not an outcome

Some checks passed, some did not. Checks under one hypothesis are consequences of the same
claim, so if it is true most pass together. Three causes produce the same symptom:

| cause | what went wrong | the fix |
|---|---|---|
| **compound claim** | the hypothesis was two or three claims; each check answered a different one | split the hypothesis |
| **non-entailed check** | the check does not follow from the claim | rewrite the check |
| **the run could not discriminate** | under-powered, confounded, wrong instrument, no control | fix the design |

Record the finding as `mixed` with the confidence the evidence allows, and name the likely
cause in the why.

## One experiment, several hypotheses: when that is allowed

> **One experiment settles several hypotheses separately only when** each hypothesis is
> turned by its own independently varied knob — a comparison the design can attribute to it
> alone, at a resolution high enough for the kind of effect it claims — and no single shared
> ingredient (one batch, one seed, one preprocessing path, one control) could flip all the
> answers together without a pre-declared outcome-neutral check catching it and voiding the
> whole run; **anything less means you ran one experiment with many labels, not many
> answers.**

Three checks, in the order they fail:
- **Different lever.** Each hypothesis is turned by its own independently varied knob: its
  own comparison, not shared with another and not a by-product of two others.
- **Different failure.** No single shared ingredient may flip every answer at once
  undetected. Block it, replicate it, cover it with an outcome-neutral check, or log it as a
  risk on every hypothesis in the bundle. This is what outcome-neutral checks are *for*: they
  are the dual of a shared failure, so **sharing one across a bundle is the fix, not the
  flaw**.
- **Different verdict.** Each hypothesis carries its own checks and its own rule, and can be
  stated without reference to the others. If flipping one answer would change another, they
  were never separable: that is one compound claim wearing several labels.
