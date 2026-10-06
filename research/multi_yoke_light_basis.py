"""Decide whether a multi-yoked chain-code check matrix can be pulled under the board cap.

H' = M H for invertible M over GF(2) leaves the row space unchanged, so k
and the distance are exactly preserved; only the choice of generators moves.
The board's ``MAX_CHECK_WEIGHT`` is 32, and the published chain codes sit
above it, so the only way any of them can be filed is to find a basis of the
row space in which every row has weight <= 32.

Criterion.  A basis of r light rows exists **iff** the row-space elements of
weight <= T span rank r -- because every basis vector is itself a row-space
element, and conversely a spanning light set contains r independent light
rows.  So the test needs no search when r is small: enumerate all 2^r
row-space elements, keep the ones of weight <= T, and ask for their rank.
That answer is exact.  For large r the enumeration is impossible and the
script falls back to biased random sampling plus a local search (replace the
heaviest row by itself xor another), which is a one-sided test: a hit proves
a light basis exists, a miss proves nothing.

The sampling fallback's miss is not the finding this script exists to
record.  The two-yoke matrices all have r = (n-k)/2 in 9..23, so they are
enumerated exactly, and every one of them fails.

Usage::

    python research/multi_yoke_light_basis.py \
        --chain-codes /path/to/multi_yoked_surface_codes/ecc/chain_codes \
        --out /tmp/light-basis

Source matrices: github.com/yugahirai/multi_yoked_surface_codes @ b3e8b3e.
"""

import argparse
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "verify"), os.path.join(ROOT, "research", "kit")]

import gf2  # noqa: E402
import numpy as np  # noqa: E402
from css import compute_k, verify_css  # noqa: E402

CAP = 32
MAX_ENUM = 1 << 23

# Already on the board from this family (or dominated by one that is).
FILED = {
    "q24_8_4",
    "q32_18_4",
    "q36_16_4",
    "q40_24_4",
    "q48_30_4",
    "q56_36_4",
    "q64_42_4",
    "q64_48_4",
    "q96_30_8",
    "q112_40_8",
}


# ---------------------------------------------------------------- source files


def dense(path):
    """Parse the paper's check-matrix text into dense uint8 HX, HZ."""
    secs, cur, width = {}, None, 0
    for line in open(path).read().split("\n"):
        if not line.strip():
            continue
        low = line.lower()
        if "check" in low and not set(line) <= set("01"):
            cur = "X" if low.startswith("x") else "Z"
            secs[cur] = []
        elif cur is not None:
            secs[cur].append([i for i, c in enumerate(line) if c == "1"])
            width = max(width, len(line))
    HX = np.zeros((len(secs["X"]), width), dtype=np.uint8)
    HZ = np.zeros((len(secs["Z"]), width), dtype=np.uint8)
    for i, sup in enumerate(secs["X"]):
        HX[i, sup] = 1
    for i, sup in enumerate(secs["Z"]):
        HZ[i, sup] = 1
    return HX, HZ


# ---------------------------------------------------------------- exact test


class Basis:
    """GF(2) row basis in leading-bit form: O(r) int XOR per insert."""

    def __init__(self):
        self.top = {}

    def insert(self, v):
        while v:
            t = v.bit_length() - 1
            b = self.top.get(t)
            if b is None:
                self.top[t] = v
                return True
            v ^= b
        return False

    @property
    def rank(self):
        return len(self.top)


def rows_as_ints(H):
    out = []
    for row in H:
        v = 0
        for j in np.flatnonzero(row):
            v |= 1 << int(j)
        out.append(v)
    return out


