# PRD: crux GUI — Wiki tab (read-only wiki browser in the cockpit)

- **Kind:** feature
- **Roadmap:** Epic 1 (`ui`) × Epic 3 (`wiki`) — adds a new checklist item to Epic 3:
  *"Browse the wiki in the cockpit"* (☑ when this lands). Follows the GUI v1 architecture
  ([`docs/prd/gui-v1.md`](gui-v1.md)); developed under the `evolve-crux` arc
  (this PRD = stage 1 sign-off; its acceptance criteria become the validation gate).

## Problem / motivation

Epic 3 gave the vault a literature layer — `type: wiki` pages under `wiki/`, compiled by
the agent from PI-curated sources in `raw/`, indexed by the generated `WIKI.md` — but the
cockpit can't show it. A PI browsing the program in `crux serve` sees the
question/hypothesis tree only; to read the knowledge the tree *cites* (`[[wiki/…]]`
links in node bodies) they must leave the cockpit for a text editor or Obsidian — exactly
the dependency GUI v1 was built to remove. The wiki is also the layer where *connectivity*
carries meaning (concepts linking concepts, hub pages, orphans), and flat files can't show
that shape at all.

We want a second cockpit view — a **Wiki tab** next to the tree — that makes the wiki
browsable, legible, and connected to the tree, while staying read-only and true to the
GUI v1 ethos: stdlib engine, no-build frontend, one JSON contract, deterministic rendering.

## Design decision

Introduce the cockpit's first **top-level tab switcher** — `Tree | Wiki` — in the topbar
(`#topbar`). Tree remains the default and is unchanged. When the vault has no wiki layer
(`wiki_active` false), the Wiki tab is hidden entirely. The active tab persists in
`localStorage` alongside the existing `crux-*` prefs; whenever `wiki.active` is false —
at load (a persisted `wiki` tab pref is ignored) or mid-session (the poll re-checks it
every second) — the cockpit falls back to the Tree tab.

### The Wiki view — three surfaces, two panes

Reuses the cockpit's two-pane + splitter skeleton, keeping the tree tab's grammar of
"spatial canvas left, detail right":

