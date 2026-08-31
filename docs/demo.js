/* ============================================================================
   crux landing — the scroll-driven demo
   ----------------------------------------------------------------------------
   Locked narrative: strategy/asset-narrative-2026-08-24.md

   Science talk on the left, cockpit filling on the right. No crux verb is
   spoken or shown. The PI talks science; the agent files in silence; the
   viewer sees the notebook happen.

   Generic placeholders, matching the chat GIF turn for turn
   (strategy/gif7-chat-2026-08-29.md). Supersedes the SortLab cut for this
   asset. Speakers are HUM and AGT only — filing is the cockpit changing,
   never a tool chip. No crux noun is ever spoken in the conversation.
   Hollow ring = question. Filled ring = hypothesis. Square = verifiable.

   The page runs the GIF's arc and then keeps going: hypothesis 2 comes back
   supported and the PI refuses the clean win. That beat has no room in a
   46-second loop but it is the sharpest proof of "you stay the lead
   scientist", so the page keeps it.

   State is declarative: for a scroll position we compute (beat, fraction)
   and *set* the stage. Scrolling backwards works for free.
   ========================================================================== */

const HUM = 'hum';
const AGT = 'agt';

/* ── the tree, shaped exactly as the GIF's ──────────────────────────────── */
/* Laid out in fixed pixels on a virtual canvas. layout() re-runs on resize
   and on the breakpoint flipping — computing it once at parse time bakes in
   the load width, which is not the display width. */
const NODES = [
  {id:'root', kind:'root', label:'Project 1',    col:0, row: 1.40},
  {id:'q1',   kind:'q',    label:'Question 1',   col:1, row: 0.60},
  {id:'h1',   kind:'h',    label:'Hypothesis 1', col:2, row: 0.00, p:'q1'},
  {id:'v1',   kind:'v',    label:'Verifiable 1', col:3, row:-0.50, p:'h1'},
  {id:'v2',   kind:'v',    label:'Verifiable 2', col:3, row: 0.50, p:'h1'},
  {id:'h2',   kind:'h',    label:'Hypothesis 2', col:2, row: 1.80, p:'q1'},
  {id:'v3',   kind:'v',    label:'Verifiable 3', col:3, row: 1.80, p:'h2'},
  {id:'q2',   kind:'q',    label:'Question 2',   col:1, row: 3.00},
];
NODES.forEach(n => { if (!n.p && n.id !== 'root') n.p = 'root'; });

const mqNarrow = matchMedia('(max-width: 640px)');

function layout() {
  const N   = mqNarrow.matches;
  const COL = N ? [0, 116, 246, 394] : [0, 168, 356, 566];
  const ROW = N ? 62 : 76;
  const PAD = N ? 24 : 32;
  const lastW = N ? 108 : 138;

  /* rows are relative offsets on the node itself, so the four columns and the
     verifiables straddling their hypothesis stay proportional at both widths */
  let lo = 1e9, hi = -1e9;
  NODES.forEach(n => { lo = Math.min(lo, n.row); hi = Math.max(hi, n.row); });

  NODES.forEach(n => {
    n.x = COL[n.col];
    n.y = PAD + (n.row - lo) * ROW + ROW / 2;
  });
  treeLayer.style.width  = (COL[3] + lastW) + 'px';
  treeLayer.style.height = (PAD * 2 + (hi - lo) * ROW + ROW) + 'px';
  NODES.forEach(n => {
    const el = nodeEls[n.id];
    if (!el) return;
    el.style.left = n.x + 'px';
    el.style.top  = n.y + 'px';
  });
  lastFit = '';
  drawEdges();
}

/* the literature wiki — generic page names matching the GIF, laid out by hand so the
   graph is stable. Categories match the vault. */
