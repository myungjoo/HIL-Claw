"""One call of an operation of ``correctness.check``: the result, or what its step ends with.

``ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md``
and ``ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md``
are the rules, with
``ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md``
for the compiler's log. The module puts :func:`hilclaw.check_operation.ask`
and :func:`hilclaw.check_failure.ended_with` together, ahead of the tool
function, and so renders the part of the rows of the table of ADR-0047
decision 8 that needs no log, and the ending of ADR-0078 decision 7:

* The operation returned a report or one of the four conditions:
  :func:`carry_out` returns the result (ADR-0040 decision 7; ADR-0042
  decision 3; ADR-0043 decision 4).
* It returned a value of neither form, or raised an error that is no tool
  failure: :class:`EndedWithoutOutcome` with the kind and the message of
  ADR-0045 decisions 3 to 5, as ``ask`` gives them.
* It raised a tool failure: :class:`EndedWithoutOutcome` with the kind and
  the message of ADR-0047 decisions 3 and 4, as ``ended_with`` gives them.
  Under the contract as it stands that is the tool's own kind of decision 4
  for every raised kind but a backend kind (decision 5). For a backend kind,
  today one of the eight of ADR-0056 decision 6 and ADR-0060 decision 4, it
  is the kind and the message that were raised, where the message can be
  read as exactly a ``str``.
* It raised a request to end that is no tool failure: what was raised is not
  caught (ADR-0045 decision 5).
* It handed over a log that ``ask`` could not write, whatever it returned
  or raised but a request to end: :class:`EndedWithoutOutcome` with the
  kind :data:`hilclaw.build_log.KIND_BUILD_LOG_UNWRITABLE` and the message
  of the write, in place of every row above (ADR-0078 decision 7).

Choices that are this module's own and no rule of a record:

* One exception for both causes. Whoever ends the step needs the kind and
  the message and tells the causes apart by the kind.
  :class:`EndedWithoutOutcome` is no :class:`hilclaw.tools.ToolFailure`: such
  a failure out of a step leaves the step open
  (:mod:`hilclaw.journaled_step`), and ADR-0045 decision 3 and ADR-0047
  decision 3 have the step ended. It is no
  :class:`hilclaw.journaled_step.StepFailed` either: that class takes the
  amounts of the step, and this module states no spend.
* Where the line between a tool failure the operation raised and one raised
  by the code of this side is drawn. Both records hand that line to the code
  (ADR-0047 Limits; ADR-0045 Limits), and an error on it can fall on either
  side. Here only a tool failure that the one call of the operation raised
  is the operation's. A tool failure raised anywhere else under ``ask``, by
  its own code or by the judging it calls, is an error of this side and
  passes through as the same object; out of a step it leaves the step open
  by the convention of :mod:`hilclaw.journaled_step`. A tool failure the
  operation raised is answered as one whatever else its class is, so it is
  looked for first. Any other
  :class:`hilclaw.check_operation.OperationAnswerInvalid` out of ``ask`` is
  taken as the one ``ask`` raised: the operation is not its source, and
  which code of this side raised it is not told. So is any
  :class:`hilclaw.build_log.BuildLogUnwritable` out of ``ask``: one the
  operation raises is answered by ``ask`` as an error of the operation.
* How the operation's own tool failure is told. ``ask`` is handed a callable
  of this module that calls the operation with the five objects it is
  handed, the four of ADR-0056 decision 3 and the keeper of ADR-0078
  decision 6, as they are, remembers the tool failure that call raised and
  raises it again as the same object. A tool failure out of ``ask`` is the
  operation's exactly when it is that remembered object.
* Nothing of what was raised is kept. The exception is raised after the
  handler has been left and after the remembered tool failure has been
  unbound: neither its ``__cause__`` nor its ``__context__`` is what the
  operation raised or the exception of ``ask``, and the frame of
  :func:`carry_out` in its traceback holds neither. ADR-0047 decision 4
  leaves undecided whether anything keeps the raised tool failure outside
  the log; this module keeps nothing.
* ``operation`` is checked to be callable here, since ``ask`` is handed the
  callable of this module and no longer sees the object.
* The output path is the fifth positional argument of :func:`carry_out`,
  as it is of ``ask``, and the fourth of an operation. It is handed on as
  the same object and not checked, read or converted, and this module puts
  it in no ``EndedWithoutOutcome``. The keeper is the sixth positional
  argument and the path of the log file the keyword ``log_path``, both
  handed to ``ask`` as the same objects; this module makes no keeper,
  forms no path and writes nothing itself. The message of a backend kind is that of
  the operation, as raised, whatever it shows.

What the module does not do: it is no tool and no step and is bound to none.
It appends no line and states no spend. It selects no backend, draws no seed,
reads no tolerance and no file of a run, and looks at nothing at the output
path. It names no kind and no backend kind, and composes no message: both
come from the two modules it joins. It is this tool's and gives no rule for
another tool. It keeps nothing between calls. It says nothing of what
anybody does after the answer. It imports :mod:`hilclaw.build_log`, :mod:`hilclaw.check_failure`,
:mod:`hilclaw.check_operation` and :mod:`hilclaw.tools` and nothing else.
"""

