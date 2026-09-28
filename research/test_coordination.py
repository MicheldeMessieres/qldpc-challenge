"""Tests for the coordination primitives (issue #2314).

Two properties are worth more than the rest and are tested hardest, because
both are about not losing something expensive. A staging write never destroys
another session's witness, and the verdict cache never serves an answer the
gate would not give right now: not after the validator changed, not after the
board changed, and not for a document that would fail the schema. A cache that
can produce a pass the gate did not is worse than no cache at all, so the
staleness conditions are pinned here one at a time.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "kit"))

from coordination import (  # noqa: E402
    RUN_ID_ENV,
    CandidateCollision,
    VerdictCache,
    board_token,
    content_digest,
    holds_same_candidate,
    run_id,
    staging_dir,
    unique_path,
    validate_cached,
    validator_sha256,
)
from submit import save_submission  # noqa: E402


def candidate(**over):
    """A schema-valid [[4,2,2]] document: the smallest thing the gate accepts."""
    doc = {
        "schema_version": "0.1",
        "name": "[[4,2,2]] coordination test code",
        "code_type": "CSS",
        "n": 4,
        "k": 2,
        "checks": {"X": [[0, 1, 2, 3]], "Z": [[0, 1, 2, 3]]},
        "distance": {
            "d": 2,
            "X": {"value": 2, "confidence": "upper_bound", "witness": [0, 1]},
            "Z": {"value": 2, "confidence": "upper_bound", "witness": [0, 2]},
        },
        "provenance": {"authors": ["@tester"], "construction": "a test fixture",
                       "date": "2026-09-28", "references": [], "notes": ""},
    }
    doc.update(over)
    return doc


def stamped(passed=True, **over):
    """A verdict shaped like the gate's, carrying the real source stamp."""
    v = {"passed": passed,
         "candidate": {"n": 4, "k": 2, "d": 2, "fingerprint": "abc123"},
         "gates": {"novelty": {"board_advancing": False}},
         "labels": [],
         "validator": {"source_sha256": validator_sha256(), "seed": 7}}
    v.update(over)
    return v


def cache_at(tmp_path, board=None):
    return VerdictCache(root=str(tmp_path / "verdicts"),
                        codes_dir=str(board or tmp_path / "codes"))


# -- run identity and staging ---------------------------------------------

def test_a_run_id_is_a_usable_directory_name(monkeypatch):
    monkeypatch.delenv(RUN_ID_ENV, raising=False)
    rid = run_id()
    assert str(os.getpid()) in rid
    assert os.sep not in rid and "/" not in rid and rid == rid.strip()


def test_a_run_id_can_be_pinned_by_the_harness(monkeypatch):
    monkeypatch.setenv(RUN_ID_ENV, "pod 3/session:1")
    assert run_id() == "pod-3-session-1"


def test_two_runs_stage_into_separate_directories(tmp_path):
    a = staging_dir("run-a", root=str(tmp_path))
    b = staging_dir("run-b", root=str(tmp_path))
    assert a != b and os.path.isdir(a) and os.path.isdir(b)
    assert os.path.basename(a) == "run-a"


# -- content addressing ---------------------------------------------------

def test_the_digest_ignores_who_packaged_a_candidate():
    """Two sessions that find the same code must land on one cache entry."""
    a = candidate()
    b = candidate(name="a different name")
    b["provenance"] = {"authors": ["@someone-else"], "construction": "elsewhere",
                       "date": "2026-01-01", "references": ["arXiv:1234.5678"],
                       "notes": "found independently"}
    assert content_digest(a) == content_digest(b)


@pytest.mark.parametrize("field,value", [
    ("n", 5),
    ("k", 1),
    ("family", "bivariate-bicycle"),
])
def test_the_digest_follows_what_the_gate_reads(field, value):
    assert content_digest(candidate()) != content_digest(candidate(**{field: value}))


def test_the_digest_follows_the_witness():
    """The witness is the expensive part; a different one is a different code."""
    other = candidate()
    other["distance"]["X"]["witness"] = [2, 3]
    assert content_digest(candidate()) != content_digest(other)


def test_a_model_claim_is_inside_the_key():
    """provenance.model is checked by value, so it cannot be keyed away."""
    named = candidate()
    named["provenance"]["model"] = "Claude Opus 5"
    assert content_digest(candidate()) != content_digest(named)


# -- staging without clobbering -------------------------------------------

def test_a_free_path_is_used_as_written(tmp_path):
    p = str(tmp_path / "4-2-2.json")
    assert unique_path(p, candidate()) == p


def test_re_saving_the_same_candidate_needs_no_new_name(tmp_path):
    p = str(tmp_path / "4-2-2.json")
    save_submission(candidate(), p)
    assert unique_path(p, candidate()) == p
    assert holds_same_candidate(p, candidate())


def test_a_second_candidate_gets_its_own_name(tmp_path):
    p = str(tmp_path / "4-2-2.json")
    save_submission(candidate(), p)
    other = candidate(k=1)
    second = unique_path(p, other)
    assert second != p and second.endswith(".json")
    save_submission(other, second)
    third = unique_path(p, candidate(k=3))
    assert third not in (p, second)


def test_saving_over_another_session_s_candidate_is_refused(tmp_path):
    """The witness in the file on disk cost the compute; do not delete it."""
    p = str(tmp_path / "4-2-2.json")
    save_submission(candidate(), p)
    before = open(p).read()
    with pytest.raises(CandidateCollision, match="already holds a different"):
        save_submission(candidate(k=1), p)
    assert open(p).read() == before


