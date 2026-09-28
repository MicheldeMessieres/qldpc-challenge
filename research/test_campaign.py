"""Tests for campaign definitions and their ledger (issue #2219).

Two properties matter more than the rest and are tested hardest, because both
protect the board rather than the code: a campaign's constraints are a
screening filter and never a claim about which track cell anything is in, and a
survivor is only a survivor once the gate has said so. Everything else here is
the schema doing its job, which is worth pinning because a campaign that
validates loosely is a task two executors can read differently.
"""
import copy
import json
import os
import sys
import time

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_HERE, "kit"))

from campaign import (  # noqa: E402
    Campaign,
    CampaignError,
    Ledger,
    load_campaign,
    validate_campaign,
    write_summary,
)

GOOD = {
    "campaign": {
        "schema_version": 1,
        "id": "test-campaign",
        "name": "A campaign for the tests",
        "objective": {"metric": "kd2_over_n", "direction": "maximize"},
        "constraints": {"max_check_weight": 8, "n": [100, 400],
                        "locality": "local-2d-bilayer"},
        "methods": {"families": ["bivariate-bicycle"]},
        "budget": {"cpu_hours": 10},
        "stopping": [{"type": "budget_exhausted"}],
    }
}


def camp(**over):
    obj = copy.deepcopy(GOOD)
    obj["campaign"].update(over)
    return obj


def passed_verdict(n=200, k=8, d=12, wc="weight-6", advancing=True):
    """Build the verdict shape verify/validate_candidate.py actually returns.

    Its ``candidate`` block carries the verifier's weight and locality CLASSES
    and no raw max check weight, so a ledger that reads one gets None.
    """
    return {
        "passed": True,
        "candidate": {"n": n, "k": k, "d": d, "family": "bivariate-bicycle",
                      "weight_class": wc, "locality_class": "unrestricted",
                      "fingerprint": "abc123", "signature": "def456"},
        "gates": {"verify": {"ok": True, "failed_checks": [],
                             "weight_class": wc,
                             "locality_class": "unrestricted"},
                  "novelty": {"board_advancing": advancing,
                              "cell": ["weight-6", "unrestricted"]}},
        "labels": ["advances the weight-6 x unrestricted board"],
    }


def doc(n=200, k=8, d=12):
    return {"n": n, "k": k, "distance": {"d": d}}


# -- the schema -----------------------------------------------------------

def test_a_valid_campaign_loads():
    c = Campaign(validate_campaign(camp()))
    assert c.id == "test-campaign" and c.families == ["bivariate-bicycle"]


def test_an_unknown_field_is_rejected():
    """A typo must not become a silently ignored instruction."""
    with pytest.raises(CampaignError, match="Additional properties|not allowed"):
        validate_campaign(camp(budgett={"cpu_hours": 1}))


def test_an_unknown_family_tag_is_rejected():
    """The Layer-2 vocabulary is shared with the board; a typo cannot match."""
    with pytest.raises(CampaignError, match="methods/families"):
        validate_campaign(camp(methods={"families": ["bivariate-biycle"]}))


def test_an_unknown_stopping_type_is_rejected():
    with pytest.raises(CampaignError, match="stopping"):
        validate_campaign(camp(stopping=[{"type": "when_i_feel_like_it"}]))


@pytest.mark.parametrize("budget", [{}, {"cpu_hours": 0}, {"cpu_hours": -5},
                                    {"cpu_hours": 1, "wall_hours": 2}])
def test_a_malformed_budget_is_rejected(budget):
    """No budget, a zero budget and a negative one are all unbounded."""
    with pytest.raises(CampaignError):
        validate_campaign(camp(budget=budget))


def test_an_empty_blocklength_range_is_rejected():
    with pytest.raises(CampaignError, match="is empty"):
        validate_campaign(camp(constraints={"n": [400, 100]}))


def test_a_stopping_condition_missing_its_number_is_rejected():
    with pytest.raises(CampaignError, match="needs a count"):
        validate_campaign(camp(stopping=[{"type": "candidates_found"}]))
    with pytest.raises(CampaignError, match="needs experiments"):
        validate_campaign(camp(stopping=[{"type": "no_progress"}]))


def test_target_reached_without_a_target_is_rejected():
    with pytest.raises(CampaignError, match="no target to reach"):
        validate_campaign(camp(stopping=[{"type": "target_reached"}]))


def test_target_reached_on_a_metric_the_ledger_cannot_score_is_rejected():
    """A stopping condition that can never fire is worse than none at all."""
    with pytest.raises(CampaignError, match="could never fire"):
        validate_campaign(camp(
            objective={"metric": "frontier_entries", "direction": "maximize",
                       "target": 3},
            stopping=[{"type": "target_reached"}]))


