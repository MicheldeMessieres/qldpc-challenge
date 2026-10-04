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
    """Every level the board claims has the evidence that level requires.

    Certificates are solver verdicts and, since #2728, proof_log entries
    carrying a checked refutation. The tripwire that used to pin the set to
    solver alone fired when that landed, which is what it was for; what is
    pinned now is the thing worth pinning, that no entry claims a level
    whose artifact is missing, and that formal has not appeared without the
    replay recipe #2511 specifies for it.
    """
    import glob
    levels = {}
    for p in glob.glob(os.path.join(_ROOT, "certs", "*.json")):
        with open(p, encoding="utf-8") as f:
            cert = json.load(f)
        v = cert.get("verification") or {}
        levels.setdefault(v.get("level"), []).append((p, v))
    assert set(levels) <= {"solver", "proof_log", "formal"}, \
        f"unknown level: {sorted(set(levels))}"
    for level, rows in levels.items():
        if level == "solver":
            continue
        for path, v in rows:
            slug = os.path.basename(path)
            # Evidence is a file in the tree or the recipe that re-derives
            # the check. proof_log ships the recipe (PR #2754): the
            # refutations are too large to commit and a committed blob is
            # not something CI can audit, so the certificate carries the
            # formula's hash and replay_proofs.py regenerates and re-checks
            # it on a schedule.
            if v.get("artifact"):
                art = os.path.join(_ROOT, v["artifact"])
                assert os.path.isfile(art), \
                    f"{slug}: level {level} names an artifact not in the tree"
                assert os.path.getsize(art) > 0, f"{slug}: empty artifact"
            else:
                assert v.get("replay"), \
                    f"{slug}: level {level} with neither artifact nor replay"
                if level == "proof_log":
                    assert v.get("cnf_sha256"), \
                        f"{slug}: replayed proof_log without cnf_sha256"
            assert v.get("checker"), f"{slug}: level {level} with no checker"
    for path, v in levels.get("formal", []):
        assert v.get("replay") and v.get("checks_sha256"), (
            f"{os.path.basename(path)}: a formal certificate needs the "
            "replay recipe and the hash binding it to this code, since the "
            "proof is a theorem rather than a file")


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
    """Refuse a checker named on a bare solver verdict.

    It asserts a check that is not there, exactly as an artifact would.
    """
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
