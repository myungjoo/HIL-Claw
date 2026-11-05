"""The build record of an attempt, ``.../measure/.../build.json`` (ADR-0004, ADR-0198).

``ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`` gives the file
its place below the measurement role of an attempt.
``ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md``
gives it the owner's form of HQ-0089 ②, for an attempt of the candidate kind
``compile_settings`` only (decision 5): an object with exactly
``schema_version`` (the integer 1), ``outcome`` (``"built"`` or
``"broken"``), ``condition`` exactly when the outcome is ``"broken"``
(``"build_time_limit"`` or ``"build_exit_status"``, the answers of a failed
build of :mod:`hilclaw.check_build`), and ``flags`` and ``trailing_flags``,
the exact arguments of the build, each an array of strings.

:func:`parse` and :func:`validate` are pure functions of the bytes of a
content and of a parsed document; :func:`read` reads the file of an attempt.
No tool reads the file (ADR-0198 decision 8).

The writer is the evaluation tool that carries out the attempt's first build
(decision 5; ``correctness.check``, ``sim.run`` and ``board.run``), through
three parts of this module:

* :func:`evaluated` says, for an attempt of a ``compile_settings`` run, which
  ``output/`` the tool hands its operation and, for a candidate whose spec is
  of version 3, the :class:`CandidateBuild` of the call (decisions 2 and 6),
  or raises :class:`KernelRefused` with an existing backend kind of
  :mod:`hilclaw.check_failure`: ``no_kernel_source`` for a spec that is
  missing or of a version other than 2 and 3, a named attempt whose spec is
  missing or of version 3, and a named attempt with no compiled set;
  ``kernel_source_unreadable`` for a spec that cannot be read, is invalid or
  whose ``id`` formats to another path, and for a failure of the reader of
  ADR-0055.
* :func:`building` makes a :class:`CandidateBuild` the one :func:`current`
  returns while the tool's operation runs. An operation that builds
  (:mod:`hilclaw.standin_check`, :mod:`hilclaw.standin_run`) adds its flags
  after the target's and tells it, by :meth:`CandidateBuild.ended`, what its
  kernel build gave and the exact argument arrays it handed the compiler; an
  operation that builds nothing (the mock) does neither. This keeps the five
  arguments of an operation (:mod:`hilclaw.backends`).
* :meth:`CandidateBuild.write`, called by the tool after the operation came
  back and before its end line, gives the file the name only if it is free
  (:func:`hilclaw.once_write.write_once`), so the first build of an attempt
  writes it and a later one writes nothing.

Conventions of this module, which the record does not fix: a content is
exactly ``bytes``, UTF-8 without a byte order mark, one JSON text with no
member name twice in any object; values are as :func:`json.loads` returns
them, an integer exactly an ``int``; an argument is a ``str`` of at least one
character without the character U+0000, which no argument of a process can
hold. The version comes first, then the members in the order above; the
first rule found broken is reported, naming its place. A
:class:`CandidateBuild` is of one call and kept in a
:class:`contextvars.ContextVar`, so a thread or a task sees only its own. A
write of the file that fails with an :class:`OSError` is not answered: the
call's result stands, and a later build of the attempt finds the name free.
"""

import codecs
import contextlib
import contextvars
import json
import os
import reprlib
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import (
    attempt_kernel,
    check_failure,
    json_text,
    kernel_source,
    keys,
    layout,
    once_write,
)

SCHEMA_VERSION = 1
OUTCOMES = ("built", "broken")
CONDITIONS = ("build_time_limit", "build_exit_status")

_MEMBERS = ("schema_version", "outcome", "flags", "trailing_flags")
_CURRENT = contextvars.ContextVar("hilclaw.build_record.current", default=None)
_NO_KERNEL = (
    attempt_kernel.NO_SPEC_FILE,
    attempt_kernel.SPEC_OTHER_VERSION,
    *kernel_source.NO_KERNEL_SOURCE_CASES,
)