const WIKI = [
  ['Area 1','overview',40,14],
  ['Paper 1','method',18,36],
  ['Paper 2','method',42,32],
  ['Paper 3','method',16,58],
  ['Paper 4','method',68,24],
  ['Paper 5','method',86,40],
  ['Paper 6','method',64,46],
  ['Paper 7','method',82,64],
  ['Area 2','overview',48,60],
  ['Paper 8','concept',32,76],
  ['Paper 9','concept',58,80],
  ['Paper 10','method',74,86],
  ['Paper 11','concept',22,90],
  ['Paper 12','concept',12,20],
  ['Area 3','overview',88,22],
  ['Area 4','concept',92,72],
];
const WIKI_EDGES = [
  [0,1],[0,2],[0,4],[0,6],
  [1,2],[2,3],[2,6],
  [4,5],[4,6],[6,7],[6,14],[7,15],
  [8,9],[8,10],[8,11],[9,12],[10,11],
  [13,0],[14,6],
];
const WIKI_CAT = {
  concept:'#5b8ff9', method:'#3fb950', dataset:'#c99219',
  entity:'#f0645a', comparison:'#8b5cf6', overview:'#e8e3d9',
};

/* work items — generic, matching the GIF's taskhub.
   The real taskhub is a hierarchy (All / By category render a nested tree):
   `p` is the parent, and the parent carries an n/m-done progress chip. */
const TASKS = [
  {id:'plan', title:'Plan 1'},
  {id:'t1', title:'Task 1', p:'plan'},
  {id:'t2', title:'Task 2', p:'plan'},
  {id:'t3', title:'Task 3', p:'plan'},
];

/* ── the beats ──────────────────────────────────────────────────────────── */
const BEATS = [
  {
    rail:'question', readout:'the question',
    cap:'More results. Further from the science.',
    sub:'You are producing more code, more experiments and more results than ever — and you are further from understanding the science than you were.',
    view:'tree', show:{root:'open', q1:'open', h1:'idea'},
    focus:['root','q1','h1'],
    lines:[
      {w:HUM, t:'«question 1» still doesn\'t add up. I think «hypothesis 1».'},
    ],
  },
  {
    rail:'literature', readout:'prior work',
    cap:'The agents keep the literature.',
    sub:'Prior work, compiled from sources you curate — after <a href="https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f" target="_blank" rel="noopener">Karpathy’s LLM-wiki</a>. Your findings never flow back into it.',
    view:'wiki', show:{root:'open', q1:'open', h1:'idea'}, weight:1.4,
    lines:[
      {w:AGT, t:'«paper 2» saw the same thing in «area 1» — but never ruled out «confound 1».'},
    ],
  },
  {
    rail:'check', readout:'a bar, set first',
    cap:'You decide what would count.',
    sub:'The checks are on the tree before anything runs — so nothing can be talked into a result afterwards. You set the bar; the notebook files it.',
    view:'tree', show:{root:'open', q1:'open', h1:'idea', v1:'open', v2:'open'},
    focus:['q1','h1','v1','v2'], weight:1.5,
    lines:[
      {w:HUM, t:'my test then: if «hypothesis 1» holds, «signal 1» shows up and «signal 2» stays flat.'},
      {w:HUM, t:'either one breaks it. run it.'},
    ],
  },
  {
    rail:'work', readout:'the work of the lab',
    cap:'The agents run the work.',
    sub:'Plans break into subtasks and the agents drive the list. A finished run still waits for your sign-off.',
    view:'taskhub', show:{root:'open', q1:'open', h1:'idea', v1:'open', v2:'open'},
    weight:1.3,
    tasks:{plan:'open', t1:'done', t2:'done', t3:'run'},
    lines:[
      {w:AGT, t:'Prepping the data. I\'ll compare as soon as it\'s through.'},
    ],
  },
  {
    rail:'finding', readout:'what the data did',
    cap:'Evidence, not a verdict.',
    sub:'The agent reports what the data did and ticks the checks. It stops there.',
    view:'tree',
    show:{root:'open', q1:'open', h1:'idea', v1:'supported', v2:'refuted'},
    focus:['h1','v1','v2'], weight:1.2,
    lines:[
      {w:AGT, t:'«signal 1» showed up. «signal 2» did not stay flat.'},
    ],
  },
  {
    rail:'verdict', readout:'you call it',
    cap:'The verdict is yours.',
    sub:'A hypothesis dies when you say it does — off the bar you set, not off a number somebody liked.',
    view:'tree',
    show:{root:'open', q1:'open', h1:'refuted', v1:'supported', v2:'refuted', h2:'idea'},
    weight:1.4,
    lines:[
      {w:HUM, t:'then «hypothesis 1» is dead. «confound 1» is the likelier story — «hypothesis 2» next.'},
    ],
  },
  {
    rail:'verdict', readout:'a clean result',
    cap:'A clean result.',
    sub:'«hypothesis 2» cleared its check. Filed as supported — and still waiting on you.',
    view:'tree',
    show:{root:'open', q1:'open', h1:'refuted', v1:'supported', v2:'refuted', h2:'supported', v3:'supported'},
    focus:['h2','v3'], weight:1.2,
    lines:[
      {w:AGT, t:'«hypothesis 2» came through — «signal 3» held everywhere we looked.'},
    ],
  },
  {
    rail:'refuse', readout:'you refuse the clean win',
    cap:'',
    sub:'',
    view:'tree',
    show:{root:'open', q1:'open', h1:'refuted', v1:'supported', v2:'refuted', h2:'supported', v3:'supported', q2:'open'},
    weight:1.6,
    lines:[
      {w:HUM, t:'not yet. «signal 3» was too easy a bar — «question 2» is what would actually settle it.'},
      {w:AGT, t:'Then that\'s next. I\'ll line up the comparison.'},
    ],
  },
  {
    rail:'refuse', readout:'you stay in the science',
    cap:'You can work for weeks without noticing.',
    sub:'The tree, the wiki and the task list fill in silence — so months later, the why is still there. You stay the lead scientist.',
    view:'tree',
    show:{root:'open', q1:'open', h1:'refuted', v1:'supported', v2:'refuted', h2:'supported', v3:'supported', q2:'open'},
    weight:1.3,
    lines:[
      {w:HUM, t:'keep going — I\'ll look again when there\'s a result worth arguing about.'},
    ],
  },
];

