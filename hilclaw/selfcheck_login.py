"""Step one of the runtime self-check: the login (ADR-0054 decision 3).

:func:`read` starts ``claude auth status`` once, without a further option, as
a child process under a time limit and reads the answer. This is runtime code:
on a runtime machine it starts the real ``claude``. It is built and tested
against a stub ``claude`` that the tests write, never against a real one (D16).

A call ends in one of four ways, told by ``outcome`` of the
:class:`LoginStatus` it returns:

- **logged in** (``outcome is None``): exit status 0 and an output that is one
  JSON object whose ``authMethod`` is a string other than ``none``;
- :data:`NOT_LOGGED_IN`: exit status 1, whatever the output is.
  :data:`LOGIN_INSTRUCTION` is the fixed text for it;
- :data:`LOGIN_UNREADABLE`: everything else that ran - exit status 0 with any
  other output, any other exit status (a signal included), the time limit;
- :data:`NO_CLAUDE`: no ``claude`` program could be started.

``outcome is None`` is the only way to tell "logged in", and no default and no
exception yields it. No member of the output other than ``authMethod`` is
read, ``loggedIn`` included.

Of the status output only the value of ``authMethod`` leaves the module, and
only when it is one of :data:`AUTH_METHODS`; any other string is carried as
:data:`AUTH_METHOD_OTHER`. Nothing else of the child's standard output and
nothing of its standard error is in the returned value or in an exception, and
the module prints nothing and passes no stream on.

Not done here: no session, no report, no exit status of the check, no
``claude auth login``, no retry. The module writes no file, reads no
configuration and no environment variable of its own, and the child gets the
environment of the calling process unchanged.

Conventions of this module (the record leaves them to the code):

- The time limit has no default: its value belongs to the code that composes
  the check. A bad ``timeout_s`` is refused as :func:`hilclaw.local_run.run`
  refuses it, before anything is started.
- The record names no working directory for this call, so none is chosen:
  ``cwd`` is passed through and ``None`` inherits. A ``cwd`` that is not a
  directory when the call begins is the caller's error
  (:class:`FileNotFoundError`) and nothing is started.
- "One JSON object" is the whole standard output decoded as strict UTF-8 and
  parsed as strict JSON, white space around the object allowed. A byte order
  mark, invalid UTF-8, a second value, ``NaN`` or ``Infinity`` anywhere, and
  nesting too deep to parse are not one JSON object. Integers are not
  converted, so their length does not matter. An object that holds the key
  ``authMethod`` more than once has no single answer and is read as having
  none.
- ``auth_method`` is carried, under the rule above, whenever the output is one
  JSON object with a string ``authMethod``, whatever the outcome (after the
  time limit: the output captured until then); otherwise it is ``None``.
  Nothing is concluded from it except what "logged in" says.
- :data:`NO_CLAUDE` covers the lookup that finds nothing and every
  :class:`OSError` of the call: a file the system cannot execute, and also a
  start that failed for a reason other than the program, such as a ``cwd``
  that cannot be entered or that vanished after the check above.

Known limits. Whoever controls the ``PATH`` or the environment decides what is
seen (ADR-0054 L6). Any ``authMethod`` other than ``none``, an API key
included, reads as logged in (L7). An exit status 1 with another cause reads
as nothing logged in. From :mod:`hilclaw.local_run`: on a timeout only the
started process is killed, so a surviving child of it can make the call
outlast the limit; the output is held in memory without a size limit; on
Windows the lookup also searches the current directory.
"""

import json
import os
from typing import NamedTuple

from hilclaw import local_run

NO_CLAUDE = "no_claude"
NOT_LOGGED_IN = "not_logged_in"
LOGIN_UNREADABLE = "login_unreadable"
AUTH_METHOD_NONE = "none"
AUTH_METHOD_OTHER = "other"
AUTH_METHODS = (
    AUTH_METHOD_NONE,
    "claude.ai",
    "oauth_token",
    "api_key",
    "api_key_helper",
    "third_party",
)
LOGIN_INSTRUCTION = "Nothing is logged in. Run `claude auth login`."
_COMMAND = ("claude", "auth", "status")


class LoginStatus(NamedTuple):
    """What one :func:`read` call found.

    ``outcome`` is ``None`` when the command line is logged in, else one of
    :data:`NO_CLAUDE`, :data:`NOT_LOGGED_IN` and :data:`LOGIN_UNREADABLE`.
    ``auth_method`` is one of :data:`AUTH_METHODS`, :data:`AUTH_METHOD_OTHER`
    or ``None`` when the output gave no string ``authMethod``. ``returncode``
    is the exit status of the child, negative when a signal ended it on POSIX,
    and ``None`` when the outcome is :data:`NO_CLAUDE` or the time limit ended
    the call; ``timed_out`` tells the last two apart.
    """

    outcome: str | None
    auth_method: str | None
    returncode: int | None
    timed_out: bool


def read(*, timeout_s, cwd=None):
    """Run ``claude auth status`` once and return a :class:`LoginStatus`.

    ``timeout_s`` is the limit in seconds and ``cwd`` the working directory of
    the child (``None`` inherits). Every way the call can end is a result.
    Raised before anything is started: :class:`TypeError` and
    :class:`ValueError` for a ``timeout_s`` that is not a positive finite
    number, :class:`TypeError` for a ``cwd`` that is not a path and
    :class:`FileNotFoundError` for one that is not a directory. Passed on from
    :func:`hilclaw.local_run.run`: :class:`OverflowError` for a ``timeout_s``
    longer than the platform can wait for, after the child was started and
    killed.
    """
    if cwd is not None and not os.path.isdir(os.fspath(cwd)):
        raise FileNotFoundError("cwd is not a directory")
    try:
        done = local_run.run(_COMMAND, timeout_s=timeout_s, cwd=cwd)
    except (local_run.ProgramNotFoundError, OSError):
        return LoginStatus(NO_CLAUDE, None, None, False)
    method = _auth_method(done.stdout)
    outcome = LOGIN_UNREADABLE
    if done.returncode == 1:
        outcome = NOT_LOGGED_IN
    elif done.returncode == 0 and method not in (None, AUTH_METHOD_NONE):
        outcome = None
    if method is not None and method not in AUTH_METHODS:
        method = AUTH_METHOD_OTHER
    return LoginStatus(outcome, method, done.returncode, done.timed_out)


class _Object(list):
    pass


def _not_json(constant):
    raise ValueError(constant)


def _unread(_digits):
    return 0


def _auth_method(output):
    try:
        value = json.loads(
            output.decode("utf-8"),
            object_pairs_hook=_Object,
            parse_constant=_not_json,
            parse_int=_unread,
        )
    except (ValueError, RecursionError):
        return None
    if not isinstance(value, _Object):
        return None
    found = [member for key, member in value if key == "authMethod"]
    if len(found) != 1 or not isinstance(found[0], str):
        return None
    return found[0]
