# beautifului.dev — research notes for the crux cockpit

Fetched 2026-08-13. Site reachable, HTTP 200, ~386 KB HTML + one 72 KB CSS bundle.

---

## 1. What the site actually is

**A single-page demo gallery of 19 copy-paste React components for AI-agent
interfaces.** Not a design-principles site, not a CSS-technique site, not a
course, not a documentation site.

Facts established by inspection, not inference:

- Title: "Beautiful UI — Crafted primitives for AI-native interfaces."
- Built by Turbo (turbodesign.co), a product design studio. MIT licensed.
  The only other pages are `/license` (200). `/docs`, `/components`, `/about`
  all 404. No GitHub link. There is no npm package.
- Stack: **Next.js (App Router) + React + TypeScript + Tailwind CSS v4**.
  Imports found in the shipped source: `react`, `iconoir-react`, `glimm`
  (a WebGL shader lib), `liveline` (charts), plus two local atoms
  (`Shimmer`, `StreamText`).
- Fonts: **Inter** and **JetBrains Mono**, self-hosted `.woff2`.
- Distribution model: each component has a "Copy code" button; the full
  TSX source of all 19 is embedded in the page payload.
- **There is zero prose about principles.** No manifesto, no rules page, no
  written guidance. Every heading on the page is a component name and a
  one-line description.

### The 19 components

Loading State · Thinking · Streaming Text · Approval Card · Tool Chips ·
Task Rows · Chat · Prompt Bar · Recommendation Card · Context Cards ·
Diff Table · Records Table · Filter Table · Sidebar Nav · Search ·
Insight Cards · Code Block · Fine-tune Card · Selection Actions

Almost all of them are chat/agent-conversation primitives. **None of them is a
tree, a graph, an SVG canvas, or a document reader.** As a *component* source
for the cockpit, the site is close to useless.

### Where the value actually is

Two places, neither of them the components:

1. **The CSS bundle.** It carries a complete, coherent, 40-token semantic
   colour system with matched light/dark pairs, a shadow ladder, an easing
   set, and a radius set. This is directly liftable into plain CSS custom
   properties — it is already plain CSS custom properties.
2. **The header comments in the shipped TSX.** The authors wrote unusually
   candid design rationale in code comments. That is the closest thing to
   stated principles the site has, and it is good.

So: treat this as **a token system and a set of implementation tricks**, and
ignore its self-description as a component library.

---

## 2. The token system (verbatim, liftable as-is)

Their light theme is `:root`, their dark theme is `.dark`. The cockpit uses
`:root[data-theme="..."]` — a straight rename, no other change needed.

### Colour — semantic, never literal

| Token | Light | Dark | Role |
|---|---|---|---|
| `--page` | `#fafafb` | `#17181a` | page backdrop |
| `--canvas` | `#f1f2f3` | `#1c1d1f` | recessed working area |
| `--surface` | `#ffffff` | `#232427` | raised card / panel |
| `--inset` | `#f7f8f9` | `#1f2022` | inset well (footers, code) |
| `--hover` | `#f4f5f6` | `#2a2b2e` | hover level 1 |
| `--hover-2` | `#e7e9eb` | `#313236` | hover level 2 |
| `--ink` | `#1f2124` | `#f2f3f4` | primary text |
| `--ink-2` | `#62656b` | `#a5a8ad` | secondary text |
| `--ink-3` | `#9a9da3` | `#6c6f75` | tertiary / metadata |
| `--line` | `#ecedef` | `#2e3033` | hairline |
| `--line-strong` | `#e0e2e5` | `#3a3c40` | emphasised divider |
| `--field` | `#f2f2f3` | `#2b2c2f` | input / chip fill |
| `--accent` | `#0285ff` | `#3d9aff` | accent |
| `--accent-ink` | `#0170dd` | `#7ec0ff` | accent *text* (contrast-safe) |
| `--accent-tint` | `#e9f3ff` | `#3d9aff29` | accent wash |
| `--green` | `#189a4d` | `#3dbb72` | success |
| `--green-tint` | `#e8f5ed` | `#3dbb7224` | |
| `--orange` | `#ef720c` | `#f68f3c` | warning |
| `--orange-tint` | `#fdf1e5` | `#f68f3c24` | |
| `--red` | `#e3474c` | `#ee5c61` | error |
| `--red-tint` | `#fcecec` | `#ee5c6124` | |
| `--tooltip-bg` | `#25272b` | `#111214` | tooltip **inverts in light, deepens in dark** |
| `--tooltip-fg` | `#f6f7f8` | `#f2f3f4` | |
| `--tooltip-border` | `#3a3c40` | `#2e3033` | |

