# h55 — run report

**Claim.** Timing one thousand repeats gets me under the floor

**Measured.** Total time for 1000 repeats: bubble 0.15 ms, insertion 0.09 ms, selection 0.12 ms.

**What the run showed.** I can see the sorts differ when I stack them. Bubble is clearly slower than insertion even over just 10 items. The timer is not getting in the way at this scale. But a thousand repeats takes less than a millisecond total, which means I have to be very careful about what I am actually timing.
