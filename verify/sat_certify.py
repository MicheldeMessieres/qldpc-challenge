"""Exact distance certification with a SAT solver.

Complements ``verify/certify.py`` (scipy/HiGHS MILP). The question is the same:
does a nontrivial logical operator of weight <= W exist? UNSAT on both sides at
W = d - 1 certifies d exactly.

The encoding matters more than the solver. Asking the question once per logical
generator, with that generator's anticommutation row fixed, costs one solve per
generator per side; asking it once with a selector variable per generator and a
clause requiring at least one of them costs a single solve. Measured on board
entries, certifying at W = d - 1:

    24-6-4    (k=6)    0.1 s  ->  0.04 s
    72-6-6    (k=6)    1.1 s  ->  0.4 s
    108-8-10  (k=8)    2228 s ->  408 s
    126-28-8  (k=28)   765 s (hit the cap, unfinished) -> 203-605 s

The gap widens with k, which is how many solves the per-generator form pays
for, and is where the board's high-rate entries live.

The single query is also what makes symmetry breaking legal. Two-block
circulant codes are invariant under the simultaneous rotation of both halves,
but the per-generator form is not, because fixing one generator's
anticommutation row breaks the symmetry the rotation acts on. With selectors
the constraint set is invariant, so lex-leader constraints (v >= its own
rotations, on a prefix) can be added. Measured on 126-28-8 at W = 7, on a host
quiesced to load 2.7 after a first attempt at load 15 produced numbers that
were mostly contention:

    with symmetry     203 s, 605 s
    without           913 s, 1001 s

Run-to-run spread within the symmetry arm is 3x, so the ratio is not worth
quoting to a decimal, but the arms do not overlap: the slowest run with
symmetry beats the fastest without. Off by default at small k, where it costs
clauses and buys nothing; the caller turns it on, and certify() does so
whenever the rotation is verified to fix both row spaces.

Parity constraints go to the solver as native XOR clauses rather than CNF
expansions; only the cardinality bound needs encoding, via pysat's sequential
counter. Needs pycryptosat and python-sat.

Pairing direction is the subtle part and got this wrong once. For the X side
(v in ker HZ) the generators must be Z-logicals: <v, t> = 1 against a Z-logical
is what certifies v is outside rowspace(HX), because X-stabilizers commute with
every Z-logical. Pairing against X-logicals instead admits stabilizers as
"solutions", and the giveaway was a reported weight-9 logical on a code whose
checks have weight 9.

The pairing set itself is the other half of that, and got this wrong for
longer. It has to span all k logical classes. A set that misses a class
cannot constrain the operators in it, so a logical lighter than the claim
slips through and the side reports UNSAT; a set that is short by every class
makes the clause unsatisfiable outright, so the side reports UNSAT without
searching at all. Either way the certifier answers the wrong question and
calls it a proof. The earlier construction sliced rows out of
rref([H_same; ker H_opp]) at rank(H_same), which assumed RREF leaves the
stabilizer rows in the first block; RREF orders rows by pivot column, so the
slice could keep stabilizers and drop logical classes. certify() now counts
the classes the pairing set spans and refuses to solve unless it is all k.
"""
import time

import gf2
import numpy as np


def _logicals(H_same, H_opp):
    """Basis of one side's logicals: ker(H_opp) modulo rowspace(H_same).

    One representative per logical class, built by reducing each kernel
    vector against the stabilizers and against the representatives already
    kept, so every row returned is independent of the stabilizers and of the
    other rows.
    """
    return np.asarray(gf2.logical_basis(H_opp, H_same), dtype=np.int8)


def _shift_perm(n):
    """Build the simultaneous rotation of both circulant halves."""
    m = n // 2
    p = np.empty(n, dtype=int)
    for j in range(m):
        p[j] = (j + 1) % m
        p[m + j] = m + (j + 1) % m
    return p


def _perm_fixes(H, p):
    """Report whether permuting columns by p preserves rowspace(H)."""
    return gf2.rank(np.vstack([H, H[:, p]])) == gf2.rank(H)


