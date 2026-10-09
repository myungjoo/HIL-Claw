"""The hw_profile record of the local ``cpu_standin`` (ADR-0035 decisions 2 to 6 and 8).

``ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md``, built on
ADR-0001, says which strings the key fields of a hw_profile hold when its
``accelerator`` is ``cpu_standin`` and the kernel is built and run on one
machine. :func:`local_record` reads those strings from the machine it runs on
and returns the record. Under WSL that machine is the Linux environment.

The rules, in short:

* ``revision`` is the word ``host`` (decision 5).
* ``toolchain`` has the one member ``clang``: the first line that
  ``<compiler> --version`` writes to standard output (decision 3).
* ``host`` has the members ``cpu`` and ``os`` and no other (decision 4). Which
  rule applies follows from the kernel name and the kernel release
  (:func:`os.uname`, the facts ``uname -s`` and ``uname -r`` name):

  ==========================================  =======================================
  kernel                                      ``host.cpu`` and ``host.os``
  ==========================================  =======================================
  ``Darwin``                                  the first line of the output of
                                              ``sysctl -n machdep.cpu.brand_string``;
                                              ``macos``, then the first line of the
                                              output of ``sw_vers -productVersion``
  ``Linux``, release contains ``microsoft``   as the next row, with the word ``wsl``
  in any case
  ``Linux`` otherwise                         of the first line of ``/proc/cpuinfo``
                                              whose text before its first colon,
                                              without spaces and tabs at both ends,
                                              is ``model name``: the text after that
                                              colon; ``linux``, then ``ID`` and, when
                                              the file has one, ``VERSION_ID`` of
                                              ``/etc/os-release``
  ==========================================  =======================================

  A value of ``/etc/os-release`` is the text after ``ID=`` or ``VERSION_ID=``
  on the first line that starts so, without one pair of double or single quotes
  around the whole of it. The words of ``host.os`` are joined by single spaces.
* A line is the text up to a line feed, without one carriage return directly
  before that line feed; nothing else ends a line. Every string taken from the
  machine is spelt in one way: each run of space and tab characters becomes one
  space, spaces at both ends are removed and nothing else is changed. The
  result must be 1 to 255 characters, each from 0x20 to 0x7E (decision 6).
* ``hw_source`` is the caller's statement and is never read from the machine
  (decision 8).

A fact that cannot be read by these rules is an :class:`UnreadableFactError`
and no record is returned. Nothing is substituted: no placeholder, no cut or
transliterated text and no value from another source.

What the module does not do: it registers and stores nothing, is bound to no
tool and to no start of an instance, and has no command-line entry. It knows no
other accelerator and no other machine than the one the process runs on, adds
no further member to ``toolchain`` or ``host``, does not tell WSL 1 from WSL 2
and never compares a machine with a record again. The limits ADR-0035 names in
decision 7 are not handled: the first ``model name`` line stands for the
machine. Nothing checks that ``compiler`` is the compiler a later build uses
(decision 3).

The kernel name is read first, and for a name without a rule nothing is
started. Otherwise the module starts at most three commands through
:func:`hilclaw.local_run.run` (without a shell, found on ``PATH``, with the
limits that module documents): ``<compiler> --version`` and, for the kernel
name ``Darwin`` only, ``sysctl -n machdep.cpu.brand_string`` and
``sw_vers -productVersion``. It reads the two files named above and no other,
and writes none. Every fact is read at each call and nothing is kept between
calls.
"""

import os
import re
import reprlib

from hilclaw import clang_build, keys, local_run

ACCELERATOR = "cpu_standin"
REVISION = "host"

_CPUINFO = "/proc/cpuinfo"
_OS_RELEASE = "/etc/os-release"
_CPU_COMMAND = ("sysctl", "-n", "machdep.cpu.brand_string")
_OS_COMMAND = ("sw_vers", "-productVersion")
_RUN = re.compile(rb"[ \t]+")
_STRING = re.compile(rb"[\x20-\x7e]+")
_MICROSOFT = re.compile("microsoft", re.ASCII | re.IGNORECASE)
_MAX_LENGTH = 255