class InvalidBuildRecordError(ValueError):
    """A content, a document or a path breaks a rule; the message names it."""


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted."""


class MissingBuildRecordError(Exception):
    """No build record was written for the attempt; the message names the path."""


class BuildRecord(NamedTuple):
    """What a valid build record states (ADR-0198 decision 5).

    ``condition`` is ``None`` when ``outcome`` is ``"built"``. ``flags`` and
    ``trailing_flags`` are the arrays of the file, unchanged.
    """

    outcome: str
    condition: str | None
    flags: list
    trailing_flags: list


class KernelRefused(Exception):
    """:func:`evaluated` found no kernel to build; ``kind`` and ``message`` are those of the end line.

    ``kind`` is :data:`hilclaw.check_failure.KIND_NO_KERNEL_SOURCE` or
    :data:`hilclaw.check_failure.KIND_KERNEL_SOURCE_UNREADABLE`; ``message``
    names the reason of :mod:`hilclaw.attempt_kernel` and shows no path.
    """

    def __init__(self, kind, message):
        super().__init__(kind, message)
        self.kind = kind
        self.message = message


class CandidateBuild:
    """The candidate's flags for the kernel build of one call, and what that build gave (ADR-0198 decisions 5 and 6).

    ``path`` is the attempt's ``build.json``; ``flags`` the candidate's
    flags, a ``tuple`` of ``str``; ``document`` is ``None`` until
    :meth:`ended` is called, then the document of the first build it was
    told of.
    """

    __slots__ = ("document", "flags", "path")

    def __init__(self, path, flags):
        """Hold ``path``, a :class:`pathlib.Path`, and ``flags``.

        Raises :class:`TypeError` for a ``path`` that is no
        :class:`pathlib.Path` or ``flags`` that is not a ``tuple`` of ``str``.
        """
        if not isinstance(path, Path):
            raise TypeError(f"path must be a Path, not {type(path).__name__}")
        if type(flags) is not tuple or not all(type(flag) is str for flag in flags):
            raise TypeError("flags must be a tuple of str")
        self.path = path
        self.flags = flags
        self.document = None

    def __repr__(self):
        return f"<CandidateBuild of {len(self.flags)} flags>"

    def ended(self, condition, flags, trailing_flags):
        """Keep the document of a kernel build that ended (ADR-0198 decision 5).

        ``condition`` is ``None`` for a build answered built, else one of
        :data:`CONDITIONS`; ``flags`` and ``trailing_flags`` are the argument
        arrays handed to the compiler before and after the sources, each a
        sequence of ``str``. The first call keeps the document and every
        later one is ignored. Raises :class:`InvalidBuildRecordError` for
        values :func:`validate` refuses, nothing kept then.
        """
        document = {"schema_version": SCHEMA_VERSION}
        if condition is None:
            document["outcome"] = "built"
        else:
            document["outcome"] = "broken"
            document["condition"] = condition
        document["flags"] = list(flags)
        document["trailing_flags"] = list(trailing_flags)
        _checked(document)
        if self.document is None:
            self.document = document

    def write(self):
        """Write the kept document to :attr:`path` if the name is free; return whether it was written.

        Returns ``False`` when no build ended (:meth:`ended` was not called),
        when the name is taken, whatever is there, and when a step of the
        write failed with an :class:`OSError`; nothing is retried. Every
        missing directory above the path is created. The content is the
        document as JSON with two spaces of indent and a final line feed.
        """
        if self.document is None:
            return False
        content = (json.dumps(self.document, indent=2) + "\n").encode("utf-8")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            return once_write.write_once(self.path, content) is None
        except OSError:
            return False


class Evaluated(NamedTuple):
    """Answer of :func:`evaluated`: the ``output/`` to build and the :class:`CandidateBuild` or ``None``."""

    output_path: Path
    build: CandidateBuild | None


def current():
    """Return the :class:`CandidateBuild` :func:`building` made current here, or ``None``."""
    return _CURRENT.get()


@contextlib.contextmanager
def building(build):
    """Make ``build``, a :class:`CandidateBuild` or ``None``, what :func:`current` returns inside the block.

    The one current before is restored when the block ends, however it ends.
    Raises :class:`TypeError` for another ``build``.
    """
    if build is not None and type(build) is not CandidateBuild:
        raise TypeError(f"build must be a CandidateBuild, not {type(build).__name__}")
    token = _CURRENT.set(build)
    try:
        yield build
    finally:
        _CURRENT.reset(token)


def evaluated(data_root, run_id, round, candidate, attempt):
    """Return the :class:`Evaluated` of an attempt of a ``compile_settings`` run (ADR-0198 decisions 2 and 6).

    The attempt's spec is read by :func:`hilclaw.attempt_kernel.kernel_attempt`.
    For a version-2 spec the answer is the attempt's own ``output/`` and no
    build: it is evaluated as in a C kernel run, and its ``output/`` is not
    read here. For a version-3 spec the ``output/`` of the attempt it names
    must yield a compiled set (:func:`hilclaw.kernel_source.read_compiled_set`);
    the answer is that ``output/`` and a new :class:`CandidateBuild` of the
    spec's flags whose path is the attempt's own ``build.json``.

    Raises :class:`KernelRefused` with the kind the module docstring gives
    for each reason, and what :func:`hilclaw.attempt_kernel.kernel_attempt`
    raises for a malformed argument. Nothing is written.
    """
    numbers = round, candidate, attempt
    try:
        followed = attempt_kernel.kernel_attempt(data_root, run_id, *numbers)
        if followed.flags is None:
            own = layout.attempt_artefact(data_root, run_id, *numbers, "output")
            return Evaluated(own, None)
        named = followed.round, followed.candidate, followed.attempt
        output = layout.attempt_artefact(data_root, run_id, *named, "output")
        try:
            source = kernel_source.read_compiled_set(output)
        except kernel_source.KernelSourceReadError as error:
            raise attempt_kernel.AttemptKernelError(error.failure) from error
        if source.missing is not None:
            raise attempt_kernel.AttemptKernelError(source.missing)
    except attempt_kernel.AttemptKernelError as error:
        kind = check_failure.KIND_KERNEL_SOURCE_UNREADABLE
        if error.reason in _NO_KERNEL:
            kind = check_failure.KIND_NO_KERNEL_SOURCE
        message = f"the attempt gives no kernel to build: {error.reason}"
        raise KernelRefused(kind, message) from None
    path = layout.attempt_artefact(data_root, run_id, *numbers, "build.json")
    return Evaluated(output, CandidateBuild(path, followed.flags))


def parse(content):
    """Return the :class:`BuildRecord` of ``content``, the bytes of a ``build.json``.

    Raises :class:`TypeError` when ``content`` is no ``bytes``,
    :class:`InvalidBuildRecordError` when it is not UTF-8 without a byte order
    mark, not exactly one JSON text, holds a member name twice in an object
    or is a document :func:`validate` refuses, and
    :class:`UnsupportedVersionError` as that function does.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidBuildRecordError("content: starts with a byte order mark")
    try:
        document = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=json_text.distinct_members,
            parse_constant=json_text.no_constant,
        )
    except RecursionError:
        raise InvalidBuildRecordError(
            "content: is nested too deeply to parse"
        ) from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidBuildRecordError(reason) from None
    return _checked(document)


