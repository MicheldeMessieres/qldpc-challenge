"""Coordination primitives for concurrent agentic sessions (issue #2314).

Several independent sessions now run campaigns against this repository at the
same time, and the kit was written for one executor. ``save_submission`` takes
a caller-chosen path and overwrites whatever is already there, so two sessions
that find the same parameters silently clobber each other's staged candidate,
and nothing stops both of them from paying separately to confirm an identical
code through the slowest step in the loop.

This module is outside the trust spine and cannot reach into it:

* It never produces a verdict. :func:`validate_cached` calls
  ``verify/validate_candidate.py`` exactly as a session would, and all it adds
  is not paying twice for the one step of that call that does not depend on
  the board.
* The cache holds the refutation and nothing else. ``dedup`` and ``novelty``
  are statements about ``codes/`` at a point in time, so they are recomputed
  on every call, always, and a cache hit still runs the gate. What it skips is
  the random search, which reads only the candidate.
* Every cached entry carries the sha256 of the validator source that produced
  it, and is served only while that still matches: the gate changed, so its
  old answer is an opinion from a previous version of the rules.
* A served refutation can only subtract. ``passed`` is the gate's own value
  for this board ANDed with "not refuted", so reusing an entry can turn a pass
  into a failure and never the other way around.
* The cache lives under the gitignored ``research/candidates/``. Nothing in it
  can be cited as evidence, and deleting it costs compute, never correctness.

    from coordination import run_id, staging_dir, unique_path, validate_cached
    out = staging_dir()                        # research/candidates/<run_id>/
    save_submission(doc, unique_path(os.path.join(out, "72-12-6.json"), doc))
    verdict, reused = validate_cached(doc)     # gate now, refutation reused
"""
import errno
import hashlib
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CANDIDATES = os.path.join(_ROOT, "research", "candidates")
VALIDATOR_SOURCE = os.path.join(_ROOT, "verify", "validate_candidate.py")
CACHE_DIRNAME = ".verdicts"
RUN_ID_ENV = "QLDPC_RUN_ID"
ENTRY_VERSION = 2

# Document fields the gate reads only for their schema validity and never by
# value, so two sessions that build the same matrices on different days under
# different handles land on the same cache key. Everything outside this list
# stays in the key, including ``provenance.model`` and ``provenance.novelty``,
# which the verifier does check by value. The rest of the guarantee is in
# :meth:`VerdictCache.entry`, which refuses to serve anything not itself
# schema-valid, so a malformed date cannot borrow a well-formed doc's verdict.
UNKEYED_TOP = ("name",)
UNKEYED_PROVENANCE = ("authors", "construction", "references", "date", "notes")


class CandidateCollision(RuntimeError):
    """A staging write that would have destroyed another session's candidate."""


# -- identity and staging -------------------------------------------------

def run_id():
    """Identify this executor: ``$QLDPC_RUN_ID`` if set, else host-pid-time.

    A session that wants two runs to share a staging directory, or a harness
    that wants a readable name in the tree, sets the environment variable. The
    fallback is unique per process on one machine and close enough to unique
    across machines that two sessions do not collide by accident.
    """
    forced = os.environ.get(RUN_ID_ENV)
    if forced and forced.strip():
        return _slug(forced.strip())
    host = _slug(socket.gethostname().split(".")[0] or "host")
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{host}-{os.getpid()}"


def _slug(text):
    keep = [c if (c.isalnum() or c in "-_.") else "-" for c in str(text)]
    return "".join(keep).strip("-") or "run"


def staging_dir(rid=None, *, root=None, create=True):
    """Return ``research/candidates/<run_id>/``, this executor's own shelf.

    Namespacing staging output by run is the whole of the collision fix: two
    sessions writing ``<n>-<k>-<d>.json`` into separate directories cannot
    overwrite each other, and the directory name says which session to ask.
    Still gitignored working state, exactly as the flat layout was.
    """
    path = os.path.join(root or CANDIDATES, rid or run_id())
    if create:
        os.makedirs(path, exist_ok=True)
    return path


# -- content addressing ---------------------------------------------------

def _canonical(doc):
    """Reduce a submission to the part the gate's verdict depends on."""
    keyed = {k: v for k, v in doc.items() if k not in UNKEYED_TOP}
    prov = keyed.get("provenance")
    if isinstance(prov, dict):
        keyed["provenance"] = {k: v for k, v in prov.items()
                               if k not in UNKEYED_PROVENANCE}
    return json.dumps(keyed, sort_keys=True, separators=(",", ":"),
                      default=str)


def content_digest(doc):
    """SHA-256 of a candidate's verdict-relevant content, as hex.

    Two documents with the same digest describe the same code, the same
    claimed distance and the same witnesses, and differ at most in who
    packaged it, when, and what they called it.
    """
    return hashlib.sha256(_canonical(doc).encode("utf-8")).hexdigest()


