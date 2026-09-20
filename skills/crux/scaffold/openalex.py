#!/usr/bin/env python3
"""OpenAlex client for the literature wiki (spec 17) — crux's only network path.

Kept out of `engine.py` deliberately. Spec 05's purity line makes the engine the part a
reader can trust by reading it: no process, no network, no clock-dependent branch. So this
module sits beside `autopilot.py` on the impure side of that line, imports `engine` and is
never imported by it, and `crux.py` imports it lazily inside the one branch that needs it —
so every verb that does not ask for OpenAlex never loads a module that can reach the network.

Three further properties, each asserted in selftest:

  opt-in   reached only from an explicit `--doi`; no existing verb gains a network path.
  cached   every response is written to `wiki/.openalex/` and re-read from there, so a
           re-run is free, reproducible, and works offline.
  secret-free   the key is read from OPENALEX_API_KEY and never written to the vault (a
           vault is a git repo). It is also excluded from the cache key, so a cache is
           portable between machines and holds nothing private.
"""
import os, json, math, hashlib
import engine as E

API = "https://api.openalex.org"
LAST_LIMITS = {}   # ratelimit headers from the most recent live request, if any


def _fetch(url):
    """The network boundary, isolated to one function so the suite can stub it.

    Also the only place the remaining daily budget is observable: OpenAlex reports it in a
    response header, so the crawl learns what is left by having asked for something."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": f"crux/{E.ENGINE_VERSION}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8")
        try:
            LAST_LIMITS["remaining"] = int(r.headers.get("x-ratelimit-remaining"))
        except (TypeError, ValueError):
            pass
        return body


def _url(path, params=None):
    import urllib.parse
    url = API + "/" + path.lstrip("/")
    if params:
        url += "?" + urllib.parse.urlencode(sorted(params.items()))
    return url


def get(root, path, params=None):
    """Fetch one OpenAlex record, caching it by url. A warm cache never hits the network."""
    url = _url(path, params)
    cache = os.path.join(root, E.OPENALEX_DIR,
                         hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")
    if os.path.exists(cache):
        return json.loads(E.read(cache))
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    try:
        body = _fetch(url + ("&" if "?" in url else "?") + "api_key=" + key if key else url)
        data = json.loads(body)
    except (OSError, ValueError) as e:   # URLError/HTTPError are OSError; JSONDecodeError is ValueError
        code = getattr(e, "code", None)
        if code == 400:
            raise E.CruxError(
                f"openalex: rejected the query as malformed ({url}). This is a crux bug, not "
                "a key or budget problem — the identifiers in it are not the shape OpenAlex "
                "expects.")
        if code in (401, 403):
            raise E.CruxError(
                f"openalex: refused the request ({code}). OPENALEX_API_KEY is "
                + ("set but not accepted — check it at https://openalex.org/settings/api."
                   if key else "unset, and this endpoint requires one."))
        raise E.CruxError(
            f"openalex: lookup failed for {url} ({e.__class__.__name__}: {e}). "
            + ("Today's budget may be spent; it resets daily. "
               if code == 429 else "")
            + "Without a key OpenAlex allows about $0.10 of traffic a day; a free key raises "
            "that to $1 a day. Register at https://openalex.org/settings/api and export it "
            "as OPENALEX_API_KEY. To skip OpenAlex entirely, ingest with --title instead — "
            "nothing else in crux needs the network.")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    E.write_if_changed(cache, json.dumps(data, ensure_ascii=False, indent=1))
    return data


def work_id(work):
    """https://openalex.org/W123 -> W123."""
    return (work.get("id") or "").rstrip("/").rsplit("/", 1)[-1]


def title_line(work):
    """The registry title: 'Title — Author, Author, ... (Year)'. The registry title is the
    vault's only author-bearing field, which is why the whole list goes in and not 'et al'."""
    name = (work.get("display_name") or work.get("title") or "").strip()
    authors = [a.get("author", {}).get("display_name") for a in work.get("authorships", [])]
    authors = [a.strip() for a in authors if a and a.strip()]
    year = work.get("publication_year")
    out = name + (" — " + ", ".join(authors) if authors else "") + (f" ({year})" if year else "")
    return " ".join(out.split())


