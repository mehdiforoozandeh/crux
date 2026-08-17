---
type: wiki
title: Power management
summary: Battery and power settings make the CPU run slower or faster, changing how long code takes to run.
category: concept
sources: raw/magazine-column-laptops-throttle.txt
---

# Power management

A laptop in battery-saving mode runs slower to preserve the battery. Plugged in, it can run faster.

## Background

Laptops have different power states for different situations. When plugged in and running from AC power, the laptop can use full CPU speed to get work done fast. When on battery, the laptop lowers the CPU speed to use less power and make the battery last longer. Some laptops also reduce the screen brightness and close things the user is not using. All of these changes affect code timing. A benchmark run on battery power gives different times than the same run plugged in. The difference can be ten to thirty percent. Many benchmarking guides recommend plugging in the laptop and setting it to maximum performance mode before measuring. On a school laptop, you may not have permission to change power settings, which means your measurements might include power-saving behavior that is not the laptop at its full speed. If you are aware of this, you can note it when you report results. The key is to measure in a controlled power state and report what that state was, so someone else can reproduce the same conditions or at least understand why their laptop gave different times.

## See also

Related:: [[benchmarking-practice-overview]], [[garbage-collection-pauses]]