def unique_path(path, doc=None):
    """Return a path next to ``path`` that no other candidate occupies.

    ``path`` itself when it is free, or when ``doc`` is given and the file
    already there holds the same content (re-running a search must not need a
    new filename). Otherwise the name grows a short content digest, which is
    the suffix convention sessions were already applying by hand, and then a
    counter if even that is taken.
    """
    path = os.fspath(path)
    if not os.path.exists(path):
        return path
    if doc is not None and holds_same_candidate(path, doc):
        return path
    stem, ext = os.path.splitext(path)
    tag = content_digest(doc)[:16] if doc is not None else _file_digest(path)[:16]
    nth = f"{stem}-{tag}{ext}"
    if not os.path.exists(nth) or (doc is not None
                                   and holds_same_candidate(nth, doc)):
        return nth
    i = 2
    while os.path.exists(f"{stem}-{tag}-{i}{ext}"):
        i += 1
    return f"{stem}-{tag}-{i}{ext}"


def _file_digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def holds_same_candidate(path, doc):
    """Report whether the file at ``path`` already holds this same candidate.

    False for a missing, unreadable or malformed file, so a caller deciding
    whether it is safe to overwrite errs toward keeping what is there.
    """
    try:
        with open(path, encoding="utf-8") as f:
            return content_digest(json.load(f)) == content_digest(doc)
    except (OSError, ValueError, AttributeError, TypeError):
        return False


# -- what a cached verdict is allowed to outlive --------------------------

def validator_sha256(path=None):
    """SHA-256 of ``verify/validate_candidate.py``, read and never written.

    The same number the gate stamps into every verdict it issues. A cached
    entry whose stamp no longer matches the validator on disk is discarded
    rather than served: the gate changed, so its old answer is an opinion from
    a previous version of the rules.
    """
    return _file_digest(path or VALIDATOR_SOURCE)


def _refutation(verdict):
    """Return the board-independent half of a verdict, the random search.

    ``gates.refute`` is produced by reading the candidate and nothing else, so
    it is the only part of a verdict that survives a board that has moved on.
    Absent when the candidate failed the structural checks, because the gate
    returns before the search in that case and there is nothing to keep.
    """
    if not isinstance(verdict, dict):
        return None
    ref = (verdict.get("gates") or {}).get("refute")
    return ref if isinstance(ref, dict) and "refuted" in ref else None


def _schema_errors(doc):
    """Return schema violations in ``doc``, or None without jsonschema."""
    try:
        import jsonschema
    except ImportError:                          # pragma: no cover
        return None
    schema_path = os.path.join(_ROOT, "schema", "code.schema.json")
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    return list(jsonschema.Draft202012Validator(schema).iter_errors(doc))


class VerdictCache:
    """Reuse of the one gate step that does not depend on the board.

    The first version of this cache keyed on the board as well as the
    candidate, because ``dedup`` and ``novelty`` are claims about ``codes/``
    at a point in time and serving a stale ``board_advancing`` would be
    worse than paying again. That reasoning is right and it is also what
    defeated the cache: on an active board the key went stale faster than
    candidates arrived, and the measured hit count was 7 against 366
    validations (#2314).

    So the layers are separated. ``gates.refute`` reads the candidate and
    nothing else, and on this board costs 8.3 s of the 8.4 s a warm
    validation takes; ``dedup`` and ``novelty`` read the board and cost
    0.11 s once its structural pass is memoized. Only the refutation is
    stored, every call still runs the gate, and the recomputed half is
    always current.

    What it stores is what ``verify/validate_candidate.py`` returned,
    sliced, never anything assembled here. It refuses an entry that does not
    carry the gate's own source stamp, so a hand-written dict cannot be
    planted in it, and it refuses to serve one produced by a validator that
    is no longer the validator on disk.

    Refutation is one-sided, and the entry records it that way. A refutation
    is a witness and keeps: once any attempt has found a lighter logical
    operator, every later read says refuted. "Not refuted" is only the
    absence of one, so the entry also counts the attempts behind it, and
    reusing it is a decision to trust that search rather than re-roll it.
    """

    def __init__(self, root=None):
        self.root = root or os.path.join(CANDIDATES, CACHE_DIRNAME)
        self._validator = None

    # -- the staleness condition -----------------------------------------
    def validator(self):
        """Return the validator source hash, computed once per cache object."""
        if self._validator is None:
            self._validator = validator_sha256()
        return self._validator

    def path_for(self, doc):
        """Where the entry for ``doc`` lives."""
        return os.path.join(self.root, f"{content_digest(doc)}.json")

    # -- read and write ---------------------------------------------------
    def entry(self, doc):
        """Return the stored entry for ``doc``, or None.

        None whenever anything is uncertain: no entry, a torn or unreadable
        one, one from a different validator, or a document that does not
        validate against the schema. The last case is the one that earns the
        key's freedom to ignore who packaged a candidate: the fields it drops
        are read by the gate only for their schema validity, which is
        re-checked here on the document in hand.
        """
        errs = _schema_errors(doc)
        if errs is None or errs:
            return None
        try:
            with open(self.path_for(doc), encoding="utf-8") as f:
                entry = json.load(f)
        except (OSError, ValueError):
            return None
        if entry.get("entry_version") != ENTRY_VERSION:
            return None
        if entry.get("validator_sha256") != self.validator():
            return None
        ref = entry.get("refute")
        return entry if isinstance(ref, dict) and "refuted" in ref else None

    def get(self, doc):
        """Return a reusable ``gates.refute`` block for ``doc``, or None."""
        entry = self.entry(doc)
        return entry["refute"] if entry else None

    def put(self, doc, verdict, *, refuted=True):
        """Store the refutation in ``verdict``; return its path, or None.

        Refused unless the verdict carries the source stamp of the validator
        on disk, which is what makes this a cache of the gate rather than a
        place to put a claim. Also refused for a verdict produced with
        ``refute=False``: that is the half this cache exists for, and a later
        reader would mistake the placeholder block for a real search.

        A stored refutation is never downgraded. ``attempts`` counts the
        searches behind a "not refuted", so a reader can tell one 8-second
        run from twenty.
        """
        if not refuted:
            return None
        ref = _refutation(verdict)
        if ref is None:
            return None
        stamp = (verdict.get("validator") or {}).get("source_sha256")
        if stamp != self.validator():
            return None
        prior = self.entry(doc)
        attempts = (prior or {}).get("attempts", 0) + 1
        if prior and prior["refute"].get("refuted") and not ref.get("refuted"):
            ref = prior["refute"]            # a witness found once stays found
        entry = {
            "entry_version": ENTRY_VERSION,
            "content_digest": content_digest(doc),
            "validator_sha256": self.validator(),
            "attempts": attempts,
            "run_id": run_id(),
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "refute": ref,
        }
        return _write_atomic(self.path_for(doc), entry)


