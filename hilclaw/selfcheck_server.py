"""The server side of the runtime self-check (ADR-0054 decisions 5 and 6).

Renders "Which server and which tools" (decision 5), the server side of "Three
sides" (decision 6) and, of the configuration-file paragraph of decision 4,
the values of the server entry.

**The server** is the unchanged :mod:`hilclaw.mcp_front`: :func:`main` calls
``mcp_front.main`` with the registry of :func:`registry` and with streams that
copy every line; no rule of the front is changed and no line is read ahead,
parsed or filtered. **The registry** holds :data:`TOKEN_TOOL` and
:data:`FAIL_TOOL` and nothing else; they are never tools of a run, and nothing
is registered into a registry the module did not make. ``selfcheck.token``
returns ``{"token": <first token>}``; ``selfcheck.fail`` raises a tool failure
of kind :data:`FAIL_KIND` whose message ends with the second token. Each takes
any request object and ignores its members, so a stray argument of the model
changes neither answer. They keep no state and read nothing.

**The tokens** come from outside: the entry creates none and has no default.
A token is 32 lowercase hexadecimal characters (:func:`new_token` makes one)
and the two must differ. A token is in no name, description or input schema,
so in no answer to ``initialize`` or ``tools/list``; the first is only in the
result of ``selfcheck.token``, the second only in the failure of
``selfcheck.fail``. They are no credential: who can read the server entry, the
environment of the server process or the wire copy can read them.

**The server entry** (:func:`server_entry`) is ``command``, ``args`` and
``env`` of one stdio server. It holds only values made here or handed in: the
interpreter that builds it (``sys.executable``), the directory that holds this
package (from the module's own location), the two tokens and the place of the
wire copy. Nothing of ``os.environ`` is read or copied. The command line is
``<python> -I -c <one line> <package directory>``; the one line puts that
directory first on the module path and calls :func:`main`, which takes no
argument. The tokens and the place travel in ``env`` as :data:`ENV_TOKEN`,
:data:`ENV_FAIL_TOKEN` and :data:`ENV_WIRE_COPY`, since the arguments of a
process show in the process listing. ``-I -c`` was taken over ``-m`` with
``PYTHONPATH``: the working directory is then not on the module path, no
``PYTHON*`` variable of whoever starts the server acts, an installed
distribution does not win, and a directory whose name holds the path separator
works. The place of the wire copy must be an absolute path, for the same
independence of the working directory.

**The wire copy** is one file, created exclusively (an existing file is
refused, never extended): the line :data:`WIRE_COPY_MAGIC`, then one record
per line passed - ``C`` (from the client) or ``S`` (from the server), a space,
the length of the line in decimal, LF, the bytes of the line unchanged, LF -
so any bytes round-trip. A line of the client is copied as ``readline``
returned it, before the front gets it. A line of the server is copied after it
was written and flushed to the real output: the copy never holds an answer
that was not sent. A record is handed to the system, unbuffered, before the
entry goes on; standard error is not copied. A copy that fails reaches the
front as the ``OSError`` of its stream and the front gives up by its own rule:
no line is handled that the copy does not show, except that the one answer
whose copy failed was already sent, and none follows it. The file grows with
the session, without a size limit.

:func:`read_wire_copy` returns the copied lines in order. A file that does not
begin with the whole magic line, an empty one included, is no wire copy
(:class:`WireCopyError`). After that line, reading stops at the first place
where no whole record stands - a cut or malformed record - and ``torn`` says
that bytes were left; none of them is returned as a line. It reads the file
into memory, parses no JSON-RPC and judges nothing.

**Exit status**, as the front: 0 at the end of input, 4 when the entry or the
front gives up; never 1 or 2. The entry gives up before a line is read when an
argument was given, a token or the place is missing or malformed, or the wire
copy cannot be created; standard error gets one fixed line, no token, no path.

Not done here: no ``claude`` is started; no session, prompt, configuration
file, directory of the check, outcome or report is here. Nothing calls it yet.

Known limits. The tests show a child process of the tests, on Linux and
Windows; that Claude Code starts this entry and finds the package on each kind
of machine (macOS and WSL too), and that it shows nothing of the entry to the
model, are runtime acceptance items (vii) and (viii) of ADR-0054. Modules that
lie beside the package directory come before the standard library on the
module path of the server process.
"""

