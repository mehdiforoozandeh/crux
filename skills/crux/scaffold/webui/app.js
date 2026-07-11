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
const KIND = {
  project:   { cw: 210, ch: 38, dw: 260, rx: 19, lbl: "t-root", lh: 16,   cpl: 28, ctrunc: 24 },
  question:  { cw: 196, ch: 32, dw: 250, rx: 7,  lbl: "t-q",    lh: 15,   cpl: 32, ctrunc: 25 },
  idea:      { cw: 156, ch: 22, dw: 224, rx: 11, lbl: "t-h",    lh: 13.5, cpl: 33, ctrunc: 17 },
  synthesis: { cw: 172, ch: 26, dw: 172, rx: 0,  lbl: "t-s",    lh: 14,   cpl: 23, ctrunc: 23 },
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
    if (state.density === "compact" || n.type === "synthesis") {
      g[id] = { w: k.cw, h: k.ch, rx: k.rx, lines: [trunc(n.title, k.ctrunc)], lh: k.lh, dotsPad: 0 };
    } else {
      const lines = wrapLines(n.title, k.cpl);
      const dotsPad = n.type === "idea" && (n.verifiables || []).length ? 10 : 0;
      const h = Math.max(k.ch, 9 + lines.length * k.lh + 9 + dotsPad);
      g[id] = { w: k.dw, h, rx: k.rx, lines, lh: k.lh, dotsPad };
    }
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
  // synthesis nodes live outside the parent tree — park them one level past the deepest
  // node, near the mean position of the questions they relate to, so their dashed edges
  // stay short and legible instead of dangling across the whole canvas.
  const beyond = crossAt[maxCross.length];
  const placed = [];
  Object.values(snap.nodes).filter((n) => n.type === "synthesis").forEach((n, i) => {
    const g = geom[n.id];
    const relIds = (n.related || []).filter((rid) => pos[rid]);
    if (horiz) {
      let y = relIds.length ? relIds.reduce((s, rid) => s + pos[rid].y, 0) / relIds.length
                            : (i + 1) * (g.h + GAP);
      while (placed.some((u) => Math.abs(u - y) < g.h + GAP)) y += g.h + GAP;
      placed.push(y);
      pos[n.id] = { x: beyond, y };
    } else {
      let cx = relIds.length ? relIds.reduce((s, rid) => s + pos[rid].x + geom[rid].w / 2, 0) / relIds.length
                             : (i + 1) * (g.w + GAP);
      while (placed.some((u) => Math.abs(u - cx) < g.w + GAP)) cx += g.w + GAP;
      placed.push(cx);
      pos[n.id] = { x: cx - g.w / 2, y: beyond + g.h / 2 };
    }
  });
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

function edgePath(a, b, dashed) {   // a, b = node objects (positions/geometry looked up)
  const pa = state.positions[a.id], pb = state.positions[b.id];
  const ga = geomOf(a.id), gb = geomOf(b.id);
  let d;
  if (state.orient !== "td") {          // left-right: right edge -> left edge
    const x1 = pa.x + ga.w, y1 = pa.y, x2 = pb.x, y2 = pb.y, mx = (x1 + x2) / 2;
    d = `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
  } else {                              // top-down: bottom centre -> top centre
    const x1 = pa.x + ga.w / 2, y1 = pa.y + ga.h / 2, x2 = pb.x + gb.w / 2, y2 = pb.y - gb.h / 2;
    const my = (y1 + y2) / 2;
    d = `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
  }
  return `<path class="edge${dashed ? " dashed" : ""}" d="${d}"/>`;
}

function diamond(p, g) {
  const cx = p.x + g.w / 2, cy = p.y, hw = g.w / 2, hh = g.h / 2 + 3;
  return `${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`;
}

// tiny tri-state dots inside a hypothesis: its verifiables (met · unmet · n/a).
// Compact: inline at the right edge. Detail: their own row at the bottom-right.
function verifDots(n, p, g) {
  const vs = (n.verifiables || []).slice(0, 6);
  const cy = state.density === "compact" ? p.y : p.y + g.h / 2 - 8;
  return vs.map((v, i) =>
    `<circle class="vdot v-${esc(v.state)}" cx="${p.x + g.w - 12 - i * 8}" cy="${cy}" r="2.6"/>`).join("");
}

// the Crux constellation, drawn inside the root node so the project is unmistakable
function rootMark(p) {
  const x = p.x + 12, y = p.y - 8;
  return `<g class="rootmark" transform="translate(${x},${y}) scale(0.19)">` +
    `<g class="mk-l"><line x1="38" y1="8" x2="33" y2="76"/><line x1="8" y1="44" x2="60" y2="38"/></g>` +
    `<g class="mk-s"><circle cx="38" cy="8" r="4"/><circle cx="33" cy="76" r="5"/>` +
    `<circle cx="8" cy="44" r="4"/><circle cx="60" cy="38" r="3.4"/><circle cx="45" cy="60" r="2.4"/></g></g>`;
}

function nodeSVG(n, p) {
  const g = geomOf(n.id), k = KIND[n.type] || KIND.question, cls = statusClass(n);
  const sel = state.selected === n.id ? " selected" : "";
  const matches = state.search && matchNode(n);
  const dimmed = (state.search && !matches) || (state.filter && cls !== state.filter);
  const wrap = "node" + (n.status === "running" ? " running" : "") +
    (dimmed ? " dim" : "") + (matches ? " hit" : "");
  const boxCls = esc(cls) + sel;
  const shape = n.type === "synthesis"
    ? `<polygon class="box ${boxCls}" points="${diamond(p, g)}"/>`
    : `<rect class="box ${boxCls}" x="${p.x}" y="${p.y - g.h / 2}" width="${g.w}" height="${g.h}" rx="${g.rx}"/>`;
  const mark = n.type === "project" ? rootMark(p) : "";
  const pad = n.type === "project" ? 32 : 12;
  // first-line baseline so the wrapped block sits centred (dots row excluded from centring)
  const y0 = p.y - g.dotsPad / 2 - ((g.lines.length - 1) * g.lh) / 2 + 4;
  const glyph = n.type === "idea" && n.verdict
    ? `<text class="glyph" x="${p.x + pad}" y="${y0}" style="fill:var(--v-${esc(n.verdict)})">${GLYPH[n.verdict]}</text>`
    : "";
  const lx = glyph ? p.x + pad + 13 : p.x + pad;
  const lbl = g.lines.map((ln, i) =>
    `<text class="lbl ${k.lbl}" x="${i === 0 ? lx : p.x + pad}" y="${y0 + i * g.lh}">${esc(ln)}</text>`).join("");
  const dots = n.type === "idea" ? verifDots(n, p, g) : "";
  const hasKids = (state.childCount && state.childCount[n.id]) || 0;
  const tcx = state.orient !== "td" ? p.x + g.w : p.x + g.w / 2;
  const tcy = state.orient !== "td" ? p.y : p.y + g.h / 2;
  const toggle = hasKids
    ? `<g class="toggle" data-toggle="${esc(n.id)}"><circle cx="${tcx}" cy="${tcy}" r="7.5"/>` +
      `<text x="${tcx}" y="${tcy + 3.5}" text-anchor="middle">${state.collapsed.has(n.id) ? "+" : "−"}</text></g>`
    : "";
  const tipStatus = n.type === "idea" && n.verdict ? n.verdict : n.status;
  const tip = `<title>${esc(n.title)} — ${esc(n.type)} · ${esc(tipStatus)}</title>`;
  return `<g class="${wrap}" data-id="${esc(n.id)}">${tip}${shape}${mark}${glyph}${lbl}${dots}${toggle}</g>`;
}

function renderTree() {
  const snap = state.snap, pos = state.positions;
  let edges = "", nodes = "";
  (function walk(node) {
    if (state.collapsed.has(node.id)) return;
    for (const c of node.children) { edges += edgePath(snap.nodes[node.id], snap.nodes[c.id], false); walk(c); }
  })(snap.tree);
  for (const n of Object.values(snap.nodes)) {
    if (n.type !== "synthesis") continue;
    for (const rid of n.related) if (pos[rid]) edges += edgePath(n, snap.nodes[rid], true);
  }
  for (const id in pos) nodes += nodeSVG(snap.nodes[id], pos[id]);
  const v = state.view;
  svg.innerHTML = `<g transform="translate(${v.tx},${v.ty}) scale(${v.k})">${edges}${nodes}</g>`;
}

// Pan/zoom only mutate the group transform — one cheap attribute write; the browser batches
// the actual paint per frame. Deliberately synchronous (not rAF-coalesced): rAF stops firing
// in an occluded/background window, which would leave the view stale until the next interaction.
function applyTransform() {
  const g = svg.firstChild;
  if (g) g.setAttribute("transform", `translate(${state.view.tx},${state.view.ty}) scale(${state.view.k})`);
}

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
  $("legend").innerHTML = LEGEND.map(([group, items]) =>
    `<div class="lg-row"><span class="lg-group">${group}</span>` +
    items.map(([key, varName, label, tip]) =>
      `<button type="button" class="lg${state.filter === key ? " on" : ""}" data-lg="${key}"` +
      ` style="--c:var(${varName})" title="${esc(tip)} — click to spotlight">` +
      `<span class="sw"></span>${label}</button>`).join("") + `</div>`).join("");
}

