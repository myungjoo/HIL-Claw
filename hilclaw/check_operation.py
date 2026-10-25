"""One call of an operation of ``correctness.check``, and what becomes of its answer.

``ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md``
is the rule for an answer of neither form of ADR-0043 decision 4; a decision
cited by its number alone is one of that record.
``ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md``
is the rule of the compiler's log. The module renders, ahead of the tool
function, the part of decisions 3 to 6 that needs no log, and the part of
ADR-0078 decisions 6 and 7 that lies between the operation and the judging:

* :func:`ask`: calls an operation once with the four things of ADR-0056
  decision 3 and the log keeper of ADR-0078 decision 6, closes the keeper
  when the operation came back, writes the log it was handed, if any, with
  :func:`hilclaw.build_log.write` (ADR-0078 decision 7), and then hands what
  the operation returned to :func:`hilclaw.check_answer.from_answer`. A
  returned value of neither form and a raised error are answered alike
  (decision 5), with :class:`OperationAnswerInvalid`. A raised request to
  end is not caught and nothing is written (decision 5; ADR-0078
  decision 7). A write that fails is
  :class:`hilclaw.build_log.BuildLogUnwritable`, in place of whatever the
  operation returned or raised (ADR-0078 decision 7).
* :data:`KIND_OPERATION_ANSWER_INVALID`: the kind of decision 4.
* The message says that the answer had neither form and which of the two ways
  it was, and carries nothing taken from the content of the answer
  (decision 6).

Choices that are this module's own and no rule of a record:

* :class:`OperationAnswerInvalid` is a class of this module. It is no
  :class:`hilclaw.tools.ToolFailure`: such a failure out of a step leaves the
  step open (:mod:`hilclaw.journaled_step`), and decision 3 has the step
  ended. It is no :class:`hilclaw.journaled_step.StepFailed` either: that
  class takes the amounts of the step, and this module states no spend.
* Where a raised error ends and a raised request to end begins: at
  :class:`Exception`. A :class:`BaseException` that is no ``Exception`` is a
  request to end (decision 1 observes this of Python and leaves the line to
  the code).
* The output path is the fourth positional argument of an operation and
  the fifth of :func:`ask`, after the check parameters in both. It is
  treated as the request and the hw_profile are: handed on as the same
  object, not checked, read or converted. The tool function alone forms it.
* The keeper is the fifth positional argument of an operation and the
  sixth of :func:`ask`, after the output path in both; ADR-0078 decision 6
  leaves its form to the code. :func:`ask` is handed the keeper and the
  path of the log file, keyword-only, and makes and forms neither, so the
  caller's step makes one keeper per call. The keeper is closed in a
  ``finally`` around the one call of the operation, before what it holds is
  read, whatever the operation did.
* The write lies outside the ``try`` of the operation's call, so a
  :class:`hilclaw.build_log.BuildLogUnwritable` the operation raises is an
  error of the operation, and one out of :func:`ask` is always the write's.
  The exception :func:`ask` raises for a failed write is a new one, made
  from the message of the write's, after the names of the answer and of a
  raised tool failure have been unbound, so that it holds nothing of the
  answer or the log.
* What counts as raised by the operation: only what the one call of the
  operation raises. What counts as a returned value of neither form: a value
  whose type is neither exactly ``bytes`` nor exactly ``str``, and a
  :class:`hilclaw.check_answer.NeitherFormError` out of the one call of
  ``from_answer``. Everything else this module's code or the code it calls
  raises is an error of this side and passes through as it is (ADR-0045
  Limits).
* A returned value whose type is neither exactly ``bytes`` nor exactly
  ``str`` is not handed to ``from_answer``. It has neither form by the first
  choice of :mod:`hilclaw.check_answer`, and the message that function
  composes for it reads the name of its type, which a metaclass can make
  code of the answer.
* A :class:`hilclaw.tools.ToolFailure` an operation raises is handed on as
  the same object. That is no rule of a record. What the tool function then
  does with it is the rule of
  ``ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md``:
  the step is ended with a ``failure`` (its decision 3), which holds the
  raised kind and message for a backend kind and otherwise the tool's own
  kind ``operation_failure_invalid`` (its decisions 4 and 5). The code gives
  that kind and message with :func:`hilclaw.check_failure.ended_with`,
  joined with :func:`ask` in :func:`hilclaw.check_ending.carry_out`.
* How the message names a kind of value: with a word of this module's own
  for each type of a closed list of built-in types, matched by the exact
  type, and with one word for everything else. No name is read from the
  answer or from its type, so no string that the code of a backend chose
  reaches the message. Every message is a constant of this module.
* The exception is raised after the handler of the error has been left and
  after the name of the returned value has been unbound, so that it holds
  nothing of the answer: neither its ``__cause__`` nor its ``__context__``
  is the error an operation raised, and the frame of :func:`ask` in its
  traceback holds neither that error nor the returned value.

What the module does not do: it is no tool and no step and is bound to none.
It appends no line and states no spend. It selects no backend, draws no seed,
reads no tolerance and no file of a run, and looks at nothing at the output
path. It writes no file but the log's, and forms no path. It validates no check parameter and gives no default of any value. It
keeps nothing between calls. It says nothing of what anybody does after the
answer, and it does not render what a tool function does with a tool
failure an operation raises. It imports :mod:`hilclaw.build_log`, :mod:`hilclaw.check_answer`,
:mod:`hilclaw.check_parameters` and :mod:`hilclaw.tools` and nothing else.
"""

from hilclaw import build_log, check_answer, check_parameters, tools

#: The kind of ADR-0045 decision 4: the tool's own, not reserved.
KIND_OPERATION_ANSWER_INVALID = "operation_answer_invalid"