def light_basis_exact(H, cap=CAP, max_enum=MAX_ENUM):
    """Exact: (light basis rows as ints | None, elements scanned).

    None means the weight-<=cap elements provably do not span, so no basis
    of light rows exists.  Returns (None, 0, False) when 2^r is too big to
    enumerate and the caller should fall back to sampling.
    """
    r = int(gf2.rank(H))
    n = H.shape[1]
    if (1 << r) > max_enum:
        return None, 0, False
    bas = Basis()
    for v in rows_as_ints(H):
        bas.insert(v)
    B = [bas.top[t] for t in sorted(bas.top, reverse=True)]
    Bm = np.zeros((r, n), dtype=np.uint8)
    for i, v in enumerate(B):
        for j in range(n):
            if (v >> j) & 1:
                Bm[i, j] = 1

    total = 1 << r
    wts = np.empty(total, dtype=np.uint8)
    batch = 1 << 16
    shifts = np.arange(r, dtype=np.uint64)
    for start in range(0, total, batch):
        stop = min(start + batch, total)
        cs = np.arange(start, stop, dtype=np.uint64)
        bits = ((cs[:, None] >> shifts) & 1).astype(np.uint8)
        wts[start:stop] = ((bits @ Bm) & 1).sum(1)

    light = np.flatnonzero(wts <= cap)
    if light.size == 0:
        return None, 0, True
    out, scan = Basis(), []
    for idx in light[np.argsort(wts[light], kind="stable")]:
        bits = ((np.array([idx], dtype=np.uint64) >> shifts) & 1).astype(np.uint8)
        vec = (bits @ Bm)[0]
        v = 0
        for j in np.flatnonzero(vec):
            v |= 1 << int(j)
        if v and out.insert(v):
            scan.append(v)
        if out.rank == r:
            return scan, light.size, True
    return None, light.size, True


# ------------------------------------------------------------ sampling fallback


def _independent(rows, cand):
    return gf2.rank(np.array(rows + [cand], dtype=np.uint8)) > len(rows)


def light_pool(H, rng, samples, T):
    r = gf2.rank(H)
    basis, i = [], 0
    while i < H.shape[0] and len(basis) < r:
        if _independent(basis, H[i]):
            basis.append(H[i])
        i += 1
    B = np.array(basis, dtype=np.uint8)
    pool = []
    for p in (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9):
        coef = (rng.random((samples, len(B))) < p).astype(np.uint8)
        vecs = (coef @ B) & 1
        for v in vecs[vecs.sum(1) <= T]:
            if _independent(pool, v):
                pool.append(v)
        if len(pool) == r:
            break
    return pool


def shave(B, rng, iters=6000):
    cur, w = B.copy(), B.sum(1)
    for _ in range(iters):
        i, j = int(np.argmax(w)), int(rng.integers(0, len(cur)))
        if i == j:
            continue
        trial = cur[i] ^ cur[j]
        if int(trial.sum()) < w[i] and _independent([cur[k] for k in range(len(cur)) if k != i], trial):
            cur[i], w[i] = trial, int(trial.sum())
    return cur


def _basis_matrix(H):
    """Return a basis of H's rows as a dense (r, n) uint8 matrix."""
    b = Basis()
    for v in rows_as_ints(H):
        b.insert(v)
    Bm = np.zeros((b.rank, H.shape[1]), dtype=np.uint8)
    for i, t in enumerate(sorted(b.top, reverse=True)):
        v = b.top[t]
        for j in range(H.shape[1]):
            if (v >> j) & 1:
                Bm[i, j] = 1
    return Bm


def light_basis_sampled(H, cap=CAP, samples=6000, seed=0):
    """Return a light basis, or None when this seed did not find one.

    One-sided test: a returned list is a light basis (it proves one exists);
    None means only that this seed failed, never that none exists.
    """
    rng = np.random.default_rng(seed)
    r = gf2.rank(H)
    pool = light_pool(H, rng, samples, cap)
    if len(pool) == r:
        return rows_as_ints(pool), True
    # local search from a basis of H, then re-sample at the weight reached
    shaven = shave(_basis_matrix(H), rng, iters=6000)
    pool2 = light_pool(H, rng, samples, int(shaven.sum(1).max()))
    if len(pool2) == r:
        return rows_as_ints(pool2), True
    return None, False


# ------------------------------------------------------------------- driver