class UnreadableFactError(RuntimeError):
    """A fact of the machine cannot be read, so no record is made (ADR-0035 decision 6).

    The message starts with the fact (``toolchain.clang``, ``host.cpu``,
    ``host.os`` or ``kernel name``) and gives the reason. It holds no text read
    from the machine. Decision 6 lists the cases of the record;
    :func:`local_record` says which further cases this module reads as such.
    """


def local_record(hw_source, *, timeout_s, compiler=None):
    """Return the hw_profile record of the ``cpu_standin`` this process runs on.

    The result is a new ``dict`` with exactly the members ``schema_version``
    (:data:`hilclaw.keys.SCHEMA_VERSION`), ``accelerator``
    (:data:`ACCELERATOR`), ``revision`` (:data:`REVISION`), ``toolchain``
    (``{"clang": ...}``), ``host`` (``{"cpu": ..., "os": ...}``) and
    ``hw_source``. It is a record :func:`hilclaw.keys.hw_profile_key` accepts;
    the key is not returned, and the record is neither stored nor registered.

    ``hw_source`` is one of :data:`hilclaw.keys.HW_SOURCES`. It has no default
    and is checked before the machine is read. ``timeout_s`` is the limit in
    seconds of each command that is started. ``compiler`` names the clang whose
    version line is read: ``None`` for
    :data:`hilclaw.clang_build.DEFAULT_COMPILER` on ``PATH``, the name or path
    of an executable (``str`` or :class:`os.PathLike`), or a sequence used as a
    command prefix: the program followed by ``str`` arguments.

    Raises :class:`hilclaw.keys.InvalidRecordError` for a ``hw_source`` that is
    not one of the two values, whatever the machine holds. Raises
    :class:`UnreadableFactError` when a fact cannot be read. The cases of the
    record: a command that is not found or ends with a status other than 0; a
    file that is missing; no ``model name`` line; no ``ID`` line; an ``ID`` or
    a ``VERSION_ID`` that, without its quotes, is empty or holds a space or a
    tab; a kernel name other than ``Darwin`` and ``Linux``, compared as it is;
    and a value that after the spelling rule is empty, longer than 255
    characters or holds a character outside 0x20 to 0x7E. Read as such by this
    module, where the record names no case: a command that cannot be started
    or does not finish within ``timeout_s``, a file that exists and cannot be
    read, and a platform without :func:`os.uname`.

    What :func:`hilclaw.local_run.run` raises for its arguments is passed on,
    from the first command and after the kernel name was read:
    :class:`TypeError` for a ``timeout_s`` that is not a number or a
    ``compiler`` part of the wrong type, :class:`ValueError` for a
    ``timeout_s`` that is not positive and finite or an argument
    :mod:`subprocess` cannot hand over, and :class:`OverflowError` for a finite
    ``timeout_s`` longer than the platform can wait for. An empty ``compiler``
    prefix is a :class:`ValueError` raised before the machine is read.
    """
    if type(hw_source) is not str or hw_source not in keys.HW_SOURCES:
        rule = " or ".join(keys.HW_SOURCES)
        got = reprlib.repr(hw_source)
        raise keys.InvalidRecordError(f"hw_source: must be {rule}, got {got}")
    command = (*_prefix(compiler), "--version")
    name, release = _kernel()
    if name not in ("Darwin", "Linux"):
        raise UnreadableFactError("kernel name: this module has no rule for it")
    clang = _command_line("toolchain.clang", command, "<compiler> --version", timeout_s)
    if name == "Darwin":
        cpu = _command_line("host.cpu", _CPU_COMMAND, " ".join(_CPU_COMMAND), timeout_s)
        words = [
            b"macos",
            _command_line("host.os", _OS_COMMAND, " ".join(_OS_COMMAND), timeout_s),
        ]
    else:
        cpu = _cpuinfo_model_name()
        lines = _file_lines("host.os", _OS_RELEASE)
        distribution = _os_release_value(lines, b"ID")
        if distribution is None:
            raise UnreadableFactError(f"host.os: {_OS_RELEASE} has no ID line")
        version = _os_release_value(lines, b"VERSION_ID")
        words = [b"wsl" if _MICROSOFT.search(release) else b"linux", distribution]
        if version is not None:
            words.append(version)
    return {
        "schema_version": keys.SCHEMA_VERSION,
        "accelerator": ACCELERATOR,
        "revision": REVISION,
        "toolchain": {"clang": clang.decode("ascii")},
        "host": {
            "cpu": cpu.decode("ascii"),
            "os": _spelling("host.os", b" ".join(words)).decode("ascii"),
        },
        "hw_source": hw_source,
    }


