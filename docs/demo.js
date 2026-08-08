/* ============================================================================
   crux landing — the scroll-driven demo
   ----------------------------------------------------------------------------
   The shape of the film (crux-marketing/briefs/film-transcript.md), stripped of
   its worked example. Nodes are Q1 / H1 / V1, not sentences: a first-time reader
   is here for the *structure*, and real hypothesis titles read as homework.

   Nothing here is presented as captured stdout — it is a schematic. The one
   place with literal strings is the ledger below the story, which runs the
   engine's own derive_verdict and shows output really captured from the vault.

   State is declarative, not a timeline: for a scroll position we compute
   (beat, fraction) and *set* the stage to what it should look like. Scrolling
   backwards therefore works for free, and there is nothing to unwind.
   ========================================================================== */

const HUM  = 'hum';   // the scientist
const AGT  = 'agt';   // the agent talking
const TOOL = 'tool';  // the agent calling crux as a tool

/* ── the tree, abstract ─────────────────────────────────────────────────── */
/* Laid out in fixed pixels on a virtual canvas, never in percentages. Node
   heights are pixels too, so a percentage pitch collides the moment the pane
   gets short — which is exactly what it did. The auto-fit transform is what
   adapts the tree to the viewport; the layout keeps its shape, and the row
   pitch is always greater than the node height at every size.

   layout() is re-run on resize and on the breakpoint flipping. Computing it
   once at parse time bakes in whatever width the document happened to load
   at — which is not the width it ends up being displayed at. */
const NODES = [
  {id:'root', kind:'root', label:'Project', col:0},
  {id:'q1', kind:'q', label:'Q1', col:1, kids:[0,2]},
  {id:'q2', kind:'q', label:'Q2', col:1},              /* centred over H4·H5·Q3 */
  {id:'q3', kind:'q', p:'q2', label:'Q3', col:2, kids:[5,6]},  /* a question under a question */
  {id:'h1', kind:'h', p:'q1', label:'H1', col:2, row:0, v:3},
  {id:'h2', kind:'h', p:'q1', label:'H2', col:2, row:1, v:3},
  {id:'h3', kind:'h', p:'q1', label:'H3', col:2, row:2, v:3},
  {id:'h4', kind:'h', p:'q2', label:'H4', col:2, row:3, v:3},
  {id:'h5', kind:'h', p:'q2', label:'H5', col:2, row:4, v:3},
  {id:'h6', kind:'h', p:'q3', label:'H6', col:3, row:5, v:3},
  {id:'h7', kind:'h', p:'q3', label:'H7', col:3, row:6, v:3},
];
NODES.forEach(n => { if (!n.p && n.id !== 'root') n.p = 'root'; });

const mqNarrow = matchMedia('(max-width: 640px)');

function layout() {
  const N   = mqNarrow.matches;
  const COL = N ? [0, 104, 208, 312] : [0, 162, 324, 486];
  const ROW = N ? 50 : 64;   // centre-to-centre, siblings
  const GRP = N ? 30 : 40;   // extra air between sibling groups
  const PAD = N ? 24 : 28;

  const hy = [];
  for (let i = 0; i < 7; i++) {
    hy[i] = i === 0 ? PAD + ROW / 2
          : hy[i-1] + ROW + (i === 3 || i === 5 ? GRP : 0);
  }
  const by = {};
  by.q1 = (hy[0] + hy[2]) / 2;
  by.q3 = (hy[5] + hy[6]) / 2;
  by.q2 = (hy[3] + hy[4] + by.q3) / 3;      // Q2 sits over its two H's *and* Q3
  by.root = (by.q1 + by.q2) / 2;

  NODES.forEach(n => {
    n.x = COL[n.col];
    n.y = by[n.id] !== undefined ? by[n.id] : hy[n.row];
  });
  treeLayer.style.width  = (COL[3] + (N ? 78 : 92)) + 'px';
  treeLayer.style.height = (hy[6] + ROW / 2 + PAD) + 'px';
  NODES.forEach(n => {
    const el = nodeEls[n.id];
    if (!el) return;
    el.style.left = n.x + 'px';
    el.style.top  = n.y + 'px';
  });
  lastFit = '';
  drawEdges();
}