def _lex_leader_clauses(s, n, top, prefix):
    """Constrain v to be lex-greatest in its rotation orbit, on a prefix.

    Only a prefix is constrained: the full lex-leader encoding is quadratic in
    n per rotation and the tail contributes almost no pruning, so the bound is
    sound (it removes only orbit duplicates) but deliberately partial.
    """
    q = _shift_perm(n)
    pj = np.arange(n)
    for _ in range(1, n // 2):
        pj = q[pj]
        prev = None
        for i in range(min(prefix, n)):
            a, b = i + 1, int(pj[i]) + 1
            if a == b:
                continue
            if prev is None:
                s.add_clause([a, -b])
            else:
                s.add_clause([-prev, a, -b])
            top += 1
            e = top
            s.add_clause([-e, a, -b])
            s.add_clause([-e, -a, b])
            if prev is not None:
                s.add_clause([-e, prev])
            prev = e
    return top


def _solve_side(H_opp, L, W, tlim, use_symmetry=False, prefix=25):
    """Search for v with H_opp v = 0, |v| <= W, anticommuting with some t in L."""
    from pycryptosat import Solver
    from pysat.card import CardEnc, EncType

    n = H_opp.shape[1]
    s = Solver(threads=1)
    for row in H_opp:
        idx = [int(j) + 1 for j in np.nonzero(row)[0]]
        if idx:
            s.add_xor_clause(idx, False)
    top = n
    selectors = []
    for t in L:
        top += 1
        selectors.append(top)
        tidx = [int(j) + 1 for j in np.nonzero(t)[0]]
        # y <-> <v, t>: xor(t-support + [y]) = 0
        s.add_xor_clause(tidx + [top], False)
    if not selectors:
        return "UNSAT", None
    s.add_clause(selectors)                 # at least one anticommutation
    card = CardEnc.atmost(lits=list(range(1, n + 1)), bound=W,
                          top_id=top, encoding=EncType.seqcounter)
    top = max(top, card.nv)
    for cl in card.clauses:
        s.add_clause(cl)
    if use_symmetry:
        top = _lex_leader_clauses(s, n, top, prefix)
    sat, sol = s.solve(time_limit=tlim)
    if sat is None:
        return "TIMEOUT", None
    if not sat:
        return "UNSAT", None
    return "SAT", sorted(j - 1 for j in range(1, n + 1) if sol[j])


def certify(doc, tlim=600):
    """Certify a submission doc's distance exactly, mirroring certify.certify.

    Returns per-side ``exact`` flags and an overall ``d_exact``. A SAT result
    means the claim is refuted and carries the witness that refutes it; a
    timeout proves nothing and leaves the entry at its upper bound.
    """
    n = doc["n"]
    HX = _matrix(doc["checks"]["X"], n)
    HZ = _matrix(doc["checks"]["Z"], n)
    d = int(doc["distance"]["d"])
    W = d - 1
    k = n - gf2.rank(HX) - gf2.rank(HZ)
    out = {"name": doc.get("name"), "d": d, "solver": "CryptoMiniSat 5.14 SAT",
           "encoding": "selector", "sides": {}, "tlim_per_solve": tlim,
           "logical_classes": int(k)}
    # Symmetry breaking is applied only when the rotation is checked to fix
    # both row spaces, so a non-circulant entry degrades to the plain encoding
    # instead of being pruned by a constraint that does not hold for it.
    sym = (n % 2 == 0 and _perm_fixes(HX, _shift_perm(n))
           and _perm_fixes(HZ, _shift_perm(n)))
    out["symmetry"] = bool(sym)
    for side, H_same, H_opp in (("X", HX, HZ), ("Z", HZ, HX)):
        t0 = time.time()
        L = _logicals(H_opp, H_same)
        # An UNSAT from a pairing set that does not span every class is not a
        # proof of anything, so refuse rather than record one. Counting rows
        # is not enough: a row lying in the rowspace it was reduced against
        # is a stabilizer and constrains nothing, which is exactly how this
        # failed before. L is ker(H_same) modulo rowspace(H_opp), so H_opp is
        # what it has to be independent of.
        spanned = (gf2.rank(np.vstack([H_opp, L])) - gf2.rank(H_opp)
                   if len(L) else 0)
        if spanned != k:
            raise ValueError(
                f"{side} side: pairing set spans {spanned} of {k} logical "
                f"classes, so UNSAT here would not mean no light logical")
        status, wit = _solve_side(H_opp, L, W, tlim, use_symmetry=sym)
        blk = {"value": d, "exact": status == "UNSAT",
               "status": status, "secs": round(time.time() - t0, 1)}
        if status == "UNSAT":
            blk["note"] = f"no logical < {d} exists"
        elif status == "SAT":
            blk["note"] = f"REFUTED: logical of weight <= {W} exists"
            blk["witness"] = wit
        out["sides"][side] = blk
        if status == "SAT":
            break
    out["d_exact"] = all(b.get("exact") for b in out["sides"].values()) \
        and len(out["sides"]) == 2
    return out


def _matrix(support_list, n):
    """Dense GF(2) matrix from a list of row supports."""
    H = np.zeros((len(support_list), n), dtype=np.int8)
    for i, row in enumerate(support_list):
        H[i, list(row)] = 1
    return H