def test_an_id_that_is_not_its_directory_is_rejected(tmp_path):
    """A copied definition must not file its ledger under the original."""
    home = tmp_path / "campaigns" / "copied-from-somewhere"
    home.mkdir(parents=True)
    p = home / "campaign.json"
    p.write_text(json.dumps(GOOD))
    with pytest.raises(CampaignError, match="not the directory name"):
        load_campaign(str(p))


def test_a_bad_schema_version_is_rejected():
    with pytest.raises(CampaignError):
        validate_campaign(camp(schema_version=2))


# -- the search space -----------------------------------------------------

def test_constraints_filter_the_search_and_nothing_else():
    """in_scope answers 'is this worth another rung', never 'which cell'.

    The cell is computed by the verifier from the matrices and the layout, so
    nothing this method returns may reach a submission document.
    """
    c = Campaign(validate_campaign(camp()))
    assert c.in_scope(n=200, w=8)
    assert not c.in_scope(n=500)
    assert not c.in_scope(w=12)
    # the locality classes nest: a single-layer code satisfies a bilayer ask
    assert c.in_scope(locality="local-2d-single")
    assert not c.in_scope(locality="unrestricted")
    # an unconstrained axis never excludes anything
    assert c.in_scope(k=10 ** 6)
    # a locality string outside the schema's classes says so
    with pytest.raises(CampaignError, match="unknown locality class"):
        c.in_scope(locality="2D local")


def test_the_objective_metric_is_computed_from_the_candidate():
    c = Campaign(validate_campaign(camp()))
    assert c.score(n=200, k=8, d=10) == 4.0


# -- the ledger -----------------------------------------------------------

def test_a_candidate_the_gate_did_not_pass_is_refused():
    """The single most important refusal in this module."""
    led = Ledger(Campaign(validate_campaign(camp())))
    with pytest.raises(CampaignError, match="passed: true"):
        led.record_candidate(doc(), {"passed": False, "labels": ["refuted"]})
    with pytest.raises(CampaignError, match="passed: true"):
        led.record_candidate(doc(), {})
    assert led.survivors == []


def test_a_survivor_outside_an_experiment_is_refused():
    """A survivor no experiment accounts for makes the ledger self-contradicting."""
    led = Ledger(Campaign(validate_campaign(camp())))
    with pytest.raises(CampaignError, match="without start_experiment"):
        led.record_candidate(doc(), passed_verdict())


def test_the_survivor_row_carries_the_verifier_s_weight_class():
    led = Ledger(Campaign(validate_campaign(camp())))
    led.start_experiment("bivariate-bicycle")
    row = led.record_candidate(doc(), passed_verdict())
    assert row["weight_class"] == "weight-6"


def test_a_family_outside_the_campaign_is_refused():
    led = Ledger(Campaign(validate_campaign(camp())))
    with pytest.raises(CampaignError, match="not one of this campaign"):
        led.start_experiment("quantum-tanner")


def test_spending_accrues_to_the_campaign_and_the_experiment():
    led = Ledger(Campaign(validate_campaign(camp())))
    led.start_experiment("bivariate-bicycle", seed=1)
    led.spend(cpu_hours=3)
    exp = led.end_experiment()
    assert led.spent["cpu_hours"] == 3 and exp["spent"]["cpu_hours"] == 3
    with pytest.raises(CampaignError, match="unknown budget field"):
        led.spend(magic_hours=1)
    with pytest.raises(CampaignError, match="negative"):
        led.spend(cpu_hours=-1)


def test_budget_exhaustion_fires_and_names_the_field():
    led = Ledger(Campaign(validate_campaign(camp())))
    assert led.stop_reason() is None
    led.spend(cpu_hours=10)
    kind, detail = led.stop_reason()
    assert kind == "budget_exhausted" and "cpu_hours" in detail


def test_a_frontier_advance_fires_when_asked_for():
    c = Campaign(validate_campaign(camp(
        stopping=[{"type": "frontier_advance"}, {"type": "budget_exhausted"}])))
    led = Ledger(c)
    led.start_experiment("bivariate-bicycle")
    led.record_candidate(doc(), passed_verdict(advancing=True))
    led.end_experiment()
    assert led.stop_reason()[0] == "frontier_advance"


