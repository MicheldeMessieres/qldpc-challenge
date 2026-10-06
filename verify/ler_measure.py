"""Measure an entry's logical error rate at one or more physical rates and
write the points into its circuit.ler block (issue #1278).

Usage:
    python verify/ler_measure.py codes/<slug>.json --p 0.005 0.001 [--shots N]
                                 [--seed S] [--replace] [--dry-run]

Each basis's committed memory circuit is stripped to its skeleton and the
canonical noise recipe is re-applied at the requested rate, so a point at p
is the same experiment as the committed one at a different rate. Points are
appended to the existing list (a point at a rate already present is
replaced); --replace discards the existing list first. Shots are raised in
steps until every basis carries at least MIN_FAILURES failures at the rate,
and a point whose failure fraction exceeds the saturation bound is reported
and not written. Entries written here declare schema 0.5.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import circuit_tools as ct
import ler_tools as lt
import ler_verify as lv

SHOT_STEPS = (10_000, 20_000, 40_000, 80_000, 160_000, 320_000)


def measure_point(circuit, n, rounds, p, seed, shots=None, log=print):
    """One basis's point at rate p, or None if saturated. Raises shots along
    SHOT_STEPS until the failure floor is met (or shots is given)."""
    skel = ct.strip_noise(circuit)
    dem = ct.derive_dem(ct.apply_noise(skel, n, p=p))
    steps = (shots,) if shots else SHOT_STEPS
    for s in steps:
        failures, _ = lt.measure_failures(dem, s, seed)
        log(f"    p={p}: {failures}/{s}")
        if failures / s > lv.SATURATION:
            return None
        if failures >= lt.MIN_FAILURES:
            break
    p_shot = failures / s
    lo, hi = lt.wilson_ci(failures, s)
    return {"p": p, "shots": s, "failures": failures, "seed": seed,
            "decoder": lt.DECODER_ID,
            "ler_per_round": round(lt.per_round(p_shot, rounds), 9),
            "ci95": [round(lt.per_round(lo, rounds), 9),
                     round(lt.per_round(hi, rounds), 9)]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("code")
    ap.add_argument("--p", type=float, nargs="+", required=True)
    ap.add_argument("--shots", type=int, default=None)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--circuits-dir", default=None)
    a = ap.parse_args(argv)
    import stim
    with open(a.code, encoding="utf-8") as f:
        raw = f.read()
    doc = json.loads(raw)
    # keep the file's own indentation (the board mixes 1 and 2 spaces)
    m = re.match(r"\{\n( +)\"", raw)
    indent = len(m.group(1)) if m else 1
    slug = os.path.splitext(os.path.basename(a.code))[0]
    cdir = a.circuits_dir or os.path.join(
        os.path.dirname(os.path.abspath(a.code)), "..", "circuits", slug)
    circ = doc.get("circuit")
    if not circ:
        print("no circuit tier; measure needs committed memory circuits")
        return 2
    for p in a.p:
        if p not in lv.P_GRID:
            print(f"p={p} is not on the grid {list(lv.P_GRID)}")
            return 2
    ler = circ.get("ler") or {}
    out = {}
    for side, fname in lv.SIDE_FILES.items():
        existing = [] if a.replace else list(lv.points_of(ler.get(side)) or [])
        existing = [q for q in existing if q.get("p") not in a.p]
        circuit = stim.Circuit.from_file(os.path.join(cdir, fname + ".stim"))
        print(f"  {side}:")
        for p in a.p:
            point = measure_point(circuit, doc["n"], circ["rounds"], p,
                                  a.seed, a.shots)
            if point is None:
                print(f"    p={p}: saturated, not written")
                continue
            existing.append(point)
        out[side] = sorted(existing, key=lambda q: -q["p"])
    if not all(out.get(s) for s in ("X", "Z")):
        print("a basis has no point left; nothing written")
        return 1
    circ["ler"] = out
    doc["schema_version"] = "0.5"
    if a.dry_run:
        print(json.dumps(out, indent=1))
        return 0
    with open(a.code, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=indent)
        f.write("\n" if raw.endswith("\n") else "")
    print(f"wrote {a.code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
