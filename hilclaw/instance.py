"""The instance record of one run, ``runs/<run_id>/instance.json`` (ADR-0018, ADR-0020, ADR-0022, ADR-0023).

``ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md`` fixes the
file as a whole (decision 2), the member ``hw_profile`` in which a run states
the hw_profile it was started with (decisions 3 and 5) and how a call of a HW
tool reads it (decision 4).
``ARCHITECTURE/decisions/ADR-0020-od8-instance-record-tolerance.md`` adds the
member ``tolerance``, in which a run states the ``rtol`` and the ``atol`` of
its correctness check in the vocabulary of the first case (decisions 2 to 4),
and says where the tolerance of a run is read from (decision 5).
``ARCHITECTURE/decisions/ADR-0022-od8-instance-record-source-commit.md`` adds
the member ``source_commit``, in which a run states the commit of the source
repository it was started with (decision 3), says that a valid file may lack
it and that a present one must be valid (decision 5), and says where the
source commit a run states is read from (decision 7).
``ARCHITECTURE/decisions/ADR-0023-od8-instance-record-n-max.md`` adds the
member ``n_max``, in which a run states the upper bound of repeats of one
timing measurement (decisions 2 and 3), says that a valid file may lack it,
that a present one must be valid and that no value stands in for an absent
one (decision 4), and says where the bound a run states is read from
(decision 5). This module is those rules: :func:`parse` and :func:`validate`
are pure functions of the bytes of a content and of a parsed document, and
:func:`read`, :func:`hw_profile_of`, :func:`tolerance_of`,
:func:`source_commit_of` and :func:`n_max_of` read the file of a run.
:func:`hw_profile_of` has the call form of the parameter ``hw_profile_of`` of
:func:`hilclaw.hw_tool.tool_function`; nothing here binds it,
:func:`tolerance_of`, :func:`source_commit_of` or :func:`n_max_of` to a tool.

Conventions of this module, which the four records do not fix:

- A content is exactly ``bytes`` (:class:`TypeError` otherwise: the encoding is
  part of validity). Values are as :func:`json.loads` returns them, an integer
  exactly an ``int``: ``true`` and ``1.0`` are none.
- Every other broken rule of a content or of a document raises
  :class:`InvalidInstanceError` naming the place, and another version raises
  :class:`UnsupportedVersionError` of this module.
- The rules for the whole text come first, whatever the version, then
  ``schema_version``, then ``hw_profile``, then ``tolerance`` when the document
  holds it, then ``source_commit`` when the document holds it, then ``n_max``
  when the document holds it: the order in which the records defined them. A
  content this interpreter cannot read (an integer too long for it anywhere
  in the text, nesting too deep) raises :class:`InvalidInstanceError` too,
  though it is a limit of this reader and not damage; the limits stay as the
  interpreter has them. A number beyond the float range in a member not
  defined here is read as an infinity and is no error, as
  :mod:`hilclaw.run_state` has it; in ``tolerance`` and as ``n_max`` it makes
  the content invalid (ADR-0020 decision 4, ADR-0023 decision 3).
- ``schema_version`` is an integer of ADR-0001, from 0 to
  :data:`hilclaw.keys.MAX_INTEGER`: a value outside that range is no integer of
  the records and makes the content invalid, it is not another version. ``-0``
  is read as the integer 0, as :mod:`hilclaw.run_state` reads it, and is then
  the unsupported version 0.
- Inside ``hw_profile`` the order is: an object, no member besides ``key`` and
  ``record``, both present, ``key`` a ``str``, ``record`` an object, the record
  valid, ``key`` the derived name. The first rule found broken is reported. An
  empty ``key`` and one of another form are reported as not the derived name.
- Inside ``tolerance`` the order is: an object, no member besides ``rtol`` and
  ``atol``, both present, ``rtol`` a valid value, ``atol`` a valid value. A
  value is exactly an ``int`` or a ``float`` (``true`` is none) whose ``float``
  is finite and not negative, so an ``int`` that no ``float`` holds is invalid.
  The first rule found broken is reported. The rule for a value is written
  here and agrees with ``check_tolerance`` of the verification harness, which
  this module does not import.
- The tolerance is handed out as a :class:`Tolerance` of two ``float``, also
  for an integer literal, and a zero as ``0.0`` whatever its sign in the file.
  A content without the member has ``None`` in that place: it states no
  tolerance, and that is no error of the content.
- ``source_commit`` is exactly a ``str`` of 40 or of 64 characters, each one
  of the sixteen ASCII characters ``0``-``9`` and ``a``-``f``; the characters
  themselves are compared, so a digit of another script is none. The one rule
  is reported as a whole, and a ``str`` that breaks it is shown as every
  ``str`` is, a long one shortened. Either length is a value: the module does
  not know or check which of the two the source repository uses. The source
  commit is handed out as the ``str`` of the file, unchanged. A content
  without the member has ``None`` in that place: it states no source commit,
  and that is no error of the content.
- ``n_max`` is exactly an ``int`` from 5 to :data:`hilclaw.keys.MAX_INTEGER`,
  both included: ``true``, ``10.0`` and ``1e1`` are none, and ``-0`` is read
  as the integer 0, which is below 5. The one rule is reported as a whole,
  and an ``int`` that breaks it is not shown, as for ``schema_version``. The
  bound is handed out as the ``int`` of the file, unchanged. A content
  without the member has ``None`` in that place: it states no bound, and that
  is no error of the content.
- The file is read as :mod:`hilclaw.run_journal` reads ``STATE.json``:
  ``run_id`` is checked first, then ``data_root``, which is used as given and
  must be an existing directory (:class:`FileNotFoundError` or
  :class:`NotADirectoryError` otherwise). A missing file (no file, no run
  directory, a file in the place of a directory above it) raises
  :class:`MissingInstanceError`. A path that is not a regular file (a symbolic
  link is not followed) raises :class:`InvalidInstanceError`. An error about
  the content names the file by its path relative to the data root, in front
  of the message of the parser. A file that disappears between the check and
  the read is an :class:`OSError`, as every other failure of the file system.

It writes, creates and removes no file and composes no content. It defines no
member besides the five (``schema_version``, ``hw_profile``, ``tolerance``,
``source_commit`` and ``n_max``) and interprets no other: a file it accepts is not
thereby a complete instance record, and not enough to start a run (ADR-0018
decisions 1 and 2). Of the tolerance it gives what the file states and nothing
else: it holds no default and substitutes no value (ADR-0020 decision 3), does
not check that a run is of the first case, and gives the member no meaning for
a run of another case (#5 B-7). A file it accepts need not state a tolerance,
and where it is checked that an instance states one is open (OD-8
sub-question 19). Which tool or component reads the member, at which moment
of a call, and what a call answers when no tolerance is stated is not said
here; "not stated" is no error of the content, and this module gives it no
tool-failure kind.
Of the source commit it gives what the file states for the start of the
instance and nothing else (ADR-0022 decisions 5 and 7): it obtains no commit
and runs no ``git``, and it substitutes no value for a member that is absent,
so no constant, default or fallback of this module is a commit. It checks the
form of the member only: not that a stated commit exists anywhere, and not
that the statement is true (ADR-0022 decisions 4 and 8). It does not identify
or locate the source repository, compares the member with nothing, and says
nothing about the source of a later result of the run (OD-11) or about a
source that is not exactly a commit. A file it accepts need not state a
source commit, and where it is checked that an instance states one is open
(OD-8 sub-question 20). Which tool or component reads the member, at which
moment, and what a call answers when no source commit is stated is not said
here; "not stated" is no error of the content here either, and this module
gives it no tool-failure kind.
Of the bound of repeats it gives what the file states and nothing else
(ADR-0023 decisions 4 and 5): it holds no default and substitutes no value
for a member that is absent, not 10 and not a constant of the harness, which
it does not import. The lower bound is the number 5 of ADR-0023 decision 3,
written here, and not the constant of the measurement policy. It checks the
form of the member only: not that a measurement was or can be taken under a
stated bound. The member bounds the samples of one measurement (ADR-0023
decision 2): this module makes it no bound of measurements, attempts,
candidates or rounds and no budget member. A file it accepts need not state
a bound; whether a measurement of a run that states none may be taken, and
where it is checked that an instance states its bound, is open (OD-8
sub-question 21). Which tool or component reads the member, at which moment,
and what a call answers when no bound is stated is not said here; "not
stated" is no error of the content here either, this module gives it no
tool-failure kind, and :func:`n_max_of` is bound to no tool and to no timing
run.
It reads no other file, so the stored record of the key below ``db/`` is not
read or compared (ADR-0018 decision 4) and no reader here needs it to exist; how
the two records relate is open (OD-8 sub-question 18). None of its errors is a
:class:`hilclaw.tools.ToolFailure`: the kind a call of a tool answers for them
is given by the tool function that calls :func:`hw_profile_of`
(:mod:`hilclaw.hw_tool`, ADR-0019), not here. It reads no other version
(OD-11) and says nothing of what writes the file, of when, or of a run
directory without it (OD-8 sub-questions 10 and 17). Nothing is kept between
calls, so a file changed between two calls is read as changed (ADR-0018
decision 6).
"""

