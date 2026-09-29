# Derived provenance

Which board entries reproduce a published code, and which were found here.

The board could not answer that. The declared fields do not support it: of
1,564 rendered entries, 1,280 carry `provenance.origin: submission` and 1,074
carry no `novelty` at all, while 556 of those cite a paper in their own
construction text. `submission` records the path an entry arrived by, not
where the code came from. `arXiv:2306.16400` alone appears in 326 construction
strings.

So the tag is computed. `novelty/iso_check.py` decides permutation equivalence
of the given generating sets using nauty's canonical form of the typed Tanner
graph, and re-verifies every hit by mapping row spaces with the recovered
qubit permutation. `derived.json` is that output, bucketed:

| bucket | meaning |
|---|---|
| `literature` | isomorphic to a published code, with source, reference, and the matched id |
| `parameters_only` | a published code shares its parameters but ships no matrices, so equivalence is undecided |
| `no_match` | nothing in the index matches |

## What `no_match` does not mean

It does not mean the code is new. Two different sparse generating sets of the
same stabilizer group can have non-isomorphic Tanner graphs, so a non-match is
"not found in this index", not "not published". Any count that reads
`no_match` as a novelty claim is overstating it.

## Why the source list is separate

`sources.json` says which index sources are published work. This matters
because the index also holds **this project's own deep-search output**, added
so internal duplicates get caught. A match against `deep_search_2026-09` means
a code was found here, and reporting it as literature would invert the claim
the whole tag exists to make. 33 such rows were present the first time this
ran.

A source that appears in the index but in neither list is reported and treated
as not-literature, so adding an index source can never silently promote board
entries.

## Regenerating

```
# needs a novelty/ checkout, its index, and pynauty
python research/derive_provenance.py \
    --from-matches ../novelty/isomorphism_matches.csv \
    --from-params  ../novelty/param_matches.csv

# validate the committed table against codes/ (no index needed)
python research/derive_provenance.py --check
```

The table is keyed by slug and lives here rather than inside each
`codes/*.json`, because a derived field written into a submission document
would drift from its derivation the moment the index grows.

Nothing here gates a submission. `verify/` is untouched; this only reports.
