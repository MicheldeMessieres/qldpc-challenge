---
title: "CSS census through n = 8: 1,916 classes at n = 7 and 9,038 at n = 8, with one and two distance-three codes"
date: 2026-10-03
author: "@vprusso"
model: Claude Fable 5.1
topics: [css-codes, exhaustive-enumeration, exact-distance, small-blocklength, canonical-form]
related:
  - fieldnotes/2026-09-24-small-css-census.md
---

## TL;DR

The exhaustive CSS census (issue #2040) now runs past n = 6. The factorial
permutation canonicalizer is replaced by nauty's canonical form of a codeword
graph, which reproduces the recorded n <= 6 counts (1, 3, 11, 37, 126, 473)
and completes n = 7 in 3.5 s and n = 8 in 43 s on one core, under 50 MB,
with every class's distance certified exactly and zero unresolved cases.
Under the census equivalence (check-row basis, qubit permutation, global X/Z
exchange) there are 1,916 CSS code classes with k >= 1 at n = 7 and 9,038 at
n = 8. Exactly one class at n = 7 has distance 3, the [[7,1,3]] code, and
exactly two at n = 8, both [[8,1,3]]. No class at n <= 8 has k >= 2 and
d >= 3, and none has d >= 4.

## What changed in the enumerator

`research/kit/census_css.py` keeps the equivalence relation of the n <= 6
census unchanged and replaces how it is computed.

A row space U is represented by the bipartite graph of its nonzero codewords
against the n qubits, with an edge from a codeword to each qubit in its
support. A pair (U, V) is the three-colored graph with the qubits, the
codewords of U, and the codewords of V as the three color classes. A qubit
permutation acts on this graph as a color-preserving isomorphism, and every
color-preserving isomorphism is induced by one, because the qubit class is
mapped to itself and the codeword classes are determined by the qubit image.
nauty's certificate of the colored graph, together with the two codeword
class sizes, is therefore a complete invariant of the pair under qubit
permutation; the smaller of that key and the key with the U and V colors
exchanged is invariant under the global X/Z swap as well. The codeword set is
basis independent, so no RREF canonicalization is needed before hashing.

The sweep visits each U orbit once: all subspaces of GF(2)^n of dimension at
most n - 1 are keyed and reduced to one representative per key, then every
subspace V of each representative's orthogonal complement is keyed as a pair.
Every pair (U, V) is equivalent to (rep(U), pi(V)) for the permutation pi
carrying U onto its representative, and pi(V) lies in rep(U)'s complement,
so the sweep is complete without visiting the orbit of U. At n = 8 this keys
417,198 subspaces for the representative stage, which leaves 341
representatives, and then 778,262 pairs, against the 89 million labeled
pairs the issue counted for a direct sweep.

The old canonicalizer is kept as `--canonicalizer permutation` (n <= 6) and
is the independent cross-check: `research/test_census_css.py` asserts that
both produce the same class keys for every n <= 5, that the nauty key is
unchanged by random and, for one asymmetric pair, by all 120 permutations and
by the X/Z swap at n = 5, that distinct classes get distinct keys, and that
the n = 7 census has 1,916 classes containing the [[7,1,3]] code with k = 1.
`pynauty` is added to the `research` extra; without it the tool falls back
to the permutation canonicalizer and its n <= 6 cap.

## Stages

Each n was run as its own stage with `--d-min 1`, so every class is
certified, not only the matches. One core of an Apple M-series laptop,
`/usr/bin/time -l` for wall-clock and peak resident set.

| stage | classes (k >= 1) | d = 1 | d = 2 | d >= 3 | exact certifications | unresolved | wall-clock | peak RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| n = 1..6 | 651 | 603 | 48 | 0 | 651 | 0 | 0.7 s | 42 MB |
| n = 7 | 1,916 | 1,750 | 165 | 1 | 1,916 | 0 | 3.5 s | 42 MB |
| n = 8 | 9,038 | 8,140 | 896 | 2 | 9,038 | 0 | 43 s | 46 MB |

Classes by k:

| n | k = 1 | k = 2 | k = 3 | k = 4 | k = 5 | k = 6 | k = 7 | k = 8 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | 384 | 682 | 564 | 223 | 55 | 7 | 1 | |
| 8 | 1,161 | 2,855 | 2,964 | 1,553 | 418 | 78 | 8 | 1 |

The n <= 6 stage reproduces the counts of the 2026-09-24 census exactly,
per n and per k.

## The distance-three classes

At n = 7 the single class with d = 3 is the [[7,1,3]] code: X and Z checks
both the Hamming matrix, supports {0,4,5,6}, {1,3,5,6}, {2,3,4,6} in the
census's qubit labeling. Under the census equivalence it is the only CSS code
on seven qubits with k >= 1 and d >= 3.

At n = 8 the two classes with d = 3 are both [[8,1,3]]:

- X checks {0,5,6,7}, {1,4,6,7}, {2,4,5,7}; Z checks the same three plus
  {3}. This is the [[7,1,3]] code with an eighth qubit fixed by a weight-one
  Z check. Its stabilizer group splits across the qubit sets {3} and the
  other seven, so the board's verifier would reject it as a product; the
  census counts it because the equivalence relation does not exclude
  products.
- X checks {0,5,6,7}, {1,4,6,7}, {2,3,4,5,7}; Z checks {0,5,6,7},
  {1,4,6,7}, {2,4,5,7}, {3,4,5,7}. Connected, with one weight-five X check.

No class at n <= 8 has k >= 2 with d >= 3, and none has d >= 4. The 896
distance-two classes at n = 8 include every k from 1 to 6.

## Go/no-go for n = 9

The representative stage keys every subspace of dimension at most n - 1,
and that count grows about twenty-fold per step: 29,211 at n = 7, 417,198
at n = 8, 8,283,457 at n = 9, 229,755,604 at n = 10. Measured on the same
machine, enumeration alone (no certification) took 1.9 s at n = 7 and 37 s
at n = 8.

The n = 9 enumeration was then run as a measurement, without certification,
in a harness around the same canonicalizer: 50,566 classes with k >= 1 (by
k: 3,916, 12,684, 17,785, 11,482, 3,849, 737, 103, 9, 1), 1,104 s of
wall-clock, 1.3 GB peak resident set. Certification at n = 8 cost about
6 s for 9,038 classes beyond the 37 s of enumeration, so the n = 9 stage
should certify in well under a minute on top of its enumeration. Decision:
n = 9 is a go as its own stage, with a budget of 30 minutes and 2 GB, and
`MAX_N` moves to 9 in the PR that records that stage. n = 10 is a no-go on
the present sweep: the representative stage would key 229,755,604
subspaces, about 28 times the n = 9 count, which extrapolates to roughly
nine hours and a memory footprint that was not measured. Reaching n = 10
needs the representative stage replaced by canonical augmentation over U,
which generates one representative per orbit directly instead of keying
every subspace, and that is a separate change.

## Reproduction

```bash
uv run --extra research python research/kit/census_css.py \
    --n-min 1 --n-max 6 --d-min 1 --canonicalizer nauty --output census-n1-6.jsonl
uv run --extra research python research/kit/census_css.py \
    --n-min 7 --n-max 7 --d-min 1 --canonicalizer nauty --output census-n7.jsonl
uv run --extra research python research/kit/census_css.py \
    --n-min 8 --n-max 8 --d-min 1 --canonicalizer nauty --output census-n8.jsonl
```

Each JSONL file carries a header record naming the equivalence and the
canonicalizer, one record per class with its checks, both distance witnesses
and the SAT certification, and a summary record whose `complete` flag is the
zero-unresolved condition. The cross-check against the permutation
canonicalizer is `--canonicalizer permutation` for any n <= 6.

## Limits

The equivalence is the one the n <= 6 census used: check-row basis, qubit
permutation, and global X/Z exchange, not local Cliffords. A local Clifford
can carry a CSS code to a non-CSS stabilizer code, so a census of CSS codes
up to local Clifford equivalence is a different object, and the counts here
should not be compared with the stabilizer board's local-Clifford dedup
(#2361). How many of these classes merge under local Cliffords is a question
for a separate stage. Product codes are counted, as the first [[8,1,3]]
class shows.
