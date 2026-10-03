---
title: "Weight-8 t=3 at n=25 and n=36 is satisfiable: correcting the 2026-09-18 dead-end list"
date: 2026-10-03
author: "@vprusso"
model: human
topics: [sat-search, weight-8, local-2d-single, t3-detection, correction, negative-result]
related:
  - fieldnotes/2026-09-18-sat-t2-weight6-2dlocal-records.md
  - fieldnotes/2026-09-18-hackathon-1155-frontier-map-and-playbook.md
---

# Weight-8 t=3 at n=25 and n=36 is satisfiable

## The claim being corrected

`fieldnotes/2026-09-18-sat-t2-weight6-2dlocal-records.md`, "Dead ends (do not
re-mine)", records weight-8 2D-local t=3 detection at n=25 and n=36 as empty
(UNSAT) at the hackathon radius, with radius 4.0 budget-walled, and
`fieldnotes/2026-09-18-hackathon-1155-frontier-map-and-playbook.md` carries the
same conclusion as a do-not-spend row ("weight-8 2D-local is structurally
sparse"). Neither note states which G, solver, or budget produced the UNSAT.

## What was measured (issue #2024, Phase 0, 2026-09-24)

Single-layer grids, `research/local_sat.py` `build_local_cnf` with the shared
t=3 encoding, anchor radius 2.0 (so interaction radius at most 4.0, the
`local-2d-single` cap), CaDiCaL 1.5.3 via python-sat, 20,000,000 conflicts per
solve, a 10,800 s wall cap per instance, at most 40 models, every model
post-checked for a weight <= t stabilizer:

| instance | result | filed |
|---|---|---|
| 5x5 G=9 w8 t=3 | SAT in 134 s; 40 models, all `[[25,7,4]]` (the kept model has max check weight 6) | `codes/25-7-4.json` |
| 6x6 G=12 w8 t=3 | SAT, first model in 322 s, the kept code in 22 min: `[[36,12,4]]` at weight 8 | `codes/36-12-4.json` |
| 4x4 G=4 w8 t=3 | UNSAT, 6,836 conflicts | closes k >= 8 at d >= 4 on 4x4; `codes/16-6-4.json` stands |

So weight-8 t=3 is not empty at n=25 or n=36 at the G that matters, and the
cell is thin rather than structurally empty. The 4x4 closure is the one UNSAT
in this family that is proved.

## What a wall claim has to carry

The error was a claim without its parameters. A negative result in this seam
is a statement about one (grid, G, w, t, radius, solver build, budget), and
the campaign found two further reasons never to record one without them:

- The column-count bound G >= 2n/(w+1) (every column of each side nonzero and
  pairwise distinct under t >= 2) retires rungs below it by hand, and CaDiCaL
  does not find that proof itself in 20M conflicts, nor when handed the
  bound's facts as redundant clauses. For w=8 the lowest G worth trying is 6
  at n=25 and 8 at n=36.
- CaDiCaL 1.9.5 closed two instances that 1.5.3 left open after 3 h, one in
  fewer conflicts than 1.5.3 had already spent. "Walled at N conflicts" is
  about one build.

The six d=4 rungs that remain walled after this campaign, and the two grids it
never entered, are listed with those parameters in issue #2703, with the
free checks to run before any solver time.
