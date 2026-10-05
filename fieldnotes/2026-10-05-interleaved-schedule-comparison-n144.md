---
title: "Interleaved syndrome extraction against the generic builder on three n = 144 bivariate bicycle codes: 13x to 25x per-round error-rate improvement, measured, and why the circuits are not yet committed"
date: 2026-10-05
author: "@vprusso"
model: "Claude Fable 5.1 (Claude Code)"
topics: [circuit-tier, syndrome-extraction, bivariate-bicycle, measurement, ler]
status: active
related:
  - 2026-09-18-hackathon-1155-frontier-map-and-playbook.md
---

## TL;DR

Issue #1026 proposed a Konig edge coloring as a depth improvement to the
generic circuit builder. The thread found that depth is not the figure of
merit: a bare Konig coloring of the combined check-qubit graph leaves X/Z
check pairs with an odd precedence count and every detector comes out
non-deterministic. With the parity condition solved (for bivariate bicycle
codes, a 16-slot SAT instance over term orderings), the interleaved schedule
cuts a round on the three n = 144 candidates from 19 to 21 CX layers to 8 or
9, and the measured per-round logical error rate at p = 0.001 falls by 19x
(144-16-12, 0.0111 to 0.00058), 25x (144-10-16, 0.0066 to 0.00026), and 12x
(144-18-9, 0.0076 to 0.00064). Against surface-code baselines at equal qubit
count, themselves given the textbook interleaved order, all three candidates
win at both rates, by 1.9x to 25x.

The measurements were made on 19 September and lived in two comments on
#1279 and a working directory outside the tree. They are committed here, with
the raw records under `research/audits/schedule-comparison-2026-09-19/`
(`results.jsonl`, `verify_summary.json`).

The circuits themselves are not committed, and the reason is a number. The
circuit tier requires `rounds >= d` and caps a memory experiment's detector
error model at 25,000 mechanisms; the interleaved schedules carry about
7,100 mechanisms per round at n = 144, so at d = 9, 12, and 16 the three
land between 65,000 and 115,000. The parity-respecting interleaving has been
the default of `qldpc submit` since #1859 (`research/circuit_autogen.py`),
and `research/circuit_backfill.py`, added with this note, runs that path over
existing entries; the three codes this note is about are the first it cannot
reach, and the cap is the decision that stands between them and the tier.

## Measurements

