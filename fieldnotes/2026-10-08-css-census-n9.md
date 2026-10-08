---
title: "CSS census through n = 9: 50,566 classes, 24 distance-three codes all with k = 1"
date: 2026-10-08
author: "@MathysRennela"
model: "MiMo-V2.6-Flash (OpenCode)"
topics: [css-codes, exhaustive-enumeration, exact-distance, small-blocklength, canonical-form]
related:
  - fieldnotes/2026-09-24-small-css-census.md
  - fieldnotes/2026-10-03-css-census-n7-n8-nauty.md
---

## TL;DR

Issue #2040's n = 9 stage is complete. Under the census equivalence (check-row
basis, qubit permutation, global X/Z exchange) there are **50,566 CSS code
classes with `k >= 1` at `n = 9`**. Every class's minimum distance is certified
exactly by the trusted SAT certifier, the summary's `unresolved` count is **0**,
and the run's `complete` flag is true. Wall-clock was 45 minutes 34 seconds and
peak resident set 69 MB on one core.

The substantive result: **24 classes at `n = 9` have `d = 3`, and all 24 have
`k = 1`.** No class has `k >= 2` with `d >= 3`, and no class reaches `d >= 4`.
This extends the `n <= 8` finding — the only CSS codes at these blocklengths
that reach distance three are `[[n,1,3]]` — past `n = 9`.

The note also corrects two numbers in the 2026-10-03 record: the n = 9 peak
memory was measured at 69 MB, not the 1.3 GB previously reported, and
certification cost nothing rather than being an extrapolable overhead. Both
change what n = 10 should be judged against, and the corrected go/no-go is
recorded below.

## The n = 9 stage

Each blocklength is its own stage with `--d-min 1`, so every class is
certified rather than only some. One core of a x86-64 Linux machine,
`/usr/bin/time -v` for wall-clock and peak resident set.

| stage | classes (k >= 1) | d = 1 | d = 2 | d = 3 | d >= 4 | exact certifications | unresolved | wall-clock | peak RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| n = 1..6 | 651 | 603 | 48 | 0 | 0 | 651 | 0 | 0.7 s | 42 MB |
| n = 7 | 1,916 | 1,750 | 165 | 1 | 0 | 1,916 | 0 | 3.5 s | 42 MB |
| n = 8 | 9,038 | 8,140 | 896 | 2 | 0 | 9,038 | 0 | 43 s | 46 MB |
| n = 9 | 50,566 | 45,168 | 5,374 | 24 | 0 | 50,566 | 0 | 45 m 34 s | 69 MB |

Classes by k:

| n | k = 1 | k = 2 | k = 3 | k = 4 | k = 5 | k = 6 | k = 7 | k = 8 | k = 9 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | 384 | 682 | 564 | 223 | 55 | 7 | 1 | | |
| 8 | 1,161 | 2,855 | 2,964 | 1,553 | 418 | 78 | 8 | 1 | |
| 9 | 3,916 | 12,684 | 17,785 | 11,482 | 3,849 | 737 | 103 | 9 | 1 |

The n = 9 per-k counts are identical to the enumeration-only measurement that
the 2026-10-03 note recorded in passing (3,916 / 12,684 / 17,785 / 11,482 /
3,849 / 737 / 103 / 9 / 1), digit for digit. That earlier figure was read from
a harness without certification; this run certifies all 50,566 of them, so the
class set is now evidenced rather than merely measured.

## The distance-three classes

Twenty-four classes at n = 9 have `d = 3`, and every one of them has `k = 1`.
Under the census equivalence the result at these blocklengths is now:

| n | classes with d >= 3 | all with k = | max k among them | max d |
|---:|---:|---:|---:|---:|
| 7 | 1 | 1 | 1 | 3 |
| 8 | 2 | 1 | 1 | 3 |
| 9 | 24 | 1 | 1 | 3 |

**No class at n = 9 has `k >= 2` with `d >= 3`, and no class at n <= 9 reaches
`d >= 4`.** Combined with the n = 8 check below, the claim now stands through
nine qubits: the only CSS codes under this equivalence that reach distance three
are `[[n,1,3]]`, and there is no CSS code with two logical qubits and distance
three on at most nine qubits.

The 5,374 distance-two classes at n = 9 spread across k = 1 through k = 7, so
the distance-two band is where the `k >= 2` codes sit. The 45,168 distance-one
classes are the majority and are dominated by codes admitting a weight-one
logical.

## Corrections to the 2026-10-03 record

Two numbers in the earlier note do not survive the measurement, and both matter
for the n = 10 decision.

**Peak memory was overstated by roughly 19x.** The n = 9 stage peaked at
**69 MB**, not the 1.3 GB previously reported. The reason is structural: the
representative stage fills a dict via `setdefault(key, x_rows)`, so it retains
**one entry per orbit representative, not one per keyed subspace**. At n = 8
that is 341 retained entries from 417,198 keyed subspaces; at n = 9 the
retained count is likewise in the hundreds while 8,283,457 subspaces are keyed.
Counting the keyed subspaces therefore tells you nothing about memory. The 1.3 GB
figure appears to have come from an instrumented harness that retained class
records, which the census tool does not.

