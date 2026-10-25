"""One call of an operation of ``sim.run`` or ``board.run``, and the form of its answer.

``ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md`` is the
rule for the form between the tool function and an operation of either run
tool; a decision cited by its number alone is one of that record.
``ARCHITECTURE/decisions/ADR-0108-od18-run-tools-timing-build-compiler-log.md``
adds the log keeper as a fifth thing (its decision 5) and the write of the
log (its decision 7). The module renders, ahead of the tool functions,
decisions 4, 6 and 7 and the part of ADR-0108 decisions 5 and 7 that lies
between the operation and the judging:

* :func:`ask`: calls an operation once with the four things of decision 2
  and the log keeper of ADR-0108 decision 5, closes the keeper when the
  operation came back, writes the log it was handed, if any, with
  :func:`hilclaw.build_log.write` (ADR-0108 decision 7), and tells the forms
  apart by the kind of value (decision 4): a pair of a report and its figure
  or none is (A), returned as :class:`Reported`; one of :data:`CONDITIONS`
  is (B), returned as that string. A returned value of neither form and a
  raised error are answered alike with :class:`OperationAnswerInvalid`
  (decisions 6 and 7). A raised request to end is not caught and nothing is
  written (decision 7; ADR-0108 decision 7). A write that fails is
  :class:`hilclaw.build_log.BuildLogUnwritable`, in place of whatever the
  operation returned or raised (ADR-0108 decision 7).
* :data:`KIND_OPERATION_ANSWER_INVALID`: the kind of decision 7, the run
  tools' own, not reserved, with the spelling and the meaning of the kind of
  ``correctness.check`` (:data:`hilclaw.check_operation.KIND_OPERATION_ANSWER_INVALID`).
* :data:`CONDITIONS`: the four strings of the form (B), in the order of
  decision 4. Decision 4 ties them to the first four values of
  :data:`hilclaw.run_result.CONDITIONS`; they are spelt here again, so that
  this module does not import that one, and the tests hold the two equal.
* The message says that the answer had neither form and which of the two
  ways it was, and carries nothing taken from the content of the answer
  (decision 7, by ADR-0045 decision 6).

Choices that are this module's own and no rule of a record:

* :class:`OperationAnswerInvalid` is a class of this module and not the one
  of :mod:`hilclaw.check_operation`, whose docstring speaks of the
  conditions of the check. It is no :class:`hilclaw.tools.ToolFailure`, for
  the reason that module gives: the step is to be ended, not left open.
* Which types count: a pair is exactly a ``tuple`` of length 2, so no
  subclass of ``tuple`` (a :class:`Reported` among them) is a pair; a report
  is exactly ``bytes``, of any content, empty included; a figure is exactly
  an ``int`` of at least 1, with no upper bound, so no ``bool`` and no
  subclass of ``int``, or ``None``; a condition is exactly a ``str`` equal to
  one of the four.
* Where a raised error ends and a raised request to end begins: at
  :class:`Exception`.
* The output path is the fourth positional argument of an operation and the
  fifth of :func:`ask`, after the timing parameters in both. It is handed on
  as the same object, not checked, read or converted, as are the request and
  the hw_profile. The keeper is the fifth positional argument of an
  operation and the sixth of :func:`ask`, exactly a
  :class:`hilclaw.build_log.LogKeeper`: the keeper of the check, since the
  properties ADR-0108 decision 5 asks for are those of ADR-0078 decision 6.
* :func:`ask` writes the log itself, as :func:`hilclaw.check_operation.ask`
  does, rather than leaving the write to the tool function: the write lies
  between the operation coming back and the telling apart of the forms, and
  so the rule that a failed write stands in place of every answer but a
  request to end is kept in one place, and no caller is handed an answer
  whose log was not written.
* What counts as raised by the operation: only what the one call of the
  operation raises. Everything else this module's code raises is an error of
  this side and passes through as it is (ADR-0065 Limits). No code of this
  module raises a :class:`hilclaw.tools.ToolFailure`, so one out of
  :func:`ask` is the operation's.
* A :class:`hilclaw.tools.ToolFailure` an operation raises is handed on as
  the same object, after its log was written. What the tool function then
  does with it is the rule of
  ``ARCHITECTURE/decisions/ADR-0068-od18-run-tools-operation-tool-failure.md``,
  rendered by :func:`hilclaw.run_failure.ended_with` and not here.
* How the message names a kind of value or error: with a word of this
  module's own for each type of a closed list of built-in types, matched by
  the exact type, and with one word for everything else. No name is read
  from the answer or from its type. Every message is a constant of this
  module, built at import.
* The exception is raised after the handler of the error has been left and
  after the names bound to the returned value have been unbound, so that it
  holds nothing of the answer: neither its ``__cause__`` nor its
  ``__context__`` is the error an operation raised, and the frame of
  :func:`ask` in its traceback holds neither that error nor the returned
  value.

What the module does not do: it is no tool and no step and is bound to none.
It appends no line and states no spend. It judges no report and makes no
result, and it neither uses nor drops the figure. It selects no backend,
draws no seed, validates no timing parameter and looks at nothing at the
output path. It makes no keeper and forms no path. It keeps nothing between
calls, reads no file, writes none but the log's and prints nothing. It
imports :mod:`hilclaw.build_log`, :mod:`hilclaw.run_parameters`,
:mod:`hilclaw.tools` and :mod:`typing` and nothing else.
"""

