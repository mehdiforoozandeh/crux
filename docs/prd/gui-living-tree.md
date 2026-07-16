# PRD: Living tree — anchored physics + radial view mode

- **Kind:** feature  **Roadmap:** Epic 1 — Graphical UI for crux (`ui`)
- **Problem / motivation:** The cockpit tree is static — informative but inert. We want it
  to feel alive (breathing, reactive, settles home after disturbance) and to offer a radial
  layout that uses panel real estate in both dimensions, while keeping the tidy tree's
  readability and refresh-stability promise.

**Design decision:** One shared force simulation for the tree pane (mirroring the wiki
tab's proven `WSIM` architecture: per-frame transform-only updates, `prefers-reduced-motion`
+ hidden-tab guards), driven by **deterministic anchor points**, with two anchor geometries:

1. **Tidy (default, unchanged layout)** — anchors are exactly today's `layout()` positions.
   Physics adds: gentle ambient breathing, node dragging (perturb → always settles back to
   anchor), and glide-to-new-anchor on refresh (replacing the tween-based `animateLayout`).
2. **Radial (new mode)** — project at center, questions/hypotheses on depth rings; angles
   allocated by subtree extent (angular version of the existing `measure` pass), ring radii
   sized so pills never overlap, slight ellipse squash toward panel aspect. Same physics on
   top.

Rejected alternative: free-floating force layout — breaks the "same structure ⇒ same
positions" readability promise (per demo comparison, 2026-07-15).

**UI:** a new view-mode button in the `.viewctl` group toggles tidy ⇄ radial; persisted as
`crux-view` in localStorage. Toolbar order is **left-right · view · density · focus** (orient
sits left of the view toggle; the view toggle sits next to density). The **orient button is
hidden while radial is active** (orientation is meaningless there) but keeps its slot, and the
view toggle has a fixed width, so no button shifts position when you switch modes. Density,
focus, search, selection, collapse, legend, zoom/pan/fit all work identically in both modes.

Two node-level refinements that radial makes necessary: (a) the ± collapse toggle moves to the
node's **inner side** in radial (toward the centre, by the single incoming parent edge) instead
of the far edge where the several child edges fan out; (b) the **root pill is sized to its full
project title** — canvas `measureText` runs a few percent under the SVG paint, so the width is
padded, the toggle gets reserved clearance, and the truncation cap is raised so ordinary titles
are never clipped.

**Behavior guarantees:** with `prefers-reduced-motion`, rendering is exactly today's static
tree (breathing off, drag disabled); hidden tab burns no frames; at rest the tidy mode
deviates from today's layout only by the breathing amplitude (a few px).

**Safari/WebKit hardening** (measured via an in-browser probe, 14→60fps on a radial drag):
WebKit re-rasterizes SVG `<text>` on every repaint and repaints on every attribute write,
even a no-op one. So (a) per-frame writes are dirty-gated — a node/edge is rewritten only
when it moved ≥ ⅓ screen px; (b) radial spokes are trimmed to the pill rims so no edge runs
under a box (untrimmed centre-to-centre spokes made every write near the hub repaint every
spoke); (c) edges don't repaint at all while the sim is cool; (d) the idle breath renders at
half rate. A brief fps dip right after a mode switch (all nodes gliding at once) remains and
is accepted as a ~1s transition cost.

- **Scope (does NOT do):** semantic zoom / level-of-detail, full-bleed/fullscreen pane
  mode, hover ripples, any engine or vault-format change, any wiki-tab change. Those are
  separate future arcs.

- **Acceptance criteria:**
  - [ ] selftest (serve section): served `index.html` contains the view-mode button;
        served `app.js` contains the `crux-view` persistence key and the radial anchor
        layout — the wiring is registered, feel is manual
  - [ ] selftest: existing serve/wiki-gui asserts unchanged and green
  - [ ] manual: default view at rest matches today's layout (± breathing); reduced-motion
        renders today's exact static tree
  - [ ] manual: drag any node in either mode → it settles back to its anchor
  - [ ] manual: radial mode on the demo vault — project centered, no pill overlaps, orient
        button hidden, mode survives reload
  - [ ] manual: collapse/expand, search, focus, density, select, zoom/pan/fit all work in
        radial
  - [ ] manual: auto-refresh with a structure change glides nodes to new anchors (no
        teleport)
  - [ ] manual: toolbar reads left-right · view · density · focus; toggling the view mode
        shifts no button (orient keeps its slot, the view toggle is fixed-width)
  - [ ] manual: in radial the ± toggle is on each node's inner (parent-edge) side; the root
        pill fits its full title with the toggle clear of the text

- **Backward-compat / migration:** webui-only; no vault format, verdict, or roll-up
  change; `ENGINE_VERSION` untouched — no migration.
