# h84 — run report

**Claim.** The speed-up is bigger for my sorts than for the built-in one

**Measured.** Insertion sped up 4.1 times; built-in sped up 1.8 times; ratio difference was 2.3.

**What the run showed.** Insertion sort improved a lot as the engine warmed up, but the built-in sort barely improved. The engine probably compiles hand-written loops more aggressively than built-in optimized code that is already fast from the start.