def work_by_doi(root, doi):
    """Resolve a DOI to an OpenAlex work record — one singleton lookup, one credit."""
    d = doi.strip().rstrip("/")
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.lower().startswith(prefix):
            d = d[len(prefix):]
    if not d.startswith("10."):
        raise E.CruxError(f"ingest: {doi!r} is not a DOI — expected something like 10.1038/nbt.3820")
    return get(root, "works/https://doi.org/" + d)


# ---------------------------------------------------------------------------------------
# The crawl (spec 17.2) — build the citation subgraph around a seed set, then rank it.
#
# "Crawl" means repeated structured queries for two fields, `referenced_works` and `cites:`,
# walked outward from the seeds and cached. Nothing is scraped and no page is followed.
#
# The ranking is the point. Ranking by citation count returns the field's furniture — Adam,
# BWA, Nextflow — works cited by everything, which is exactly why they say nothing about
# THIS problem. The signal that means on-topic is how many distinct seeds reach a candidate.
# ---------------------------------------------------------------------------------------

IDS_PER_REQUEST = 100     # measured ceiling for an OR'd openalex_id filter, 1 credit a call
FORWARD_CAP     = 200     # top citers per work, by citation count; a seed can have thousands
DEPTH2_MIN_REACH = 2      # a depth-1 work expands only if at least two seeds reach it
DEPTH2_WEIGHT   = 0.5     # a hub reaching a work is worth half a seed reaching it
CITES_FLOOR     = 100     # below this, citation count does not change the divisor at all
CAND_SELECT = "id,doi,display_name,publication_year,cited_by_count,best_oa_location"
HUB_SELECT  = CAND_SELECT + ",referenced_works"



def _bare(wid):
    return (wid or "").rstrip("/").rsplit("/", 1)[-1]


def _norm_title(t):
    """Lowercase alphanumerics only — enough to match a paper against its own duplicate
    record, without matching two genuinely different papers."""
    return "".join(ch for ch in (t or "").lower() if ch.isalnum())


def works_by_ids(root, ids, select=CAND_SELECT):
    """Batch-fetch work records, IDS_PER_REQUEST at a time. One credit per request."""
    out, ids = {}, [i for i in dict.fromkeys(_bare(i) for i in ids) if i]
    for i in range(0, len(ids), IDS_PER_REQUEST):
        chunk = ids[i:i + IDS_PER_REQUEST]
        page = get(root, "works", {"filter": "openalex_id:" + "|".join(chunk),
                                   "per-page": len(chunk), "select": select})
        for w in page.get("results", []):
            out[_bare(w.get("id"))] = w
    return out


def citers(root, wid, cap=FORWARD_CAP, select=CAND_SELECT):
    """The works that cite `wid`, most-cited first. Capped: the tail is noise by construction."""
    page = get(root, "works", {"filter": "cites:" + _bare(wid), "per-page": min(cap, 200),
                               "sort": "cited_by_count:desc", "select": select})
    return page.get("results", [])[:cap]


def _mark(table, cand, source, direction):
    """Record that `source` — a seed at depth 1, or a hub at depth 2 — reaches `cand`."""
    cand = _bare(cand)
    if cand:
        table.setdefault(cand, {}).setdefault(source, direction)