Four structural ideas worth naming:

- **Six background levels, not two.** `page → canvas → inset → surface →
  hover → hover-2`. Depth is expressed by *which background token*, never by
  a hand-written hex. This is what lets the same markup read correctly in
  both themes with no per-theme overrides anywhere in component CSS.
- **Three ink tiers, and only three.** Usage count in their own markup:
  `text-ink` 240, `text-ink-3` 216, `text-ink-2` 146. All three are heavily
  used — this is a real working hierarchy, not decoration.
- **A separate `--accent-ink` for accent-coloured *text*.** The accent used
  as a fill and the accent used as text are different values, because a fill
  needs saturation and text needs contrast. Light darkens the accent for
  text; dark lightens it.
- **Tints flip technique between themes.** Light tints are *opaque pastels*
  (`#e9f3ff`); dark tints are *alpha over whatever is beneath*
  (`#3d9aff29`). Opaque in light avoids muddiness; translucent in dark
  composites correctly over any of the six background levels. I would copy
  this exactly.
- They also use `color-mix()` for one-off blends, e.g. selected row =
  `color-mix(in srgb, var(--accent) 7%, var(--surface))`. Baseline-supported,
  no build step. Useful for tree node states.

### Shadow ladder — elevation *is* the hairline

```css
--shadow-hairline: 0 0 0 1px var(--line);
--shadow-btn:      0 0 0 1px var(--line-strong), 0 1px 2px  #1018280d;  /* light */
--shadow-card:     0 0 0 1px var(--line),        0 1px 2px  #1018280a, 0 2px 6px #10182808;
--shadow-raised:   0 0 0 1px var(--line),        0 2px 10px #0000000b;
--shadow-overlay:  0 0 0 1px var(--line),        0 8px 28px #0001;
--shadow-inset-field: inset 0 1px 2px #0000001f;
```

Dark equivalents keep the same ring but hit the blur far harder
(`#0003`, `#00000038`, `#00000057`, `inset 0 1px 2px #0006`).

Two principles here:

- **Every elevation begins with a 1px spread ring instead of a `border`.**
  One token gives you outline + depth, and the box never changes size when
  elevation changes — no layout shift, no `box-sizing` fights.
- **Dark mode needs roughly 4–6× the shadow alpha of light mode.** On a dark
  page a soft shadow is invisible; they compensate in the token, so callers
  never think about it.

### Easing set

```css
--ease-out:        cubic-bezier(0, 0, .2, 1);      /* default exit of motion */
--ease-out-strong: cubic-bezier(.23, 1, .32, 1);   /* the workhorse, 8 uses */
--ease-link:       cubic-bezier(.16, 1, .3, 1);    /* long, very settled */
--ease-in-out:     cubic-bezier(.4, 0, .2, 1);
```

`--ease-out-strong` is the one that gives the "settles into place" feel.
Nothing on the site uses an ease-*in* for an entrance.

### Duration ladder (observed, consistent)

| Duration | Used for |
|---|---|
| 100–120 ms | hover / colour changes only |
| 140–160 ms | small pops, menu open (`pop-in`) |
| 200–300 ms | disclosure (rotate chevron, expand row) |
| 320–400 ms | layout / width / crossfade |
| 350 ms | entrance `fade-up` |
| 90 ms | stagger step between list items |

### Radius set

```css
--radius-chip: 6px; --radius-control: 8px; --radius-card: 10px;
```

Plus a stated rule, quoted from their Fine-tune Card source:
"A 36px pill wraps 28px controls at a 4px inset. The controls resolve to a
14px radius, preserving the concentric curve." — i.e. **inner radius = outer
radius − inset**. Cheap, and it is why their nested boxes look right.

### Typography settings

```css
body {
  font-size: 14px; line-height: 1.5;
  letter-spacing: -.01em;
  font-feature-settings: "cv11", "ss01";
}
```

`--tw-tracking` values used: `-.01em` at body, `-.02em` on large text.
Micro-label recipe (their uppercase section labels):
`font-size: 10.5px; font-weight: 650; letter-spacing: .04em; text-transform:
uppercase; color: var(--ink-3)`.

