"""The compiler's log of a build of ``correctness.check``: its keeper and its once-only write (ADR-0078).

``ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md``
keeps the log of every build whose compiler ended in a text file of the
attempt (decisions 2 and 3), handed over by the operation to a fifth thing it
is called with, the log keeper, and written by the tool function after the
operation came back (decisions 6 and 7). This module is the part of that
record that wires nothing:

* :class:`LogKeeper`: the keeper of decision 6. An operation hands the log
  over with :meth:`LogKeeper.hand_over`; the tool function closes the keeper
  with :meth:`LogKeeper.close` when the operation came back and reads what
  it holds with :meth:`LogKeeper.held`.
* :class:`HandOverRefused`: what the keeper raises in the operation for a
  hand-over it refuses (decision 6).
* :data:`KIND_BUILD_LOG_UNWRITABLE` and :class:`BuildLogUnwritable`: the
  tool's own kind of decision 7 and the error that carries it.
* :func:`write`: the write of decision 7, the steps of ADR-0029 decisions 4
  to 6 by :func:`hilclaw.once_write.write_once`, of the bytes of decision 4.

Choices that are this module's own and no rule of a record:

* The keeper counts accepted hand-overs only: a refused hand-over changes
  nothing, so an operation may hand the log over after a refusal, and a
  second hand-over after an accepted one is refused.
* A hand-over after :meth:`LogKeeper.close` is refused with
  :class:`HandOverRefused` and changes nothing; closing twice is no error.
* Nothing handed over is :data:`None`; an empty ``str`` is a log, held as
  the empty text (decision 2).
* :class:`HandOverRefused` is an :class:`Exception` and no
  :class:`hilclaw.tools.ToolFailure`, so an operation that lets it pass is
  answered ``operation_answer_invalid`` (ADR-0045 decision 4), as decision 6
  relies on. :class:`BuildLogUnwritable` is no ``ToolFailure`` either, in the
  manner of :class:`hilclaw.check_operation.OperationAnswerInvalid`.
* :func:`write` creates the missing directories of the parent of its path,
  and nothing beside them; with a path of :func:`hilclaw.layout.build_log_file`
  that is the chain of the measure attempt directory. It tells a taken name
  and a refused write apart in its message, and says nothing more.
* Every message is a constant of this module. Each error is raised after the
  handler of the error it replaces has been left, so neither its
  ``__cause__`` nor its ``__context__`` holds that error.

What the module does not do: it wires nothing into ``correctness.check`` and
is called by no tool yet. It forms no path, reads no file, appends no end
line, states no spend, judges no answer and composes no message that holds a
path, the text of an error or a byte of a log. It bounds no size of a log
(open under ADR-0078 decision 4) and commits nothing (OD-17). It imports
:mod:`hilclaw.once_write` and the standard library and nothing else.
"""

import threading
from pathlib import Path

from hilclaw import once_write

#: The kind of ADR-0078 decision 7: the tool's own, not reserved.
KIND_BUILD_LOG_UNWRITABLE = "build_log_unwritable"

_SECOND = "the log was already handed over"
_CLOSED = "the keeper is closed: the operation came back"
_NOT_TEXT = "the log must be exactly a str"
_NOT_UTF8 = "the log cannot be encoded as UTF-8"
_TAKEN = "the file of the compiler's log exists already; nothing was written"
_REFUSED = "the file system refused the file of the compiler's log"


class HandOverRefused(Exception):
    """The keeper refused a hand-over; it holds what it held before (ADR-0078 decision 6).

    ``message`` is exactly a ``str``, a constant of this module that shows
    nothing of the handed value. It is no :class:`hilclaw.tools.ToolFailure`.
    """

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class BuildLogUnwritable(Exception):
    """The log handed over could not be written to its file (ADR-0078 decision 7).

    - ``kind``: always :data:`KIND_BUILD_LOG_UNWRITABLE`.
    - ``message``: exactly a ``str``, composed by this module. It shows no
      path, no text of an error and no byte of the log; nothing may depend on
      its wording.

    The instance holds no amount: the code that ends the step states the
    spend. It is no :class:`hilclaw.tools.ToolFailure`, which can be built
    from ``kind`` and ``message``.

    Raises :class:`TypeError` when ``message`` is not exactly a ``str``.
    """

    kind = KIND_BUILD_LOG_UNWRITABLE

    def __init__(self, message):
        if type(message) is not str:
            raise TypeError("the message of an unwritable log must be str")
        super().__init__(message)
        self.message = message


class LogKeeper:
    """The thing an operation hands the log of its build to, made for one call (ADR-0078 decision 6).

    The keeper holds at most one log and writes, reads and keeps nothing
    else. Its methods may be called from several threads.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._log = None
        self._closed = False

    def __repr__(self):
        return f"<LogKeeper handed={self._log is not None} closed={self._closed}>"

    def hand_over(self, log):
        """Keep ``log``, the text the compiler wrote; return ``None``.

        Raises :class:`HandOverRefused`, and keeps nothing, when ``log`` is not
        exactly a ``str``, when it cannot be encoded as UTF-8 (a lone
        surrogate), when a log was handed over already, or when the keeper is
        closed.
        """
        refusal = None
        if type(log) is not str:
            refusal = _NOT_TEXT
        else:
            try:
                log.encode("utf-8")
            except UnicodeEncodeError:
                refusal = _NOT_UTF8
        if refusal is None:
            with self._lock:
                if self._closed:
                    refusal = _CLOSED
                elif self._log is not None:
                    refusal = _SECOND
                else:
                    self._log = log
        if refusal is not None:
            raise HandOverRefused(refusal)

    def close(self):
        """Refuse every later hand-over; return ``None``. Closing again does nothing."""
        with self._lock:
            self._closed = True

    def held(self):
        """Return the log handed over, or ``None`` when nothing was."""
        with self._lock:
            return self._log


def write(path, log):
    """Give the file ``path`` the bytes of ``log`` if its name is free; return ``None``.

    ``path`` is the final name, as :func:`hilclaw.layout.build_log_file` forms
    it; ``log`` is the text held by a :class:`LogKeeper`. The bytes written
    are exactly ``log.encode("utf-8")``: no byte order mark, no added newline,
    no line-end conversion; an empty ``log`` gives an empty file. The missing
    directories of ``path.parent`` are created first; then
    :func:`hilclaw.once_write.write_once` writes the file.

    Raises :class:`TypeError` when ``log`` is not exactly a ``str`` and
    :class:`ValueError` when it cannot be encoded as UTF-8, before the file
    system is touched. Raises :class:`BuildLogUnwritable` when the name is
    taken, whose entry is then left as it was found, or when an
    :class:`OSError` arises in creating a directory or in the write; nothing
    is retried, and a directory created is left.
    """
    if type(log) is not str:
        raise TypeError("log: must be exactly a str")
    content = _encoded(log)
    if content is None:
        raise ValueError("log: " + _NOT_UTF8)
    path = Path(path)
    message = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if once_write.write_once(path, content) is not None:
            message = _TAKEN
    except OSError:
        message = _REFUSED
    if message is not None:
        raise BuildLogUnwritable(message)


def _encoded(log):
    try:
        return log.encode("utf-8")
    except UnicodeEncodeError:
        return None