- **Left pane — navigation.** Two stacked navigators:
  - **Explorer rail** — a slim, collapsible file-tree docked at the left edge. Since
    `wiki/` is flat by convention (the scanner tolerates subdirectories; see the slug
    collision rule under the data contract), folders are *virtual*, derived from each
    page's `category:` frontmatter (`concept/`, `method/`, `entity/`, … — folder names
    are the raw frontmatter category values, exactly the grouping the generated
    `WIKI.md` computes; pages missing `category:` fall under `uncategorized/`, matching
    `scan_wiki_pages`). Pinned below the categories: `index` (the vault's `WIKI.md`),
    `log` (`wiki/log.md`), `schema` (`wiki/SCHEMA.md`), and `sources/` (the `.sources.tsv`
    registry, listed as title + date metadata — not openable in v1).
  - **Graph canvas** — an Obsidian-style link graph of the wiki, filling the rest of the
    pane. Nodes = wiki pages; edges = wikilinks between existing pages. **Force-directed
    but deterministic**: initial positions seeded from a hash of each slug, a fixed
    iteration count, stable node ordering — the same vault renders the same constellation
    on every load (the cockpit's stability ethos, which plain Obsidian physics violates).
    **Color encodes `category`** (legend shown, mirroring the tree tab's kind-color
    grammar); **size encodes link degree** (in + out, over the graph's wiki-to-wiki
    edges), so hub concepts read large and pages with no wiki links read visibly tiny
    and disconnected. (Not the same set as `crux validate`'s orphans — validate counts
    *inbound* links only and also counts citations from tree nodes; the graph
    deliberately shows wiki-layer connectivity.)
    Pan/zoom as in the tree; hover highlights a node's neighborhood; click opens the page.
- **Right pane — the reader.** A stable, dedicated markdown reader (never displaced by
  navigation — the dead-end of putting the explorer here was considered and rejected).
  Before any selection — first open, or when the persisted selection no longer resolves
  to an existing page — the reader shows the wiki index (`_index`), the wiki analog of
  the tree tab's default review-queue pane. Clicking a rail entry *or* a graph node
  renders that page: frontmatter as a compact
  header (category badge, updated date, source paths as text), then the rendered body,
  then a **backlinks section** — "Linked from — N pages", each with the linking page and
  a snippet of the sentence containing the mention; clicking one navigates to it.

### Data contract — index in the snapshot, bodies lazy

The 1s `/snapshot.json` poll gains one **additive** top-level key, `wiki`:

```
wiki: {
  active: bool,
  pages:   [ {slug, title, summary, category, links, sources, hash} … ],   # no bodies
  sources: [ {date, path, title} … ],                     # registry (sha256 dropped)
  specials: {index: bool, log: bool, schema: bool}                          # which exist
}
```

`pages` comes from the existing `scan_wiki_pages` (which already yields slug / title /
summary / category / outgoing `links` / `sources`), stripped to those public fields —
dropping `body` and the scan entries' internal `fn` / `path` / `fm` keys; `path` is an
absolute filesystem path that must never reach the browser — plus a per-page content
`hash` so the frontend can detect that an open page changed. This keeps the rail
and graph **live** (a `crux ingest` or agent page-edit appears within the poll interval)
without shipping page bodies through the poll.

Page bodies are fetched lazily from a new read-only route:

```
GET /wiki/<slug>.json → {slug, title, summary, category, sources, updated,
                          body,                      # raw markdown (no frontmatter)
                          backlinks: [ {slug, title, snippet} … ] }
```

Backlinks are computed server-side per request (the pages whose `links` contain this
slug, with a text snippet around the `[[mention]]`) — consistent with `snapshot()`'s
regenerate-per-request model. Reserved slugs `_index`, `_log`, `_schema` serve the three
special pages through the same response shape: metadata fields the file lacks are `null`
(`WIKI.md` and `wiki/log.md` have no frontmatter; `wiki/SCHEMA.md` carries only
`type`/`title`) and `backlinks` is always `[]` — specials are never graph nodes or
backlink sources, since `scan_wiki_pages` yields only `type: wiki` pages. `updated` is
likewise optional on regular pages (`validate_wiki` requires only `title`/`summary`):
absent → `null`. Slugs are not guaranteed unique (`scan_wiki_pages` recurses into
subdirectories and derives the slug from the bare filename), so lookups resolve
deterministically: reserved names always win, and among scanned pages sharing a slug the
first by sorted path wins. The slug is validated against the scanned page set + reserved
names — never used as a filesystem path — so the route cannot read outside the wiki layer.

### Rendering — client-side, hand-rolled, safe

The frontend renders markdown itself; the server stays a pure JSON API (matching how the
tree works — `app.js` renders, the engine describes). A small hand-rolled renderer in
`app.js` covers the subset the wiki template produces: headings, paragraphs, bold/italic,
inline + fenced code, lists, blockquotes, tables, horizontal rules, external links
(new tab). All content is HTML-escaped before transformation — page text is data, never
injected as markup. `[[slug]]` / `[[slug|alias]]` / `[[slug\|alias]]` (the escaped-pipe
alias form the generated `WIKI.md` index emits — `render.py` writes every index link as
`[[slug\|Title]]`) become in-app navigation; wikilinks to nonexistent pages render in a
distinct broken-link style. Images and raw-source previews
are out of scope (render as inert path text).

### Motion — one vendored file, progressive enhancement

GUI v1 allowed "at most a *single vendored JS file* for graph layout" and never used the
allowance (the tree layout is hand-rolled in `app.js`). This PRD proposes **repurposing
that one-file budget from layout to animation** — a new decision, part of this sign-off.
The file is the **motion.dev browser build** (`dist/motion.js` from `motion@12.x` —
~136 kB minified / ~46 kB gzipped, MIT, exposing the `Motion` global; the package's only
no-build script-tag artifact — the advertised ~2.3 kB "mini" variant exists only as an
ESM subpath requiring a bundler), vendored as a static asset under `webui/vendor/` —
used for graph node entry/hover, tab transitions, and reader content transitions. It is
a *static asset, not a dependency*: no CDN, no build step, and the UI must remain fully
functional (just unanimated) if the file is absent. The engine stays stdlib-only.
Consequence of the repurposing: the wiki graph's deterministic force layout cannot be
vendored and is hand-rolled in `app.js`, per the determinism recipe below. (If ~136 kB
offends, the fallbacks are the legacy `motion@10` UMD at ~25 kB — unmaintained — or a
hand-rolled Web Animations API helper at ~0 kB; the official current artifact is the
default for auditability.)

### Tree ↔ Wiki integration — make the citations live

Tree nodes already cite wiki pages (`[[wiki/slug]]` in question/hypothesis markdown —
encouraged by the one-way flow rule). Today the tree tab's detail pane shows those as
dead text; this feature makes them **clickable**: click → switch to the Wiki tab with
that page open in the reader. No reverse direction exists by design (wiki pages are
forbidden from citing tree nodes; `crux validate` enforces it).

### Search

The topbar search box scopes to the active tab. In the Wiki tab it filters the rail and
dims non-matching graph nodes, matching on slug / title / summary (not full text in v1);
Enter jumps to the best match.

**Main alternatives rejected:**

| Rejected | Why |
|---|---|
| Ship page bodies in `snapshot.json` | Bloats a 1 s poll with tens–hundreds of markdown bodies that are rarely being read; index-only keeps the poll light while staying live. |
| Fully lazy (index outside the snapshot too) | Loses the free liveness of the existing poll; the snapshot stays the one contract the cockpit watches. |
| Server-side markdown → HTML | Moves presentation into the engine and makes the contract HTML instead of data; a renderer gets hand-rolled either way, and client-side matches the tree's division of labor. |
| Reader replacing the explorer in one pane | Both graph and explorer are navigation; the reader evicting the explorer creates a browse/read dead-end. Rail + graph left, stable reader right. |
| Free-floating Obsidian physics | Re-settles differently every load — disorienting in a cockpit; seeded + fixed-iteration force layout keeps the organic look with deterministic positions. |
| Reusing the tree tab's tidy-tree layout for the wiki graph | Wikilinks form an arbitrary graph, not a hierarchy; a tidy tree can't represent it. |
| Raw source preview (`raw/` PDFs etc.) | Client-side renderer can't show PDFs; deferred — sources appear as registry metadata only. |
| Uniform node colors (Obsidian default) | `category:` is right there in frontmatter and the cockpit already speaks color-per-kind; a flat color wastes the channel. |

## Scope

**In v1:**
- `wiki` key in `engine.snapshot()` + `/wiki/<slug>.json` route in `serve.py` (with
  backlinks + snippets), both read-only.
- `Tree | Wiki` tab switcher (Tree default; Wiki hidden when no wiki layer).
- Wiki view: collapsible explorer rail (virtual category folders + pinned
  index/log/schema/sources) + deterministic force-directed graph (color = category,
  size = degree, hover-highlight, click-to-open) + stable reader pane (rendered
  markdown, live wikilinks, broken-link styling, backlinks with snippets).
- Client-side markdown subset renderer (HTML-escaped, XSS-safe).
- Clickable `[[wiki/slug]]` citations in the tree tab's detail pane → Wiki tab.
- Tab-scoped search (slug/title/summary).
- Live updates via the existing poll; an open page re-fetches when its `hash` changes.
- Vendored motion.dev browser build (`dist/motion.js`) as the single allowed static JS
  asset.

**Explicitly NOT in v1 (non-goals):**
- **No writes** — no page creation/editing, no ingest from the GUI; mutations stay in
  the agent/CLI (unchanged GUI v1 rule).
- **No `raw/` preview** — no PDF/text source viewing; registry metadata only.
- **No ghost nodes** for unresolved wikilinks in the graph (broken-link styling in the
  reader only).
- **No full-text search** of page bodies.
- **No URL routing / deep links** (`#wiki/slug`) — the active tab persists via
  `localStorage` like every other cockpit pref. The last-open wiki page also persists —
  **new behavior**, not mirrored from the tree tab (which keeps its selection in memory
  only); a persisted slug that no longer exists on load falls back to the `_index`
  default, per the reader's empty state above.
- **No combined tree+wiki graph** — the one-way flow rule keeps the layers distinct;
  each tab owns its own canvas.
- **No auth / remote hosting / packaging** changes (unchanged from GUI v1).

## Proposed defaults (iterate post-v1; here so the build has a target)

- **Category colors:** stable assignment from a fixed palette keyed by category name
  (hash-based so new categories get colors without config), rendered in a legend chip
  row above the graph. Degree-0 pages (no wiki-to-wiki links in either direction) get a
  muted outline — graph degree, not `crux validate`'s inbound-only orphan check, which
  the snapshot cannot reproduce client-side (it carries no tree-inbound counts).
- **Node size:** radius scales with `sqrt(degree)`, clamped to a sane min/max so a
  single mega-hub can't dominate the canvas.
- **Determinism recipe:** initial position = polar coordinates from
  `hash(slug)`, fixed iteration budget (e.g. 300 ticks), nodes processed in sorted-slug
  order; no randomness anywhere in the simulation.
- **Backlink snippet:** the line containing the `[[mention]]`, trimmed to ~140 chars
  around it.
- **Rail state** (collapsed/expanded, per-category folds) persists in `localStorage`.

## Acceptance criteria

**Automatable → new asserts in `skills/crux/scaffold/selftest.py`:**
- [x] `engine.snapshot(v)` top-level keys are exactly
  `{engine_version, project, nodes, tree, queue, wiki}` (the existing exact-keys assert
  is updated — pre-registered here as an intentional, additive contract change; the
  webui is the contract's only consumer).
- [x] The existing webui pure-read assert ("app.js is pure-read (one GET of
  snapshot.json, no write verbs)") is relaxed — pre-registered here as an intentional
  change for lazy page bodies: `app.js` performs exactly two GET fetches
  (`snapshot.json` and the `/wiki/<slug>.json` route), still with no `method:`
  override anywhere (no write verbs).
- [x] `snapshot(v)["wiki"]` remains JSON-serializable (`json.dumps` round-trips).
- [x] For a wiki-bearing test vault (as built in selftest's `run_wiki`), `wiki.pages`
  has one entry per `scan_wiki_pages` result, each with keys **exactly**
  `{slug, title, summary, category, links, sources, hash}` — in particular none of the
  scan entries' internal `body`, `path`, `fm`, or `fn` keys.
- [x] For a vault with no `wiki/` dir, `wiki.active` is false and `pages` is empty;
  the snapshot is otherwise unchanged and valid.
- [x] `wiki.sources` matches the `.sources.tsv` registry for the wiki-bearing test
  vault: one entry per `load_sources` item, with `path` = the registry key and
  `date`/`title` from its value; `sha256` is intentionally omitted from the served
  spec, so the selftest compares on the projected `{date, path, title}` fields only.
- [x] `/wiki/<slug>.json` for a page of the wiki-bearing test vault returns 200 with
  keys `{slug, title, summary, category, sources, updated, body, backlinks}`, where
  `body` equals the page's markdown body (frontmatter stripped) and missing metadata
  is `null`.
- [x] Backlinks are correct: for the wiki-bearing test vault, each page's `backlinks`
  equals the set of pages whose `links` contain it, and every backlink carries a
  `snippet` containing the `[[mention]]`. (`run_wiki`'s fixture already has real,
  asymmetric inter-page links, so this assert is non-vacuous.)
- [x] Reserved slugs `_index`, `_log`, `_schema` serve `WIKI.md`, `wiki/log.md`,
  `wiki/SCHEMA.md` bodies respectively, with the same JSON keys, `null` for missing
  metadata, and empty `backlinks`.
- [x] Unknown slugs → 404. Traversal-shaped slugs sent through the `/wiki/` route
  specifically (`/wiki/../…`, absolute paths, encoded dots — not bare `/../…`, which
  the static handler already neutralizes) → 404, and no response body contains any
  bytes of a sentinel file planted outside `wiki/` (e.g. the vault's `.crux.yaml`).
  Since the selftest hosts the server in-process, the assert additionally records
  paths opened during these requests (monkeypatched `open`) and verifies none resolve
  outside the wiki layer.
- [x] **Pure read:** serving `/snapshot.json` and `/wiki/<slug>.json` leaves the vault
  byte-for-byte unchanged.
- [x] **Stdlib-only:** all engine/`serve.py` additions import only Python stdlib.
- [x] **No external assets:** `webui/` references no external URLs in `src`/`href`
  attributes (SVG `xmlns` namespace identifiers — `http://www.w3.org/2000/svg` in
  `index.html` and `favicon.svg` — are not fetched assets and are exempt) — the
  vendored motion file is the only third-party JS, served locally.

**Manual → checklist walked in `validate`:**
- [x] `crux serve` on a wiki-bearing vault shows `Tree | Wiki` tabs; Tree is default;
  switching is instant and each tab keeps its state; opening the Wiki tab with no
  prior selection shows the index page in the reader. On a vault without a wiki
  layer, no Wiki tab appears. *(manual)*
- [x] The rail groups pages into category folders matching `WIKI.md`'s grouping, with
  pinned `index` / `log` / `schema` / `sources`; folders collapse/expand; the rail
  itself collapses to reclaim canvas. *(manual)*
- [x] The graph shows one node per page, colored by category (with legend), sized by
  degree; hover highlights the neighborhood; click opens the page; pan/zoom work.
  *(manual)*
- [x] **Deterministic layout:** reloading the page three times renders identical node
  positions. *(manual)*
- [x] The reader renders the test wiki pages' markdown correctly; `[[wikilinks]]`
  navigate in-app (including the `_index` page's `[[slug\|Title]]` links); a link to a
  nonexistent page is visibly broken and inert. *(manual)*
- [x] Each page shows its backlinks with snippets; clicking one navigates to the
  linking page. *(manual)*
- [x] In the Tree tab, a node citing `[[wiki/slug]]` renders it as a link; clicking it
  switches to the Wiki tab with that page open. *(manual)*
- [x] Search in the Wiki tab filters the rail and dims non-matching graph nodes.
  *(manual)*
- [x] `crux ingest` / editing a wiki page via the agent updates the rail and graph
  within ~1–2 s without reload; an open page whose content changed re-renders. *(manual)*
- [x] Animations run via the vendored motion file; deleting the vendor file leaves the
  UI fully functional, just unanimated. *(manual)*
- [x] Light/dark theme applies across rail, graph, and reader. *(manual)*
- [x] The GUI performs **no writes** during a full wiki-browsing session. *(manual)*

## Backward-compat / migration

**None required.** Purely **additive**: a new `wiki` key in the snapshot, a new
read-only route, new frontend code, one vendored static asset. Vault format, verdict
derivation, roll-up, and generated views are untouched — `ENGINE_VERSION` stays `1.1`,
existing vaults load unchanged, and a wiki-less vault simply shows no Wiki tab.
No migration.

## Build sequencing (informative, not part of the gate)

Tests-first, two natural stages: **(1)** engine + server — the `wiki` snapshot key and
`/wiki/<slug>.json` with backlinks, landed fully green against the wiki-bearing test
vault before any
UI exists; **(2)** frontend — tabs, rail, graph, reader, cross-tab links, motion
(manual-checklist criteria). One PR either way; the PRD is the body per `evolve-crux`.