import typing

from hilclaw import build_log, run_parameters, tools

#: The kind of ADR-0065 decision 7: the run tools' own, not reserved.
KIND_OPERATION_ANSWER_INVALID = "operation_answer_invalid"

#: The four strings of the form (B), in the order of ADR-0065 decision 4.
CONDITIONS = ("build_time_limit", "build_exit_status", "time_limit", "exit_status")

_RETURNED = (
    "the operation returned {}, which is neither a report with its figure"
    " nor one of the four conditions"
)
_RAISED = "the operation raised {}, which is no tool failure"
_VALUES = tuple(
    (kind, _RETURNED.format(word))
    for kind, word in (
        (type(None), "nothing"),
        (bool, "a truth value"),
        (int, "an integer"),
        (float, "a floating number"),
        (str, "a string"),
        (bytes, "a lone byte string"),
        (bytearray, "a byte array"),
        (memoryview, "a memory view"),
        (list, "a list"),
        (tuple, "a tuple"),
        (dict, "a mapping"),
    )
)
_OTHER_VALUE = _RETURNED.format("a value of another type")
_ERRORS = tuple(
    (kind, _RAISED.format(word))
    for kind, word in (
        (TypeError, "a type error"),
        (ValueError, "a value error"),
        (KeyError, "a key error"),
        (IndexError, "an index error"),
        (AttributeError, "an attribute error"),
        (RuntimeError, "a runtime error"),
        (NotImplementedError, "a not-implemented error"),
        (OSError, "a system error"),
        (MemoryError, "a memory error"),
        (OverflowError, "an overflow error"),
        (ZeroDivisionError, "a division by zero"),
        (AssertionError, "an assertion error"),
    )
)
_OTHER_ERROR = _RAISED.format("an error of another class")


class Reported(typing.NamedTuple):
    """An answer of the form (A) of ADR-0065 decision 4.

    - ``report``: the report, exactly ``bytes``, as the operation returned it.
    - ``memory_bytes``: the figure, exactly an ``int`` of at least 1, or
      ``None`` when there is none.
    """

    report: bytes
    memory_bytes: int | None


class OperationAnswerInvalid(Exception):
    """The answer of the operation had neither form, so no result was made.

    In the words of ADR-0065 decision 7: the operation was called and its call
    is over; what it returned or raised had neither form of decision 4, and
    was no tool failure. It says nothing about the attempt or about why.

    - ``kind``: always :data:`KIND_OPERATION_ANSWER_INVALID`.
    - ``message``: exactly a ``str``, composed by this module. Nothing may
      depend on its wording.

    The instance holds no amount and nothing of the answer.
    :class:`hilclaw.tools.ToolFailure` can be built from ``kind`` and
    ``message``.

    Raises :class:`TypeError` when ``message`` is not exactly a ``str``.
    """

    kind = KIND_OPERATION_ANSWER_INVALID

    def __init__(self, message):
        if type(message) is not str:
            raise TypeError("the message of an invalid answer must be str")
        super().__init__(message)
        self.message = message


def _message(answer, known, other):
    kind = type(answer)
    for known_kind, message in known:
        if kind is known_kind:
            return message
    return other


def _unwritten(held, log_path):
    if held is None:
        return None
    try:
        build_log.write(log_path, held)
    except build_log.BuildLogUnwritable as unwritable:
        return unwritable.message
    return None