_RETURNED = (
    "the operation returned {}, which is neither a report"
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


class OperationAnswerInvalid(Exception):
    """The answer of the operation had neither form, so no result was made.

    In the words of ADR-0045 decision 4: the operation was called and its
    call is over; what it returned or raised was neither a report nor one of
    the conditions of ADR-0043 decision 4 (four since ADR-0060 decision 4),
    and no tool failure. It says nothing about the attempt or about why the
    answer had neither form.

    - ``kind``: always :data:`KIND_OPERATION_ANSWER_INVALID`.
    - ``message``: exactly a ``str``, composed by this module. Nothing may
      depend on its wording.

    The instance holds no amount: the code that ends the step states the
    spend. It holds neither the answer nor anything of it.
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


def ask(
    operation,
    request,
    hw_profile,
    parameters,
    output_path,
    keeper,
    *,
    log_path,
    rtol,
    atol,
):
    """Call ``operation`` once, write the log it handed over, and return the result of the check, as a new ``dict``.

    - ``operation``: an operation of ``correctness.check``, a callable.
    - ``request``, ``hw_profile``: the request and the hw_profile of the
      call. They are handed on as they are and not read.
    - ``parameters``: the check parameters, exactly a
      :class:`hilclaw.check_parameters.CheckParameters`.
    - ``output_path``: the output path of the call (ADR-0056 decision 3). It
      is handed on as it is and not read, whatever its type is.
    - ``keeper``: the log keeper of the call (ADR-0078 decision 6), exactly a
      new :class:`hilclaw.build_log.LogKeeper`.
    - ``log_path``: the file of the compiler's log of the call, keyword-only,
      as :func:`hilclaw.layout.build_log_file` forms it (ADR-0078
      decision 3). It is handed to :func:`hilclaw.build_log.write` as it is,
      and only when a log was handed over.
    - ``rtol``, ``atol``: the tolerance of the check, keyword-only.

    No parameter has a default. Before the operation is called,
    :class:`TypeError` is raised when ``operation`` is not callable,
    ``parameters`` are not exactly a ``CheckParameters`` or ``keeper`` is not
    exactly a ``LogKeeper``. The five values, the log path and the tolerance
    are not checked here: whoever calls checks them.

    The operation is called as
    ``operation(request, hw_profile, parameters, output_path, keeper)``, with
    the five objects as they are (ADR-0056 decision 3; ADR-0078 decision 6).
    When it came back, by returning or by raising anything, the keeper is
    closed, so a later hand-over is refused and never written. When it
    returned, or raised an :class:`Exception` (a
    :class:`hilclaw.tools.ToolFailure` included), and the keeper holds a log,
    the log is written to ``log_path`` by :func:`hilclaw.build_log.write`
    before anything else (ADR-0078 decision 7). When that write raises
    :class:`hilclaw.build_log.BuildLogUnwritable`, a new
    ``BuildLogUnwritable`` with the same message is raised in place of
    whatever the operation returned or raised, and nothing is judged. When
    nothing was handed over, nothing is written. Then:

    1. It returned exactly ``bytes`` or exactly a ``str``: the result is
       that of :func:`hilclaw.check_answer.from_answer` for the returned
       value, the five values of ``parameters``, ``rtol`` and ``atol``,
       returned as it is. A ``str`` of neither form raises
       :class:`OperationAnswerInvalid`. Everything else that function
       raises, for a value of the five or of the tolerance it refuses,
       passes through unchanged. It returned anything else:
       :class:`OperationAnswerInvalid`, and ``from_answer`` is not called.
    2. It raised an :class:`Exception` that is no
       :class:`hilclaw.tools.ToolFailure`: :class:`OperationAnswerInvalid`,
       whatever the class of the error is. A
       :class:`hilclaw.build_log.HandOverRefused` it let pass is one of them
       (ADR-0078 decision 6).
    3. It raised a ``ToolFailure``, of any kind: the same object is handed
       on, which is this module's own choice. What the tool function then
       does with it is in the module docstring (ADR-0047).
    4. It raised a :class:`BaseException` that is no ``Exception``: it is not
       caught (ADR-0045 decision 5) and nothing is written (ADR-0078
       decision 7).

    Only the call of the operation, the write and the call of
    ``from_answer`` are inside a ``try``. The message of
    ``OperationAnswerInvalid`` says which of the cases 1 and 2 it was and may
    name the kind of the value or of the error with a word of this module;
    it shows nothing of either and nothing of the output path, and composing
    it calls no code of the answer. Neither the ``__cause__`` nor the
    ``__context__`` of the exception is the error of case 2, nor that of a
    ``BuildLogUnwritable`` raised here the error of the write.

    What :func:`hilclaw.build_log.write` raises that is no
    ``BuildLogUnwritable``, for a ``log_path`` it cannot take, passes through
    unchanged. No argument is modified or kept but the keeper, which is
    closed; no file is read, and none is written but the log's.
    """
    if not callable(operation):
        raise TypeError("operation: must be callable")
    if type(parameters) is not check_parameters.CheckParameters:
        raise TypeError("parameters: must be CheckParameters")
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
    unwritable = _unwritten(keeper.held(), log_path)
    if unwritable is not None:
        answer = failure = None
        raise build_log.BuildLogUnwritable(unwritable)
    del unwritable
    if failure is not None:
        raise failure
    del failure
    if message is None:
        message = _message(answer, _VALUES, _OTHER_VALUE)
        if type(answer) is bytes or type(answer) is str:
            seed, draws, m, k, n = parameters
            try:
                return check_answer.from_answer(
                    answer, m=m, k=k, n=n, draws=draws, seed=seed, rtol=rtol, atol=atol
                )
            except check_answer.NeitherFormError:
                pass
        del answer
    raise OperationAnswerInvalid(message)