const RAIL = ['question','literature','check','work','finding','verdict','refuse'];

/* ── build the stage DOM once ───────────────────────────────────────────── */
const cliBody   = document.getElementById('cliBody');
const treeLayer = document.getElementById('treeLayer');
const edgeSvg   = document.getElementById('edges');
const wikiSvg   = document.getElementById('wikiG');
const taskView  = document.getElementById('taskhubView');
const railEl    = document.getElementById('rail');
const readoutEl = document.getElementById('readout');
const capEl     = document.getElementById('cap');
const subEl     = document.getElementById('sub');
const cockpit   = document.getElementById('cockpit');
const tabTree   = document.getElementById('tabTree');
const tabWiki   = document.getElementById('tabWiki');
const tabTask   = document.getElementById('tabTaskhub');
const progEl    = document.getElementById('prog');
const tfm       = document.getElementById('tfm');

const nodeEls = {};
NODES.forEach(n => {
  const el = document.createElement('div');
  el.className = 'nd nd-' + n.kind;
  const ring = document.createElement('i');
  ring.className = 'ring';
  const lab = document.createElement('span');
  lab.className = 'nlb';
  lab.textContent = n.label;
  el.appendChild(ring);
  el.appendChild(lab);
  treeLayer.appendChild(el);
  nodeEls[n.id] = el;
});

