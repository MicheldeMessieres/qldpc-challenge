"""Two-layer layout annealer for board codes.

Python twin of the JavaScript annealer used for the search; both give the same layout for the same inputs.

Places every qubit of a CSS code on a unit-spacing triangular ("hex") or square lattice, at most ``cap``
qubits per site (two layers -> cap 2), so that every check (X and Z rows) has Euclidean diameter <= 7.0,
the board's local-2d-bilayer cap. Same family of method as the board's research/local2d/hinge_anneal.py
(@MathysRennela, #2156) and research/local2d/fold_layout.py; separate implementation:

    cost  = sum over checks of max(0, diam^2 - T^2)      (T slightly under the cap, default 6.95)
    moves = move one qubit to a random site within radius 3.2, or swap it with a qubit there
    schedule: one long Metropolis chain, temperature 4.0 -> 0.01 geometrically over all iterations
    start: a random permutation of the qubits packed around the centre of the patch

Deterministic: the same code, iterations, seed, T and grid give the same layout (32-bit xorshift).
Reproduce codes/510-16-26.json with --iters 3e7 --seed 1
(defaults T 6.95, hex grid).
The board verifier (verify/qldpc_verify.py), not this script, decides whether a layout is valid.

Design notes (measured on this script, October 2026). On tight codes, where the 7.0 cap is only just reachable
(e.g. codes/184-50-10.json, codes/558-14-28.json), each of these was necessary in one-change-at-a-time tests
(3 seeds each, 3e7 moves): (1) a SOFT over-cap penalty on the same scale as the temperature, so the search can
briefly cross the cap and come back (multiplying the penalty by 1e6 made every run fail); (2) a triangular lattice
(a square lattice made every run fail); (3) long single chains (30 chains of 1e6 moves succeeded in only 5/30 and
10/30 runs). The margin T = 6.95 vs 7.0 made no difference. In a variant of this script, moving the target linearly
from 7.6 down to T during the run reduced the final radius on harder codes, but did not reach 7.0 for codes such as
codes/672-20-32.json.

Credits: simulated annealing (Kirkpatrick, Gelatt and Vecchi, Science 220, 671, 1983); the xorshift random-number
generator (Marsaglia, J. Stat. Softw. 8(14), 2003); hinge-cost annealing for this cap, research/local2d/hinge_anneal.py
(@MathysRennela, #2156); the plain-radius layout annealer research/local2d/fold_layout.py.

usage: python research/local2d/tri_hinge_anneal.py codes/<n>-<k>-<d>.json --out layout.json
           [--iters 3e7] [--seed 1] [--T 6.95] [--grid hex]
"""

