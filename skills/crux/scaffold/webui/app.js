/* crux cockpit — read-only. Polls /snapshot.json (~1s), lays out a deterministic
   hierarchical tree, and shows a review queue / node detail on the right.
   No writes, no build step, no dependencies. */
"use strict";

const COL_W = 220, ROW_H = 42, NODE_W = 172, NODE_H = 26;
const VERDICTS = ["supported", "partial", "refuted", "inconclusive"];

const state = {
  snap: null,
  lastJSON: "",
  collapsed: new Set(),     // node ids whose subtree is hidden (client-only)
  selected: null,           // node id, or null => review queue
  view: { tx: 60, ty: 40, k: 1 },
  positions: {},            // id -> {x, y, depth}
  search: "",
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
  $("project-title").textContent = snap.project.title || "crux";
  $("meta").textContent = "engine v" + snap.engine_version;
  // drop selection if the node disappeared
  if (state.selected && !(state.selected in snap.nodes)) state.selected = null;
  updateReviewBtn();
  layout();
  if (!state.centered) { fitToView(); state.centered = true; }
  renderLegend();
  renderTree();
  renderDetail();
}

// ------------------------------------------------------------------ deterministic layout
// x = depth column; y = leaf order (post-order). Same structure => same positions,
// so nodes never jump on auto-refresh. Collapsed nodes lay out as leaves.
function layout() {
  const snap = state.snap, pos = {};
  let leaf = 0;
  (function visit(node, depth) {
    const kids = state.collapsed.has(node.id) ? [] : node.children;
    if (!kids.length) {
      pos[node.id] = { x: depth * COL_W, y: leaf * ROW_H, depth };
      leaf++;
    } else {
      const ys = [];
      for (const c of kids) { visit(c, depth + 1); ys.push(pos[c.id].y); }
      pos[node.id] = { x: depth * COL_W, y: (ys[0] + ys[ys.length - 1]) / 2, depth };
    }
  })(snap.tree, 0);
  // synthesis nodes are outside the parent tree; stack them past the deepest column
  const maxDepth = Math.max(0, ...Object.values(pos).map((p) => p.depth));
  Object.values(snap.nodes).filter((n) => n.type === "synthesis").forEach((n, i) => {
    pos[n.id] = { x: (maxDepth + 1) * COL_W, y: (leaf + i) * ROW_H, depth: maxDepth + 1 };
  });
  state.positions = pos;
}

// ------------------------------------------------------------------ tree render
function statusClass(n) {
  if (n.type === "project") return "n-project";
  if (n.type === "synthesis") return "n-synth";
  if (n.type === "question") return "q-" + n.status;
  if (n.status === "done") return "h-" + (n.verdict || "inconclusive");
  return "h-" + n.status;
}

function edgePath(a, b, dashed) {
  const x1 = a.x + NODE_W, y1 = a.y, x2 = b.x, y2 = b.y, mx = (x1 + x2) / 2;
  return `<path class="edge${dashed ? " dashed" : ""}" d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}"/>`;
}

function diamond(p) {
  const cx = p.x + NODE_W / 2, cy = p.y, hw = NODE_W / 2, hh = NODE_H / 2 + 3;
  return `${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`;
}

function nodeSVG(n, p) {
  const cls = statusClass(n);
  const sel = state.selected === n.id ? " selected" : "";
  const matches = state.search && matchNode(n);
  const wrap = "node" + (n.status === "running" ? " running" : "") +
    (state.search && !matches ? " dim" : "") + (matches ? " hit" : "");
  const boxCls = esc(cls) + sel;
  const shape = n.type === "synthesis"
    ? `<polygon class="box ${boxCls}" points="${diamond(p)}"/>`
    : `<rect class="box ${boxCls}" x="${p.x}" y="${p.y - NODE_H / 2}" width="${NODE_W}" height="${NODE_H}" rx="6"/>`;
  const lbl = `<text class="lbl" x="${p.x + 11}" y="${p.y + 4}">${esc(trunc(n.title, 25))}</text>`;
  const hasKids = n.children && n.children.length;
  const toggle = hasKids
    ? `<g class="toggle" data-toggle="${esc(n.id)}"><circle cx="${p.x + NODE_W}" cy="${p.y}" r="7.5"/>` +
      `<text x="${p.x + NODE_W}" y="${p.y + 3.5}" text-anchor="middle">${state.collapsed.has(n.id) ? "+" : "−"}</text></g>`
    : "";
  return `<g class="${wrap}" data-id="${esc(n.id)}">${shape}${lbl}${toggle}</g>`;
}

