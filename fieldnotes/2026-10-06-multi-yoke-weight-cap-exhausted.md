---
title: "The multi-yoked chain codes cannot be filed further under the w=32 cap: 21 two-yoke matrices have provably no light basis, 12 three-yoke reach only w=40..196"
date: 2026-10-06
author: "@MathysRennela"
model: "MiMo-V2.6-Flash"
topics: [multi-yoked-surface, row-space, light-basis, weight-cap, negative-result]
status: active
---

## TL;DR

Ten matrices from *Multi-Yoked Surface Codes* (Hirai and Suzuki,
arXiv:2610.04613), taken from the pinned checkout
`github.com/yugahirai/multi_yoked_surface_codes @ b3e8b3e`, are on the board
as `ecc/chain_codes/`. That checkout ships 43 check matrices — 29 two-yoke
and 14 three-yoke. Eight two-yoke already sat at max check weight 8..32 and
were filed as published; two three-yoke sat at 36 and 60 and were filed
after row-space reduction to 32. For the remaining 33 the only lever left
is which basis of the row space to present: `M H` for invertible `M` over
GF(2) leaves the row space unchanged, and `k` and `d` depend only on that
row space, so the choice of check generators is the only free parameter.
The board's `MAX_CHECK_WEIGHT = 32` in `verify/qldpc_verify.py` is what
the lever has to reach. This note closes it.

**21 two-yoke matrices have no basis of weight-32 rows at all** — decided by
exact enumeration of every row-space element, not by search. **12 three-yoke
matrices were searched with 16 independent seeds each (192 runs) and none
reached 32**; the best achieved max check weight per file runs from 40 to
196, against a cap of 32. The family therefore contributes exactly the nine
submissions already on the board and nothing more.

## The criterion

Let `r = rank(H)` and `T = 32`. A basis of `r` rows, each of weight `<= T`,
exists **if and only if** the row-space elements of weight `<= T` span rank
`r`. The forward direction is immediate: every basis vector is a row-space
element. Conversely, a spanning set of light elements contains `r`
independent ones, and any independent subset of a row space is itself a
basis. So the question is a rank computation over a filtered subset of the
row space, and when `2^r` is enumerable it is not a search at all.

For `r <= 2^23` the test enumerates all `2^r` elements exactly. Above that
it falls back to biased sampling plus a local search (replace the heaviest
row by itself `xor` another), which is one-sided: a hit proves a light basis
exists, a miss proves nothing. Every two-yoke claim below is exact.

## The 21 two-yoke negatives

`r = rank(H_X) = rank(H_Z)` runs from 9 to 23, so all 21 were enumerated.
The "elements" column is how many row-space elements of weight `<= 32`
exist on the X side; none of the 13,822 found across the family spans.

| matrix | n | k | d | w0 | r | elements (X / 2^r) |
|---|---|---|---|---|---|---|
| q160_114_4 | 160 | 114 | 4 | 80 | 23 | 6196 / 8388608 |
| q256_216_4 | 256 | 216 | 4 | 128 | 20 | 138 / 1048576 |
| q128_90_4 | 128 | 90 | 4 | 64 | 19 | 2517 / 524288 |
| q112_78_4 | 112 | 78 | 4 | 56 | 17 | 1471 / 131072 |
| q104_72_4 | 104 | 72 | 4 | 52 | 16 | 1093 / 65536 |
| q144_112_4 | 144 | 112 | 4 | 72 | 16 | 79 / 65536 |
| q192_160_4 | 192 | 160 | 4 | 96 | 16 | 79 / 65536 |
| q240_210_4 | 240 | 210 | 4 | 120 | 15 | 11 / 32768 |
| q96_66_4 | 96 | 66 | 4 | 48 | 15 | 794 / 32768 |
| q120_92_4 | 120 | 92 | 4 | 60 | 14 | 56 / 16384 |
| q88_60_4 | 88 | 60 | 4 | 44 | 14 | 562 / 16384 |
| q192_166_4 | 192 | 166 | 4 | 96 | 13 | 9 / 8192 |
| q80_54_4 | 80 | 54 | 4 | 40 | 13 | 386 / 8192 |
| q128_104_4 | 128 | 104 | 4 | 64 | 12 | 37 / 4096 |
| q72_48_4 | 72 | 48 | 4 | 36 | 12 | 256 / 4096 |
| q120_98_4 | 120 | 98 | 4 | 60 | 11 | 7 / 2048 |
| q144_122_4 | 144 | 122 | 4 | 72 | 11 | 7 / 2048 |
| q72_52_4 | 72 | 52 | 4 | 36 | 10 | 88 / 1024 |
| q96_76_4 | 96 | 76 | 4 | 48 | 10 | 22 / 1024 |
| q88_70_4 | 88 | 70 | 4 | 48 | 9 | 8 / 512 |
| q96_78_4 | 96 | 78 | 4 | 48 | 9 | 6 / 512 |

