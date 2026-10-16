"""The exact-match lookup of the stored cases of a run's key directory (ADR-0073 decisions 1 and 3).

``ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md``
decision 1 fixes what the selection role of a round reads of the stored
hypothesis-outcome cases: the key of the run's instance, a hit of the
exact-match lookup of ADR-0001 decision 4 (:func:`hilclaw.key_records.lookup`)
and, on a hit only, every valid case directly in that key directory except
those of the reader's own run, each the parsed document whole, given in
ascending byte order of the file names. A file counts when its name begins
``case-`` and ends ``.json``; it is read by ADR-0072 decision 2
(:func:`hilclaw.cases_file.parse` and :func:`hilclaw.cases_file.final_name`).
:func:`find` is that lookup for given records, :func:`lookup` reads them from
the run's ``instance.json`` (:func:`hilclaw.instance.read`), and
:func:`cases_read` gives the value of ``cases_read`` (decision 3) that a
selection given the result records.

The result depends only on the two records, the two key record files, the
counted entries of the key directory and the reader's ``run_id``, not on the
order in which the file system lists entries (NFR-2). The order of the cases
is fixed for that reason only and claims no meaning: not recency, not rank.

``data_root`` is always given by the caller and must be an existing directory
(:class:`FileNotFoundError` or :class:`NotADirectoryError` otherwise). Errors
of :mod:`hilclaw.keys`, :mod:`hilclaw.layout` and :mod:`hilclaw.instance` for
the caller's arguments pass through unchanged, and so does an
:class:`OSError` of listing the key directory.

Conventions of this module, which ADR-0073 does not fix:

- The result is a :class:`Found` of the key, the cases and the
  :class:`Report` values. A file ADR-0073 says is reported is **returned** as
  a report, not raised, so that one never hides the others.
- A report has one of four kinds: ``"key_record"`` for a stored key record
  file that collides (ADR-0001 decision 3) or is not valid; ``"invalid"`` for
  a case file not valid by ADR-0072 decision 2, its name not formed from its
  ``run_id`` and ``round`` included, and for an entry of the counted name form
  that is not a regular file; ``"set_apart"`` for a case or a copy of another
  integer ``schema_version`` (OD-11); ``"unreadable"`` for an
  :class:`OSError` of taking the kind of one entry or of reading its bytes,
  after which the rest are still read.
- An entry's kind is taken by :func:`os.lstat`: a symbolic link is not
  followed and is reported as ``"invalid"``, as is a directory.
- The reports are in ascending byte order of their ``path``.
- **How a report is carried to the selection, and whether a selection may go
  on after one, is not decided** (ADR-0073 Boundaries; OD-18, OD-23).
- A run that states no op_signature has no key: nothing is substituted, no
  file is read and its hw_profile record is not validated.

What this module does not do: it is no tool, no hook and no command, and it
does not decide which agent performs the lookup or how a selection is made to
take its output and record ``cases_read`` (OD-18, OD-23). It has no selection
rule for many cases (OD-30), no similar-key lookup (OD-4) and no ranking
(OD-7). It does not check the rules between files of ADR-0073 decisions 2 and
3 (that the ``case`` entries and ``cases_read`` of a ``hypotheses.json`` name
cases of the key directory), resolves no *ref* inside a case, compares no
copy with ``runs/`` and reads no other version (OD-11). Besides the run's
``instance.json`` read by :func:`lookup` and the two key record files, it
reads nothing outside the key directory, nothing below ``runs/`` of another
run, and no subdirectory; it writes, creates, removes and repairs nothing,
takes no lock and makes no commit.
"""

import os
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import cases_file, instance, key_records, keys, layout


class Report(NamedTuple):
    """A file the lookup reports (module docstring).

    ``path`` is the POSIX path of the file relative to ``data_root``, ``kind``
    one of ``"key_record"``, ``"invalid"``, ``"set_apart"`` and
    ``"unreadable"``, and ``reason`` the message of the error.
    """

    path: str
    kind: str
    reason: str


class Found(NamedTuple):
    """Result of :func:`find` and :func:`lookup`.

    ``key`` is the pair of :class:`hilclaw.keys.Key` values (hw_profile,
    op_signature) on a hit and ``None`` otherwise. ``cases`` is a tuple of the
    case documents, each the ``dict`` :func:`hilclaw.cases_file.parse`
    returned, whole and unaltered, in ascending byte order of their file
    names; the order claims no meaning. ``reports`` is a tuple of
    :class:`Report` in ascending byte order of ``path``.
    """

    key: tuple | None
    cases: tuple
    reports: tuple


