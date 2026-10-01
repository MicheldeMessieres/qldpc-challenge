"""Keep the scope check's notion of code data aligned with the workflow's.

codes/*.json and anything under circuits/<slug>/ are code data, so a PR
cannot pair a circuit-artifact change with a verifier edit any more than a
codes/ change.
"""
import subprocess

import check_submission_scope as S


def test_code_data_includes_entries_and_their_circuits():
    assert S.is_code_submission("codes/72-6-6.json")
    assert S.is_code_submission("circuits/72-6-6/memory_x.stim")
    assert S.is_code_submission("circuits/72-6-6/memory_z.dem")
    assert not S.is_code_submission("circuits/README.md")
    assert not S.is_code_submission("codes/README.md")
    assert not S.is_code_submission("verify/ler_tools.py")


def test_verifier_stack_is_critical_not_code_data():
    for f in ("verify/ler_tools.py", "uv.lock", "pyproject.toml"):
        assert S.is_critical(f) and not S.is_code_submission(f)


def test_one_entry_with_its_circuit_artifacts_is_one_submission():
    # A first circuit tier adds four files under circuits/<slug>/ next to an
    # existing codes/<slug>.json; that is one submission, not five.
    paths = ["codes/72-6-6.json", "circuits/72-6-6/memory_x.stim",
             "circuits/72-6-6/memory_x.dem", "circuits/72-6-6/memory_z.stim",
             "circuits/72-6-6/memory_z.dem"]
    assert {S.submission_slug(p) for p in paths} == {"72-6-6"}
    assert S.submission_slug("codes/168-20-14.json") == "168-20-14"
    assert {S.submission_slug(p) for p in ("codes/a-1-1.json", "circuits/b-2-2/x.stim")} == {"a-1-1", "b-2-2"}


# -- deletions are code data too (issue #2638) ----------------------------
#
# The rule is "a PR must not change code data and the code that validates it
# in the same diff". Deletions were outside both filters, so one shape slipped
# through entirely: tighten a rule in verify/ and delete the entries the new
# rule would reject. Neither this check nor the workflow step that decides to
# run it saw any code data, so the check was skipped and verify_all ran from
# the PR's own tree rather than the trusted one.

def _repo(tmp_path, base_files, change):
    """Build a repo with `base_files`, then apply `change`; return (root, base).

    `change` maps a path to its content, or to None to delete it. The base is
    returned as a commit SHA rather than a branch name, because both commits
    land on the same branch and a branch ref would point at the tip.
    """
    root = tmp_path / "repo"
    root.mkdir()

    def run(*a):
        return subprocess.run(["git", *a], cwd=root, check=True,
                              capture_output=True, text=True)

    run("init", "-q", "-b", "work")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    for rel, content in base_files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    run("add", "-A")
    run("commit", "-q", "-m", "base")
    base = run("rev-parse", "HEAD").stdout.strip()
    for rel, content in change.items():
        p = root / rel
        if content is None:
            p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
    run("add", "-A")
    run("commit", "-q", "-m", "change")
    return str(root), base


def test_a_deleted_entry_counts_as_code_data(tmp_path):
    """The shape the hole allowed: a rule change plus its own counterexamples."""
    root, base = _repo(
        tmp_path,
        {"codes/72-6-6.json": '{"n": 72}', "verify/qldpc_verify.py": "x = 1\n"},
        {"codes/72-6-6.json": None, "verify/qldpc_verify.py": "x = 2\n"})
    assert "codes/72-6-6.json" in S.changed_files(base, root), \
        "a deletion is a change to the board"
    assert S.main(["--root", root, "--base", base]) == 1, \
        "deleting entries while editing the verifier must be refused"


def test_a_deletion_alone_is_still_fine(tmp_path):
    """Removing an entry on its own is an ordinary board correction."""
    root, base = _repo(tmp_path, {"codes/72-6-6.json": '{"n": 72}'},
                       {"codes/72-6-6.json": None})
    assert S.main(["--root", root, "--base", base]) == 0


def test_a_deletion_does_not_consume_the_one_new_code_budget(tmp_path):
    """The cap prices the deep refutation budget, and a deletion costs none.

    The contents differ on purpose. Given two byte-identical files git pairs
    the delete with the add as a rename, and the new code is then reported
    under R rather than A, which would make this test pass for the wrong
    reason.
    """
    root, base = _repo(
        tmp_path,
        {"codes/a-1-1.json": '{"n": 1}', "codes/b-2-2.json": '{"n": 2}'},
        {"codes/a-1-1.json": None, "codes/c-3-3.json": '{"n": 3}'})
    assert S.added_files(base, root) == ["codes/c-3-3.json"]
    assert S.main(["--root", root, "--base", base]) == 0
