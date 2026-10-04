---
title: "What a formal distance certificate would be: Lean-QEC is public, and it does not ship a file"
date: 2026-10-04
author: "@vprusso"
model: "Claude Fable 5.1 (Claude Code)"
topics: [certificates, formal-verification, lean, trust]
status: active
related:
  - 2026-10-03-sat-weight8-t3-at-n25-n36-is-sat.md
---

## TL;DR

Issue #2511 left one question open: how a Lean-QEC certificate is consumed,
and whether it travels in `certs/` as a file or only as a Lean build a
checker replays. It was recorded as blocked on the library. The library is
public, at `VerifiedQC/Lean-QEC` with a mathlib port at `QCL-SUAT/Lean-QEC`,
so the question is answerable now.

The answer is that there is no file to ship, and chasing one would miss the
point. What makes a Lean-QEC certificate formal is the verified reduction
from the code to the SAT instance, and that lives in the Lean development,
not in any artifact it emits. The transportable object it does produce, a
SAT query and its refutation, is exactly the `proof_log` level, which is
what #2728 is already building on our own encoding.

So the `formal` tier should record a replay recipe, not an attachment. And
the binding between the Lean-side code and the board entry is the new place
a #2273-shaped bug can live.

## What the library emits

Top-level layout: `LeanQEC/`, `bv_decide_queries/`, `data_analysis/`.
Toolchain Lean v4.30.0-rc2 on mathlib4, Apache 2.0, built with
`lake exe cache get && lake build`.

`bv_decide_queries/` holds the emitted SAT queries, four per code: X and Z,
distance and rank. The codes present are BB18, BB70, BB72, BB90, BB108,
BB144, GB54, plus Steane and Golay. The worked example named in the README
is `BB72_dist_6`.

The directory name is the tell. Lean's `bv_decide` normalizes a BitVec goal,
emits CNF, calls an external SAT solver, and then checks the solver's LRAT
proof with a checker that is itself verified in Lean, so the solver is not
in the trusted base. The paper's own contribution sits one level above
that: `bitvec_sat_translation_correct` is the theorem linking the binary
symplectic distance to the SAT formulation, which is the step that was
wrong in #2273 and is here proved rather than assumed. Confirm the
`bv_decide` detail against the paper before relying on it; it is read off
the directory name and the tactic's documented behavior, not off a
statement in the README.

## Why there is no file

A certificate at this level is a Lean theorem. Checking it means having the
toolchain, the pinned mathlib, the development, and the time to build. The
things that could be extracted and attached are:

- the CNF, which is an input and asserts nothing;
- the LRAT refutation, which asserts that the CNF is unsatisfiable and
  nothing about what the CNF asks.

The second is `proof_log`, and our own pipeline in #2728 already produces
it, from our own encoding, without Lean. Attaching Lean's LRAT to a
certificate and calling it `formal` would claim the verified reduction
while shipping only the part that does not contain it. The schema's note
already says the two levels are kept apart for this reason; this is that
distinction showing up in the artifact.

## What a `formal` entry should carry

A replay recipe precise enough that a third party reaches the same theorem,
and a binding precise enough that the theorem is about our entry:

| field | why |
|---|---|
| `verification.level: formal` | as today |
| `verification.reference` | the formalization, `arXiv:2605.16523` |
| `verification.checker` | `Lean <toolchain> + mathlib <rev>` |
| `verification.replay.repo`, `.commit` | the development and the exact commit |
| `verification.replay.theorem` | the theorem name, e.g. `BB72_dist_6` |
| `verification.replay.build` | the command that reproduces it |
| `verification.checks_sha256` | sha256 of the entry's canonical `(H_X, H_Z)` |

The last row is the load-bearing one and it is new. Lean-QEC proves things
about a code it defines in Lean. A perfect proof about a different matrix
pair certifies nothing about the board. The hash makes the binding
checkable, and the only honest way to maintain it is to generate the Lean
definition from `codes/<slug>.json` rather than transcribe it, so the two
cannot drift. That generator does not exist yet and is the first piece of
work if this tier is pursued.

## What this does not settle

Whether to pursue it at all. The case for is unchanged and is about the
next bug rather than the current numbers: every distance in `certs/`
survived the #2273 re-check, so the value is that the encoding step stops
being ours to get wrong. The case against is that the tier costs a Lean
development, a generator, and a replay story for every reader, to
re-certify entries we already believe.

Two numbers for that decision, recounted against the tree today rather
than carried forward:

| | count |
|---|---|
| certificate records in `certs/` | 645, all of them `d_exact` |
| at n <= 90, the demonstrated in-kernel range | 286 |
| at n <= 144, the stated formulation range | 389 |
| of those 389: generalized bicycle | 247 |
| of those 389: bivariate bicycle | 42 |

The two families Lean-QEC targets cover 289 of the 389. Note that the
earlier recount on #2511 gave 624 `d_exact` of 645; every file under
`certs/*.json` carries `d_exact: true` today, so the figure to use is 645.