from hilclaw import build_log, check_failure, check_operation, tools


class EndedWithoutOutcome(Exception):
    """The check made no result: the kind and the message its step ends with.

    The two strings are what the ``failure`` of the end line holds: after an
    answer of neither form those of ADR-0045 decision 3, after a raised tool
    failure those of ADR-0047 decisions 3 and 4, and after a log that could
    not be written those of ADR-0078 decision 7.

    - ``kind``: exactly a ``str``.
    - ``message``: exactly a ``str``. Nothing may depend on its wording.

    The instance holds no amount: the code that ends the step states the
    spend. It holds neither the answer, nor a raised error, nor the raised
    tool failure, nor anything of them beyond the two strings.
    :class:`hilclaw.tools.ToolFailure` can be built from ``kind`` and
    ``message`` of every instance :func:`carry_out` raises.

    Raises :class:`TypeError` when ``kind`` or ``message`` is not exactly a
    ``str``.
    """

    def __init__(self, kind, message):
        if type(kind) is not str or type(message) is not str:
            raise TypeError("the kind and the message of an ending must be str")
        super().__init__(kind, message)
        self.kind = kind
        self.message = message


def carry_out(
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
    """Call ``operation`` once and return the result of the check, or raise what its step ends with.

    - ``operation``: an operation of ``correctness.check``, a callable.
    - ``request``, ``hw_profile``: the request and the hw_profile of the
      call. They are handed on as they are and not read.
    - ``parameters``: the check parameters, exactly a
      :class:`hilclaw.check_parameters.CheckParameters`.
    - ``output_path``: the output path of the call (ADR-0056 decision 3). It
      is handed on as it is and not read, whatever its type is.
    - ``keeper``: the log keeper of the call (ADR-0078 decision 6), handed to
      ``ask`` as it is.
    - ``log_path``: the file of the compiler's log of the call, keyword-only,
      handed to ``ask`` as it is.
    - ``rtol``, ``atol``: the tolerance of the check, keyword-only.

    No parameter has a default. :class:`TypeError` is raised before anything
    is called when ``operation`` is not callable. The operation is then
    called once, through :func:`hilclaw.check_operation.ask`, as
    ``operation(request, hw_profile, parameters, output_path, keeper)``, and
    ``ask`` writes the log it handed over before it judges (ADR-0078
    decision 7). Then:

    1. ``ask`` returned a result: the same ``dict`` object is returned.
    2. The call of the operation raised a
       :class:`hilclaw.tools.ToolFailure`, of any kind and of any subclass,
       one that is an ``OperationAnswerInvalid`` as well included:
       :class:`EndedWithoutOutcome` with the pair
       :func:`hilclaw.check_failure.ended_with` returns for it (ADR-0047
       decisions 3 and 4).
    3. A ``ToolFailure`` came out of ``ask`` that the call of the operation
       did not raise: it is not caught, and the same object passes through.
       This line is the module's own choice (see the module docstring).
    4. ``ask`` raised a
       :class:`hilclaw.check_operation.OperationAnswerInvalid` that is no
       ``ToolFailure``, for a returned value of neither form or a raised
       error: :class:`EndedWithoutOutcome` with the ``kind`` and the
       ``message`` of that exception, unchanged (ADR-0045 decisions 3 to 5).
    5. ``ask`` raised a :class:`hilclaw.build_log.BuildLogUnwritable`, for a
       log it could not write: :class:`EndedWithoutOutcome` with the kind
       ``build_log_unwritable`` and the ``message`` of that exception,
       unchanged, whatever the operation returned or raised (ADR-0078
       decision 7).
    6. Everything else passes through unchanged: the :class:`TypeError` of
       ``ask`` for ``parameters`` or a ``keeper`` of another type, raised
       before the operation is called; what the judging raises for a value
       of the five or of the tolerance it refuses; a :class:`BaseException`
       that is no ``Exception`` out of the operation (ADR-0045 decision 5),
       with nothing written, or out of a read inside ``ended_with``.

    Neither the ``__cause__`` nor the ``__context__`` of an
    ``EndedWithoutOutcome`` raised here is what the operation raised or the
    exception of ``ask``.

    No argument is modified or kept but the keeper, which ``ask`` closes; no
    file is read, and none is written but the log's, by ``ask``.
    """
    if not callable(operation):
        raise TypeError("operation: must be callable")
    own = None

    def call(request, hw_profile, parameters, output_path, keeper):
        nonlocal own
        try:
            return operation(request, hw_profile, parameters, output_path, keeper)
        except tools.ToolFailure as raised:
            own = raised
            raise

    try:
        return check_operation.ask(
            call,
            request,
            hw_profile,
            parameters,
            output_path,
            keeper,
            log_path=log_path,
            rtol=rtol,
            atol=atol,
        )
    except tools.ToolFailure as raised:
        if raised is not own:
            raise
        kind, message = check_failure.ended_with(raised)
    except check_operation.OperationAnswerInvalid as invalid:
        kind, message = invalid.kind, invalid.message
    except build_log.BuildLogUnwritable as unwritable:
        kind, message = unwritable.kind, unwritable.message
    own = None
    raise EndedWithoutOutcome(kind, message)