import codecs
import json
import math
import os
import reprlib
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import keys, layout

SCHEMA_VERSION = 1

_MAX = keys.MAX_INTEGER
_DEFINED = ("schema_version", "hw_profile", "tolerance", "source_commit", "n_max")
_SECTION = ("key", "record")
_TOLERANCE = ("rtol", "atol")
_COMMIT_LENGTHS = (40, 64)
_COMMIT_CHARACTERS = frozenset("0123456789abcdef")


class InvalidInstanceError(ValueError):
    """A content, a document or a path breaks a rule; the message names it.

    The rules are those of ADR-0018, ADR-0020, ADR-0022 and ADR-0023 and the
    conventions of this module.
    """


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted."""


class MissingInstanceError(Exception):
    """No instance record was written for the ``run_id``; the message names the path."""


class Tolerance(NamedTuple):
    """The tolerance a content states (ADR-0020 decision 2): ``rtol`` and ``atol``.

    As :func:`parse` returns it, both are ``float``, finite and not negative.
    They are what the content states, in the vocabulary of the first case; no
    value here is a default.
    """

    rtol: float
    atol: float


class Instance(NamedTuple):
    """Result of :func:`parse`: what a content states and the members not defined.

    ``tolerance`` is a :class:`Tolerance`, or ``None`` for a content without
    the member ``tolerance``. ``source_commit`` is the ``str`` of the member
    ``source_commit``, or ``None`` for a content without that member.
    ``n_max`` is the ``int`` of the member ``n_max``, or ``None`` for a content
    without that member. No field has a default. ``others`` is the last field.
    """

    hw_profile_key: str
    hw_profile: dict
    tolerance: Tolerance | None
    source_commit: str | None
    n_max: int | None
    others: dict


def parse(content):
    """Return the :class:`Instance` of ``content``, the bytes of an ``instance.json``.

    ``hw_profile_key`` is ``hw_profile.key`` and ``hw_profile`` is
    ``hw_profile.record``, the ``dict`` parsed from this content;
    ``tolerance`` is the :class:`Tolerance` of the member ``tolerance``, each
    value the ``float`` of its literal (``2`` gives ``2.0``; ``-0``, ``-0.0``,
    ``-1e-999`` and ``1e-999`` give ``0.0``), or ``None`` when the content has
    no such member, and no value is substituted then; ``source_commit`` is
    the string of the member ``source_commit`` as the content states it
    (ADR-0022 decision 3), not normalised, shortened or resolved, or ``None``
    when the content has no such member, and no value is substituted then
    either; ``n_max`` is the ``int`` of the member ``n_max`` as the content
    states it (ADR-0023 decision 3), not clamped, rounded or replaced, or
    ``None`` when the content has no such member, and no value is substituted
    then either; ``others`` holds every top-level member that is none of
    ``schema_version``, ``hw_profile``, ``tolerance``, ``source_commit`` and
    ``n_max``, as parsed and not interpreted, whatever its name and value
    (``tolerence``, a top-level ``rtol``, ``source-commit`` or ``nmax`` among
    them). Any order of members and any white space of JSON are accepted.

    Raises :class:`InvalidInstanceError` when ``content`` is not UTF-8 without
    a byte order mark, is not exactly one JSON text (the tokens ``NaN``,
    ``Infinity`` and ``-Infinity`` are no JSON; an empty content is none),
    holds a member name twice in any object or is a document :func:`validate`
    refuses, and :class:`UnsupportedVersionError` as that function does.
    Nothing is returned then, and nothing is repaired.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidInstanceError("content: starts with a byte order mark")
    try:
        text = content.decode("utf-8")
        document = json.loads(text, object_pairs_hook=_object, parse_constant=_nan)
    except RecursionError:
        raise InvalidInstanceError("content: is nested too deeply to parse") from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidInstanceError(reason) from None
    return _checked(document)