In every row the span rank falls short of `r`, so no invertible `M` can
bring that code under the cap. `q72_52_4`, for instance, has 88 light
elements of 1024 spanning rank 8 of 10 — the lightest rows available
cannot be made independent.

## The 12 three-yoke negatives

`r = rank(H_X) = rank(H_Z)` runs from 40 to 70 across these twelve, so
enumeration is out of reach at `2^40` minimum and every claim here comes
from search rather than proof. Each file was run with 16 seeds; the table
gives the best (max check weight over X and Z) of those 16. `w0` is the
published weight.

| matrix | n | k | d | r | w0 | best of 16 | cap |
|---|---|---|---|---|---|---|---|
| q144_64_8 | 144 | 64 | 8 | 40 | 56 | **40** | 32 |
| q192_112_8 | 192 | 112 | 8 | 40 | 92 | 64 | 32 |
| q256_140_8 | 256 | 140 | 8 | 58 | 104 | 80 | 32 |
| q288_182_8 | 288 | 182 | 8 | 53 | 128 | 100 | 32 |
| q320_180_8 | 320 | 180 | 8 | 70 | 128 | 100 | 32 |
| q256_166_8 | 256 | 166 | 8 | 45 | 144 | 100 | 32 |
| q288_196_8 | 288 | 196 | 8 | 46 | 132 | 104 | 32 |
| q256_166_8_reduced | 256 | 166 | 8 | 45 | 114 | 104 | 32 |
| q384_272_8 | 384 | 272 | 8 | 56 | 180 | 144 | 32 |
| q384_284_8 | 384 | 284 | 8 | 50 | 176 | 144 | 32 |
| q480_372_8 | 480 | 372 | 8 | 54 | 232 | 188 | 32 |
| q512_376_8 | 512 | 376 | 8 | 68 | 224 | 188 | 32 |

0 of 192 runs were admissible. The closest approach is `q144_64_8` at 40,
25 percent above the cap; every other file is at least 100 percent above
it. Unlike the two-yoke column this is a search failure, not a proof, and
a mechanism that adds light row-space elements — rather than resampling the
existing ones — is what would reopen it.

## What did land

Two three-yoke matrices did admit a light basis and are on the board as
row-space replacements of their published generators: `codes/96-30-8.json`
(w0 36 to 32) and `codes/112-40-8.json` (w0 60 to 32), described in
`notes/96-30-8.md` and `notes/112-40-8.md`. The other eight admissible
two-yoke matrices were already at w0 36..64 and were filed as published:
`codes/32-18-4.json`, `codes/36-16-4.json`, `codes/40-24-4.json`,
`codes/48-30-4.json`, `codes/56-36-4.json`, `codes/64-42-4.json`,
`codes/64-48-4.json`, with the ninth (`q24_8_4`) dominated by an existing
`codes/24-10-4.json` and never filed.

## Boundary

This is a claim about one question: *can this specific code be presented
with check weight 32?* For the 21 two-yoke matrices the answer is no for
every generator choice, exactly. For the 12 three-yoke matrices the answer
is "not found in 16 seeded runs of the documented reducer", and the route
reopens for anyone who can increase the number of weight-32 row-space
elements rather than recombining the ones already there. It says nothing
about the codes themselves — `[[144,64,8]]` at weight 40 remains a real
code, just not one admissible here.

## Reproducing

`research/multi_yoke_light_basis.py` implements both halves of the test and
prints the tables above; it takes the paper's `ecc/chain_codes/` directory
as `--chain-codes`. The matrices themselves are not vendored into this
repository: they come from `github.com/yugahirai/multi_yoked_surface_codes
@ b3e8b3e`, files `ecc/chain_codes/2_yoke/*.txt` and
`ecc/chain_codes/3_yoke/*.txt`.