/* the literature wiki — laid out by hand so it is stable and needs no
   simulation; categories are the ones the wiki actually uses */
/* Page names are kept — unlike the tree, the wiki is *literature*, not the
   reader's own experiment, and a field of unlabelled dots says nothing. */
const WIKI = [
  ['scaling-laws','concept',20,42],        ['data-vs-model-scaling','comparison',63,30],
  ['compute-optimal-training','concept',38,26], ['sample-efficiency','concept',52,72],
  ['irreducible-error','concept',30,74],   ['distribution-shift','concept',18,88],
  ['data-quality','concept',44,12],        ['data-repetition','concept',72,52],
  ['transfer-learning','concept',80,74],   ['compute-budget','method',10,62],
  ['controlled-comparison','method',48,4], ['held-out-evaluation','method',31,52],
  ['seeds-and-variance','method',44,40],   ['data-pruning','method',80,40],
  ['fine-tuning','method',66,88],          ['imagenet','dataset',88,60],
  ['jft-300m','dataset',92,26],            ['text-corpora','dataset',62,14],
  ['web-scale-image-text','dataset',56,48],['resnet','entity',60,38],
  ['vision-transformer','entity',52,16],   ['transformer-language-models','entity',74,62],
  ['efficientnet','entity',36,90],         ['overview','overview',56,60],
];
const WIKI_EDGES = [
  [0,2],[0,1],[0,4],[0,12],[1,19],[1,20],[1,13],[2,9],[2,17],[3,7],[3,23],
  [4,3],[5,8],[6,13],[7,3],[9,12],[10,6],[11,19],[12,0],[14,8],[15,19],
  [16,17],[18,20],[19,23],[20,23],[21,7],[22,15],[23,3],[23,5],[8,14],[13,16],
];
const WIKI_CAT = {
  concept:'#5b8ff9', method:'#3fb950', dataset:'#c99219',
  entity:'#f0645a', comparison:'#8b5cf6', overview:'#e8e3d9',
};