RAIL.forEach(r => {
  const el = document.createElement('span');
  el.className = 'pill'; el.dataset.r = r; el.textContent = r;
  railEl.appendChild(el);
  if (r !== RAIL[RAIL.length - 1]) {
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

const taskEls = {}, taskChips = {};
TASKS.forEach((tk, i) => {
  const el = document.createElement('div');
  el.className = 'tk' + (tk.p ? ' sub' : '');
  el.style.transitionDelay = (i * 70) + 'ms';
  const dot = document.createElement('i');
  const lab = document.createElement('span');
  lab.textContent = tk.title;
  el.appendChild(dot);
  el.appendChild(lab);
  if (TASKS.some(o => o.p === tk.id)) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    el.appendChild(chip);
    taskChips[tk.id] = chip;
  }
  taskView.appendChild(el);
  taskEls[tk.id] = el;
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

/* frame whatever exists so far: two nodes read large, five pull back */
let lastFit = '';
function fit(show, focus) {
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
  const availW = cw - pad * 2;
  const availH = ch - pad * 2;
  const s  = Math.max(0.42, Math.min(2.4, availW / (x1 - x0), availH / (y1 - y0)));
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
    cockpit.dataset.view = b.view;
    tabTree.classList.toggle('on', b.view === 'tree');
    tabWiki.classList.toggle('on', b.view === 'wiki');
    tabTask.classList.toggle('on', b.view === 'taskhub');
    curBeat = beatIdx;
  }

  /* ---- the conversation ---- */
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
    html += line(live, live.t ? live.t.slice(0, chars) : '', ' live');
  }
  cliBody.innerHTML = html;
  cliBody.scrollTop = cliBody.scrollHeight;

  /* ---- the cockpit ---- */
  lastShow = b.show;
  NODES.forEach(nd => {
    const st = b.show[nd.id], el = nodeEls[nd.id];
    el.classList.toggle('on', !!st);
    el.dataset.st = st || '';
  });
  paintEdges();
  if (b.view === 'tree') fit(b.show, b.focus);

  TASKS.forEach(tk => {
    const st = (b.tasks || {})[tk.id];
    const el = taskEls[tk.id];
    el.classList.toggle('on', !!st);
    el.dataset.st = st || '';
  });
  Object.keys(taskChips).forEach(id => {
    const kids = TASKS.filter(o => o.p === id);
    const done = kids.filter(o => (b.tasks || {})[o.id] === 'done').length;
    taskChips[id].textContent = done + '/' + kids.length + ' subtasks';
  });

  progEl.style.transform = 'scaleX(' + (((beatIdx ? CUM[beatIdx-1] : 0) + frac * W[beatIdx]) / TOTAL_W) + ')';
}

function line(l, text, extra) {
  if (l.w === HUM) {
    return '<div class="ln l-hum' + extra + '"><span class="tx">' + esc(text) + '</span></div>';
  }
  return '<div class="ln l-agt' + extra + '"><span class="gl">⏺</span>' +
    '<span class="tx">' + esc(text) + '</span></div>';
}
function esc(s) { return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

/* ── drive it from scroll ───────────────────────────────────────────────── */
const track = document.getElementById('track');
const W = BEATS.map(b => b.weight || 1);
const TOTAL_W = W.reduce((a, b) => a + b, 0);
const CUM = W.reduce((acc, w) => (acc.push((acc[acc.length-1] || 0) + w), acc), []);
const BEAT_VH = innerWidth < 640 ? 78 : 100;
track.style.height = (TOTAL_W * BEAT_VH + 50) + 'vh';

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

layout();

/* Reduced motion gets the last frame — the finished tree — because a static
   reader sees one frame and it should be the one carrying the most. Repaint
   through paint(), never through onScroll() directly: onScroll recomputes a
   beat from scroll position and would replace the finished tree with beat 1. */
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const paint = () => REDUCED ? render(BEATS.length - 1, 0.999) : onScroll();

if (REDUCED) {
  track.style.height = 'auto';
  document.getElementById('stageWrap').classList.add('static');
} else {
  addEventListener('scroll', onScroll, {passive:true});
  render(0, 0);
}
addEventListener('resize', () => { layout(); paint(); });
mqNarrow.addEventListener('change', () => { layout(); paint(); });
paint();
addEventListener('load', () => { layout(); paint(); });