def ask(operation, request, hw_profile, parameters, output_path, keeper, *, log_path):
    """Call ``operation`` once, write the log it handed over, and return its answer of the form (A) or (B).

    - ``operation``: an operation of ``sim.run`` or ``board.run``, a callable.
    - ``request``, ``hw_profile``: the request and the hw_profile of the
      call, handed on as they are and not read.
    - ``parameters``: the timing parameters, exactly a
      :class:`hilclaw.run_parameters.TimingParameters`.
    - ``output_path``: the output path of the call, handed on as it is and
      not read, whatever its type is.
    - ``keeper``: the log keeper of the call (ADR-0108 decision 5), exactly a
      :class:`hilclaw.build_log.LogKeeper`. That it is new for the call is
      the caller's to keep: a log it holds already is written as handed.
    - ``log_path``: the file of the compiler's log of the call, keyword-only,
      as :func:`hilclaw.layout.build_log_file` forms it (ADR-0108
      decision 3). It is handed to :func:`hilclaw.build_log.write` as it is,
      and only when a log was handed over.

    No parameter has a default. Before the operation is called,
    :class:`TypeError` is raised when ``operation`` is not callable,
    ``parameters`` are not exactly a ``TimingParameters`` or ``keeper`` is
    not exactly a ``LogKeeper``.

    The operation is called as
    ``operation(request, hw_profile, parameters, output_path, keeper)``, with
    the five objects as they are and nothing else. When it came back, by
    returning or by raising anything, the keeper is closed, so a later
    hand-over is refused and never written. When it returned, or raised an
    :class:`Exception` (a :class:`hilclaw.tools.ToolFailure` included), and
    the keeper holds a log, the log is written to ``log_path`` by
    :func:`hilclaw.build_log.write` before anything else (ADR-0108
    decision 7). When that write raises
    :class:`hilclaw.build_log.BuildLogUnwritable`, a new
    ``BuildLogUnwritable`` with the same message is raised in place of
    whatever the operation returned or raised, and no form is told apart.
    When nothing was handed over, nothing is written. Then:

    1. It returned a pair of a report and its figure or ``None`` (the types
       are in the module docstring): a new :class:`Reported` of the two.
    2. It returned one of :data:`CONDITIONS`: that string.
    3. It returned anything else: :class:`OperationAnswerInvalid`.
    4. It raised an :class:`Exception` that is no
       :class:`hilclaw.tools.ToolFailure`: :class:`OperationAnswerInvalid`,
       whatever the class of the error is. A
       :class:`hilclaw.build_log.HandOverRefused` it let pass is one of them
       (ADR-0108 decision 5).
    5. It raised a ``ToolFailure``, of any kind: the same object is handed
       on (the module docstring says where it is answered).
    6. It raised a :class:`BaseException` that is no ``Exception``: it is not
       caught and nothing is written (ADR-0108 decision 7).

    The message of ``OperationAnswerInvalid`` says which of the cases 3 and 4
    it was and may name the kind of the value or of the error with a word of
    this module; it shows nothing of either and nothing of the output path or
    the seed. Neither the ``__cause__`` nor the ``__context__`` of the
    exception is the error of case 4, nor that of a ``BuildLogUnwritable``
    raised here the error of the write.

    What :func:`hilclaw.build_log.write` raises that is no
    ``BuildLogUnwritable``, for a ``log_path`` it cannot take, passes through
    unchanged. No argument is modified or kept but the keeper, which is
    closed; no file is read, and none is written but the log's.
    """
    if not callable(operation):
        raise TypeError("operation: must be callable")
    if type(parameters) is not run_parameters.TimingParameters:
        raise TypeError("parameters: must be TimingParameters")
    if type(keeper) is not build_log.LogKeeper:
        raise TypeError("keeper: must be exactly a hilclaw.build_log.LogKeeper")
    failure = message = None
    try:
        try:
            answer = operation(request, hw_profile, parameters, output_path, keeper)
        finally:
            keeper.close()
    except tools.ToolFailure as raised:
        failure = raised
    except Exception as error:  # noqa: BLE001
        message = _message(error, _ERRORS, _OTHER_ERROR)
    unwritten = _unwritten(keeper.held(), log_path)
    if unwritten is not None:
        answer = failure = None
        raise build_log.BuildLogUnwritable(unwritten)
    del unwritten
    if failure is not None:
        raise failure
    del failure
    if message is None:
        if type(answer) is tuple and len(answer) == 2:
            report, figure = answer
            if type(report) is bytes and (
                figure is None or (type(figure) is int and figure >= 1)
            ):
                return Reported(report, figure)
            del report, figure
        elif type(answer) is str and answer in CONDITIONS:
            return answer
        message = _message(answer, _VALUES, _OTHER_VALUE)
        del answer
    raise OperationAnswerInvalid(message)