/* ── the beats ──────────────────────────────────────────────────────────── */
const BEATS = [
  {
    rail:'ask', readout:'a question',
    cap:'You ask. The agent opens it.',
    sub:'A question holds hypotheses. It has no answer of its own.',
    view:'tree', show:{root:'open', q1:'open'},
    lines:[
      {w:HUM,  t:'here is what I actually want to know.'},
      {w:TOOL, n:'crux · ask', r:'Q1 opened'},
    ],
  },
  {
    rail:'ask', readout:'literature · 24 pages',
    cap:'It reads the literature first.',
    sub:'Prior work, compiled from sources you curate — after <a href="https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f" target="_blank" rel="noopener">Karpathy’s LLM-wiki</a>.',
    view:'wiki', show:{root:'open', q1:'open'}, weight:1.6,
    lines:[
      {w:HUM,  t:'what does prior work claim? the bar should come from that, not from us.'},
      {w:TOOL, n:'read · wiki/…', r:'1 of 24 pages', plain:true},
      {w:AGT,  t:'Prior work clusters near a 2-point gain at this scale.'},
    ],
  },
  {
    rail:'ask', readout:'cross-linked into the tree',
    cap:'And it only ever flows one way.',
    sub:'Literature informs the questions. Your findings never flow back into it.',
    view:'wiki', show:{root:'open', q1:'open'}, weight:1.4,
    lines:[
      {w:HUM,  t:'so the bar is theirs, not ours. good.'},
      {w:AGT,  t:'Pages are cross-linked into the tree, so every hypothesis can point at what it came from.'},
    ],
  },
  {
    rail:'hypothesize', readout:'H1 · three verifiables',
    cap:'It proposes a bar. You sharpen it.',
    sub:'Written down before anything runs.',
    view:'tree', show:{root:'open', q1:'open', h1:'idea'},
    lines:[
      {w:AGT,  t:'Proposed bar: one check, a 2-point gain.'},
      {w:HUM,  t:'too weak — one run could give us that by luck. add a second task, and make it hold across three repeats.'},
      {w:TOOL, n:'crux · hypothesize', r:'H1 · V1 V2 V3 locked'},
    ],
  },
  {
    rail:'test', readout:'running',
    cap:'Then it runs.',
    sub:'Fetch, run, compute, record. The cheap part.',
    view:'tree', show:{root:'open', q1:'open', h1:'running'},
    lines:[
      {w:HUM,  t:'run it.'},
      {w:TOOL, n:'crux · test', r:'H1 running'},
    ],
  },
  {
    rail:'close', readout:'checking each bar',
    cap:'The verdict is derived, not argued.',
    sub:'The number it returned is not an input.',
    view:'evidence', show:{root:'open', q1:'open', h1:'supported'},
    focus:['q1','h1'], ticks:3,
    lines:[
      {w:AGT,  t:'Result in. Ticking each bar against it.'},
      {w:TOOL, n:'crux · close', r:'H1 → supported'},
      {w:AGT,  t:'3 of 3 — off the boxes you set, not off the number.'},
    ],
  },
  {
    rail:'review', readout:'weighing the evidence',
    cap:'The part you never delegate.',
    sub:'A clean win, refused. The other arm also got a bigger budget.',
    view:'tree', show:{root:'open', q1:'open', h1:'supported'},
    lines:[
      {w:AGT, t:'H1 is supported. Enough to answer Q1?'},
      {w:HUM, t:'no — the other arm also got a bigger budget, which predicts the same result. test that, and test the harder case.'},
    ],
  },
  {
    rail:'close', readout:'both on the record',
    cap:'Losses stay on the record.',
    sub:'Refuted is filed, not deleted. You never re-run a dead end.',
    view:'tree', show:{root:'open', q1:'open', h1:'supported', h2:'partial', h3:'refuted'},
    lines:[
      {w:TOOL, n:'crux · close', r:'H2 → partial'},
      {w:TOOL, n:'crux · close', r:'H3 → refuted'},
      {w:AGT,  t:'Both on the record. The refuted one stays.'},
    ],
  },
  {
    rail:'answer', readout:'3 questions · 7 hypotheses · 1 open',
    cap:'Then the next question.',
    sub:'Questions nest — Q3 sits under Q2, with hypotheses of its own.',
    view:'tree',
    show:{root:'open', q1:'resolved', h1:'supported', h2:'partial', h3:'refuted',
          q2:'resolved', h4:'supported', h5:'refuted', q3:'open', h6:'running', h7:'idea'},
    lines:[
      {w:TOOL, n:'crux · answer', r:'Q1 resolved'},
      {w:HUM,  t:'good. open the next one.'},
    ],
  },
];

const RAIL = ['ask','hypothesize','test','close','review','answer'];

/* ── build the stage DOM once ───────────────────────────────────────────── */
const cliBody   = document.getElementById('cliBody');
const treeLayer = document.getElementById('treeLayer');
const edgeSvg   = document.getElementById('edges');
const wikiSvg   = document.getElementById('wikiG');
const railEl    = document.getElementById('rail');
const readoutEl = document.getElementById('readout');
const capEl     = document.getElementById('cap');
const subEl     = document.getElementById('sub');
const cockpit   = document.getElementById('cockpit');
const evidence  = document.getElementById('evidence');
const tabTree   = document.getElementById('tabTree');
const tabWiki   = document.getElementById('tabWiki');
const progEl    = document.getElementById('prog');
const tfm       = document.getElementById('tfm');