def test_saving_the_same_candidate_again_is_not_a_collision(tmp_path):
    p = str(tmp_path / "4-2-2.json")
    save_submission(candidate(), p)
    assert save_submission(candidate(name="renamed"), p) == []


def test_a_caller_that_means_to_replace_still_can(tmp_path):
    p = str(tmp_path / "4-2-2.json")
    save_submission(candidate(), p)
    save_submission(candidate(k=1), p, on_collision="overwrite")
    assert json.load(open(p))["k"] == 1
    with pytest.raises(ValueError, match="unknown mode"):
        save_submission(candidate(), p, on_collision="clobber")


# -- the verdict cache ----------------------------------------------------

def test_a_stored_verdict_comes_back_unchanged(tmp_path):
    c = cache_at(tmp_path)
    assert c.get(candidate()) is None
    c.put(candidate(), stamped())
    assert c.get(candidate()) == stamped()


def test_a_verdict_is_reused_for_the_same_code_packaged_by_someone_else(tmp_path):
    c = cache_at(tmp_path)
    c.put(candidate(), stamped())
    mine = candidate(name="my own name")
    mine["provenance"] = {"authors": ["@me"], "construction": "my own search",
                          "date": "2026-09-30"}
    assert c.get(mine) == stamped()


def test_a_verdict_without_the_gate_s_stamp_is_refused(tmp_path):
    """Otherwise the cache is a place to plant a pass, not a cache."""
    c = cache_at(tmp_path)
    assert c.put(candidate(), {"passed": True}) is None
    assert c.put(candidate(), {"passed": True,
                              "validator": {"source_sha256": "0" * 64}}) is None
    assert c.get(candidate()) is None


def test_a_verdict_that_skipped_the_refutation_is_not_kept(tmp_path):
    c = cache_at(tmp_path)
    assert c.put(candidate(), stamped(), refuted=False) is None
    assert c.get(candidate()) is None


def test_a_failing_verdict_is_cached_too(tmp_path):
    """A refusal cost the same compute as a pass and is worth as much."""
    c = cache_at(tmp_path)
    c.put(candidate(), stamped(passed=False))
    assert c.get(candidate())["passed"] is False


def test_a_changed_board_retires_the_entry(tmp_path):
    """dedup and novelty are claims about codes/, not about the candidate."""
    board = tmp_path / "codes"
    board.mkdir()
    (board / "a.json").write_text('{"n": 1}')
    cache_at(tmp_path, board).put(candidate(), stamped())
    assert cache_at(tmp_path, board).get(candidate()) == stamped()
    (board / "b.json").write_text('{"n": 2}')
    assert cache_at(tmp_path, board).get(candidate()) is None


def test_a_changed_validator_retires_the_entry(tmp_path):
    c = cache_at(tmp_path)
    c.put(candidate(), stamped())
    path = c.path_for(candidate())
    entry = json.load(open(path))
    entry["validator_sha256"] = "0" * 64
    open(path, "w").write(json.dumps(entry))
    assert cache_at(tmp_path).get(candidate()) is None


def test_a_document_that_would_fail_the_schema_is_never_served(tmp_path):
    """The key drops the date, so the schema check has to catch a bad one."""
    c = cache_at(tmp_path)
    c.put(candidate(), stamped())
    bad = candidate()
    bad["provenance"]["date"] = "the third of never"
    assert content_digest(bad) == content_digest(candidate())
    assert c.get(bad) is None


def test_an_unreadable_entry_is_a_miss_and_not_a_crash(tmp_path):
    c = cache_at(tmp_path)
    c.put(candidate(), stamped())
    open(c.path_for(candidate()), "w").write('{"entry_version": 1, "verdi')
    assert c.get(candidate()) is None


def test_the_board_token_moves_with_the_bytes(tmp_path):
    board = tmp_path / "codes"
    board.mkdir()
    (board / "a.json").write_text('{"n": 1}')
    first = board_token(str(board))
    (board / "a.json").write_text('{"n": 2}')
    assert board_token(str(board)) != first
    assert board_token(str(tmp_path / "nowhere")) == "no-board"


# -- the wrapper ----------------------------------------------------------

def test_the_gate_runs_once_and_the_second_call_reuses_it(tmp_path):
    calls = []

    def fake_gate(doc, *, seed=None, refute=True):
        calls.append(seed)
        return stamped()

    c = cache_at(tmp_path)
    first, reused = validate_cached(candidate(), cache=c, validator=fake_gate)
    assert first == stamped() and reused is False
    second, reused = validate_cached(candidate(), cache=c, validator=fake_gate)
    assert second == stamped() and reused is True
    assert len(calls) == 1


def test_a_shallow_run_neither_reads_nor_writes_the_cache(tmp_path):
    """refute=False skips the expensive half, so its answer is not the answer."""
    c = cache_at(tmp_path)
    c.put(candidate(), stamped())
    seen = []

    def fake_gate(doc, *, seed=None, refute=True):
        seen.append(refute)
        return stamped(passed=False)

    verdict, reused = validate_cached(candidate(), cache=c, validator=fake_gate,
                                      refute=False)
    assert seen == [False] and reused is False and verdict["passed"] is False
    assert c.get(candidate())["passed"] is True     # the deep answer survives
