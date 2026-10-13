"""The tool function of a journaled HW tool over a backend table (ADR-0016 decisions 2 to 4).

:func:`tool_function` builds the tool function of a HW tool
(:data:`hilclaw.backends.HW_TOOLS`) one call of which is one journaled step.
It is the tool function of :mod:`hilclaw.journaled_tool` with one moment more:
the selection of the backend, between the lookup and the start line. Whether a
HW tool is journaled is its contract's; a HW tool that is not journaled has no
builder here. :func:`tool_function` is for a contract with one ``step``
value; :func:`stepped_tool_function`, for one with several, is described
after the order of a call.

A call, in the order of ADR-0016 decision 2, with the read of the layout
version stamp that ADR-0030 decision 3 places between 2 and 3:

1. The request is checked as :mod:`hilclaw.journaled_tool` checks it, by the
   same code (:func:`hilclaw.journaled_tool.checked_function`): ``run_id``,
   ``execution`` and the numbers the contract requires, then the tool's own
   check. A refusal is ``invalid_request``.
2. The data root is asked, once; ``no_data_root`` passes through. Then the
   layout version stamp of the run is read from
   ``runs/<run_id>/instance.json``, by the same code as in
   :mod:`hilclaw.journaled_tool`, before ``STATE.json`` or the log is opened.
   When the stamp cannot be had, the call is a tool failure of one of the
   four kinds below and nothing of 3 to 7 takes place.
3. The lookup. An ended identity is answered with what its end line holds and
   an open one with ``step_open``. For neither is the hw_profile read, a
   backend selected or anything called: the answer depends on the data plane
   only, ``instance.json`` for the stamp included, and the table is asked
   nothing, so the answer of a run whose stamp can be had stays obtainable
   when the table has changed since.
4. For an identity with no line the reader is asked for the hw_profile of the
   run, once, and :func:`hilclaw.backends.select` returns the operation of the
   tool of the backend under its ``accelerator``.
5. The start line is appended.
6. The step of the tool's contract is called with that hw_profile and that
   operation; calling the operation is its part.
7. The end line is appended and the result returned.

5 to 7 are :func:`hilclaw.journaled_step.run_prepared`, and 4 is what it calls
before the start line.

:func:`stepped_tool_function` builds the tool function of a contract that
:func:`tool_function` cannot carry: one with several ``step`` values, the
``step`` of a call following from its request, and with a place between the
selection and the start line (ADR-0040 decisions 3 and 7; ADR-0021 decision 4
needs both). A call of it is the call above, by the same code, but for this:

- In 1 the ``step`` is obtained from the request, after the tool's own check
  (:func:`hilclaw.journaled_tool.stepped_function`), and the lookup of 3 is
  under the identity with that ``step``.
- In 4 the one reader returns whatever the contract takes from
  ``instance.json`` in one read, and a callable of the contract gives the
  hw_profile record in it. After the selection has succeeded, another
  callable of the contract is called with the request and what the reader
  returned. What it raises is the answer of the call and passes through
  unchanged; what it returns is handed to the step. It is not called when
  the selection failed, so a kind it raises follows ``no_backend`` and
  ``not_offered``.
- In 6 the step is handed that object too.

What is said below of a call that fails in 4 holds for both builders, the
two callables of the contract included, and so does what is said of the
reader, by whichever name a builder takes it.

A call that fails in 4 has not started the step: no line was appended, neither
the step nor an operation was called, nothing was consumed at any target, and
the same request can be repeated. ``no_backend`` and ``not_offered`` pass
through as the selection raises them. A call answered at the read of the
stamp has not started the step either, and it has not carried out the lookup,
asked the reader or selected a backend: its kind is answered for every
identity and says nothing about it, so an ended or an open identity of such a
run is not answered from the log (ADR-0030 decision 4).

What the read of the stamp and the call of the reader raise for
``runs/<run_id>/instance.json`` is answered, each where it is raised, with a
``ToolFailure`` of one of the four kinds of ADR-0019 decision 2, by the rows
its decision 3 has for that file and the borders of its decision 4 (ADR-0030
decision 4: those rows are answered at the read of the stamp and in 4),
chained to the error it answers for:

- ``run_file_missing``: :class:`hilclaw.instance.MissingInstanceError`, and a
  :class:`FileNotFoundError` or :class:`NotADirectoryError` (a data root that
  is no existing directory at the read, a file gone during the read).
- ``run_file_invalid``: :class:`hilclaw.instance.InvalidInstanceError` (an
  invalid content, an empty file included, or a path that is no regular file).
- ``run_file_unsupported``: :class:`hilclaw.instance.UnsupportedVersionError`.
- ``run_file_unreadable``: every other :class:`OSError`.

Everything else the two raise passes through unchanged, and so does what
the selection raises for a record that is no valid hw_profile record
(:class:`hilclaw.keys.InvalidRecordError`): no kind is given here, and an
:class:`Exception` among them that is no ``ToolFailure`` is ``tool_crashed``
at :func:`hilclaw.tools.call` (ADR-0019 decision 4). A ``ToolFailure`` the
reader raises itself keeps the kind it has, and a :class:`BaseException` that
is no ``Exception`` is not answered at all. The reader is asked for an
identity with no line only; the stamp is read at each call that has a data
root, whatever the identity. The read of the stamp and the call of the reader
are two (ADR-0030 decision 4): the read of the stamp serves nothing in 4, so
a run whose stamp was had and for which the reader then raises one of the
classes above is answered in 4, the identity having no line.

Conventions of this module, which the records do not fix:

- The reader of the hw_profile of a run is a parameter. A run states its
  hw_profile in ``runs/<run_id>/instance.json`` (ADR-0018 decision 3), which
  :func:`hilclaw.instance.hw_profile_of` reads; this module reads no file for
  it and binds no reader of it. The reader of the stamp is no parameter:
  :func:`hilclaw.journaled_tool.checked_function` binds
  :func:`hilclaw.instance.layout_version_of`.
- The step of the contract calls the operation, not this module: what an
  operation returns and how that becomes the amounts and the result of the
  step are each tool's contract. Nothing here checks that the step calls it,
  how often or with what.
- What the reader returns is not looked at here; the selection validates the
  hw_profile record, which is that object or, in
  :func:`stepped_tool_function`, what the contract's callable gives for it.
- The file is read once in 4 and not again by this module, so what the
  contract takes besides the hw_profile is of the same content of the file.
  Nothing here says what that is, and no seed is drawn here: both the place
  after the selection and the step can hold what a contract does there.
- The classes above count for whatever reader was handed over, since this
  module cannot tell why a reader raised one of them; the three of
  :mod:`hilclaw.instance` are named here for that and no file is read for it.
- Only the read of the stamp and the call of the reader are answered this
  way: the same classes out of the tool's own check, out of the selection,
  out of the two callables of the contract in 4, out of the step, out of an
  operation or out of an append are not. Out of
  an append :mod:`hilclaw.journaled_step` answers an :class:`OSError` with
  ``start_line_failed`` or ``end_line_failed`` (ADR-0026 decision 3) and the
  three of :mod:`hilclaw.instance` pass through.
- The reader is not asked a second time in one call: "not there" is
  ``run_file_missing`` at whatever read it is found (ADR-0019 decision 4).
- The message of such a failure starts with ``runs/<run_id>/instance.json``
  (ADR-0019 decision 6): for the three classes it is the message of the
  reader as it is, which :func:`hilclaw.instance.hw_profile_of` and
  :func:`hilclaw.instance.layout_version_of` start that way, and for an
  :class:`OSError` it is composed by :mod:`hilclaw.run_files`.
  The message of another reader that raises one of the three is used
  unchanged and not checked. Nothing may depend on the rest of the wording.
- Nothing is kept between calls (ADR-0010 decision 7): the stamp is read at
  each call that has a data root and the reader is asked at each call that
  reaches 4.

Limits it does not remove (ADR-0016 decision 6, with those of
:mod:`hilclaw.journaled_tool`): no access control, so a caller can name another
run; the target a backend reaches is not checked against the other key fields
of the record; a backend that does not answer the contract of the tool is not
detected; two calls at once; and two processes hold two tables.

It defines no tool, no backend, no table, no reader, no script and no default,
registers nothing and reads no configuration and no variable of the process.
It compares the stamp with nothing (ADR-0030 decision 5).
"""

