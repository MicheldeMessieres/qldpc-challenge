"""Independent trivariate bicycle codes (Galimova, arXiv:2603.17703), from the paper's Table 1.

H_X = [A | B], H_Z = [B^T | A^T] over the group algebra of Z_l1 x Z_l2 x Z_l3,
with A and B sums of monomials x^a y^b z^c. The table gives every instance; the
one not already on the board, [[128,20,8]] on the 4 x 4 x 4 torus, rebuilds to
k = 20 and reads 8, and is dominated at check weight <= 8 by eight board
entries ([[128,21,8]], [[96,20,8]], [[104,30,8]] among them).

    python research/campaigns/openalex-harvest-2863/itb_codes.py
"""

import itertools
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path[:0] = [os.path.join(_ROOT, "verify"), os.path.join(_ROOT, "research", "kit")]
import gf2
import surrogate

INSTANCES = {
    "128-20-8": ((4, 4, 4), [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)], [(0, 0, 0), (3, 0, 0), (0, 3, 0), (0, 0, 3)]),
    "54-14-5": ((3, 3, 3), [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)], [(0, 0, 0), (2, 0, 0), (0, 2, 0), (0, 0, 2)]),
    "140-6-14": ((2, 5, 7), [(0, 0, 0), (0, 1, 3), (1, 1, 2)], [(0, 0, 0), (1, 4, 2), (1, 4, 3)]),
    "84-6-10": ((2, 3, 7), [(0, 0, 0), (0, 2, 4), (1, 1, 5)], [(0, 0, 0), (0, 0, 1), (1, 1, 3)]),
}


def build(dims, a_terms, b_terms):
    l1, l2, l3 = dims
    half = l1 * l2 * l3
    idx = {(i, j, k): t for t, (i, j, k) in enumerate(itertools.product(range(l1), range(l2), range(l3)))}

    def mono(a, b, c):
        M = np.zeros((half, half), dtype=np.int8)
        for (i, j, k), r in idx.items():
            M[r, idx[((i + a) % l1, (j + b) % l2, (k + c) % l3)]] ^= 1
        return M

    A = sum(mono(*t) for t in a_terms) % 2
    B = sum(mono(*t) for t in b_terms) % 2
    return np.hstack([A, B]).astype(np.int8), np.hstack([B.T, A.T]).astype(np.int8)


if __name__ == "__main__":
    for slug, (dims, a, b) in INSTANCES.items():
        HX, HZ = build(dims, a, b)
        n = HX.shape[1]
        k = n - gf2.rank(HX) - gf2.rank(HZ)
        w = surrogate.distance_rand_witness(HX, HZ, trials=200_000, seed=3, backend="fast", pair_depth=24, threads=4)
        print(f"{slug}: n={n} k={k} commute={not ((HX @ HZ.T) % 2).any()} RIS 200k -> {w.weight}")
