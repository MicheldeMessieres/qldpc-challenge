---
title: "Proof-log certificates at n <= 144: 306 of 389 moved, and the proof path beat the incumbent on the hardest seven"
date: 2026-10-04
author: "@vprusso"
model: "Claude Fable 5.1 (Claude Code)"
topics: [certificates, sat, drat, trust]
status: active
related:
  - 2026-10-04-formal-tier-lean-qec-artifact-model.md
---

## TL;DR

Every exact certificate at n <= 144 was re-emitted as pure CNF, refuted with
kissat, and the refutation checked with drat-trim. 306 of 389 now carry a
checked artifact and sit at `proof_log`. 76 stayed at `solver`, and 74 of
those for one reason: the trimmed proof is larger than the tree should
carry.

Two things the issue did not predict. The proof path is not uniformly
slower than the incumbent: on seven entries, including the gross code
`[[144,12,12]]`, the XOR encoding timed out at 120 s per solve and the pure
CNF was refuted and checked inside the same budget. And the binding
constraint is not time but proof size, which runs three orders of magnitude
across the range.

## What ran

`verify/proof_log_all.py`, 6 workers, 120 s per solve, 4 MB cap on the
trimmed artifact per entry. The question handed to kissat is the same one
`_solve_side` hands CryptoMiniSat, with each XOR split into chunks of arity
5 through Tseitin auxiliaries, and with the lex-leader symmetry prefix
dropped: refuting the unpruned instance is the stronger statement and keeps
a pruning constraint out of the artifact.

| outcome | entries |
|---|---|
| moved to `proof_log` | 306 |
| stayed at `solver`, trimmed proof over the 4 MB cap | 81 |
| stayed at `solver`, neither path closed it in 120 s | 2 |

2.30 core-hours for the batch, plus the seven re-runs below. Median time
per entry 0.2 s, longest 571 s.

## Sizes are the binding constraint

| | trimmed bundle |
|---|---|
| median | 6.3 kB |
| 90th percentile | 208 kB |
| largest stored | 703 kB |
| total added to the tree | 18.7 MB across 306 bundles |

The 74 that stayed at `solver` were refuted and checked; their proofs are
simply too big to carry, from 4.0 MB to 303 MB trimmed. The cap is a policy
choice and the note on each of those certificates says so, so none of them
is recorded as unproved when what happened is that the artifact was not
stored.

## The proof path is sometimes the faster one

Seven entries had the XOR encoding time out at 120 s while kissat refuted
the chunked CNF and drat-trim checked it inside the same budget.
CryptoMiniSat's Gaussian elimination over native XOR clauses is the reason
the incumbent exists, and on these it did not pay.

| entry | kissat solve, X side | trimmed, both sides |
|---|---|---|
| `96-4-12` | 49.9 s | 645 MB |
| `98-6-12` | 61.6 s | 635 MB |
| `128-13-10` | 38.0 s | 428 MB |
| `140-10-10` | 112.9 s | 750 MB |
| `144-12-12` | 59.3 s | 581 MB |
| `144-16-10` | 25.7 s | 243 MB |
| `144-2-12` | 59.6 s | 660 MB |

All seven are `d_exact` with both sides checked, and all seven stay at
`solver` because their proofs are two orders of magnitude over the cap.
Being faster to refute and more expensive to carry is the same property
seen twice: these instances are hard for the XOR reasoning and produce long
resolution proofs.

This first surfaced as seven "disagreements", because the cross-check
treated a timeout as a verdict. It is not one, and the guard now says so: a
real disagreement is only SAT against UNSAT, and that did not occur
anywhere in the 389. Where the incumbent times out and a checked refutation
exists, the checked refutation settles the side, since refusing stronger
evidence for not matching weaker evidence would be perverse.

## What this does and does not buy

It buys one level: the CNF handed to the solver is independently confirmed
unsatisfiable, by a checker that is not ours, against a file anyone can
regenerate from the code JSON. The bundle carries both sides' trimmed cores
and a manifest with the per-side CNF hashes and the commands to regenerate
and re-check.

It does not buy the thing #2273 cost us. A DRAT proof says the formula is
unsatisfiable and nothing about whether the formula asks the distance
question, and in #2273 the formula was fine and asked the wrong one. That
gap is what the `formal` tier is for, and the artifact model for it is in
the note beside this one.

## Caveats

- The 4 MB cap is per entry and arbitrary. At 18.7 MB total the tree is
  carrying as much proof as it is carrying codes; a lower cap would trade
  coverage for size, and the batch log records every size so the trade can
  be re-made without re-running anything.
- `drat-trim` prints no version, so the checker field records the binary's
  sha256 prefix. A different build that disagreed would be visible, which a
  bare tool name would not make visible.
- The two entries that closed in neither path were certified originally at
  a 900 s budget. 120 s is this batch's limit, not a statement about them.
- Timings are from one laptop with six workers competing; the per-entry
  numbers in `certs/proof_log_batch.jsonl` are wall time under contention,
  not clean measurements.
