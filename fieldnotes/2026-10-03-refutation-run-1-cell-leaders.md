---
title: "Refutation run 1 over the board's cell leaders: 929 screened, 478 attacked at 300M trials per side, 87 corrections"
date: 2026-10-03
author: "@vprusso"
model: human
topics: [refutation, gpu, cell-leaders, distance-upper-bounds, campaign-record]
---

# Refutation run 1 over the cell leaders

The first run of the standing refutation pass proposed in issue #2025, on
2026-09-24 to 2026-09-26. Its working report and receipts live in a
gitignored staging tree and so cannot serve as evidence; this note and
`research/audits/refute-run-1-2026-09-26.json` (the attack list with the
reason per entry, the 87 corrections, and the 476 GPU receipt rows) are the
committed record. Every correction PR also carries its witness, budget,
seed, and trial count on the entry itself.

## Attack list

Board head `7b05f407`, 1,403 entries. Cell leaders, the union of the per-cell
Pareto frontiers over (n, k, d, w) across the twelve locality by weight
cells: 929.

| status | reason | count |
|---|---|---|
| in | uncertified cell leader without a fresh-seed 300M receipt | 478 |
| out | exact certificate in `certs/` consistent with the entry | 378 |
| refuted without GPU | cyclic two-block entry whose norm-lift quotient bound is below the claim | 42 |
| out | cyclic two-block entry whose claim equals the minimum of its single-block and quotient bounds | 20 |
| out | fresh-seed 300M-per-side receipt already on file beyond the audit seeds | 11 |

GPU order was descending kd^2/n.

## GPU pass

`verify/ris_gpu.py` in campaign mode, recover mode, 300,000,000 trials per
side, pair depth 0, two fresh seeds (4101, 4102) for every target, both
sides. 476 of 478 targets ran, 88.57 A40-hours over 187 jobs on three pods
(pod 3 alone until the queue was split three ways on 25 September).

| outcome | targets |
|---|---|
| held, read at the claim on both sides | 403 |
| held, read above the claim on both sides at both seeds (inconclusive; the entry's own ladder stays the deepest evidence) | 24 |
| refuted | 45 |
| no reading (tool error, below) | 4 |
| not run (correction PRs already open from another session) | 2: `684-20-48`, `602-8-40` |

## Corrections

87 correction PRs, #2056 to #2213: 42 structural (norm-word lift of a
quotient logical, no GPU time) and 45 from the GPU pass. The gate's own
pair-depth kernel refuted three of them further and each was re-amended in
place (#2087, #2092, #2190). Largest collapses: `666-150-76-b` 66 to 36,
`674-84-90` 90 to 44, `630-28-90` and `630-16-90` 90 to 60, `630-10-100` 100
to 72. All merged.

## The four with no reading, and the bug behind them

`625-1-25`, `729-1-27`, `841-1-29`, `961-1-31`, all large k = 1 surface
codes. The GPU committed invalid operators: in `sqetch_ksub_recover_kernel`
a block that found no logical never wrote `control[0]`, which still held the
column loop's last pivot result, so a stale row was copied out. The failure
rate rose with n (one request in four at 625, four in four at 961). Every
GPU-proposed operator is re-verified on the CPU before it counts, so the bug
surfaced as failed receipts rather than false refutations; CPU pair-depth
passes read exactly the claims on all four. Fixed in #2218 with a regression
test over those entries, merged 26 September, after this run.

## Incident

At about 16:20 UTC on 24 September the shared network volume disconnected on
all three pods; every process writing to it died, including the batch in
flight. Runners fell back to local disk within minutes. Lost: about thirty
GPU-minutes of refutation; no completed receipt.

## What was not done

Step 2 of the issue, shadow construction (pre-gating an owned entry inside
each target's dominance shadow so a collapse converts into a record), was
not run. The run opened corrections only.

## Limits

Two seeds at 300M trials per side is the depth of this pass, not a
certificate: the audit convention counts a target as held only when the
search reached the claimed weight, and 24 did not. Where the single-block
kernel exceeds 22 dimensions the structural cap is the accelerator's
20,000-trial sample, so "claim at cap" is itself a sampled statement. The
pass is pod-dependent; with no pod up it does not run.
