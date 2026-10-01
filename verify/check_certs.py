#!/usr/bin/env python3
"""Validate certs/ against schema/cert.schema.json, and refuse an unearned level.

A `certs/<slug>.json` with `d_exact: true` upgrades a board entry from a
witnessed upper bound to an exact distance, so it is the strongest thing the
board asserts and, until #2511, the least checkable. The upper bound ships an
explicit logical operator anyone can re-verify in seconds. The lower bound
shipped a solver's verdict and a sentence.

`verification.level` records how much that verdict is worth:

    solver     a solver said UNSAT or optimal. No artifact a third party can
               check without re-running our encoding.
    proof_log  a machine-checkable refutation artifact accompanies the run.
    formal     a machine-checked proof of the distance statement, with the
               reduction verified too.

The distinction between the last two is the load-bearing one and is easy to
blur. A DRAT proof establishes that the CNF we handed the solver is
unsatisfiable; it says nothing about whether that CNF asks the distance
question. #2273 is exactly that failure: the CNF was fine and it asked the
wrong thing, because the pairing set spanned the wrong space. Only `formal`
closes that, because the reduction is part of what is proved.

So this checker enforces the one rule that keeps the tier honest: a
certificate may not claim a level it carries no evidence for. Claiming
`proof_log` or `formal` requires an artifact that exists and a checker that
produced it.

    python verify/check_certs.py            # validate every certificate
    python verify/check_certs.py --level    # print the level mix
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCHEMA = os.path.join(ROOT, "schema", "cert.schema.json")
LEVELS = ("solver", "proof_log", "formal")


def load_schema():
    with open(SCHEMA, encoding="utf-8") as f:
        return json.load(f)


def _inside_tree(art):
    """True when `art` is a file inside the repository.

    os.path.join discards the root when the second argument is absolute, and
    `..` walks out of it, so joining and calling os.path.exists accepts
    "/etc/hosts" and "certs/../verify/check_certs.py". This is the field whose
    entire job is pointing at committed evidence, so it is resolved and
    required to land under ROOT, and to be a file rather than a directory.
    """
    if os.path.isabs(art):
        return False
    # "certs/../verify/x.py" resolves in-tree and is still wrong to store: the
    # recorded path should name where the evidence is, so a reader can find it
    # without normalising it first.
    if os.path.normpath(art) != art.rstrip("/"):
        return False
    full = os.path.realpath(os.path.join(ROOT, art))
    root = os.path.realpath(ROOT)
    if os.path.commonpath([full, root]) != root:
        return False
    return os.path.isfile(full)


def evidence_problems(slug, cert):
    """Rules a schema cannot state: the artifact has to be there."""
    out = []
    v = cert.get("verification") or {}
    level = v.get("level")
    if level not in LEVELS:
        return [f"{slug}: verification.level {level!r} is not one of {LEVELS}"]
    if level == "solver":
        # The rule is "no evidence you cannot point at", so it has to cover
        # every field that asserts one. A checker or a reference on a bare
        # solver verdict claims a check that did not happen.
        for field in ("artifact", "checker", "reference"):
            if v.get(field):
                out.append(f"{slug}: level 'solver' names a {field}; if "
                           "something was checked, claim the level it earns")
        return out
    art = v.get("artifact")
    if not art:
        out.append(f"{slug}: level {level!r} with no artifact")
    elif not _inside_tree(art):
        out.append(f"{slug}: level {level!r} names {art}, which is not a file "
                   "committed in this tree")
    if not v.get("checker"):
        out.append(f"{slug}: level {level!r} with no checker recorded")
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--level", action="store_true",
                    help="print the level mix and exit")
    a = ap.parse_args(argv)

    # Non-recursively, on purpose. certs/heuristic/ holds a different artifact
    # entirely (claimed_d / verdict / methods / seed) that this schema does not
    # describe and should not be made to; making the glob recursive would fail
    # all six wholesale. Heuristic evidence is also the weakest thing under
    # certs/ and has no level in the enum yet, which is its own question.
    certs = sorted(glob.glob(os.path.join(ROOT, "certs", "*.json")))
    if not certs:
        print("no certificates found")
        return 0

    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(load_schema())
    except ImportError:                       # pragma: no cover
        validator = None
        print("note: jsonschema unavailable; structural check skipped, "
              "evidence rules still enforced")

    problems, mix = [], dict.fromkeys(LEVELS, 0)
    for path in certs:
        slug = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as f:
            cert = json.load(f)
        if validator is not None:
            for e in sorted(validator.iter_errors(cert), key=lambda e: e.path):
                where = "/".join(str(p) for p in e.absolute_path) or "(root)"
                problems.append(f"{slug}: {where}: {e.message}")
        problems.extend(evidence_problems(slug, cert))
        lv = (cert.get("verification") or {}).get("level")
        if lv in mix:
            mix[lv] += 1

    if a.level:
        print(f"{len(certs)} certificates")
        for lv in LEVELS:
            print(f"  {mix[lv]:>4}  {lv}")
        return 0

    if problems:
        print(f"certificate problems ({len(problems)}):")
        for p in problems[:40]:
            print("  " + p)
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        return 1
    print(f"ok: {len(certs)} certificates valid "
          + ", ".join(f"{mix[lv]} {lv}" for lv in LEVELS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