| pair | code | role | schedule | rounds | p | layers/round | DEM mech. | shots | failures | per-round rate [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|
| 144-16-12 | surface-d3-x16 | baseline | generic | 3 | 0.002 | 9 CX / 13 | 3518 | 4000 | 1242 | 0.1382 [0.1294, 0.1476] |
| 144-16-12 | surface-d3-x16 | baseline | interleaved | 3 | 0.002 | 4 CX / 6 | 3504 | 4000 | 342 | 0.0303 [0.02719, 0.03375] |
| 144-16-12 | surface-d3-x16 | baseline | interleaved-sat | 3 | 0.002 | 4 CX / 6 | 3342 | 4000 | 444 | 0.04014 [0.03647, 0.04415] |
| 144-16-12 | 144-16-12 | candidate | generic | 3 | 0.002 | 21 CX / 25 | 20539 | 2072* | 847 | 0.2164 [0.1962, 0.2405] |
| 144-16-12 | 144-16-12 | candidate | interleaved | 3 | 0.002 | 9 CX / 11 | 21312 | 1730* | 81 | 0.01612 [0.01294, 0.02007] |
| 144-16-12 | surface-d3-x16 | baseline | generic | 3 | 0.001 | 9 CX / 13 | 3518 | 4000 | 396 | 0.03545 [0.03205, 0.03921] |
| 144-16-12 | surface-d3-x16 | baseline | interleaved | 3 | 0.001 | 4 CX / 6 | 3504 | 4000 | 108 | 0.009167 [0.007585, 0.01108] |
| 144-16-12 | surface-d3-x16 | baseline | interleaved-sat | 3 | 0.001 | 4 CX / 6 | 3342 | 4000 | 176 | 0.01512 [0.01303, 0.01754] |
| 144-16-12 | 144-16-12 | candidate | generic | 3 | 0.001 | 21 CX / 25 | 20539 | 4000 | 130 | 0.01108 [0.009318, 0.01316] |
| 144-16-12 | 144-16-12 | candidate | interleaved | 3 | 0.001 | 9 CX / 11 | 21312 | 4000 | 7 | 0.000584 [0.0002828, 0.001206] |
| 144-16-12 | 144-16-12 | candidate | interleaved | 4 | 0.001 | 9 CX / 11 | 29808 | 2750* | 6 | 0.0005463 [0.0002503, 0.001192] |
| 144-10-16 | surface-d3-x10 | baseline | generic | 3 | 0.002 | 9 CX / 13 | 2124 | 4000 | 804 | 0.07875 [0.07313, 0.08481] |
| 144-10-16 | surface-d3-x10 | baseline | interleaved | 3 | 0.002 | 4 CX / 6 | 2190 | 4000 | 214 | 0.01851 [0.01617, 0.02119] |
| 144-10-16 | surface-d3-x10 | baseline | interleaved-sat | 3 | 0.002 | 4 CX / 6 | 2091 | 4000 | 339 | 0.03002 [0.02693, 0.03345] |
| 144-10-16 | 144-10-16 | candidate | generic | 3 | 0.002 | 20 CX / 24 | 20526 | 2072* | 611 | 0.1285 [0.1172, 0.141] |
| 144-10-16 | 144-10-16 | candidate | interleaved | 3 | 0.002 | 8 CX / 10 | 21888 | 1250* | 24 | 0.006484 [0.00435, 0.009655] |
| 144-10-16 | surface-d3-x10 | baseline | generic | 3 | 0.001 | 9 CX / 13 | 2124 | 4000 | 245 | 0.02131 [0.01877, 0.02419] |
| 144-10-16 | surface-d3-x10 | baseline | interleaved | 3 | 0.001 | 4 CX / 6 | 2190 | 4000 | 78 | 0.006586 [0.005273, 0.008224] |
| 144-10-16 | surface-d3-x10 | baseline | interleaved-sat | 3 | 0.001 | 4 CX / 6 | 2091 | 4000 | 105 | 0.008908 [0.007351, 0.01079] |
| 144-10-16 | 144-10-16 | candidate | generic | 3 | 0.001 | 20 CX / 24 | 20526 | 4000 | 78 | 0.006586 [0.005273, 0.008224] |
| 144-10-16 | 144-10-16 | candidate | interleaved | 3 | 0.001 | 8 CX / 10 | 21888 | 3860* | 3 | 0.0002592 [8.813e-05, 0.0007621] |
| 144-10-16 | 144-10-16 | candidate | interleaved | 4 | 0.001 | 8 CX / 10 | 30384 | 1680* | 2 | 0.0002979 [8.165e-05, 0.001086] |
| 144-18-9 | surface-d3-x18 | baseline | generic | 3 | 0.002 | 10 CX / 14 | 3913 | 4000 | 1428 | 0.1706 [0.1596, 0.1825] |
| 144-18-9 | surface-d3-x18 | baseline | interleaved | 3 | 0.002 | 4 CX / 6 | 3942 | 4000 | 396 | 0.03545 [0.03205, 0.03921] |
| 144-18-9 | surface-d3-x18 | baseline | interleaved-sat | 3 | 0.002 | 4 CX / 6 | 3799 | 4000 | 535 | 0.04928 [0.04514, 0.0538] |
| 144-18-9 | 144-18-9 | candidate | generic | 3 | 0.002 | 19 CX / 23 | 20549 | 4000 | 1234 | 0.1369 [0.1282, 0.1463] |
| 144-18-9 | 144-18-9 | candidate | interleaved | 3 | 0.002 | 8 CX / 10 | 21888 | 1160* | 38 | 0.01117 [0.008117, 0.01535] |
| 144-18-9 | surface-d3-x18 | baseline | generic | 3 | 0.001 | 10 CX / 14 | 3913 | 4000 | 486 | 0.04431 [0.04043, 0.04856] |
| 144-18-9 | surface-d3-x18 | baseline | interleaved | 3 | 0.001 | 4 CX / 6 | 3942 | 4000 | 105 | 0.008908 [0.007351, 0.01079] |
| 144-18-9 | surface-d3-x18 | baseline | interleaved-sat | 3 | 0.001 | 4 CX / 6 | 3799 | 4000 | 184 | 0.01583 [0.01368, 0.01831] |
| 144-18-9 | 144-18-9 | candidate | generic | 3 | 0.001 | 19 CX / 23 | 20549 | 4000 | 90 | 0.007615 [0.00619, 0.009366] |
| 144-18-9 | 144-18-9 | candidate | interleaved | 3 | 0.001 | 8 CX / 10 | 21888 | 3640* | 7 | 0.0006418 [0.0003108, 0.001325] |
| 144-18-9 | 144-18-9 | candidate | interleaved | 4 | 0.001 | 8 CX / 10 | 30384 | 1690* | 3 | 0.0004444 [0.000151, 0.001307] |

`*` shot count truncated by the 1500 s budget.

## Verdicts per pair

### 144-16-12

- p = 0.002, generic: surface-d3-x16 (baseline) has the lower rate, 0.1382 against 0.2164 (ratio 1.57); intervals separate.
- p = 0.002, interleaved: 144-16-12 (candidate) has the lower rate, 0.01612 against 0.0303 (ratio 1.88); intervals separate.
- p = 0.001, generic: 144-16-12 (candidate) has the lower rate, 0.01108 against 0.03545 (ratio 3.20); intervals separate.
- p = 0.001, interleaved: 144-16-12 (candidate) has the lower rate, 0.000584 against 0.009167 (ratio 15.70); intervals separate.
- rounds = 4 at p = 0.001, interleaved candidate only: per-round rate 0.0005463 [0.0002503, 0.001192] from 6 failures in 2750 shots, against 0.000584 at rounds = 3; intervals overlap.

### 144-10-16

- p = 0.002, generic: surface-d3-x10 (baseline) has the lower rate, 0.07875 against 0.1285 (ratio 1.63); intervals separate.
- p = 0.002, interleaved: 144-10-16 (candidate) has the lower rate, 0.006484 against 0.01851 (ratio 2.85); intervals separate.
- p = 0.001, generic: 144-10-16 (candidate) has the lower rate, 0.006586 against 0.02131 (ratio 3.24); intervals separate.
- p = 0.001, interleaved: 144-10-16 (candidate) has the lower rate, 0.0002592 against 0.006586 (ratio 25.41); intervals separate.
- rounds = 4 at p = 0.001, interleaved candidate only: per-round rate 0.0002979 [8.165e-05, 0.001086] from 2 failures in 1680 shots, against 0.0002592 at rounds = 3; intervals overlap.

### 144-18-9

- p = 0.002, generic: 144-18-9 (candidate) has the lower rate, 0.1369 against 0.1706 (ratio 1.25); intervals separate.
- p = 0.002, interleaved: 144-18-9 (candidate) has the lower rate, 0.01117 against 0.03545 (ratio 3.17); intervals separate.
- p = 0.001, generic: 144-18-9 (candidate) has the lower rate, 0.007615 against 0.04431 (ratio 5.82); intervals separate.
- p = 0.001, interleaved: 144-18-9 (candidate) has the lower rate, 0.0006418 against 0.008908 (ratio 13.88); intervals separate.
- rounds = 4 at p = 0.001, interleaved candidate only: per-round rate 0.0004444 [0.000151, 0.001307] from 3 failures in 1690 shots, against 0.0006418 at rounds = 3; intervals overlap.

## Schedule verification

Each built circuit passed: gate set and per-layer parallelism conformance, all detectors deterministic in the noiseless circuit (256 sampled shots), canonical-noise round trip (`noise_recipe_errors` empty), DEM derivation, and `dem_lint` clean. The bare Konig coloring of the combined graph reaches Delta layers but leaves X/Z pairs with an odd precedence count, and those circuits fail the determinism check.

| code | Delta | generic layers (CX / all) | bare Konig depth | pairs violating commutation | interleaved source | interleaved layers (CX / all) | DEM mech. generic | DEM mech. interleaved |
|---|---|---|---|---|---|---|---|---|
| 144-16-12 | 8 | 21 / 25 | 8 | 620 of 1080 | bb-invariant-D9 | 9 / 11 | 20539 | 21312 |
| surface-d3-x16 | 4 | 9 / 13 | 4 | 64 of 128 | geometric | 4 / 6 | 3518 | 3504 |
| 144-10-16 | 8 | 20 / 24 | 8 | 554 of 1008 | bb-invariant-D8 | 8 / 10 | 20526 | 21888 |
| surface-d3-x10 | 4 | 9 / 13 | 4 | 40 of 80 | geometric | 4 / 6 | 2124 | 2190 |
| 144-18-9 | 8 | 19 / 23 | 8 | 586 of 1080 | bb-invariant-D8 | 8 / 10 | 20549 | 21888 |
| surface-d3-x18 | 4 | 10 / 14 | 4 | 72 of 144 | geometric | 4 / 6 | 3913 | 3942 |

RIS upper bound on the circuit distance of the surface baselines (100000 trials or 60 s, seed 7): interleaved rows below; the generic greedy schedule of surface-d3-x10 measured 2 in a separate 60 s run, i.e. a weight-2 undetected logical fault (hook error).

- surface-d3-x10, interleaved (geometric): d_circ <= 3
- surface-d3-x10, interleaved-sat (sat-D4): d_circ <= 2
- surface-d3-x16, interleaved (geometric): d_circ <= 3
- surface-d3-x16, interleaved-sat (sat-D4): d_circ <= 2
- surface-d3-x18, interleaved (geometric): d_circ <= 3
- surface-d3-x18, interleaved-sat (sat-D4): d_circ <= 2

## How the interleaved schedules were built

`build_interleaved.py` keeps build_css_memory's detector, observable and measurement-record conventions and replaces the round body with one reset layer (RX on X ancillas and R on Z ancillas together), D combined CX layers, and one measurement layer (MX and M together). Noise is `apply_noise`, the DEM is `derive_dem`, so the mechanism set is the canonical one.

A Konig coloring of the combined graph (`konig_coloring`, alternating-path recoloring with a built-in audit) reaches exactly Delta layers on every code, but it is not sufficient for interleaving. An X ancilla is prepared in |+>, so Z on it is random; pushing a Z-check measurement back through the circuit, each shared data qubit on which the X-check CX precedes the Z-check CX contributes a factor of that random Z. A Z-check outcome is deterministic iff, for every overlapping X/Z check pair, the number of shared qubits with the X edge first is even (the X-check outcome then follows because overlaps have even size). `parity_violations` counts the offending pairs; the bare Konig coloring violates it on 40 to 620 pairs per code and stim reports every detector as non-deterministic. Issue #1026 counts layers of such colorings and its mechanism counts must have come from circuits that either satisfy this by luck or were derived with gauge detectors allowed; the depth figure stands, the interleaving needs the extra constraint.

Candidates. All three are bivariate bicycle codes on Z_12 x Z_6 in the form HX = [A | B], HZ = [B^T | A^T] (`bb_decompose` recovers the monomials from the matrices). `bb_layers` uses a translation-invariant schedule: X checks couple term A_i in layer alpha_i and B_j in beta_j, Z checks couple B_j^T in gamma_j and A_i^T in delta_i, and because the group is abelian the shared qubits of any overlapping pair come in (L, R) couples indexed by the same (i, j), so the parity condition reduces to (alpha_i < gamma_j) iff (beta_j < delta_i) for all i, j. That 16-slot problem is solved by SAT in milliseconds. At D = Delta = 8 it is feasible iff the A/B interleaving pattern is a palindrome, which needs even term counts: 144-10-16 and 144-18-9 (4+4) get D = 8, 144-16-12 (3+5) gets D = 9. A general SAT encoding of the full graph (`sat_layers`, 11376 variables, 221040 clauses, 1080 parity constraints) was left running on 144-16-12 at D = 8 for about 100 minutes without returning, so whether a non-invariant depth-8 schedule exists for it is open.

Baselines. The interleaved rows use the textbook rotated-surface-code order (`surface_geometric_layers`: X plaquettes in Z order, Z plaquettes in N order), which is a Konig coloring at Delta = 4 and satisfies the parity condition. The interleaved-sat rows use a schedule from the general SAT encoding at D = 4 with no hook-error preference, as a check on how much of the baseline gain is the textbook order rather than the depth. RIS finds a weight-2 undetected logical in the generic greedy baseline circuits (hook error through the d = 3 code), against weight 3 for the geometric schedule.

## Caveats

- Interleaved candidate rows at p = 0.002 are truncated at 1160 to 1730 shots by the budget with 4 workers; the intervals in the table carry that.
- Only the Z basis was measured, as in the pilot.
- The candidate schedules are the first feasible translation-invariant assignment with seed 0; no search over the feasible assignments for hook-error quality was done, and no circuit-distance estimate is available at 21000 mechanisms.
- Same seed 7 and shot cap as the pilot; the sampled shots are identical between schedules of the same code only up to the DEM, which differs, so the two rows of a pair are independent samples.

- The three candidate circuits are not in `circuits/` for the reason in the
  summary: at `rounds = d` their DEMs are three to five times the tier cap.
  Committing them means either raising `MAX_DEM_MECHANISMS` in
  `verify/circuit_verify.py`, a trusted-code change with a CI cost, or
  admitting a declared `rounds < d` for large-d codes, which the tier
  refuses on purpose. Neither is decided here.
- The cap is not specific to these three. The first two frontier entries
  `research/circuit_backfill.py` was pointed at, `[[136,36,10]]` and
  `[[102,20,10]]`, both without a two-block decomposition and so on the
  generic sequential schedule, came out at 89,570 and 65,416 mechanisms at
  `rounds = d = 10`. A crude estimate from the 48 committed tiers (a median
  of 17 mechanisms per round per qubit, which the generic schedule roughly
  matches and the weight-8 bicycle codes exceed threefold) puts about 660 of
  the 1,681 circuit-less CSS entries under the cap, all at small n or small
  d; the efficiency frontier above n = 100 is not among them.