def validate(document):
    """Check ``document``, a parsed ``instance.json``, against the four records.

    ``document`` must be a ``dict`` with ``schema_version`` (an ``int`` from 0
    to :data:`hilclaw.keys.MAX_INTEGER`) and, at version 1, ``hw_profile``: a
    ``dict`` with exactly ``key`` and ``record``, the record a ``dict`` that
    :func:`hilclaw.keys.hw_profile_key` accepts and the key the name derived
    from it (ADR-0018 decisions 2 and 3). It may hold ``tolerance``, which is
    then a ``dict`` with exactly ``rtol`` and ``atol``, each exactly an ``int``
    or a ``float`` whose ``float`` is finite and not negative (ADR-0020
    decisions 2 to 4): for a value built in memory, an infinity, a NaN and an
    ``int`` that no ``float`` holds are invalid, and a ``bool`` is no number.
    It may hold ``source_commit``, which is then exactly a ``str`` of 40 or of
    64 characters, each one of ``0``-``9`` and ``a``-``f`` (ADR-0022 decisions
    3 and 5): for a value built in memory, a subclass of ``str`` and a
    ``bytes`` are none. Only that form is checked, not that such a commit
    exists. It may hold ``n_max``, which is then exactly an ``int`` from 5 to
    :data:`hilclaw.keys.MAX_INTEGER`, both included (ADR-0023 decisions 3 and
    4): for a value built in memory, a ``bool``, a ``float`` such as ``10.0``
    and a subclass of ``int`` are none. Only that form is checked, not that a
    measurement was or can be taken under the bound. Its other members are
    not looked at. The rules for the text (the encoding, a member name twice)
    cannot be checked on a parsed value. The four records are ADR-0018,
    ADR-0020, ADR-0022 and ADR-0023.

    Raises :class:`InvalidInstanceError` for the first rule found broken,
    naming the place (for example ``hw_profile.record.accelerator``,
    ``tolerance.rtol``, ``source_commit`` or ``n_max``). The version comes
    first: an integer other than :data:`SCHEMA_VERSION` raises
    :class:`UnsupportedVersionError` before any other member is looked at.
    """
    _checked(document)


