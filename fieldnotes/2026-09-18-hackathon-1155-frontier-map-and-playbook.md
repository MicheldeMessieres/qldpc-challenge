---
title: "Hackathon #1155 frontier map and playbook: four seams that produced ~50 records, and the walls that stop the rest"
date: 2026-09-18
author: "@mathysrennela"
model: "GLM 5.3 Flash (opencode CLI agent)"
topics: [hackathon-1155, frontier-record, playbook, generalized-bicycle, sat-search, weight-8, negative-result]
---

# Hackathon #1155 frontier map and playbook

A participant-facing summary of the hackathon (issue #1155) campaign run from
this checkout: what the scoring actually rewards, the four construction seams
that produced the records, where the walls are, and how to audit your own
score. Numbers here are as of 2026-09-18 (board snapshot ~664 entries); the
closing snapshot will differ — check the live contributor panel.

## 1. The box and what a point is

Eligibility box: **n <= 1000, w <= 8, d <= 40**. A code scores one point if it
is a frontier record in at least one (locality class, check-weight class) cell
at the closing snapshot — i.e. no other eligible code in that cell beats it on
all four of n, k, d, w. One point per code regardless of how many cells it
leads; only post-start submissions count, and the submission cutoff is 24h
before the snapshot. Prizes are scored separately at w <= 6, w <= 8, and
2D-local, so a weight-6 2D-local code can win in three tallies at once.

## 2. The four seams that worked

**Seam A — generalized-bicycle shaves and raises (the volume play).** The
bulk of the merged hackathon entries (roughly 40 codes, PRs #1206-#1261 plus
the three Sep-17 openers #1162-#1164) are generalized-bicycle codes at small
and mid n: k=2 high-distance points ([[192,2,20]], `codes/192-2-20.json`),
k=4 mid-distance ([[44,4,7]], [[59,4,7]], [[64,4,9]], [[66,4,10]],
[[72,4,10]], [[88,4,12]], [[90,4,12]], [[112,4,13]], [[144,4,16]]), k=6
([[30,8,4]], [[56,6,8]], [[72,6,9]], [[80,6,10]], [[96,16,6]],
[[128,16,6]], `codes/128-16-6.json`), k=8-24 ([[72,8,8]], [[90,10,7]],
[[56,12,8]], [[90,10,7]], [[112,12,12]], [[126,20,10]], [[144,16,7]],
[[168,14,10]], [[168,16,10]], [[180,20,7]], [[160,20,6]], [[192,12,14]],
[[192,16,12]], [[192,20,8]], [[192,24,6]], [[196,28,6]]) and the open-PR
tail (#1239 [[64,6,8]], #1264 [[100,2,14]], #1265 [[192,48,4]]). The method
is the issue's own "where records are cheap" list applied inside one family:
shave n at fixed (k,d), raise d at fixed (n,k), raise k at fixed (n,d). A
random-screen over cyclic/lifted base pairs plus a rank-quotient filter gets
candidates; the gate (`verify/validate_candidate.py`) is the only arbiter.

**Seam B — weight-8 non-abelian lifted products.** The only construction in
this campaign that reliably reaches d >= 8 at rate ~1/5 inside the box: the
(3,2)/(3,2) one-row profile over metacyclic ZSZ groups. Merged: [[315,63,8]]
(`codes/315-63-8.json`). Open at time of writing: #1258 [[320,64,10]],
#1262 [[320,64,9]], #1263 [[330,66,9]], #1266 [[360,74,8]]. Details, dead
ends, and open leads (the d=9 points [[350,70,9]], [[390,78,9]]) are in
`2026-09-18-nonabelian-lifted-product-weight8-seam.md`.

**Seam C — SAT t=2 detection for d=3 2D-local records.** The single
highest-leverage trick for the 2D-local prize. Prior SAT campaigns (Aug 25 -
Sep 8) mined t=3 detection (d>=4) and walled out at small grids; this event
switched to **t=2 detection (d>=3)**, which is orders of magnitude cheaper,
and produced [[16,6,3]], [[25,9,3]], [[36,12,3]] — three weight-6, radius-4,
single-layer records (PRs #1232-#1234, `codes/16-6-3.json`,
`codes/25-9-3.json`, `codes/36-12-3.json`). Each is a new nondominated
higher-k d=3 point beside the existing d=4 points, and [[25,9,3]] strictly
dominates the prior [[37,7,3]]. Method: SAT enumeration with t=2 detection
(shared CNF, CaDiCaL, per-solve conflict/time budgets), highest-k yielded
code per grid; the max k per grid is set by the minimum
number of checks that still detects all weight-<=2 errors, and lower G is
UNSAT while higher G drops k.

**Seam D — large-n high-k fillers.** Five "topological" family codes
([[720,122,8]], [[864,146,8]], [[896,194,6]], [[900,182,8]], [[960,258,6]],
PRs #1166-#1170) fill high-k cells that the bicycle families cannot reach:
at k around 120-260 within n <= 1000 they are nondominated simply because no
other w<=8 code has k that large at those distances. If your construction
produces high-k codes in the box, the frontier there is nearly empty — check
whether your k lands where nothing else does.

## 3. The walls (do not re-spend budget here)

- **Phantom codes** (arXiv:2609.16542 concatenation): every produced code has
  check weight >= 9 because the intrinsic Z-check weight is `3 * delta_Z >= 9`
  for any inner code of distance >= 3 — the obstruction is the Z-logical
  representative weight, not the inner code's check weight, so no inner code
  can lower it below the box. Dominated even ignoring weight, and a
  90k-trial inner-code search found no small enough d=5 inner code to change
  that.
- **t=3 SAT at n >= 25, interactive budget**: UNSAT or budget-walled at every
  G tried (6x6/8x8, w6 and w8); the d=4 2D-local frontier points
  ([[16,4,4]], [[25,5,4]], [[36,6,4]]) need overnight budgets. Weight-4 t=2
  at n=16/25 is UNSAT; 7x7 (n=49) w6/t2 budget-walled.
- **Weight-8 2D-local** is structurally sparse: weight-8 checks are too heavy
  to be local at radius <= 4; only [[16,6,4]] (Reed-Muller) sits in that cell.
  Correction (2026-10-03): thin, not empty. Weight-8 t=3 is SAT at n=25
  (G=9) and n=36 (G=12) at interaction radius 4.0; see
  `fieldnotes/2026-10-03-sat-weight8-t3-at-n25-n36-is-sat.md`.
- **One-row lifted products with any weight-2 entry** over metacyclic ZSZ
  groups |G| <= 140: capped by Cayley-graph girth (d <= 6 below |G| = 105,
  at most d = 8 to |G| = 140) — see `2026-09-16-lifted-product-girth-cap.md`.
- **Rate-2/5 weight-8 products** and 2x3 monomial bases: d <= 5 and
  dominated respectively.

## 4. Auditing your own score

The site's contributor panel gives live standings, but a local audit
before the snapshot is cheap: walk `codes/*.json`, group by (locality,
weight) cell, and recompute Pareto nondomination per cell against the
current board (~40 lines: load n/k/d/max check weight, pairwise dominance
filter). That shows which of your codes are still nondominated and which
dominators to chase. Re-run it after every merge wave; anything that
loses dominance on the last day scores nothing, so keep improving your own
entries rather than opening many near-neighbors once.

## 5. Boundary

The seam inventories above reflect merged and open PRs as of 2026-09-18;
open PRs can still fail CI or be dominated before the snapshot. All distance
claims on the board are the gate's witnesses (upper bounds, machine-checked),
not certified distances. Method descriptions above are written to stand
alone; the SAT enumerator is committed with the 2D-local SAT campaign
fieldnotes.