def test_a_dry_spell_fires_no_progress():
    c = Campaign(validate_campaign(camp(
        stopping=[{"type": "no_progress", "experiments": 2}])))
    led = Ledger(c)
    for _ in range(2):
        led.start_experiment("bivariate-bicycle")
        led.record_negative("wall", "every draw screened above the cap")
        led.end_experiment()
    kind, detail = led.stop_reason()
    assert kind == "no_progress" and "2 experiments" in detail


def test_a_survivor_resets_the_dry_spell():
    c = Campaign(validate_campaign(camp(
        stopping=[{"type": "no_progress", "experiments": 2}])))
    led = Ledger(c)
    led.start_experiment("bivariate-bicycle")
    led.end_experiment()                      # dry
    led.start_experiment("bivariate-bicycle")
    led.record_candidate(doc(), passed_verdict(advancing=False))
    led.end_experiment()                      # not dry
    assert led.stop_reason() is None


def _with_survivor(c, **candidate):
    led = Ledger(c)
    led.start_experiment("bivariate-bicycle")
    led.record_candidate(doc(**candidate), passed_verdict(advancing=False))
    led.end_experiment()
    return led


def test_the_target_is_read_in_the_objective_direction():
    up = Campaign(validate_campaign(camp(
        objective={"metric": "kd2_over_n", "direction": "maximize",
                   "target": 100},
        stopping=[{"type": "target_reached"}])))
    assert _with_survivor(up, n=200, k=8, d=12).stop_reason() is None
    assert _with_survivor(up, n=100, k=10, d=32).stop_reason()[0] \
        == "target_reached"
    # no current metric is naturally minimized; the comparison still honours it
    down = Campaign(validate_campaign(camp(
        objective={"metric": "distance", "direction": "minimize", "target": 4},
        stopping=[{"type": "target_reached"}])))
    assert _with_survivor(down, d=5).stop_reason() is None
    assert _with_survivor(down, d=4).stop_reason()[0] == "target_reached"


def test_the_target_cannot_be_reached_by_a_candidate_the_gate_refused():
    """The refusal that the shipped smoke campaign exercises end to end.

    A screening score for a code the gate went on to reject must not end a
    campaign, and must not appear in its summary as an objective met.
    """
    c = Campaign(validate_campaign(camp(
        objective={"metric": "kd2_over_n", "direction": "maximize",
                   "target": 6},
        stopping=[{"type": "target_reached"}, {"type": "budget_exhausted"}])))
    led = Ledger(c)
    led.start_experiment("bivariate-bicycle")
    with pytest.raises(CampaignError):
        led.record_candidate(doc(n=72, k=12, d=6),          # kd^2/n = 6
                             {"passed": False, "labels": ["duplicate"]})
    led.record_negative("gate rejected", "duplicate of a board entry")
    led.end_experiment()
    assert led.best_score() is None
    assert led.stop_reason() is None
    s = led.summary()
    assert s["stopped_by"]["type"] is None and s["status"] == "paused"


def test_wall_time_is_measured_rather_than_reported():
    """A cap nothing observes is advisory; budget_exhausted must see the clock."""
    c = Campaign(validate_campaign(camp(budget={"walltime_hours": 1e-9})))
    led = Ledger(c)
    # the cap is 3.6 us, which two method calls do not reliably outlast; sleep
    # past it so the assertion tests that the clock is read, not how long the
    # interpreter took to get here
    time.sleep(0.01)
    assert led.consumed()["walltime_hours"] > 0
    assert led.budget_exhausted() == "walltime_hours"
    assert led.stop_reason()[0] == "budget_exhausted"


# -- the summary ----------------------------------------------------------

def test_the_summary_records_what_was_spent_and_what_stopped_it():
    led = Ledger(Campaign(validate_campaign(camp())))
    led.start_experiment("bivariate-bicycle", seed=3)
    led.spend(cpu_hours=10)
    led.record_candidate(doc(), passed_verdict())
    led.end_experiment()
    s = led.summary()
    assert s["summary_version"] == 1 and s["campaign_id"] == "test-campaign"
    assert s["status"] == "completed"
    assert s["stopped_by"]["type"] == "budget_exhausted"
    assert s["budget"]["consumed"]["cpu_hours"] == 10
    assert s["budget"]["remaining"]["cpu_hours"] == 0
    assert len(s["experiments"]) == 1 and len(s["survivors"]) == 1
    assert s["survivors"][0]["cell"] == ["weight-6", "unrestricted"]
    assert "board entry until a human reviews" in s["authority"]


