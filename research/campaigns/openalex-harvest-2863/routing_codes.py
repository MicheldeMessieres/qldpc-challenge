"""Routing codes (Zhang et al., arXiv:2606.25330), rebuilt from the routing rule.

Torus Z_l x Z_m. Data qubits sit at i + j even, X syndromes at i odd and j
even, Z syndromes at i even and j odd. At step t every X syndrome at position
r swaps with the data qubit at r + v_t and every Z syndrome with the data qubit
at r + w_t; a syndrome's stabilizer is the set of data qubits it swapped with
over the T steps, so the check weight is T. w is the time reversal of v unless
the paper's Table 3 marks the row "identical". Every instance of Tables 3 and
4 rebuilds to its stated (n, k) with the stated d as the RIS reading; see the
fieldnote of 2026-10-07 for the readings and the board comparison.

    python research/campaigns/openalex-harvest-2863/routing_codes.py
"""

import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path[:0] = [os.path.join(_ROOT, "verify"), os.path.join(_ROOT, "research", "kit")]
import gf2
import surrogate


def build(ell, m, v, w=None):
    T = len(v)
    w = w or list(reversed(v))
    kind = {}
    for i in range(ell):
        for j in range(m):
            kind[(i, j)] = "D" if (i + j) % 2 == 0 else ("X" if (i % 2 == 1 and j % 2 == 0) else "Z")
    data_ids = {p: idx for idx, p in enumerate(sorted(p for p, kd in kind.items() if kd == "D"))}
    n = len(data_ids)
    xs = sorted(p for p, kd in kind.items() if kd == "X")
    zs = sorted(p for p, kd in kind.items() if kd == "Z")
    occ = {
        p: (("D", data_ids[p]) if kd == "D" else ((kd, xs.index(p)) if kd == "X" else (kd, zs.index(p))))
        for p, kd in kind.items()
    }
    supX = [set() for _ in xs]
    supZ = [set() for _ in zs]
    conflicts = 0
    for t in range(T):
        vt, wt = v[t], w[t]
        moves = []
        for p, o in occ.items():
            if o[0] == "X":
                moves.append((p, ((p[0] + vt[0]) % ell, (p[1] + vt[1]) % m), o))
            elif o[0] == "Z":
                moves.append((p, ((p[0] + wt[0]) % ell, (p[1] + wt[1]) % m), o))
        new = dict(occ)
        for p, q, o in moves:
            tgt = occ[q]
            if tgt[0] != "D":
                conflicts += 1
                continue
            (supX if o[0] == "X" else supZ)[o[1]].add(tgt[1])
            new[q] = o
            new[p] = tgt
        occ = new
    HX = np.zeros((len(xs), n), dtype=np.int8)
    HZ = np.zeros((len(zs), n), dtype=np.int8)
    for i, s in enumerate(supX):
        HX[i, list(s)] = 1
    for i, s in enumerate(supZ):
        HZ[i, list(s)] = 1
    return HX, HZ, n, conflicts


INST = [
    (
        "200-24-14",
        (20, 20),
        [(1, 0), (0, 1), (1, 0), (1, 0), (6, 1), (6, 1), (6, 1), (1, 0), (1, 0), (0, 1), (1, 0)],
        None,
    ),
    (
        "200-16-17",
        (40, 10),
        [(1, 0), (0, 1), (1, 0), (1, 0), (6, 1), (6, 1), (6, 1), (1, 0), (1, 0), (0, 1), (1, 0)],
        None,
    ),
    ("54-8-6", (18, 6), [(0, 1), (1, 0), (3, 0), (0, 1), (3, 0), (1, 0), (0, 1)], "same"),
    ("70-8-7", (14, 10), [(1, 0), (2, 1), (0, 1), (0, 1), (0, 1), (2, 1), (1, 0)], "same"),
    ("80-8-8", (16, 10), [(1, 0), (0, 1), (0, 1), (0, 1), (4, 1), (4, 1), (1, 0)], None),
    ("90-8-9", (18, 10), [(1, 0), (0, 1), (0, 1), (0, 1), (2, 1), (2, 1), (1, 0)], None),
    ("100-8-10", (20, 10), [(1, 0), (0, 1), (0, 1), (2, 1), (2, 1), (2, 1), (1, 0)], None),
    ("110-8-11", (22, 10), [(1, 0), (0, 1), (0, 1), (6, 1), (6, 1), (0, 1), (1, 0)], None),
    ("140-8-12", (28, 10), [(1, 0), (0, 1), (0, 1), (4, 1), (0, 1), (0, 1), (1, 0)], "same"),
    ("140-8-13", (28, 10), [(1, 0), (6, 1), (6, 1), (0, 1), (0, 1), (0, 1), (1, 0)], None),
]
import glob

os.makedirs(os.path.join(_ROOT, "research", "candidates"), exist_ok=True)
board = []
for f in glob.glob(os.path.join(_ROOT, "codes", "*.json")):
    d = json.load(open(f))
    if "X" in d["checks"]:
        board.append((f[6:-5], d["n"], d["k"], d["distance"]["d"], max(len(r) for s in "XZ" for r in d["checks"][s])))
out = {}
for slug, (ell, m), v, wmode in INST:
    HX, HZ, n, conf = build(ell, m, v, v if wmode == "same" else None)
    comm = not ((HX @ HZ.T) % 2).any()
    k = n - gf2.rank(HX) - gf2.rank(HZ)
    wmax = int(max(HX.sum(1).max(), HZ.sum(1).max()))
    trials = 2_000_000 if n >= 200 else 500_000
    t0 = time.time()
    wit = surrogate.distance_rand_witness(HX, HZ, trials=trials, seed=5, backend="fast", pair_depth=32, threads=4)
    dt = time.time() - t0
    dd = wit.weight
    doms = [
        b
        for b in board
        if b[4] <= wmax and b[1] <= n and b[2] >= k and b[3] >= dd and (b[1] < n or b[2] > k or b[3] > dd)
    ]
    same = [b for b in board if (b[1], b[2], b[3]) == (n, k, dd)]
    print(
        f"{slug:>10} n={n} k={k} w={wmax} commute={comm} conf={conf} | RIS {trials // 1000}k: {dd} ({dt:.0f}s) | dominated by {len(doms)} board entries at w<={wmax}: {[b[0] for b in doms[:4]]} | same params on board: {[b[0] for b in same]}",
        flush=True,
    )
    out[slug] = {
        "ell": ell,
        "m": m,
        "v": v,
        "w_same": wmode == "same",
        "n": n,
        "k": k,
        "w": wmax,
        "d_ris": dd,
        "trials": trials,
        "side": wit.side,
        "support": sorted(map(int, wit.support)),
        "X": [sorted(map(int, np.flatnonzero(r))) for r in HX],
        "Z": [sorted(map(int, np.flatnonzero(r))) for r in HZ],
    }
json.dump(out, open(os.path.join(_ROOT, "research", "candidates", "routing_codes.json"), "w"))
print("ROUTING DONE", flush=True)
