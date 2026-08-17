# h62 — run report

**Claim.** The laptop sorts slower on battery than plugged in

**Measured.** Plugged in: 8.7 ms. Battery: 9.6 ms. Ratio: 1.10x slower on battery.

**What the run showed.** Battery power is definitely slower. The sort is 10 percent slower on battery. The times are also more spread out on battery, which suggests the CPU is throttling to save power. I will need to control for this.
