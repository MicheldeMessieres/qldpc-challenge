---
title: "Issue #2863 Tier 1 reconstructions: every paper publishes enough to rebuild its codes, two of the seven yield a filing ([[200,16,17]] routing code, [[468,36,20]] canonical lifted product), the vine and self-dual BB families are dominated"
date: 2026-10-07
author: "@vprusso"
model: "Claude Fable 5.1 (Claude Code)"
topics: [literature, openalex, routing-codes, lifted-product, vine-codes, self-dual-bb, trivariate-bicycle, negative-result]
status: active
---

## TL;DR

Issue #2863 listed seven papers (L1 to L7) whose abstracts claim codes absent
from the board, and asked first whether each publishes check matrices or a
complete generator (S1). Read from the full texts and TeX sources rather than
the abstracts, all seven do, with one twist: the two in-range canonical
lifted-product instances are printed in arXiv:2607.28605's own appendix, not
in the Cain et al. paper its main text cites for them. Rebuilding everything
that was rebuildable and screening it against the board with the four-axis
dominance rule of `verify/validate_candidate.py` leaves two filings and five
negatives.

| item | paper | verdict | instances rebuilt | outcome |
|---|---|---|---|---|
| L1 | Vine codes, 2606.20263 | (b), stim circuits on Zenodo | the four Figure 5 patches and the Figure 11 patch | negative: bilayer class, dominated even by single-layer entries |
| L2 | Routing codes, 2606.25330 | (b), routing rule plus Tables 3 and 4 | all 10 instances | [[200,16,17]] undominated and filed; [[200,24,14]] dominated by [[170,32,14]]; the weight-7 family dominated |
| L3 | Self-dual BB, 2510.05211 | (b), Tables 1 and 2 | all 71 rows | negative (also found independently by @MathysRennela): 11 on the board, the rest dominated, [[48,16,4]] decomposes |
| L4 | Canonical LP, 2607.28605 | (b), appendix matrices | the two in-range instances | [[468,36,20]] undominated and filed; [[952,112,17]] dominated by 18 entries |
| L5 | Trivariate bicycle, 2603.17703 | (b), Table 1 | [[128,20,8]] and the three already on the board | negative: dominated by eight weight-8 entries |
| L6 | Subsystem BB, 2605.04151 | (b) for [[75,10,5]], Appendix E for the rest | none | gauge codes; not a stabilizer entry, no track proposed |
| L7 | BB over group algebras, 2609.36213 | (b) | [[18,4,3]] over C3 | no board-absent parameters; the C3 code is not isomorphic to the board's [[18,4,3]] (nauty), but dominated |

The builders are under `research/campaigns/openalex-harvest-2863/`; each
runs from the repository root and writes its reconstructions to the
gitignored staging directory, from which the two filings were packaged.

## Method

Every claim was rebuilt from the paper's own definition and checked three
ways before any comparison: the two check matrices commute, k recomputed by
GF(2) rank equals the paper's k, and the paper's distance is reached as the
lightest logical found by `research/kit/surrogate.distance_rand_witness`
(fast backend, pair depth 32). A reconstruction that failed any of these would
have been reported as such; none did. Dominance was then tested the way the
gate does, with `b.n <= n`, `b.k >= k`, `b.d >= d`, `b.w <= w` and at least
one strict, over every CSS entry in `codes/`, and the gate itself
(`verify/validate_candidate.py`) was run on the two survivors.

## L2, routing codes

The paper defines the family by a routing rule rather than by matrices:
on the torus Z_l x Z_m, data qubits sit at i + j even, X syndromes at i odd
and j even, Z syndromes at i even and j odd; at step t every X syndrome at r
swaps with the data qubit at r + v_t and every Z syndrome with the data qubit
at r + w_t, and a syndrome's stabilizer is the set of data qubits it swapped
with over the T steps (`routing_codes.py`). The weight is T. w is the time
reversal of v except where Table 3 says the two are identical.

| paper | (l, m) | rebuilt | RIS trials | reading | dominators at w |
|---|---|---|---|---|---|
| [[200,24,14]] | (20, 20) | n 200, k 24, w 11 | 2,000,000 and 10,000,000 | 14 | 1: [[170,32,14]] |
| [[200,16,17]] | (40, 10) | n 200, k 16, w 11 | 2,000,000 and 10,000,000 | 17 | none |
| [[54,8,6]] | (18, 6) | k 8, w 7 | 500,000 | 6 | on the board at these parameters |
| [[70,8,7]] | (14, 10) | k 8, w 7 | 500,000 | 7 | [[62,10,7]], [[60,8,8]] |
| [[80,8,8]] | (16, 10) | k 8, w 7 | 500,000 | 8 | on the board at these parameters |
| [[90,8,9]] | (18, 10) | k 8, w 7 | 500,000 | 9 | [[90,8,11]], [[84,10,9]] and two more |
| [[100,8,10]] | (20, 10) | k 8, w 7 | 500,000 | 10 | [[90,8,11]], [[96,8,11]], [[90,8,10]] |
| [[110,8,11]] | (22, 10) | k 8, w 7 | 500,000 | 11 | on the board at these parameters |
| [[140,8,12]] | (28, 10) | k 8, w 7 | 500,000 | 12 | [[120,8,14]], [[120,8,12]], [[140,8,14]] |
| [[140,8,13]] | (28, 10) | k 8, w 7 | 500,000 | 13 | [[120,8,14]], [[140,8,14]] |

