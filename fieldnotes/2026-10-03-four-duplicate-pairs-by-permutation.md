---
title: Four board pairs are one code each, by explicit qubit permutation
date: 2026-10-03
author: "@vprusso"
model: human
topics: [dedup, permutation-equivalence, weisfeiler-leman, board-hygiene]
---

Henryk Sobon (issue #2643) exhibited, for each of four pairs the gate had
flagged as WL-equivalent and nobody had resolved, an explicit permutation of
the physical qubits carrying the first entry's X and Z row spaces onto the
second's. The permutations are in `research/audits/permutation_equivalences.json`
and `research/audits/permutation_equivalence.py` re-checks them from the blob
hashes cited there (rank of A, rank of B, rank of the stacked matrix after
the permutation; equality of the three on both sides is row-space equality):

| pair | X | Z | n |
|---|---|---|---|
| `17-1-5` and `17-1-5-b` | 8 / 8 / 8 | 8 / 8 / 8 | 17 |
| `144-12-12` and `144-12-12-b` | 66 / 66 / 66 | 66 / 66 / 66 | 144 |
| `190-20-8` and `190-20-8-b` | 85 / 85 / 85 | 85 / 85 / 85 | 190 |
| `682-182-66` and `682-182-66-b` | 250 / 250 / 250 | 250 / 250 / 250 | 682 |

Each permutation composed with one extra transposition fails the check, so
the checker is not trivially satisfied. The record for `144-12-12` cites blob
`a6332af5`, which PR #2669 superseded by adding a `locality` block; the
`checks` are byte-identical between the two revisions and the current blob
`09588dde` passes the same check.

## What each second file was

None of the four was filed by mistake. Each was a second presentation of a
code already on the board, admitted with the collision noted, because it
carried something the incumbent did not at the time:

- `17-1-5-b` (@mathysrennela): a single-layer 4.8.8 layout at interaction
  radius 3.606, earning `local-2d-single`, which the incumbent's layout
  (radius 4.2, `local-2d-bilayer`) does not reach. Same author on both.
- `144-12-12-b` (@fullymiddleaged): the first bilayer layout of the gross
  code, filed 30 September. The baseline `144-12-12` has since received a
  bilayer layout of its own (PR #2669, `locality.contributed_by`
  @dorakingx), with comparable diameters.
- `190-20-8-b` (@MathysRennela): the same `[[4,2,2]]` amplification of
  `40-10-4` as @FarLab's `190-20-8`, filed under `-b` because replacing
  another author's entry is reserved to them. No layout on either.
- `682-182-66-b` (@natestemen): the tightened `682-182-75` of issue #1651,
  the same cyclic two-block code as @JiahaoYao's `682-182-66`; both sides
  carry witnesses at 66.

## What is done about it

Under "One code, one entry" (`CONTRIBUTING.md`), the entry that earns more
stays and the other is removed, with credit recorded here:

- `17-1-5`: the incumbent is removed and `17-1-5-b` stays, because its layout
  earns the stricter class and single-layer membership nests into the
  bilayer and unrestricted cells, so nothing is lost. The incumbent's
  construction route (the doubling construction of arXiv:2608.11160) is
  recorded in `17-1-5-b`'s note already.
- `144-12-12-b`, `190-20-8-b`, `682-182-66-b`: removed; the incumbents stay.
  The bilayer layout of the gross code was first contributed by
  @fullymiddleaged; the independent tightening of `[[682,182]]` to 66 by
  @natestemen stands in the history of `682-182-66-b`.

The gate still cannot decide equivalence on arrival for codes outside the
cyclic two-block family (`verify/two_block_equivalence.py` covers that
family; everything else is a WL flag). A permutation-invariant quantity that
would have separated two other flagged clusters outright, the dimension of
the intersection of the X and Z row spaces, is not computed by the verifier
yet; its finder has been invited to contribute it.
