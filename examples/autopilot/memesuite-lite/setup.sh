#!/usr/bin/env bash
# Build the frozen work dir: memesuite-lite at the pinned pre-PR-#21 commit, plus an
# isolated venv. Nothing is installed globally. Idempotent; safe to re-run.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/work"
PIN=dd413f654eb9fb9b095fe61edd69b37c53962367     # first parent of PR #21's merge 45549db
POST=45549db5b9bbce69bf6039a6fc0e3f35601138ee    # PR #21 merged (the known answer)
PY="${PYTHON:-python3.11}"

mkdir -p "$WORK"
if [ ! -d "$WORK/memesuite-lite/.git" ]; then
  git clone --quiet https://github.com/jmschrei/memesuite-lite.git "$WORK/memesuite-lite"
fi
git -C "$WORK/memesuite-lite" fetch --quiet origin
git -C "$WORK/memesuite-lite" checkout --quiet --detach "$PIN"
test "$(git -C "$WORK/memesuite-lite" rev-parse HEAD)" = "$PIN"

# The frozen copy the scorer reads tests and the non-tomtom package files from.
rm -rf "$WORK/frozen"
mkdir -p "$WORK/frozen"
git -C "$WORK/memesuite-lite" archive "$PIN" memelite tests | tar -x -C "$WORK/frozen"

# Two candidate checkouts for validation: the pinned baseline and the PR #21 answer.
for name in baseline:$PIN pr21:$POST; do
  dir="$WORK/cand-${name%%:*}"; sha="${name#*:}"
  rm -rf "$dir"; mkdir -p "$dir"
  git -C "$WORK/memesuite-lite" archive "$sha" memelite | tar -x -C "$dir"
done

# The benchmark workload: JASPAR 2024 CORE non-redundant (2,346 motifs), the set PR #21 timed
# and the file memelite's own CLI downloads. Pinned by sha256; the scorer checks it again.
JASPAR_URL=https://jaspar.elixir.no/download/data/2024/CORE/JASPAR2024_CORE_non-redundant_pfms_meme.txt
JASPAR_SHA=9edfb03b9415171a79e2911a84002320232394d34b97952b69bbbbd56b89933d
JASPAR="$WORK/data/JASPAR2024_CORE_non-redundant_pfms_meme.txt"
mkdir -p "$WORK/data"
if [ ! -f "$JASPAR" ]; then
  curl -sSfL -o "$JASPAR.part" "$JASPAR_URL" && mv "$JASPAR.part" "$JASPAR"
fi
if command -v sha256sum >/dev/null; then SHA="sha256sum"; else SHA="shasum -a 256"; fi
got="$($SHA "$JASPAR" | cut -d' ' -f1)"
if [ "$got" != "$JASPAR_SHA" ]; then
  echo "JASPAR sha256 mismatch: got $got, want $JASPAR_SHA" >&2; exit 1
fi

if [ ! -x "$WORK/venv/bin/python" ]; then
  "$PY" -m venv "$WORK/venv"
fi
# Alliance clusters (Fir, Nibi) set CC_CLUSTER. Their Python refuses PyPI manylinux wheels and
# pip there reads only the cluster wheelhouse, which lacks three of the PyPI pins; those
# clusters use requirements.alliance.lock instead.
LOCK="$HERE/requirements.lock"
if [ -n "${CC_CLUSTER:-}" ]; then LOCK="$HERE/requirements.alliance.lock"; fi
"$WORK/venv/bin/python" -m pip install --quiet --upgrade pip
"$WORK/venv/bin/python" -m pip install --quiet --only-binary=:all: -r "$LOCK"
{ "$WORK/venv/bin/python" --version; "$WORK/venv/bin/python" -m pip freeze; } > "$WORK/versions.txt"
echo "ready: $WORK  (versions in work/versions.txt)"
