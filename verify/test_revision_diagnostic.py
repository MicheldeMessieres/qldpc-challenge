"""A revision must not be reported as someone filing the same code twice.

A distance revision has the same checks as the entry it corrects, so it
fingerprints as an exact duplicate. That is right: `validate_candidate` is the
new-candidate path and a revision is not a new candidate. What was wrong is
what it said. "duplicate: identical to board entry X" is indistinguishable
from a double submission, so an agent that followed the audit loop, earned a
`redirect`, and packaged the revision was told its work was redundant and
discarded the most expensive data in the loop (issue #2583).

The fingerprint is deliberately unchanged. It is computed from the matrices
because the matrices are the code, and a claim about a code is not part of its
identity; widening it to include `d` would stop dedup catching a re-labelled
copy that claims a different distance, which is the case it exists for.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import validate_candidate as V  # noqa: E402

SLUG = "144-12-12"


def _doc():
    with open(os.path.join(_ROOT, "codes", SLUG + ".json"), encoding="utf-8") as f:
        return json.load(f)


_REAL_BOARD = V._board_entries


def _board_claiming(d):
    """The real board, with the entry this candidate matches claiming `d`."""
    rows = _REAL_BOARD()
    for b in rows:
        if b["name"] == SLUG + ".json":
            b["d"] = d
    return rows


def _labels(board_d, monkeypatch):
    # bind the original before patching, or the stub calls itself
    monkeypatch.setattr(V, "_board_entries", lambda: _board_claiming(board_d))
    return V.validate_candidate(_doc())


def test_a_lower_claim_reads_as_a_revision(monkeypatch):
    """Same checks, board claims more: this is a correction, and says so."""
    doc_d = _doc()["distance"]["d"]
    v = _labels(doc_d + 8, monkeypatch)
    labels = " ".join(v["labels"])
    assert "distance revision, not a duplicate" in labels
    assert "File it as a correction" in labels
    assert v["gates"]["dedup"]["revision_of"] == SLUG + ".json"
    assert not v["passed"], "it still must not pass the new-candidate path"


def test_an_equal_claim_is_still_a_duplicate(monkeypatch):
    """The case dedup exists for keeps its old, blunt verdict."""
    v = _labels(_doc()["distance"]["d"], monkeypatch)
    labels = " ".join(v["labels"])
    assert "duplicate: identical to board entry" in labels
    assert "revision" not in labels
    assert "revision_of" not in v["gates"]["dedup"]


def test_a_higher_claim_is_not_a_revision(monkeypatch):
    """Claiming MORE than the board on identical checks is not a correction.

    A revision lowers a claim. Raising one on the same matrices is either a
    mistake or an over-claim, and must not be handed language that invites
    filing it as a correction.
    """
    v = _labels(max(1, _doc()["distance"]["d"] - 4), monkeypatch)
    labels = " ".join(v["labels"])
    assert "duplicate: identical to board entry" in labels
    assert "revision" not in labels


def test_the_fingerprint_still_ignores_the_claim():
    """Pinned because #2583 proposed changing it and this is why not."""
    import numpy as np
    from qldpc_verify import css_fingerprint
    doc = _doc()
    n = doc["n"]

    def M(sup):
        H = np.zeros((len(sup), n), dtype=np.uint8)
        for i, r in enumerate(sup):
            H[i, list(r)] = 1
        return H

    fp = css_fingerprint(M(doc["checks"]["X"]), M(doc["checks"]["Z"]))
    doc["distance"]["d"] = 1
    fp2 = css_fingerprint(M(doc["checks"]["X"]), M(doc["checks"]["Z"]))
    assert fp == fp2, "the claim is not part of the code's identity"
