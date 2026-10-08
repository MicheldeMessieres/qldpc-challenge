---
title: "Running a collaborative literature-harvest campaign: what 14 numbered items produced, and the five silent screening errors behind every false positive"
date: 2026-10-08
author: "@MathysRennela"
model: "Space Bunny Alpha 1.0"
topics: [literature, openalex, arxiv, campaign-method, screening, negative-result, collaboration]
status: active
---

## TL;DR

Issue #2863 ran as a collaborative harvest: 14 numbered items, claimed one at a
time, each ending either in a filed code or in a written negative. It produced
submissions, a follow-up round over a 400-paper arXiv batch produced another,
and — more usefully — it produced a list of the ways to get a **false
positive**, because all five of mine were silent. None raised an error. Four of
them would have filed a code the gate rejects.

The yield is low: roughly one code per 180 papers. That is the expected number
for this activity, not a sign of a bad campaign. The durable output is the
method below.

This note is deliberately tool-agnostic. Round 1 harvested from OpenAlex, round
2 from an arXiv listing sweep, and the two differ enough to matter (last
section). The process advice is independent of the source and should survive a
change of tool.

The per-paper reconstruction verdicts for items L1–L7 are already recorded in
`fieldnotes/2026-10-07-openalex-harvest-reconstructions.md`, with builders under
`research/campaigns/openalex-harvest-2863/`. This note does not repeat them. It
covers what running the campaign taught us about running it.

## Yield

| round | pool | construction candidates | already on the board | codes filed |
|---|---|---|---|---|
| 1 (OpenAlex) | 1507 works | 14 numbered items | 0 after triage | 3 |
| 2 (arXiv) | 400 papers | 197 | 24 | 1 |

Two things are worth stating plainly.

**A negative is the common outcome and is a real result.** Eleven of fourteen
items closed negative. Per `CONTRIBUTING.md` those belong in fieldnotes, not in
`codes/`. The roster's *Done when* criterion should therefore describe the
**finding**, not the filing: an item whose criterion is "determine whether this
paper publishes rebuildable matrices" is finished when that question is
answered either way. Several of ours ended there, and "the paper publishes no
matrices" is a useful answer — `TRACKS.md` records exactly that failure mode
for `[[282,12,14]]` and for the Kasai codes.

**Novelty, not recall, is the binding constraint.** By round 2 the board
already held the good instances from the papers that print generators. Of 197
construction candidates, the survivors were overwhelmingly quaternary or qudit
codes (not submittable as qubit entries), codes dominated once screened at their
real weight, and papers with no finite instances. When a campaign runs dry,
widening recall helps more than refining the screen.

## Five false positives, all silent

**1. Not deduplicating against the board before screening.** A board entry does
not strictly dominate *itself* — the four-axis rule requires at least one strict
axis — so any triple already on the board trivially "survives". In round 2,
`[[66,20,7]]` came out of the screen as the single best candidate of the round.
It is the board's own entry, from a paper the board cites 37 times (which also
supplies `[[90,20,7]]`, `[[54,16,6]]`, `[[674,86,89]]` and six 682-length
entries). 8 of 43 shortlisted papers were already cited; 24 of 400 across the
batch. **Diff against `codes/`, `notes/`, `fieldnotes/` and `TRACKS.md` before
screening, not after.** This was the largest single source of false positives.

**2. Screening at an assumed weight class.** Check weight is an input to the
dominance rule, and it is the one axis a parameter table does not give you. We
screened a bicycle family at "weight-6, surely"; the source's own table states
weights of **19 to 38** for those instances. Two candidates that screened as
advancing at w=6 — `[[90,18,8]]` and `[[70,16,7]]` — are dominated at w=38, by
`[[64,18,8]]` and `[[66,20,7]]` respectively. Rebuilding the generators from the
table reproduced n, k *and* w=38 exactly, which is how the discrepancy
surfaced: the construction was right and the screen was wrong. **Take the weight
from the paper. If you cannot, do not screen the triple — you are screening a
guess.**

**3. Believing a parameter screen tells you whether a code is submittable.** It
does not. `[[162,24,6]]` (arXiv:2407.03973 Table 1) builds to the paper's
n=162, k=24, is undominated at w=6, and is rejected by the gate with
`failed_checks: ["tanner_connected", "stabilizer_group_connected"]`. Its Tanner
graph is disconnected, so the d=6 it exhibits is not a property of one connected
code. Every axis the Pareto rule inspects says "file this"; only the gate sees
it. **The screen ranks candidates; `verify/validate_candidate.py` decides.**

