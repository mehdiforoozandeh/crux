# crux cockpit — performance diagnosis against the CANDI vault

Measured 2026-08-13. **Diagnosis only — no source files were changed.**

---

## 1. Setup and methodology

| Item | Value |
|---|---|
| Vault | `/Users/mforooz/Desktop/research/libbrechteam@sfu/CANDI/cruxvault` (181 `.md` files on disk) |
| Snapshot | 482,520 bytes; **101 nodes** (76 idea, 23 question, 1 project, 1 synthesis); **100 drawn** tree nodes, 99 edges, max depth 4 |
| Server | `crux serve --dir … --port 8913 --no-open` (pid 46467), stopped at end of run |
| Cockpit source | `/Users/mforooz/crux/skills/crux/scaffold/webui/app.js` (2301 lines), `style.css` (599 lines) |
| Browser | Claude browser pane — **Chromium 148 / Electron 42**, 8 cores, DPR 2, viewport 1280×720 |
| DOM at rest | **1352 SVG elements**, **520 `<text>` elements**, 117 KB of `svg.innerHTML` |

Instrumentation was injected with `javascript_tool`: the globals `renderTree`, `layout`,
`onSnapshot`, `treeSimTick` and `window.fetch` were monkey-patched to record wall time and
call counts; `PerformanceObserver({entryTypes:['longtask']})` for long tasks; a `rAF`
counter for frame times. Every timing below wraps the call in
`performance.now()` and, where noted, follows it with `void document.body.offsetHeight` to
force a synchronous style + layout flush, so the number includes the browser work the call
queues, not only the JS.

### What could NOT be measured — read this before acting on anything below

1. **Paint / raster / composite cost is entirely absent from these numbers.**
   The Claude browser pane reports `document.hidden === true` and `visibilityState:
   "hidden"` for its whole life. `requestAnimationFrame` never fires (4 frames in 7.4 s,
   and only because a screenshot forced a capture); `performance.getEntriesByType('paint')`
   is empty. So the renderer never rasterizes. Everything below is **JS + style recalc +
   layout**. The stages that SVG-heavy UIs actually die on — rasterizing 520 text runs at
   DPR 2, recompositing ten `backdrop-filter: blur()` panels stacked over the tree, running
   ~100 concurrent CSS opacity transitions — produce **zero** cost in this environment.

2. **Achieved frame rate during a relayout could not be measured** for the same reason.
   The living-tree sim (`treeSimLoop`) explicitly bails on `document.hidden`, so it never
   ran on its own. Per-frame *JS* cost was measured by calling `treeSimTick` / `treeSimDraw`
   in a synchronous loop instead.

3. **Safari was not tested.** The user's machine is a Mac and the code comments in `app.js`
   (lines 310–312, 575–581, 653–655) repeatedly cite Safari-specific measurements
   (14 fps vs 60, 60 fps drag dropping to ~20). Chromium's SVG pipeline is not Safari's.
   If the lag is observed in Safari, the paint-side items in §8 are the likeliest cause and
   this report does not price them.

4. Interaction was driven by **synthetic events** (`dispatchEvent`), not a real pointer.
   That reproduces the handler and style work faithfully but not the browser's real event
   coalescing (a trackpad delivers wheel/pointermove faster than one per frame).

---

## 2. Cold load — time to first tree paint

From `performance.getEntriesByType('navigation' | 'resource')` after a clean reload:

| Phase | Start (ms) | Duration (ms) |
|---|---|---|
| HTML response end | — | 220.5 |
| `style.css` (41 KB) | 230.3 | 40.9 |
| `app.js` (114 KB) | 230.4 | 41.8 |
| `vendor/motion.js` (**140 KB**) | 230.4 | 41.5 |
| DOMContentLoaded / load | 278.3 | — |
| `snapshot.json` (482 KB) | 278.2 | 39.0 |
| `JSON.parse` of the 482 KB body | — | **1.2** (p50 0.9) |
| `layout()` | — | **0.5** (p50) |
| `renderTree()` | — | **4.1** (p50 JS) / ~6.6 incl. layout flush |

**Time to first tree ≈ 325–340 ms**, of which the cockpit's own tree code is **~7 ms
(2 %)**. The rest is asset transfer + the serial dependency `page load → snapshot fetch →
render`: the snapshot request does not start until after DOMContentLoaded at 278 ms.

Notes:
- `vendor/motion.js` is **140 KB — larger than `app.js`** — and is a render-blocking
  `<script>` before it (index.html:94).
