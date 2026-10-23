"""The command-line entry that starts a first-case instance (ADR-0155).

Command line: ``python -m hilclaw.new_run <file>``. The one argument is the
path of a file whose content is the ``instance.json`` document as JSON; no
option exists and nothing is read from standard input. A person or a script
runs it to start an instance of ADR-0076 decision 1. It calls
:func:`hilclaw.start_instance.start` once and is the caller of that function
for such a start (ADR-0155 decision 2). It is no FR-10 tool and has no entry
in :mod:`hilclaw.tools` or any registry and no MCP name.

**One start**, in this order: standard output must exist; exactly one
argument; the file is read and decoded; the data root is obtained once with
:func:`hilclaw.data_root_source.obtain` from the source (by default
:func:`hilclaw.data_root_source.configured`, so ``hilclaw.config``); then
:func:`hilclaw.start_instance.start` is called once with the parsed object,
unchanged: nothing is added, defaulted or removed, and nobody is asked. Every
failure before ``start`` starts nothing, and nothing is written before it.

**Decoding rules** (ADR-0155 decision 3, this module's): the bytes are decoded
as strict UTF-8 and parsed as one JSON text by :func:`json.loads`. A leading
byte order mark, a member name given twice in one object (at any depth), and
the tokens ``NaN``, ``Infinity`` and ``-Infinity`` are **bad input**. A number
too large for a float, such as ``1e400``, is parsed as an infinity and handed
on; ``start`` refuses it as **invalid** in a member :mod:`hilclaw.instance`
defines and as **unwritable value** elsewhere.

**What the starter is told**, through the process only. Standard output gets
exactly one line, a compact JSON object in ASCII ended by one LF, whose member
``outcome`` names the kind; the data are further members:

=====================  ======  ===================================================
``outcome``            status  further members
=====================  ======  ===================================================
``started``            0       ``run_id``: the id ``start`` built
``given_run_id``       10      none
``missing_members``    11      ``missing``: list, in the order of ``REPORT_ORDER``
``invalid``            12      ``reason``
``out_of_scope``       13      ``reason``
``run_id_in_use``      14      ``run_id``: the id ``start`` built
``file_system``        15      ``reason``
``unwritable_value``   16      ``reason``
``bad_usage``          20      ``reason``
``unreadable_input``   21      ``reason``
``bad_input``          22      ``reason``
``no_data_root``       23      ``reason``
``fault``              24      ``fault``: the class name of the exception, if any
=====================  ======  ===================================================

Each kind has its own status; only ``started`` has 0 and no status is 1 or 2.
``reason`` is free text, which may name a path, and is never parsed.
``invalid`` is :class:`hilclaw.instance.InvalidInstanceError` or
:class:`hilclaw.instance.UnsupportedVersionError`; ``unwritable_value`` is the
plain :class:`ValueError` of :func:`json.dumps` inside ``start``, told apart by
its exact class; ``run_id_in_use`` is
:class:`hilclaw.start_instance.RunIdInUseError`, told apart from the
:class:`OSError` of ``file_system``. Any other :class:`Exception` is ``fault``.

Standard error gets nothing for a kind, with two exceptions. A process
without a standard output gets ``fault`` (status 24), said on standard error,
and nothing is started. When the line cannot be written, or is written only
in part, standard error gets one line saying so and the status is 24; after a
started run that line names the run id. No traceback reaches the starter, and
:class:`KeyboardInterrupt` and :class:`SystemExit` are not caught.

**What it does not do** (ADR-0155 decision 6): it starts no turn, turn loop,
self-check or ``claude``; writes no ``STATE.json`` and no line of
``events.ndjson``; makes no commit, takes no lock, looks at no run directory
before ``start`` and writes nothing beyond what ``start`` writes. The starter
goes on with ``python -m hilclaw.turn_start <run_id>``, with the id of the
``started`` line.
"""

import contextlib
import json
import sys
from pathlib import Path

from hilclaw import data_root_source, instance, instance_start, start_instance, tools

STARTED = "started"
GIVEN_RUN_ID = "given_run_id"
MISSING_MEMBERS = "missing_members"
INVALID = "invalid"
OUT_OF_SCOPE = "out_of_scope"
RUN_ID_IN_USE = "run_id_in_use"
FILE_SYSTEM = "file_system"
UNWRITABLE_VALUE = "unwritable_value"
BAD_USAGE = "bad_usage"
UNREADABLE_INPUT = "unreadable_input"
BAD_INPUT = "bad_input"
NO_DATA_ROOT = "no_data_root"
FAULT = "fault"