def validate(document):
    """Check ``document``, a parsed ``build.json``, against ADR-0198 decision 5.

    Raises :class:`UnsupportedVersionError` for an integer ``schema_version``
    from 0 to :data:`hilclaw.keys.MAX_INTEGER` other than 1, before any other
    member is looked at, and :class:`InvalidBuildRecordError` for the first
    other rule found broken: a member missing or not admitted, an
    ``outcome`` or ``condition`` outside its list, a ``condition`` with the
    outcome ``"built"`` or none with ``"broken"``, or an argument array that
    is not one of strings of at least one character without U+0000.
    """
    _checked(document)


def read(data_root, run_id, round, candidate, attempt):
    """Return the :class:`BuildRecord` of an attempt, read from its ``build.json``.

    The path is :func:`hilclaw.layout.attempt_artefact` for the tuple and
    ``build.json``; no other file is read and nothing is written. Raises
    :class:`hilclaw.layout.InvalidPathValueError` for a tuple that names no
    attempt; :class:`FileNotFoundError` or :class:`NotADirectoryError` when
    ``data_root`` is no existing directory; :class:`MissingBuildRecordError`
    when there is no file; :class:`InvalidBuildRecordError` when the path is
    no regular file or the content is invalid, and
    :class:`UnsupportedVersionError` for another version, each message
    prefixed with the path below ``data_root``; an :class:`OSError` of the
    file system, unchanged, when the file cannot be read.
    """
    numbers = round, candidate, attempt
    path = layout.attempt_artefact(data_root, run_id, *numbers, "build.json")
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    file = path.relative_to(root).as_posix()
    try:
        status = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        reason = f"{file}: is missing: no build record was written for this attempt"
        raise MissingBuildRecordError(reason) from None
    if not stat.S_ISREG(status.st_mode):
        raise InvalidBuildRecordError(f"{file}: is not a regular file")
    try:
        return parse(path.read_bytes())
    except (InvalidBuildRecordError, UnsupportedVersionError) as error:
        raise type(error)(f"{file}: {error}") from None


def _fail(place, rule, value):
    raise InvalidBuildRecordError(f"{place}: must be {rule}, got {reprlib.repr(value)}")


def _checked(document):
    if type(document) is not dict:
        _fail("document", "an object", document)
    if "schema_version" not in document:
        raise InvalidBuildRecordError("document: lacks the member schema_version")
    version = document["schema_version"]
    if type(version) is not int or not 0 <= version <= keys.MAX_INTEGER:
        _fail("schema_version", f"an int from 0 to {keys.MAX_INTEGER}", version)
    if version != SCHEMA_VERSION:
        raise UnsupportedVersionError(f"schema_version: {version} is not supported")
    for name in _MEMBERS:
        if name not in document:
            raise InvalidBuildRecordError(f"document: lacks the member {name}")
    for name in document:
        if name not in (*_MEMBERS, "condition"):
            _fail("document", "an object without the member", name)
    outcome = document["outcome"]
    if type(outcome) is not str or outcome not in OUTCOMES:
        _fail("outcome", " or ".join(OUTCOMES), outcome)
    condition = None
    if outcome == "broken":
        if "condition" not in document:
            raise InvalidBuildRecordError("document: lacks the member condition")
        condition = document["condition"]
        if type(condition) is not str or condition not in CONDITIONS:
            _fail("condition", " or ".join(CONDITIONS), condition)
    elif "condition" in document:
        _fail("condition", 'absent when outcome is "built"', document["condition"])
    flags = _arguments("flags", document["flags"])
    trailing = _arguments("trailing_flags", document["trailing_flags"])
    return BuildRecord(outcome, condition, flags, trailing)


def _arguments(place, value):
    if type(value) is not list:
        _fail(place, "an array", value)
    for index, item in enumerate(value):
        if type(item) is not str or not item or "\0" in item:
            _fail(
                f"{place}[{index}]",
                "a str of at least one character without U+0000",
                item,
            )
    return value
