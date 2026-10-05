"""The documented examples must still match the board.

`research/QUICKSTART.md` is the page `AGENTS.md` sends an agent to, and its
worked example builds a code the board already holds. `research/test_smoke.py`
cannot notice that: it calls `qldpc_verify.verify(doc, refute=False)`, which
stops before dedup, so the suite establishes that the kit agrees with the
verifier's *schema* and never that the kit agrees with the *board*. A kit that
drifts onto published codes passes CI silently.

This closes that gap for the page. It runs the documented snippet once, then
checks that what the page says about it is still true:

  - the snippet still runs, and what it builds is still schema-valid;
  - the `[[n,k,d]]` the page names is the one the snippet builds;
  - the gate still returns the verdict the page's prose claims.

So if the page and the board ever disagree -- an entry removed, a construction
edited, a claim left behind after a change -- this fails instead of misleading
the next reader.

Costs about as much as `research/test_smoke.py`: one Monte Carlo witness search
(~14 s, the documented snippet's own `trials`, run once for the module) plus a
board load and a `refute=False` gate pass.
"""
import io
import os
import re
import sys
from contextlib import redirect_stdout

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUICKSTART = os.path.join(ROOT, "research", "QUICKSTART.md")


def _quickstart_text():
    with open(QUICKSTART, encoding="utf-8") as fh:
        return fh.read()


def _documented_snippet():
    """The first ```python block on the page, verbatim."""
    m = re.search(r"```python\n(.*?)```", _quickstart_text(), re.S)
    assert m, "QUICKSTART.md no longer has a python example to check"
    return m.group(1)


def _claimed_gate_outcome():
    """What the page says the gate will say about its example.

    Read from an explicit `# gate: <outcome>` marker in the snippet rather than
    inferred from the prose. An earlier version of this test searched the whole
    page for the word "duplicate", which matched an incidental mention and so
    passed even after the claim it was meant to police had been deleted.
    """
    m = re.search(r"^\s*#\s*gate:\s*(\w+)", _documented_snippet(), re.M)
    assert m, ("QUICKSTART.md's example carries no `# gate: <outcome>` marker, so "
               "there is nothing for this test to hold the page to")
    return m.group(1)


def _prose_after_snippet():
    """The text between the end of the snippet and the next `##` heading.

    Anchored on the python block itself. Splitting the page on ``` alone would
    match the loop diagram that comes first, not the example.
    """
    text = _quickstart_text()
    m = re.search(r"```python\n(.*?)```", text, re.S)
    assert m, "QUICKSTART.md no longer has a python example to check"
    return text[m.end():].split("\n## ", 1)[0]


@pytest.fixture(scope="module")
def board():
    """The board's entries, loaded once for the module.

    Not just an assertion input: loading it here warms the memoized structural
    pass over `codes/` that `validate_candidate` shares, which is the difference
    between a gate call costing 0.3 s and costing minutes. Requesting this from
    the gate test is what keeps that ordering.
    """
    for p in ("research/kit", "verify", "site"):
        if p not in sys.path:
            sys.path.insert(0, os.path.join(ROOT, p))
    from build import load_entries
    entries = load_entries()
    assert entries, f"could not load the board from {ROOT}"
    return entries


@pytest.fixture(scope="module")
def doc():
    """The submission the documented snippet builds.

    Module-scoped because it is the expensive half: the snippet runs a Monte
    Carlo witness search at its own documented `trials`, and every test below
    reads the same document.

    `staging_dir` and `save_submission` are stubbed so a test run writes nothing
    to the staging tree. Everything else executes as written, so a changed
    signature in `make_submission` is caught here rather than by a reader.
    """
    for p in ("research/kit", "verify"):
        if p not in sys.path:
            sys.path.insert(0, os.path.join(ROOT, p))
    import coordination
    import submit

    # Save and restore rather than monkeypatch: the fixture is module-scoped and
    # pytest's monkeypatch is function-scoped, and leaving these replaced would
    # hand every later test in the process a stubbed staging tree.
    real_staging_dir, real_save = coordination.staging_dir, submit.save_submission
    coordination.staging_dir = lambda *a, **k: os.path.join(ROOT, "research", "candidates")
    submit.save_submission = lambda doc_, path, **k: path

    cwd = os.getcwd()
    os.chdir(ROOT)                      # the snippet uses relative sys.path entries
    ns = {"__name__": "documented_example"}
    try:
        with redirect_stdout(io.StringIO()):
            exec(compile(_documented_snippet(), QUICKSTART, "exec"), ns)  # noqa: S102
    finally:
        os.chdir(cwd)
        coordination.staging_dir = real_staging_dir
        submit.save_submission = real_save
    assert "doc" in ns, "the documented snippet no longer builds a submission doc"
    return ns["doc"]


def test_documented_snippet_builds_a_schema_valid_submission(doc):
    """The page's example must still run and still be well-formed."""
    from submit import validate
    errs = validate(doc)
    assert not errs, f"QUICKSTART.md's example is no longer schema-valid: {errs}"


def test_documented_parameters_match_the_page(doc):
    """The `[[n,k,d]]` the page names must be the one the snippet builds."""
    named = re.findall(r"\[\[(\d+),(\d+),(\d+)\]\]", _quickstart_text())
    assert named, "QUICKSTART.md no longer names a [[n,k,d]] for its example"
    n, k, _d = (int(x) for x in named[0])
    assert (doc["n"], doc["k"]) == (n, k), (
        f"QUICKSTART.md names [[{n},{k},...]] but the snippet builds "
        f"[[{doc['n']},{doc['k']},{doc['distance']['d']}]]")


def test_page_claim_agrees_with_the_gate(doc, board):
    """The page's stated expectation and the gate must say the same thing.

    Checked in whichever direction they drift: if the page says `duplicate`, the
    gate must find a duplicate; if it says `pass`, the gate must pass. Either
    way the page cannot present a failing candidate as the model to follow
    without saying that it fails.

    `refute=False` because this is a dedup and novelty question. The gate is
    untouched; only the random distance search is skipped, and it cannot change
    either answer -- it moves `d` down, which moves the candidate away from the
    duplicate rather than toward it.
    """
    from validate_candidate import validate_candidate

    verdict = validate_candidate(doc, refute=False)
    dup = (verdict.get("gates", {}).get("dedup") or {}).get("exact_duplicate_of")
    claims_duplicate = _claimed_gate_outcome() == "duplicate"

    if claims_duplicate:
        assert dup, (
            "QUICKSTART.md's example is marked `# gate: duplicate` and the prose "
            f"says it is already on the board, but the gate reports no duplicate "
            f"(passed={verdict.get('passed')}). Either the entry left the board or "
            "the page is stale; fix whichever is wrong.")
        assert verdict.get("passed") is False
        assert "duplicate" in _prose_after_snippet().lower(), (
            "the example is marked `# gate: duplicate` but the paragraph after it "
            "never tells the reader so; a reader who skips the comment is misled")
    else:
        assert verdict.get("passed") is True, (
            f"QUICKSTART.md's example is marked `# gate: "
            f"{_claimed_gate_outcome()}` but the gate returns passed="
            f"{verdict.get('passed')}. Update the marker or the example.")
