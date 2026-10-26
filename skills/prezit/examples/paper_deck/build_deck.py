"""Rebuild index.html from deck_src.html by embedding the numbers as DATA.

The paper-arc build pattern: every number on a slide is read here from a result file,
never typed into the deck, and the build records the sha256 of every file it read in the
deck-sources manifest so `crux deck --verify` can prove the deck is current.

Inputs (vault-relative):
  results/h1/metrics.json   first and second task, each arm at its own cost; design constants
  results/h2/metrics.json   replication at own cost; first task at equal training compute
  results/h3/metrics.json   harder task, at own cost and at equal training compute

    python build_deck.py [VAULT]     # default: the shipped scaling_vault
"""
import hashlib, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
VAULT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else \
    (HERE / ".." / ".." / ".." / "crux" / "examples" / "scaling_vault").resolve()
read = []                                       # every file the build reads, in order


def load(rel):
    p = VAULT / rel
    read.append(p)
    return json.loads(p.read_bytes().decode("utf-8"))


def gap(leaf, a=None):
    """A difference leaf as {v, lo, hi}, plus the two arms' accuracies when given."""
    out = {"v": leaf["delta"]["value"], "lo": leaf["delta"]["ci"][0], "hi": leaf["delta"]["ci"][1]}
    if a is not None:
        out.update(data=leaf["data_arm"]["value"], model=leaf["model_arm"]["value"])
    return out


h1, h2, h3 = (load(f"results/{h}/metrics.json") for h in ("h1", "h2", "h3"))
data = {
    "design": {"seeds": h1["design"]["seeds"]["value"],
               "heldout_n": h1["design"]["heldout_n"]["value"],
               "train_base": h1["design"]["train_n_baseline"]["value"],
               "train_data": h1["design"]["train_n_data_arm"]["value"]},
    "own": {"a": gap(h1["task_a"], 1), "b": gap(h1["task_b"]), "rep": gap(h2["equal_data"])},
    "eqc": {"a": gap(h2["equal_compute"])},
    "hard": {"own": gap(h3["equal_data"], 1), "eqc": gap(h3["equal_compute"])},
}

def in_vault(p):
    """p's vault-relative POSIX path, or None when p lies outside the vault."""
    try:
        return p.relative_to(VAULT).as_posix()
    except ValueError:
        return None


# the manifest: every file read, plus this script and the source page when they live in
# the vault (in a real vault they do; this shipped example lives outside it)
src_path = HERE / "deck_src.html"
read += [p for p in (pathlib.Path(__file__).resolve(), src_path) if in_vault(p)]
sources = {in_vault(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in read}

# bytes in, bytes out: UTF-8 and "\n" on every platform, so the build is byte-stable
src = src_path.read_bytes().decode("utf-8")
assert src.count("__DATA__") == 1 and src.count("__SOURCES__") == 1
out = src.replace("__SOURCES__", json.dumps(sources, sort_keys=True))
out = out.replace("__DATA__", json.dumps(data, separators=(",", ":")))
(HERE / "index.html").write_bytes(out.encode("utf-8"))
print(f"wrote {HERE / 'index.html'}: {len(sources)} source file(s)")