- The snapshot is not preloaded; adding `<link rel="preload" as="fetch">` would recover
  ~50 ms.

---

## 3. `renderTree()` — cost per call and how often it runs

### 3a. Cost, decomposed (100 nodes, 1352 elements, 114 KB string)

| Phase | p50 (ms) | p95 | max | n |
|---|---|---|---|---|
| String build only (walk + `nodeSVG` × 100 + `edgeD` × 99) | **0.30** | 3.4 | 3.4 | 20 |
| `svg.innerHTML = …` (parse + DOM construction, JS-visible) | **2.0** | 3.4 | 3.4 | 20 |
| `innerHTML` **+ forced synchronous layout** | **8.8** | 19.5 | 19.5 | 20 |
| `treeSimBind()` (2 × `querySelectorAll` + full `treeSimDraw(true)`) | 2.2 | 12.2 | 12.2 | 20 |
| **Whole `renderTree()`, JS only** | **4.1** | 13.8 | 13.8 | 20 |
| **Whole `renderTree()` + layout flush** | **6.6–10.9** | 29.4 | 29.6 | 25 |

The string build is **not** the problem (0.3 ms). The cost is `innerHTML` teardown +
re-parse of 1352 elements (2 ms) and the browser layout that follows (~7 ms).

### 3b. Call frequency per action (measured with a call counter)

| Action | `renderTree()` calls | `layout()` calls | Wall incl. flush |
|---|---|---|---|
| **Idle, 55.8 s** (28 polls) | **0** | **0** | 0 |
| Collapse a 36-node branch | 1 | 1 | 6.1 ms |
| Density toggle (detail↔compact) | 1 | 1 | 9.4 / 12.2 ms |
| Orientation toggle (lr↔td) | 1 | 1 | 8.6 / 19.1 ms |
| View mode (tidy↔radial) | 1 | 1 | 10.1 / 8.0 ms |
| **Search — per keystroke** | **1** | 0 | **6.4–32.0 ms** |
| **Click a node (`selectNode`)** | **1** | 0 | 10.9 ms (of a 23.4 ms total) |
| Click "Review" (`showQueue`) | 1 | 0 | 17.8 ms (p95 40.4) |
| Snapshot content change (`onSnapshot`) | 1 | 1 | **21.4 ms** (max 30.4) |

Typing the 10-character word `imputation` in the search box produced **10 full SVG
rebuilds, 127.5 ms of wall time, worst single keystroke 32.0 ms**. There is no debounce
(`app.js:1490` → `applySearch()` → `renderTree()`).

---

## 4. Is `renderTree()` called by the 1 Hz poll when nothing changed? — **NO**

Instrumented over a **55.8 s idle window**:

```
polls issued          : 28
HTTP 304 responses    : 28   (100 %)
onSnapshot() calls    : 0
renderTree() calls    : 0
layout() calls        : 0
treeSimDraw() calls   : 0
rAF frames            : 0
long tasks            : 0
```

The gating is correct and doubly belt-and-braces: `serve.py:154` computes the ETag as a
SHA-256 of the serialized snapshot (content hash, so it is stable across requests —
verified: two consecutive requests returned the identical ETag `"755d682b4df8a268270bfccbd331692f"`),
and `poll()` additionally compares the raw text against `state.lastJSON` before calling
`onSnapshot()`. **An idle cockpit costs the browser nothing.** This prime suspect is cleared.

**But the server side is not free.** `serve.py` regenerates the whole snapshot on *every*
request in order to compute the ETag, then throws it away for a 304:

- `crux.snapshot()` + `json.dumps` = **29 ms of Python per poll** (curl, 5 runs: 61, 29, 29, 29, 29 ms)
- measured process CPU: **0.24 s over a 10 s window = ~2.4 % of one core, continuously, forever**, and it re-reads 181 markdown files each second.

---

## 5. `treeSimDraw()` / the living-tree sim — **not a bottleneck**

100 sim nodes, 99 edge elements, 4950 repulsion pairs per warm tick.

