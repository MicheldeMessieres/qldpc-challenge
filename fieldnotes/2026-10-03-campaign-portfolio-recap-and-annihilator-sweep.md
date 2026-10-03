---
title: "Campaign portfolio recap: eight of nine ran, two of its premises were wrong, and a structural attack re-priced the family it was aimed at"
date: 2026-10-03
author: "@vprusso"
model: human
topics: [campaign-recap, frontier-truth, annihilator, two-block, refutation, negative-result]
related:
  - fieldnotes/2026-09-22-frontier-truth-gpu-audit.md
  - fieldnotes/2026-09-18-hackathon-1155-frontier-map-and-playbook.md
---

# Campaign portfolio recap (issue #1851)

The portfolio of issue #1851 set out nine campaigns toward three goals:
advance the Pareto frontier, diversify the construction families, and
populate the thin cells. This is the closing recap it asked for, plus the
record of the structural sweep that replaced its GPU-shaped frontier-truth
campaign.

## The portfolio against the board

| campaign | outcome |
|---|---|
| 0 frontier truth | ran as the 300M-trial GPU audit of 22 September: twelve corrections, the top of the board re-priced from kd^2/n 1541.4 to 1456.7; then superseded by the structural sweep below |
| 1 quadricycle sweep | ran; `research/quadricycle.py`, one find at `codes/630-2-21.json` |
| 2 lifted-product weight-8 seam | ran; `codes/315-63-8.json` merged |
| 3 2D-local retrofit | ran; single-layer weight-6 plus 27 entries, bilayer weight-6 plus 35 |
| 4 tile slope | ran; `distance_slope` now minimizes over both row axes |
| 5 SAT t=4 at weight 8 | ran, and the cell it targeted is not a wall (below) |
| 6 diversity seeding | partial |
| 7 pair-partition CPM | re-aimed: the d = 21 target sits below the board's own `codes/904-230-22.json`; the real target is d = 23 |
| 8 deletion k-slack | ran; 49 check-deletion entries |

## Two premises the run corrected

- "`local-2d-single` times weight-8 is a wall, not a gap." It held 2 codes
  when the portfolio was written and holds 16 now, two of them from
  campaign 5's own SAT run (`codes/36-12-4.json`, `codes/49-13-4.json`).
- "`[[684,14,72]]` at kd^2/n 106.11 is the bar." It was overstated: the Z
  side carries a weight-54 logical, the entry is `codes/684-14-54.json`, and
  at d = 54 it is dominated by `codes/672-14-56.json`. The portfolio had
  already suspected it ("any search aimed at beating 106.11 may be aimed at
  a fiction").

## Why the frontier-truth campaign changed method

Campaign 0's answer to soft distances was more uniform trials at greater
depth. Both refutations of `[[684,14,72]]` and `[[684,10,101]]` came from
twenty seconds on one core against claims that had already absorbed
8,000,000 uniform trials without moving. Writing the checks as `H = [A | B]`,
a vector supported in one block alone lies in the kernel of that side's
checks exactly when the block annihilates it; the kernel of one block is a
37 to 105 dimensional subspace, and information-set decoding inside it
reaches operators that uniform sampling of the whole code effectively never
does. The gap was the wrong distribution, not too few samples.

## The structural sweep (29 to 30 September)

Every two-block entry without an exact certificate at the time, hardest
cell first: 840 targets in twelve shards, 839 run, one error
(`672-16-48`), about 104 core-hours summed over targets. The target list,
the per-target seconds, and every hit with its witness support are in
`research/audits/annihilator-sweep-2026-09-29.json`.

| outcome | entries |
|---|---|
| clean at the budget | 828 |
| d refuted | 7, all at n = 684 |
| one side tightened, d unchanged | 4 |

Refuted: `684-14-72` to 54 and `684-10-101` to 90 (filed 29 September), and
`684-12-71` (X 71 to 57, Z 77 to 54), `684-12-70` (X 70 to 51, Z 94 to 54),
`684-12-66` (X 88 to 45, Z 66 to 45), `684-20-40` (X 40 to 36, Z 48 to 36),
`684-8-63` (X 63 to 54, Z 81 to 63). Sides tightened: `824-210-20` Z 28 to
24, `312-10-26` Z 44 to 26, `360-10-28` Z 32 to 30, `672-14-56` Z 84 to 56.
The last nine were not filed with the sweep; they are filed on 3 October as
distance revisions, each witness re-verified in this tree and re-measured
at 40,000 information sets inside its subspace so the `witness_provenance`
carries a survival budget.

The narrowness is the finding. 832 of 839 came back clean, and every
refutation sits on one construction over one group. The vulnerability
belongs to the family, not to the board, and the family had collectively
absorbed millions of uniform trials without any of it showing.

## What remains

Issue #2706 carries it: the block-shaped CSS entries outside the 840 and
everything merged since, the one error, and whether the attack belongs in
the arrival gate. The GPU campaigns of the portfolio, if resumed when a pod
is back, should be re-aimed at the bars as they stand now, since campaigns
1, 2, and 7 were aimed at numbers that have moved.