function renderTree() {
  const snap = state.snap, pos = state.positions;
  let edges = "", nodes = "";
  (function walk(node) {
    if (state.collapsed.has(node.id)) return;
    for (const c of node.children) { edges += edgePath(pos[node.id], pos[c.id], false); walk(c); }
  })(snap.tree);
  for (const n of Object.values(snap.nodes)) {
    if (n.type !== "synthesis") continue;
    for (const rid of n.related) if (pos[rid]) edges += edgePath(pos[n.id], pos[rid], true);
  }
  for (const id in pos) nodes += nodeSVG(snap.nodes[id], pos[id]);
  const v = state.view;
  svg.innerHTML = `<g transform="translate(${v.tx},${v.ty}) scale(${v.k})">${edges}${nodes}</g>`;
}

function applyTransform() {
  const g = svg.firstChild;
  if (g) g.setAttribute("transform", `translate(${state.view.tx},${state.view.ty}) scale(${state.view.k})`);
}

function renderLegend() {
  const items = [
    ["q-open", "Q open"], ["q-review", "Q review"], ["q-resolved", "Q resolved"],
    ["h-running", "running"], ["h-supported", "supported"], ["h-partial", "partial"],
    ["h-refuted", "refuted"], ["n-synth", "synthesis"],
  ];
  $("legend").innerHTML = items.map(([c, t]) =>
    `<span class="lg"><span class="sw ${c}"></span>${t}</span>`).join("");
}

// ------------------------------------------------------------------ search / navigation
function matchNode(n) {
  const q = state.search.toLowerCase();
  return q && (n.title.toLowerCase().includes(q) || n.id.toLowerCase().includes(q));
}

function fitToView() {
  const ps = Object.values(state.positions);
  if (!ps.length) return;
  const minX = Math.min(...ps.map((p) => p.x)), maxX = Math.max(...ps.map((p) => p.x)) + NODE_W;
  const minY = Math.min(...ps.map((p) => p.y)) - NODE_H, maxY = Math.max(...ps.map((p) => p.y)) + NODE_H;
  const r = svg.getBoundingClientRect();
  const k = Math.min(1, (r.width - 60) / (maxX - minX || 1), (r.height - 60) / (maxY - minY || 1));
  state.view.k = clamp(k, 0.2, 1);
  state.view.tx = 30 - minX * state.view.k;
  state.view.ty = (r.height - (maxY - minY) * state.view.k) / 2 - minY * state.view.k;
}

function centerOn(id) {
  const p = state.positions[id];
  if (!p) return;
  const r = svg.getBoundingClientRect();
  state.view.tx = r.width / 2 - (p.x + NODE_W / 2) * state.view.k;
  state.view.ty = r.height / 2 - p.y * state.view.k;
  applyTransform();
}

// ------------------------------------------------------------------ selection / detail
function selectNode(id) {
  state.selected = id;
  updateReviewBtn();
  renderTree();
  renderDetail();
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
let drag = null, moved = false;
svg.addEventListener("wheel", (e) => {
  e.preventDefault();
  const v = state.view, r = svg.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const k2 = clamp(v.k * Math.exp(-e.deltaY * 0.0016), 0.2, 3);
  v.tx = mx - (mx - v.tx) * (k2 / v.k);
  v.ty = my - (my - v.ty) * (k2 / v.k);
  v.k = k2;
  applyTransform();
}, { passive: false });

svg.addEventListener("pointerdown", (e) => {
  drag = { x: e.clientX, y: e.clientY, tx: state.view.tx, ty: state.view.ty };
  moved = false;
  svg.setPointerCapture(e.pointerId);
});
svg.addEventListener("pointermove", (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
  state.view.tx = drag.tx + dx;
  state.view.ty = drag.ty + dy;
  applyTransform();
});
svg.addEventListener("pointerup", () => { drag = null; });

svg.addEventListener("click", (e) => {
  if (moved) return;
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
  if (go) selectNode(go.getAttribute("data-go"));
});

$("review-btn").addEventListener("click", showQueue);

$("search").addEventListener("input", (e) => {
  state.search = e.target.value.trim();
  if (state.snap) renderTree();
});
$("search").addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || !state.search || !state.snap) return;
  const hit = Object.keys(state.positions).find((id) => matchNode(state.snap.nodes[id]));
  if (hit) { selectNode(hit); centerOn(hit); }
});

window.addEventListener("resize", () => { if (state.snap) renderTree(); });

poll();