**Certification is free at this scale, so extrapolating it was a mistake.** The
earlier note predicted certification would cost "well under a minute on top of
its enumeration" by scaling the n = 8 ratio. In practice every one of the 50,566
solves reported 0.00 s: distance one is trivial to prove and distance two
returns a witness immediately. Certification was never the constraint;
enumeration is, and it is 99% of the wall-clock.

**Machine-speed ratio.** This run took 2,728 s where the 2026-10-03 machine took
1,104 s for the same enumeration: **2.47x**; n = 8 shows the same factor (109 s
against 43 s: 2.53x), so the gap is one consistent machine difference.

## Go/no-go for n = 10

The n = 9 stage supersedes the earlier judgement, which rested partly on a
memory number now known to be wrong. The cost driver is unchanged: the
representative stage keys every subspace of dimension at most `n - 1` —
29,211 / 417,198 / 8,283,457 / 229,755,604 at n = 7 / 8 / 9 / 10, about 28x per
step. Those counts were right; only their interpretation as memory was wrong.

**Wall-clock is the binding constraint.** n = 10 would key 27.7x the n = 9
subspaces, and n = 9 is now a *measured* 2,728 s rather than an estimate, so n
= 10 extrapolates to **about 21 hours on this machine** (about 8.5 hours on the
faster one, which matches the ~9 hours previously quoted). That is far outside
any sane stage budget and it is a wall-clock problem, not a memory one.

**Memory is not a constraint.** At 69 MB for n = 9, n = 10 would plausibly need
a few hundred MB — the retained representative and seen-key sets grow with the
class count (~5.6x per step), not with the keyed-subspace count. Memory should
not appear in any future n = 10 no-go argument.

Decision: **n = 10 is a no-go on the present sweep, on wall-clock alone.**
Reaching it needs the representative stage replaced by canonical augmentation
over U, which generates one representative per orbit directly instead of keying
every subspace, and that is a separate change.

## Independent verification

The counts were checked against three calculations that share no code with the
census and no SAT solver, each described precisely enough to rewrite; none of
their outputs is committed.

**Distances, brute force rather than SAT.** For every one of the 50,566 n = 9
classes, the exact CSS distance was recomputed by enumerating all 512 vectors
of GF(2)^9: the X-type logicals are `ker(H_Z)` modulo the row space of `H_X`,
the Z-type are `ker(H_X)` modulo the row space of `H_Z`, and the distance is
the least weight of either. **Zero mismatches** against the SAT-certified
values. The same test over n = 6, 7, 8 checked 11,427 classes with **zero
mismatches**, so the exactness claim is corroborated across all 62,000-odd
certified classes without trusting the certifier.

**Completeness at n = 6, with the orbit optimization removed.** The census's one
non-obvious step is reducing U to a single orbit representative and sweeping V
inside that representative's orthogonal complement, which never visits the orbit
of U. Dropping that optimization and sweeping all 92,881 orthogonal pairs of
GF(2)^6 with `k >= 1`, keyed with the same nauty pair key, yields **exactly 473
distinct keys — zero missing from the census, zero extra, zero disagreements on
k**. The reduction is sound; this is the blocklength at which an independent
full sweep is affordable.

**The k = 3 slice at n = 8, with no canonical form at all.** The absence of a
`[[8,3,3]]` CSS code is not obvious from outside — that code is a well-known
stabilizer code — so all 36,335,970 orthogonal pairs of GF(2)^8 with
`rank(U) + rank(V) = 5` were enumerated and tested directly for exact CSS
distance three. **Zero pairs qualify**, confirming that `[[8,3,3]]` is not a CSS
code under this equivalence and that the census did not miss it.

## Reproduction

```bash
uv run --extra research python research/kit/census_css.py \
    --n-min 9 --n-max 9 --d-min 1 --canonicalizer nauty --output census-n9.jsonl
```

The budget was declared before launching: **180 minutes and 6 GB**, raised from
the 30 minutes / 2 GB the earlier note assumed for its faster machine — 74
minutes at the measured 2.47x ratio, and 6 GB sized on the 1.3 GB claim this
stage disproves. The run used 45 m 34 s and 69 MB, inside budget by 3.95x and
88x respectively. `MAX_N` moves to 9 with this stage, and the `census_css.py`
docstring records the n = 9 measurements alongside n = 7 and n = 8.

Each JSONL file carries a header record naming the equivalence and canonicalizer,
one record per class with its checks, both distance witnesses and SAT
certification, and a summary whose `complete` flag is the zero-unresolved
condition. The independent cross-check against the original canonicalizer
remains `--canonicalizer permutation` for any `n <= 6`.

## Limits

The equivalence is unchanged from the n <= 6 census: check-row basis, qubit
permutation, and global X/Z exchange — **not** local Cliffords. A local Clifford
can carry a CSS code to a non-CSS stabilizer code, so a CSS census up to local
Clifford equivalence counts a different object, and these numbers must not be
compared with the stabilizer board's local-Clifford dedup (#2361). How many of
the 50,566 classes merge under local Cliffords remains a question for a
separate stage.

Product codes are counted, as the first `[[8,1,3]]` class at n = 8 shows; the
census's relation does not exclude them, so a class here need not survive the
board's own verifier.

The negative result through n = 9 is a statement about this equivalence and
these blocklengths only. It is not a bound against `[[10,2,3]]` or larger, and
nothing here rules those out.