def find(data_root, hw_profile, op_signature, run_id):
    """Return the :class:`Found` of the key (``hw_profile``, ``op_signature``) for the reader ``run_id``.

    ``hw_profile`` and ``op_signature`` are the records an ``instance.json``
    states; ``op_signature`` is ``None`` for a run that states none, which
    gives ``Found(None, (), ())`` and reads no file. Otherwise a miss of
    :func:`hilclaw.key_records.lookup` gives the same and nothing below the
    key is read or listed; a stored key record file that collides or is not
    valid gives no case and one ``"key_record"`` report. On a hit the key
    directory is listed once; each entry directly in it whose name begins
    ``case-`` and ends ``.json`` is read, every other entry is neither opened
    nor looked into. Every valid case whose ``run_id`` is not ``run_id`` is
    returned; one whose ``run_id`` is ``run_id`` is left out without a report.

    Raises :class:`hilclaw.layout.InvalidPathValueError` for a ``run_id`` that
    is none and :class:`FileNotFoundError` or :class:`NotADirectoryError` for a
    ``data_root`` that is no existing directory, before any file is read; what
    :mod:`hilclaw.keys` raises for an invalid record; and the
    :class:`OSError` of listing the key directory.
    """
    layout.check_run_id(run_id)
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    if op_signature is None:
        return Found(None, (), ())
    try:
        key = key_records.lookup(root, hw_profile, op_signature)
    except (key_records.KeyCollisionError, key_records.CorruptKeyRecordError) as error:
        return Found(None, (), (_key_report(root, hw_profile, op_signature, error),))
    if key is None:
        return Found(None, (), ())
    hw, op = key
    key_dir = layout.op_signature_dir(root, hw.name, op.name)
    names = [
        name
        for name in os.listdir(key_dir)
        if name.startswith("case-") and name.endswith(".json")
    ]
    found = []
    reports = []
    for name in sorted(names, key=_bytes):
        path = key_dir / name
        where = path.relative_to(root).as_posix()
        try:
            document = _case(root, hw.name, op.name, path)
        except _Reported as report:
            reports.append(Report(where, *report.args))
            continue
        if document["run_id"] != run_id:
            found.append(document)
    reports.sort(key=lambda report: _bytes(report.path))
    return Found(key, tuple(found), tuple(reports))


def lookup(data_root, run_id):
    """Return the :class:`Found` of the run ``run_id``: :func:`find` for the records its ``instance.json`` states.

    The instance record is read once by :func:`hilclaw.instance.read`, whose
    errors pass through unchanged (:class:`hilclaw.instance.MissingInstanceError`,
    :class:`hilclaw.instance.InvalidInstanceError`,
    :class:`hilclaw.instance.UnsupportedVersionError`, an :class:`OSError`,
    :class:`hilclaw.layout.InvalidPathValueError`); no other file of the run
    is read. Then raises what :func:`find` raises.
    """
    stated = instance.read(data_root, run_id)
    op_signature = stated.op_signature.record if stated.op_signature else None
    return find(data_root, stated.hw_profile, op_signature, run_id)


def cases_read(found):
    """Return the ``cases_read`` value of ``found`` (ADR-0073 decision 3).

    The result is a new ``list`` of ``{"run_id": ..., "round": ...}``, one
    per case of ``found.cases`` and in that order; it is empty when
    ``found.cases`` is. Raises :class:`TypeError` when ``found`` is not a
    :class:`Found`.
    """
    if not isinstance(found, Found):
        raise TypeError(f"found must be a Found, got {type(found).__name__}")
    return [{"run_id": case["run_id"], "round": case["round"]} for case in found.cases]


class _Reported(Exception):
    pass


def _bytes(text):
    return text.encode("utf-8", "surrogatepass")


def _key_report(root, hw_profile, op_signature, error):
    hw = keys.hw_profile_key(hw_profile)
    record = layout.hw_profile_record(root, hw.name)
    if not str(error).startswith(f"{record.relative_to(root).as_posix()}:"):
        op = keys.op_signature_key(op_signature)
        record = layout.op_signature_file(root, hw.name, op.name, "op_signature.json")
    return Report(record.relative_to(root).as_posix(), "key_record", str(error))


def _case(root, hw_name, op_name, path):
    try:
        mode = os.lstat(path).st_mode
    except OSError as error:
        raise _Reported("unreadable", str(error)) from None
    if not stat.S_ISREG(mode):
        raise _Reported("invalid", "is not a regular file")
    try:
        content = path.read_bytes()
    except OSError as error:
        raise _Reported("unreadable", str(error)) from None
    try:
        document = cases_file.parse(content)
    except cases_file.UnsupportedVersionError as error:
        raise _Reported("set_apart", str(error)) from None
    except cases_file.InvalidCaseFileError as error:
        raise _Reported("invalid", str(error)) from None
    try:
        name = cases_file.final_name(root, hw_name, op_name, document)
    except layout.InvalidPathValueError as error:
        raise _Reported("invalid", str(error)) from None
    if name.as_posix() != path.as_posix():
        expected = name.relative_to(root).as_posix()
        reason = f"the name is not formed from its run_id and round ({expected})"
        raise _Reported("invalid", reason)
    return document