// ------------------------------------------------------------------ search / navigation
function matchNode(n) {
  const q = state.search.toLowerCase();
  return q && (n.title.toLowerCase().includes(q) || n.id.toLowerCase().includes(q));
}

function fitToView() {
  const ids = Object.keys(state.positions);
  if (!ids.length) return false;
  const r = svg.getBoundingClientRect();
  if (r.width < 80 || r.height < 80) return false;   // hidden/background tab — nothing to fit against
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const id of ids) {
    const p = state.positions[id], g = geomOf(id);
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x + g.w);
    minY = Math.min(minY, p.y - g.h / 2 - 10); maxY = Math.max(maxY, p.y + g.h / 2 + 10);
  }
  const k = Math.min(1, (r.width - 60) / (maxX - minX || 1), (r.height - 60) / (maxY - minY || 1));
  state.view.k = clamp(k, 0.12, 1);
  state.view.tx = 30 - minX * state.view.k;
  state.view.ty = (r.height - (maxY - minY) * state.view.k) / 2 - minY * state.view.k;
  return true;
}

function centerOn(id) {
  const p = state.positions[id];
  if (!p) return;
  const r = svg.getBoundingClientRect();
  state.view.tx = r.width / 2 - (p.x + geomOf(id).w / 2) * state.view.k;
  state.view.ty = r.height / 2 - p.y * state.view.k;
  applyTransform();
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
    const id = tog.getAttribute("data-toggle");
    state.collapsed.has(id) ? state.collapsed.delete(id) : state.collapsed.add(id);
    layout(); renderTree();
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
  const chip = e.target.closest("[data-lg]");
  if (!chip) return;
  const key = chip.getAttribute("data-lg");
  state.filter = state.filter === key ? null : key;
  renderLegend();
  if (state.snap) renderTree();
});