EXIT_STATUS = {
    STARTED: 0,
    GIVEN_RUN_ID: 10,
    MISSING_MEMBERS: 11,
    INVALID: 12,
    OUT_OF_SCOPE: 13,
    RUN_ID_IN_USE: 14,
    FILE_SYSTEM: 15,
    UNWRITABLE_VALUE: 16,
    BAD_USAGE: 20,
    UNREADABLE_INPUT: 21,
    BAD_INPUT: 22,
    NO_DATA_ROOT: 23,
    FAULT: 24,
}


class _Refused(ValueError):
    pass


def _described(error):
    try:
        return f"{type(error).__name__}: {error}"
    except Exception:  # noqa: BLE001
        return type(error).__name__


def _told(outcome, reason):
    return {"outcome": outcome, "reason": reason}


def _unique(pairs):
    made = {}
    for name, value in pairs:
        if name in made:
            raise _Refused(f"the member name {name!r} is given twice in one object")
        made[name] = value
    return made


def _constant(token):
    raise _Refused(f"the token {token} is not JSON")


def _parsed(path):
    try:
        content = Path(path).read_bytes()
    except (OSError, ValueError) as e:
        return None, _told(UNREADABLE_INPUT, _described(e))
    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique,
            parse_constant=_constant,
        )
    except (ValueError, RecursionError) as e:
        return None, _told(BAD_INPUT, _described(e))
    if type(value) is not dict:
        return None, _told(
            BAD_INPUT, f"the JSON text is no object, got {type(value).__name__}"
        )
    return value, None


def _started(document, root):
    try:
        built = start_instance.start(document, data_root=root)
    except start_instance.GivenRunIdError:
        return {"outcome": GIVEN_RUN_ID}
    except instance_start.MissingMembersError as e:
        return {"outcome": MISSING_MEMBERS, "missing": list(e.missing)}
    except (instance.InvalidInstanceError, instance.UnsupportedVersionError) as e:
        return _told(INVALID, _described(e))
    except instance_start.OutOfScopeError as e:
        return _told(OUT_OF_SCOPE, _described(e))
    except start_instance.RunIdInUseError as e:
        return {"outcome": RUN_ID_IN_USE, "run_id": e.run_id}
    except OSError as e:
        return _told(FILE_SYSTEM, _described(e))
    except Exception as e:  # noqa: BLE001
        if type(e) is ValueError:
            return _told(UNWRITABLE_VALUE, _described(e))
        return {"outcome": FAULT, "fault": type(e).__name__}
    return {"outcome": STARTED, "run_id": built}


def _start(args, source):
    if len(args) != 1:
        return _told(BAD_USAGE, f"usage: expected one file, got {len(args)} arguments")
    document, refused = _parsed(args[0])
    if refused is not None:
        return refused
    try:
        root = data_root_source.obtain(source)
    except tools.ToolFailure as e:
        return _told(NO_DATA_ROOT, e.message)
    except Exception as e:  # noqa: BLE001
        return {"outcome": FAULT, "fault": type(e).__name__}
    return _started(document, root)


def _standard(name):
    return getattr(getattr(sys, name), "buffer", None)


def _say(stderr, text):
    with contextlib.suppress(Exception):
        if stderr is not None:
            line = f"hilclaw.new_run: {text}".replace("\r", " ").replace("\n", " ")
            stderr.write((line + "\n").encode("utf-8", "backslashreplace"))
            stderr.flush()


def main(argv=None, *, source=data_root_source.configured, stdout=None, stderr=None):
    """Start the instance of the file named by the one argument; return the exit status.

    ``argv`` defaults to ``sys.argv[1:]``. ``source`` is the data-root source
    (:mod:`hilclaw.data_root_source`), asked once and only after the input was
    read. ``stdout`` and ``stderr`` are binary streams and default to the
    standard ones; a standard stream that the process does not have, or that
    has no binary layer, is missing. Returns the status of the module
    docstring's table; no :class:`Exception` leaves the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    if stdout is None:
        _say(stderr, "fault: there is no standard output; nothing was started")
        return EXIT_STATUS[FAULT]
    told = _start(args, source)
    try:
        line = tools.encode(told)
        if stdout.write(line) != len(line):
            raise OSError("it took a part of the line")
        stdout.flush()
    except Exception as e:  # noqa: BLE001
        text = f"cannot write standard output: {_described(e)}"
        if told["outcome"] == STARTED:
            text += f"; the run {told['run_id']} was started"
        _say(stderr, text)
        return EXIT_STATUS[FAULT]
    return EXIT_STATUS[told["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())