| Measurement | p50 (ms) | p95 | max | n |
|---|---|---|---|---|
| `treeSimTick`, cool (`heat = 0`, repulsion skipped) | 0.0 | 0.1 | 0.9 | 200 |
| `treeSimTick`, **warm** (full O(n²) = 4950 pairs) | **0.10** | 0.2 | 1.7 | 200 |
| `treeSimDraw(true)` — forced full write, 100 nodes + 99 edges | 0.10 | 0.6 | 1.3 | 50 |
| `treeSimDraw(false)`, cool, nothing moved | **0.00** | 0.1 | 1.1 | 200 |
| `treeSimDraw(false)`, warm, nothing moved | **0.00** | 0.1 | 1.2 | 100 |
| Full warm frame (jiggle all 100 + tick + draw) | 0.10 | 0.3 | 0.6 | 100 |
| …same **+ forced layout flush** | **0.50** | 0.7 | 9.2 | 60 |

**The dirty-gating works exactly as documented.** A cool frame with nothing moving costs
0.00 ms; the `_wx/_wy` and `e.px/e.py` epsilon guards genuinely skip the writes. A
worst-case frame with all 100 nodes in motion costs **0.5 ms including layout** — a 33×
headroom against a 16.7 ms budget *in JS/layout terms*. In Chromium the sim could not be
made to cost anything.

**Caveat and future cliff:** the O(n²) repulsion is 0.10 ms at n=100. It scales as n²:
≈2.5 ms at n=500, ≈10 ms at n=1000. At around 700–900 drawn nodes the warm-frame tick
alone starts eating the frame budget. Not this vault's problem.

---

## 6. Interaction latency

All numbers include a forced style + layout flush. Synthetic events; no paint.

| Interaction | p50 (ms) | p95 | max | n |
|---|---|---|---|---|
| **Pan drag** — `applyTransform()`, one attribute write | 0.05 | 0.1 | 0.2 | 30 |
| Pan drag + forced layout read | 0.16–0.28 | 0.4 | 0.7 | 60 |
| **Wheel zoom** — real `zoomAt()`, monotone ramp | **0.40** | 1.1 | 1.5 | 40 |
| Wheel zoom — raw scale write + `getBoundingClientRect()` | 0.20 | 0.4 | 1.7 | 40 |
| **Hover a node** (`pointerover` handler, fresh node) | **0.90** | 1.5 | 1.6 | 25 |
| Hover-out (`pointerout`, clears 98 classes) | 1.20 | 1.9 | 2.1 | 25 |
| 12 redundant repeats crossing one node's children | 0.80 | 2.0 | 2.8 | 25 |
| **Click a node** (`selectNode`) | **23.4** | 32.1 | 35.6 | 25 |
| ├─ `renderTree()` (full SVG rebuild) | 10.9 | 29.4 | 29.6 | 25 |
| ├─ `renderDetail()` | 7.3 | 23.6 | 26.4 | 25 |
| ├─ `updateToolbar()` | 0.5 | 1.0 | 1.1 | 25 |
| ├─ `updateReviewBtn()` | 0.3 | 0.4 | 0.4 | 25 |
| └─ `renderCrumb()` | 0.0 | 0.0 | 0.3 | 25 |
| **the same visual effect via a 2-class swap** | **0.19** | 0.3 | 0.7 | 40 |
| Click "Review" (`showQueue`) | 17.8 | 40.4 | 40.4 | 15 |
| **Search keystroke** | 6.4–9.8 | — | **32.0** | 10 |
| Snapshot-change handler `onSnapshot()` | **21.4** | 30.4 | 30.4 | 20 |

`longtask` PerformanceObserver registered **0 long tasks** during the idle window; the
observer was installed successfully (no `no-longtask` mark was recorded).

One transient anomaly: an early, unrepeatable run measured `zoomAt` at 3.6 ms p50 /
31.9 ms max over 100 samples. Four subsequent isolation runs (including one deliberately
performed while 98 nodes carried live opacity transitions) all returned 0.1–0.4 ms p50. The
first run is treated as an artifact (GC or a cold layout path after 20 back-to-back
`innerHTML` rewrites), not a reproducible cost. Flagged because if it *is* real and
intermittent, `zoomAt`'s `svg.getBoundingClientRect()` on every wheel event
(`app.js:1062`) is a forced synchronous layout inside the event handler and is the thing
to remove.

### 6a. The hover spotlight — amplification, but cheap in JS

`svg.addEventListener("pointerover", …)` (app.js:1154) does, on **every** `pointerover`:

- `svg.querySelectorAll(".edge")` → 99 elements, `classList.toggle("hot", …)` on each
- `svg.querySelectorAll(".node")` → 100 elements, `classList.toggle("cold", …)` on each
- **199 class writes per event**

Measured amplification:

- a node group contains **12 child elements** (rect, qbar, text runs, vdots, toggle)
- crossing one node fires the handler **12 times** — verified with a counting probe
- there is **no guard** for "this is the same node that is already `.hov`", so 11 of those
  12 runs are pure waste
- after one hover, `svgEl.querySelectorAll('.node.cold').length` = **98**, and
  `document.getAnimations().length` = **105** (vs 4 at rest)

`.node.cold { opacity: .38 }` (style.css:302) combined with
`.node { transition: opacity .18s ease }` (style.css:300) means **one mouse-over starts a
180 ms opacity animation on 98 SVG groups covering the entire tree**, and hover-out starts
98 more. In this hidden-pane environment that costs ~1 ms because nothing repaints. **In a
visible window it is a full-tree repaint held for 180 ms on every hover-in and every
hover-out.** This is the single strongest structural candidate for the reported lag, and it
is exactly the axis the environment prevented me from pricing.

---

## 7. Focus mode vs no focus

Same measurement battery in three states:

| | no focus | focus-open | focus-node (`q10`) |
|---|---|---|---|
| Drawn nodes | **100** | 64 | **21** |
| SVG elements | **1352** | 890 | **279** |
| `<text>` elements | **520** | 327 | **104** |
| `svg.innerHTML` bytes | 117,014 | 76,012 | 21,972 |
| `renderTree()` + flush, p50 | **7.5 ms** | 3.5 ms | **2.7 ms** |
| `renderTree()` + flush, p95 | 144.8 ms* | 6.8 ms | 3.8 ms |
| Wheel-zoom event, p50 | 0.10 ms | 0.10 ms | 0.10 ms |
| Pan event, p50 | 0.05 ms | 0.05 ms | 0.05 ms |
| Search, 6 keystrokes total | **45.2 ms** | 27.8 ms | **7.3 ms** |
| CSS animations started per hover | 105 | ~65 | ~22 |

\* single 144.8 ms outlier in a 12-sample run; the p50 of 7.5 ms is the representative figure.

**Attribution.** In the JS/style/layout layer, focus mode buys **2.8× on `renderTree()`**
and **6.2× on search**, and **nothing at all** on pan and zoom (both flat at
0.05–0.10 ms in all three states). That is *not enough* to explain "smooth in focus mode,
laggy out of it" — pan and zoom are the interactions where lag is felt, and they are
identical.

The difference that *does* track the user's report is the one this environment cannot
price: **4.8× fewer SVG elements, 5× fewer text runs, 4.8× fewer concurrently-animating
groups per hover, over a 5.3× smaller painted area.** Every one of those is a paint/raster
multiplier, not a JS multiplier. The conclusion is therefore: **the lag is in paint, not in
script.** The specific paint amplifiers are listed next.

---

## 8. Scaling — cost is LINEAR in drawn nodes, with no fixed overhead

Measured by collapsing top-level branches progressively and re-running the battery:

| Drawn nodes | SVG els | `<text>` | `renderTree()` p50 | `renderTree()`+flush p50 | zoom evt p50 | `.morph` toggle p50 |
|---|---|---|---|---|---|---|
| 100 | 1352 | 520 | 5.4 | 6.6 | 0.2 | **7.8** |
| 95 | 1292 | 493 | 3.9 | 6.5 | 0.1 | 7.3 |
| 90 | 1232 | 467 | 4.1 | 5.7 | 0.2 | 7.0 |
| 87 | 1197 | 452 | 4.1 | 6.1 | 0.1 | 7.0 |
| 83 | 1151 | 433 | 3.7 | 6.0 | 0.2 | 7.8 |
| 80 | 1118 | 420 | 3.6 | 7.0 | 0.1 | 6.3 |
| 77 | 1081 | 403 | 2.9 | 5.0 | 0.2 | 6.6 |
| 71 | 1011 | 373 | 2.4 | 5.7 | 0.1 | 6.4 |
| 34 | 487 | 170 | 2.6 | 2.1 | 0.1 | **2.5** |
| 21 | 287 | 106 | 1.1 | 1.8 | 0.1 | 0.9 |
| 20 | 268 | 100 | 1.6 | 2.2 | 0.2 | 1.4 |

`renderTree` cost ≈ **4.5 µs per SVG element**, intercept ≈ 0. **Linear, not superlinear,
and not dominated by a fixed overhead.** Halving the drawn nodes halves the cost.

Pan and zoom event cost is **flat at 0.1 ms** across the whole range — in Chromium with no
paint, transform writes on the viewport `<g>` are free regardless of subtree size.

---

