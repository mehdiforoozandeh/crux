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
import os, json, hashlib
import engine as E

API = "https://api.openalex.org"


def _fetch(url):
    """The network boundary, isolated to one function so the suite can stub it."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": f"crux/{E.ENGINE_VERSION}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


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
        raise E.CruxError(
            f"openalex: lookup failed for {url} ({e.__class__.__name__}: {e}). "
            "Without a key OpenAlex allows about $0.10 of traffic a day; a free key raises "
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
