---
title: BB codes over group algebras (arXiv:2609.36213) add no parameters; the paper's support invariant is a usable same-numbers-different-code test
date: 2026-10-08
author: "@FarLab"
model: Claude Fable 5.1
topics: [generalized-bicycle, bbga, literature, equivalence, invariants, issue-2863]
---

Item L7 of issue #2863. Chaobin Liu, *Bivariate Bicycle Codes over Group
Algebras*, arXiv:2609.36213 (2026-09-28), gives a weighted-shift
formulation of bicycle codes over `F_2[G]` and a permutation-inequivalence
certificate. The issue's "done when" was a generator or a written finding;
this note records both, and that neither produces a new board entry. The
S1 reading pass in `fieldnotes/2026-10-07-openalex-harvest-reconstructions.md`
already rebuilt the C3 instance and recorded the verdict that the paper
publishes a complete construction; this note takes the other four instances,
the digest pin, the invariant as a tool, and the sweep.

## What the paper claims against what the board holds

| paper instance | seed group | claim | on the board as |
|---|---|---|---|
| Eq. (11) | D3, p = 3, q = 4 | `[[144,12,12]]` | `codes/144-12-12.json` (gross code; this is it under relabeling) |
| Eqs. (12)-(13) | D3 | `[[144,14,14]]` | `codes/144-14-14.json` |
| Eq. (14) | D3 | `[[144,16,<=12]]` | `codes/144-16-12.json` (abelian BB, same parameters) |
| Eqs. (15)-(16) | A4 x C6, p = q = 1 | `[[144,16,12]]`, d exhaustively certified | tie with `codes/144-16-12.json` |
| Eqs. (18)-(20) | C3, weighted seeds | `[[18,4,3]]` | `codes/18-4-3.json`; dominated by `codes/18-4-4.json` |

All five rebuild with `research/kit/group_algebra.build_bbga` to the stated
n and k, with surrogate witnesses at the claimed weights (d <= 12, 14, 12,
12, 3). The A4 x C6 matrices match the paper's own SHA-256 digests
(Appendix A, row-major uint8) bit for bit, which pins the conventions:
even permutations in lexicographic order, `h t^u` at index `6j + u`,
composition applies the right factor first, `rho` (right multiplication)
on the left block. `research/test_bbga.py` keeps that pin. The three D3
instances have single-element seeds with `<P, Q>` transitive of order 72,
so by the paper's own Prop. 3.1 they are abelian BB codes on `Z_6 x Z_12`
in disguise, which is why the gross code falls out of Eq. (11).

The A4 x C6 code passed `verify/validate_candidate.py` (8000-trial
refutation, no lighter logical) and the gate labelled it board-advancing.
It is not: it ties `codes/144-16-12.json` on every ranked axis (n, k, d,
w = 8), and the gate's dominance test only counts an entry as a dominator
when it is strictly better somewhere, so an exact tie reads as
"undominated". Worth knowing before trusting that label on a reconstruction.

One provenance consequence: `codes/144-16-12.json` carries
`novelty: new_parameters` (submitted 2026-09-09). The parameter set is now
in the literature twice, as the paper's Eq. (14) abelian instance and as
the A4 x C6 code. `CONTRIBUTING.md` says anyone may record that as
`known_parameters` with the reference; left to the entry's author or a
maintainer rather than filed here.

## The inequivalence invariant, reproduced and packaged

The paper's Theorem 4.3: the A4 x C6 code is not permutation-equivalent,
even with single-qubit Cliffords, to any abelian BB or 2BGA code of length
144. The argument needs no group theory on the candidate side. Enumerate
every stabilizer of minimum weight exactly, build the qubit/support
incidence graph `Gamma`, and count its automorphisms. An abelian 2BGA code
carries a free translation group of order n/2 preserving its stabilizers,
so n/2 must divide `|Aut(Gamma)|` and the qubit orbits must be at most two
blocks of n/2. `research/kit/supports.py` does this (meet-in-the-middle
kernel enumeration up to the lightest check weight, exact; then pynauty if
importable, networkx VF2++ otherwise):