## 9. Other findings, from reading + targeted probes

1. **`.morph` toggle costs 7.8 ms at 100 nodes.** `treeSimBind()` adds `svg.morph` whenever
   more than 12 nodes move (app.js:663), and `#tree.morph .lbl, .glyph, .vdot, .code-div
   { display: none }` (style.css:164) flips `display` on ~1000 elements — a full style
   recalc plus a full SVG layout, twice (once on, once off) per relayout. It is a
   deliberate Safari mitigation, and it is not free: 7.8 ms × 2 per collapse / orientation
   change / snapshot update.

2. **Ten `backdrop-filter: blur(3px)` panels sit on top of the tree canvas**: `#legend`,
   `#legend-btn`, `#focus-crumb`, `#zoom-in`, `#zoom-out`, `#zoom-fit`, `#help-btn`, plus
   the wiki equivalents and `#detail-fontctl` (style.css:175, 199, 211, 231, 259, 278, 496,
   510, 519). A `backdrop-filter` forces the compositor to re-sample and re-blur its
   backdrop whenever *anything underneath it changes* — which, during a pan, a zoom, or any
   sim frame, is the entire tree. This is a per-frame compositing cost that is **independent
   of node count** and invisible to every measurement in this report.

3. **`.node.running .box { animation: pulse 1.8s infinite }` with `filter: brightness()`
   keyframes** (style.css:347–348) runs forever. This vault has exactly **1** running node,
   so it is minor here — but an animated `filter` on an SVG element keeps the compositor
   awake permanently and repaints that node's region at display rate for as long as the
   cockpit is open.

4. **`.node .box` declares a 4-property transition** including `filter` (style.css:288), and
   `.node:hover .box { filter: brightness(1.3) saturate(1.15) }` (style.css:301). SVG
   `filter` is not compositor-accelerated in the same way `opacity`/`transform` are; a
   filter transition on hover forces a repaint of the affected region for 160 ms.

5. **`renderDetail()` costs 7.3 ms p50 / 26.4 ms max for a pane containing 26 elements.**
   That is ~280 µs per element and is far out of line with the rest of the app. Every child
   of `#detail-content` also carries `animation: d-in .28s both` (style.css:189), so a
   selection change starts 26 simultaneous entrance animations. Worth a look; it is the
   second-largest term in the 23.4 ms node click.

6. **`selectNode()` rebuilds the entire SVG to move one CSS class** (app.js:775). Measured:
   10.9 ms for the rebuild vs **0.19 ms** for the equivalent two-class swap — a **55×**
   difference for an identical visual result. `showQueue()` (app.js:786) does the same.

7. **The search input has no debounce** (app.js:1490). Each keystroke triggers a complete
   114 KB `innerHTML` teardown and rebuild of 1352 elements, plus a `treeSimBind()`
   re-query. It also destroys and recreates the DOM under the cursor mid-type, which re-fires
   `pointerover` and re-triggers the 98-group opacity spotlight.

8. **`onSnapshot()` costs 21.4 ms (max 30.4 ms) end-to-end and runs on every vault change.**
   Idle is free, but during an active agent session — the normal crux workflow, where an
   agent is writing files — the vault changes constantly, so this fires at up to 1 Hz, each
   time with a full rebuild, a warm sim glide, and a `.morph` flicker. If the user's "lag"
   is observed *while an agent is working*, this is the loop to look at.

9. **`vendor/motion.js` is 140 KB and render-blocking** (index.html:94), for what is used
   only for entrance fades.

---

## 10. Ranked bottlenecks, by measured cost