def read(data_root, run_id):
    """Return the :class:`Instance` of the run ``run_id``, read from its ``instance.json``.

    The bytes of ``runs/<run_id>/instance.json`` below ``data_root`` are given
    to :func:`parse`; no other file is read and nothing is written. The whole
    file is read at each call and nothing is kept, so each call returns new
    objects.

    Raises :class:`hilclaw.layout.InvalidPathValueError` for a ``run_id`` that
    is none, before the file system is touched; :class:`FileNotFoundError` or
    :class:`NotADirectoryError` when ``data_root`` is no existing directory;
    then one error for each situation of ADR-0018 decision 4:
    :class:`MissingInstanceError` when there is no file, an :class:`OSError`
    of the file system, unchanged, when it cannot be read,
    :class:`InvalidInstanceError` for an invalid content, an empty file
    included, and :class:`UnsupportedVersionError` for another version. A path
    that is not a regular file is none of the four: by the convention of this
    module it raises :class:`InvalidInstanceError`.
    """
    path = layout.run_file(data_root, run_id, "instance.json")
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    file = path.relative_to(root).as_posix()
    try:
        status = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        reason = f"{file}: is missing: no instance record was written for this run_id"
        raise MissingInstanceError(reason) from None
    if not stat.S_ISREG(status.st_mode):
        raise InvalidInstanceError(f"{file}: is not a regular file")
    try:
        return parse(path.read_bytes())
    except (InvalidInstanceError, UnsupportedVersionError) as error:
        raise type(error)(f"{file}: {error}") from None


