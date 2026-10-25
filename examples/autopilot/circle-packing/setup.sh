#!/usr/bin/env bash
# Build the work dir: an isolated venv (numpy, scipy) that runs candidate programs.
# Nothing is installed globally.
# Idempotent; safe to re-run. On an Alliance cluster (Fir), first run:
#   module load python/3.11.5
# and the venv is built from the cluster's own wheelhouse (pip --no-index).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/work"
PY="${PYTHON:-python3}"
# No reference packing is kept on disk: a candidate runs as the same user and could read it.
# validate.py fetches AlphaEvolve's construction into memory when it needs it. Remove the
# copy that earlier versions of this script left behind.
rm -rf "$WORK/reference" "$WORK/cases"
mkdir -p "$WORK"

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

echo "ready: $WORK  (versions in work/versions.txt)"
