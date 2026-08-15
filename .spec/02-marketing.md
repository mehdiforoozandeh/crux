# Spec 02 — Marketing animation + README hero

**Label:** `marketing` · **Status:** ☑ done

## Goal

A short explainer that shows what crux does, embedded as the hero on the README and as the
repo's social preview.

## Delivered

The hero slot is filled and the epic's outcome is met — by hand-authored SVG-to-GIF assets
rather than by the Remotion pipeline the original spec proposed.

- ☑ **The explainer narrative** — one hypothesis with three pre-registered verifiables ticking
  to a derived verdict → pull back to the question that holds it → pull back to the research
  programme → the open questions resolve into the Southern Cross. The ownership gutter (you
  write the hypothesis and verifiables; the agent runs and checks; the verdict is derived)
  carries the leash, and the Southern-Cross / navigation motif closes it.
- ☑ **Rendered assets** — `assets/crux-hero-light.gif` / `crux-hero-dark.gif` (seamless loop,
  follows the reader's GitHub theme via `<picture>`), the `crux-schematic-*.svg` pair, and
  `crux-social-preview.png` / `.svg`.
- ☑ **Embedded** — README hero at the top with full alt text, plus the repo's GitHub
  social-preview image. Cockpit and wiki-tab screenshots under `assets/screens/` back it up.
- ☑ **Reduced-motion handling** — the marketing site honours `prefers-reduced-motion`
  (`e510def`).

Shipped across `8e8c557` (animate the hero + the vault it is drawn from), `a2b0f4f`
(theme-following), `d7bf5f6` (seamless loop), `e510def` (site pass).

## Dropped, deliberately: the Remotion pipeline

The original work items scaffolded a React/TypeScript Remotion project under `marketing/` and
rendered MP4 + GIF from it. That was never built and is **not** carried forward.

The argument for it was re-renderability when the loop or the vocabulary changes. Against it:
it introduces a Node/React toolchain into a repo whose one hard dependency rule is *stdlib
only, no build step* — the webui is deliberately no-build vanilla JS. Paying that cost for an
asset that has changed three times in a year, each time cheaply, is the wrong trade. The
hand-authored SVG source is itself re-renderable; it just re-renders by editing SVG rather
than by running a build.

If the loop's vocabulary changes enough to invalidate the hero, reopen this as a new spec with
the toolchain question settled first.