const nodeEls = {};
NODES.forEach(n => {
  const el = document.createElement('div');
  el.className = 'nd nd-' + n.kind;
  el.innerHTML = '<span class="nlb">' + n.label + '</span>' +
    (n.v ? '<span class="dots"><i>V1</i><i>V2</i><i>V3</i></span>' : '');
  treeLayer.appendChild(el);
  nodeEls[n.id] = el;
});

RAIL.forEach(r => {
  const el = document.createElement('span');
  el.className = 'pill'; el.dataset.r = r; el.textContent = r;
  railEl.appendChild(el);
  if (r !== 'answer') {
    const a = document.createElement('span');
    a.className = 'arw'; a.textContent = '→';
    railEl.appendChild(a);
  }
});

WIKI.forEach((w, i) => {
  const g = document.createElementNS('http://www.w3.org/2000/svg','g');
  g.setAttribute('class','wn');
  g.setAttribute('transform','translate(' + w[2] + ',' + w[3] + ')');
  g.style.transitionDelay = (i * 26) + 'ms';
  const c = document.createElementNS('http://www.w3.org/2000/svg','circle');
  c.setAttribute('r', String(1.4 + (i % 4) * 0.4));
  c.setAttribute('fill', WIKI_CAT[w[1]]);
  const t = document.createElementNS('http://www.w3.org/2000/svg','text');
  t.setAttribute('y','4.7'); t.setAttribute('text-anchor','middle');
  t.textContent = w[0];
  g.appendChild(c); g.appendChild(t);
  wikiSvg.appendChild(g);
});
WIKI_EDGES.forEach(([a,b]) => {
  const l = document.createElementNS('http://www.w3.org/2000/svg','line');
  l.setAttribute('x1',WIKI[a][2]); l.setAttribute('y1',WIKI[a][3]);
  l.setAttribute('x2',WIKI[b][2]); l.setAttribute('y2',WIKI[b][3]);
  l.setAttribute('class','we');
  wikiSvg.insertBefore(l, wikiSvg.firstChild);
});

/* Edges come from untransformed layout geometry (offsetLeft/Top), not from
   getBoundingClientRect — #tfm is scaled and rects would bake that in. */
function geo(el) {
  return {l: el.offsetLeft, t: el.offsetTop - el.offsetHeight / 2,
          w: el.offsetWidth, h: el.offsetHeight};
}
function drawEdges() {
  const W = treeLayer.clientWidth, H = treeLayer.clientHeight;
  if (!W) return;
  edgeSvg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  edgeSvg.setAttribute('width', W); edgeSvg.setAttribute('height', H);
  edgeSvg.innerHTML = '';
  NODES.forEach(n => {
    if (!n.p) return;
    const a = geo(nodeEls[n.p]), b = geo(nodeEls[n.id]);
    const x1 = a.l + a.w, y1 = a.t + a.h / 2;
    const x2 = b.l,       y2 = b.t + b.h / 2;
    const mx = x1 + (x2 - x1) * 0.5;
    const p = document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d','M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2);
    p.setAttribute('class','edge');
    p.dataset.to = n.id;
    edgeSvg.appendChild(p);
  });
  paintEdges();
}
let lastShow = {};
function paintEdges() {
  edgeSvg.querySelectorAll('path').forEach(p => {
    p.classList.toggle('on', !!lastShow[p.dataset.to]);
  });
}

