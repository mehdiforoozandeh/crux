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
    let w, h, lines, dotsPad;
    if (state.density === "compact" || n.type === "synthesis") {
      w = k.cw; h = k.ch; lines = [trunc(n.title, k.ctrunc)]; dotsPad = 0;
    } else {
      lines = wrapLines(n.title, k.cpl);
      dotsPad = n.type === "idea" && (n.verifiables || []).length ? 13 : 0;
      w = k.dw; h = Math.max(k.ch, 9 + lines.length * k.lh + 9 + dotsPad);
    }
    g[id] = { w, h, rx: k.pill ? h / 2 : k.rx, lines, lh: k.lh, dotsPad, kind: n.type };
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
  updateReviewBtn();
  layout();
  // One-time fit — but a tab opened in the background has a 0×0 rect until it's shown,
  // so keep retrying on each poll until the pane has real geometry to fit against.
  if (!state.centered && fitToView()) state.centered = true;
  renderLegend();
  renderTree();
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
  if (state.density === "compact") {
    const r = 3.2, gap = 9, x0 = g.w - 11;
    return vs.map((v, i) => `<circle class="vdot ${vBadgeClass(v, n)}" cx="${x0 - i * gap}" cy="0" r="${r}"/>`).join("");
  }
  const r = 4.2, gap = 12.5, y = g.h / 2 - r - 4, x0 = 12 + r;
  return vs.map((v, i) => `<circle class="vdot ${vBadgeClass(v, n)}" cx="${x0 + i * gap}" cy="${y}" r="${r}"/>`).join("");
}

// the Crux constellation, drawn inside the root node (local coords) so the project is unmistakable
const ROOT_MARK =
  `<g class="rootmark" transform="translate(12,-8) scale(0.19)">` +
  `<g class="mk-l"><line x1="38" y1="8" x2="33" y2="76"/><line x1="8" y1="44" x2="60" y2="38"/></g>` +
  `<g class="mk-s"><circle cx="38" cy="8" r="4"/><circle cx="33" cy="76" r="5"/>` +
  `<circle cx="8" cy="44" r="4"/><circle cx="60" cy="38" r="3.4"/><circle cx="45" cy="60" r="2.4"/></g></g>`;

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
  const mark = n.type === "project" ? ROOT_MARK : "";
  const pad = n.type === "project" ? 32 : n.type === "question" ? 15 : 12;
  const y0 = -g.dotsPad / 2 - ((g.lines.length - 1) * g.lh) / 2 + 4;   // centred wrapped block
  const glyph = n.type === "idea" && n.verdict
    ? `<text class="glyph" x="${pad}" y="${y0}" style="fill:var(--v-${esc(n.verdict)})">${GLYPH[n.verdict]}</text>`
    : "";
  const lx = glyph ? pad + 13 : pad;
  const lbl = g.lines.map((ln, i) =>
    `<text class="lbl ${k.lbl}" x="${i === 0 ? lx : pad}" y="${y0 + i * g.lh}">${esc(ln)}</text>`).join("");
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
    `${tip}${shape}${qbar}${mark}${glyph}${lbl}${dots}${toggle}</g>`;
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
  state.selected = null;
  updateReviewBtn();
  renderTree();
  renderDetail();
}

function updateReviewBtn() {
  const n = state.snap ? state.snap.queue.length : 0;
  const b = $("review-btn");
  b.textContent = `Review (${n})`;
  b.classList.toggle("active", state.selected === null);
  b.classList.toggle("has-queue", n > 0);
}

function badge(text, varName, cls) {
  const style = varName ? ` style="--b:var(${esc(varName)})"` : "";
  return `<span class="badge ${cls || ""}${varName ? " dot" : ""}"${style}>${esc(text)}</span>`;
}

function section(title, html) { return `<div class="sec"><h4>${title}</h4>${html}</div>`; }
function bodyOr(text, empty) {
  return text && text.trim() ? `<div class="body">${esc(text)}</div>` : `<div class="body muted">${empty}</div>`;
}

function renderDetail() {
  const pane = $("detail-pane");
  if (!state.snap) { pane.innerHTML = ""; return; }
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
  const go = e.target.closest("[data-go]");
  if (go) selectNode(go.getAttribute("data-go"), { center: true });
});

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

$("search").addEventListener("input", (e) => {
  state.search = e.target.value.trim();
  if (state.snap) renderTree();
});
$("search").addEventListener("keydown", (e) => {
  if (e.key === "Escape") { e.target.value = ""; state.search = ""; if (state.snap) renderTree(); return; }
  if (e.key !== "Enter" || !state.search || !state.snap) return;
  const hit = Object.keys(state.positions).find((id) => matchNode(state.snap.nodes[id]));
  if (hit) selectNode(hit, { center: true });
});

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
document.addEventListener("visibilitychange", retryFit);

poll();