def test_a_campaign_with_no_submission_still_reports():
    """Zero survivors is a complete outcome, not a failure to report."""
    led = Ledger(Campaign(validate_campaign(camp())))
    led.start_experiment("bivariate-bicycle")
    led.record_negative("closed family",
                        "every draw collapsed under the quotient lift")
    led.spend(cpu_hours=10)
    led.end_experiment()
    s = led.summary()
    assert s["status"] == "completed"
    assert s["survivors"] == [] and s["frontier_advances"] == 0
    assert s["negative_results"][0]["what"] == "closed family"
    assert s["stopped_by"]["type"] == "budget_exhausted"


def test_an_interrupted_run_does_not_file_itself_as_completed():
    led = Ledger(Campaign(validate_campaign(camp())))
    led.start_experiment("bivariate-bicycle")
    led.spend(cpu_hours=1)
    led.end_experiment()
    assert led.summary()["status"] == "paused"


def test_the_summary_round_trips_through_disk(tmp_path):
    led = Ledger(Campaign(validate_campaign(camp())))
    out = write_summary(led.summary(status="abandoned"),
                        str(tmp_path / "sub" / "summary.json"))
    assert json.load(open(out))["status"] == "abandoned"


# -- the shipped definitions ---------------------------------------------

@pytest.mark.parametrize("cid", ["w8-2dlocal-n700-1000", "smoke-bb-72"])
def test_the_committed_campaigns_validate(cid):
    """A shipped example that does not load is worse than no example."""
    c = load_campaign(os.path.join(_ROOT, "research", "campaigns", cid,
                                   "campaign.json"))
    assert c.id == cid and c.required_outputs


def test_a_definition_that_is_not_json_says_so(tmp_path):
    p = tmp_path / "campaign.json"
    p.write_text("{not json")
    with pytest.raises(CampaignError, match="not valid JSON"):
        load_campaign(str(p))


# -- the journal and the merge (issue #2314) ------------------------------

def survivor_verdict(fingerprint, **over):
    v = passed_verdict(**over)
    v["candidate"]["fingerprint"] = fingerprint
    return v


def run_one(journal, family="bivariate-bicycle", *, seed, cpu_hours=1,
            fingerprints=(), negatives=()):
    """Run one experiment of the shared campaign and journal it."""
    led = Ledger(Campaign(validate_campaign(camp())), journal=str(journal))
    led.start_experiment(family, seed=seed)
    led.spend(cpu_hours=cpu_hours)
    for fp in fingerprints:
        led.record_candidate(doc(), survivor_verdict(fp))
    for what, detail in negatives:
        led.record_negative(what, detail)
    led.end_experiment()
    return led


def test_each_closed_experiment_is_journaled_as_it_closes(tmp_path):
    """A kill then costs the experiment in flight, not the whole run."""
    j = tmp_path / "ledger.jsonl"
    led = Ledger(Campaign(validate_campaign(camp())), journal=str(j))
    led.start_experiment("bivariate-bicycle", seed=1)
    led.spend(cpu_hours=2)
    assert not j.exists()                        # nothing is written mid-run
    led.end_experiment()
    led.start_experiment("bivariate-bicycle", seed=2)
    led.record_candidate(doc(), passed_verdict())
    led.end_experiment()
    lines = j.read_text().strip().split("\n")
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["campaign_id"] == "test-campaign"
    assert first["experiment"]["seed"] == 1 and first["survivors"] == []
    assert json.loads(lines[1])["survivors"][0]["cell"] == \
        ["weight-6", "unrestricted"]


def test_a_journal_replays_into_the_ledger_it_came_from(tmp_path):
    j = tmp_path / "ledger.jsonl"
    run_one(j, seed=1, cpu_hours=4, fingerprints=("fp-a",),
            negatives=[("closed family", "every draw collapsed")])
    back = Ledger.from_journal(Campaign(validate_campaign(camp())), str(j))
    assert back.consumed()["cpu_hours"] == 4
    assert [s["fingerprint"] for s in back.survivors] == ["fp-a"]
    assert back.negative_results[0]["what"] == "closed family"
    assert back.frontier_advances == 1


def test_a_truncated_last_line_loses_only_the_tail(tmp_path):
    j = tmp_path / "ledger.jsonl"
    run_one(j, seed=1, cpu_hours=4, fingerprints=("fp-a",))
    with open(j, "a") as f:
        f.write('{"record_version": 1, "campaign_id": "test-camp')
    back = Ledger.from_journal(Campaign(validate_campaign(camp())), str(j))
    assert len(back.experiments) == 1 and back.consumed()["cpu_hours"] == 4


def test_a_corrupt_line_in_the_middle_is_not_quietly_skipped(tmp_path):
    j = tmp_path / "ledger.jsonl"
    run_one(j, seed=1)
    with open(j, "a") as f:
        f.write("{not json\n")
    run_one(j, seed=2)
    with pytest.raises(CampaignError, match="not the last line"):
        Ledger.from_journal(Campaign(validate_campaign(camp())), str(j))


