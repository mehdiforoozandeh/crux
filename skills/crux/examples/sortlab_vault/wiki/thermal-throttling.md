---
type: wiki
title: Thermal throttling
summary: When a laptop gets too hot, it automatically slows down to protect the hardware, making later runs slower than earlier ones.
category: concept
sources: raw/magazine-column-laptops-throttle.txt
---

# Thermal throttling

A laptop has thermal limits. When it reaches them, the processor steps down to a lower speed and power to cool off.

## Background

Laptops are designed to be fast but stay cool. The CPU and GPU can run at full speed for a short time, but if they stay hot, the hardware is at risk. So the operating system monitors temperature, and when it gets too high, the system reduces the CPU speed. This is called throttling. A slower CPU means your code runs slower, so your measurements change. If you run your benchmark when the laptop is cool, you get one set of times. Then you run it again immediately, before the laptop has cooled down from the first run, and the times are slower because of throttling. This makes it impossible to compare results fairly. The fix is to let the laptop cool between runs, or to run your entire benchmark suite in one block quickly while the laptop is still cool, so all runs stay in the same thermal state. On a school laptop that is already warm from the morning, throttling might be happening from the start. This is one reason why benchmark results depend on when and where you measure, and why one person's results do not always match another person's even with the same code.

## See also

Related:: [[benchmarking-practice-overview]], [[power-management]]
