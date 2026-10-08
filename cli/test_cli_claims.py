"""Tests for `qldpc targets --claim` (issue #2314, item 6).

What matters at this layer is that the flag is a note and not a door. Two
things are pinned here because getting either wrong is the failure the
mechanism exists to prevent: a session must be able to *see* a live claim on
a cell it is about to aim at, and it must not be *stopped* by one. The
primitives are tested in research/test_coordination.py; these check that the
CLI reads and writes them faithfully, and that adding a claim to a cell does
not disturb the board numbers printed beside it.
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "cli"))
import coordination  # noqa: E402
import qldpc  # noqa: E402

ENTRY = {"n": 100, "k": 2, "d": 6, "w": 6, "locality_class": "unrestricted",
         "weight_class": "weight-6", "board_advancing": True}


def _args(**over):
    base = {"cell": None, "n": None, "top": 6, "claim": "", "release": "",
            "campaign": "", "note": "", "ttl": 60, "prune": False,
            "json": False}
    base.update(over)
    return type("A", (), base)()


def _say(fn, *a, **kw):
    """Run fn, returning what it printed."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn(*a, **kw)
    return rc, buf.getvalue()


@pytest.fixture
def claims_dir(tmp_path, monkeypatch):
    """Point the claims primitives at a tmp directory and a stable run id."""
    monkeypatch.setattr(coordination, "CLAIMS", str(tmp_path / "claims"))
    monkeypatch.setenv(coordination.RUN_ID_ENV, "session-a")
    return tmp_path / "claims"


@pytest.fixture
def one_cell(monkeypatch):
    """Stub a board holding one populated cell, so the listing stays short."""
    monkeypatch.setattr(qldpc, "_load_board_entries", lambda: [ENTRY])


# -- taking and dropping a claim -------------------------------------------

def test_claiming_a_cell_writes_the_record_and_says_so(claims_dir):
    rc, out = _say(qldpc.cmd_targets,
                   _args(claim="weight-6/unrestricted", campaign="bb-1155"))
    assert rc == 0 and "claimed weight-6/unrestricted" in out
    rec = coordination.read_claim("weight-6/unrestricted",
                                  root=str(claims_dir))
    assert rec["campaign"] == "bb-1155" and rec["session_id"] == "session-a"


def test_a_second_session_is_warned_and_not_blocked(claims_dir, monkeypatch):
    _say(qldpc.cmd_targets, _args(claim="weight-6/unrestricted", campaign="first"))
    monkeypatch.setenv(coordination.RUN_ID_ENV, "session-b")
    rc, out = _say(qldpc.cmd_targets,
                   _args(claim="weight-6/unrestricted", campaign="second"))
    assert rc == 0
    assert "session-a had a live claim" in out
    assert "Nothing blocks either of you" in out
    rec = coordination.read_claim("weight-6/unrestricted", root=str(claims_dir))
    assert rec["session_id"] == "session-b"


def test_claiming_does_not_read_the_board(claims_dir, monkeypatch):
    """A claim is cheap, and an empty cell is the one worth claiming."""
    def boom():
        raise AssertionError("the board should not be read to take a claim")
    monkeypatch.setattr(qldpc, "_load_board_entries", boom)
    assert _say(qldpc.cmd_targets, _args(claim="weight-6/unrestricted"))[0] == 0


def test_releasing_reports_whether_this_session_held_it(claims_dir, monkeypatch):
    _say(qldpc.cmd_targets, _args(claim="weight-6/unrestricted"))
    monkeypatch.setenv(coordination.RUN_ID_ENV, "session-b")
    rc, out = _say(qldpc.cmd_targets, _args(release="weight-6/unrestricted"))
    assert rc == 0 and "no live claim of this session's" in out
    assert coordination.read_claim("weight-6/unrestricted", root=str(claims_dir))
    monkeypatch.setenv(coordination.RUN_ID_ENV, "session-a")
    rc, out = _say(qldpc.cmd_targets, _args(release="weight-6/unrestricted"))
    assert rc == 0 and "released weight-6/unrestricted" in out
    assert coordination.read_claim("weight-6/unrestricted",
                                   root=str(claims_dir)) is None


def test_pruning_counts_only_what_expired(claims_dir):
    _say(qldpc.cmd_targets, _args(claim="weight-6/unrestricted", ttl=1))
    rc, out = _say(qldpc.cmd_targets, _args(prune=True))
    assert rc == 0 and "pruned 0 expired claim(s)" in out
    later = datetime.now(timezone.utc) + timedelta(hours=1)
    assert coordination.prune_claims(root=str(claims_dir), now=later) == 1


# -- the listing -----------------------------------------------------------

def test_a_claimed_cell_is_marked_and_its_numbers_do_not_move(
        claims_dir, one_cell):
    _, plain = _say(qldpc.cmd_targets, _args(top=2))
    _say(qldpc.cmd_targets, _args(claim="weight-6/unrestricted",
                                  campaign="bb-1155"))
    _, claimed = _say(qldpc.cmd_targets, _args(top=2))
    assert "claimed by session-a (bb-1155)" in claimed
    assert "advisory, not enforced" in claimed
    assert [x for x in plain.splitlines() if "kd2/n" in x] == \
           [x for x in claimed.splitlines() if "kd2/n" in x]
    assert "1 live claim" in claimed


def test_an_expired_claim_is_not_marked(claims_dir, one_cell, monkeypatch):
    _say(qldpc.cmd_targets, _args(claim="weight-6/unrestricted", ttl=1))
    ahead = datetime.now(timezone.utc) + timedelta(hours=1)
    real = coordination._now
    monkeypatch.setattr(coordination, "_now", lambda now=None: ahead)
    try:
        _, out = _say(qldpc.cmd_targets, _args(top=1))
    finally:
        monkeypatch.setattr(coordination, "_now", real)
    assert "claimed by" not in out
    # No claims means no section at all: absence is the signal, and an empty
    # "0 live claims" line on every run would be noise on the common path.
    assert "live claim" not in out


def test_the_json_record_carries_claims_as_data(claims_dir, one_cell, capsys):
    _say(qldpc.cmd_targets, _args(claim="weight-6/unrestricted", campaign="bb"))
    capsys.readouterr()
    rc = qldpc.main(["targets", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    record = json.loads(captured.out)                # one object, nothing else
    assert record["ok"] and record["exit_code"] == 0
    assert [c["cell"] for c in record["claims"]] == ["weight-6/unrestricted"]
    assert record["claims"][0]["session_id"] == "session-a"
    assert "codes across" in captured.err             # the prose went to stderr


def test_the_json_record_reports_a_claim_action(claims_dir, capsys):
    rc = qldpc.main(["targets", "--claim", "weight-8/unrestricted",
                     "--campaign", "sweep-2", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    record = json.loads(captured.out)
    assert record["claim"]["cell"] == "weight-8/unrestricted"
    assert record["claim"]["campaign"] == "sweep-2"
    assert record["claim"]["session_id"] == "session-a"
    assert "claimed" in captured.err
