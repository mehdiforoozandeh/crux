# Requirement — `clamp(value, lo, hi)`

1. Returns `value` when `lo <= value <= hi`.
2. Returns `lo` when `value < lo`.
3. Returns `hi` when `value > hi`.
4. Raises `ValueError` when `lo > hi`. It must refuse rather than silently swap them.
5. The empty case: `lo == hi` is legal, and every input returns that single value.
