"""The runtime self-check: its composition and its command (ADR-0054 decisions 1, 3, 4, 7).

Command line: ``python -m hilclaw.selfcheck``. It takes no argument and no
option, and reads nothing from standard input. This is runtime code: on a
runtime machine it starts the real ``claude``. It is built and tested against a
stub ``claude`` that the tests write, never against a real one (D16).

**One check** is :func:`check`, in this order and with nothing tried twice:

1. ``selfcheck_login.read`` once, under :data:`LOGIN_TIMEOUT_S`, in the
   working directory of the calling process;
2. only when that says logged in (``outcome is None``),
   ``selfcheck_session.run`` once, under :data:`SESSION_TIMEOUT_S`, with the
   configured data root in ``keep_out``; after any other answer no session is
   started;
3. ``selfcheck_report.build`` over the two values and
   ``selfcheck_report.system_facts()``.

:func:`main` runs one check, writes ``selfcheck_report.line`` of the report to
standard output, flushes it and returns
``selfcheck_report.exit_status(report["outcome"])``: 0 when the outcome is
``passed`` and for nothing else, 10 to 15 for the other six outcomes.

**What leaves the command.** Standard output gets the one report line or
nothing. Standard error gets nothing when a report was written, and one fixed
line otherwise (below). No progress, no path, no token, no command line and
nothing of a child's output is written, and the standard error of a child is
not passed on. The module writes no file, sets, removes and reads no
environment variable and hands no ``env`` on; what ``hilclaw.config`` reads to
name the data root is that module's.

**Conventions of this module** (the record leaves them to the code):

- *The two time limits* are fixed constants, 30 and 300 seconds; no argument,
  option or environment variable changes them. **Both are provisional**: no
  run on a runtime machine stands behind either (a runtime acceptance item,
  HQ-0016). A limit that is too short costs a pass, never a false one: the
  outcome is then ``login_unreadable`` or ``session_failed``.
- *The data root* is asked of ``data_root_source.configured`` once, just
  before the session, and only named to it: nothing in it is read or written
  and it need not exist. **When none is configured**
  (``hilclaw.config.ConfigError``) **the check goes on with an empty**
  ``keep_out``: the check needs no data root (decision 5), and a bring-up
  without a configuration fails for that elsewhere. "Outside both checkouts"
  is then checked against the source checkout only. Nothing of this is in the
  report and the text of that error, which names a path, reaches no stream.
- *A fault of the check itself* is :data:`EXIT_FAULT` (20): any
  :class:`Exception` of a step, of the report or of the data-root source
  other than the one above - "What is raised" of ``selfcheck_session``, a
  directory of the check that would lie inside a checkout included - and a
  standard output that is closed, cannot be written or flushed, or takes
  fewer bytes than the line. **It is not an eighth outcome and has no
  report**: nothing is written to standard output unless the write itself
  failed part-way, so with this status whatever standard output holds is no
  report. The value is none of 0, 1, 2 (the interpreter's), 3, 4
  (``python -m hilclaw``), 10 to 15 (the outcomes), 120, and 126 and above.
  If the interpreter's own flush at exit fails as well, the status is 120.
- *Standard error* then gets one line, ``hilclaw.selfcheck: fault: <class>``:
  the name of the exception's class and **never its text**, which may name a
  path under the user's name. A standard error that is closed or cannot be
  written gets nothing, and the status stays.
- *A bad usage* - any argument, ``--help`` and the empty string included -
  shares :data:`EXIT_FAULT`: it is refused before anything is started, no
  report is written, and standard error gets the fixed line
  ``hilclaw.selfcheck: usage: no argument is taken``.
- :class:`KeyboardInterrupt` and :class:`SystemExit` are not caught;
  ``selfcheck_session.run`` still removes its directory.

Known limits. Running the command starts ``claude`` and, when logged in,
spends one session of plan usage; when to run it is the caller's (L5). A pass
is one observation (L2). Whoever controls the ``PATH`` or the environment
decides what is seen (L6). ``system_facts()`` may start a system command of
the interpreter's own on some platforms. A ``session_failed`` report says how
far the session got and not why. The instance's log, how the report reaches
it and where the record of the check is stored are not this module's (O7);
what a bring-up does after each outcome is PLAN P2-1's. The limits of the
steps are said in their modules. Nothing calls the module yet.
"""

import contextlib
import sys

from hilclaw import (
    config,
    data_root_source,
    selfcheck_login,
    selfcheck_report,
    selfcheck_session,
)

LOGIN_TIMEOUT_S = 30
SESSION_TIMEOUT_S = 300
EXIT_FAULT = 20


def _keep_out():
    try:
        return (data_root_source.configured(),)
    except config.ConfigError:
        return ()


def check():
    """Run one check and return its report, the ``dict`` of ``selfcheck_report.build``.

    Step one is called once and step two at most once, as the module docstring
    orders them; nothing is written to a stream. Every outcome is a returned
    report. What the steps, the report and the data-root source raise is
    passed on (``hilclaw.config.ConfigError`` of the source excepted), with
    their own text, which may name a path.
    """
    login = selfcheck_login.read(timeout_s=LOGIN_TIMEOUT_S)
    run = None
    if login.outcome is None:
        run = selfcheck_session.run(timeout_s=SESSION_TIMEOUT_S, keep_out=_keep_out())
    return selfcheck_report.build(login, run, system=selfcheck_report.system_facts())


def _standard(name):
    return getattr(getattr(sys, name), "buffer", None)


def _say(stderr, text):
    with contextlib.suppress(OSError, ValueError):
        if stderr is not None:
            line = f"hilclaw.selfcheck: {text}\n"
            stderr.write(line.encode("ascii", "backslashreplace"))
            stderr.flush()


def main(argv=None, *, stdout=None, stderr=None):
    """Run one check, write its report line and return the exit status.

    ``argv`` defaults to ``sys.argv[1:]`` and must be empty. ``stdout`` and
    ``stderr`` are binary streams and default to the standard ones; a
    standard stream that is closed or has no binary layer counts as closed.
    Returns ``selfcheck_report.exit_status`` of the outcome written, or
    :data:`EXIT_FAULT` when no report was written; no :class:`Exception`
    leaves the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    if args:
        _say(stderr, "usage: no argument is taken")
        return EXIT_FAULT
    try:
        report = check()
        line = selfcheck_report.line(report)
        status = selfcheck_report.exit_status(report["outcome"])
        if stdout is None:
            raise OSError("standard output is closed")
        if stdout.write(line) != len(line):
            raise OSError("standard output took a part of the line")
        stdout.flush()
    except Exception as fault:  # noqa: BLE001
        _say(stderr, f"fault: {type(fault).__name__}")
        return EXIT_FAULT
    return status


if __name__ == "__main__":
    raise SystemExit(main())