**4. Construction-convention errors that produce valid codes.** For a bivariate
bicycle code, transposing the orders l and m, or misreading `y³` as `(3,0)`,
yields a square matrix of plausible rank that commutes perfectly and has the
**wrong k**. In round 2 this produced k=8 for a published `[[144,12,12]]` and
k=0 for a published `[[162,24,6]]`. Only comparing *all* rows of the source
table against their published `[[n,k,d]]` caught it. **Pin a convention against a
known-good board entry before trusting any parameter derived from it**, then
confirm the generator family reproduces its source table wholesale — one row
agreeing proves nothing, and nine disagreeing is the signal.

Note the shape of the trap: these are the errors a language model makes when
transcribing a table, and they are invisible to every check except comparing
against the source. Treat a reproduced parameter triple as evidence about your
transcription, not just about your algebra.

**5. Treating quaternary and qudit codes as qubit codes.** Round 2's
highest-`kd²/n` source, arXiv:2610.06820, lists ten attractive off-board codes;
exactly **one** is binary (`F2 [[1088,128,12]]`, w=8 — and it is dominated). The
other nine are over F₄. Likewise arXiv:2501.07363's `[[169,24,12]]` is
`[[169,24,12;1]]₂`, an entanglement-assisted code over a quaternary alphabet.
Both read as ordinary qubit codes in a parameter table. **Check the field, not
just the triple.**

## Source-specific findings

*These depend on the harvest tool and may not survive a different one.*

**OpenAlex: high recall, poor precision.** Round 1's 1507-work pool needed heavy
filtering. Roughly 40% of the works under the `qldpc-codes` keyword are
self-published preprints with no codes, and about 35 of 102 papers carrying
abstract `[[n,k,d]]` claims were decoder or hardware papers quoting
`[[144,12,12]]`, which has been on the board for years.

**OpenAlex also misses recent work.** Of the 50 most recent `abs:"quantum LDPC"`
arXiv papers, OpenAlex indexes 42 — a 16% miss rate — including arXiv:2601.08824,
which `TRACKS.md` cites as a bar. A future round using arXiv listing sweeps
directly should expect better coverage of recent work and worse precision, and
should expect to re-learn error 3 above on parameters quoted without generators.

**On tool choice.** If the next campaign swaps the source, do not carry these two
numbers across — re-measure both on the new source. The five errors above are
tool-independent; the two paragraphs above are not.

## Advice for running the next one

**Give every item a stable ID and a finding-shaped *Done when*.** Numbering is
what lets several people work the same list without colliding. A criterion
described as a *finding* rather than a *filing* is what makes a negative result
count as completion, which is what keeps people from abandoning items that turn
out barren.

**Claim by editing the issue body, not by commenting.** The #2863 protocol listed
a comment *and* a roster edit, and the comment alone proved insufficient to
signal a live claim — the roster drifted out of date as a result, and a stale
roster is worse than none because it reads as authoritative. If the roster is the
coordination surface, treat an edit to it as the claim. Keep claims atomic and
visible: several people claiming against a comment thread is how two sessions end
up rebuilding the same paper.

**Split the expensive part deliberately.** The deep distance search is the
bottleneck and it parallelises. On item L4 one session reconstructed the code and
ran a 10M-trial pass while another rebuilt it independently, screened the
surrounding family, and prepared the filing; both are credited on the merged
entry. That was luck rather than design, and it is worth doing on purpose.

**Let people file their own work, and settle attribution before opening the PR.**
A reconstruction is still someone's work. On this campaign one build was
initially left unfiled because the agent running it was not the person who made
it, and the item stalled until co-authorship and both models were written into
`provenance` explicitly. Attribution is CI-checked precisely because this is
easy to get wrong, and a misattributed PR is expensive to walk back.

**Publish the negatives in the same campaign as the codes.** Eleven negative
results from fourteen items is most of the knowledge here. Each belongs in a
fieldnote with numbers — region and depth — so the route can be reopened by
someone with a genuinely new mechanism, and closed again cheaply by the next
person who tries it.

**Watch for the failure mode where a screen starts looking like a result.** Late
in round 2 we began comparing two screening methods instead of looking for codes,
and produced a confident recommendation that measurement then refuted twice —
first on sample size, then on the weight error above. **A screen is an
instrument; calibrate it against known positives and known negatives before
believing its ranking.** If a metric reports that one arm wins on four viable
papers per arm, it has not established which arm wins.

## Reproducing

```bash
gh issue view 2863                                  # the roster and its closing state
ls research/campaigns/openalex-harvest-2863/        # round-1 builders
cat fieldnotes/2026-10-07-openalex-harvest-reconstructions.md   # per-paper verdicts
cat notes/200-16-17.md notes/512-174-8.md           # two of this campaign's submissions
```

The remaining two submissions from this campaign are in review and are not part
of this tree: the canonical lifted-product code of arXiv:2607.28605 in PR #2889,
and a bivariate bicycle code of arXiv:2407.03973 in PR #2888, whose generator
builder (which reproduces all ten rows of that paper's Table 1) is added there.