/* frame whatever exists so far: two nodes read large, eleven pull back */
let lastFit = '';
function fit(show, evidenceOpen, focus) {
  const cw = tfm.clientWidth, ch = tfm.clientHeight;
  if (!cw) return;
  const ids = focus && focus.length ? focus : Object.keys(show);
  if (!ids.length) return;
  const pad = 26;
  const ox = treeLayer.offsetLeft, oy = treeLayer.offsetTop;
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  ids.forEach(id => {
    const g = geo(nodeEls[id]);
    x0 = Math.min(x0, g.l + ox); y0 = Math.min(y0, g.t + oy);
    x1 = Math.max(x1, g.l + g.w + ox); y1 = Math.max(y1, g.t + g.h + oy);
  });
  /* Measure the ledger rather than guessing a fraction of the pane — guessing
     is what let it sit on top of H1. Below 640px the ledger is full-width and
     the tree is hidden behind it anyway, so it claims no space. */
  const narrow = innerWidth < 640;
  const evW    = (evidenceOpen && !narrow) ? evidence.offsetWidth : 0;
  const availW = cw - evW - pad * 2;
  const availH = ch - pad * 2;
  const floor  = 0.34;   // never clamp so hard that a node lands under the ledger
  const s  = Math.max(floor, Math.min(3.0, availW / (x1 - x0), availH / (y1 - y0)));
  const tx = pad + (availW - (x1 - x0) * s) / 2 - x0 * s;
  const ty = pad + (availH - (y1 - y0) * s) / 2 - y0 * s;
  const t = 'translate(' + tx.toFixed(1) + 'px,' + ty.toFixed(1) + 'px) scale(' + s.toFixed(3) + ')';
  if (t !== lastFit) { tfm.style.transform = t; lastFit = t; }
}

/* ── render one frame of the story ──────────────────────────────────────── */
let curBeat = -1;
function render(beatIdx, frac) {
  const b = BEATS[beatIdx];
  if (!b) return;

  if (beatIdx !== curBeat) {
    capEl.textContent = b.cap;
    subEl.innerHTML   = b.sub;
    capEl.classList.remove('in'); subEl.classList.remove('in');
    void capEl.offsetWidth;
    capEl.classList.add('in'); subEl.classList.add('in');
    readoutEl.textContent = b.readout;
    railEl.querySelectorAll('.pill').forEach(p => {
      const i = RAIL.indexOf(p.dataset.r), j = RAIL.indexOf(b.rail);
      p.classList.toggle('now', i === j);
      p.classList.toggle('done', i < j || (beatIdx === BEATS.length - 1 && i <= j));
    });
    const now = railEl.querySelector('.pill.now');
    if (now && railEl.scrollWidth > railEl.clientWidth) {
      railEl.scrollTo({left: now.offsetLeft - railEl.clientWidth / 2 + now.offsetWidth / 2,
                       behavior:'smooth'});
    }
    cockpit.dataset.view = b.view === 'wiki' ? 'wiki' : 'tree';
    tabTree.classList.toggle('on', b.view !== 'wiki');
    tabWiki.classList.toggle('on', b.view === 'wiki');
    evidence.classList.toggle('open', b.view === 'evidence');
    curBeat = beatIdx;
  }

  /* ---- the agent session ---- */
  const seen = [];
  for (let i = 0; i < beatIdx; i++) seen.push(...BEATS[i].lines);
  const n = b.lines.length, per = 1 / n;
  const upTo = Math.min(n, Math.floor(frac / per) + 1);
  for (let i = 0; i < upTo - 1; i++) seen.push(b.lines[i]);
  const live = b.lines[upTo - 1];
  const liveFrac = Math.min(1, (frac - (upTo - 1) * per) / (per * 0.7));

  let html = '';
  const tail = seen.slice(-12);
  tail.forEach((l, i) => html += line(l, l.t, i < tail.length - 4 ? ' fade' : ''));
  if (live) {
    const chars = live.t ? Math.max(1, Math.round(live.t.length * liveFrac)) : 0;
    html += line(live, live.t ? live.t.slice(0, chars) : '', ' live',
                 liveFrac > 0.55);
  }
  cliBody.innerHTML = html;
  cliBody.scrollTop = cliBody.scrollHeight;

  /* ---- the cockpit ---- */
  lastShow = b.show;
  NODES.forEach(nd => {
    const st = b.show[nd.id], el = nodeEls[nd.id];
    el.classList.toggle('on', !!st);
    el.dataset.st = st || '';
    if (!nd.v) return;
    const pips = el.querySelectorAll('.dots i');
    let lit = st === 'supported' ? 3 : st === 'partial' ? 1 : 0;
    if (b.ticks && nd.id === 'h1') lit = Math.min(3, Math.floor(frac * 4.2));
    pips.forEach((d, i) => {
      d.className = i < lit ? 'lit' : (st === 'refuted' || st === 'partial') ? 'off' : '';
    });
  });
  paintEdges();
  fit(b.show, b.view === 'evidence', b.focus);

  if (b.ticks) {
    const lit = Math.min(3, Math.floor(frac * 4.2));
    evidence.querySelectorAll('.ev-v').forEach((v, i) => v.classList.toggle('met', i < lit));
    const vd = evidence.querySelector('.ev-verdict');
    vd.textContent = lit === 3 ? 'supported' : lit === 0 ? 'running' : 'checking…';
    vd.dataset.v = lit === 3 ? 'supported' : 'pending';
  }

  progEl.style.transform = 'scaleX(' + (((beatIdx ? CUM[beatIdx-1] : 0) + frac * W[beatIdx]) / TOTAL_W) + ')';
}

