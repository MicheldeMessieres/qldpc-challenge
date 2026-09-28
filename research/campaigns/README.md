# Campaigns

A campaign is a bounded, reproducible search task: what to look for, where to
look, how much may be spent, and when to stop. It is the input to the loop in
[`../AUTORESEARCH.md`](../AUTORESEARCH.md), not a replacement for it, and it is
not a submission mechanism.

```
campaign  →  many experiments  →  many candidates  →  few validated survivors
          →  human review      →  optional PR
```

| Object | What it is | Where it lives |
|---|---|---|
| Campaign | the task: objective, constraints, methods, budget, stopping | `research/campaigns/<id>/campaign.json`, validated by `schema/campaign.schema.json` |
| Experiment | one run: a family, a budget slice, a seed | a row in the ledger |
| Candidate | one packaged code and the gate's verdict on it | staged in `research/candidates/` (gitignored) |
| Artifact | the submission JSON, its verdict, and any `certs/` entry | `codes/` and `certs/`, only after a human submits it |

## Running one

```python
import sys; sys.path[:0] = ["research/kit", "verify"]
from campaign import Ledger, load_campaign, write_summary
from validate_candidate import validate_candidate

camp = load_campaign("research/campaigns/<id>/campaign.json")
led = Ledger(camp)
led.start_experiment("lifted-product", seed=7)
led.spend(cpu_hours=1.5, candidates_screened=250)
led.record_candidate(doc, validate_candidate(doc))   # refused unless passed
led.end_experiment()
if led.stop_reason():
    write_summary(led.summary(), "research/campaigns/<id>/summary.json")
```

`research/campaigns/smoke-bb-72/run.py` is the same thing end to end, small
enough to run in a test.

## Two things a campaign cannot do

**Its constraints are a screening filter, never a claim.** A campaign may
restrict a search to `local-2d-bilayer` at check weight 8. Which track cell a
finished code actually lands in is computed by the verifier from `(H_X, H_Z)`
and the layout. `Campaign.in_scope` answers "is this worth another rung", and
its answer never reaches a submission document. It narrows the ladder and does
not forbid staging: a strong candidate that falls outside the declared window
should still be packaged, validated and reported, and an out-of-scope screen is
not a negative result, because nothing was measured.

**It cannot weaken the gate.** `Ledger.record_candidate` refuses any verdict
without `passed: true`, and `Ledger.best_score` reads the objective off the
recorded survivors, so neither a find nor a `target_reached` stop can rest on
a candidate `verify/validate_candidate.py` did not accept. A campaign never
opens a PR: unattended runs stage for review, and publication follows
`../../AGENTS.md` unchanged.

## Ending one

A campaign owes its ledger and its negative results whether or not it found
anything. Zero submissions is a complete, reportable outcome, and the closed
family is the finding. `summary.json` is the machine-readable half;
`TEMPLATE_report.md` is the human half.

`abandoned` keeps everything a run produced. Stopping early throws nothing
away.

The ledger is held in memory, so a kill loses it. Pass `journal=` and every
experiment is appended to a JSONL file as it closes, which narrows the loss to
the experiment in flight:

```python
from coordination import staging_dir
led = Ledger(camp, journal=f"{staging_dir()}/ledger.jsonl")
...
back = Ledger.from_journal(camp, path)      # everything that had closed
```

One journal per executor. `Ledger.merge` folds two of them into one, keyed by
`(family, seed)`, so the same family at the same seed is counted once and its
budget is not charged twice, and survivors are unioned on the verifier's
fingerprint. That is what turns two executors handed the same campaign file
into one campaign rather than two results a human compares by hand.

`write_summary(led.summary(), ".../summary.json")` still overwrites in place
whenever it is called, and the status it records is `paused` until a stopping
condition fires.

## The run manifest

`summary.json` says what a campaign found. It does not say what produced it:
which code snapshot ran, at what depth, with which seeds. Those lived in a
shell history, so a note quoting "5.3M trials" pointed at nothing a reviewer
could open. `manifest.json` is the other half.

```python
led = Ledger(camp,
             manifest="research/campaigns/<id>/manifest.json",
             params={"trials": 2_000_000, "ladder": [[2000, 12], [20000, 11]],
                     "seeds": [51, 52], "workers": 8})
```

It is rewritten at every experiment boundary, so a kill leaves a manifest for
everything that closed. It records:

| field | why it is there |
|---|---|
| `snapshot` | git HEAD, plus a hash of the working-tree diff and whether there was one. HEAD alone does not identify a run: campaigns are normally run from a tree with edits in it, and two such runs give different numbers from one sha |
| `params` | the depth, ladder, seeds and workers actually invoked, recorded as given rather than re-derived from the campaign file |
| `seeds`, `experiments`, `consumed` | what was run and what it cost |
| `survivor_verdicts` | `(n, k, d)` and a fingerprint of each survivor's gate verdict, enough to detect one whose verdict changed between the run and the PR |
| `logs` | excerpts promoted out of gitignored `*.log` files |

`snapshot` and `params` are also written into `summary.json`, so a summary
separated from its manifest still identifies its own run.

### Logs

`*.log` is gitignored, which is right for a multi-gigabyte trial log and wrong
for the six lines a written claim rests on. Promote those:

```python
led.attach_log(f"{staging_dir()}/lane3.log",
               why="the 5.3M trial count in the note")
```

The excerpt is the tail, capped, with the full file's sha256 and a
`truncated` flag beside it. Say in `why` which claim it supports: an excerpt
nobody can connect to an assertion is weight without evidence.
`verify/check_prose.py` rejects a `*.log` citation and points here.

### When a manifest is required

Any campaign whose numbers appear in `notes/` or `fieldnotes/` commits its
manifest beside the note, and the note cites it. A campaign that submits
nothing does not need one.