def _kernel():
    if not hasattr(os, "uname"):
        raise UnreadableFactError("kernel name: this platform has no os.uname")
    uname = os.uname()
    return uname.sysname, uname.release


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


def _run(command, timeout_s):
    return local_run.run(command, timeout_s=timeout_s)


def _prefix(compiler):
    if compiler is None:
        return (clang_build.DEFAULT_COMPILER,)
    if isinstance(compiler, (str, os.PathLike)):
        return (compiler,)
    prefix = tuple(compiler)
    if not prefix:
        raise ValueError("compiler command prefix is empty")
    return prefix


def _lines(data):
    *ended, last = data.split(b"\n")
    return [line.removesuffix(b"\r") for line in ended] + [last]


def _spelling(fact, raw):
    text = _RUN.sub(b" ", raw).strip(b" ")
    if not text:
        raise UnreadableFactError(f"{fact}: the value is empty")
    if len(text) > _MAX_LENGTH:
        raise UnreadableFactError(
            f"{fact}: the value is longer than {_MAX_LENGTH} characters"
        )
    if not _STRING.fullmatch(text):
        raise UnreadableFactError(
            f"{fact}: the value holds a character outside 0x20 to 0x7E"
        )
    return text


def _command_line(fact, command, shown, timeout_s):
    try:
        result = _run(command, timeout_s)
    except local_run.ProgramNotFoundError:
        raise UnreadableFactError(
            f"{fact}: the command of `{shown}` was not found"
        ) from None
    except OSError as error:
        reason = type(error).__name__
        raise UnreadableFactError(
            f"{fact}: `{shown}` could not be started ({reason})"
        ) from None
    if result.timed_out:
        raise UnreadableFactError(
            f"{fact}: `{shown}` did not finish within {timeout_s} s"
        )
    if result.returncode != 0:
        raise UnreadableFactError(
            f"{fact}: `{shown}` ended with status {result.returncode}"
        )
    return _spelling(fact, _lines(result.stdout)[0])


def _file_lines(fact, path):
    try:
        return _lines(_read(path))
    except OSError as error:
        reason = type(error).__name__
        raise UnreadableFactError(f"{fact}: {path} cannot be read ({reason})") from None


def _cpuinfo_model_name():
    for line in _file_lines("host.cpu", _CPUINFO):
        name, colon, value = line.partition(b":")
        if colon and name.strip(b" \t") == b"model name":
            return _spelling("host.cpu", value)
    raise UnreadableFactError(f"host.cpu: {_CPUINFO} has no model name line")


def _os_release_value(lines, name):
    start = name + b"="
    for line in lines:
        if line.startswith(start):
            value = line[len(start) :]
            quoted = len(value) >= 2 and value[:1] == value[-1:]
            if quoted and value[:1] in (b'"', b"'"):
                value = value[1:-1]
            if not value or b" " in value or b"\t" in value:
                label = name.decode("ascii")
                raise UnreadableFactError(
                    f"host.os: {label} in {_OS_RELEASE} is empty "
                    "or holds a space or a tab"
                )
            return value
    return None