// theme: resolve saved preference (else system) once at boot, then the button toggles
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  $("theme-btn").textContent = t === "dark" ? "☀" : "☾";
}
applyTheme(localStorage.getItem("crux-theme") ||
  (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
$("theme-btn").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("crux-theme", next);
  applyTheme(next);
});

// ------------------------------------------------------------------ tree toolbar
// orientation (left-right / top-down) · node text (full / compact) · focus open questions
function relayout() {
  if (!state.snap) return;
  layout(); fitToView(); renderTree();
}
function updateToolbar() {
  const ob = $("orient-btn");
  ob.textContent = state.orient === "td" ? "⇄" : "⇅";
  ob.title = state.orient === "td" ? "Switch to a left-to-right tree" : "Switch to a top-down tree";
  const db = $("density-btn");
  db.textContent = state.density === "detail" ? "▭" : "☰";
  db.title = state.density === "detail"
    ? "Compact nodes — one truncated line each"
    : "Full-text nodes — read whole questions/hypotheses without clicking";
  const fb = $("focus-btn");
  fb.classList.toggle("on", state.focused);
  fb.title = state.focused
    ? "Show everything again"
    : "Focus — collapse every non-open question, keep what needs work";
}
$("orient-btn").addEventListener("click", () => {
  state.orient = state.orient === "td" ? "lr" : "td";
  localStorage.setItem("crux-orient", state.orient);
  updateToolbar(); relayout();
});
$("density-btn").addEventListener("click", () => {
  state.density = state.density === "detail" ? "compact" : "detail";
  localStorage.setItem("crux-density", state.density);
  updateToolbar(); relayout();
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

// on-screen zoom controls (zoom about the tree-pane centre)
function centerZoom(factor) {
  const r = svg.getBoundingClientRect();
  zoomAt(r.left + r.width / 2, r.top + r.height / 2, factor);
}
$("zoom-in").addEventListener("click", () => centerZoom(1.25));
$("zoom-out").addEventListener("click", () => centerZoom(1 / 1.25));
$("zoom-fit").addEventListener("click", () => { if (state.snap) { fitToView(); applyTransform(); } });

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

// If the initial fit was deferred (tab opened in the background), run it as soon as the
// pane actually has geometry — on first show or on a resize.
function retryFit() {
  if (!state.centered && state.snap && fitToView()) { state.centered = true; applyTransform(); }
}
window.addEventListener("resize", () => { retryFit(); applyTransform(); });
document.addEventListener("visibilitychange", retryFit);

poll();