import argparse
import json
import math
import sys
import time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("doc", help="board entry codes/<n>-<k>-<d>.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--iters", type=float, default=2e7)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--T", type=float, default=6.95)
    ap.add_argument("--grid", choices=("hex", "square"), default="hex")
    ap.add_argument("--cap", type=int, default=2, help="qubits per site (layers)")
    a = ap.parse_args(argv)
    doc = json.load(open(a.doc))
    n, checks = doc["n"], doc["checks"]["X"] + doc["checks"]["Z"]
    ITERS, T, CAP = int(a.iters), a.T, a.cap
    M = 0xFFFFFFFF
    seed = a.seed & M

    def rnd():
        nonlocal seed
        seed = (seed ^ (seed << 13)) & M
        seed = seed ^ (seed >> 17)
        seed = (seed ^ (seed << 5)) & M
        return seed / 4294967296

    S3 = math.sqrt(3) / 2
    e2 = (0.5, S3) if a.grid == "hex" else (0.0, 1.0)
    L = math.ceil(math.sqrt(n / CAP * 1.2))
    minx = miny = 0.0
    maxx, maxy = float(L), L * (S3 if a.grid == "hex" else 1.0)
    pad = 3
    sx, sy = [], []
    for v in range(math.floor((miny - pad) / e2[1]), math.ceil((maxy + pad) / e2[1]) + 1):
        y, off = v * e2[1], v * e2[0]
        for u in range(math.floor(minx - pad - off), math.ceil(maxx + pad - off) + 1):
            sx.append(u + off)
            sy.append(y)
    NS = len(sx)
    R = 3.2
    cell = {}
    for s in range(NS):
        cell.setdefault((math.floor(sx[s] / R), math.floor(sy[s] / R)), []).append(s)
    near = [[] for _ in range(NS)]
    for s in range(NS):
        cx, cy = math.floor(sx[s] / R), math.floor(sy[s] / R)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for t in cell.get((cx + dx, cy + dy), ()):
                    if t != s and (sx[t] - sx[s]) ** 2 + (sy[t] - sy[s]) ** 2 <= R * R:
                        near[s].append(t)

    site, occ, slot = [0] * n, [0] * NS, [[] for _ in range(NS)]
    cxm, cym = (minx + maxx) / 2, (miny + maxy) / 2
    order = [s for _, s in sorted(((sx[s] - cxm) ** 2 + (sy[s] - cym) ** 2, s) for s in range(NS))]
    perm = list(range(n))
    for i in range(n - 1, 0, -1):
        j = math.floor(rnd() * (i + 1))
        perm[i], perm[j] = perm[j], perm[i]
    k = 0
    for s in order:
        for _ in range(CAP):
            if k >= n:
                break
            q = perm[k]
            k += 1
            site[q] = s
            occ[s] += 1
            slot[s].append(q)
        if k >= n:
            break
    qc = [[] for _ in range(n)]
    for i, c in enumerate(checks):
        for q in c:
            qc[q].append(i)
    T2 = T * T

    def diam2(c):
        m = 0.0
        for ia in range(len(c)):
            sa = site[c[ia]]
            for ib in range(ia + 1, len(c)):
                sb = site[c[ib]]
                d = (sx[sa] - sx[sb]) ** 2 + (sy[sa] - sy[sb]) ** 2
                m = max(m, d)
        return m

    def hinge(d):
        return d - T2 if d > T2 else 0

    cd = [diam2(c) for c in checks]
    cost = 0
    for i in range(len(checks)):
        cost += hinge(cd[i])

    def maxD():
        return math.sqrt(max(cd))

    best_cost, best_r, best_site = cost, maxD(), site[:]
    touched, stamp = [0] * len(checks), 1
    temp = 4.0
    alpha = (0.01 / temp) ** (1 / ITERS)
    t0 = time.time()
    for it in range(ITERS):
        q = math.floor(rnd() * n)
        s0 = site[q]
        nb = near[s0]
        s1 = nb[math.floor(rnd() * len(nb))]
        q2 = -1
        if occ[s1] >= CAP or (occ[s1] > 0 and rnd() < 0.5):
            q2 = slot[s1][math.floor(rnd() * occ[s1])]
        site[q] = s1
        if q2 >= 0:
            site[q2] = s0
        stamp += 1
        tl = []
        for c in qc[q]:
            if touched[c] != stamp:
                touched[c] = stamp
                tl.append(c)
        if q2 >= 0:
            for c in qc[q2]:
                if touched[c] != stamp:
                    touched[c] = stamp
                    tl.append(c)
        delta = 0
        newd = []
        for c in tl:
            d = diam2(checks[c])
            newd.append(d)
            delta += hinge(d) - hinge(cd[c])
        if delta <= 0 or rnd() < math.exp(-delta / temp):
            for i in range(len(tl)):
                cd[tl[i]] = newd[i]
            slot[s0].remove(q)
            slot[s1].append(q)
            if q2 >= 0:
                slot[s1].remove(q2)
                slot[s0].append(q2)
            else:
                occ[s0] -= 1
                occ[s1] += 1
            cost += delta
            if cost < best_cost - 1e-9 or (cost <= 1e-9 and it % 1000 == 0):
                r = maxD()
                if cost < best_cost - 1e-9 or r < best_r:
                    best_cost, best_r, best_site = cost, r, site[:]
        else:
            site[q] = s0
            if q2 >= 0:
                site[q2] = s1
        temp *= alpha
        if it % 2000000 == 0:
            print(
                f"it {it} temp {temp:.3f} cost {cost:.2f} best {best_cost:.2f} r {best_r:.3f} {time.time() - t0:.0f}s",
                file=sys.stderr,
                flush=True,
            )
    coords = [[sx[s], sy[s]] for s in best_site]
    json.dump(
        {
            "radius": best_r,
            "cost": best_cost,
            "cap": CAP,
            "grid": a.grid,
            "T": T,
            "iters": ITERS,
            "seed": a.seed,
            "coordinates": coords,
        },
        open(a.out, "w"),
    )
    print(json.dumps({"radius": best_r, "cost": best_cost}))


if __name__ == "__main__":
    main()