import contextlib
import os
import re
import secrets
import sys
from typing import NamedTuple

from hilclaw import mcp_front, tools

TOKEN_TOOL = "selfcheck.token"
FAIL_TOOL = "selfcheck.fail"
RESULT_MEMBER = "token"
FAIL_KIND = "selfcheck_expected"
ENV_TOKEN = "HILCLAW_SELFCHECK_TOKEN"
ENV_FAIL_TOKEN = "HILCLAW_SELFCHECK_FAIL_TOKEN"
ENV_WIRE_COPY = "HILCLAW_SELFCHECK_WIRE_COPY"
FROM_CLIENT = "client"
FROM_SERVER = "server"
WIRE_COPY_MAGIC = b"hilclaw selfcheck wire copy 1\n"

_PACKAGE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOKEN = re.compile(r"[0-9a-f]{32}")
_RECORD = re.compile(rb"([CS]) (0|[1-9][0-9]{0,17})\n")
_MARKS = {FROM_CLIENT: b"C", FROM_SERVER: b"S"}
_DIRECTIONS = {mark: direction for direction, mark in _MARKS.items()}
_SCHEMA = {"type": "object", "properties": {}}
_TOKEN_DESCRIPTION = (
    "Runtime self-check of hilclaw: returns a result whose member "
    '"token" holds a one-time value. Call it without arguments.'
)
_FAIL_DESCRIPTION = (
    "Runtime self-check of hilclaw: always answers with a tool failure whose "
    "message holds a second one-time value. The failure is expected. Call it "
    "without arguments."
)
_FAIL_TEXT = "the self-check asked for this failure; its token is "
_START = (
    "import sys; sys.path.insert(0, sys.argv.pop(1)); "
    "from hilclaw.selfcheck_server import main; raise SystemExit(main())"
)


class WireCopyError(ValueError):
    """The file does not begin with :data:`WIRE_COPY_MAGIC`: it is no wire copy."""


class WireCopy(NamedTuple):
    """What :func:`read_wire_copy` found.

    ``lines`` is a tuple of ``(direction, line)`` in the order copied: the
    direction is :data:`FROM_CLIENT` or :data:`FROM_SERVER`, the line ``bytes``.
    ``torn`` is true when bytes follow the last whole record.
    """

    lines: tuple
    torn: bool


def new_token():
    """Return a new random token of the form the entry accepts."""
    return secrets.token_hex(16)


def _check_tokens(token, fail_token):
    for value in (token, fail_token):
        if type(value) is not str:
            raise TypeError("a token must be a str")
        if not _TOKEN.fullmatch(value):
            raise ValueError("a token must be 32 lowercase hexadecimal characters")
    if token == fail_token:
        raise ValueError("the two tokens must differ")


def _checked_place(wire_copy):
    place = os.fspath(wire_copy)
    if type(place) is not str:
        raise TypeError("the place of the wire copy must be a str or a path")
    if "\0" in place or not os.path.isabs(place):
        raise ValueError("the place of the wire copy must be an absolute path")
    return place


def registry(token, fail_token):
    """Return a new registry that holds the two tools of the check and nothing else.

    Raises :class:`TypeError` for a token that is not a ``str`` and
    :class:`ValueError` for one of another form or two equal ones; no message
    holds a token.
    """
    _check_tokens(token, fail_token)

    def give(request):
        return {RESULT_MEMBER: token}

    def fail(request):
        raise tools.ToolFailure(FAIL_KIND, _FAIL_TEXT + fail_token)

    held = tools.Registry()
    held.register(TOKEN_TOOL, give, _TOKEN_DESCRIPTION, _SCHEMA)
    held.register(FAIL_TOOL, fail, _FAIL_DESCRIPTION, _SCHEMA)
    return held


