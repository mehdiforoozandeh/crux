# Reference outputs

`expected.json` holds the frozen reference. It holds hashes, not arrays, so it stays small.

- `cases`: one sha256 per input case, over the `.npy` file of `numpy.stack(tomtom(...))`.
  The `.npy` header holds the dtype and the shape, so the hash covers them too.
  A case that raised in the pinned code holds `{"raises": true}`.
- `bench`: one sha256 per JASPAR all-vs-all run: motif orders 0-9 (seeded permutations)
  and `file` (file order, the warm-up run).
- `frozen_tree`: a hash of every file in `work/frozen/` except `memelite/tomtom.py`.
  The scorer refuses to run when the frozen copy differs from it.
- `jaspar_sha256`: the pinned hash of the JASPAR file.
- `versions`: the venv that made the reference. The hashes hold only for these versions.

## How it was made

```
./setup.sh
python3 score.py --make-reference
```

This runs the pinned pre-PR-#21 code (`dd413f6`, in `work/cand-baseline`) through the same
worker that scores a candidate. It takes about 3 minutes. The run used Python 3.11.5 on an Apple M1. Two runs gave
identical hashes for the cases; the JASPAR hashes come from one run, and PR #21 reproduces them.

The cases are:

- All 36 `TOMTOM_CASES` from the repo's own `tests/_golden_inputs.py`, at 1 and 4 threads.
  The two thread counts must give the same bytes.
- 16 edge and bad inputs, defined in `score.py` (`_edge_cases`). Six of them raise in the
  pinned code: an empty query list, an all-zero query, all-zero targets, a NaN column, a
  1-D query, and `n_target_bins=1`.

These inputs were left out because the pinned code is not deterministic on them, or reads
memory it did not write: a width-0 query, a 3-row query against 4-row targets, values near
1e150 (their squares overflow), and `n_score_bins=1` (its output changes with the thread
count). PR #21 gives different bytes from the pinned code on the first three.
