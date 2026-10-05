---
title: "The first formal-tier replay: Lean-QEC's BB72_dist_6 is about the board's [[72,12,6]], its binding is now checked by hash, and its stored proofs do not verify at the pinned commit"
date: 2026-10-05
author: "@vprusso"
model: "Claude Fable 5.1 (Claude Code)"
topics: [certificates, formal-verification, lean, trust, negative-results]
status: active
related:
  - 2026-10-04-formal-tier-lean-qec-artifact-model.md
  - 2026-10-04-proof-log-batch-at-n-144.md
---

## TL;DR

The formal tier got its first full replay today, and the replay failed in
the way the tier was designed to make visible. Lean-QEC's `BB72_dist_6`
(`VerifiedQC/Lean-QEC` at `e0b90148694c`) proves `6 <= distance` for a code
whose check matrices decode to exactly the board's `codes/72-12-6.json`, so
the binding is right, and `verify/check_certs.py` now holds any formal
certificate to that binding by hash. But `lake build` of the proof file at
the pinned commit, on the pinned toolchain, fails on the two distance
lemmas: the stored LRAT certificates that `bv_check` replays do not verify
against the formulas the tactic produces there. The two rank lemmas, which
use the same mechanism, verify. No formal certificate is filed. The theorem itself is not in doubt: with the two `bv_check` calls replaced by `bv_decide`, so that Lean re-solves the instances with its bundled CaDiCaL and checks the fresh LRAT with its verified checker, the file builds in 95 s on the same toolchain. What does not replay is the recipe as committed, and a certificate is about the recipe.

## The binding, which is right

Lean-QEC defines the code twice and proves the definitions agree:
`BB72_X_mat` from the bivariate bicycle polynomials (`A = x^3 + y + y^2`,
`B = x + x^2 + y^3` on `Z_6 x Z_6`), and `BB72_X` as a 36 x 72 bit-vector
literal with `BB72_X_correct : BB72_X = flatten_matrix BB72_X_mat` by
`decide`; likewise for Z. Decoding the literals (row-major, bit `i*72 + j`
is entry `(i, j)`, least significant bit first) gives 36 rows per side whose
supports are, as sets, exactly the rows of `codes/72-12-6.json`; the other
three bit orderings do not match.

`checks_sha256` is now defined: sha256 over the compact JSON of
`{"X": rows, "Z": rows}` with each row's support sorted and each side's rows
sorted, so it names the stabilizer presentation on the labeled qubits and
nothing about file layout. `check_certs.py --checks-sha256 <slug>` prints it
(`9deb83c9d05295a2...` for this entry), and a formal certificate whose hash
is not its entry's is refused with both hashes in the message. The 4 October
note said the binding is where a #2273-shaped bug could still live; it is
now a checked field rather than a convention.

## The replay, which failed

Recipe as recorded: clone at `e0b90148694c`, toolchain
`leanprover/lean4:v4.30.0-rc2`, mathlib `5450b53e5ddc`,
`lake exe cache get && lake build LeanQEC.Stabilizer.Examples.BB.BB72`.

Two things went wrong, one of them ours to know about and one theirs.

The LRAT files are Git LFS objects. A plain clone leaves 129-byte pointer
files where `bv_check` expects proofs, and the build fails with "SAT solver
produced invalid LRAT: offset 0: digit expected". The recipe has to say
`git lfs pull`, and ours now does.

With the objects pulled (the distance proofs are about 3 MB each), the two
rank lemmas (`BB72_X_rank`, `BB72_Z_rank`, lines 53 and 65) verify, and the
two distance lemmas (`BB72_dist_z` at line 120, `BB72_dist_x` at line 131)
fail with "The LRAT certificate could not be verified; evaluating
`Std.Tactic.BVDecide.Reflect.verifyBVExpr BB72_dist_x._expr_def_1_18
BB72_dist_x._cert_def_1_18` returned `false`". That is Lean's verified
checker rejecting the stored proof against the formula `bv_decide`
normalizes to on this toolchain. The stored files last changed in a commit
titled "analyze runtimes and add benchmarks"; the proof file changed after
that. A stale LRAT against a changed `simp` set is the ordinary reading, and
it is a question for the authors rather than a conclusion.

The development's green CI badge does not bear on this. Its workflow is
`actions/checkout@v4` followed by `leanprover/lean-action@v1`, which runs
`lake build` on the library target; that target's root module imports only
`LeanQEC.Basic`, and nothing outside `Examples/` imports any example, so the
BB72 file is never built in CI. The checkout also does not fetch LFS, so
even a CI that built it would have found pointer files. The theorem's status
on the pinned commit is therefore whatever a local build says, and a local
build says the stored proofs do not check.

## What would make a certificate

A recipe that a third party can run unmodified and that ends in the theorem.
Two routes: the authors regenerate the two LRAT files (or switch the
distance lemmas to `bv_decide`, which costs a minute of solving per build
and no stored artifact), and the certificate pins that commit; or a fork
carries the two-line change at a pinned public commit, the certificate pins
the fork, and the note on it says why. Either way the recipe must include
`git lfs pull` while stored proofs are used. The binding hash and the
checker rule do not depend on which route is taken, and they are in the
tree now.

## What this means for the tier

Nothing about the tier's design is contradicted; this is the design doing
its job. A certificate at `formal` says a third party can rebuild the
theorem from the recipe, and here a third party could not, so no certificate
is filed. Had the tier been a file attachment, the LRAT files would have
been copied into `certs/` and the entry would read `formal` today with a
proof that does not check.

The 389 `proof_log` certificates, `72-12-6` among them, are unaffected: that
tier replays our own CNF and drat-trim, which CI re-derives weekly.

## Caveats

- One commit, one toolchain. The port at `QCL-SUAT/Lean-QEC` and the
  development's own later commits may carry regenerated proofs; the recipe
  in a certificate would point at whichever commit builds.
- The rank lemmas verifying is evidence the pipeline (LFS, toolchain, cache,
  `bv_check`) works here; the failure is specific to the two distance
  certificates.
- Replaying Lean is not something CI does. When a formal certificate is
  filed, the replay is recorded in a note like this one and the binding hash
  is what CI checks on every run.
