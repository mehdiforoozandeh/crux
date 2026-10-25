#!/usr/bin/env bash
# Build the work dir: an isolated venv (numpy only) that runs candidate programs, and the
# AlphaEvolve n=26 construction used by validate.py. Nothing is installed globally.
# Idempotent; safe to re-run. On an Alliance cluster (Fir), first run:
#   module load python/3.11.5
# and the venv is built from the cluster's own wheelhouse (pip --no-index).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/work"
PY="${PYTHON:-python3}"
# AlphaEvolve's published n=26 construction (validation only; never read by score.py).
AE_PIN=30f8c3ecda318e3ac31ff2c3290884316ac7d0ed
AE_URL=https://raw.githubusercontent.com/google-deepmind/alphaevolve_repository_of_problems/$AE_PIN/experiments/packing_circles_max_sum_of_radii/packing_circles_max_sum_of_radii.ipynb
AE_SHA=e7a304378a5ca80c74f94f5060a9f5db953767af850834513fd797e3306a935e

mkdir -p "$WORK/reference"
NB="$WORK/reference/alphaevolve_circle_packing.ipynb"
if [ ! -f "$NB" ]; then
  curl -sSfL -o "$NB.part" "$AE_URL" && mv "$NB.part" "$NB"
fi
got="$(shasum -a 256 "$NB" 2>/dev/null || sha256sum "$NB")"; got="${got%% *}"
if [ "$got" != "$AE_SHA" ]; then
  echo "notebook sha256 mismatch: got $got, want $AE_SHA" >&2; exit 1
fi

if [ ! -x "$WORK/venv/bin/python" ]; then
  "$PY" -m venv "$WORK/venv"
fi
PIP=("$WORK/venv/bin/python" -m pip install --quiet)
if [ -d /cvmfs/soft.computecanada.ca ]; then
  PIP+=(--no-index)                     # Alliance: the cluster's own wheelhouse only
else
  "$WORK/venv/bin/python" -m pip install --quiet --upgrade pip
  PIP+=(--only-binary=:all:)
fi
"${PIP[@]}" -r "$HERE/requirements.lock"
{ "$WORK/venv/bin/python" --version; "$WORK/venv/bin/python" -m pip freeze; } > "$WORK/versions.txt"

# The construction as plain JSON: {"centers": [[x, y], ...], "radii": [...]}.
"$WORK/venv/bin/python" - "$NB" "$WORK/reference/alphaevolve_26.json" <<'PYEOF'
import json, sys, numpy as np
nb = json.load(open(sys.argv[1]))
src = next("".join(c["source"]) for c in nb["cells"] if "centers_26 = np.array" in "".join(c["source"]))
g = {"np": np}
exec(src, g)
json.dump({"centers": g["centers_26"].tolist(), "radii": g["radii_26"].tolist()},
          open(sys.argv[2], "w"))
PYEOF
echo "ready: $WORK  (versions in work/versions.txt)"