---

## 3. What they do about typographic scale — and why it cuts against our framing

**Their type sizes, counted from their own markup:**

| size | uses |
|---|---|
| 13px | 101 |
| 12px | 91 |
| 12.5px | 86 |
| 11.5px | 58 |
| 11px | 41 |
| 10.5px | 23 |
| 17 / 19 / 20 / 21px | 8 total |

That is *nine* sizes crammed between 10.5 and 13px — steps of half a pixel.
By our own complaint about "12.5 / 14 / 16.5 being too close", their chrome
should be unreadable mush. It is not, and the reason is the finding:

> **In dense UI chrome they do not encode hierarchy in size at all.**
> Hierarchy is carried by the three ink tiers plus weight (medium 133 uses,
> semibold 40, bold only 4) plus case. Size only tracks *physical fit* —
> how much room the row has.

Weights used: 400 / 500 / 550 / 600 / 650 / 700. Note the odd 550 and 650 —
they nudge weight rather than size when they need one more step.

**How this applies to the cockpit.** We have two different type problems and
were treating them as one:

1. **Chrome type** — top bar, tab labels, node labels in the SVG, search
   field, breadcrumbs. Adopt their approach: pick basically one size
   (12–13px), and get every level of hierarchy from `--ink` / `--ink-2` /
   `--ink-3` and weight 500/600. Stop trying to distinguish chrome levels by
   size.
2. **Detail-pane reading type** — that is prose, and it is a *user
   preference control*, not a hierarchy. Three steps of a preference control
   must be obviously different when you click them, so they need a real
   ratio. 12.5 → 14 → 16.5 is 1.12× then 1.18×; below the ~1.2 threshold at
   which a step reads as a step. Use a clean ratio instead, e.g.
   **13 / 15.5 / 18.5** (≈1.19×, ≈1.19×) or **13 / 16 / 19.5** (1.23×) —
   and scale the *whole* pane by changing one `--md-size` variable that
   headings, code, and lists derive from with `em`, so a step visibly moves
   everything, not just body copy. Their own large sizes (17 / 19 / 21) sit
   in the right region for a reading step.

The site gives no ratio, no modular scale, and no stated type doctrine. The
above is my reading of what they do, not something they claim.

---

## 4. Techniques we can lift, and exactly where they land in the cockpit

Grouped by our stated problem areas. Everything here is plain CSS or plain
DOM — no React, no Tailwind, no build.

### 4.1 Colour system (applies everywhere)

| Technique | Cockpit application |
|---|---|
| Six background levels | `--page` = app background; `--canvas` = the SVG tree canvas (recessed reads correctly for a pannable field); `--surface` = the detail pane and the top bar; `--inset` = code blocks and blockquotes inside markdown; `--hover`/`--hover-2` = tree-node hover and wiki list hover. |
| Three ink tiers | `--ink` = node title / markdown body; `--ink-2` = node subtitle, tab labels, table headers; `--ink-3` = metadata, edge labels, counts, breadcrumb separators, empty states. |
| `--line` vs `--line-strong` | `--line` = SVG tree edges and markdown `hr`; `--line-strong` = top-bar bottom border and the tree/detail split. |
| Separate `--accent-ink` | markdown links and the "current node" label need `--accent-ink`; the selected-node fill needs `--accent`. Using one value for both is why accent text usually looks wrong in one theme. |
| Alpha tints in dark, opaque in light | node status washes (answered / open / stale) that must sit correctly on both `--canvas` and `--surface`. |
| `color-mix(in srgb, var(--accent) 7%, var(--surface))` | selected tree row / selected wiki row, one line, no extra token. |

### 4.2 Elevation

- Replace any `border: 1px solid` on panels with `box-shadow: var(--shadow-hairline)`.
  Panels stop shifting by 2px when they gain/lose a border, and the SVG
  canvas edge stays crisp under transform.
- Use `--shadow-overlay` for the search dropdown and any node context menu.
- Remember the dark-mode alpha multiplier; put it in the token, not the rule.

### 4.3 Motion and perceived responsiveness

