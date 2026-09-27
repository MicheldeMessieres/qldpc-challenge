# arXiv watch: finding papers that may carry a board-relevant code

`research/arxiv_watch.py` polls the arXiv API for papers that might introduce a
qLDPC code, a construction, or reusable code data, and keeps `arxiv-ledger.jsonl`
next to this file as both the dedup state and the human review record. This file
is the process: the query, the polling rules, the ledger format and the review
path are all here, so a poll can be rerun and reproduced from this page alone.

Screening is triage, not a claim. A screened-in paper is one whose abstract
carries a hard signal and is therefore worth a human minute. It is not a claim
that the paper contains a code, that the code is new, or that its distance is
what the abstract says. Parameters read out of an abstract are stored as
`claimed_params` and printed as claims (`[[288,12]] claims d = 18`), never as a
distance.

No board change happens here. This workflow writes one file, the ledger. It
never adds or edits an entry under `codes/` and never touches anything under
`verify/`. A lead that survives reading goes through the normal submission and
gate path in [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) like any other
candidate.

The tests in `research/test_arxiv_watch.py` run offline: a fixture breaks the
socket and `urlopen`, so a change that reaches for the network fails in the suite
instead of hitting arXiv during a test run.

## Running a poll

```
uv run --frozen python research/arxiv_watch.py
```

The intended cadence is weekly. With no `--days` the window is derived from the
ledger: the latest `last_seen` across its rows, plus two days of slack for
arXiv's indexing lag, floored at seven days. A skipped week therefore widens the
next run instead of leaving a hole, and the window actually used, with the reason
for it, is printed on the first line of every run. An explicit `--days` shorter
than the gap since the last poll is honoured with a warning, since it will skip
the uncovered days.

Rows marked `READ` in the output are the screened-in ones. Everything already in
the ledger at the same version is silently skipped, which is the point of the
ledger; a version bump is re-announced under "new versions of papers already
seen" and carries `vN -> vM`.

| flag | effect |
|---|---|
| `--days N` | fix the window instead of deriving it |
| `--pages N` | page cap per poll (default 10) |
| `--batch N` | entries per page (default 100) |
| `--limit N`, `--full` | rows printed per section (default 10) |
| `--abstracts` | add the first 400 characters of each abstract |
| `--dry-run` | poll and print without writing the ledger |
| `--json` | emit the new and updated rows, with the query, the screen fingerprint and the scan record |
| `--list [all\|screened-in\|unreviewed\|relevant\|not-relevant\|uncertain]` | read the ledger back without polling |
| `--ledger PATH` | use a different ledger file |

The defaults walk at most 1000 entries per poll. A walk that ends on the page cap
or on a short page inside the window is reported on stderr as a truncated window,
naming the oldest entry it reached, rather than passing for a complete one. Rerun
with a larger `--pages` or a narrower `--days` when that happens.

A poll needs network. Reading the ledger back does not:

```
uv run --frozen python research/arxiv_watch.py --list screened-in --full
uv run --frozen python research/arxiv_watch.py --list unreviewed
```

## The query

One `search_query` against `https://export.arxiv.org/api/query`, requested with
`sortBy=lastUpdatedDate&sortOrder=descending`, paged with `start` and
`max_results`. It is built by `build_query()` from `QUERY_GROUPS` as a union of
(category group, term group) pairs, because the category gate cuts both ways: a
phrase whose wording is also classical ("quasi-cyclic", "code distance") drags in
the whole `cs.IT` coding feed unless it is held to `quant-ph`, while a phrase that
only ever means one thing ("bivariate bicycle") needs no gate, where a gate could
only lose papers. A paper introducing a construction often never writes "qLDPC",
so family names and CSS/stabilizer vocabulary are queried alongside it.

| group | categories | terms |
|---|---|---|
| unambiguous families | none | bivariate / trivariate / multivariate / coprime / generalized bicycle, lifted product, balanced product, hypergraph product, quantum Tanner, two-block group algebra, 2BGA, twisted tori |
| quantum vocabulary | `quant-ph`, `cs.IT`, `math.CO` | quantum LDPC, qLDPC, quantum low-density parity-check, CSS code, stabilizer code, group algebra code, good quantum codes |
| classical-sounding or broad | `quant-ph` | quasi-cyclic, circulant permutation matrix, code distance, check weight, geometrically local, generalized toric, tile code, coset code, high-rate quantum, finite-length quantum, low-weight quantum, code discovery, search for quantum codes |

That comes out as one 904-character query string, which the live API accepts:

```
(abs:"bivariate bicycle" OR abs:"trivariate bicycle" OR abs:"multivariate bicycle" OR abs:"coprime bicycle" OR abs:"generalized bicycle" OR abs:"lifted product" OR abs:"balanced product" OR abs:"hypergraph product" OR abs:"quantum Tanner" OR abs:"two-block group algebra" OR abs:"2BGA" OR abs:"twisted tori") OR ((cat:quant-ph OR cat:cs.IT OR cat:math.CO) AND (abs:"quantum LDPC" OR abs:"qLDPC" OR abs:"quantum low-density parity-check" OR abs:"CSS code" OR abs:"stabilizer code" OR abs:"group algebra code" OR abs:"good quantum codes")) OR ((cat:quant-ph) AND (abs:"quasi-cyclic" OR abs:"circulant permutation matrix" OR abs:"code distance" OR abs:"check weight" OR abs:"geometrically local" OR abs:"generalized toric" OR abs:"tile code" OR abs:"coset code" OR abs:"high-rate quantum" OR abs:"finite-length quantum" OR abs:"low-weight quantum" OR abs:"code discovery" OR abs:"search for quantum codes"))
```

Three phrases are deliberately absent, each because it costs more than it
returns: bare `CPM` (in `quant-ph` that is overwhelmingly "completely positive
map"), `"minimum distance"` (with `cs.IT` and `math.CO` in scope it is the entire
classical coding feed), and `"quantum error-correcting code"` (a large fraction of
all `quant-ph` QEC output). The same note sits in the source next to the query.

`sortBy=lastUpdatedDate` is load-bearing, not a preference. The walk stops at the
first entry whose `updated` is older than the cutoff, so the sort key and the
cutoff key have to be the same field or the stop is unsound. Sorting by
`submittedDate` would also hide every new version of an older submission, which
is the common case: referee rounds put v2 months after v1.

## Rate limits, and the 406

Read this before changing the transport or the request pacing.

- `export.arxiv.org` answers HTTP 406 to Python's `urllib` default header set.
  Sending `Accept` and `Accept-Encoding` explicitly is what it wants, and
  `HEADERS` in the script does.
- Headers alone are not enough. arXiv's edge also decides on the TLS client: with
  byte-identical headers and interleaved requests to equivalent uncached URLs,
  `curl` was served 200 and `urllib.request` was refused 406 every time. HTTP
  version, `Connection`, query length and request spacing were each ruled out
  separately; only the client changed the answer. So `http_get()` shells out to
  `curl` and keeps `urllib` as an announced fallback for machines without it.
  A 406 carries no body, no `Retry-After` and no diagnostic, so the two causes
  cannot be told apart by inspection.
- arXiv answers 406 to bursts as well, in streaks lasting several minutes during
  which every request is refused whatever its query, headers or spacing, and then
  serves normally again. A page request therefore waits a streak out:
  `PAUSE_SECONDS = 3` between requests, and on a 406 or 429 a backoff starting at
  30 seconds and doubling to a 120-second ceiling over 6 retries, which rides out
  roughly ten minutes.
- Never run two fetchers against `export.arxiv.org` at once, and in a
  multi-agent run let exactly one agent hold the network. Concurrency is what
  turns an occasional refusal into a streak.
- A short or empty page comes back transiently even when more results exist, so
  the walk disbelieves one short page and retries it after the backoff, but only
  when `opensearch:totalResults` says more results remain. Otherwise a legitimate
  last page would cost 30 seconds on every small window.

## Screening and tiers

`triage()` matches a normalised haystack (title, abstract and the arXiv comment
field, lowercased with hyphens, slashes and runs of space collapsed) against
`SCREEN_TERMS`, in four tiers: 20 family terms, 13 structure terms (check weight,
locality, girth), 24 generic terms, and 10 use-not-introduce terms that carry
negative weight (among them decoder, BP+OSD, threshold, logical error rate,
magic state, lattice surgery, benchmark). Term keys are normalised the same way as the
haystack and a module-level assertion enforces it, because a key carrying a
capital or a hyphen can never fire and its weight is then silently unreachable.

`screened_in` is a hard-signal gate, not a score threshold: a paper is screened in
when its abstract carries a family term, a check-weight or locality term, or
states an `[[n,k,d]]` that it does not attribute to other work. Generic
vocabulary alone never screens a paper in, since every QEC paper writes
"construction", "distance" and "parity-check", and a threshold over those admits
the whole candidate set and carries no information. The score only orders the
rows a human then reads top down; it is ordinal and uncalibrated.

| tier | meaning |
|---|---|
| `strong` | states its own `[[n,k,d]]` and carries a family or structure term |
| `candidate` | one hard signal, either the parameters or the vocabulary |
| `background` | neither; kept in the ledger for dedup, not queued for reading |

Each `[[n,k,d]]` match keeps the sentence it sits in and a `comparison` flag,
raised when the wording before it attributes the parameters elsewhere
("improving on the [[72,12,6]] code of prior work"). An attributed claim earns no
score bonus, no tier credit, and renders as attributed, so nothing downstream
reads a comparison against a published code as this paper's own.

`triage.screen` records a 12-character fingerprint of the query, the term
weights, the hard-signal set and the parameter bonus. Two rows whose fingerprints
differ were screened under different criteria and their scores are not
comparable; the current criteria fingerprint is `7f52932425fe`.

## The ledger

