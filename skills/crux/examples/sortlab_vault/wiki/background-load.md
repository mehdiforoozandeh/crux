---
type: wiki
title: Background load
summary: Other programs running on your laptop steal CPU and memory time, making your code slower in unpredictable ways.
category: concept
sources: raw/club-talk-benchmark-mistakes.txt
---

# Background load

Your code is not alone on the laptop. The operating system, browser windows, and background tasks all compete for the same resources.

## Background

When you measure code, you want to measure just the code. But the laptop is doing many things at once. The operating system is running, background updates are happening, the file system is working, and if you have a browser open, it is using CPU too. All of this steals time from your code. A web server might check for new email. The virus scanner might suddenly start scanning. A Bluetooth device might want to connect. Each of these steals a little CPU time, and your code runs slower. This is why benchmark researchers close other applications before measuring. Less background load means less noise in your measurements. You cannot eliminate it completely, but you can reduce it. One way is to measure on a newly booted laptop, before background tasks have accumulated. Another way is to measure many times and use the [[measuring-program-speed]] median or a similar robust statistic, because one slow run from a random background spike does not ruin the whole result. On a shared laptop or in a classroom, background load is always there and always unpredictable, which is why home measurements are often cleaner than school measurements.

## See also

Related:: [[benchmarking-practice-overview]], [[thermal-throttling]]
