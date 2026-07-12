/* crux cockpit — read-only. Polls /snapshot.json (~1s), lays out a deterministic
   hierarchical tree, and shows a review queue / node detail on the right.
   No writes, no build step, no dependencies. */
"use strict";

const VERDICTS = ["supported", "partial", "refuted", "inconclusive"];

// Node geometry comes in two densities. "detail" (the default) sizes every box to fit its
// full title, word-wrapped up to MAX_LINES, so a question or hypothesis is readable without
// clicking it; "compact" is the one-line truncated map view. Kinds are sized to be told
// apart at a glance — questions are deliberately BIGGER than hypotheses (box and font), and
// the root is a colorless pill carrying the Crux mark.
//   cw/ch = compact box   dw = detail width (height follows the wrapped text)
//   cpl   = chars per wrapped line (detail)   ctrunc = truncation (compact)
//   shape: questions are sharp-cornered rectangles (container/"header" look); hypotheses and
//   the root are full pills/stadiums (rx = half-height). That shape split — plus the width and
//   font gap — is what tells the two kinds apart at a glance in either density.
const KIND = {
  project:   { cw: 210, ch: 36, dw: 250, pill: true, lbl: "t-root", lh: 16,   cpl: 28, ctrunc: 24 },
  question:  { cw: 202, ch: 34, dw: 270, rx: 4,      lbl: "t-q",    lh: 15.5, cpl: 34, ctrunc: 26 },
  idea:      { cw: 150, ch: 24, dw: 206, pill: true, lbl: "t-h",    lh: 13.5, cpl: 30, ctrunc: 17 },
  synthesis: { cw: 172, ch: 26, dw: 172, rx: 0,      lbl: "t-s",    lh: 14,   cpl: 23, ctrunc: 23 },
};
const MAX_LINES = 4;
const geomOf = (id) => state.nodeGeom[id];
// verdict glyph shown inside a done hypothesis (colored by verdict)
const GLYPH = { supported: "✓", partial: "◐", refuted: "✕", inconclusive: "~" };
// Every question & hypothesis carries its short code (Q10 / H13) on the LEFT of the node —
// monospace so digits align, measured with the same font the CSS renders so the left gutter
// fits it snugly. Root/synthesis have no code. In compact density the code is ALL a node shows.
const MONO = "ui-monospace, SFMono-Regular, Menlo, monospace";
const codeFontOf = (type) => (type === "question" ? "700 15px " : "650 12.5px ") + MONO;
const codeOf = (id, type) => (type === "project" || type === "synthesis") ? "" : String(id).toUpperCase();

function wrapLines(text, cpl) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let cur = "";
  for (let i = 0; i < words.length; i++) {
    const cand = cur ? cur + " " + words[i] : words[i];
    if (cand.length <= cpl || !cur) { cur = cand; continue; }
    if (lines.length === MAX_LINES - 1) {          // out of lines — ellipsize the remainder
      const rest = cur + " " + words.slice(i).join(" ");
      lines.push(rest.length > cpl ? rest.slice(0, cpl - 1) + "…" : rest);
      return lines;
    }
    lines.push(cur); cur = words[i];
  }
  if (cur) lines.push(cur);
  return lines.length ? lines : [""];
}

// Per-snapshot geometry: id -> {w, h, rx, lines, lh, dotsPad}. Synthesis stays single-line
// in both densities (a diamond doesn't wrap well and it's a link marker, not content).
function computeGeom() {
  const g = {};
  for (const [id, n] of Object.entries(state.snap.nodes)) {
    const k = KIND[n.type] || KIND.question;
    const code = codeOf(id, n.type);        // "Q10" / "H13" — questions & hypotheses only
    let w, h, lines, dotsPad = 0, gutter = 0;
    if (n.type === "project") {
      // snug pill sized to the Crux mark + centred title — no empty slack
      lines = [trunc(n.title, 42)];
      w = Math.round(ROOT_PAD * 2 + ROOT_MARK_W + ROOT_MARK_GAP + measure(lines[0], ROOT_FONT));
      h = 42;
    } else if (n.type === "synthesis") {
      lines = [trunc(n.title, k.ctrunc)];   // (never drawn, but keep geometry defined)
      w = k.cw; h = k.ch;
    } else if (state.density === "compact") {
      // compact = a codes-only map: the box carries just its code (Q10 / H13), nothing else
      const isQ = n.type === "question";
      lines = [code];
      dotsPad = n.type === "idea" && (n.verifiables || []).length ? 11 : 0;   // bottom badge row
      let cw = measure(code, codeFontOf(n.type)) + 30;
      if (dotsPad) cw = Math.max(cw, (Math.min(n.verifiables.length, 8) - 1) * 12 + 22);  // fit the dot row
      w = Math.max(cw, isQ ? 56 : 44); h = k.ch + dotsPad;
    } else {
      // detail = a left code gutter (Q10 / H13) + the wrapped title to its right
      const isQ = n.type === "question", codeX = isQ ? 14 : 11, basePad = isQ ? 15 : 12;
      lines = wrapLines(n.title, k.cpl);
      dotsPad = n.type === "idea" && (n.verifiables || []).length ? 16 : 0;   // bottom badge row
      gutter = codeX + measure(code, codeFontOf(n.type)) + 12;                // left gutter fits the code
      w = gutter + (k.dw - basePad);                                          // keep the title zone width
      h = Math.max(k.ch, 9 + lines.length * k.lh + 9 + dotsPad);
    }
    g[id] = { w, h, rx: k.pill ? h / 2 : k.rx, lines, lh: k.lh, dotsPad, kind: n.type, code, gutter };
  }
  return g;
}

const state = {
  snap: null,
  lastJSON: "",
  collapsed: new Set(),     // node ids whose subtree is hidden (client-only)
  selected: null,           // node id, or null => review queue
  view: { tx: 60, ty: 40, k: 1 },
  positions: {},            // id -> {x, y, depth}
  childCount: {},           // id -> number of tree children (drives the ± toggle)
  nodeGeom: {},             // id -> {w, h, rx, lines, lh, dotsPad} for the current density
  orient: localStorage.getItem("crux-orient") || "lr",       // "lr" | "td"
  density: localStorage.getItem("crux-density") || "detail", // "detail" | "compact"
  focused: false,           // focus-open mode: all non-open questions collapsed
  search: "",
  filter: null,             // legend chip key (e.g. "h-supported"), or null = show all
  centered: false,          // one-time fit after first snapshot
  tab: "tree",              // "tree" | "wiki" — applied from localStorage once wiki.active is known
  wiki: {
    selected: localStorage.getItem("crux-wiki-slug") || null,  // slug, or null => the _index page
    page: null,             // fetched /wiki/<slug>.json payload for the reader
    pageKey: "",            // slug+hash of the fetched page — refetch when the index says it changed
    readerKey: "",          // last-rendered reader signature — re-render only on change
    positions: null,        // slug -> {x, y} (deterministic force layout)
    layoutKey: "",          // page-set + edge signature — relayout only when the graph changed
    railKey: "",            // last-rendered rail signature
    view: { tx: 40, ty: 40, k: 1 },
    centered: false,        // one-time graph fit on first show
    folds: new Set(),       // collapsed rail folders (category names, or "sources")
    railHidden: localStorage.getItem("crux-wiki-rail") === "1",
  },
};

const $ = (id) => document.getElementById(id);
const svg = $("tree");

// ------------------------------------------------------------------ polling
async function poll() {
  try {
    const r = await fetch("snapshot.json", { cache: "no-store" });
    if (r.ok) {
      const txt = await r.text();
      $("offline").hidden = true;
      if (txt !== state.lastJSON) {
        state.lastJSON = txt;
        state.snap = JSON.parse(txt);
        onSnapshot();
      }
    }
  } catch (e) {
    $("offline").hidden = false;   // keep last-known view; positions stay put
  }
  setTimeout(poll, 1000);
}

function onSnapshot() {
  const snap = state.snap;
  $("project-title").textContent = snap.project.title || "";
  // drop selection if the node disappeared
  if (state.selected && !(state.selected in snap.nodes)) state.selected = null;
  updateTabs();
  updateReviewBtn();
  layout();
  // One-time fit — but a tab opened in the background has a 0×0 rect until it's shown,
  // so keep retrying on each poll until the pane has real geometry to fit against.
  if (!state.centered && fitToView()) state.centered = true;
  renderLegend();
  renderTree();
  renderWiki();
  renderDetail();
}

// ------------------------------------------------------------------ deterministic layout
// A tidy tree in either orientation. Every subtree gets a slot along the MAIN axis
// (y when left-right, x when top-down) sized max(own extent, sum of child slots); the
// CROSS axis advances per depth by that depth's tallest/widest node. Same structure =>
// same positions, so nodes never jump on auto-refresh; collapsed nodes lay out as leaves.
// pos[id] = { x: left edge, y: vertical center }.
function layout() {
  const snap = state.snap, geom = (state.nodeGeom = computeGeom());
  const pos = {}, kids = {};
  const GAP = 14, CROSS_GAP = state.orient === "td" ? 56 : 70;
  const horiz = state.orient !== "td";
  const mainOf = (id) => (horiz ? geom[id].h : geom[id].w);
  const ext = {}, depthOf = {}, center = {}, maxCross = [];
  (function measure(node, depth) {
    kids[node.id] = node.children ? node.children.length : 0;   // true count (for the toggle)
    depthOf[node.id] = depth;
    maxCross[depth] = Math.max(maxCross[depth] || 0, horiz ? geom[node.id].w : geom[node.id].h);
    const shown = state.collapsed.has(node.id) ? [] : node.children;
    let e = mainOf(node.id) + GAP;
    if (shown.length) {
      let sum = 0;
      for (const c of shown) sum += measure(c, depth + 1);
      e = Math.max(e, sum);
    }
    return (ext[node.id] = e);
  })(snap.tree, 0);
  (function place(node, start) {
    const shown = state.collapsed.has(node.id) ? [] : node.children;
    if (!shown.length) center[node.id] = start + ext[node.id] / 2;
    else {
      let cur = start + (ext[node.id] - shown.reduce((s, c) => s + ext[c.id], 0)) / 2;
      for (const c of shown) { place(c, cur); cur += ext[c.id]; }
      center[node.id] = (center[shown[0].id] + center[shown[shown.length - 1].id]) / 2;
    }
  })(snap.tree, 0);
  const crossAt = [0];
  for (let d = 0; d < maxCross.length; d++) crossAt[d + 1] = crossAt[d] + maxCross[d] + CROSS_GAP;
  for (const id in depthOf) {
    const d = depthOf[id], g = geom[id];
    pos[id] = horiz ? { x: crossAt[d], y: center[id] }
                    : { x: center[id] - g.w / 2, y: crossAt[d] + g.h / 2 };
  }
  // synthesis nodes are intentionally NOT laid out or drawn in the cockpit — they add clutter
  // without helping navigation. (They still exist in the vault and the JSON snapshot.)
  state.positions = pos;
  state.childCount = kids;
}