def score(n_seeds, n_hubs, cited_by_count):
    """reach / log10(10 + max(citations, CITES_FLOOR)).

    The numerator counts how much of the seed set reaches this work: one per distinct seed
    that reaches it directly, and DEPTH2_WEIGHT per distinct *hub* that reaches it at depth
    two. Counting hubs rather than seeds at depth two is what stops a single popular hub
    handing its whole seed set to all two hundred of its citers — reaching a hub is not
    reaching the seeds, and crediting it as though it were put bibliographies and
    supplementary files above the field's actual papers.

    The divisor demotes works that everything cites — the field's furniture, which is cited
    universally and says nothing about THIS problem. log10 rather than the raw count, because
    a genuinely central paper in a large field legitimately has a high count. The floor is
    the other half: without it the divisor is smallest at zero citations, so among works of
    equal reach the most obscure one wins, which is the opposite of what is wanted. Below
    CITES_FLOOR citations the divisor is flat and reach alone decides."""
    r = n_seeds + DEPTH2_WEIGHT * n_hubs
    return r / math.log10(10 + max(CITES_FLOOR, int(cited_by_count or 0))), r


def estimate_requests(n_seeds, n_hubs, n_candidates):
    """What the remaining phases will cost, in credits (one credit per request)."""
    return (_ceil_div(n_seeds, IDS_PER_REQUEST) + n_seeds          # seed records + forward
            + _ceil_div(n_hubs, IDS_PER_REQUEST) + n_hubs
            + _ceil_div(n_candidates, IDS_PER_REQUEST))


def _ceil_div(a, b):
    return (a + b - 1) // b if a else 0


def _check_budget(need, phase):
    """Refuse a crawl that cannot finish. Half a candidate list looks complete and is not.

    The budget is only knowable from a response header, so this runs after the first cheap
    request rather than before it — there is no way to ask OpenAlex what is left without
    asking OpenAlex something."""
    left = LAST_LIMITS.get("remaining")
    if left is None or need <= left:
        return
    raise E.CruxError(
        f"openalex: this crawl needs about {need} more credits at the {phase} phase and "
        f"{left} remain on today's budget. It is refusing rather than returning a partial "
        "candidate list, which looks complete and is not. Either wait for the daily reset, "
        "set OPENALEX_API_KEY to a free key (10,000 credits a day instead of 1,000 — "
        "register at https://openalex.org/settings/api), or narrow the crawl with fewer seeds.")


