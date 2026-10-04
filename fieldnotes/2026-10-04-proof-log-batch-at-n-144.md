---
title: "Proof-log certificates at n <= 144: all 389 re-derived and checked, with the recipe committed rather than the refutation"
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
kissat, and the refutation checked with drat-trim. All 389 now sit at
`proof_log`. 385 closed at the batch's 120 s per solve, and the last four
at 900 s.

No refutation is committed. A `proof_log` certificate carries the sha256 of
the formula each side's refutation is of, the solver and checker with
versions, and the command that regenerates the formula from the code JSON
and re-checks it. A CI job replays a rotating subset on every pull request
that touches the certificates or the emitter, and the whole set weekly.

Two things the issue did not predict. The proof path is not uniformly
slower than the incumbent: on seven entries, including the gross code
`[[144,12,12]]`, the XOR encoding timed out at 120 s per solve and the pure
CNF was refuted and checked inside the same budget. And proof size runs
five orders of magnitude across the range, which is what settled the
question of what to commit.

## What ran

`verify/proof_log_all.py`, 6 workers, 120 s per solve, then the four
entries that budget did not close again at 900 s. The question handed
to kissat is the same one `_solve_side` hands CryptoMiniSat, with each XOR
split into chunks of arity 5 through Tseitin auxiliaries, and with the
lex-leader symmetry prefix dropped: refuting the unpruned instance is the
stronger statement and keeps a pruning constraint out of what a checker
has to take on trust.

| outcome | entries |
|---|---|
| moved to `proof_log` at 120 s per solve | 385 |
| moved to `proof_log` at 900 s per solve | 4 |

2.1 core-hours of solving and checking in total. Median time per entry
under a second, longest 40 minutes (`[[140,6,14]]`, both sides). 365 of
the 389 re-check in 20 s or less, which is the pool the per-PR subset
draws from.

## Why the recipe and not the refutation

The first version of this committed a tarball per entry with both sides'
trimmed cores, capped at 4 MB, and left 81 entries at `solver` because
their proofs were over the cap. The review objection was that a committed
binary is not auditable: CI cannot grep it, a reviewer cannot diff it, and
an artifact nobody opens looks like evidence without being any. Plain text
does not rescue it, since the same content uncompressed was 95.8 MB
against 18.7 MB gzipped, and the trimmed cores across all 389 come to
15.1 GB.

So nothing is stored. `cnf_sha256` on the certificate is what makes
regeneration honest: a formula that does not hash to the recorded value is
not the one that was refuted, and `verify/replay_proofs.py` stops on that
side before solving anything. Where the hash matches, it re-runs kissat and
has drat-trim check the new proof, and fails the run if either verdict
moved. The 81 entries the cap had held back are in on the same terms as
the rest, since there is no longer a size to hold them back on.

## The proof path is sometimes the faster one

Seven entries, `96-4-12`, `98-6-12`, `128-13-10`, `140-10-10`, `144-12-12`,
`144-16-10`, and `144-2-12`, had the XOR encoding time out at 120 s while
kissat refuted the chunked CNF and drat-trim checked it inside the same
budget. CryptoMiniSat's Gaussian elimination over native XOR clauses is the
reason the incumbent exists, and on these it did not pay.

This first surfaced as seven "disagreements", because the cross-check
treated a timeout as a verdict. It is not one, and the guard now says so: a
real disagreement is only SAT against UNSAT, and that did not occur
anywhere in the 389. Where the incumbent times out and a checked refutation
exists, the checked refutation settles the side, since refusing stronger
evidence for not matching weaker evidence would be perverse.

## What this does and does not buy

It buys one level: the CNF handed to the solver is independently confirmed
unsatisfiable, by a checker that is not ours, against a formula anyone can
regenerate from the code JSON and confirm by hash, on a schedule rather
than once.

It does not buy the thing #2273 cost us. A DRAT proof says the formula is
unsatisfiable and nothing about whether the formula asks the distance
question, and in #2273 the formula was fine and asked the wrong one. That
gap is what the `formal` tier is for, and the artifact model for it is in
the note beside this one.

## Caveats

- `drat-trim` prints no version, so the checker field records the binary's
  sha256 prefix. CI builds kissat and drat-trim from pinned commits, so a
  different build that disagreed would be a deliberate edit to the
  workflow and not a drift in whatever a package manager ships.
- The four entries that needed 900 s were certified originally at that
  budget too. The weekly replay runs them at 1800 s per solve and per
  check, since CI timings are not laptop timings.
- The per-PR replay is a sample. Twelve entries out of 365 quick ones, by
  pull request number, so a defect in the emitter that touched one
  formula in thirty would be caught on the weekly run and not necessarily
  on the PR that introduced it.
- Timings are from one laptop with six workers competing; the per-entry
  numbers in `certs/proof_log_batch.jsonl` are wall time under contention,
  not clean measurements.
