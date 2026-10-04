---
title: "The six walled d=4 SAT rungs re-run on CaDiCaL 1.9.5, the 7x7 bilayer entered, and a [[64,14,4]] from the 8x8 weight-8 rung"
date: 2026-10-04
author: "@vprusso"
model: "Claude Fable 5.1 (Claude Code)"
topics: [sat-search, local-2d-single, t3-detection, negative-result, closure-map]
status: active
related:
  - 2026-10-03-sat-weight8-t3-at-n25-n36-is-sat.md
  - 2026-09-18-sat-2dlocal-campaign.md
---

## TL;DR

Issue #2703 asked for two free checks on the six walled d=4 rungs of the
2D-local SAT campaign and then compute only for what survived. The counting
bound closes none of the six. Re-run on CaDiCaL 1.9.5 at 20,000,000
conflicts per solve and a 3 h wall, all six are still walled, and the
reason is arithmetic rather than solver strength: the issue's "would give
k >= ..." column is 2(n - G), not n - 2G, so at the G it lists a model with
the target k needs 2G - (n - k) dependent rows, which the encoding cannot
ask for. The rungs that ask the question the issue meant are at
G = floor((n - k_min)/2) per side. Of those, 4x4 G=5 w6 is UNSAT in a
minute, 5x5 G=8 w6 and 5x5 G=7 w8 wall at 20,000,000 conflicts, and 6x6
G=12 w6 walls at 3 h.

The 8x8 weight-8 t=3 rung, never entered before, returned a [[64,14,4]] in
80 minutes at G=25 and it passes the gate: `codes/64-14-4.json`, two more
logical qubits than the weight-6 code at the same size. The 7x7 bilayer at
t=2 walled at 3 h in its first solve.

One tool finding. python-sat cannot interrupt a running CaDiCaL solve
(`interrupt` raises NotImplementedError), so a wall cap enforced by a timer
is not enforced at all. The eight runs that were still going at the cap were
stopped by hand eleven minutes late, and `research/sat_rungs.py` now solves
in conflict chunks and checks the wall between them.

## Free check 1: the counting bound

Under t >= 2 every column of each side is nonzero and the columns are
pairwise distinct, which gives G >= 2n/(w+1). For the six rungs that is
G >= 5 (4x4 w6), 4 (4x4 w8), 8 (5x5 w6), 6 (5x5 w8), and 11 (6x6 w6). Every
listed G is above its bound, so the bound closes none of them. It does fix
the lowest G worth entering elsewhere: 28 for the 7x7 bilayer at weight 6
(n = 98) and 15 for 8x8 at weight 8.

## The arithmetic the table rests on

Every model has k >= n - 2G, with equality at full rank, and the campaign's
own codes are all at equality (`codes/64-12-4.json` is 64 - 2(26)). The
issue's table says 5x5 G=16 w6 "would give k >= 18", 4x4 G=8 w8 "k >= 16",
and so on: each entry is 2(n - G). At G=16 per side on 25 qubits a model has
k >= 25 - 32, and reaching k = 8 needs seven dependent rows across the two
sides. The encoding has no way to ask for dependent rows, so an enumeration
at that G walks through near-full-rank models with k of 0 to 2 until the
budget ends, which is what the campaign saw and what the re-run below saw
again (65,000 models at 4x4 G=8, none above k = 2).

The rung that asks "is there a weight-w 2D-local code with k >= k_min at
d >= 4 on this grid" is G = floor((n - k_min)/2) per side, where every model
has k >= k_min by rank alone. With k_min set to one more than the board's
best in each cell: 4x4 w6 G=5 (k >= 6), 4x4 w8 G=4 (k >= 8, already proved
UNSAT on 24 September), 5x5 w6 G=8 (k >= 9), 5x5 w8 G=7 (k >= 11), 6x6 w6
G=12 (k >= 12). An odd k_min on an even grid, such as k = 5 or 7 at n = 16,
needs unequal row counts on the two sides, which the encoder does not have.

## What ran

`research/sat_rungs.py`, CaDiCaL 1.9.5 via python-sat 1.9.dev15, anchor
radius 2.0 (3.5 for the bilayer), shared t=3 encoding with nonempty rows
and lazy exact detection, 20,000,000 conflicts per solve, 3 h wall, one
process per rung on an 18-core laptop with 64 GB. The record is
`research/audits/sat-rungs.jsonl`, one line per rung.

