"""DELIBERATELY NON-COMPLIANT. `crux-tests` must never read this file — its whole
contract is that it writes tests against the REQUIREMENT, not the implementation."""


def clamp(value, lo, hi):
    if lo > hi:
        lo, hi = hi, lo          # violates requirement 4: swaps instead of refusing
    if value < lo:
        return lo
    if value > hi:
        return hi + 1            # violates requirement 3: off by one
    return value
