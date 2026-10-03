"""Tests for the exhaustive small CSS-code census."""

import os
import sys
import types

import numpy as np
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "kit"))
sys.path.insert(0, os.path.join(_HERE, "..", "verify"))

import census_css


def test_rref_subspaces_are_unique_and_complete_through_six_qubits():
    expected = [1, 2, 5, 16, 67, 374, 2825]
    for n, count in enumerate(expected):
        spaces = list(census_css._rref_subspaces(n))
        assert len(spaces) == count
        assert len(set(spaces)) == count
        assert all(census_css._rref_masks(space, n) == space for space in spaces)


def test_small_code_classes_quotient_qubit_permutations_and_global_duality():
    all_classes = list(census_css.iter_css_classes(2, k_min=0))
    encoded_classes = list(census_css.iter_css_classes(2, k_min=1))

    assert len(all_classes) == 6
    assert len(encoded_classes) == 3
    assert all(k == 2 - len(x_rows) - len(z_rows) for x_rows, z_rows, k in all_classes)
    assert all(census_css._orthogonal(x_rows, z_rows) for x_rows, z_rows, _ in all_classes)


def test_exact_distance_retries_with_and_preserves_refuting_witness(monkeypatch):
    doc = {
        "distance": {
            "d": 3,
            "X": {"value": 3, "witness": [0, 1, 2]},
            "Z": {"value": 3, "witness": [0, 1, 2]},
        }
    }
    calls = []

    def make_submission(*args, **kwargs):
        return doc

    def certify(current_doc, tlim):
        calls.append((current_doc["distance"]["d"], tlim))
        if len(calls) == 1:
            return {
                "d_exact": False,
                "sides": {"X": {"status": "SAT", "witness": [1]}},
            }
        return {"d_exact": True, "sides": {"X": {"status": "UNSAT"}, "Z": {"status": "UNSAT"}}}

    monkeypatch.setattr(census_css, "make_submission", make_submission)
    monkeypatch.setattr(census_css, "_load_sat_certifier", lambda: types.SimpleNamespace(certify=certify))

    result = census_css.exact_css_distance(np.zeros((0, 2)), np.zeros((0, 2)), tlim=7)

    assert result["exact"]
    assert result["d"] == 1
    assert result["distance"]["X"]["witness"] == [1]
    assert calls == [(3, 7), (1, 7)]


def test_cli_defaults_and_parameter_ranges():
    defaults = census_css._parse_args([])
    assert (defaults.n_min, defaults.n_max) == (1, 6)
    assert (defaults.k_min, defaults.k_max) == (1, None)
    assert (defaults.d_min, defaults.d_max) == (3, None)

    selected = census_css._parse_args(
        [
            "--n-min",
            "4",
            "--n-max",
            "6",
            "--k-min",
            "2",
            "--k-max",
            "3",
            "--d-min",
            "3",
            "--d-max",
            "5",
        ]
    )
    assert (selected.n_min, selected.n_max) == (4, 6)
    assert (selected.k_min, selected.k_max) == (2, 3)
    assert (selected.d_min, selected.d_max) == (3, 5)


def test_cli_rejects_inconsistent_bounds_and_unsupported_n():
    with pytest.raises(SystemExit):
        census_css._parse_args(["--n-min", "7", "--n-max", "6"])
    with pytest.raises(SystemExit):
        census_css._parse_args(["--n-max", str(census_css.MAX_N + 1)])
    with pytest.raises(SystemExit):
        census_css._parse_args(["--n-max", "7", "--canonicalizer", "permutation"])
    with pytest.raises(ValueError, match="between 1 and"):
        list(census_css.iter_css_classes(census_css.MAX_N + 1))
    with pytest.raises(ValueError, match="stops at n = 6"):
        list(census_css.iter_css_classes(7, canonicalizer="permutation"))


def _permute(mask, image):
    out = 0
    for q, target in enumerate(image):
        if (mask >> q) & 1:
            out |= 1 << target
    return out


def test_nauty_and_permutation_canonicalizers_agree_through_five_qubits():
    pytest.importorskip("pynauty")
    expected = [1, 3, 11, 37, 126]
    for n, count in enumerate(expected, start=1):
        nauty = list(census_css.iter_css_classes(n, canonicalizer="nauty"))
        permutation = list(census_css.iter_css_classes(n, canonicalizer="permutation"))
        assert len(nauty) == len(permutation) == count
        # the two canonicalizers pick different representatives, so compare
        # the classes through the nauty key of each permutation representative
        keys = {census_css._nauty_pair_key(x, z, n) for x, z, _ in nauty}
        assert keys == {census_css._nauty_pair_key(x, z, n) for x, z, _ in permutation}
        assert all(census_css._orthogonal(x, z) and k == n - len(x) - len(z) for x, z, k in nauty)


def test_nauty_pair_key_is_invariant_under_permutation_and_duality_and_separates_classes():
    pytest.importorskip("pynauty")
    import itertools

    n = 5
    classes = list(census_css.iter_css_classes(n, canonicalizer="nauty"))
    keys = [census_css._nauty_pair_key(x, z, n) for x, z, _ in classes]
    assert len(set(keys)) == len(classes)
    rng = np.random.default_rng(2040)
    for (x, z, _), key in zip(classes, keys):
        for _ in range(3):
            image = tuple(int(i) for i in rng.permutation(n))
            px = tuple(_permute(row, image) for row in x)
            pz = tuple(_permute(row, image) for row in z)
            assert census_css._nauty_pair_key(px, pz, n) == key
            assert census_css._nauty_pair_key(pz, px, n) == key
    # every permutation of one asymmetric pair, not just a sample
    x, z = (0b00111,), (0b11100,)
    key = census_css._nauty_pair_key(x, z, n)
    for image in itertools.permutations(range(n)):
        px = tuple(_permute(row, image) for row in x)
        pz = tuple(_permute(row, image) for row in z)
        assert census_css._nauty_pair_key(px, pz, n) == key


def test_perp_basis_and_subspaces_cover_the_orthogonal_complement():
    n = 6
    for rows in census_css._rref_subspaces(n, 2):
        basis = census_css._perp_basis(rows, n)
        assert len(basis) == n - 2
        assert all((b & r).bit_count() % 2 == 0 for b in basis for r in rows)
        subspaces = list(census_css._subspaces_of(basis))
        assert len(subspaces) == 1 + 15 + 35 + 15 + 1  # Gaussian binomials of GF(2)^4
        assert all(census_css._orthogonal(rows, sub) for sub in subspaces)


def test_seven_qubit_census_contains_the_steane_code():
    pytest.importorskip("pynauty")
    n = 7
    classes = list(census_css.iter_css_classes(n, k_min=1, canonicalizer="nauty"))
    assert len(classes) == 1916
    hamming = (0b1010101, 0b0110011, 0b0001111)
    steane = census_css._nauty_pair_key(hamming, hamming, n)
    keys = {census_css._nauty_pair_key(x, z, n): k for x, z, k in classes}
    assert keys[steane] == 1
