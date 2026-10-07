"""Stabilizers of a vine code (Nixon, McLauchlan and van Rest, arXiv:2606.20263) from its published stim circuit.

The Zenodo record 10.5281/zenodo.20746752 ships memory circuits for the
Figure 5 and Figure 11 patches. Data qubits are the ones prepared with RX at
t = 0 (an X-basis memory); measure and routing qubits start in |0>. Each
round-1 measurement, pulled back through the round's CX, CXSWAP and SWAP steps
to t = 0, is a stabilizer on the data: components on |0> qubits that read Z
are fixed and dropped, and anything else there would be a bug (none occurs).
Pass the directory of .stim files as the argument.

    python research/campaigns/openalex-harvest-2863/vine_extract.py <dir with Fig_*.stim>
"""

import collections
import glob
import json
import math
import os
import sys

import numpy as np
import stim

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path[:0] = [os.path.join(_ROOT, "verify"), os.path.join(_ROOT, "research", "kit")]
import gf2
import surrogate

UNITARY = {
    "H",
    "S",
    "S_DAG",
    "X",
    "Y",
    "Z",
    "CX",
    "CNOT",
    "CZ",
    "CY",
    "SWAP",
    "CXSWAP",
    "SWAPCX",
    "ISWAP",
    "ISWAP_DAG",
    "SQRT_X",
    "SQRT_X_DAG",
    "SQRT_Y",
    "SQRT_Y_DAG",
    "C_XYZ",
    "C_ZYX",
    "I",
    "CZSWAP",
}


def analyze(path):
    c = stim.Circuit.from_file(path).without_noise().flattened()
    nq = c.num_qubits
    coords = {q: tuple(v) for q, v in c.get_final_qubit_coordinates().items()}
    insts = list(c)
    reset0 = {}
    i = 0
    while i < len(insts) and insts[i].name in (
        "R",
        "RX",
        "RZ",
        "TICK",
        "QUBIT_COORDS",
        "DETECTOR",
        "OBSERVABLE_INCLUDE",
        "SHIFT_COORDS",
    ):
        if insts[i].name in ("R", "RZ"):
            for t in insts[i].targets_copy():
                reset0[t.value] = "Z"
        if insts[i].name == "RX":
            for t in insts[i].targets_copy():
                reset0[t.value] = "X"
        i += 1
    data = sorted(q for q, b in reset0.items() if b == "X")  # X-memory: data prepared in |+>
    if not data:
        data = sorted(q for q, b in reset0.items() if b == "Z")
    tab = stim.Tableau(nq)
    ops = []
    for ins in insts[i:]:
        name = ins.name
        if name in ("TICK", "QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "SHIFT_COORDS"):
            continue
        if name in UNITARY:
            if ops:
                break
            g = stim.Tableau.from_named_gate("CX" if name == "CNOT" else name)
            targs = [t.value for t in ins.targets_copy()]
            k = len(g)
            for a in range(0, len(targs), k):
                tab.append(g, targs[a : a + k])
            continue
        if name in ("M", "MR", "MX", "MRX", "MZ", "MRZ"):
            basis = "X" if "X" in name else "Z"
            inv = tab.inverse()
            for t in ins.targets_copy():
                q = t.value
                P = inv.z_output(q) if basis == "Z" else inv.x_output(q)
                ops.append((q, basis, P))
            continue
        if name in ("R", "RX", "RZ"):
            if ops:
                break
            continue
        raise ValueError(name)
    dset = set(data)
    X = []
    Z = []
    mixed = 0
    bad = collections.Counter()
    for q, basis, P in ops:
        s = str(P)
        s = s[1:] if s[0] in "+-" else s
        comps = {}
        for qi, ch in enumerate(s):
            if ch == "_":
                continue
            if qi in dset:
                comps[qi] = ch
                continue
            rb = reset0.get(qi, "Z")  # unreset qubits start in |0>
            if ch == rb:
                continue
            bad[(rb, ch)] += 1
        kinds = set(comps.values())
        if kinds == {"X"}:
            X.append(sorted(comps))
        elif kinds == {"Z"}:
            Z.append(sorted(comps))
        elif comps:
            mixed += 1
    return nq, coords, data, X, Z, mixed, bad


for path in sorted(glob.glob(os.path.join(sys.argv[1], "Fig_*.stim"))):
    nq, coords, data, X, Z, mixed, bad = analyze(path)
    idx = {q: i for i, q in enumerate(data)}
    n = len(data)
    Xr = [[idx[q] for q in r] for r in X]
    Zr = [[idx[q] for q in r] for r in Z]

    def M(rows):
        H = np.zeros((len(rows), n), dtype=np.int8)
        for i, r in enumerate(rows):
            H[i, r] = 1
        return H

    HX, HZ = M(Xr), M(Zr)
    comm = not ((HX @ HZ.T) % 2).any() if Xr and Zr else None
    k = n - gf2.rank(HX) - gf2.rank(HZ) if comm else None
    co = [coords[q] for q in data]
    diam = 0
    for rows in (Xr, Zr):
        for r in rows:
            for a in range(len(r)):
                for b in range(a + 1, len(r)):
                    diam = max(diam, math.dist(co[r[a]], co[r[b]]))
    line = f"{path.split('/')[-1]}: qubits {nq}, data {n}, X {len(Xr)} Z {len(Zr)} mixed {mixed} bad {dict(bad)}, commute {comm}, k {k}, w {sorted(set(HX.sum(1)) | set(HZ.sum(1)))}, max diam {diam:.2f}"
    if comm and k and k > 0:
        w = surrogate.distance_rand_witness(HX, HZ, trials=300_000, seed=2, backend="fast", pair_depth=24, threads=4)
        line += f", RIS 300k d<= {w.weight}"
        json.dump(
            {
                "file": path.split("/")[-1],
                "n": n,
                "k": k,
                "d_ris": w.weight,
                "X": Xr,
                "Z": Zr,
                "coords": [list(c) for c in co],
            },
            open(
                os.path.join(
                    _ROOT, "research", "candidates", "vine_" + os.path.basename(path).replace(".stim", ".json")
                ),
                "w",
            ),
        )
    print(line, flush=True)