def server_entry(*, token, fail_token, wire_copy):
    """Return the stdio server entry that starts :func:`main` with these values.

    A new ``dict`` of exactly ``command`` (``str``), ``args`` (``list`` of
    ``str``) and ``env`` (``dict`` of ``str`` with exactly the three ``ENV_``
    names). ``wire_copy`` is a ``str`` or path object naming an absolute path;
    nothing is created. Raises as :func:`registry` for the tokens,
    :class:`TypeError` or :class:`ValueError` for another ``wire_copy``, and
    :class:`RuntimeError` when the interpreter does not know its own path. No
    message holds a token or a path.
    """
    _check_tokens(token, fail_token)
    place = _checked_place(wire_copy)
    if not sys.executable:
        raise RuntimeError("the interpreter does not know its own path")
    return {
        "command": sys.executable,
        "args": ["-I", "-c", _START, _PACKAGE_DIRECTORY],
        "env": {ENV_TOKEN: token, ENV_FAIL_TOKEN: fail_token, ENV_WIRE_COPY: place},
    }


def read_wire_copy(path):
    """Return the :class:`WireCopy` of the file at ``path`` (a ``str`` or path object).

    Raises :class:`WireCopyError` for a file that is no wire copy and the
    :class:`OSError` of the system, whose message may name the path, for one
    that is not there or cannot be read; nothing else of the content raises.
    """
    with open(os.fspath(path), "rb") as file:
        data = file.read()
    if not data.startswith(WIRE_COPY_MAGIC):
        raise WireCopyError("not a wire copy")
    lines, at = [], len(WIRE_COPY_MAGIC)
    while header := _RECORD.match(data, at):
        end = header.end() + int(header[2])
        if data[end : end + 1] != b"\n":
            break
        lines.append((_DIRECTIONS[header[1]], data[header.end() : end]))
        at = end + 1
    return WireCopy(tuple(lines), at != len(data))


def _put(copy, data):
    left = memoryview(data)
    try:
        while left:
            left = left[copy.write(left) :]
    except (OSError, ValueError):
        raise OSError("the wire copy cannot be written") from None


class _Copied:
    def __init__(self, stream, copy):
        self._stream, self._copy = stream, copy

    def _record(self, mark, line):
        _put(self._copy, b"%s %d\n%s\n" % (mark, len(line), line))

    def readline(self):
        line = self._stream.readline()
        if line:
            self._record(_MARKS[FROM_CLIENT], line)
        return line

    def write(self, data):
        self._stream.write(data)
        self._stream.flush()
        self._record(_MARKS[FROM_SERVER], data)

    def flush(self):
        self._stream.flush()


def _standard(name):
    return getattr(getattr(sys, name), "buffer", None)


def _give_up(stderr, text):
    with contextlib.suppress(OSError, ValueError):
        if stderr is not None:
            stderr.write(f"hilclaw.selfcheck_server: {text}\n".encode("ascii"))
            stderr.flush()
    return mcp_front.EXIT_FRONT_FAILURE


def main(argv=None, *, environ=None, stdin=None, stdout=None, stderr=None):
    """Serve the two tools over the copying streams and return the exit status (0 or 4).

    ``argv`` defaults to ``sys.argv[1:]`` and must be empty. ``environ`` is the
    mapping the tokens and the place of the wire copy are read from and
    defaults to ``os.environ``; no other variable is read. The three streams
    are binary and default to the standard ones, as
    :func:`hilclaw.mcp_front.main` takes them.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    environ = os.environ if environ is None else environ
    stdin = _standard("stdin") if stdin is None else stdin
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    if args:
        return _give_up(stderr, "expected no argument")
    try:
        held = registry(environ.get(ENV_TOKEN), environ.get(ENV_FAIL_TOKEN))
        place = _checked_place(environ.get(ENV_WIRE_COPY))
    except (TypeError, ValueError):
        return _give_up(stderr, "a token or the place of the wire copy is not usable")
    try:
        with open(place, "xb", buffering=0) as copy:
            _put(copy, WIRE_COPY_MAGIC)
            return mcp_front.main(
                [],
                registry=held,
                stdin=None if stdin is None else _Copied(stdin, copy),
                stdout=None if stdout is None else _Copied(stdout, copy),
                stderr=stderr,
            )
    except OSError:
        return _give_up(stderr, "the wire copy cannot be created or written")
