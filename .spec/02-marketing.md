# Spec 02 — Marketing animation + README hero

**Label:** `marketing` · **Status:** ☐ todo

## Goal

A short programmatic (Remotion / React-video) explainer that shows what crux does,
rendered to video + GIF and embedded as the hero on the README and the repo's social
preview.

## Work items

- ☐ **Storyboard the explainer** (~30–60s) — narrative: open a Question → propose a
  Hypothesis → register verifiables → land a finding → roll up the ledger → answer the
  question; carry the Southern-Cross / navigation motif throughout.
- ☐ **Scaffold the Remotion project** (React/TypeScript) under `marketing/`.
- ☐ **Build the animation scenes** from the storyboard.
- ☐ **Render & optimize** — export MP4 + an optimized GIF/webp sized for README and web.
- ☐ **Embed the hero** — add to README top, and set the repo's GitHub social-preview image.

## Notes

`assets/` already carries a hero GIF pair (`crux-hero-light.gif` / `crux-hero-dark.gif`),
a schematic SVG pair, and the social preview — so the README hero slot is filled. This
epic is the *programmatic* replacement, which buys re-renderability when the loop or the
vocabulary changes.

The `remotion` skill is the reference for the implementation.

## Open questions

- Whether the animation replaces the current hero assets or sits alongside them (e.g. GIF
  in README, MP4 on a landing page).
