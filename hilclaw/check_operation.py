"""One call of an operation of ``correctness.check``, and what becomes of its answer.

``ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md``
is the rule for an answer of neither form of ADR-0043 decision 4; a decision
cited by its number alone is one of that record. The module renders, ahead of
the tool function, the part of its decisions 3 to 6 that needs no log:

* :func:`ask`: calls an operation once with the four things of ADR-0056
  decision 3 and hands what it returned to
  :func:`hilclaw.check_answer.from_answer`. A returned value of neither form
  and a raised error are answered alike (decision 5), with
  :class:`OperationAnswerInvalid`. A raised request to end is not caught
  (decision 5).
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
path. It validates no check parameter and gives no default of any value. It
keeps nothing between calls. It says nothing of what anybody does after the
answer, and it does not render what a tool function does with a tool
failure an operation raises. It imports :mod:`hilclaw.check_answer`,
:mod:`hilclaw.check_parameters` and :mod:`hilclaw.tools` and nothing else.
"""

from hilclaw import check_answer, check_parameters, tools

#: The kind of ADR-0045 decision 4: the tool's own, not reserved.
KIND_OPERATION_ANSWER_INVALID = "operation_answer_invalid"

_RETURNED = (
    "the operation returned {}, which is neither a report nor one of the two conditions"
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
    the two conditions of ADR-0043 decision 4, and no tool failure. It says
    nothing about the attempt or about why the answer had neither form.

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


def ask(operation, request, hw_profile, parameters, output_path, *, rtol, atol):
    """Call ``operation`` once and return the result of the check, as a new ``dict``.

    - ``operation``: an operation of ``correctness.check``, a callable.
    - ``request``, ``hw_profile``: the request and the hw_profile of the
      call. They are handed on as they are and not read.
    - ``parameters``: the check parameters, exactly a
      :class:`hilclaw.check_parameters.CheckParameters`.
    - ``output_path``: the output path of the call (ADR-0056 decision 3). It
      is handed on as it is and not read, whatever its type is.
    - ``rtol``, ``atol``: the tolerance of the check, keyword-only.

    No parameter has a default. Before the operation is called,
    :class:`TypeError` is raised when ``operation`` is not callable or
    ``parameters`` are not exactly a ``CheckParameters``. The five values and
    the tolerance are not checked here: whoever calls checks them.

    The operation is called as
    ``operation(request, hw_profile, parameters, output_path)``, with the
    four objects as they are (ADR-0056 decision 3). Then:

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
       whatever the class of the error is.
    3. It raised a ``ToolFailure``, of any kind: the same object is handed
       on, which is this module's own choice. What the tool function then
       does with it is in the module docstring (ADR-0047).
    4. It raised a :class:`BaseException` that is no ``Exception``: it is not
       caught (ADR-0045 decision 5).

    Only the call of the operation and the call of ``from_answer`` are inside
    a ``try``. The message of ``OperationAnswerInvalid`` says which of the
    cases 1 and 2 it was and may name the kind of the value or of the error
    with a word of this module; it shows nothing of either and nothing of
    the output path, and composing it calls no code of the answer. Neither
    the ``__cause__`` nor the ``__context__`` of the exception is the error
    of case 2.

    No argument is modified or kept, and no file is read or written.
    """
    if not callable(operation):
        raise TypeError("operation: must be callable")
    if type(parameters) is not check_parameters.CheckParameters:
        raise TypeError("parameters: must be CheckParameters")
    try:
        answer = operation(request, hw_profile, parameters, output_path)
    except tools.ToolFailure:
        raise
    except Exception as error:  # noqa: BLE001
        message = _message(error, _ERRORS, _OTHER_ERROR)
    else:
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
