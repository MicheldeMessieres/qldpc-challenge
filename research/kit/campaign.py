"""Campaign definitions: bounded, reproducible search tasks (issue #2219).

A campaign is the INPUT to the autoresearch loop, not a replacement for it and
not a submission mechanism. It says what to look for, where to look, how much
may be spent and when to stop, so that two executors handed the same file are
running the same task and their results can be compared. What comes out is a
ledger and a summary; what does or does not reach the board is still decided by
``verify/validate_candidate.py`` and then by a human.

Two invariants this module will not let a caller break, because both have cost
the board real entries before:

* **Constraints filter a search, they never make a claim.** ``constraints``
  narrows where to look. Which track cell a finished code lands in is computed
  by the verifier from ``(H_X, H_Z)`` and the layout. :meth:`Campaign.in_scope`
  is therefore named for what it does, and its result never reaches a document.
* **A survivor is a validated survivor.** :meth:`Ledger.record_candidate`
  refuses anything whose verdict does not carry ``passed: true``, and
  :meth:`Ledger.best_score` reads the objective off the recorded survivors, so
  neither a summary nor a stopping condition can report a find, or a target
  reached, that the gate did not accept.

    from campaign import load_campaign, Ledger
    c = load_campaign("research/campaigns/<id>/campaign.json")
    led = Ledger(c)
    led.start_experiment("lifted-product", seed=7)
    led.spend(cpu_hours=1.5, candidates_screened=250)
    led.record_candidate(doc, verdict)          # only if verdict["passed"]
    led.end_experiment()
    if led.stop_reason():                        # which condition fired
        json.dump(led.summary(), open(out, "w"), indent=2)
"""
import json
import os
import time
from datetime import datetime, timezone

try:
    import jsonschema
except ImportError:                              # pragma: no cover
    jsonschema = None

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
SCHEMA_PATH = os.path.join(_ROOT, "schema", "campaign.schema.json")
SUMMARY_VERSION = 1
JOURNAL_VERSION = 1

# The metrics :meth:`Campaign.score` computes from a survivor's (n, k, d), and
# therefore the only ones a target_reached condition can ever fire on.
SCORABLE_METRICS = ("kd2_over_n", "distance", "logical_qubits")


class CampaignError(ValueError):
    """A campaign definition that cannot be run as written."""


def _schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_campaign(obj):
    """Validate a campaign object against the schema; raise CampaignError.

    The schema does the structural work (unknown fields, malformed budgets,
    unknown stopping types, unknown family tags). What is checked here is the
    handful of things JSON Schema cannot say about one field in terms of
    another.
    """
    if jsonschema is None:                       # pragma: no cover
        raise CampaignError("jsonschema is required to validate a campaign")
    try:
        jsonschema.Draft202012Validator(_schema()).validate(obj)
    except jsonschema.ValidationError as e:
        where = "/".join(str(p) for p in e.absolute_path) or "(root)"
        raise CampaignError(f"{where}: {e.message}") from None

    c = obj["campaign"]
    for field in ("n", "k"):
        rng = (c.get("constraints") or {}).get(field)
        if rng and rng[0] > rng[1]:
            raise CampaignError(
                f"constraints.{field}: [{rng[0]}, {rng[1]}] is empty; the low "
                "bound is above the high one")
    for cond in c["stopping"]:
        if cond["type"] == "candidates_found" and not cond.get("count"):
            raise CampaignError(
                "stopping candidates_found: needs a count, otherwise nothing "
                "says how many survivors is enough")
        if cond["type"] == "no_progress" and not cond.get("experiments"):
            raise CampaignError(
                "stopping no_progress: needs experiments, otherwise nothing "
                "says how long a dry spell has to be")
        if cond["type"] == "target_reached":
            if "target" not in c["objective"]:
                raise CampaignError(
                    "stopping target_reached: objective.target is not set, so "
                    "there is no target to reach")
            metric = c["objective"]["metric"]
            if metric not in SCORABLE_METRICS:
                raise CampaignError(
                    f"stopping target_reached: objective.metric {metric!r} is "
                    "not computed from a survivor's (n, k, d), so the "
                    "condition could never fire; use one of "
                    f"{', '.join(SCORABLE_METRICS)}")
    return obj