from hilclaw import backends, instance, journaled_step, journaled_tool, run_files, tools

_KINDS = {
    instance.MissingInstanceError: tools.KIND_RUN_FILE_MISSING,
    instance.InvalidInstanceError: tools.KIND_RUN_FILE_INVALID,
    instance.UnsupportedVersionError: tools.KIND_RUN_FILE_UNSUPPORTED,
}


def tool_function(*, tool, step, numbers, source, table, hw_profile_of, check, perform):
    """Return the tool function of the journaled HW tool that these eight state.

    - ``tool``: the name of the HW tool, one of
      :data:`hilclaw.backends.HW_TOOLS`.
    - ``step``, ``numbers``, ``source``, ``check``: as in
      :func:`hilclaw.journaled_tool.tool_function`.
    - ``table``: the :class:`hilclaw.backends.BackendTable` the tool is bound
      to (ADR-0016 decision 2).
    - ``hw_profile_of``: the reader of the hw_profile of a run, called as
      ``hw_profile_of(data_root, run_id)`` with the data root of this call, a
      :class:`pathlib.Path`, and the checked ``run_id``. It returns the
      hw_profile record of that run.
    - ``perform``: the step, called as ``perform(data_root, request,
      hw_profile, operation)`` with the request as the caller gave it, the
      object the reader returned and the operation
      :func:`hilclaw.backends.select` returned for it, only for an identity
      with no line and only after the start line. An operation is called
      with the request and the hw_profile of the call (ADR-0016 decision 2);
      what else it is handed is the tool's contract. The step returns
      ``(spend, result)`` or raises :class:`hilclaw.journaled_step.StepFailed`.

    Raises, in this order: :class:`TypeError` when ``tool`` is no ``str`` and
    :class:`ValueError` when it is no HW tool; :class:`TypeError` when
    ``table`` is no ``BackendTable``; then what
    :func:`hilclaw.journaled_tool.tool_function` raises for ``step`` and
    ``numbers``, and :class:`TypeError` when ``source``, ``check``,
    ``hw_profile_of`` or ``perform`` is not callable. Building calls none of
    the four, reads no file and asks the table nothing.

    The function returned takes one request and returns the ``result`` of the
    step, a ``dict``. It raises ``ToolFailure`` of kind ``invalid_request``
    with a message that names the member, or says that the request is no
    object; of one of the four kinds ``run_file_missing``,
    ``run_file_unreadable``, ``run_file_invalid`` and
    ``run_file_unsupported`` when the layout version stamp of the run cannot
    be had, for every identity, and for what ``hw_profile_of`` raises that the
    module docstring counts as a situation of ``instance.json``, for an
    identity with no line (ADR-0019 decisions 2 to 4, ADR-0030 decision 4),
    in both cases having appended no line and called neither the step nor an
    operation; and otherwise what ``check``,
    :func:`hilclaw.data_root_source.obtain`, the read of the stamp,
    ``hw_profile_of``,
    :func:`hilclaw.backends.select` and
    :func:`hilclaw.journaled_step.run_prepared` raise. It does not modify the
    request or the record.
    """
    _check_bound(tool, table)
    return journaled_tool.checked_function(
        step=step,
        numbers=numbers,
        carry_out=_carry_out(
            tool,
            table,
            hw_profile_of,
            lambda value: value,
            lambda request, value: None,
            lambda data_root, request, hw_profile, operation, admitted: perform(
                data_root, request, hw_profile, operation
            ),
        ),
        source=source,
        check=check,
        hw_profile_of=hw_profile_of,
        perform=perform,
    )