def hw_profile_of(data_root, run_id):
    """Return the hw_profile record the run ``run_id`` states (ADR-0018 decision 4).

    It is the ``hw_profile`` of what :func:`read` returns: the
    ``hw_profile.record`` of ``runs/<run_id>/instance.json``, a ``dict`` valid
    by ADR-0001 and new at each call, which the caller may hand to
    :func:`hilclaw.backends.select`. Raises what :func:`read` raises, so
    :class:`InvalidInstanceError` also for a file whose ``tolerance``,
    ``source_commit`` or ``n_max`` is invalid: no member of an invalid file is
    used (ADR-0020 decision 3, ADR-0022 decision 5, ADR-0023 decision 4).
    """
    return read(data_root, run_id).hw_profile


def tolerance_of(data_root, run_id):
    """Return the tolerance the run ``run_id`` states, or ``None`` when it states none.

    It is the ``tolerance`` of what :func:`read` returns (ADR-0020 decision
    5): a :class:`Tolerance` with the ``rtol`` and the ``atol`` of the member
    ``tolerance`` of ``runs/<run_id>/instance.json``, new at each call, or
    ``None`` for a valid file without that member. ``None`` says that no
    tolerance is stated; no value stands in for it, here or in a default of
    this module. Raises what :func:`read` raises, so no tolerance is returned
    for a missing, unreadable or invalid file or one of another version.
    """
    return read(data_root, run_id).tolerance


def source_commit_of(data_root, run_id):
    """Return the source commit the run ``run_id`` states, or ``None`` when it states none.

    It is the ``source_commit`` of what :func:`read` returns (ADR-0022
    decision 7): the string of the member ``source_commit`` of
    ``runs/<run_id>/instance.json``, 40 or 64 characters of ``0``-``9`` and
    ``a``-``f``, as the file states it at this call, or ``None`` for a valid
    file without that member. ``None`` says that no source commit is stated;
    no value stands in for it (ADR-0022 decision 5): not the commit of the
    source this function runs from, which it does not look for. The string is
    what the file states for the start of the instance; that the commit
    exists or that the statement is true is not checked. Raises what
    :func:`read` raises, so no source commit is returned for a missing,
    unreadable or invalid file or one of another version.
    """
    return read(data_root, run_id).source_commit