`arxiv-ledger.jsonl`, one JSON object per line, keyed by arXiv id, sorted newest
first and rewritten atomically on every write. A line that will not parse is
reported on stderr and skipped rather than ending the run.

It stores decisions and identity, not a copy of arXiv. A poll holds the
abstract, the author list, the categories and the matched screening terms in
memory, screens on them, prints them, and drops them. Keeping them would add
about 2.4 KiB per paper forever, on a feed that runs at roughly a hundred
papers a month, for text that is one click away at its source and is better
read there. What stays is 379 bytes a row, so a year of polling is about
460 KiB.

| field | content |
|---|---|
| `id`, `version` | the bare arXiv id (an old-style id keeps its archive prefix) and the version seen |
| `title` | how a human scans the list |
| `updated` | the date the cutoff and the feed order both use |
| `tier` | `strong`, `candidate` or `background` |
| `claimed_params` | parameters the abstract states about its own code, as `n`, `k`, `d` and `comparison`; never a distance, always a claim |
| `first_seen`, `last_seen` | poll dates; `last_seen` is what the next window is derived from |
| `review` | the current verdict: `status`, `reason`, `by`, `date`, and the `version` it was formed on |
| `reviews` | superseded verdicts, oldest first |
| `version_history` | present once a row has been seen at more than one version |

A field is written only when it says something. No `review` key means
unreviewed, no `version_history` means the row has only ever been seen at one
version, and the link is derived from the id and version rather than stored.
Reading the ledger fills those defaults back in, so nothing downstream sees a
gap.

Two budgets keep it that way, both asserted by `research/test_arxiv_watch.py`:
a row with no verdict is at most 250 bytes, and a fully reviewed one with a
reason at its 300-character cap is at most 800. A field added later that puts
the bulk back fails the suite.

The ledger is the dedup state, so deleting a row makes its paper new again, and
editing one by hand is how a bad verdict becomes unexplainable. Change it
through the tool.

## Recording a verdict

```
uv run --frozen python research/arxiv_watch.py --review 2609.30069 \
    --status relevant \
    --reason "pair-partition templates; claims [[90,21]] d = 11, admissible and undominated"
```

`--status` is one of `relevant`, `not-relevant`, `uncertain`, and a non-empty
`--reason` is required with it: a verdict with no reason cannot be re-checked by
the next reader. `--by` defaults to `$USER`. The id is normalised, so an
`arXiv:` prefix, an abs or pdf URL and a trailing `v2` all work, and a miss
prints near-matches rather than reaching for the network. `--dry-run` prints the
verdict without writing.

A verdict records the version it was formed on. When a later poll finds a higher
version, the verdict is carried forward but marked `stale: true` and renders as
"predates this version, needs re-reading", since a v3 can add the codes the
abstract only promised in v1. Recording a new verdict moves the old one into
`reviews` rather than overwriting it.

State a claim as a claim in the reason. "claims d = 15" is right; a bare `d = 15`
in a reason is the same error the tool is built to avoid.

## Following a lead

A `relevant` verdict is a reading assignment, not a board change.

1. Check admissibility against the resource limits in
   [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md): `n <= 700`, or `n <= 1000`
   with max check weight `w <= 8` and claimed `d <= 40`. The claimed
   `[[34542,23032,18]]` sitting in this ledger is out of scope whatever else it
   is.
2. Check the claim against the board: `./qldpc recent`, `codes/*.json`, and the
   track it would land in. Most admissible claims in the literature are already
   matched or dominated, in which case the construction, not the instance, is the
   lead.
3. Reconstruct the code from the paper and put it through
   `verify/validate_candidate.py`, as in
   [`../AUTORESEARCH.md`](../AUTORESEARCH.md). Only `passed: true` makes it a
   find. A parameter claim in an abstract never becomes a board entry by being
   quoted.

A published claim that cannot be reconstructed can still be recorded as a
reference bar in [`../../TRACKS.md`](../../TRACKS.md), which is where the
literature-derived bars already live.

## State of the ledger

First real poll on 2026-09-27 with `--days 30`: 105 papers, 54 screened in (15
`strong`, 39 `candidate`), 51 `background`. All 54 screened-in rows carry a human
verdict (8 `relevant`, 7 `uncertain`, 39 `not-relevant`); the 51 background rows
stay `unreviewed` by design. Every parameter in those reasons is an unverified
claim read out of an abstract.

The window is on `updated`, so 47 of the 105 rows are new versions of older
submissions, reaching back to a v4 of a 2016 paper. That is the case sorting by
`submittedDate` would lose.

The strongest lead from that poll is arXiv:2609.30069v1, "Design Principles for
Ultra-High-Rate Quantum Codes", the only screened-in paper whose claimed
parameters are both admissible and undominated: claims `[[90,21]]` d = 11 against
a board best of d = 6 at n <= 90 with k >= 21, `[[140,31]]` d = 15 against
`[[136,34]]` d = 12, and `[[200,43]]` d = 20 against `[[192,43]]` d = 12, all
non-CSS at check weight 10. Nothing has been reconstructed or verified.