def load_campaign(path):
    """Load and validate a campaign definition from disk."""
    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
    except json.JSONDecodeError as e:
        raise CampaignError(f"{path}: not valid JSON ({e})") from None
    camp = Campaign(validate_campaign(obj), path=path)
    home = os.path.dirname(os.path.abspath(path))
    if os.path.basename(os.path.dirname(home)) == "campaigns" \
            and os.path.basename(home) != camp.id:
        raise CampaignError(
            f"{path}: campaign id {camp.id!r} is not the directory name "
            f"{os.path.basename(home)!r}; a copied definition would file its "
            "ledger under the campaign it was copied from")
    return camp


class Campaign:
    """A validated campaign definition."""

    def __init__(self, obj, path=None):
        self.obj = obj
        self.path = path
        self.c = obj["campaign"]

    # -- identity ---------------------------------------------------------
    @property
    def id(self):
        return self.c["id"]

    @property
    def name(self):
        return self.c["name"]

    @property
    def status(self):
        return self.c.get("status", "draft")

    @property
    def families(self):
        return list((self.c.get("methods") or {}).get("families") or [])

    @property
    def required_outputs(self):
        return list(self.c.get("required_outputs") or [])

    # -- the search space -------------------------------------------------
    def in_scope(self, *, n=None, k=None, d=None, w=None, locality=None):
        """Report whether a candidate is inside the campaign search space.

        A screening filter, and only that. It answers "is this worth spending
        the next rung on", never "which cell does this belong to": the cell is
        the verifier's to compute, from the matrices and the layout.
        """
        con = self.c.get("constraints") or {}
        if n is not None and con.get("n") and not con["n"][0] <= n <= con["n"][1]:
            return False
        if k is not None and con.get("k") and not con["k"][0] <= k <= con["k"][1]:
            return False
        if d is not None and con.get("min_distance") and d < con["min_distance"]:
            return False
        if w is not None and con.get("max_check_weight") \
                and w > con["max_check_weight"]:
            return False
        if locality is not None and con.get("locality"):
            want, order = con["locality"], ("local-2d-single",
                                            "local-2d-bilayer", "unrestricted")
            if locality not in order:
                raise CampaignError(
                    f"unknown locality class {locality!r}; the schema's "
                    f"classes are {', '.join(order)}")
            # the classes nest: a single-layer code satisfies a bilayer ask
            if order.index(locality) > order.index(want):
                return False
        return True

    def score(self, *, n, k, d, geo=None):
        """Compute the objective metric for a candidate, or None."""
        metric = self.c["objective"]["metric"]
        if metric == "kd2_over_n":
            return k * d * d / n
        if metric == "geometric_efficiency":
            return geo
        if metric == "distance":
            return d
        if metric == "logical_qubits":
            return k
        return None


BUDGET_FIELDS = ("cpu_hours", "gpu_hours", "walltime_hours",
                 "candidates_screened")