[[200,16,17]] is filed as a literature baseline with the issue referenced;
its note carries the ladder. The paper's claim that all non-local couplings
are mutually parallel is a connectivity property the board does not price,
so it appears in the note and nowhere in the ranking.

## L4, canonical lifted-product codes

LP_l(A, A*) with R = F2[x]/(x^l + 1), H_X = B(A (x) I, I (x) B) and
H_Z^T = B(I (x) B ; A (x) I), B = A* the transpose with x replaced by x^-1,
B(.) the circulant binarization (their Eq. 5; `lp_canonical.py`). The
appendix gives, in the example of canonical matrices,

- LP_36^(2x3): A = (A' | q_1), A' = [[1, 1 + x^11 + x^29], [1, 0]],
  q_1 = [1; x^8 + x^13 + x^16 + x^17], l = 36;
- LP_28^(3x5): A = (A' | q_1 | q_2), A' upper triangular with diagonal
  x^8 + x^11 + x^22, x^4, x^12 and off-diagonal x^18, x in the first row,
  (q_1 | q_2) = [[0, 0], [x^14 + x^19, x^18 + x^25], [x + x^10, x^3 + x^27]],
  l = 28.

Both rebuild to the stated n and k. [[468,36,20]] has check weight 10,
reads 20 at 500,000 and at 10,000,000 trials (the single-block annihilator
attack was not run: it is built for two-block GB codes and does not apply to
an LP block), and is dominated by nothing on the board; it is filed under
L4 by @MathysRennela from the staged document.
[[952,112,17]] has check weight 9, reads 17, and is dominated by 18 entries
([[872,222,18]], [[576,148,18]], [[888,226,18]], [[776,198,20]] among them).
The n > 1000 instances ([[1122,148,<=20]] and larger) are in Cain et al.,
arXiv:2603.28627, Appendix A, and are outside the board's range.

## L1, vine codes

The Zenodo record 10.5281/zenodo.20746752 ships memory circuits for the
Figure 5 and Figure 11 patches with QUBIT_COORDS on every qubit. The data
qubits are the ones prepared with RX at t = 0; pulling each round-1
measurement back through the round's CX, CXSWAP and SWAP steps gives a
stabilizer on the data (`vine_extract.py`). Every circuit yields a commuting
CSS code with the paper's logical count.

| patch | code | check weights | max check diameter | class |
|---|---|---|---|---|
| Fig. 5a | [[437,6,<=10]] | 2 to 7 | 6.32 | local-2d-bilayer |
| Fig. 5b | [[538,6,<=10]] | 3 to 7 | 6.32 | local-2d-bilayer |
| Fig. 5c | [[557,6,<=10]] | 2 to 7 | 6.32 | local-2d-bilayer |
| Fig. 5d | [[435,6,<=10]] | 2 to 7 | 6.32 | local-2d-bilayer |
| Fig. 11 | [[83,4,<=5]] | 2 to 7 | 5.66 | small |

Distances are 2,000,000-trial readings. The routing qubits let a measure
qubit collect data it is not adjacent to, so the check diameters reach 6.32
grid units and the verifier classes the codes bilayer, not single-layer; and
in the bilayer cell every one is dominated, including by single-layer entries
([[373,8,15]], [[240,8,11]], [[410,8,16]]). The abstract's [[121,4,6]],
[[221,6,7]] and [[234,9,6]] are the sequences nENENEs, nSeWwSs and nSeWWwSs
(weights 7, 7 and 8), smaller than the Figure 5 patches, and do not change
the picture.

## L3, L5, L6, L7

L3: all 71 weight-8 self-dual BB codes of Tables 1 and 2 rebuild from
H_X = H_Z = [circ(f) | circ(fbar)] on the twisted torus
Z^2 / <(0, alpha), (beta, gamma)>, with the RIS reading equal to the stated
exact distance on every row. Eleven are on the board at their parameters, the
rest are dominated at check weight <= 8, and the one undominated row,
[[48,16,4]], is a direct sum of two [[24,8,4]] codes (f = 1 + x + y^2 + x^-2
moves y only by even steps), which the connectivity check refuses.
@MathysRennela reached the same result independently in the issue thread.

L5: Table 1 gives torus and polynomials for every instance; [[128,20,8]]
(4 x 4 x 4, A = 1 + x + y + z, B = 1 + x^3 + y^3 + z^3) rebuilds to k = 20 and
reads 8, and is dominated at check weight <= 8 by eight entries
(`itb_codes.py`). [[140,6,14]], [[54,14,5]] and [[84,6,10]] are on the board.

L6: the subsystem BB codes are gauge codes with a non-trivial gauge group;
the stabilizer group alone does not have the stated parameters, so there is
nothing to enter as a stabilizer code, and one paper's three instances do
not justify a gauge track.

L7: the weighted-shift BBGA construction is fully specified. The C3 instance
[[18,4,3]] (a = (e, e, c), b = (c), c = r + r^2, A = P^2 + Q,
B = P^2 + PQ + P^2 Q) rebuilds to k = 4 and is not isomorphic to the board's
[[18,4,3]] under the typed-Tanner-graph canonical form, but it is dominated
at the same parameters by twelve literature codes, so it is recorded here and
not filed. [[144,12,12]], [[144,14,14]] and [[144,16,12]] are on the board.

## What this changes about the triage

Mathys's correction in the thread stands: an abstract's "zero dominators"
count means little until the weight is known and the test is the gate's own.
Of seven papers with board-absent abstracts, two produced entries. The cost
of the whole pass was under a day, most of it reading, and the builders make
each family a few-minute check the next time a paper in it appears.