| Technique | Cockpit application |
|---|---|
| **Disclosure via `grid-template-rows: 0fr → 1fr`** with `min-height: 0; overflow: hidden` on the child. Their Tool Chips row does exactly this at 300 ms `--ease-out-strong`. | Collapsing sections in the detail pane, and the wiki tree. Animates to *intrinsic* height with no JS measurement, no `max-height` guess. Big win for a no-framework codebase. |
| **One gliding highlight, not per-row backgrounds.** Their comment: "a single highlight glides to the active row instead of each row toggling its own background". | Tree selection and wiki list selection. One absolutely-positioned (or one SVG `<rect>`) element whose `transform`/`y` is animated. This is also a **performance** technique: one animated element instead of N nodes each with a transitioning `fill`. Directly attacks our "sluggish as the tree grows" problem. |
| **Transition only named properties**, never `all`: `transition: background-color .12s ease-out, color .12s ease-out`. | Tree nodes especially — `transition: all` on hundreds of nodes is a repaint bomb. |
| **`active:scale(0.96)`** on buttons, 100 ms. | Top-bar buttons, tab switches, collapse toggles. Costs nothing, makes a local app feel like a native one. |
| **Staggered entrance**: `fade-up 350ms cubic-bezier(.23,1,.32,1)` with `i * 90ms` delay. | Detail-pane content on node change, and search results. Caps at ~5 items or the tail feels slow. |
| **Blurred crossfade** between pages (`stream-in`: `opacity 0→1` + `blur(4px)→0`). | Detail-pane swap when a different node is selected — hides the fact that markdown re-render isn't instant. This is the classic perceived-responsiveness trade: the blur buys you ~200 ms of render time for free. |
| **`requestAnimationFrame` batching for measurement.** Their comment: "requestAnimationFrame batches streaming reflow measurements and avoids visible intermediate positions." They combine it with `ResizeObserver` and cancel the pending frame each call. | Our pan/zoom and any layout recompute. Coalescing `getBoundingClientRect` / tree relayout into one rAF is probably the single biggest fix for tree sluggishness. |
| **Web Animations API for layout**: `el.animate([{width: a},{width: b}], {duration: 320, easing: 'cubic-bezier(.23,1,.32,1)'})` — measure old, set new, animate between, before paint. | Detail-pane width when the tree collapses, or the pane opening. Vanilla, no library. |
| **Shimmer as a text gradient**, not a skeleton box: `background-image: linear-gradient(90deg, var(--ink-3) 35%, var(--ink) 50%, var(--ink-3) 65%); background-size: 200% 100%; -webkit-background-clip: text; color: transparent; animation: shimmer-text 1.4s linear infinite`. | "Loading vault…", "Searching…" in the top bar. One element, theme-aware because it is built from ink tokens. |
| **`will-change: filter, opacity`** used sparingly (exactly once on the site). | Apply to the SVG pan/zoom group only while a gesture is active, then remove. Leaving it on permanently is what usually causes the memory/compositing regression. |
| **Global reduced-motion kill switch** — they ship the standard one *and* per-component opt-outs. | Ship the global one; then make sure the tree's pan/zoom still *works* with motion off, just instantly. |