| rung | asks | state | detail |
|---|---|---|---|
| 4x4 G=10 w6 t=3 | k >= 5 | walled | 8,300 models in 3 h, best k = 1 |
| 4x4 G=8 w8 t=3 | k >= 7 | walled | 65,000 models in 3 h, best k = 2 |
| 5x5 G=16 w6 t=3 | k >= 8 | walled | 600 models in 3 h, best k = 1 |
| 5x5 G=13 w8 t=3 | k >= 10 | walled | 1,300 models in 3 h, best k = 2 |
| 6x6 G=25 w6 t=3 | k >= 11 | walled | 100 models in 3 h, best k = 1, 4.5 GB |
| 6x6 G=24 w6 t=3 | k >= 11 | walled | 200 models in 3 h, best k = 1, 4.4 GB |
| 4x4 G=5 w6 t=3 | k >= 6 | UNSAT | 60 s |
| 5x5 G=8 w6 t=3 | k >= 9 | walled | 20,000,000 conflicts in 91 min, no model |
| 5x5 G=7 w8 t=3 | k >= 11 | walled | 20,000,000 conflicts in 68 min, no model |
| 6x6 G=12 w6 t=3 | k >= 12 | walled | 3 h in the first solve, no model, 2.5 GB |
| 7x7x2 G=28 w6 t=2 | k >= 42 | walled | 3 h in the first solve, no model, 5.5 GB |
| 8x8 G=25 w8 t=3 | k >= 14 | SAT | first model at 80 min, k = 14, 19.4 GB |

The eight rows at 3 h were stopped by hand at 3 h 11 min (see the tool
finding below); their model counts are the last the log printed and so
lower bounds.

## The closure

4x4 G=5 w6 t=3 is UNSAT: no weight-6 2D-local CSS code at anchor radius 2.0
on the 4x4 grid detects every weight-3 error with 5 or fewer checks per
side, so none has k >= 6 at d >= 4. With 4x4 G=4 w8 t=3 UNSAT from 24
September, the 4x4 grid is closed at k >= 6 for weight 6 and k >= 8 for
weight 8 under this encoding. k = 5 at weight 6 and k = 7 at weight 8 are
open and need unequal row counts.

## The code

`codes/64-14-4.json`, from 8x8 G=25 w8 t=3: 64 qubits, 14 logical, d = 4,
check weight at most 8, interaction radius 4.0 by construction. The
enumerator's first model passed the post-check and the gate labels it
"advances the weight-8 x local-2d-single board". d >= 4 was re-derived after
staging by enumerating every single-type error of weight at most 3 (43,744
supports per side), and weight-4 logicals of both types were found, so d = 4
exactly; the file carries upper_bound as the kit labels it. The cell's
previous best at d = 4 was [[49,13,4]]; this trades 15 qubits for one
logical qubit and both stay on the frontier. `notes/64-14-4.md` has the
full trail.

## The encoding fix that was not needed

The issue held the 8x8 weight-8 rung back for an encoding change, since a
model the post-check rejects there costs a full solve. On 5x5 weight-8 t=3
at G=9, 40 consecutive models all passed the post-check, and on the 8x8 run
the first model passed, so the rejection rate the concern rests on was not
reproduced. The two guards are in anyway and cost nothing:
`nonempty_rows` adds the clause that every row acts on some qubit, and
`exact_on_reject` adds the exact detection constraint for the error a
rejected model missed instead of blocking the model, so every later model
detects it.

## Tool finding: a wall cap that was never enforced

`research/sat_rungs.py` enforced its wall with a timer thread calling the
solver's `interrupt`. python-sat raises NotImplementedError for CaDiCaL
there, the runner swallowed it, and all eight runs sailed past 3 h. The
same would have been true of any earlier wall cap enforced that way on this
backend. The runner now gives each solve call a chunk of 250,000 conflicts
and checks both caps between chunks; the overrun is bounded by a chunk,
`conflicts_total` is recorded, and `test_sat_rungs.py` has a test that a
zero-hour wall stops after the first chunk.

## Caveats

- Walled is a statement about one build at one budget. The 6x6 G=12 w6 and
  7x7 bilayer rungs were in their first solve at 3 h with no model, so a
  longer run is the next step for both, and memory (2.5 and 5.5 GB) is not
  the constraint at these sizes.
- The stated six rungs at their listed G are not worth re-running at any
  budget as k-increment screens; the question they stand for is the
  G = floor((n - k_min)/2) instance, and that is what the next budget
  should go to. 8x8 G=24 w8 t=3 (k >= 16) is the next rung on the
  weight-8 ladder.
- The 4x4 closures are under this encoding: anchor radius 2.0 on the 4x4
  grid and equal row counts per side.