def crawl(root, seed_ids, forward_cap=FORWARD_CAP):
    """Walk the citation graph out from `seed_ids` to depth 2 and rank what it finds.

    Depth 1: every seed's references (backward) and its top citers (forward). Depth 2
    expands only from depth-1 works that at least DEPTH2_MIN_REACH distinct seeds already
    reach — the frontier would otherwise be ~320,000 works, and a work only one seed points
    at is not where the shared subgraph is. Returns rows sorted best-first."""
    # A seed may be given as a DOI. It has to become a work id before anything else, because
    # _bare() would shear "10.1038/nmeth.1906" down to "nmeth.1906" and query for a work that
    # does not exist.
    resolved = []
    for sd in dict.fromkeys(seed_ids):
        sd = (sd or "").strip()
        if not sd:
            continue
        resolved.append(work_id(work_by_doi(root, sd)) if "/" in sd and "10." in sd
                        else _bare(sd))
    seed_ids = [x for x in dict.fromkeys(resolved) if x]
    if not seed_ids:
        raise E.CruxError(
            "lit crawl: no seeds. Seeds are the sources in raw/ that carry an OpenAlex work "
            "id — register them with `crux ingest <file> --doi 10.…` first, or pass "
            "`--seed W…` for a paper that is not in raw/ yet. The seed set is what defines "
            "the subgraph, so a crawl without one has nothing to be about.")
    d1, d2, known = {}, {}, {}      # cand -> {seed: dir} ; cand -> {hub: dir}

    seeds = works_by_ids(root, seed_ids, HUB_SELECT)
    _check_budget(len(seed_ids), "forward-citation")
    for sid in seed_ids:
        for ref in (seeds.get(sid) or {}).get("referenced_works", []):
            _mark(d1, ref, sid, "backward")
        for w in citers(root, sid, forward_cap):
            known[_bare(w.get("id"))] = w
            _mark(d1, w.get("id"), sid, "forward")

    hubs = [c for c, slot in d1.items() if len(slot) >= DEPTH2_MIN_REACH]
    _check_budget(estimate_requests(0, len(hubs), len(d1)), "depth-2")
    hub_works = works_by_ids(root, hubs, HUB_SELECT)
    for hid, w in hub_works.items():
        known[hid] = w
        for ref in w.get("referenced_works", []):
            _mark(d2, ref, hid, "backward")
        for c in citers(root, hid, forward_cap):
            known[_bare(c.get("id"))] = c
            _mark(d2, c.get("id"), hid, "forward")

    # A seed is not a candidate, and neither is anything already curated into raw/. Matching
    # on the work id alone is not enough: OpenAlex carries duplicate records for the same
    # paper (a preprint, a reprint, a second deposit), each with its own id, and a seed's own
    # twin would otherwise come back ranked first. Title and DOI catch those.
    have = {r.get("workid", "") for r in E.load_sources(root).values() if r.get("workid")}
    drop = set(seed_ids) | have
    seen = {_norm_title(w.get("display_name")) for w in seeds.values()}
    seen |= {(w.get("doi") or "").lower() for w in seeds.values() if w.get("doi")}
    seen.discard("")
    cands = [c for c in dict.fromkeys(list(d1) + list(d2)) if c not in drop]
    known.update(works_by_ids(root, [c for c in cands if c not in known]))

    rows = []
    for c in cands:
        w = known.get(c)
        if not w:                       # OpenAlex knows the id as a reference but not the work
            continue
        if _norm_title(w.get("display_name")) in seen or (w.get("doi") or "").lower() in seen:
            continue                    # a duplicate record of a seed, under a second id
        seeds_hit, hubs_hit = d1.get(c, {}), d2.get(c, {})
        cites = int(w.get("cited_by_count") or 0)
        sc, r = score(len(seeds_hit), len(hubs_hit), cites)
        dirs = sorted(set(seeds_hit.values()) | set(hubs_hit.values()))
        rows.append({"score": round(sc, 4), "reach": round(r, 2), "seeds": len(seeds_hit),
                     "hubs": len(hubs_hit), "depth": 1 if seeds_hit else 2,
                     "direction": "+".join(dirs), "workid": c, "cites": cites,
                     "year": w.get("publication_year") or "",
                     "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                     "oa_pdf": (w.get("best_oa_location") or {}).get("pdf_url") or "",
                     "title": title_line(w)})
    # among equal scores the better-cited work wins: the floor made them tie, not the evidence
    rows.sort(key=lambda r: (-r["score"], -r["cites"], r["workid"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


CAND_COLUMNS = ["rank", "score", "reach", "seeds", "hubs", "depth", "direction", "year",
                "cites", "workid", "doi", "oa_pdf", "title"]


def candidates_path(root, slug):
    return os.path.join(root, E.WIKI_DIR, "lit", slug, "candidates.tsv")


def write_candidates(root, slug, rows):
    """Tab-separated and git-tracked: this is the record of what the PI chose from."""
    path = candidates_path(root, slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["\t".join(CAND_COLUMNS)]
    lines += ["\t".join(str(r[c]).replace("\t", " ") for c in CAND_COLUMNS) for r in rows]
    E.write_if_changed(path, "\n".join(lines) + "\n")
    return path


def crawl_scope(root, slug, forward_cap=FORWARD_CAP):
    """Crawl the search named by `slug`: its scope's seeds when it has a scope file, and
    every raw/ source carrying a work id when it does not. A one-topic vault should not have
    to hold a conversation before it can search."""
    scope = E.load_scope(root, slug)
    if scope:
        problems = E.scope_problems(root, scope, slug)
        if problems:
            raise E.CruxError("lit crawl: " + E.scope_path(root, slug) + " has problems:\n  · "
                              + "\n  · ".join(p["message"] for p in problems))
        seeds = scope["seeds"]
    else:
        seeds = [r["workid"] for r in E.load_sources(root).values() if r.get("workid")]
    return crawl(root, seeds, forward_cap=forward_cap)