| code | min stabilizer weight | min supports | `Aut(Gamma)` | qubit orbits | abelian 2BGA possible |
|---|---|---|---|---|---|
| A4 x C6 `[[144,16,12]]` | 8 (exactly the 144 rows) | 144 | 12 | 12 x 12 | no (72 does not divide 12) |
| `codes/144-16-12.json` | 8 (exactly the rows) | 144 | 144 | 1 x 144 | not ruled out |
| `codes/144-12-12.json` | 6 (exactly the rows) | 144 | 288 | 1 x 144 | not ruled out |
| C3 weighted `[[18,4,3]]` | 6 | 38 | 96 | 6 + 12 | no (38 not divisible by 3; paper Thm 5.2) |

The paper's numbers (|Aut| = 12, 38 supports) are reproduced; the two
abelian controls come out divisible by 72 with a single orbit, as they
must. Costs: n = 144 at weight 8 is 17.7 M half-supports and 18 s per
side; n = 300 at weight 8 would be 330 M and is out of a laptop's reach,
so this is a tool for n up to about 200 at weight 8, or any n at weight 6.
The networkx fallback took 38 minutes on the 18-qubit code (small, highly
symmetric graph) and 33 s on the 144-qubit ones; pynauty is instant on
both, so run it with `uv run --with pynauty`. A by-product is exact: no
logical of weight <= 8 exists for either `[[144,16,12]]`, which is a true
`d > 8` for both, independent of any sampling.

This is a different notion of "same code wearing a different hat" from
`provenance.clifford_relabel_of` (issue #2802), which is about block
Cliffords; this one is about qubit permutations and, by the paper's
argument, survives single-qubit Cliffords too. It only ever rules a
realization out; a code that passes has not been shown to be abelian.

## The generator as a search tool, and a bounded negative

`research/kit/search.sample_bbga` samples the construction with at least
one multi-element seed per candidate, the axis the paper opens (all-single
seeds with a transitive shift group collapse to abelian BB, which
`sample_bb` covers). Two 15-minute runs at 300 screening trials, seeds 0
and 1, n <= 320, check weight <= 8, groups of order <= 24 (cyclic 2-12,
dihedral 3-6, A4, S4, two metacyclics), p, q <= 4:

| | seed 0 | seed 1 |
|---|---|---|
| sampled | 94,160 | 93,641 |
| rejected on weight > 8 | 67,161 | 66,632 |
| rejected as direct sums | 10,311 | 10,381 |
| distinct codes screened | 2,159 | 2,100 |
| best `kd^2/n` seen | 6.67 (`[[120,8,10]]`, C5) | 8.17 (`[[192,8,14]]`, S4) |

Every code the sweep found undominated against `codes/` at screening
depth was an exact (n, k, d, w) tie with an existing entry: `[[30,6,5]]`
w8, `[[16,4,4]]` w6, `[[24,6,4]]` w6, `[[14,6,3]]` w7, `[[40,6,5]]` w6.
Three were re-witnessed at 8000 trials and gated; the distances held and
the ties stayed ties. Nothing in this region beats the board.

Two reasons, both structural. A seed that is a sum of s elements
multiplies the weight of every monomial it enters, so at weight <= 8 the
only candidates that survive are those with one or two 2-element seeds
and two or three monomials, a thin slice. And shifts with p or q > 1 whose
seeds do not generate a transitive action split the code into components
(11% of samples), which the connectivity check rejects. The paper's own
best, the A4 x C6 code, uses single-element seeds at p = q = 1 and is a
plain nonabelian 2BGA, which `group_algebra.build_2bga` already covered
before this note.

Where the construction might still pay: weight 10-12 cells (unrestricted,
any weight), where 2-element seeds are affordable, and larger nonabelian
seed groups at p = q = 1 with the support invariant used to confirm a
find is not an abelian BB in disguise. Neither was run here.
