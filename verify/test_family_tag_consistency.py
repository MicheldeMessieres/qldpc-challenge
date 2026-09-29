"""A construction that names its family must carry that family's tag.

`family` is self-declared and used to filter, never to rank, so a wrong tag
never invalidates a claim. What it does is hide the entry: every query by
family misses it, including the ones that set campaign targets.

That is not hypothetical. 21 pair-partition CPM codes were tagged
`lifted-product` while their own construction text named the family and cited
its paper. One of them, `904-230-22`, is the `unrestricted x weight-8` leader
at kd^2/n 123.14, and a campaign was scoped to hunt d=21 in that family for a
target near 112, i.e. to look for something strictly worse than the board
already held, because the leader was invisible to the query that set the
target.

This checks the direction that costs something: if the construction text
names a family unambiguously, the tag has to agree. It deliberately does not
check the converse, because a construction is free not to mention its family.
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

# (tag, pattern the construction text uses when it is that family). Anchored
# on how the papers are cited rather than on prose, since the same family is
# written several ways: "Pair-partition CPM", "Cyclic all-one pair-partition
# CPM", and "Okada-Kasai pair-partition CPM" are all one thing.
RULES = [
    ("pair-partition-cpm", re.compile(r"pair.partition|2607\.14091", re.I)),
    ("bivariate-bicycle", re.compile(r"\bbivariate[- ]bicycle\b", re.I)),
    ("generalized-bicycle", re.compile(r"\bgenerali[sz]ed[- ]bicycle\b", re.I)),
]

# Two families can both be true of one code: the open-boundary tile codes are
# built from a bivariate-bicycle construction and say so, and `tile` is the
# more specific tag. So a construction naming family F is only a contradiction
# when it does not also name the tag the entry actually carries. That keeps
# this a tripwire for a tag nobody can find the code by, rather than a
# taxonomy that argues with submitters about which parent is primary.
OPENING = 60


def _entries():
    root = os.path.join(_ROOT, "codes")
    for fname in sorted(os.listdir(root)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(root, fname), encoding="utf-8") as f:
            yield fname[:-5], json.load(f)


def test_a_construction_that_names_its_family_carries_that_tag():
    problems = []
    for slug, doc in _entries():
        prov = doc.get("provenance") or {}
        con = str(prov.get("construction") or "")
        if not con:
            continue
        tag = doc.get("family")
        if not tag:
            continue          # a missing tag is a gap, not a contradiction
        if tag.replace("-", " ") in con.lower().replace("-", " "):
            continue          # the construction names the tag it carries
        for family, pat in RULES:
            if tag == family:
                break
            if pat.search(con[:OPENING]):
                problems.append(
                    f"  {slug}: construction opens on {family!r} but "
                    f"family={tag!r}\n      {con[:OPENING].strip()}")
                break
    assert not problems, (
        f"{len(problems)} entries whose family tag contradicts their own "
        "construction text; a filter by family will not find them:\n"
        + "\n".join(problems[:20]))