def stepped_tool_function(
    *,
    tool,
    steps,
    step_of,
    numbers,
    source,
    table,
    read,
    hw_profile_in,
    check,
    admit,
    perform,
):
    """Return the tool function of the journaled HW tool that these eleven state.

    The ``step`` of a call follows from its request. It is for a contract with several ``step`` values and with something to
    take from ``instance.json`` besides the hw_profile, or something to
    answer before the step starts (ADR-0040 decisions 3 and 7, ADR-0021
    decision 4). The module docstring has the order of a call.

    - ``tool``, ``numbers``, ``source``, ``table``, ``check``: as in
      :func:`tool_function`.
    - ``steps``, ``step_of``: as in
      :func:`hilclaw.journaled_tool.stepped_function`: the ``step`` names of
      the contract and the callable that gives the ``step`` of a checked
      request, called as ``step_of(request)``.
    - ``read``: the one reader of 4, called as ``read(data_root, run_id)``
      with the data root of this call, a :class:`pathlib.Path`, and the
      checked ``run_id``, once and only for an identity with no line. What
      it returns is the contract's and is not looked at here.
    - ``hw_profile_in``: called as ``hw_profile_in(value)`` with what
      ``read`` returned, once, right after it. It returns the hw_profile
      record of the run, which the selection validates.
    - ``admit``: the place between the selection and the start line, called
      as ``admit(request, value)`` with the request as the caller gave it
      and what ``read`` returned, once and only after
      :func:`hilclaw.backends.select` returned. It raises to answer the call
      before the step starts, a ``ToolFailure`` of a kind of the tool for
      instance, or returns what the step is handed.
    - ``perform``: the step, called as ``perform(data_root, request,
      hw_profile, operation, admitted)`` with the request as the caller gave
      it, the object ``hw_profile_in`` returned, the operation the selection
      returned for it and the object ``admit`` returned, only after the start
      line. It returns ``(spend, result)`` or raises
      :class:`hilclaw.journaled_step.StepFailed`; calling the operation is
      its part.

    Raises, in this order: what :func:`tool_function` raises for ``tool`` and
    ``table``; what :func:`hilclaw.journaled_tool.stepped_function` raises
    for ``steps`` and ``numbers``; and :class:`TypeError` for the first of
    ``step_of``, ``source``, ``check``, ``read``, ``hw_profile_in``,
    ``admit`` and ``perform`` that is not callable. Building calls none of
    the seven, reads no file and asks the table nothing.

    The function returned takes one request and returns the ``result`` of the
    step, a ``dict``. It raises what the function of :func:`tool_function`
    raises, with ``read`` in the place of ``hw_profile_of``, and besides:
    what ``step_of`` raises and the :class:`RuntimeError` for a ``step`` that
    is none of ``steps``, both before the data root is asked; and what
    ``hw_profile_in`` and ``admit`` raise, unchanged, whatever it is, with no
    line appended and neither the step nor an operation called, so that the
    same request can be repeated. It does not modify the request or what
    ``read`` returned, and keeps nothing between calls.
    """
    _check_bound(tool, table)
    return journaled_tool.stepped_function(
        steps=steps,
        step_of=step_of,
        numbers=numbers,
        carry_out=_carry_out(tool, table, read, hw_profile_in, admit, perform),
        source=source,
        check=check,
        read=read,
        hw_profile_in=hw_profile_in,
        admit=admit,
        perform=perform,
    )


def _check_bound(tool, table):
    backends.check_hw_tool(tool)
    if not isinstance(table, backends.BackendTable):
        raise TypeError(f"table must be a BackendTable, got {type(table).__name__}")


def _carry_out(tool, table, read, hw_profile_in, admit, perform):
    def carry_out(data_root, run_id, identity, request):
        prepared = []

        def prepare():
            with run_files.reading(data_root, run_id, "instance.json", _KINDS):
                value = read(data_root, run_id)
            hw_profile = hw_profile_in(value)
            operation = backends.select(table, hw_profile, tool)
            prepared.extend((hw_profile, operation, admit(request, value)))

        return journaled_step.run_prepared(
            data_root,
            run_id,
            identity,
            lambda: perform(data_root, request, *prepared),
            before_start=prepare,
        )

    return carry_out
