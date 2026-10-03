"""Verify every submission under codes/ and the verify/fixtures/ test inputs, and flag possible
duplicates by permutation-invariant signature. Used by CI. Exit 0 only if all
pass and no two codes/ entries share a signature.

This runs the cheap structural checks (schema, n/k/CSS/weight, witness validity,
duplicates) on every entry, plus the circuit-tier fast path (circuit_verify:
determinism, noise recipe, code binding, DEM + d_circ witness -- all
deterministic and cheap) on entries declaring one. Distance refutation is NOT
run here -- it is the per-submission job of gate_changed.py (changed files) and
the weekly job of refute_board.py (whole board, random seed).

The structural reports come from qldpc_verify.board_reports, the same pass
validate_candidate, site/build.py, and board_frontier_audit read (issue
#2613). There used to be a second copy of that pass here, a bare verify() per
entry, so the research gate's notion of a duplicate and CI's notion of a pass
could drift without any test noticing. Now one implementation produces the
report and this file only layers the circuit and measured-rate tiers on top
and accumulates the fingerprint and signature collisions. The pass is still
paid in full in CI: board_reports's disk memo is off there, and the
collision detection below is inherently a scan of the submitted tree, which
is the untrusted input. The memo only spares a developer who has already
verified these bytes in another process.

The one expensive thing here is the measured-rate tier: a circuit.ler claim is
re-measured by a sampled replica (ler_verify), ~2 x 120 s per entry at the wall
budget, and on a hosted runner the handful of entries carrying one took ~13 of
the PR job's minutes -- for claims nothing in the PR had touched. With
--ler-base REF the replica runs only for entries whose codes/<slug>.json or
circuits/<slug>/ changed since REF (the same diff principle gate_changed prices
by). PR runs pass the base branch; a push to main passes the previous head of
main, so a merge re-measures what it changed and nothing else (issue #2614:
before that it re-measured every claim on the board, about 21 CPU-hours per
merge). A diff that cannot be computed falls back to re-measuring everything.

Two things make the skip safe, and one is a cost. Safe: an unchanged claim
can only go stale through the verifier stack (a stim bump in uv.lock, a
ler_tools edit), and verify.yml routes any run whose diff touches that stack,
PR or push, to the unflagged full re-measure; check_submission_scope.py keeps
such a change out of a PR that also carries code data. The full re-measure of
every claim also runs weekly on a schedule, so no measured rate on the board
goes more than a week without being re-derived from scratch. Cost: an entry
nobody touches is re-measured weekly rather than on every merge, and a
failing scheduled run reverts nothing on its own; it is a signal to a
maintainer, not a gate."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from qldpc_verify import board_reports
from circuit_verify import verify_circuit
from gate_changed import changed_codes as changed_code_paths
from ler_verify import verify_ler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ler_slugs_to_measure(base, code_root):
    """Slugs whose codes/<slug>.json or circuits/<slug>/ differ from git ref
    `base`, or None when the diff is unavailable (then every claim is
    re-measured -- the failure mode must cost time, never coverage)."""
    changed = changed_code_paths(base, code_root)
    if changed is None:
        print(f"note: could not diff vs {base}; re-measuring every ler claim")
        return None
    return {os.path.splitext(os.path.basename(p))[0] for p in changed}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT,
                    help="repository tree containing codes/ to verify; verifier "
                         "code and fixtures still come from this checkout")
    ap.add_argument("--ler-base", default=None, metavar="REF",
                    help="re-measure circuit.ler claims only for entries whose "
                         "codes/<slug>.json or circuits/<slug>/ changed since "
                         "this git ref (PR runs); omit to re-measure every claim")
    args = ap.parse_args(argv)
    code_root = os.path.abspath(args.root)
    ler_slugs = (ler_slugs_to_measure(args.ler_base, code_root)
                 if args.ler_base else None)
    # One structural pass per tree, shared with every other consumer. The
    # reports are the memoized objects other callers in this process read, so
    # each is copied before the circuit tier writes a verdict into it.
    entries = [(e, True) for e in board_reports(os.path.join(code_root, "codes"))]
    entries += [(e, False) for e in
                board_reports(os.path.join(ROOT, "verify", "fixtures"))]
    if not entries:
        print("no submissions found")
        return 0
    failed = []
    sigs = {}
    fps = {}
    for e, is_code in entries:
        p = e["path"]
        rel = os.path.relpath(p, code_root if is_code else ROOT)
        if e["size_error"]:
            failed.append(rel)
            print(f"FAIL  {rel}  -> file_size_within_limit: {e['size_error']}")
            continue
        if e["load_error"]:
            failed.append(rel)
            print(f"FAIL  {rel}  -> {e['load_error']}")
            continue
        doc = e["doc"]
        rep = dict(e["report"])
        rep["checks"] = list(rep["checks"])
        circ = ""
        if rep["ok"] and is_code and doc.get("circuit"):
            slug = e["slug"]
            circuits_dir = os.path.join(code_root, "circuits", slug)
            crep = verify_circuit(doc, circuits_dir)
            if crep["ok"]:
                circ = (f", d_circ<="
                        f"{crep['earned_d_circ']['d_circ']['value']}")
            else:
                rep["ok"] = False
                rep["checks"] += [c for c in crep["checks"] if not c["ok"]]
            # measured-rate tier: an ler claim is re-measured,
            # never trusted; a missing decoder fails the claim rather than
            # skipping it, so an unverifiable number cannot merge.
            if rep["ok"] and (doc["circuit"] or {}).get("ler"):
                if ler_slugs is not None and slug not in ler_slugs:
                    circ += ", ler unchanged since base (re-measured on main)"
                    lrep = {"ok": True, "skipped": True}
                else:
                    lrep = verify_ler(doc, circuits_dir)
                if lrep.get("skipped"):
                    pass
                elif lrep["ok"]:
                    lers = [doc["circuit"]["ler"][s]["ler_per_round"]
                            for s in ("X", "Z")]
                    circ += f", ler/round<={max(lers):.3g}"
                else:
                    rep["ok"] = False
                    rep["checks"] += [c for c in lrep["checks"]
                                      if not c["ok"]]
        if rep["ok"]:
            ed = rep["earned_distance"].get("d", {})
            print(f"PASS  {rel}  -> d{ed.get('value','?')} "
                  f"({ed.get('tier','-')}){circ}")
            if is_code:
                if "signature" in rep:
                    sigs.setdefault(rep["signature"]["hash"], []).append(rel)
                if "fingerprint" in rep:
                    fps.setdefault(rep["fingerprint"], []).append(rel)
                # a stabilizer entry that is CSS up to local Hadamards is also
                # filed under that CSS code's identity, so a
                # Hadamard-relabeled copy of a CSS entry collides with it
                ceq = rep.get("css_equivalent") or {}
                for fp in set(ceq.get("fingerprints") or []):
                    fps.setdefault(fp, []).append(rel + " (via local Hadamard)")
                for h in set(ceq.get("signatures") or []):
                    sigs.setdefault(h, []).append(rel + " (via local Hadamard)")
        else:
            failed.append(rel)
            bad = [c["check"] for c in rep["checks"] if not c["ok"]]
            print(f"FAIL  {rel}  -> {', '.join(bad)}")

    # identical codes (same stabilizer group, same labeling): a hard error.
    # A stabilizer entry filed under its own CSS image is one entry twice,
    # not a collision, so count distinct entries per fingerprint.
    fps = {h: v for h, v in fps.items()
           if len({x.split(" (")[0] for x in v}) > 1}
    sigs = {h: v for h, v in sigs.items()
            if len({x.split(" (")[0] for x in v}) > 1}
    identical = {h: v for h, v in fps.items() if len(v) > 1}
    if identical:
        print("\nIDENTICAL CODES (same stabilizer group) -- reject:")
        for h, v in identical.items():
            print(f"  {', '.join(v)}")
    # same WL signature but not identical: likely permutation-equivalent, flag
    # for human review (WL is a strong necessary condition, not a proof).
    soft = {h: v for h, v in sigs.items()
            if len(v) > 1 and not any(set(v) <= set(iv)
                                      for iv in identical.values())}
    if soft:
        print("\nPOSSIBLE EQUIVALENT CODES (same Weisfeiler-Leman signature; "
              "review):")
        for h, v in soft.items():
            print(f"  {h}: {', '.join(v)}")

    print(f"\n{len(entries)-len(failed)}/{len(entries)} passed")
    return 1 if (failed or identical) else 0


if __name__ == "__main__":
    sys.exit(main())
