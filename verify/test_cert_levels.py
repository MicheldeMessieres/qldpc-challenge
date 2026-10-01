"""A certificate may not claim a verification level it cannot evidence.

The exact tier is the strongest thing the board asserts and was, until
#2511, the least checkable: the upper bound ships a logical operator anyone
can re-verify in seconds, and the lower bound shipped a solver's verdict.
`verification.level` records what that verdict is worth, and the only way it
stays meaningful is if claiming a level requires the artifact.
"""
import copy
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import check_certs as C  # noqa: E402

BASE = {"d": 12, "d_exact": True, "solver": "CryptoMiniSat 5.14.7 SAT",
        "sides": {"X": {"value": 12, "exact": True}},
        "verification": {"level": "solver"}}


def test_every_committed_certificate_declares_a_level():
    assert C.main([]) == 0, "certs/ does not validate"


def test_the_board_claims_no_level_it_cannot_evidence():
    """Today every certificate is a solver verdict. That is the honest state.

    This is not a permanent assertion; it fails the day a stronger one lands,
    which is the point at which someone should look at whether the artifact
    really is in the tree.
    """
    import glob
    levels = set()
    for p in glob.glob(os.path.join(_ROOT, "certs", "*.json")):
        with open(p, encoding="utf-8") as f:
            levels.add((json.load(f).get("verification") or {}).get("level"))
    assert levels == {"solver"}, (
        f"levels present: {sorted(levels)}. If a stronger level landed, check "
        "its artifact is committed and update this test deliberately.")


@pytest.mark.parametrize("level", ["proof_log", "formal"])
def test_a_stronger_level_needs_an_artifact_that_exists(level):
    c = copy.deepcopy(BASE)
    c["verification"] = {"level": level, "checker": "drat-trim 2024-05"}
    assert C.evidence_problems("x", c), "no artifact must be refused"

    c["verification"]["artifact"] = "certs/proofs/does-not-exist.drat"
    probs = C.evidence_problems("x", c)
    assert probs and "not a file committed in this tree" in probs[0], \
        "an artifact that is not committed must be refused"


@pytest.mark.parametrize("level", ["proof_log", "formal"])
def test_a_stronger_level_needs_a_named_checker(level):
    c = copy.deepcopy(BASE)
    c["verification"] = {"level": level, "artifact": "schema/cert.schema.json"}
    probs = C.evidence_problems("x", c)
    assert any("checker" in p for p in probs), \
        "an unchecked artifact is not a check"


def test_solver_level_does_not_smuggle_an_artifact():
    """If something checkable exists, the certificate should claim its level."""
    c = copy.deepcopy(BASE)
    c["verification"] = {"level": "solver",
                         "artifact": "schema/cert.schema.json"}
    assert C.evidence_problems("x", c)


def test_an_unknown_level_is_refused():
    c = copy.deepcopy(BASE)
    c["verification"] = {"level": "probably_fine"}
    assert C.evidence_problems("x", c)


def test_a_well_formed_stronger_certificate_passes():
    """The path has to work, or nobody will use it."""
    c = copy.deepcopy(BASE)
    c["verification"] = {"level": "formal",
                         "artifact": "schema/cert.schema.json",
                         "checker": "Lean 4 + mathlib",
                         "reference": "arXiv:2605.16523"}
    assert C.evidence_problems("x", c) == []


@pytest.mark.parametrize("art", [
    "/etc/hosts",                      # absolute: os.path.join drops ROOT
    "certs/../verify/check_certs.py",  # resolves in-tree, still not a path to
                                       # store, since a reader has to normalise
                                       # it before it names anything
    "certs",                           # a directory is not an artifact
    "certs/heuristic",
])
def test_an_artifact_outside_the_tree_is_refused(art):
    c = copy.deepcopy(BASE)
    c["verification"] = {"level": "proof_log", "artifact": art,
                         "checker": "drat-trim 2024-05"}
    assert C.evidence_problems("x", c), f"{art} must not be accepted"


@pytest.mark.parametrize("field", ["artifact", "checker", "reference"])
def test_solver_level_claims_no_check_it_did_not_run(field):
    """A checker named on a bare solver verdict asserts a check that is not
    there, exactly as an artifact would."""
    c = copy.deepcopy(BASE)
    c["verification"] = {"level": "solver", field: "drat-trim 2024-05"}
    assert C.evidence_problems("x", c)


def test_the_cert_writer_stamps_a_level_the_checker_accepts(tmp_path,
                                                           monkeypatch):
    """The gate is only worth having if the next regeneration satisfies it.

    certify_all.py writes certs/<slug>.json, so a cert written today has to
    carry the block check_certs.py requires, rather than needing a backfill
    after every run.
    """
    import certify_all

    monkeypatch.setattr(certify_all, "certify", lambda doc, tlim: {
        "d": 7, "d_exact": True, "sides": {"X": {"value": 7, "exact": True}}})
    monkeypatch.setattr(certify_all, "CERTS", str(tmp_path / "certs"))

    src = tmp_path / "98-6-7.json"
    src.write_text(json.dumps({"name": "98-6-7"}), encoding="utf-8")
    certify_all.run(str(src))

    with open(tmp_path / "certs" / "98-6-7.json", encoding="utf-8") as f:
        written = json.load(f)
    assert written["verification"] == {"level": "solver"}
    assert C.evidence_problems("98-6-7", written) == []
