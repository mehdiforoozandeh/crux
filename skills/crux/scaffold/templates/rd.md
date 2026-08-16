---
type: rd
node: <<node>>
title: <<title>>
status: draft
supersedes: <<supersedes>>
created: <<now>>
updated: <<now>>
---

# <<title>>

RD for [[<<node_basename>>]] — `<<node>>`

## Context

_(what forced this design — the constraint, the finding, or the question that made it necessary)_

## Out of scope

_(an explicit fence: what this design deliberately does NOT cover, binding on the node and its children)_

## Design

_(the substance)_

## Considered options

_(the alternatives, and why each lost — research reasoning lives in the rejected branch)_

## Consequences and known distortions

_(what this design gets wrong on purpose, and what must travel with every result because of it)_

## Supersedes

_(forward-only. An active RD is never amended in place: a design change writes a NEW RD with
  `crux rd <node> "<title>" --supersedes <slug>`, and the chain is the reasoning history.
  The reverse link is generated into RD.md — never write `superseded by` into an old RD.)_