def _write_atomic(path, obj):
    """Write JSON so a concurrent reader sees the old file or the new one.

    Sessions read this directory while other sessions write it, and a reader
    that catches a half-written entry would either crash or, worse, parse a
    truncated verdict.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.{time.monotonic_ns()}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
    try:
        os.replace(tmp, path)
    except OSError:                              # pragma: no cover
        os.unlink(tmp)
        raise
    return path


def _gate():
    """Import the trusted gate, read-only, the way a session would."""
    vdir = os.path.join(_ROOT, "verify")
    if vdir not in sys.path:
        sys.path.insert(0, vdir)
    import validate_candidate
    return validate_candidate.validate_candidate


def _with_refutation(verdict, ref):
    """Return ``verdict`` with its refutation replaced by ``ref``.

    The composition is subtractive by construction. ``verdict`` is the gate's
    own answer for the board as it is right now, computed with the search
    skipped, so its ``passed`` already carries every structural and dedup
    condition; ANDing "not refuted" on top can only clear it. There is no
    path here that turns a refusal into a pass.
    """
    out = dict(verdict)
    gates = dict(out.get("gates") or {})
    if "refute" not in gates:
        return out                           # structural failure: nothing to splice
    gates["refute"] = ref
    out["gates"] = gates
    if ref.get("refuted"):
        label = f"refuted (over-claimed distance): {ref.get('detail')}"
        if label not in (out.get("labels") or []):
            out["labels"] = [label] + list(out.get("labels") or [])
        out["passed"] = False
    else:
        out["passed"] = bool(out.get("passed"))
    return out


def validate_cached(doc, *, cache=None, validator=None, seed=None, refute=True):
    """Run the gate on ``doc``, reusing an existing refutation when one applies.

    Returns ``(verdict, reused)``. The gate runs either way: ``reused`` is
    True when the random distance search was served from the cache and the
    rest of the verdict was recomputed against the board as it is now, so
    ``dedup`` and ``novelty`` are never stale and ``board_advancing`` is
    never older than this call.

    ``validator`` exists so a test can drive this without paying for a real
    confirmation; leaving it unset calls ``verify/validate_candidate.py``.
    """
    cache = VerdictCache() if cache is None else cache
    gate = validator or _gate()
    ref = cache.get(doc) if refute else None
    if ref is not None:
        return _with_refutation(gate(doc, seed=seed, refute=False), ref), True
    verdict = gate(doc, seed=seed, refute=refute)
    try:
        cache.put(doc, verdict, refuted=refute)
    except OSError as e:                         # pragma: no cover
        if e.errno not in (errno.EACCES, errno.EROFS, errno.ENOSPC):
            raise
    return verdict, False


if __name__ == "__main__":
    _cache = VerdictCache()
    print(f"run_id       {run_id()}")
    print(f"staging      {staging_dir(create=False)}")
    print(f"verdicts     {_cache.root}")
    print(f"validator    {_cache.validator()[:16]}")