class Ledger:
    """The running record of one campaign: what was spent, tried and found.

    It is the committed half of the evidence trail, so it names only things a
    reviewer can open: staged candidates live in the gitignored
    ``research/candidates/`` and are recorded by their parameters and verdict,
    never cited as files.

    Pass ``journal=<path>`` and each experiment is appended to a JSONL file as
    it closes, so a kill costs the current experiment rather than the run.
    :meth:`from_journal` reads one back, and :meth:`merge` folds two ledgers of
    the same campaign into one. That last part is what turns "two executors
    handed the same file" from a human comparison exercise into a campaign
    several sessions can run between them.

    One journal per executor. Two processes appending to the same file would
    interleave partial lines once a record outgrows the atomic write size, and
    separate files merge cleanly anyway.
    """

    def __init__(self, campaign, *, journal=None):
        self.campaign = campaign
        self.journal = journal
        self.spent = dict.fromkeys(BUDGET_FIELDS, 0)
        self._t0 = time.monotonic()
        self._walltime_base = 0.0
        self.experiments = []
        self.survivors = []
        self.negative_results = []
        self.frontier_advances = 0
        self._current = None
        self._exp_t0 = None
        self._mark = (0, 0)
        self._dry_streak = 0

    # -- experiments ------------------------------------------------------
    def start_experiment(self, family, *, seed=None, note=""):
        """Begin one run: a family, a budget slice, and a seed."""
        if family not in self.campaign.families and self.campaign.families:
            raise CampaignError(
                f"family {family!r} is not one of this campaign's families "
                f"({', '.join(self.campaign.families)})")
        self._current = {"family": family, "seed": seed, "note": note,
                         "spent": dict.fromkeys(BUDGET_FIELDS, 0),
                         "survivors": 0}
        self._exp_t0 = time.monotonic()
        self._mark = (len(self.survivors), len(self.negative_results))
        return self._current

    def end_experiment(self):
        """Close the current run, fold it into the ledger, and journal it.

        The experiment's own wall time is measured here rather than reported,
        for the same reason the campaign's is: it is the only number a merged
        or replayed ledger can add up, and a cap nothing observes is advisory.
        """
        if self._current is None:
            raise CampaignError("end_experiment without start_experiment")
        exp = self._current
        elapsed = (time.monotonic() - self._exp_t0) / 3600
        exp["spent"]["walltime_hours"] = max(exp["spent"]["walltime_hours"],
                                             elapsed)
        self.experiments.append(exp)
        self._dry_streak = 0 if exp["survivors"] else self._dry_streak + 1
        si, ni = self._mark
        self._append_journal(exp, self.survivors[si:],
                             self.negative_results[ni:])
        self._current = None
        self._exp_t0 = None
        return exp

    # -- the journal ------------------------------------------------------
    def _append_journal(self, exp, survivors, negatives):
        """Append one experiment and what it produced, then force it to disk."""
        if not self.journal:
            return None
        record = {"record_version": JOURNAL_VERSION,
                  "campaign_id": self.campaign.id,
                  "recorded_at": datetime.now(timezone.utc).isoformat(),
                  "experiment": exp,
                  "survivors": list(survivors),
                  "negative_results": list(negatives)}
        parent = os.path.dirname(os.path.abspath(self.journal))
        os.makedirs(parent, exist_ok=True)
        with open(self.journal, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return self.journal

    @classmethod
    def from_journal(cls, campaign, path):
        """Rebuild a ledger from one journal, or several merged.

        What a journal cannot restore is spend recorded outside any
        experiment, since nothing closes to carry it, and the in-flight
        experiment the kill interrupted. Everything that closed is here.
        """
        paths = [path] if isinstance(path, (str, os.PathLike)) else list(path)
        if not paths:
            raise CampaignError("from_journal: no journal given")
        out = None
        for one in paths:
            led = cls(campaign)
            led._replay(one)
            out = led if out is None else out.merge(led)
        return out

    def _replay(self, path):
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                if i == len(lines) - 1:
                    break                        # the tail a kill truncated
                raise CampaignError(
                    f"{path}: line {i + 1} is not valid JSON, and it is not "
                    "the last line, so this is corruption rather than an "
                    "interrupted write") from None
            if rec.get("campaign_id") != self.campaign.id:
                raise CampaignError(
                    f"{path}: journal is for campaign "
                    f"{rec.get('campaign_id')!r}, not {self.campaign.id!r}")
            exp = rec.get("experiment") or {}
            exp.setdefault("spent", dict.fromkeys(BUDGET_FIELDS, 0))
            self.experiments.append(exp)
            self.survivors.extend(rec.get("survivors") or [])
            self.negative_results.extend(rec.get("negative_results") or [])
        self.spent = {f: sum(e["spent"].get(f, 0) for e in self.experiments)
                      for f in BUDGET_FIELDS}
        self._recount()
        return self

    def merge(self, other):
        """Fold another executor's ledger for the same campaign into a new one.

        Experiments are keyed by ``(family, seed)``: the same family at the
        same seed is the same deterministic work, so it is counted once and
        its budget is not charged twice. An experiment with no seed cannot be
        told apart from another, so both copies are kept; that over-counts the
        budget rather than silently discarding work someone paid for.

        Survivors are unioned on the verifier's fingerprint, so one code found
        by two executors is one survivor rather than two. Wall time is the sum
        of the merged experiments' own measured wall times, because two
        executors that ran in parallel each consumed theirs. Neither input
        ledger is modified.
        """
        if other.campaign.id != self.campaign.id:
            raise CampaignError(
                f"merge: {other.campaign.id!r} is a different campaign from "
                f"{self.campaign.id!r}; their budgets and objectives are not "
                "the same task and adding them up would say nothing")
        out = Ledger(self.campaign)
        seen, dropped = set(), []
        for src in (self, other):
            for exp in src.experiments:
                key = (exp.get("family"), exp.get("seed"))
                if exp.get("seed") is not None and key in seen:
                    dropped.append(exp)
                    continue
                seen.add(key)
                out.experiments.append(exp)
        out.spent = {f: self.spent.get(f, 0) + other.spent.get(f, 0)
                     - sum(d["spent"].get(f, 0) for d in dropped)
                     for f in BUDGET_FIELDS}
        keys = set()
        for src in (self, other):
            for row in src.survivors:
                key = row.get("fingerprint") or (
                    row.get("n"), row.get("k"), row.get("d"),
                    tuple(row.get("cell") or ()))
                if key in keys:
                    continue
                keys.add(key)
                out.survivors.append(row)
        for src in (self, other):
            for neg in src.negative_results:
                if neg not in out.negative_results:
                    out.negative_results.append(neg)
        out._recount()
        return out

    def _recount(self):
        """Recompute the derived counters from the rows now held."""
        self.frontier_advances = sum(1 for r in self.survivors
                                     if r.get("advanced_frontier"))
        self._walltime_base = sum(e.get("spent", {}).get("walltime_hours", 0)
                                  for e in self.experiments)
        streak = 0
        for exp in reversed(self.experiments):
            if exp.get("survivors"):
                break
            streak += 1
        self._dry_streak = streak

    def spend(self, **amounts):
        """Record consumption against the budget."""
        for field, amount in amounts.items():
            if field not in BUDGET_FIELDS:
                raise CampaignError(f"unknown budget field {field!r}")
            if amount < 0:
                raise CampaignError(f"{field}: cannot spend a negative amount")
            self.spent[field] += amount
            if self._current is not None:
                self._current["spent"][field] += amount

    def record_candidate(self, doc, verdict, *, advanced_frontier=None):
        """Record a validated survivor.

        ``verdict`` is what ``validate_candidate`` returned. Anything without
        ``passed: true`` is refused rather than recorded, so no summary can
        report a find the gate did not accept.
        """
        if not (verdict or {}).get("passed"):
            raise CampaignError(
                "record_candidate: the verdict does not say passed: true. A "
                "candidate is not a find until the gate accepts it")
        if self._current is None:
            raise CampaignError(
                "record_candidate without start_experiment: a survivor no "
                "experiment accounts for leaves the ledger contradicting "
                "itself about what the budget bought")
        gates = verdict.get("gates") or {}
        novelty = gates.get("novelty") or {}
        if advanced_frontier is None:
            advanced_frontier = bool(novelty.get("board_advancing"))
        row = {
            "n": doc["n"], "k": doc["k"], "d": doc["distance"]["d"],
            # the weight class the verifier computed; the gate does not put a
            # raw max check weight in its verdict
            "weight_class": (verdict.get("candidate") or {}).get("weight_class")
                            or (gates.get("verify") or {}).get("weight_class"),
            "cell": novelty.get("cell"),
            "board_advancing": novelty.get("board_advancing"),
            "fingerprint": (verdict.get("candidate") or {}).get("fingerprint"),
            "advanced_frontier": bool(advanced_frontier),
            "labels": list(verdict.get("labels") or []),
        }
        self.survivors.append(row)
        self._current["survivors"] += 1
        if advanced_frontier:
            self.frontier_advances += 1
        return row

    def record_negative(self, what, detail):
        """Record something that did not work, and why.

        A closed family, a wall, a ladder that collapsed. This is the half of a
        campaign that survives a zero-submission run, and the next searcher
        pays for it twice if it is not written down.
        """
        self.negative_results.append({"what": what, "detail": detail})

    # -- stopping ---------------------------------------------------------
    def consumed(self):
        """Report what has been spent, with wall time read off the clock.

        ``walltime_hours`` is measured rather than reported: a cap nothing
        observes is advisory, and the budget object exists to be enforceable.
        """
        out = dict(self.spent)
        measured = self._walltime_base + (time.monotonic() - self._t0) / 3600
        out["walltime_hours"] = max(out["walltime_hours"], measured)
        return out

    def budget_exhausted(self):
        """Name the first budget field that has been reached, or None."""
        budget, spent = self.campaign.c["budget"], self.consumed()
        for field, cap in budget.items():
            if spent.get(field, 0) >= cap:
                return field
        return None

    def best_score(self):
        """Return the best objective over the validated survivors, or None.

        Read off the recorded survivor rows and nowhere else, so a stopping
        condition on the objective cannot fire on a screening number for a
        candidate the gate went on to refuse.
        """
        scores = [s for s in (self.campaign.score(n=r["n"], k=r["k"], d=r["d"])
                              for r in self.survivors) if s is not None]
        if not scores:
            return None
        up = self.campaign.c["objective"]["direction"] == "maximize"
        return max(scores) if up else min(scores)

    def stop_reason(self):
        """Which stopping condition has fired, as (type, detail), or None."""
        for cond in self.campaign.c["stopping"]:
            kind = cond["type"]
            if kind == "budget_exhausted":
                field = self.budget_exhausted()
                if field:
                    cap = self.campaign.c["budget"][field]
                    spent = self.consumed()[field]
                    return kind, f"{field} reached {spent:g} of {cap:g}"
            elif kind == "frontier_advance" and self.frontier_advances:
                return kind, f"{self.frontier_advances} validated frontier advance(s)"
            elif kind == "candidates_found" and len(self.survivors) >= cond["count"]:
                return kind, f"{len(self.survivors)} validated survivors"
            elif kind == "no_progress" and self._dry_streak >= cond["experiments"]:
                return kind, f"{self._dry_streak} experiments with no survivor"
            elif kind == "target_reached":
                best = self.best_score()
                if best is None:
                    continue
                target = self.campaign.c["objective"]["target"]
                up = self.campaign.c["objective"]["direction"] == "maximize"
                if (best >= target) if up else (best <= target):
                    return kind, f"objective reached {best:g} against {target:g}"
        return None

    # -- output -----------------------------------------------------------
    def summary(self, *, status=None, report=None):
        """Build the machine-readable campaign summary.

        Written beside the definition when a campaign ends. Zero survivors is a
        complete, reportable outcome: the ledger and the negative results are
        the finding in that case. ``status`` defaults to what happened, so an
        interrupted run does not file itself as completed.
        """
        fired = self.stop_reason()
        budget = self.campaign.c["budget"]
        spent = self.consumed()
        shown = [f for f in BUDGET_FIELDS if spent[f] and
                 (f != "walltime_hours" or f in budget)]
        if status is None:
            status = "completed" if fired else "paused"
        return {
            "summary_version": SUMMARY_VERSION,
            "campaign_id": self.campaign.id,
            "campaign_name": self.campaign.name,
            "status": status,
            "objective": self.campaign.c["objective"],
            "stopped_by": {"type": fired[0], "detail": fired[1]} if fired
                          else {"type": None, "detail": "still running"},
            "budget": {"declared": budget,
                       "consumed": {f: round(spent[f], 3) for f in shown},
                       "remaining": {f: round(budget[f] - spent.get(f, 0), 3)
                                     for f in budget}},
            "experiments": self.experiments,
            "survivors": self.survivors,
            "frontier_advances": self.frontier_advances,
            "negative_results": self.negative_results,
            "required_outputs": self.campaign.required_outputs,
            "report": report,
            "authority": "candidates listed here passed "
                         "verify/validate_candidate.py; nothing here is a "
                         "board entry until a human reviews and submits it",
        }


def write_summary(summary, path):
    """Write a campaign summary, creating its directory."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    return path