// ------------------------------------------------------------------ tree render
function statusClass(n) {
  if (n.type === "project") return "n-project";
  if (n.type === "synthesis") return "n-synth";
  if (n.type === "question") return "q-" + n.status;
  if (n.status === "done") return "h-" + (n.verdict || "inconclusive");
  return "h-" + n.status;
}

// edge path between two nodes, from a position map (so it can be recomputed each frame while
// animating a relayout). Left-right: right edge -> left edge. Top-down: bottom -> top centre.
function edgeD(paId, chId, pos) {
  const pa = pos[paId], pb = pos[chId], ga = geomOf(paId), gb = geomOf(chId);
  if (state.orient !== "td") {
    const x1 = pa.x + ga.w, y1 = pa.y, x2 = pb.x, y2 = pb.y, mx = (x1 + x2) / 2;
    return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
  }
  const x1 = pa.x + ga.w / 2, y1 = pa.y + ga.h / 2, x2 = pb.x + gb.w / 2, y2 = pb.y - gb.h / 2, my = (y1 + y2) / 2;
  return `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
}

// Verifiable badges on a hypothesis (LOCAL coords). Three meanings:
//   met  -> filled green (approved)
//   unmet on a CLOSED hypothesis -> filled red (tested & rejected)
//   anything else (unmet-but-not-yet-tested, or n/a) -> hollow circle (not decided)
// Detail: their own row along the bottom-left, clear of the pill's rounded right cap.
// Compact: inline near the right edge (there's no room for a row).
function vBadgeClass(v, n) {
  if (v.state === "met") return "v-met";
  if (v.state === "unmet" && n.status === "done") return "v-unmet";
  return "v-pending";
}
function verifDots(n, g) {
  const vs = (n.verifiables || []).slice(0, 8);
  if (!vs.length) return "";
  const compact = state.density === "compact";
  const r = compact ? 4 : 5, gap = compact ? 12 : 15;
  const x0 = g.w / 2 - ((vs.length - 1) * gap) / 2;   // centre the row on the box
  const y = g.h / 2 - r - 4;                            // bottom
  return vs.map((v, i) => `<circle class="vdot ${vBadgeClass(v, n)}" cx="${x0 + i * gap}" cy="${y}" r="${r}"/>`).join("");
}

// A node is a <g> positioned by `transform="translate(anchorX, anchorY)"`; everything inside is
// drawn relative to that anchor (0,0). This lets a relayout animate by tweening just the wrapper
// transform (and the edge paths) instead of rebuilding geometry.
function nodeSVG(n, p) {
  const g = geomOf(n.id), k = KIND[n.type] || KIND.question, cls = statusClass(n);
  const sel = state.selected === n.id ? " selected" : "";
  const matches = state.search && matchNode(n);
  const dimmed = (state.search && !matches) || (state.filter && cls !== state.filter);
  const wrap = "node" + (n.status === "running" ? " running" : "") +
    (dimmed ? " dim" : "") + (matches ? " hit" : "");
  const shape = `<rect class="box k-${n.type} ${esc(cls)}${sel}" x="0" y="${-g.h / 2}" width="${g.w}" height="${g.h}" rx="${g.rx}"/>`;
  // questions get a bold left accent stripe (in their status colour) so they read as containers
  const qbar = n.type === "question"
    ? `<rect class="qbar ${esc(cls)}" x="0" y="${-g.h / 2 + 3}" width="4" height="${g.h - 6}" rx="2"/>` : "";
  const inner = n.type === "project" ? rootLabel(n, g, k) : bodyLabel(n, g, k);
  const dots = n.type === "idea" ? verifDots(n, g) : "";
  const hasKids = (state.childCount && state.childCount[n.id]) || 0;
  const tcx = state.orient !== "td" ? g.w : g.w / 2;
  const tcy = state.orient !== "td" ? 0 : g.h / 2;
  const toggle = hasKids
    ? `<g class="toggle" data-toggle="${esc(n.id)}"><circle cx="${tcx}" cy="${tcy}" r="7.5"/>` +
      `<text x="${tcx}" y="${tcy + 3.5}" text-anchor="middle">${state.collapsed.has(n.id) ? "+" : "−"}</text></g>`
    : "";
  const tipStatus = n.type === "idea" && n.verdict ? n.verdict : n.status;
  const tip = `<title>${esc(n.title)} — ${esc(n.type)} · ${esc(tipStatus)}</title>`;
  return `<g class="${wrap}" data-id="${esc(n.id)}" transform="translate(${p.x},${p.y})">` +
    `${tip}${shape}${qbar}${inner}${dots}${toggle}</g>`;
}

// Canvas text measurement so we can size the (snug) root box to its content.
const _mctx = document.createElement("canvas").getContext("2d");
const FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif";
const ROOT_FONT = "780 16.5px " + FAMILY;
function measure(text, font) { _mctx.font = font; return _mctx.measureText(text).width; }

// the Crux constellation mark, drawn at local x (vertically centred on the node anchor)
function rootMark(x) {
  return `<g class="rootmark" transform="translate(${x},-8) scale(0.19)">` +
    `<g class="mk-l"><line x1="38" y1="8" x2="33" y2="76"/><line x1="8" y1="44" x2="60" y2="38"/></g>` +
    `<g class="mk-s"><circle cx="38" cy="8" r="4"/><circle cx="33" cy="76" r="5"/>` +
    `<circle cx="8" cy="44" r="4"/><circle cx="60" cy="38" r="3.4"/><circle cx="45" cy="60" r="2.4"/></g></g>`;
}
const ROOT_MARK_W = 14, ROOT_MARK_GAP = 7, ROOT_PAD = 15;

// project root: the Crux mark next to the centred title, in a snug pill
function rootLabel(n, g, k) {
  const nameW = measure(g.lines[0], ROOT_FONT);
  const startX = (g.w - (ROOT_MARK_W + ROOT_MARK_GAP + nameW)) / 2;
  const tx = startX + ROOT_MARK_W + ROOT_MARK_GAP;
  return rootMark(startX) + `<text class="lbl ${k.lbl}" x="${tx}" y="4">${esc(g.lines[0])}</text>`;
}

// question / hypothesis body. Compact: ONLY the code (Q10 / H13), centred. Detail: the code in
// a left gutter, then the verdict glyph (ideas) plus the wrapped title, left-aligned beside it.
function bodyLabel(n, g, k) {
  const codeCls = n.type === "question" ? "t-code t-code-q" : "t-code t-code-h";
  if (state.density === "compact") {
    return `<text class="lbl ${codeCls}" x="${g.w / 2}" y="${-g.dotsPad / 2 + 5}" text-anchor="middle">${esc(g.code)}</text>`;
  }
  const codeX = n.type === "question" ? 14 : 11;
  // the code sits at the box's TRUE vertical middle (y=0 + baseline nudge), independent of the
  // verifiable-dots row — the divider separates it from the title, so it needn't line up with it
  const codeEl = g.code ? `<text class="lbl ${codeCls}" x="${codeX}" y="4">${esc(g.code)}</text>` : "";
  const divEl = g.code ? `<line class="code-div" x1="${g.gutter - 6}" y1="${-g.h / 2 + 7}" x2="${g.gutter - 6}" y2="${g.h / 2 - 7}"/>` : "";
  const startX = g.gutter;
  const y0 = -g.dotsPad / 2 - ((g.lines.length - 1) * g.lh) / 2 + 4;
  const glyph = n.type === "idea" && n.verdict
    ? `<text class="glyph" x="${startX}" y="${y0}" style="fill:var(--v-${esc(n.verdict)})">${GLYPH[n.verdict]}</text>`
    : "";
  const lbl = g.lines.map((ln, i) => {
    const x = i === 0 && glyph ? startX + 13 : startX;
    return `<text class="lbl ${k.lbl}" x="${x}" y="${y0 + i * g.lh}">${esc(ln)}</text>`;
  }).join("");
  return codeEl + divEl + glyph + lbl;
}

// `fromPos`, when given, is the previous position map; surviving nodes animate from there to
// their new spots (and entrants fade in). Synthesis nodes are never in `positions`, so never drawn.
function renderTree(fromPos) {
  const snap = state.snap, pos = state.positions;
  let edges = "", nodes = "";
  (function walk(node) {
    if (state.collapsed.has(node.id)) return;
    for (const c of node.children) {
      edges += `<path class="edge" data-p="${esc(node.id)}" data-c="${esc(c.id)}" d="${edgeD(node.id, c.id, pos)}"/>`;
      walk(c);
    }
  })(snap.tree);
  for (const id in pos) nodes += nodeSVG(snap.nodes[id], pos[id]);
  const v = state.view;
  svg.innerHTML = `<g class="viewport" transform="translate(${v.tx},${v.ty}) scale(${v.k})">${edges}${nodes}</g>`;
  if (fromPos && !REDUCED_MOTION) animateLayout(fromPos);
}

// Pan/zoom only mutate the group transform — one cheap attribute write; the browser batches
// the actual paint per frame. Deliberately synchronous (not rAF-coalesced): rAF stops firing
// in an occluded/background window, which would leave the view stale until the next interaction.
function applyTransform() {
  const g = svg.firstChild;
  if (g) g.setAttribute("transform", `translate(${state.view.tx},${state.view.ty}) scale(${state.view.k})`);
}

// ------------------------------------------------------------------ motion
const REDUCED_MOTION = matchMedia("(prefers-reduced-motion: reduce)").matches;
const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

// Tween nodes from their previous positions to the freshly-rendered ones, redrawing edges each
// frame so they stay attached. Surviving nodes glide; new nodes fade in place.
let _layoutRAF = 0;
function animateLayout(fromPos) {
  cancelAnimationFrame(_layoutRAF);
  // renderTree already drew nodes at their FINAL positions; only animate if rAF will actually
  // run. In a hidden/background tab rAF is paused, so skipping leaves the correct final state
  // (rather than the synchronous first frame stranding nodes at their old positions).
  if (document.hidden) return;
  const vp = svg.firstChild;
  if (!vp) return;
  const pos = state.positions;
  const nodeEls = {};
  vp.querySelectorAll(".node").forEach((el) => (nodeEls[el.getAttribute("data-id")] = el));
  const edgeEls = [...vp.querySelectorAll(".edge")].map((el) =>
    ({ el, p: el.getAttribute("data-p"), c: el.getAttribute("data-c") }));
  const DUR = 400, t0 = performance.now();
  function frame(now) {
    const e = easeOutCubic(Math.min(1, (now - t0) / DUR));
    const ip = {};
    for (const id in pos) {
      const np = pos[id], op = fromPos[id] || np;
      ip[id] = { x: op.x + (np.x - op.x) * e, y: op.y + (np.y - op.y) * e };
    }
    for (const id in nodeEls) {
      const q = ip[id];
      if (q) nodeEls[id].setAttribute("transform", `translate(${q.x},${q.y})`);
      if (!fromPos[id]) nodeEls[id].style.opacity = String(e);   // entrants fade in
    }
    for (const { el, p, c } of edgeEls) if (ip[p] && ip[c]) el.setAttribute("d", edgeD(p, c, ip));
    if (e < 1) _layoutRAF = requestAnimationFrame(frame);
    else for (const id in nodeEls) if (!fromPos[id]) nodeEls[id].style.opacity = "";
  }
  frame(t0);
}

// Glide the camera (pan + zoom together) to a target view. Used for programmatic moves —
// fit, centre-on-node, the zoom buttons — while drag and wheel stay 1:1 (they cancel this).
let _viewRAF = 0;
function tweenView(tx, ty, k, dur = 440) {
  cancelAnimationFrame(_viewRAF);
  // reduced-motion or a hidden tab (rAF paused): jump straight to the target
  if (REDUCED_MOTION || document.hidden) { state.view = { tx, ty, k }; applyTransform(); return; }
  const s = { ...state.view }, t0 = performance.now();
  function frame(now) {
    const e = easeOutCubic(Math.min(1, (now - t0) / dur));
    state.view = { tx: s.tx + (tx - s.tx) * e, ty: s.ty + (ty - s.ty) * e, k: s.k + (k - s.k) * e };
    applyTransform();
    if (e < 1) _viewRAF = requestAnimationFrame(frame);
  }
  _viewRAF = requestAnimationFrame(frame);
}
function stopViewTween() { cancelAnimationFrame(_viewRAF); }

// The legend is the color key for the tree; every chip is also a filter — click one to
// spotlight only nodes in that state (click again, or another chip, to change/clear).
// Chip keys match statusClass() outputs so filtering is a straight comparison.
const LEGEND = [
  ["questions", [
    ["q-open", "--q-open", "open", "Question — open, still being worked"],
    ["q-review", "--q-review", "review", "Question — awaiting your decision (the review gate)"],
    ["q-resolved", "--q-resolved", "resolved", "Question — resolved by your decision"],
  ]],
  ["hypotheses", [
    ["h-running", "--h-running", "running", "Hypothesis — experiment running now"],
    ["h-supported", "--v-supported", "supported", "Hypothesis — verdict: supported (approved)"],
    ["h-partial", "--v-partial", "partial", "Hypothesis — verdict: partially supported"],
    ["h-refuted", "--v-refuted", "refuted", "Hypothesis — verdict: refuted (rejected)"],
  ]],
];

function renderLegend() {
  const head = `<div class="lg-head"><span class="lg-title">Color key</span>` +
    `<button type="button" class="lg-hide" data-legend-hide title="Hide the color key" aria-label="Hide the color key">×</button></div>`;
  $("legend").innerHTML = head + LEGEND.map(([group, items]) =>
    `<div class="lg-row"><span class="lg-group">${group}</span>` +
    items.map(([key, varName, label, tip]) =>
      `<button type="button" class="lg${state.filter === key ? " on" : ""}" data-lg="${key}"` +
      ` style="--c:var(${varName})" title="${esc(tip)} — click to spotlight">` +
      `<span class="sw"></span>${label}</button>`).join("") + `</div>`).join("");
}

// show/hide the color key (persisted); a small "Key" button takes its place when hidden
function setLegendHidden(hidden) {
  $("legend").hidden = hidden;
  $("legend-btn").hidden = !hidden;
  localStorage.setItem("crux-legend-hidden", hidden ? "1" : "0");
}

// ------------------------------------------------------------------ search / navigation
function matchNode(n) {
  const q = state.search.toLowerCase();
  return q && (n.title.toLowerCase().includes(q) || n.id.toLowerCase().includes(q));
}

// Returns the view {tx,ty,k} that frames the whole tree, or null if there's nothing/no room.
function fitView() {
  const ids = Object.keys(state.positions);
  if (!ids.length) return null;
  const r = svg.getBoundingClientRect();
  if (r.width < 80 || r.height < 80) return null;   // hidden/background tab — nothing to fit against
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const id of ids) {
    const p = state.positions[id], g = geomOf(id);
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x + g.w);
    minY = Math.min(minY, p.y - g.h / 2 - 10); maxY = Math.max(maxY, p.y + g.h / 2 + 10);
  }
  const k = clamp(Math.min(1, (r.width - 60) / (maxX - minX || 1), (r.height - 60) / (maxY - minY || 1)), 0.12, 1);
  return { k, tx: 30 - minX * k, ty: (r.height - (maxY - minY) * k) / 2 - minY * k };
}

// fit the tree to the pane. animate => glide there; otherwise snap. Returns false if it couldn't.
function fitToView(animate) {
  const v = fitView();
  if (!v) return false;
  if (animate) tweenView(v.tx, v.ty, v.k);
  else { state.view = v; applyTransform(); }
  return true;
}

function centerOn(id, animate) {
  const p = state.positions[id];
  if (!p) return;
  const r = svg.getBoundingClientRect(), k = state.view.k;
  const tx = r.width / 2 - (p.x + geomOf(id).w / 2) * k, ty = r.height / 2 - p.y * k;
  if (animate === false) { state.view.tx = tx; state.view.ty = ty; applyTransform(); }
  else tweenView(tx, ty, k);
}

// ------------------------------------------------------------------ selection / detail
function selectNode(id, opts) {
  state.selected = id;
  updateReviewBtn();
  renderTree();
  renderDetail();
  if (opts && opts.center) centerOn(id);   // used when jumping from the queue / a detail link / search
}

function showQueue() {
  if (state.tab !== "tree") setTab("tree");   // the review gate lives in the tree view
  state.selected = null;
  updateReviewBtn();
  renderTree();
  renderDetail();
}

function updateReviewBtn() {
  const n = state.snap ? state.snap.queue.length : 0;
  const b = $("review-btn");
  b.textContent = `Review (${n})`;
  b.classList.toggle("active", state.tab === "tree" && state.selected === null);
  b.classList.toggle("has-queue", n > 0);
}

function badge(text, varName, cls) {
  const style = varName ? ` style="--b:var(${esc(varName)})"` : "";
  return `<span class="badge ${cls || ""}${varName ? " dot" : ""}"${style}>${esc(text)}</span>`;
}

function section(title, html) { return `<div class="sec"><h4>${title}</h4>${html}</div>`; }
function bodyOr(text, empty) {
  if (!(text && text.trim())) return `<div class="body muted">${empty}</div>`;
  // tree nodes may cite the wiki as [[wiki/slug]] (never the reverse) — make those live:
  // click one and the cockpit switches to the Wiki tab with that page open in the reader
  const html = esc(text).replace(
    /\[\[\s*wiki\/([^\]|#\\]+?)\s*(?:(?:\\\||\||#)([^\]]*))?\]\]/g,
    (m, t, alias) => wikiLink("wiki/" + t, alias));
  return `<div class="body">${html}</div>`;
}

function renderDetail() {
  const pane = $("detail-content");
  if (!state.snap) { pane.innerHTML = ""; return; }
  if (state.tab === "wiki") { renderWikiReader(); return; }
  state.wiki.readerKey = "";   // leaving the wiki reader — force a fresh render on return
  const n = state.selected ? state.snap.nodes[state.selected] : null;
  pane.innerHTML = n ? nodeDetail(n) : queueDetail();
}

function queueDetail() {
  const q = state.snap.queue;
  const head = `<div class="d-kind">review gate</div><div class="d-title">Awaiting your decision</div>`;
  if (!q.length) return head + `<p class="d-empty">No questions are waiting on a decision.</p>`;
  const rows = q.map((r) =>
    `<button class="rowlink" data-go="${esc(r.id)}"><span class="rid">${esc(r.id)}</span>${esc(r.title)}` +
    `<span class="rsum">${esc(r.summary)}</span></button>`).join("");
  return head + `<div class="sec">${rows}</div>`;
}

function nodeDetail(n) {
  if (n.type === "question") return questionDetail(n);
  if (n.type === "idea") return ideaDetail(n);
  if (n.type === "synthesis") return synthesisDetail(n);
  return projectDetail(n);
}

function head(kind, title) { return `<div class="d-kind">${kind}</div><div class="d-title">${esc(title)}</div>`; }

function projectDetail(n) {
  return head("project", n.title) + section("Goal", bodyOr(state.snap.project.goal, "—"));
}

function questionDetail(n) {
  const qColor = { open: "--q-open", review: "--q-review", resolved: "--q-resolved" }[n.status];
  let badges = badge(n.status, qColor);
  if (n.stale) badges += badge("stale", null, "stale");
  const l = n.ledger;
  const ledger = `<div class="body">` +
    `${l.children} children · ${l.ideas_done}/${l.ideas_total} hypotheses done` +
    (l.subq_total ? ` · ${l.subq_resolved}/${l.subq_total} sub-questions resolved` : "") + `<br>` +
    VERDICTS.map((k) => `${l[k]} ${k}`).join(" · ") + `</div>`;
  const kids = n.children.map((cid) => childLink(cid)).join("");
  // the question's own framing (## Question); shown only when it adds to the title
  const stmt = n.detail && n.detail.trim() && n.detail.trim() !== n.title.trim()
    ? section("Detail", bodyOr(n.detail, "")) : "";
  return head("question", n.title) + `<div class="badges">${badges}</div>` +
    stmt +
    section("Answer so far", bodyOr(n.answer, "not yet interpreted")) +
    section("Evidence ledger", ledger) +
    (kids ? section("Children", `<div>${kids}</div>`) : "");
}

function ideaDetail(n) {
  let badges = badge(n.status, { idea: "--h-idea", staged: "--h-staged", running: "--h-running", done: null }[n.status] || null);
  if (n.verdict) badges += badge(n.verdict, "--v-" + n.verdict);
  if (n.metric) badges += `<span class="badge">metric <span class="inline">${esc(n.metric)}</span></span>`;
  const vs = n.verifiables.length
    ? `<ul class="verif">` + n.verifiables.map((v) => {
        const m = { met: ["met", "✓"], unmet: ["unmet", ""], na: ["na", "–"] }[v.state];
        return `<li><span class="tick ${m[0]}">${m[1]}</span><span>${esc(v.text)}</span></li>`;
      }).join("") + `</ul>`
    : `<div class="body muted">none registered</div>`;
  const runs = n.run_links.length
    ? `<ul class="linklist">` + n.run_links.map((r) => `<li>${esc(r)}</li>`).join("") + `</ul>`
    : `<div class="body muted">none</div>`;
  return head("hypothesis", n.title) + `<div class="badges">${badges}</div>` +
    section("Problem", bodyOr(n.problem, "—")) +
    section("Verifiables", vs) +
    section("Run links", runs) +
    section("Findings", bodyOr(n.findings, "not closed yet"));
}

function synthesisDetail(n) {
  const rel = n.related.length
    ? n.related.map((cid) => childLink(cid)).join("")
    : `<div class="body muted">none</div>`;
  return head("synthesis", n.title) + section("Related questions", `<div>${rel}</div>`);
}

function childLink(cid) {
  const c = state.snap.nodes[cid];
  if (!c) return "";
  const kind = c.type === "question" ? "Q" : c.type === "idea" ? "H" : c.type[0].toUpperCase();
  const extra = c.type === "idea" && c.verdict ? ` — ${c.verdict}` : ` — ${c.status}`;
  return `<button class="rowlink" data-go="${esc(cid)}"><span class="rid">${esc(kind)} ${esc(cid)}</span>${esc(c.title)}` +
    `<span class="rsum">${esc(extra.slice(3))}</span></button>`;
}

// ------------------------------------------------------------------ helpers
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function trunc(s, n) { s = s || ""; return s.length > n ? s.slice(0, n - 1) + "…" : s; }
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

// ------------------------------------------------------------------ interaction wiring
// Pan and select are separate gestures. A pointerdown starts a *possible* pan; only once the
// pointer travels past DRAG_THRESHOLD does it become a real pan (and suppress the trailing
// click). We deliberately do NOT call setPointerCapture on the <svg>: capturing retargets the
// follow-up `click` to the svg itself, so `e.target.closest('.node')` would be null and every
// node click / ± toggle would no-op. Instead, while a pan is live we listen on `window`, so the
// drag keeps tracking even when the cursor leaves the svg and always ends cleanly.
const DRAG_THRESHOLD = 5;
let pan = null, moved = false;

// cursor-anchored zoom by `factor` about viewport point (cx, cy)
function zoomAt(cx, cy, factor) {
  const v = state.view, r = svg.getBoundingClientRect();
  const k2 = clamp(v.k * factor, 0.1, 3);
  if (k2 === v.k) return;
  const mx = cx - r.left, my = cy - r.top;
  v.tx = mx - (mx - v.tx) * (k2 / v.k);
  v.ty = my - (my - v.ty) * (k2 / v.k);
  v.k = k2;
  applyTransform();
}

// Trackpad-first zoom: a two-finger scroll zooms about the cursor, and a pinch (which the
// browser reports as ctrl+wheel) zooms too, at a higher sensitivity to feel 1:1 with the
// gesture. deltaMode normalizes mouse wheels that report lines instead of pixels.
svg.addEventListener("wheel", (e) => {
  e.preventDefault();
  stopViewTween();   // wheel/pinch is 1:1 — never fight a running camera glide
  const dy = e.deltaMode === 1 ? e.deltaY * 20 : e.deltaY;
  const sens = e.ctrlKey ? 0.012 : 0.0028;
  zoomAt(e.clientX, e.clientY, Math.exp(-dy * sens));
}, { passive: false });

function onPanMove(e) {
  if (!pan) return;
  const dx = e.clientX - pan.x, dy = e.clientY - pan.y;
  if (!moved && dx * dx + dy * dy > DRAG_THRESHOLD * DRAG_THRESHOLD) {
    moved = true;
    svg.classList.add("panning");
  }
  if (moved) {
    state.view.tx = pan.tx + dx;
    state.view.ty = pan.ty + dy;
    applyTransform();
  }
}
function onPanEnd() {
  window.removeEventListener("pointermove", onPanMove);
  window.removeEventListener("pointerup", onPanEnd);
  window.removeEventListener("pointercancel", onPanEnd);
  svg.classList.remove("panning");
  pan = null;   // `moved` stays set until the trailing click reads it; next pointerdown clears it
}
svg.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  e.preventDefault();   // a drag on the canvas must never start a text selection
  stopViewTween();      // grabbing the canvas cancels any running camera glide
  pan = { x: e.clientX, y: e.clientY, tx: state.view.tx, ty: state.view.ty };
  moved = false;
  window.addEventListener("pointermove", onPanMove);
  window.addEventListener("pointerup", onPanEnd);
  window.addEventListener("pointercancel", onPanEnd);
});

// Hover spotlight — parity with the wiki graph's responsiveness: the touched node
// lights up, its edges heat, everything unrelated cools. A CSS-only brightness change
// was imperceptible at tree zoom levels; the spotlight is what reads as "responsive".
svg.addEventListener("pointerover", (e) => {
  const node = e.target.closest(".node");
  if (!node || pan) return;
  const id = node.getAttribute("data-id");
  const nb = new Set([id]);
  svg.querySelectorAll(".edge").forEach((el) => {
    const p = el.getAttribute("data-p"), c = el.getAttribute("data-c");
    if (p === id) nb.add(c);
    if (c === id) nb.add(p);
    el.classList.toggle("hot", p === id || c === id);
  });
  node.classList.add("hov");
  svg.querySelectorAll(".node").forEach((el) =>
    el.classList.toggle("cold", !nb.has(el.getAttribute("data-id"))));
});
svg.addEventListener("pointerout", (e) => {
  if (!e.target.closest(".node")) return;
  if (e.relatedTarget && e.relatedTarget.closest &&
      e.relatedTarget.closest(".node") === e.target.closest(".node")) return;
  svg.querySelectorAll(".hot, .cold, .hov").forEach((el) =>
    el.classList.remove("hot", "cold", "hov"));
});

svg.addEventListener("click", (e) => {
  if (moved) return;   // the pointer travelled — this was a pan, not a click
  const tog = e.target.closest("[data-toggle]");
  if (tog) {
    const from = state.positions;             // animate the subtree collapse/expand
    const id = tog.getAttribute("data-toggle");
    state.collapsed.has(id) ? state.collapsed.delete(id) : state.collapsed.add(id);
    if (state.focused) { state.focused = false; updateToolbar(); }   // manual toggle leaves focus mode
    layout(); renderTree(from);
    return;
  }
  const node = e.target.closest(".node");
  if (node) selectNode(node.getAttribute("data-id"));
});

$("detail-pane").addEventListener("click", (e) => {
  // Scope to the font BUTTONS: #detail-content also carries a data-font attribute (it drives the
  // text-size CSS), so a bare closest("[data-font]") swallows every click inside the detail
  // content — including the review-queue rows and child links — and their data-go never fires.
  const fbtn = e.target.closest("#detail-fontctl [data-font]");
  if (fbtn) { setDetailFont(fbtn.getAttribute("data-font")); return; }
  const wl = e.target.closest("[data-wiki]");
  if (wl) { openWikiPage(wl.getAttribute("data-wiki")); return; }   // [[wiki/…]] citations + reader links
  const go = e.target.closest("[data-go]");
  if (go) selectNode(go.getAttribute("data-go"), { center: true });
});

// detail-pane text size — small / medium (default) / large, persisted
function setDetailFont(size) {
  document.getElementById("detail-content").dataset.font = size;
  [...document.querySelectorAll("#detail-fontctl button")].forEach((b) =>
    b.classList.toggle("on", b.getAttribute("data-font") === size));
  localStorage.setItem("crux-detail-font", size);
}
setDetailFont(localStorage.getItem("crux-detail-font") || "medium");

$("review-btn").addEventListener("click", showQueue);

// legend chips: click to spotlight one status; click again (or another chip) to change/clear
$("legend").addEventListener("click", (e) => {
  if (e.target.closest("[data-legend-hide]")) { setLegendHidden(true); return; }
  const chip = e.target.closest("[data-lg]");
  if (!chip) return;
  const key = chip.getAttribute("data-lg");
  state.filter = state.filter === key ? null : key;
  renderLegend();
  if (state.snap) renderTree();
});
$("legend-btn").addEventListener("click", () => setLegendHidden(false));
setLegendHidden(localStorage.getItem("crux-legend-hidden") === "1");

// controls-help hint: the ? button shows/hides it (persisted)
$("help-btn").addEventListener("click", () => {
  const hint = document.querySelector("#help .hint");
  hint.hidden = !hint.hidden;
  localStorage.setItem("crux-help-hidden", hint.hidden ? "1" : "0");
});
document.querySelector("#help .hint").hidden = localStorage.getItem("crux-help-hidden") === "1";

// theme: resolve saved preference (else system) once at boot, then the button toggles
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  $("theme-btn").textContent = t === "dark" ? "☀" : "☾";
}
// dark is the default; only a saved preference (the toggle) can switch to light
applyTheme(localStorage.getItem("crux-theme") === "light" ? "light" : "dark");
$("theme-btn").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("crux-theme", next);
  applyTheme(next);
});

// ------------------------------------------------------------------ tree toolbar
// orientation (left-right / top-down) · node text (full / compact) · focus open questions.
// `refit` glides the camera to the new fit (for big reshapes: orientation, density); otherwise
// the camera holds still and only the nodes glide (for local changes: focus, collapse).
function relayout(refit) {
  if (!state.snap) return;
  const from = state.positions;
  layout();
  renderTree(from);
  if (refit) { const v = fitView(); if (v) tweenView(v.tx, v.ty, v.k); }
}
// each toolbar button shows an icon AND a text label of its CURRENT mode
function iconLabel(icon, label) { return `<span class="ic">${icon}</span><span class="tb-label">${label}</span>`; }
function updateToolbar() {
  const ob = $("orient-btn");
  ob.innerHTML = state.orient === "td" ? iconLabel("⇅", "Top-down") : iconLabel("⇄", "Left-right");
  ob.title = state.orient === "td" ? "Layout: top-down — click for left-to-right" : "Layout: left-to-right — click for top-down";
  const db = $("density-btn");
  db.innerHTML = state.density === "detail" ? iconLabel("☰", "Full text") : iconLabel("▭", "Compact");
  db.title = state.density === "detail"
    ? "Nodes: full text — click for compact one-line nodes"
    : "Nodes: compact — click for full-text nodes you can read without opening";
  const fb = $("focus-btn");
  fb.classList.toggle("on", state.focused);
  fb.innerHTML = iconLabel("◎", state.focused ? "Focused" : "Focus open");
  fb.title = state.focused
    ? "Focus on — showing only open questions; click to show everything"
    : "Focus — collapse every non-open question, keep what still needs work";
}
$("orient-btn").addEventListener("click", () => {
  state.orient = state.orient === "td" ? "lr" : "td";
  localStorage.setItem("crux-orient", state.orient);
  updateToolbar(); relayout(true);
});
$("density-btn").addEventListener("click", () => {
  state.density = state.density === "detail" ? "compact" : "detail";
  localStorage.setItem("crux-density", state.density);
  updateToolbar(); relayout(true);
});
$("focus-btn").addEventListener("click", () => {
  if (!state.snap) return;
  if (!state.focused) {
    state.collapsed = new Set(Object.values(state.snap.nodes)
      .filter((n) => n.type === "question" && n.status !== "open").map((n) => n.id));
    state.focused = true;
  } else {
    state.collapsed.clear();
    state.focused = false;
  }
  updateToolbar(); relayout();
});
updateToolbar();

// on-screen zoom controls — glide to the new zoom about the tree-pane centre
function centerZoom(factor) {
  const r = svg.getBoundingClientRect(), v = state.view;
  const k2 = clamp(v.k * factor, 0.1, 3);
  if (k2 === v.k) return;
  const mx = r.width / 2, my = r.height / 2;
  tweenView(mx - (mx - v.tx) * (k2 / v.k), my - (my - v.ty) * (k2 / v.k), k2, 260);
}
$("zoom-in").addEventListener("click", () => centerZoom(1.35));
$("zoom-out").addEventListener("click", () => centerZoom(1 / 1.35));
$("zoom-fit").addEventListener("click", () => { if (state.snap) fitToView(true); });

// the one search box is scoped to the active tab: tree nodes, or wiki pages (rail + graph)
function applySearch() {
  if (!state.snap) return;
  if (state.tab === "wiki") { state.wiki.railKey = ""; renderWikiRail(); dimWikiGraph(); }
  else renderTree();
}
$("search").addEventListener("input", (e) => {
  state.search = e.target.value.trim();
  applySearch();
});
$("search").addEventListener("keydown", (e) => {
  if (e.key === "Escape") { e.target.value = ""; state.search = ""; applySearch(); return; }
  if (e.key !== "Enter" || !state.search || !state.snap) return;
  if (state.tab === "wiki") {
    const hit = wikiPages().find(matchWiki);
    if (hit) openWikiPage(hit.slug);
    return;
  }
  const hit = Object.keys(state.positions).find((id) => matchNode(state.snap.nodes[id]));
  if (hit) selectNode(hit, { center: true });
});

// ================================================================== wiki tab
// A read-only browser over the vault's literature layer (docs/prd/gui-wiki-tab.md):
// explorer rail + deterministic force-directed link graph on the left, a stable
// markdown reader on the right. The index rides the snapshot poll; page bodies are
// fetched lazily from /wiki/<slug>.json. Motion (vendor/motion.js) is progressive
// enhancement — everything works, just unanimated, if the file is absent.
const wsvg = $("wiki-graph");
const RESERVED = { _index: "index", _log: "log", _schema: "schema" };
const M = window.Motion || null;
// `keyframes` uses Motion's [from, to] array form, e.g. { opacity: [0, 1], y: [6, 0] }.
// SVG caveat: never animate transform/scale on a <g> positioned by its transform
// ATTRIBUTE — Motion writes style.transform, which overrides it. Opacity only there.
function animateIn(els, keyframes, opts) {
  els = [...(els || [])];
  if (!M || REDUCED_MOTION || document.hidden || !els.length) return;
  try { M.animate(els, keyframes, { duration: 0.3, ease: [0.22, 0.61, 0.36, 1], ...opts }); }
  catch (e) { /* animation is decoration — never let it break the cockpit */ }
}

function wikiPages() { return (state.snap && state.snap.wiki && state.snap.wiki.pages) || []; }
function wikiActive() { return !!(state.snap && state.snap.wiki && state.snap.wiki.active); }
function wikiHasSlug(slug) {
  return slug in RESERVED || wikiPages().some((p) => p.slug === slug);
}
function matchWiki(p) {
  const q = state.search.toLowerCase();
  return q && (p.slug.toLowerCase().includes(q)
    || String(p.title || "").toLowerCase().includes(q)
    || String(p.summary || "").toLowerCase().includes(q));
}

// a live wikilink (or a visibly-broken one, when no such page exists). `target` may carry a
// dir prefix / .md — resolved the way the engine's link parser does.
function wikiLink(target, alias) {
  const slug = String(target).trim().split("/").pop().replace(/\.md$/, "");
  const label = String(alias == null ? "" : alias).trim() || String(target).trim();
  return wikiHasSlug(slug)
    ? `<a class="wl" data-wiki="${slug}">${label}</a>`
    : `<span class="wl broken" title="no wiki page named ‘${slug}’">${label}</span>`;
}

// ------------------------------------------------------------------ tabs
function setTab(tab) {
  if (tab === "wiki" && !wikiActive()) tab = "tree";
  state.tab = tab;
  localStorage.setItem("crux-tab", tab);
  document.body.dataset.tab = tab;
  $("tree-pane").hidden = tab !== "tree";
  $("wiki-pane").hidden = tab !== "wiki";
  document.querySelectorAll("#tabs [data-tab]").forEach((b) =>
    b.classList.toggle("on", b.getAttribute("data-tab") === tab));
  $("search").placeholder = tab === "wiki" ? "Search wiki pages — Enter to open"
                                           : "Search nodes — Enter to jump";
  updateReviewBtn();
  applySearch();
  renderDetail();
  if (tab === "wiki") {
    renderWiki();
    if (!state.wiki.centered && fitWikiGraph()) state.wiki.centered = true;
    wikiReheat(0.1);   // a gentle settle-in breath; resumes any pending motion
    animateIn([$("wiki-pane"), $("detail-content")], { opacity: [0.35, 1] }, { duration: 0.25 });
  } else if (state.snap) {
    retryFit();
    animateIn([$("tree-pane"), $("detail-content")], { opacity: [0.35, 1] }, { duration: 0.25 });
  }
}
let _tabsBooted = false;
function updateTabs() {
  const active = wikiActive();
  $("tabs").hidden = !active;
  if (!active && state.tab === "wiki") { setTab("tree"); return; }
  if (!_tabsBooted && active) {
    _tabsBooted = true;
    if (localStorage.getItem("crux-tab") === "wiki") { setTab("wiki"); return; }
  }
  if (active && state.tab === "wiki") renderWiki();
}
$("tabs").addEventListener("click", (e) => {
  const b = e.target.closest("[data-tab]");
  if (b) setTab(b.getAttribute("data-tab"));
});

function renderWiki() {
  if (!wikiActive() || state.tab !== "wiki") return;
  renderWikiRail();
  layoutWikiGraph();
  refreshWikiPage();
}

// ------------------------------------------------------------------ explorer rail
// wiki/ is flat by convention; the folders are *virtual* — the raw `category:` frontmatter
// values (exactly WIKI.md's grouping, `uncategorized` included), plus the pinned specials.
function renderWikiRail() {
  const w = state.snap.wiki;
  const key = JSON.stringify([w.pages.map((p) => [p.slug, p.category]), w.sources,
    w.specials, [...state.wiki.folds], state.wiki.selected, state.search, state.wiki.railHidden]);
  if (key === state.wiki.railKey) return;
  state.wiki.railKey = key;
  const rail = $("wiki-rail");
  rail.classList.toggle("hidden", state.wiki.railHidden);
  // the divider sets an inline flex width; it must yield to collapse and come back after
  const savedW = parseInt(localStorage.getItem("crux-wiki-rail-w") || "", 10);
  rail.style.flex = state.wiki.railHidden ? "" : (savedW ? `0 0 ${savedW}px` : "");
  $("wiki-rail-divider").style.display = state.wiki.railHidden ? "none" : "";
  $("wiki-rail-btn").textContent = state.wiki.railHidden ? "⟩" : "⟨";
  $("wiki-rail-btn").title = state.wiki.railHidden ? "Expand the explorer" : "Collapse the explorer";
  const q = state.search;
  const shown = q ? w.pages.filter(matchWiki) : w.pages;
  const cats = {};
  for (const p of shown) (cats[p.category] = cats[p.category] || []).push(p);
  const item = (p) => `<button class="wr-item${state.wiki.selected === p.slug ? " on" : ""}"` +
    ` data-wiki="${esc(p.slug)}" title="${esc(p.title || p.slug)} — ${esc(p.summary || "")}">${esc(p.slug)}</button>`;
  const folder = (name, inner, count) => {
    const open = !state.wiki.folds.has(name);
    return `<div class="wr-folder"><button class="wr-fold" data-fold="${esc(name)}">` +
      `<span class="wr-arrow">${open ? "▾" : "▸"}</span>${esc(name)}/<span class="wr-count">${count}</span></button>` +
      (open ? `<div class="wr-items">${inner}</div>` : "") + `</div>`;
  };
  let html = Object.keys(cats).sort().map((c) => folder(c, cats[c].map(item).join(""), cats[c].length)).join("");
  if (q && !shown.length) html += `<div class="wr-empty">no pages match</div>`;
  const sp = w.specials || {};
  // sources filter too — titles carry the full author list, so "yann lecun" finds papers
  const ql = q.toLowerCase();
  const srcs = (w.sources || []).filter((s) =>
    !q || s.title.toLowerCase().includes(ql) || s.path.toLowerCase().includes(ql));
  const srcRows = srcs.map((s) =>
    `<div class="wr-src" title="${esc(s.title)} — ${esc(s.path)} — ingested ${esc(s.date)}">${esc(s.title)}<span class="wr-date">${esc(s.date)}</span></div>`).join("");
  html += `<div class="wr-specials">` +
    (srcs.length ? folder("sources", srcRows, srcs.length) : "") +
    (sp.schema ? `<button class="wr-item wr-special${state.wiki.selected === "_schema" ? " on" : ""}" data-wiki="_schema">schema</button>` : "") +
    (sp.log ? `<button class="wr-item wr-special${state.wiki.selected === "_log" ? " on" : ""}" data-wiki="_log">log</button>` : "") +
    (sp.index ? `<button class="wr-item wr-special${state.wiki.selected === "_index" || state.wiki.selected == null ? " on" : ""}" data-wiki="_index">index</button>` : "") +
    `</div>`;
  $("wiki-rail-body").innerHTML = html;
}
$("wiki-rail").addEventListener("click", (e) => {
  const fold = e.target.closest("[data-fold]");
  if (fold) {
    const name = fold.getAttribute("data-fold");
    state.wiki.folds.has(name) ? state.wiki.folds.delete(name) : state.wiki.folds.add(name);
    state.wiki.railKey = ""; renderWikiRail();
    return;
  }
  const it = e.target.closest("[data-wiki]");
  if (it) openWikiPage(it.getAttribute("data-wiki"));
});
$("wiki-rail-btn").addEventListener("click", () => {
  state.wiki.railHidden = !state.wiki.railHidden;
  localStorage.setItem("crux-wiki-rail", state.wiki.railHidden ? "1" : "0");
  state.wiki.railKey = ""; renderWikiRail();
});

// the rail's own divider — draggable like the main splitter; width persists.
// Width is computed from the GRAB point, not read back per-frame: the rail's
// flex-basis transition lags live reads and would eat the increments.
(function () {
  const rail = $("wiki-rail"), div = $("wiki-rail-divider");
  function setW(px) { rail.style.flex = `0 0 ${clamp(px, 130, 420)}px`; }
  const saved = parseInt(localStorage.getItem("crux-wiki-rail-w") || "", 10);
  if (saved) setW(saved);
  let dragging = false, sx = 0, w0 = 0;
  function onMove(e) {
    if (!dragging) return;
    setW(w0 + (e.clientX - sx));
  }
  function onUp() {
    dragging = false;
    document.body.style.cursor = "";
    div.classList.remove("active");
    rail.classList.remove("resizing");
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
    localStorage.setItem("crux-wiki-rail-w", String(Math.round(rail.getBoundingClientRect().width)));
  }
  div.addEventListener("pointerdown", (e) => {
    if (state.wiki.railHidden) return;   // nothing to resize while collapsed
    e.preventDefault();
    dragging = true; sx = e.clientX; w0 = rail.getBoundingClientRect().width;
    rail.classList.add("resizing");      // suspend the flex transition while dragging
    document.body.style.cursor = "col-resize";
    div.classList.add("active");
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  });
  div.addEventListener("dblclick", () => { localStorage.removeItem("crux-wiki-rail-w"); rail.style.flex = ""; });
})();

// ------------------------------------------------------------------ living force graph
// Obsidian-like physics: the graph is a continuously-simulated system — it settles with
// a visible ease, wakes when you grab a node (the neighborhood springs along), and
// morphs organically when the vault changes. Initial positions are still seeded from a
// hash of each slug (a stable starting shape), but the layout is deliberately NOT
// deterministic — the wiki is a web, not a hierarchy; the tree keeps determinism.
// Node color = category, node radius = wiki-to-wiki link degree.
function hash32(s) {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h;
}
const hash01 = (s) => hash32(s) / 4294967296;
const WIKI_COLORS = ["#4f9fe0", "#3fa06a", "#8b5cf6", "#d9a13b", "#d75a5a",
                     "#2f9e8f", "#c66bb0", "#7a9e3f", "#5b74c8", "#b98050"];
const catColor = (c) => WIKI_COLORS[hash32(String(c)) % WIKI_COLORS.length];

function wikiEdges(pages) {
  const have = new Set(pages.map((p) => p.slug));
  const seen = new Set(), edges = [];
  for (const p of pages) for (const t of p.links) {
    if (!have.has(t) || t === p.slug) continue;
    const key = p.slug < t ? p.slug + " " + t : t + " " + p.slug;
    if (!seen.has(key)) { seen.add(key); edges.push([p.slug, t].sort()); }
  }
  edges.sort((a, b) => (a[0] + a[1] < b[0] + b[1] ? -1 : 1));
  return edges;
}

// The simulation (d3-force style, hand-rolled): many-body repulsion + link springs +
// a soft centering pull, integrated with velocity damping. `alpha` is the system's
// heat — it eases toward `alphaTarget` and the loop sleeps once cool, so an idle
// graph costs nothing. Dragging a node pins it (fx/fy) and reheats the system, so
// the neighborhood tugs along and the network springs back on release.
const WSIM = {
  nodes: new Map(),   // slug -> {x, y, vx, vy, fx, fy}
  edges: [],          // [a, b] slug pairs
  els: {},            // slug -> <g> DOM cache; only transforms update per frame
  edgeEls: [],        // [{el, a, b}]
  alpha: 0, alphaTarget: 0, raf: 0,
  // tuned for an airy constellation: strong repulsion + long rest length spread the
  // web out (labels breathe, no node overlap); the soft center keeps it bounded
  CHARGE: 14000, SPRING: 0.025, REST: 280, CENTER: 0.003, DAMP: 0.62,
};

function wikiSimTick() {
  const ns = [...WSIM.nodes.values()], n = ns.length, a = WSIM.alpha;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    const p = ns[i], q = ns[j];
    let dx = p.x - q.x, dy = p.y - q.y;
    const d2 = Math.max(dx * dx + dy * dy, 64);
    const d = Math.sqrt(d2);
    const f = (WSIM.CHARGE * a) / d2;
    dx = (dx / d) * f; dy = (dy / d) * f;
    p.vx += dx; p.vy += dy; q.vx -= dx; q.vy -= dy;
  }
  for (const [ea, eb] of WSIM.edges) {
    const p = WSIM.nodes.get(ea), q = WSIM.nodes.get(eb);
    if (!p || !q) continue;
    let dx = q.x - p.x, dy = q.y - p.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1e-4;
    const f = (d - WSIM.REST) * WSIM.SPRING * a;
    dx = (dx / d) * f; dy = (dy / d) * f;
    p.vx += dx; p.vy += dy; q.vx -= dx; q.vy -= dy;
  }
  for (const p of ns) {
    p.vx -= p.x * WSIM.CENTER * a; p.vy -= p.y * WSIM.CENTER * a;
    p.vx *= WSIM.DAMP; p.vy *= WSIM.DAMP;
    if (p.fx != null) { p.x = p.fx; p.y = p.fy; p.vx = 0; p.vy = 0; }
    else { p.x += p.vx; p.y += p.vy; }
  }
  WSIM.alpha += (WSIM.alphaTarget - WSIM.alpha) * 0.035;
}

function wikiSimDraw() {
  const pos = {};
  for (const [s, p] of WSIM.nodes) {
    pos[s] = p;
    const el = WSIM.els[s];
    if (el) el.setAttribute("transform", `translate(${p.x},${p.y})`);
  }
  for (const { el, a, b } of WSIM.edgeEls) {
    const p = pos[a], q = pos[b];
    if (p && q) {
      el.setAttribute("x1", p.x); el.setAttribute("y1", p.y);
      el.setAttribute("x2", q.x); el.setAttribute("y2", q.y);
    }
  }
  state.wiki.positions = pos;   // fit / centering read the live positions
}

function wikiSimLoop() {
  cancelAnimationFrame(WSIM.raf);
  if (state.tab !== "wiki") return;   // a hidden graph burns no physics
  if (REDUCED_MOTION) {               // settle instantly — no animation
    let guard = 0;
    while (WSIM.alpha > 0.006 && guard++ < 600) wikiSimTick();
    WSIM.alpha = 0;
    wikiSimDraw();
    return;
  }
  const step = () => {
    if (state.tab !== "wiki") return;   // tab switched away mid-flight: sleep
    wikiSimTick();
    wikiSimDraw();
    if (WSIM.alpha > 0.006 || WSIM.alphaTarget > 0) WSIM.raf = requestAnimationFrame(step);
  };
  WSIM.raf = requestAnimationFrame(step);
}

function wikiReheat(alpha) {
  WSIM.alpha = Math.max(WSIM.alpha, alpha);
  wikiSimLoop();
}

// Sync the sim to the polled index. Surviving nodes KEEP their positions (the graph
// morphs, never resets); a new node seeds next to a linked neighbor and flies in.
function layoutWikiGraph() {
  const pages = wikiPages();
  const edges = wikiEdges(pages);
  const key = JSON.stringify([pages.map((p) => p.slug), edges]);
  if (key === state.wiki.layoutKey) return;
  const first = !state.wiki.layoutKey;
  state.wiki.layoutKey = key;
  const live = new Set(pages.map((p) => p.slug));
  for (const s of [...WSIM.nodes.keys()]) if (!live.has(s)) WSIM.nodes.delete(s);
  const R = 90 * Math.sqrt(Math.max(pages.length, 1));
  for (const p of pages) {
    if (WSIM.nodes.has(p.slug)) continue;
    const nb = edges.find((e) => e.includes(p.slug));
    const anchor = nb && WSIM.nodes.get(nb[0] === p.slug ? nb[1] : nb[0]);
    const th = hash01(p.slug) * Math.PI * 2, rr = 0.25 + 0.75 * hash01(p.slug + " r");
    const seed = anchor
      ? { x: anchor.x + Math.cos(th) * 60, y: anchor.y + Math.sin(th) * 60 }
      : { x: Math.cos(th) * R * rr, y: Math.sin(th) * R * rr };
    WSIM.nodes.set(p.slug, { ...seed, vx: 0, vy: 0, fx: null, fy: null });
  }
  WSIM.edges = edges;
  renderWikiGraph(first);
  wikiReheat(first ? 1 : 0.5);
}

function wikiDegree() {
  const deg = {};
  for (const p of wikiPages()) deg[p.slug] = 0;
  for (const [a, b] of wikiEdges(wikiPages())) { deg[a]++; deg[b]++; }
  return deg;
}
const nodeR = (d) => clamp(7 + 3.2 * Math.sqrt(d), 7, 26);

// (Re)build the graph DOM when the structure changes; per-frame motion only touches
// the cached transforms/endpoints in wikiSimDraw — never innerHTML.
function renderWikiGraph(entering) {
  if (state.tab !== "wiki") return;
  const pages = wikiPages(), deg = wikiDegree();
  let lines = "", nodes = "";
  for (const [a, b] of WSIM.edges)
    lines += `<line class="wedge" data-a="${esc(a)}" data-b="${esc(b)}"/>`;
  for (const p of pages) {
    const r = nodeR(deg[p.slug] || 0);
    const on = state.wiki.selected === p.slug ? " on" : "";
    const orphan = (deg[p.slug] || 0) === 0 ? " orphan" : "";
    nodes += `<g class="wnode${on}${orphan}" data-slug="${esc(p.slug)}">` +
      `<title>${esc(p.title || p.slug)} — ${esc(p.category)} · ${deg[p.slug] || 0} links · drag me</title>` +
      `<circle r="${r}" style="--wc:${catColor(p.category)}"/>` +
      `<text y="${r + 12}">${esc(trunc(p.slug, 24))}</text></g>`;
  }
  const v = state.wiki.view;
  wsvg.innerHTML = `<g class="viewport" transform="translate(${v.tx},${v.ty}) scale(${v.k})">${lines}${nodes}</g>`;
  WSIM.els = {};
  wsvg.querySelectorAll(".wnode").forEach((el) => (WSIM.els[el.getAttribute("data-slug")] = el));
  WSIM.edgeEls = [...wsvg.querySelectorAll(".wedge")].map((el) =>
    ({ el, a: el.getAttribute("data-a"), b: el.getAttribute("data-b") }));
  wikiSimDraw();
  renderWikiLegend(pages);
  dimWikiGraph();
  if (entering) animateIn(wsvg.querySelectorAll(".wnode"), { opacity: [0, 1] },
    { duration: 0.35, delay: M && M.stagger ? M.stagger(0.012) : 0 });
}

function renderWikiLegend(pages) {
  const cats = [...new Set(pages.map((p) => p.category))].sort();
  const head = `<button type="button" class="wlg-hide" data-wlg-hide title="Hide the category key" aria-label="Hide the category key">×</button>`;
  $("wiki-legend").innerHTML = cats.map((c) =>
    `<span class="wlg"><span class="sw" style="background:${catColor(c)}"></span>${esc(c)}</span>`).join("") +
    (pages.length ? `<span class="wlg dim-note">size = links</span>` : "") + head;
}
// the category key is minimizable, like the tree's color key (persisted)
function setWikiLegendHidden(hidden) {
  $("wiki-legend").hidden = hidden;
  $("wiki-legend-btn").hidden = !hidden;
  localStorage.setItem("crux-wiki-legend-hidden", hidden ? "1" : "0");
}
$("wiki-legend").addEventListener("click", (e) => {
  if (e.target.closest("[data-wlg-hide]")) setWikiLegendHidden(true);
});
$("wiki-legend-btn").addEventListener("click", () => setWikiLegendHidden(false));
setWikiLegendHidden(localStorage.getItem("crux-wiki-legend-hidden") === "1");

// search dims non-matching nodes (and their labels/edges) without a relayout
function dimWikiGraph() {
  if (state.tab !== "wiki") return;
  const q = state.search;
  const hit = new Set(q ? wikiPages().filter(matchWiki).map((p) => p.slug) : []);
  wsvg.querySelectorAll(".wnode").forEach((el) => {
    const s = el.getAttribute("data-slug");
    el.classList.toggle("dim", !!q && !hit.has(s));
    el.classList.toggle("hit", !!q && hit.has(s));
  });
  wsvg.querySelectorAll(".wedge").forEach((el) => {
    const a = el.getAttribute("data-a"), b = el.getAttribute("data-b");
    el.classList.toggle("dim", !!q && !(hit.has(a) && hit.has(b)));
  });
}

// hover: spotlight a node's neighborhood (its edges + direct neighbors)
wsvg.addEventListener("pointerover", (e) => {
  const node = e.target.closest(".wnode");
  if (!node) return;
  const s = node.getAttribute("data-slug");
  const nb = new Set([s]);
  wsvg.querySelectorAll(".wedge").forEach((el) => {
    const a = el.getAttribute("data-a"), b = el.getAttribute("data-b");
    if (a === s) nb.add(b);
    if (b === s) nb.add(a);
    el.classList.toggle("hot", a === s || b === s);
  });
  wsvg.querySelectorAll(".wnode").forEach((el) =>
    el.classList.toggle("cold", !nb.has(el.getAttribute("data-slug"))));
});
wsvg.addEventListener("pointerout", (e) => {
  if (e.target.closest(".wnode") && !e.relatedTarget?.closest?.(".wnode")) {
    wsvg.querySelectorAll(".hot").forEach((el) => el.classList.remove("hot"));
    wsvg.querySelectorAll(".cold").forEach((el) => el.classList.remove("cold"));
  }
});

// pan / zoom — the tree's gestures, on the wiki camera
function applyWikiTransform() {
  const g = wsvg.firstChild;
  const v = state.wiki.view;
  if (g) g.setAttribute("transform", `translate(${v.tx},${v.ty}) scale(${v.k})`);
}
function fitWikiGraph() {
  const pos = state.wiki.positions;
  const slugs = pos ? Object.keys(pos) : [];
  if (!slugs.length) return false;
  const r = wsvg.getBoundingClientRect();
  if (r.width < 80 || r.height < 80) return false;
  const deg = wikiDegree();
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const s of slugs) {
    const m = nodeR(deg[s] || 0) + 26;
    minX = Math.min(minX, pos[s].x - m); maxX = Math.max(maxX, pos[s].x + m);
    minY = Math.min(minY, pos[s].y - m); maxY = Math.max(maxY, pos[s].y + m);
  }
  const k = clamp(Math.min(1.2, (r.width - 40) / (maxX - minX || 1), (r.height - 40) / (maxY - minY || 1)), 0.08, 1.2);
  state.wiki.view = { k, tx: (r.width - (maxX - minX) * k) / 2 - minX * k,
                      ty: (r.height - (maxY - minY) * k) / 2 - minY * k };
  applyWikiTransform();
  return true;
}
function wikiZoomAt(cx, cy, factor) {
  const v = state.wiki.view, r = wsvg.getBoundingClientRect();
  const k2 = clamp(v.k * factor, 0.06, 3);
  if (k2 === v.k) return;
  const mx = cx - r.left, my = cy - r.top;
  v.tx = mx - (mx - v.tx) * (k2 / v.k);
  v.ty = my - (my - v.ty) * (k2 / v.k);
  v.k = k2;
  applyWikiTransform();
}
wsvg.addEventListener("wheel", (e) => {
  e.preventDefault();
  const dy = e.deltaMode === 1 ? e.deltaY * 20 : e.deltaY;
  wikiZoomAt(e.clientX, e.clientY, Math.exp(-dy * (e.ctrlKey ? 0.012 : 0.0028)));
}, { passive: false });
let wpan = null, wmoved = false;
function onWikiPanMove(e) {
  if (!wpan) return;
  const dx = e.clientX - wpan.x, dy = e.clientY - wpan.y;
  if (!wmoved && dx * dx + dy * dy > DRAG_THRESHOLD * DRAG_THRESHOLD) { wmoved = true; wsvg.classList.add("panning"); }
  if (wmoved) { state.wiki.view.tx = wpan.tx + dx; state.wiki.view.ty = wpan.ty + dy; applyWikiTransform(); }
}
function onWikiPanEnd() {
  window.removeEventListener("pointermove", onWikiPanMove);
  window.removeEventListener("pointerup", onWikiPanEnd);
  window.removeEventListener("pointercancel", onWikiPanEnd);
  wsvg.classList.remove("panning");
  wpan = null;
}
// Grabbing a NODE drags it through the simulation (the neighborhood tugs along and
// springs back on release — the Obsidian joy); grabbing empty canvas pans the camera.
// A sub-threshold grab on a node is still a click (opens the page in the reader).
let wdrag = null;   // { node: sim entry, sx, sy }
function wikiWorldOf(e) {
  const r = wsvg.getBoundingClientRect(), v = state.wiki.view;
  return { x: (e.clientX - r.left - v.tx) / v.k, y: (e.clientY - r.top - v.ty) / v.k };
}
function onWikiDragMove(e) {
  if (!wdrag) return;
  const dx = e.clientX - wdrag.sx, dy = e.clientY - wdrag.sy;
  if (!wmoved && dx * dx + dy * dy > DRAG_THRESHOLD * DRAG_THRESHOLD) {
    wmoved = true;
    wsvg.classList.add("dragging");
    WSIM.alphaTarget = 0.3;   // hold the system warm while the pointer leads it
    wikiReheat(0.3);
  }
  if (wmoved) {
    const w = wikiWorldOf(e);
    wdrag.node.fx = w.x; wdrag.node.fy = w.y;
    wdrag.node.x = w.x; wdrag.node.y = w.y;
    wikiSimDraw();   // the grabbed node tracks the pointer with zero frame lag
    if (REDUCED_MOTION) wikiSimLoop();   // static mode: re-settle synchronously
  }
}
function onWikiDragEnd() {
  window.removeEventListener("pointermove", onWikiDragMove);
  window.removeEventListener("pointerup", onWikiDragEnd);
  window.removeEventListener("pointercancel", onWikiDragEnd);
  wsvg.classList.remove("dragging");
  if (wdrag) { wdrag.node.fx = null; wdrag.node.fy = null; }
  wdrag = null;
  WSIM.alphaTarget = 0;   // release: the network springs back, settles, sleeps
}
wsvg.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  e.preventDefault();
  wmoved = false;
  const nodeEl = e.target.closest(".wnode");
  const sim = nodeEl && WSIM.nodes.get(nodeEl.getAttribute("data-slug"));
  if (sim) {
    wdrag = { node: sim, sx: e.clientX, sy: e.clientY };
    window.addEventListener("pointermove", onWikiDragMove);
    window.addEventListener("pointerup", onWikiDragEnd);
    window.addEventListener("pointercancel", onWikiDragEnd);
    return;
  }
  wpan = { x: e.clientX, y: e.clientY, tx: state.wiki.view.tx, ty: state.wiki.view.ty };
  window.addEventListener("pointermove", onWikiPanMove);
  window.addEventListener("pointerup", onWikiPanEnd);
  window.addEventListener("pointercancel", onWikiPanEnd);
});
wsvg.addEventListener("click", (e) => {
  if (wmoved) return;
  const node = e.target.closest(".wnode");
  if (node) openWikiPage(node.getAttribute("data-slug"));
});
function wikiCenterZoom(factor) {
  const r = wsvg.getBoundingClientRect();
  wikiZoomAt(r.left + r.width / 2, r.top + r.height / 2, factor);
}
$("wgraph-in").addEventListener("click", () => wikiCenterZoom(1.35));
$("wgraph-out").addEventListener("click", () => wikiCenterZoom(1 / 1.35));
$("wgraph-fit").addEventListener("click", fitWikiGraph);

// ------------------------------------------------------------------ reader (lazy page fetch)
function openWikiPage(slug) {
  if (state.tab !== "wiki") setTab("wiki");
  state.wiki.selected = slug;
  localStorage.setItem("crux-wiki-slug", slug);
  state.wiki.railKey = "";
  renderWikiRail();
  wsvg.querySelectorAll(".wnode").forEach((el) =>
    el.classList.toggle("on", el.getAttribute("data-slug") === slug));
  fetchWikiPage(slug);
}

// what the open page's content is *supposed* to be, per the polled index (specials aren't
// indexed — key on the whole index instead, since WIKI.md is derived from it)
function pageKeyOf(slug) {
  if (slug in RESERVED) return slug + " " + JSON.stringify([wikiPages(), (state.snap.wiki || {}).sources]);
  const p = wikiPages().find((x) => x.slug === slug);
  return p ? slug + " " + p.hash : null;
}

// on each snapshot: default the reader to the index, drop a selection that no longer
// resolves, and refetch the open page when the poll says its content changed
function refreshWikiPage() {
  let slug = state.wiki.selected || "_index";
  if (pageKeyOf(slug) == null) { slug = "_index"; state.wiki.selected = null; }
  if (pageKeyOf(slug) !== state.wiki.pageKey) fetchWikiPage(slug);
  else renderWikiReader();
}

async function fetchWikiPage(slug) {
  const key = pageKeyOf(slug);
  try {
    const r = await fetch("/wiki/" + encodeURIComponent(slug) + ".json", { cache: "no-store" });
    if (!r.ok) throw new Error(String(r.status));
    state.wiki.page = await r.json();
    state.wiki.pageKey = key;
  } catch (e) {
    state.wiki.page = { slug, title: null, summary: null, category: null, sources: [],
                        updated: null, body: "_could not load this page (" + e.message + ")_",
                        backlinks: [], error: true };
    state.wiki.pageKey = key;
  }
  renderWikiReader();
}

function renderWikiReader() {
  if (state.tab !== "wiki") return;
  const pane = $("detail-content"), pg = state.wiki.page;
  if (!pg) { pane.innerHTML = `<div class="d-kind">wiki</div><p class="d-empty">loading…</p>`; return; }
  const key = JSON.stringify([pg.slug, state.wiki.pageKey, pg.body, pg.backlinks]);
  if (key === state.wiki.readerKey) return;   // steady state: don't stomp selection/animation
  state.wiki.readerKey = key;
  const special = pg.slug in RESERVED;
  const kind = special ? "wiki · " + RESERVED[pg.slug] : "wiki · " + (pg.category || "page");
  let badges = "";
  if (!special && pg.category)
    badges += `<span class="badge dot" style="--b:${catColor(pg.category)}">${esc(pg.category)}</span>`;
  if (pg.updated) badges += `<span class="badge">updated <span class="inline">${esc(pg.updated)}</span></span>`;
  const srcs = (pg.sources || []).length
    ? section("Sources", `<ul class="linklist">` +
        pg.sources.map((s) => `<li><span class="inline">${esc(s)}</span></li>`).join("") + `</ul>`)
    : "";
  // snippets render INERT (mention highlighted, not linkified): the row itself is the link
  // to the citing page — a live link inside it would nest interactives and point back here
  const snip = (s) => esc(s).replace(/\[\[[^\]]*\]\]/g, (m) => `<span class="wl-mark">${m}</span>`);
  const backs = special ? "" : section(`Linked from — ${pg.backlinks.length} page${pg.backlinks.length === 1 ? "" : "s"}`,
    pg.backlinks.length
      ? pg.backlinks.map((b) =>
          `<button class="rowlink" data-wiki="${esc(b.slug)}"><span class="rid">${esc(b.slug)}</span>${esc(b.title || "")}` +
          `<span class="rsum">${snip(b.snippet || "")}</span></button>`).join("")
      : `<div class="body muted">nothing links here yet — an orphan by wiki-graph degree</div>`);
  pane.innerHTML = `<div class="d-kind">${esc(kind)}</div>` +
    `<div class="d-title">${esc(pg.title || pg.slug)}</div>` +
    (badges ? `<div class="badges">${badges}</div>` : "") +
    `<div class="wiki-body">${mdRender(pg.body)}</div>` + backs + srcs;
  animateIn(pane.children, { opacity: [0, 1], y: [6, 0] },
    { duration: 0.28, delay: M && M.stagger ? M.stagger(0.03) : 0 });
}

// ------------------------------------------------------------------ markdown (hand-rolled subset)
// Renders the subset crux wiki pages use: headings, paragraphs, bold/italic, inline +
// fenced code, lists, blockquotes, tables, rules, external links, and wikilinks —
// [[slug]] / [[slug|alias]] / [[slug\|alias]] (the escaped-pipe form the generated
// WIKI.md emits). Every fragment is HTML-escaped BEFORE any markup is added: page text
// is data, never injected as markup.
function mdInline(s) {
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\[\[\s*([^\]|#\\]+?)\s*(?:(?:\\\||\||#)([^\]]*))?\]\]/g, (m, t, a) => wikiLink(t, a));
  s = s.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g,
    `<a class="ext" href="$2" target="_blank" rel="noopener">$1</a>`);
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
  s = s.replace(/(^|[\s(])_([^_\s][^_]*)_/g, "$1<em>$2</em>");
  return s;
}
function mdRender(md) {
  const lines = String(md || "").split("\n");
  const out = [];
  let para = [], list = null, quote = [], code = null, table = null;
  const flush = () => {
    if (para.length) { out.push(`<p>${mdInline(esc(para.join(" ")))}</p>`); para = []; }
    if (list) { out.push(`<${list.tag}>` + list.items.map((i) => `<li>${mdInline(esc(i))}</li>`).join("") + `</${list.tag}>`); list = null; }
    if (quote.length) { out.push(`<blockquote>${mdInline(esc(quote.join(" ")))}</blockquote>`); quote = []; }
    if (table) {
      const row = (cells, tag) => `<tr>` + cells.map((c) => `<${tag}>${mdInline(esc(c))}</${tag}>`).join("") + `</tr>`;
      out.push(`<table>` + row(table.head, "th") + table.rows.map((r) => row(r, "td")).join("") + `</table>`);
      table = null;
    }
  };
  const cells = (l) => l.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (code) {
      if (/^\s*```/.test(l)) { out.push(`<pre><code>${esc(code.join("\n"))}</code></pre>`); code = null; }
      else code.push(l);
      continue;
    }
    let m;
    if (/^\s*```/.test(l)) { flush(); code = []; }
    else if ((m = l.match(/^(#{1,6})\s+(.*)$/))) { flush(); const h = Math.min(m[1].length + 1, 5); out.push(`<h${h}>${mdInline(esc(m[2]))}</h${h}>`); }
    else if (/^\s*([-*_])\s*\1\s*\1[\s\-*_]*$/.test(l)) { flush(); out.push("<hr>"); }
    else if ((m = l.match(/^\s*>\s?(.*)$/))) { if (para.length || list || table) flush(); quote.push(m[1]); }
    else if ((m = l.match(/^\s*[-*+]\s+(.*)$/))) {
      if (para.length || quote.length || table || (list && list.tag !== "ul")) flush();
      (list = list || { tag: "ul", items: [] }).items.push(m[1]);
    }
    else if ((m = l.match(/^\s*\d+[.)]\s+(.*)$/))) {
      if (para.length || quote.length || table || (list && list.tag !== "ol")) flush();
      (list = list || { tag: "ol", items: [] }).items.push(m[1]);
    }
    else if (/^\s*\|.*\|\s*$/.test(l) && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1] || "")) {
      flush(); table = { head: cells(l), rows: [] }; i++;   // skip the |---| separator
    }
    else if (table && /^\s*\|.*\|\s*$/.test(l)) table.rows.push(cells(l));
    else if (!l.trim()) flush();
    else { if (list || quote.length || table) flush(); para.push(l.trim()); }
  }
  flush();
  if (code) out.push(`<pre><code>${esc(code.join("\n"))}</code></pre>`);   // unclosed fence
  return out.join("\n");
}

// ------------------------------------------------------------------ movable pane splitter
// Drag the divider to resize the detail pane; the tree pane takes the rest. Width persists.
(function () {
  const detail = $("detail-pane"), split = $("splitter");
  function setW(px) {
    const w = clamp(px, 300, Math.max(320, window.innerWidth - 420));
    detail.style.flex = `0 0 ${w}px`;
    detail.style.maxWidth = "none";
  }
  const saved = parseInt(localStorage.getItem("crux-detail-w") || "", 10);
  if (saved) setW(saved);
  let dragging = false;
  function onMove(e) {
    if (!dragging) return;
    setW(window.innerWidth - e.clientX);
  }
  function onUp() {
    dragging = false;
    document.body.style.cursor = "";
    split.classList.remove("active");
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
    localStorage.setItem("crux-detail-w", String(Math.round(detail.getBoundingClientRect().width)));
  }
  split.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    dragging = true;
    document.body.style.cursor = "col-resize";
    split.classList.add("active");
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  });
  split.addEventListener("dblclick", () => { localStorage.removeItem("crux-detail-w"); detail.style.flex = ""; detail.style.maxWidth = ""; });
})();

// If the initial fit was deferred (tab opened in the background), run it as soon as the
// pane actually has geometry — on first show or on a resize.
function retryFit() {
  if (!state.centered && state.snap && fitToView()) { state.centered = true; applyTransform(); }
}
window.addEventListener("resize", () => { retryFit(); applyTransform(); });
document.addEventListener("visibilitychange", () => {
  retryFit();
  // an occluded page suspends rAF, freezing any pending physics — resume on return
  if (!document.hidden && state.tab === "wiki" && WSIM.alpha > 0.006) wikiSimLoop();
});

poll();