```css
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after {
    transition-duration: .01ms !important;
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

Their keyframe set, all trivially reusable: `fade-in`, `fade-up`
(`translateY(8px)→0`), `pop-in` (`scale(.95)→1` with `transform-origin` set
to the trigger corner), `stream-in` (opacity + blur), `shimmer-text`,
`caret-blink` (`step-end`), `spin`, `pixel-on`, `eq-bounce`.

### 4.4 Focus and keyboard

This is the **weakest** part of the resource. What is genuinely there:

| Technique | Cockpit application |
|---|---|
| `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px }` as a single global rule, with `outline: none` only on text inputs (which show focus by other means). | Adopt wholesale. One rule, both themes, no per-component focus styling. |
| **Negative offset inside scroll containers**: `.records-scroll:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px }`. | The SVG canvas and the markdown pane — a positive offset would be clipped by the scroller. |
| **The scroll container itself is focusable**: `tabIndex={0}` + `role="region"` + a descriptive `aria-label` ("Companies table. Scroll horizontally and vertically to view all columns and records."). | **Directly applicable and currently missing.** Make the SVG tree a focusable region so Tab reaches it and arrow keys pan/navigate. This is the cheapest single keyboard win available to us. |
| `overscroll-behavior: contain` on inner scrollers. | Detail pane — stops scroll chaining into the page when you hit the bottom of a long note. |
| Arrow-key handling in menus: `ArrowDown`/`ArrowUp` with `event.preventDefault()` and wraparound via `(i + 1) % n`; `Shift` as a ×10 multiplier on a slider. | Search-result navigation, and Shift as a coarse-step modifier for zoom. |
| `aria-expanded` on every disclosure toggle (21 uses), `aria-pressed` on toggle buttons (22), `aria-current` on nav items (4), `aria-hidden` on all decorative SVG (72). | Tree collapse toggles, Tree/Wiki tabs, current node. |
| Pointer/key takeover: `onKeyDownCapture` cancels an autoplaying demo. | Not applicable, but the shape — any real input cancels an animation in flight — matters if we ever auto-focus the tree. |

**What is missing from the site and we must design ourselves:** roving
tabindex, a global command palette / shortcut map, focus trapping in
overlays, skip links, any keyboard route into the SVG canvas beyond focusing
it, and a visible shortcut cheat-sheet. There are `<kbd>` elements on the
site (`10px`, `--surface` background, `5px` radius, `--ink-3`), but they are
decorative — nothing is actually bound. Do not expect help here.

### 4.5 Information density

| Technique | Cockpit application |
|---|---|
| **`tabular-nums` everywhere numbers appear** — 80 uses. Also `font-variant-numeric: tabular-nums` in their table CSS. | Node counts, verifiable counts, timers, any right-aligned figure. Stops the "jitter" of changing digits. |
| **`truncate` + `min-w-0` discipline** — 69 uses, always paired with `min-width: 0` on the flex parent. | Node labels in the tree, wiki titles, breadcrumb. The `min-width: 0` is the part everyone forgets; without it flex children refuse to shrink and ellipsis never fires. |
| **Consistent padding rhythm**: card pad 12px; bar / cell / footer `10px 12px`; icon button 28×28; table header row 42px; footer 38px; toolbar min-height 52px. | Gives us a spacing scale without inventing one: **4px base**, used at 4 / 6 / 8 / 10 / 12 / 16. Their observed gaps: 1, 4, 5, 6, 7, 8, 12, 16px. |
| **Sticky headers and footers inside the scroller** with explicit `z-index` layering (`thead th` z-5, sticky first column z-2, `tfoot` z-4) and each sticky cell painting its own `background: var(--surface)`. | Wiki tables and long markdown tables in the detail pane. The "sticky cells need their own background" rule is a classic bug source. |
| **A sticky first column with a directional shadow**: `box-shadow: 5px 0 8px -10px #0006`. | If the wiki grows a table view. |
| **Row-level micro-affordances that appear on hover *or* focus**: `opacity: 0` → `1` on `:hover` and `:focus-visible`. | Node action buttons — keeps the tree quiet at rest without hiding functionality from the keyboard. Note they bind **both** hover and focus-visible; binding only hover is an a11y bug. |
| **Uppercase micro-labels** for section grouping (10.5px / 650 / `.04em` / `--ink-3`). | Detail-pane section headers ("VERIFIABLES", "FINDINGS") — separates sections without spending a size step. |
| `-mx-1.5 + px-1.5` trick: pull a row out by its own padding so the hover pill can extend past the text without shifting the text's x-position. Their comment: "keeps content at the same x while giving the row hover pills room inside this overflow-hidden clip box". | Wiki list and detail-pane nav items — full-bleed hover highlight with text still aligned to the pane's grid. |
| `user-select: none` on chrome, re-enabled on `input, textarea, [contenteditable], pre, code`; `-webkit-user-drag: none` on `img, svg, canvas`. | The SVG tree — stops text selection during a pan drag, which is currently a common annoyance in any drag-to-pan canvas. **This one is worth doing immediately.** |
| `scrollbar-width: none` on horizontal chip strips. | Tab strip if it ever overflows. Use with care — hidden scrollbars hurt discoverability. |

---

## 5. Theming: what they do, and where they do *not* help us

Their theme switch is:

```html
<script>(function(){try{var t=localStorage.getItem("bui-theme");
document.documentElement.classList.toggle("dark",t!=="light")}catch(e){...}})()</script>
```

Inlined in `<head>`, before first paint, so there is no flash. Two things:

- **Worth copying:** the blocking inline `<head>` script that reads storage
  and stamps the root element before the first paint. Our cockpit should do
  the same or it will flash the wrong theme on every load.
