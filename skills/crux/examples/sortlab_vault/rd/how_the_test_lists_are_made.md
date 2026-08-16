---
type: rd
node: q2
title: How the test lists are made
status: active
supersedes: 
created: 2026-08-16T16:06:40
updated: 2026-08-16T16:06:40
---

# How the test lists are made

RD for [[q2_does_the_shape_of_the_list_change_which_]] — `q2`

## Context

I needed to test my sorts on different kinds of lists—random, sorted, reversed, duplicate-heavy—to see if the same sort won every time. I could not just make lists randomly each time because then I would not know if a difference was real or just luck.

Background:: [[wiki/input-generators]], [[wiki/seeded-randomness]]

## Out of scope

This design does not handle lists larger than 1 million items and does not generate adversarial inputs crafted to break a specific algorithm.

## Design

I wrote a generator that takes a shape name and a size. For random, it shuffles numbers 1 to N. For sorted, it leaves them 1 to N. For reversed, it goes N down to 1. For duplicates, it repeats each value 10 times. For nearly sorted, it sorts the list and then swaps 1 percent of pairs. Each shape is generated once with a fixed seed, saved to a file, and reused in all runs. This way every sort sees the exact same list every time.

## Considered options

I thought about generating new lists each run, but that would add noise. I also considered hardcoding the lists, but the generator is more flexible. Using a seed means I can regenerate a list if it gets corrupted, and I can prove to someone else that I used the same input.

## Consequences and known distortions

The lists are deterministic, so if my sort has a bug that only shows up on one random seed, I might miss it. But for this project, one seed per shape is enough. I have to remember that the duplicates list is not random—it is constructed, so it might not match real data.

## Supersedes

_(forward-only. An active RD is never amended in place: a design change writes a NEW RD with
  `crux rd <node> "<title>" --supersedes <slug>`, and the chain is the reasoning history.
  The reverse link is generated into RD.md — never write `superseded by` into an old RD.)_