def n_max_of(data_root, run_id):
    """Return the bound of repeats the run ``run_id`` states, or ``None`` when it states none.

    It is the ``n_max`` of what :func:`read` returns (ADR-0023 decision 5):
    the ``int`` of the member ``n_max`` of ``runs/<run_id>/instance.json``,
    from 5 to :data:`hilclaw.keys.MAX_INTEGER`, as the file states it at this
    call, or ``None`` for a valid file without that member. The member
    states the largest number of samples one timing measurement may hold
    (ADR-0023 decision 2). ``None`` says that no bound is stated; no value
    stands in for it (ADR-0023 decision 4): not 10, not a constant of the
    harness and not the bound of another run. That a measurement was or can
    be taken under the bound is not checked, and nothing here hands the
    bound to a measurement. Raises what :func:`read` raises, so no bound is
    returned for a missing, unreadable or invalid file or one of another
    version.
    """
    return read(data_root, run_id).n_max


def _fail(place, rule, value):
    got = type(value).__name__
    if type(value) is str:
        got = f"{got} {reprlib.repr(value)}"
    raise InvalidInstanceError(f"{place}: must be {rule}, got {got}")


def _checked(document):
    if type(document) is not dict:
        _fail("document", "an object", document)
    if "schema_version" not in document:
        raise InvalidInstanceError("document: lacks the member schema_version")
    version = document["schema_version"]
    if type(version) is not int or not 0 <= version <= _MAX:
        _fail("schema_version", f"an int from 0 to {_MAX}", version)
    if version != SCHEMA_VERSION:
        raise UnsupportedVersionError(f"schema_version: {version} is not supported")
    if "hw_profile" not in document:
        raise InvalidInstanceError("document: lacks the member hw_profile")
    key, record = _hw_profile(document["hw_profile"])
    tolerance = _tolerance(document["tolerance"]) if "tolerance" in document else None
    commit = None
    if "source_commit" in document:
        commit = _source_commit(document["source_commit"])
    n_max = _n_max(document["n_max"]) if "n_max" in document else None
    others = {name: value for name, value in document.items() if name not in _DEFINED}
    return Instance(key, record, tolerance, commit, n_max, others)


def _hw_profile(section):
    if type(section) is not dict:
        _fail("hw_profile", "an object", section)
    for name in section:
        if name not in _SECTION:
            _fail("hw_profile", "an object without the member", name)
    for name in _SECTION:
        if name not in section:
            raise InvalidInstanceError(f"hw_profile: lacks the member {name}")
    key, record = section["key"], section["record"]
    if type(key) is not str:
        _fail("hw_profile.key", "a str", key)
    if type(record) is not dict:
        _fail("hw_profile.record", "an object", record)
    try:
        name = keys.hw_profile_key(record).name
    except keys.InvalidRecordError as error:
        raise InvalidInstanceError(f"hw_profile.record.{error}") from None
    if key != name:
        _fail("hw_profile.key", f"{name}, the name derived from hw_profile.record", key)
    return key, record


def _tolerance(section):
    if type(section) is not dict:
        _fail("tolerance", "an object", section)
    for name in section:
        if name not in _TOLERANCE:
            _fail("tolerance", "an object without the member", name)
    for name in _TOLERANCE:
        if name not in section:
            raise InvalidInstanceError(f"tolerance: lacks the member {name}")
    return Tolerance(*(_number(name, section[name]) for name in _TOLERANCE))


def _number(name, value):
    try:
        number = float(value) if type(value) in (int, float) else math.nan
    except OverflowError:
        number = math.inf
    if not 0 <= number < math.inf:
        _fail(f"tolerance.{name}", "a finite number that is not negative", value)
    return abs(number)


def _source_commit(value):
    if (
        type(value) is not str
        or len(value) not in _COMMIT_LENGTHS
        or not _COMMIT_CHARACTERS.issuperset(value)
    ):
        rule = "a str of 40 or of 64 characters, each one of 0-9 and a-f"
        _fail("source_commit", rule, value)
    return value


def _n_max(value):
    if type(value) is not int or not 5 <= value <= _MAX:
        _fail("n_max", f"an int from 5 to {_MAX}", value)
    return value


def _object(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def _nan(name):
    raise ValueError(f"{name} is not a JSON value")