- **Does not help with our OS-follow problem.** There is **no
  `@media (prefers-color-scheme: ...)` anywhere in their 72 KB CSS**. Their
  site defaults to dark and ignores the OS entirely. We must design the
  three-state (system / light / dark) behaviour ourselves. The right shape:

```html
<script>(function(){try{var t=localStorage.getItem("crux-theme")||"system";
var d=t==="dark"||(t==="system"&&matchMedia("(prefers-color-scheme:dark)").matches);
document.documentElement.dataset.theme=d?"dark":"light";}catch(e){}})()</script>
```

plus a `matchMedia(...).addEventListener('change', ...)` that re-stamps
`data-theme` only while the stored preference is `"system"`.

---

## 6. What we must NOT take — closed, do not relitigate

| Item | Why it is out |
|---|---|
| **All 19 components as source** | React + TypeScript + JSX. Every one needs a compiler. Non-negotiable. |
| **Every Tailwind utility class** (`text-[12.5px]`, `size-6`, `-mx-1.5`, `bg-hover-2`, `active:scale-[0.96]`, `focus-visible:*`) | These are generated by the Tailwind v4 build. We can copy the *declarations* they compile to; we cannot copy the class names. Translate to real CSS rules and stop. |
| **`iconoir-react`** | npm dependency. Draw our own inline `<svg>` paths — theirs are simple 24×24 stroke paths at `stroke-width: 2`–`2.2`, `stroke-linecap: round`, trivially re-authored. |
| **`glimm`** (the rainbow WebGL shader sweep in the Prompt Bar) | WebGL library, npm, and it burns GPU next to our SVG canvas. Out. |
| **`liveline`** (the scrubbable charts in Insight Cards) | npm charting library. If we ever want a chart, hand-roll an SVG path. |
| **Inter and JetBrains Mono `.woff2`** | Self-hosted, so not a CDN violation, but they are binary assets we would have to vendor or base64-inline (~200 KB+ per face). Use the system stack: `ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif` and `ui-monospace, "SF Mono", Menlo, monospace`. |
| **`font-feature-settings: "cv11", "ss01"`** | Inter-specific glyph alternates. Meaningless without Inter — drop it rather than carry a dead declaration. |
| **`font-weight: 550` / `650`** | Variable-font weights. The system UI font on macOS handles these, but Linux/Windows fallbacks will snap to 500/700 and the hierarchy will collapse. Stick to 400 / 500 / 600 / 700. |
| **The diagonal repeating-stripe body texture** (`repeating-linear-gradient(-45deg, …)` with `background-attachment: fixed`) | It is showcase chrome for a marketing page. `background-attachment: fixed` is a known scroll-performance hazard, and visual noise behind a node-link diagram is actively harmful. |
| **Next.js / App Router / RSC anything** | Obviously out. |
| **Chat, composer, streaming, approval, tool-chip patterns** | Wrong product. The cockpit is read-only; there is no agent conversation in it. |
| **Their type "scale"** | Nine sizes between 10.5 and 13px is not a scale, it is fitting. Take the *principle* (hierarchy by ink tier + weight in chrome), not the numbers. |

---

## 7. Honest assessment

The site is real, well-crafted, and reachable — but it is **not** the kind of
resource the request assumed. It has no principles, no writing, no
documentation, and no components we can use. Roughly 90% of its surface area
is irrelevant to a read-only tree + markdown viewer.

The remaining 10% is genuinely good and unusually concrete: a battle-tested
light/dark token system that we can paste in almost verbatim, an easing and
duration ladder, and about a dozen implementation tricks — the `0fr → 1fr`
disclosure, the single gliding highlight, rAF-batched measurement, the
focusable scroll region, ring-as-elevation, `tabular-nums`, and the
`user-select` discipline for a drag canvas.

On our four stated problems:

- **Font steps** — helps *indirectly*, and reframes the problem usefully
  (chrome vs reading pane are different problems), but gives no scale.
- **Sluggishness** — helps concretely: gliding highlight, named-property
  transitions, rAF batching, disciplined `will-change`.
- **Keyboard** — barely helps. The focusable-scroll-region idea and the
  global `:focus-visible` rule are the whole harvest.
- **OS theme** — does not help at all; they ignore the OS too. The inline
  no-flash head script is the one thing worth taking.