function line(l, text, extra, showResult) {
  if (l.w === TOOL) {
    return '<div class="ln l-tool' + extra + '"><span class="gl">⏺</span><span class="tx">' +
      '<b' + (l.plain ? ' class="pl"' : '') + '>' + esc(l.n) + '</b>' +
      (showResult === false ? '' : '<span class="res">✓ ' + esc(l.r) + '</span>') +
      '</span></div>';
  }
  if (l.w === HUM) {   /* no gutter glyph — the bubble's side already says who */
    return '<div class="ln l-hum' + extra + '"><span class="tx">' + esc(text) + '</span></div>';
  }
  return '<div class="ln l-agt' + extra + '"><span class="gl">⏺</span>' +
    '<span class="tx">' + esc(text) + '</span></div>';
}
function esc(s) { return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

/* ── drive it from scroll ───────────────────────────────────────────────── */
/* Beats do not all deserve the same amount of thumb. `weight` buys a beat more
   scroll — the wiki needs time to land, "then it runs" does not. */
const track = document.getElementById('track');
const W = BEATS.map(b => b.weight || 1);
const TOTAL_W = W.reduce((a, b) => a + b, 0);
const CUM = W.reduce((acc, w) => (acc.push((acc[acc.length-1] || 0) + w), acc), []);
const BEAT_VH = innerWidth < 640 ? 78 : 100;
track.style.height = (TOTAL_W * BEAT_VH + 50) + 'vh';

/* progress in [0,1) → which beat, and how far through it */
function locate(p) {
  const x = p * TOTAL_W;
  let i = 0;
  while (i < CUM.length - 1 && x >= CUM[i]) i++;
  const lo = i === 0 ? 0 : CUM[i-1];
  return [i, Math.min(0.9999, (x - lo) / W[i])];
}

let ticking = false;
function onScroll() {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    ticking = false;
    const r = track.getBoundingClientRect();
    const span = r.height - innerHeight;
    if (span <= 0) return;
    const p = Math.max(0, Math.min(0.9999, (-r.top) / span));
    const [i, f] = locate(p);
    render(i, f);
  });
}

layout();   /* place the nodes before anything tries to measure them */

if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
  track.style.height = 'auto';
  document.getElementById('stageWrap').classList.add('static');
  render(BEATS.length - 1, 0.999);
} else {
  addEventListener('scroll', onScroll, {passive:true});
  addEventListener('resize', () => { layout(); onScroll(); });
  mqNarrow.addEventListener('change', () => { layout(); onScroll(); });
  render(0, 0);
  onScroll();
}
addEventListener('load', () => { layout(); onScroll(); });