| # | Bottleneck | Measured cost | Confidence | Implied fix |
|---|---|---|---|---|
| 1 | Hover spotlight repaints the whole tree: 199 class writes/event, **98 groups** given a 180 ms opacity transition, **105 concurrent animations**, handler fires **12× per node** (no same-node guard) | 0.9–1.2 ms JS/style per event **+ unmeasured full-tree repaint held 180 ms**, ×2 per node crossed | High on the mechanism, **unmeasured on the paint cost** | Guard on "same node already `.hov`"; dim by toggling one class on the viewport `<g>` (`#tree.spot .node:not(.hov)`) instead of 98 per-element classes; drop or shorten the opacity transition |
| 2 | `selectNode()` / `showQueue()` rebuild the whole SVG to move one class | **23.4 ms** per node click (10.9 ms rebuild + 7.3 ms detail); the equivalent class swap is **0.19 ms** — **55×** | High, directly measured | Swap the `.selected` class in place; only rebuild when the tree's structure changes |
| 3 | Undebounced search — one full `innerHTML` rebuild per keystroke | **127.5 ms** for a 10-char word; worst keystroke **32.0 ms**; 6.2× worse without focus mode | High, directly measured | Debounce ~120 ms, and dim via class toggles rather than a rebuild |
| 4 | `onSnapshot()` full rebuild on every vault change | **21.4 ms** (max 30.4), up to 1 Hz while an agent is writing | High, directly measured | Diff the snapshot and patch; skip `layout()`/`renderTree()` when only node *content* changed |
| 5 | Ten stacked `backdrop-filter: blur()` overlays over the tree canvas | **Not measurable here** (no compositing). Node-count-independent per-frame cost | Medium — structural | Drop `backdrop-filter` on the tree-pane overlays, or use an opaque background |
| 6 | Server regenerates the 482 KB snapshot on every 1 Hz poll to compute the ETag, then answers 304 | **29 ms of Python/poll**, **2.4 % of a core continuously**, 181 files re-read per second | High, directly measured | Cache the snapshot keyed on max mtime of the vault; skip regeneration when nothing changed |
| 7 | `.morph` class flips `display` on ~1000 elements, twice per relayout | **7.8 ms** per toggle at 100 nodes | High, directly measured | Use `visibility`/`opacity` on a parent `<g>` instead of `display:none` on 1000 leaves |
| 8 | `renderDetail()` — 7.3 ms p50 / 26.4 ms max for 26 elements, plus 26 entrance animations | 7.3 ms, second-largest term in a node click | High on the number, cause not isolated | Profile it; drop the per-child `d-in` animation |

### Explicitly cleared

- **The 1 Hz poll does not re-render.** 28/28 polls returned 304 over 55.8 s; 0 calls to
  `onSnapshot`, `layout`, `renderTree`, `treeSimDraw`; 0 rAF frames; 0 long tasks. The ETag
  is a stable content hash and `poll()` also text-diffs. **An idle cockpit is genuinely free
  in the browser.**
- **The living-tree sim is not the problem.** Warm tick 0.10 ms, forced full draw 0.10 ms,
  cool no-op draw 0.00 ms. The dirty-gating skips work exactly as documented. Headroom
  ~33× at this vault size. (It becomes O(n²)-bound somewhere past ~700 drawn nodes.)
- **Pan and zoom JS is not the problem.** 0.05 ms and 0.10–0.40 ms per event, flat across
  20→100 drawn nodes and identical in and out of focus mode.
- **Cold load is not the problem.** ~330 ms, of which the tree code is ~7 ms.
- **Scaling is linear**, ~4.5 µs per SVG element, no fixed-overhead floor.

### The honest bottom line

At 100 drawn nodes, **in Chromium, the cockpit's script and layout are fast** — nothing in
the JS layer is slow enough to be felt as continuous lag, and the two suspects named up
front (poll-driven re-render, sim per-frame cost) are both cleared with hard numbers. Three
discrete hitches are real and measured: a **23 ms node click**, a **32 ms worst-case search
keystroke**, and a **21 ms snapshot update**.

The *continuous* lag the user reports, and the focus-mode difference, do **not** appear in
the numbers this environment can produce, because this environment never paints. The
evidence points at paint/composite: the hover spotlight animating 98 groups' opacity for
180 ms at a time, over 520 text runs, under ten live `backdrop-filter` blurs — all of which
shrink by ~5× in focus mode, exactly matching the reported symptom. **Confirming that needs
a visible window and a real profiler** (Safari Web Inspector's Timelines, or Chrome DevTools
Performance with paint flashing), which the Claude browser pane cannot provide.

## 11. Suggested next step to close the gap

Open the cockpit in the user's own Safari and Chrome against this vault with the devtools
Performance panel recording, and capture two traces: (a) mouse sweeping across the tree
with no clicks, (b) the same in focus-node mode. If the hover-spotlight hypothesis is
right, trace (a) will show a continuous band of Paint/Composite work correlated with
`pointerover`, absent from (b). A zero-risk A/B without touching source: in the console,
run `document.getElementById('tree').replaceWith(...)` — or simply
`getComputedStyle`-neutralize the transition with
`document.head.insertAdjacentHTML('beforeend','<style>.node{transition:none!important}.node.cold{opacity:1!important}</style>')`
and re-do the sweep. If the lag vanishes, bottleneck #1 is confirmed.
