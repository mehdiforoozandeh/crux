# Spec 12 — Cockpit craft: interaction & performance

**Label:** `ui` · **Status:** ☑ done (landed 2026-08-15 — PRs #13 non-perf + #15 perf; paint profiling convicted the spotlight×backdrop-filter interaction, blur dropped by PI ruling; deferred: canvas click-to-focus (D10), Safari probe cell unmeasured)
**Sibling of:** [01 GUI cockpit](01-gui-cockpit.md)

## Goal

Make the cockpit feel fast and drivable without a mouse. 01 is the *architecture* spec — what
the GUI is, what it may edit, how it ships. This one is craft: measured latency, keyboard
traversal, a typographic scale that reads, and a theme that follows the machine it runs on.
They are split so 01's open questions (packaging, whether editing ever lands) do not gate a
set of defects that can each be fixed and shipped independently.

## Motivation — measured, not guessed

Benchmarked on the CANDI vault, 2026-08-13: **101 nodes drawn, 1,352 SVG elements, 520
`<text>` runs, a 482 KB snapshot.** Full method and raw numbers in
[`research/perf-cockpit-candi.md`](research/perf-cockpit-candi.md).

Two plausible-sounding suspects were **cleared with evidence**, and recording that is the
point of this section — neither should be re-investigated:

| suspect | verdict |
|---|---|
| the 1 Hz snapshot poll re-renders the tree | **false.** 28/28 polls returned 304 over 55.8 s; zero calls to `onSnapshot` / `layout` / `renderTree` / `treeSimDraw`; zero frames. An idle cockpit is genuinely free. |
| the living-tree physics sim is the cost | **false.** Warm tick 0.10 ms, forced full draw 0.10 ms, cool no-op draw 0.00 ms. The dirty-gating works exactly as `gui-living-tree.md` documents. |
| pan/zoom is expensive | **false.** Flat at 0.05–0.40 ms, unchanged from 20 to 100 nodes, identical in and out of focus mode. |

What is actually slow, ranked by measured cost:

| # | bottleneck | measured | implied fix |
|---|---|---|---|
| 1 | **Selecting a node rebuilds the entire SVG** to move one CSS class (`renderTree` 10.9 ms + `renderDetail` 7.3 ms) | 23.4 ms p50, 35.6 ms max. The identical visual result via a two-class swap measured **0.19 ms — 55× cheaper** | swap `.selected` in place; rebuild only on *structural* change. Same for `showQueue` |
| 2 | **Search is undebounced** — one full 114 KB `innerHTML` rebuild per keystroke | 127.5 ms to type a 10-character word; worst single keystroke 32.0 ms | debounce ~120 ms; dim non-matches by class toggle |
| 3 | **Hover spotlight** writes 199 classes, puts **98 node groups** into a 180 ms opacity transition (105 concurrent animations), and fires **12× per node** because there is no same-node guard | ~1 ms of JS, but it queues a full-tree repaint held for 180 ms, twice per node crossed | same-node guard; dim with one class on the viewport `<g>` instead of per-node |
| 4 | `onSnapshot()` full rebuild on any vault change, up to 1 Hz while an agent is writing files | 21.4 ms, max 30.4 ms | diff and patch instead of rebuild |
| 5 | **The server regenerates the 482 KB snapshot on every poll purely to compute the ETag**, then answers 304 | 29 ms of Python per poll = **2.4% of a core, continuously**; 181 files re-read per second | cache on max mtime |

### The unmeasured half, and why it matters most

The instrumented browser pane is permanently `document.hidden`, so `requestAnimationFrame`
never fires and the renderer never rasterizes. **Every number above is JS + style + layout
only. Paint, raster and composite were not measured.**

That gap is load-bearing. Focus mode buys only 2.8× on `renderTree` and **nothing** on
pan/zoom — nowhere near enough to explain the reported "smooth when focused, laggy when not."
What focus mode *does* buy is 4.8× fewer elements, 5× fewer text runs, 4.8× fewer animating
groups, and **under ten live `backdrop-filter: blur()` overlays instead of many.**

So the continuous lag is most likely **paint**, and `backdrop-filter` is the leading
candidate. Confirming it needs a visible window and a real profiler. That is work item 1, and
nothing else in the performance list should be built before it lands — fixing five measured
milliseconds while a paint stall goes unexamined is optimizing the fast half.

## Design

### 1. The structural-vs-cosmetic split

The root cause of bottlenecks 1, 2 and 4 is one design gap: `renderTree()` is the only path
to changing anything on screen, and it rebuilds the whole SVG as a string
([`app.js:457`](../skills/crux/scaffold/webui/app.js)). Selection, search dimming and hover
spotlight are all **cosmetic** — they change how existing elements look, not which elements
exist.

The rule: **a change that does not add, remove or move a node never calls `renderTree()`.**
Cosmetic state becomes class toggles on elements that already exist. `renderTree()` stays for
structural change only (collapse/expand, layout switch, a node appearing or disappearing).

That single rule is worth 55× on the most common interaction in the product.

### 2. Keyboard traversal

**Arrow keys are orientation-relative, not fixed.** The tree renders left-to-right,
top-down, or radially, and a key that means "child" must point at where the children
visibly are:

| layout | child | parent | siblings |
|---|---|---|---|
| left-to-right | `→` | `←` | `↑` / `↓` |
| top-down | `↓` | `↑` | `←` / `→` |
| radial | outward from centre | inward | around the ring |

`Space` collapses/expands. `Enter` opens the detail pane. Existing single-letter bindings
(`[`, `]`, `f`, `Esc`) are untouched.

**The camera follows the selection.** Moving to a child pans and zooms to that child; moving
back to the parent returns. Without this, keyboard traversal walks off-screen within three
presses and is useless on a large tree. Reuse `tweenView()`, which already glides the camera
for programmatic moves and already jumps instantly under `prefers-reduced-motion`.

**Binding rule: keyboard must not cost the mouse anything.** Every existing pointer
interaction keeps its current behaviour. Keyboard focus and pointer hover are separate states
with separate styling, and a keyboard move must not fire the hover spotlight path (bottleneck
3) as a side effect.

Prerequisite, and it is cheap: the SVG canvas becomes a real focusable region —
`tabindex="0"`, `role="tree"`, `aria-label`, and `outline-offset: -2px` so the focus ring is
not clipped by the canvas edge.

### 3. Search that cycles

`Enter` currently jumps to the first match and then does nothing
([`app.js:1496`](../skills/crux/scaffold/webui/app.js) —
`const hit = Object.keys(state.positions).find(...)`). With several matches there is no way
to reach the second.

`Enter` advances to the next match and wraps; `Shift+Enter` goes back. A match counter
(`3 / 11`) sits in the search field so you know the set size before you start cycling. Match
order is the deterministic tree walk order, so it is stable across renders. Same behaviour in
the wiki tab.

### 4. Theme follows the OS until you touch it

The comment at the top of `style.css` claims the initial theme is resolved from "saved
preference, else system." It is not — [`app.js:1256`](../skills/crux/scaffold/webui/app.js)
reads `localStorage.getItem("crux-theme") === "light" ? "light" : "dark"`, which defaults to
dark and never consults the OS. The documentation was written for behaviour that does not
exist.

Fix: with no saved preference, resolve from `prefers-color-scheme` and **keep following it
live** via the media query listener, so a machine that flips at sunset flips the cockpit. The
first press of the ☀/☾ button writes an explicit preference, and from then on that choice
sticks.

The theme must be stamped on `:root` by a blocking inline script in `<head>`, before first
paint, or a dark-mode user gets a white flash on every load.

### 5. Typographic scale

The three detail-pane font steps are 12.5 / 14 / 16.5 px — ratios of **1.12 and 1.18**. A
step below roughly 1.2 does not read as a step, which is exactly the reported complaint.

New scale: **12 / 16 / 21 px** — a perfect fourth, 1.33×. Everything inside the pane is sized
in `em` off this base, so all three steps scale the whole pane: small becomes a genuine
overview, large becomes a genuine reading mode for working through a report.

**The chrome is a separate problem with the opposite fix.** The top bar, legend and rails
currently carry ten-odd distinct sizes between 8.5 and 15.5 px. Dense UI chrome should carry
hierarchy in **ink tier and weight, not size** — pick two or three chrome sizes and hold the
line. This keeps the three-step control meaningful, because the only thing that changes size
is the thing the user asked to change.

### 6. What `beautifului.dev` actually is

Investigated at the PI's direction; notes in
[`research/research-beautifui.md`](research/research-beautifui.md). It is **not** a
principles site or a CSS-technique site: it is a one-page gallery of 19 copy-paste
**React + TypeScript + Tailwind v4** components for AI-chat interfaces. `/docs`, `/components`
and `/about` all 404. None of the 19 is a tree, graph, SVG canvas or document reader.

Recording that plainly so nobody re-reads it hoping for more. Everything usable had to be
extracted from its CSS bundle and its authors' code comments:

- **A six-level background ladder and three ink tiers** (`page → canvas → inset → surface →
  hover → hover-2`; `ink / ink-2 / ink-3`). Depth is a token choice, never a hex. Maps
  directly: canvas = the SVG tree, surface = the detail pane, `ink-3` = metadata.
- **Tints flip technique by theme** — opaque pastels in light, alpha over surface in dark —
  plus a separate `--accent-ink` for accent *text* versus accent *fill*. This is the usual
  reason accent text breaks in one theme.
- **Elevation as a 1px spread ring** (`0 0 0 1px var(--line)`) rather than a border, so
  changing elevation causes no layout shift. Dark needs ~5× the shadow alpha.
- **Disclosure via `grid-template-rows: 0fr → 1fr`** — animates to intrinsic height with no
  JS measurement and no `max-height` guess. Directly useful for 06's collapsed `detail`.
- **One gliding highlight instead of N per-node backgrounds** — their own comment says so, and
  it is the same fix as bottleneck 3.
- **Named-property transitions, never `all`**; `user-select: none` on chrome and
  `-webkit-user-drag: none` on the SVG to kill text selection during pan drags.

**Closed, do not revisit:** all 19 components (JSX), every Tailwind class name,
`iconoir-react`, `glimm` (WebGL), `liveline` (charts), the bundled woff2 fonts, Inter-only
`font-feature-settings`, variable-font weights 550/650, and the striped
`background-attachment: fixed` body texture. It also offers nothing on OS theme following —
there is no `prefers-color-scheme` anywhere in its CSS.

## Decisions

| decision | rationale |
|---|---|
| split from 01 | 01's open questions are packaging and editability; these are independently shippable defects and should not wait on them |
| paint profiling before any optimization | the measured JS cost cannot explain the reported lag; the unmeasured half probably can |
| cosmetic changes never call `renderTree()` | one rule fixes the three most common interactions; 55× on node selection |
| arrow keys are orientation-relative | a key that means "child" must point where the children visibly are, or it is wrong in two of three layouts |
| the camera follows keyboard selection | without it, traversal leaves the viewport in three presses |
| keyboard must not regress the mouse | explicit constraint from the PI; keyboard focus and pointer hover stay separate states |
| theme follows the OS live until first toggle | the code comment already promised this; a live listener costs one line more than boot-only |
| 12 / 16 / 21 for the pane, fewer sizes in the chrome | opposite fixes for opposite problems — the control needs separation, the chrome needs consistency |
| record what `beautifului.dev` is not | it looks like a principles resource and is not; without this note it gets re-read |

## Rejected alternatives

- **Virtualizing / culling off-screen nodes.** The largest possible win, and premature: cost
  measured **linear at ~4.5 µs per element with no fixed-overhead floor**, and the real vault
  is 101 nodes. Revisit if a vault reaches four figures.
- **Reducing the poll rate.** The poll was measured innocent — it returns 304 and triggers no
  render. The waste is on the *server* side (bottleneck 5), and the fix there is an mtime
  cache, not a slower poll.
- **Vim bindings (`hjkl`).** Fastest for one user, hostile to everyone else, and inconsistent
  with the existing single-letter bindings.
- **Spatial arrow-key navigation** (nearest node in that screen direction). Tempting for
  radial layout, but it makes the same keypress mean different things depending on where a
  node happens to have landed, and it is not the accessible treeview pattern.
- **A four-step font control.** Three steps at 1.33× already span 12–21 px; a fourth adds a
  size nobody picks.
- **Adopting anything from `beautifului.dev` directly.** React + Tailwind, against a hard
  no-build rule. The techniques transfer; the code does not.

## Open questions

- Whether `backdrop-filter: blur()` is in fact the paint cost. Work item 1 answers it. If it
  is, the follow-on question is whether the blur is worth keeping at all on a canvas that can
  hold a hundred overlays.
- Whether the keyboard focus ring and the existing selection highlight should be one visual
  state or two. Two is correct for accessibility; one is less noisy.
- Whether search should cycle in tree-walk order or in match-quality order (title hits before
  body hits). Tree order is stable and deterministic; quality order is more useful and harder
  to predict.

## Work items

- ☑ **Profile paint on a visible window** with a real profiler, on the CANDI vault; confirm or
  clear `backdrop-filter`. Nothing else here ships first.
- ☑ Structural-vs-cosmetic split: `.selected` swaps in place; `showQueue` likewise
- ☑ Debounce search input; dim non-matches by class toggle
- ☑ Hover spotlight: same-node guard; one dim class on the viewport `<g>`
- ☑ `onSnapshot()` diffs and patches instead of rebuilding
- ☑ Server: cache the snapshot on max mtime; stop regenerating it per poll for the ETag
- ☑ SVG canvas as a focusable region — `tabindex`, `role="tree"`, `aria-label`, focus ring
- ☑ Orientation-relative arrow traversal + `Space` / `Enter`, camera follows selection
- ☑ `Enter` / `Shift+Enter` cycle search matches with wrap; match counter in the field
- ☑ Theme: resolve from `prefers-color-scheme` with a live listener; explicit toggle wins
  thereafter; blocking `<head>` stamp to prevent the flash
- ☑ Detail-pane scale → 12 / 16 / 21; reduce the chrome to two or three sizes
- ☑ A repeatable benchmark harness, so these numbers can be re-measured after each change

## Acceptance criteria

- Selecting a node does not call `renderTree()`, and measures under 2 ms on the CANDI vault
  (from 23.4 ms).
- Typing a 10-character search query triggers at most two full rebuilds (from ten).
- Crossing a node with the pointer fires the spotlight path once, not twelve times.
- An idle cockpit with a vault under active agent writes holds under 5% of a core across
  client and server combined.
- Every node in the tree is reachable using only the keyboard, in all three layouts, with the
  selected node always within the viewport.
- No existing pointer interaction changes behaviour — asserted, not assumed.
- With no saved preference, the cockpit matches the OS theme, and follows a live OS change.
  After one toggle it stops following.
- The three font steps measure 12 / 16 / 21 px and every step is visibly distinct.
- `selftest.py` passes with a grown assert count.
