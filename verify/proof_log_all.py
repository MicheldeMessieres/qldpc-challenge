"""Upgrade exact certificates to proof_log where a checked refutation fits.

The one-off batch behind issue #2728. For each exact certificate whose code
is in range, re-emit the question as pure CNF, refute it with kissat, check
the refutation with drat-trim, and record the result on the certificate.

Nothing here can strengthen a claim the solver path did not already make: an
entry is considered only when its certificate already says `d_exact`, the two
emitters must agree on every side, and a side counts as proved only when
drat-trim verifies. An entry whose proof does not verify, does not finish, or
whose trimmed core is too large for the tree keeps the certificate it had.

    python verify/proof_log_all.py --limit 20
    python verify/proof_log_all.py --max-n 144 --workers 4 --tlim 120
"""
import argparse
import glob
import json
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sat_certify import certify  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTS = os.path.join(ROOT, "certs")
BUNDLES = os.path.join(CERTS, "proofs")


def in_range(max_n):
    """Exact certificates whose code is at or under max_n, smallest first."""
    out = []
    for path in sorted(glob.glob(os.path.join(CERTS, "*.json"))):
        slug = os.path.splitext(os.path.basename(path))[0]
        code = os.path.join(ROOT, "codes", slug + ".json")
        if not os.path.exists(code):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                cert = json.load(f)
            with open(code, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, ValueError):
            continue
        if not cert.get("d_exact") or doc["n"] > max_n:
            continue
        out.append((doc["n"], slug, path, code))
    out.sort()
    return out


def one(job):
    """Run the proof path for one entry and report what happened."""
    n, slug, cert_path, code_path, tlim, max_bytes = job
    with open(code_path, encoding="utf-8") as f:
        doc = json.load(f)
    work = tempfile.mkdtemp(prefix=f"proof-{slug}-")
    t0 = time.time()
    try:
        out = certify(doc, tlim=tlim, proof_dir=work, bundle_dir=BUNDLES,
                      slug=slug, max_artifact_bytes=max_bytes)
    except Exception as e:                       # noqa: BLE001
        return {"slug": slug, "n": n, "level": "error", "detail": str(e)[:300],
                "secs": round(time.time() - t0, 1)}
    finally:
        shutil.rmtree(work, ignore_errors=True)

    v = out.get("verification") or {}
    rec = {"slug": slug, "n": n, "level": v.get("level"),
           "secs": round(time.time() - t0, 1),
           "detail": v.get("note", "")[:300]}
    for side, blk in (out.get("sides") or {}).items():
        pr = blk.get("proof") or {}
        rec[f"{side}_cnf_clauses"] = (pr.get("cnf") or {}).get("clauses")
        rec[f"{side}_trimmed_bytes"] = (pr.get("trimmed") or {}).get("bytes")
        rec[f"{side}_solve_secs"] = pr.get("solve_secs")
        rec[f"{side}_check_secs"] = pr.get("check_secs")
    if v.get("level") == "proof_log":
        with open(cert_path, encoding="utf-8") as f:
            cert = json.load(f)
        cert["verification"] = v
        with open(cert_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cert, f, indent=2, sort_keys=True)
            f.write("\n")
        rec["artifact"] = v.get("artifact")
        rec["artifact_bytes"] = os.path.getsize(
            os.path.join(ROOT, v["artifact"]))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-n", type=int, default=144)
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after this many entries (0 = all)")
    ap.add_argument("--tlim", type=int, default=120)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-artifact-bytes", type=int, default=4_000_000)
    ap.add_argument("--log", default=os.path.join(ROOT, "certs",
                                                  "proof_log_batch.jsonl"))
    a = ap.parse_args(argv)

    todo = in_range(a.max_n)
    if a.limit:
        todo = todo[:a.limit]
    jobs = [(n, slug, cp, dp, a.tlim, a.max_artifact_bytes)
            for n, slug, cp, dp in todo]
    os.makedirs(BUNDLES, exist_ok=True)
    print(f"{len(jobs)} exact certificates at n <= {a.max_n}")

    counts, t0 = {}, time.time()
    with open(a.log, "w", encoding="utf-8", newline="\n") as log:
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            for i, rec in enumerate(pool.map(one, jobs), 1):
                counts[rec["level"]] = counts.get(rec["level"], 0) + 1
                log.write(json.dumps(rec, sort_keys=True) + "\n")
                log.flush()
                if i % 25 == 0 or i == len(jobs):
                    print(f"  {i}/{len(jobs)}  {counts}  "
                          f"{round(time.time() - t0)}s")
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