def analyse(path, cap, samples, seeds, max_enum):
    t0 = time.time()
    HX, HZ = dense(path)
    n = HX.shape[1]
    stem = os.path.basename(path)[:-4]
    rec = {
        "file": stem,
        "n": n,
        "k": int(compute_k(HX.astype(int), HZ.astype(int))),
        "d": int(re.search(r"_(\d+)(?:_reduced)?\.txt$", stem + ".txt").group(1)),
        "w0": int(max(HX.sum(1).max(), HZ.sum(1).max())),
        "rX": int(gf2.rank(HX)),
        "rZ": int(gf2.rank(HZ)),
    }
    sides, exhaustive = {}, True
    for side, H in (("X", HX), ("Z", HZ)):
        rows, scanned, exact = light_basis_exact(H, cap, max_enum)
        exhaustive &= exact
        if rows is None and not exact:
            found = None
            for seed in range(seeds):
                cand, _ = light_basis_sampled(H, cap, samples, seed)
                if cand:
                    found = cand
                    break
            rec[f"{side}_method"] = "sampling"
            rec[f"{side}_seeds"] = seeds
            sides[side] = found
        else:
            rec[f"{side}_method"] = "exact" if exact else "sampling"
            rec[f"{side}_elements"] = scanned
            sides[side] = rows
    rec["exact"] = exhaustive
    ok = sides["X"] is not None and sides["Z"] is not None
    # exact=True -> a basis at the target weight exists (and only then);
    # exact=False -> a basis was found at whatever weight the search reached.
    rec["basis_found"] = ok
    if ok:
        hx = np.array([[1 if (v >> j) & 1 else 0 for j in range(n)] for v in sides["X"]], dtype=np.uint8)
        hz = np.array([[1 if (v >> j) & 1 else 0 for j in range(n)] for v in sides["Z"]], dtype=np.uint8)
        w = int(max(hx.sum(1).max(), hz.sum(1).max()))
        rec.update(
            w=w,
            sup=int(hx.sum()) + int(hz.sum()),
            kr=int(compute_k(hx.astype(int), hz.astype(int))),
            css=bool(verify_css(hx.astype(int), hz.astype(int))),
        )
        rec["admissible"] = bool(w <= cap and rec["css"] and rec["sup"] <= 200000)
    else:
        rec["admissible"] = False
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain-codes", required=True, help="the paper's ecc/chain_codes directory")
    ap.add_argument("--out", required=True, help="directory for per-file JSON")
    ap.add_argument("--target-weight", type=int, default=CAP)
    ap.add_argument("--max-enum", type=int, default=MAX_ENUM)
    ap.add_argument("--seeds", type=int, default=16)
    ap.add_argument("--samples", type=int, default=6000)
    ap.add_argument("--only", default="", help="substring filter on the matrix file name")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    rows = []
    for fam in ("2_yoke", "3_yoke"):
        d = os.path.join(a.chain_codes, fam)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".txt") or f[:-4] in FILED:
                continue
            HX, HZ = dense(os.path.join(d, f))
            if max(HX.sum(1).max(), HZ.sum(1).max()) > a.target_weight and a.only in f:
                rows.append((fam, f))
    print(
        f"{len(rows)} matrices over w = {a.target_weight}; filed/dominated from this family: {len(FILED)}", flush=True
    )

    good = []
    for i, (fam, f) in enumerate(rows, 1):
        rec = analyse(os.path.join(a.chain_codes, fam, f), a.target_weight, a.samples, a.seeds, a.max_enum)
        json.dump(rec, open(os.path.join(a.out, f"{f[:-4]}.json"), "w"), indent=1)
        print(
            f"[{i}/{len(rows)}] {fam}/{f} r={rec['rX']}/{rec['rZ']} "
            f"method={rec['X_method']}/{rec['Z_method']} "
            f"basis={rec['basis_found']} "
            f"w={rec.get('w')} ({rec['seconds']}s)",
            flush=True,
        )
        if rec["admissible"]:
            good.append(rec)

    print(f"\n{len(good)} of {len(rows)} reach w <= {a.target_weight}")
    for r in good:
        print(f"  {r['file']} n={r['n']} k={r['kr']} d={r['d']} w0={r['w0']} -> w={r['w']} sup={r['sup']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
