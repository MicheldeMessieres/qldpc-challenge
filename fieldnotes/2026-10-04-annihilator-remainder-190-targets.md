---
title: "The rest of the block-shaped board: 190 targets, one side tightened, and the sweep tool is committed this time"
date: 2026-10-04
author: "@vprusso"
model: "Claude Fable 5.1 (Claude Code)"
topics: [negative-results, refutation, generalized-bicycle, audit]
status: active
related:
  - 2026-10-03-campaign-portfolio-recap-and-annihilator-sweep.md
---

## TL;DR

Every uncertified entry of even blocklength that the 29 September sweep did
not reach has now been attacked at 40,000 information sets inside each
block annihilator. 190 targets: 136 clean, 53 skipped as out of scope, one
side tightened. 4.44 core-hours.

The one finding is `[[646,162,26]]`, a generalized bicycle code whose Z side
was recorded at 77 and holds a weight-48 logical in each block annihilator.
The distance is unchanged, because the X side bounds it at 26.

The tool is committed this time. The 29 September sweep's was not, which is
why this note exists at all rather than a second run of the same script.

## What was attacked, and what was not

Selection: no exact certificate, even blocklength, not already covered by a
committed annihilator audit. The 53 skips are `code_type: stabilizer`
entries carrying one symplectic check matrix rather than two CSS blocks, so
there is no `A | B` to split. That is out of scope rather than a failure,
and each one records the reason, so the next sweep does not retry them.

| verdict | entries |
|---|---|
| clean at 40,000 information sets | 136 |
| skipped, not CSS | 53 |
| side tightened | 1 |
| distance refuted | 0 |

## The finding

`codes/646-162-26.json`, generalized bicycle, n = 646, k = 162, d = 26.

The Z side was an upper bound of 77. Both block annihilators are
81-dimensional, and each holds a Z-type logical of weight 48, found at
information set 19 and re-measured against the full 40,000 before filing.
The operator is confined to one block, has zero syndrome against the X
checks, and lies outside the row space of the Z checks, all re-derived from
its own support against the live file rather than taken from the search's
report.

The distance does not move: the X side is 26 and 48 is well above it. This
is the fourth shape the attack has produced, after two refutations and four
side tightenings on 29 September, and it is the same shape as those four.

## That the vulnerability is narrow is holding up

Across both sweeps the attack has now run on 1,029 entries and moved eight:
seven distance refutations and five side tightenings, every refutation on
one construction over one group. 136 clean out of 136 in-scope targets here
is consistent with that. The attack is cheap enough to keep running and it
is not finding much, which is the useful thing to be able to say.

## Caveats

- Clean is a statement about a budget, not a proof. 40,000 information sets
  inside a subspace of 8 to 105 dimensions is the budget the filed
  revisions were re-measured at, and nothing here claims more.
- The attack only reaches operators confined to one block. An operator
  split across both blocks is invisible to it, which is the whole reason it
  is cheap.
- The 53 non-CSS entries are untouched by this attack and still have no
  verdict from any structural attack. Whether the analogous split exists
  for a symplectic check matrix is a separate question.
- Two bugs were hit and fixed while running this, both worth knowing about
  because they are the kind that fail quietly. The sweep's skip list
  globbed `research/audits/annihilator-*.json`, which matched the file the
  run was about to write, so a re-run skipped every target and then
  overwrote the record with an empty one. And the 53 non-CSS entries first
  came back as `error`, which would have read as 53 failures rather than 53
  entries the attack does not apply to.