def test_a_journal_for_another_campaign_is_refused(tmp_path):
    j = tmp_path / "ledger.jsonl"
    run_one(j, seed=1)
    other = Campaign(validate_campaign(camp(id="some-other-campaign")))
    with pytest.raises(CampaignError, match="journal is for campaign"):
        Ledger.from_journal(other, str(j))


def test_two_executors_of_the_same_campaign_merge(tmp_path):
    a = run_one(tmp_path / "a.jsonl", seed=1, cpu_hours=3,
                fingerprints=("fp-a",))
    b = run_one(tmp_path / "b.jsonl", seed=2, cpu_hours=5,
                fingerprints=("fp-b",),
                negatives=[("wall", "nothing under weight 8")])
    both = a.merge(b)
    assert len(both.experiments) == 2
    assert both.consumed()["cpu_hours"] == 8
    assert sorted(s["fingerprint"] for s in both.survivors) == ["fp-a", "fp-b"]
    assert both.negative_results[0]["what"] == "wall"
    assert both.frontier_advances == 2
    assert len(a.experiments) == 1 and len(b.experiments) == 1


def test_the_same_seed_is_the_same_work_and_is_charged_once(tmp_path):
    """Replicated execution is the point; paying twice for it is not."""
    a = run_one(tmp_path / "a.jsonl", seed=7, cpu_hours=3,
                fingerprints=("fp-a",))
    b = run_one(tmp_path / "b.jsonl", seed=7, cpu_hours=3,
                fingerprints=("fp-a",))
    both = a.merge(b)
    assert len(both.experiments) == 1
    assert both.consumed()["cpu_hours"] == 3
    assert len(both.survivors) == 1 and both.frontier_advances == 1


def test_an_experiment_with_no_seed_cannot_be_deduplicated(tmp_path):
    """Nothing tells the two apart, so over-count rather than discard work."""
    a = run_one(tmp_path / "a.jsonl", seed=None, cpu_hours=3)
    b = run_one(tmp_path / "b.jsonl", seed=None, cpu_hours=3)
    both = a.merge(b)
    assert len(both.experiments) == 2 and both.consumed()["cpu_hours"] == 6


def test_merging_a_different_campaign_is_refused(tmp_path):
    a = run_one(tmp_path / "a.jsonl", seed=1)
    other = Ledger(Campaign(validate_campaign(camp(id="some-other-campaign"))))
    with pytest.raises(CampaignError, match="different campaign"):
        a.merge(other)


def test_a_merged_ledger_stops_on_the_shared_budget(tmp_path):
    """The budget is the campaign's, not each executor's."""
    a = run_one(tmp_path / "a.jsonl", seed=1, cpu_hours=6)
    b = run_one(tmp_path / "b.jsonl", seed=2, cpu_hours=6)
    assert a.stop_reason() is None and b.stop_reason() is None
    kind, detail = a.merge(b).stop_reason()
    assert kind == "budget_exhausted" and "cpu_hours" in detail


def test_a_merged_ledger_summarizes_like_any_other(tmp_path):
    a = run_one(tmp_path / "a.jsonl", seed=1, cpu_hours=5,
                fingerprints=("fp-a",))
    b = run_one(tmp_path / "b.jsonl", seed=2, cpu_hours=5,
                fingerprints=("fp-b",))
    s = a.merge(b).summary()
    assert s["budget"]["consumed"]["cpu_hours"] == 10
    assert len(s["survivors"]) == 2 and s["frontier_advances"] == 2
    assert "board entry until a human reviews" in s["authority"]


def test_several_journals_load_as_one_ledger(tmp_path):
    run_one(tmp_path / "a.jsonl", seed=1, cpu_hours=2, fingerprints=("fp-a",))
    run_one(tmp_path / "b.jsonl", seed=2, cpu_hours=2, fingerprints=("fp-b",))
    both = Ledger.from_journal(Campaign(validate_campaign(camp())),
                               [str(tmp_path / "a.jsonl"),
                                str(tmp_path / "b.jsonl")])
    assert len(both.experiments) == 2 and both.consumed()["cpu_hours"] == 4
    assert len(both.survivors) == 2


def test_a_ledger_with_no_journal_writes_nothing(tmp_path):
    led = Ledger(Campaign(validate_campaign(camp())))
    led.start_experiment("bivariate-bicycle", seed=1)
    led.end_experiment()
    assert list(tmp_path.iterdir()) == []
