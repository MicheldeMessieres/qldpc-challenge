"""Canonical lifted-product codes of Zheng, Zheng, Jiang and Xu (arXiv:2607.28605), from the appendix matrices.

LP_l(A, A*) with R = F2[x]/(x^ell + 1): H_X = B(A (x) I, I (x) B) and
H_Z^T = B(I (x) B ; A (x) I) with B = A* (transpose, x -> x^-1), B(.) the
circulant binarization (their Eq. 5). The two in-range instances are given
explicitly in the paper's appendix (Example "canonical matrices" and
Eq. saturating-C28-matrix), not in the Cain et al. paper the main text cites,
whose Appendix A carries only the n > 1000 instances.

    python research/campaigns/openalex-harvest-2863/lp_canonical.py
"""

import glob
import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path[:0] = [os.path.join(_ROOT, "verify"), os.path.join(_ROOT, "research", "kit")]
import gf2
import surrogate


def circ(poly, ell):
    M = np.zeros((ell, ell), dtype=np.int8)
    for e in poly:
        for i in range(ell):
            M[i, (i + e) % ell] ^= 1
    return M


def conj(poly, ell):
    return [(-e) % ell for e in poly]


def binarize(Mpoly, ell):  # Mpoly: list of lists of exponent lists
    rows = len(Mpoly)
    cols = len(Mpoly[0])
    out = np.zeros((rows * ell, cols * ell), dtype=np.int8)
    for i in range(rows):
        for j in range(cols):
            out[i * ell : (i + 1) * ell, j * ell : (j + 1) * ell] = circ(Mpoly[i][j], ell)
    return out


def kron_poly(
    A, B
):  # A ⊗_R B for polynomial matrices (lists of exponent lists), product of ring elements = polynomial multiplication
    ra, ca = len(A), len(A[0])
    rb, cb = len(B), len(B[0])
    out = [[None] * (ca * cb) for _ in range(ra * rb)]
    for i in range(ra):
        for j in range(ca):
            for p in range(rb):
                for q in range(cb):
                    prod = []
                    for e1 in A[i][j]:
                        for e2 in B[p][q]:
                            prod.append(e1 + e2)
                    out[i * rb + p][j * cb + q] = prod
    return out


def ident(m):
    return [[[0] if i == j else [] for j in range(m)] for i in range(m)]


def transpose_conj(A, ell):
    return [[conj(A[i][j], ell) for i in range(len(A))] for j in range(len(A[0]))]


def lp(A, ell):
    B = transpose_conj(A, ell)  # B = A^*  (n_A x m_A)
    mA, nA = len(A), len(A[0])
    mB, nB = len(B), len(B[0])
    HX = np.hstack([binarize(kron_poly(A, ident(mB)), ell), binarize(kron_poly(ident(mA), B), ell)])
    HZT = np.vstack([binarize(kron_poly(ident(nA), B), ell), binarize(kron_poly(A, ident(nB)), ell)])
    HZ = HZT.T.copy()
    return HX % 2, HZ % 2


CODES = {
    "468-36-20": (36, [[[0], [0, 11, 29], [0]], [[0], [], [8, 13, 16, 17]]]),
    "952-112-17": (
        28,
        [[[8, 11, 22], [18], [1], [], []], [[], [4], [], [14, 19], [18, 25]], [[], [], [12], [1, 10], [3, 27]]],
    ),
}
os.makedirs(os.path.join(_ROOT, "research", "candidates"), exist_ok=True)
board = []
for f in glob.glob(os.path.join(_ROOT, "codes", "*.json")):
    d = json.load(open(f))
    if "X" in d["checks"]:
        board.append((f[6:-5], d["n"], d["k"], d["distance"]["d"], max(len(r) for s in "XZ" for r in d["checks"][s])))
out = {}
for slug, (ell, A) in CODES.items():
    HX, HZ = lp(A, ell)
    n = HX.shape[1]
    comm = not ((HX @ HZ.T) % 2).any()
    k = n - gf2.rank(HX) - gf2.rank(HZ)
    wmax = int(max(HX.sum(1).max(), HZ.sum(1).max()))
    t0 = time.time()
    w = surrogate.distance_rand_witness(HX, HZ, trials=500_000, seed=5, backend="fast", pair_depth=32, threads=4)
    dt = time.time() - t0
    doms = [
        b
        for b in board
        if b[4] <= wmax
        and b[1] <= n
        and b[2] >= k
        and b[3] >= w.weight
        and (b[1] < n or b[2] > k or b[3] > w.weight or b[4] < wmax)
    ]
    print(
        f"{slug}: n={n} k={k} w={wmax} commute={comm} | RIS 500k: {w.weight} ({dt:.0f}s) | dominated by {len(doms)}: {[b[0] for b in doms[:4]]}",
        flush=True,
    )
    out[slug] = {
        "ell": ell,
        "A": A,
        "n": n,
        "k": int(k),
        "w": wmax,
        "d_ris": w.weight,
        "side": w.side,
        "support": sorted(map(int, w.support)),
        "X": [sorted(map(int, np.flatnonzero(r))) for r in HX],
        "Z": [sorted(map(int, np.flatnonzero(r))) for r in HZ],
    }
json.dump(out, open(os.path.join(_ROOT, "research", "candidates", "lp_codes.json"), "w"))
print("LP DONE", flush=True)
