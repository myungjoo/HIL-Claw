"""The tool function of a journaled HW tool over a backend table (ADR-0016 decisions 2 to 4).

:func:`tool_function` builds the tool function of a HW tool
(:data:`hilclaw.backends.HW_TOOLS`) one call of which is one journaled step.
It is the tool function of :mod:`hilclaw.journaled_tool` with one moment more:
the selection of the backend, between the lookup and the start line. Whether a
HW tool is journaled is its contract's; a HW tool that is not journaled has no
builder here.

A call, in the order of ADR-0016 decision 2:

1. The request is checked as :mod:`hilclaw.journaled_tool` checks it, by the
   same code: ``run_id``, ``execution`` and the numbers the contract requires,
   then the tool's own check. A refusal is ``invalid_request``.
2. The data root is asked, once; ``no_data_root`` passes through.
3. The lookup. An ended identity is answered with what its end line holds and
   an open one with ``step_open``. For neither is the hw_profile read, a
   backend selected or anything called: the answer depends on the data plane
   only and stays obtainable when the table has changed since.
4. For an identity with no line the reader is asked for the hw_profile of the
   run, once, and :func:`hilclaw.backends.select` returns the operation of the
   tool of the backend under its ``accelerator``.
5. The start line is appended.
6. The step of the tool's contract is called with that hw_profile and that
   operation; calling the operation is its part.
7. The end line is appended and the result returned.

5 to 7 are :func:`hilclaw.journaled_step.run_prepared`, and 4 is what it calls
before the start line.

A call that fails in 4 has not started the step: no line was appended, neither
the step nor an operation was called, nothing was consumed at any target, and
the same request can be repeated. ``no_backend`` and ``not_offered`` pass
through as the selection raises them. A hw_profile that cannot be read or is no
valid record is neither of the two: what the reader raises, and what the
selection raises for the record, pass through unchanged with no kind given here
(OD-18 sub-question 4, open).

Conventions of this module, which the records do not fix:

- The reader of the hw_profile of a run is a parameter. Where a run states its
  hw_profile is open (OD-18 sub-question 6), so this module reads no file for
  it and names none.
- The step of the contract calls the operation, not this module: what an
  operation returns and how that becomes the amounts and the result of the
  step are each tool's contract.
- What the reader returns is not looked at here; the selection validates it.
- Nothing is kept between calls (ADR-0010 decision 7): the reader is asked at
  each call that reaches 4.

Limits it does not remove (ADR-0016 decision 6, with those of
:mod:`hilclaw.journaled_tool`): no access control, so a caller can name another
run; the target a backend reaches is not checked against the other key fields
of the record; a backend or a step that does not answer the contract of the
tool is not detected; two calls at once; and two processes hold two tables.

It defines no tool, no backend, no table, no reader, no script and no default,
registers nothing and reads no configuration and no variable of the process.
"""

from hilclaw import backends, journaled_step, journaled_tool


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
      with no line and only after the start line. It returns ``(spend,
      result)`` or raises :class:`hilclaw.journaled_step.StepFailed`.

    Raises, in this order: :class:`TypeError` when ``tool`` is no ``str`` and
    :class:`ValueError` when it is no HW tool; :class:`TypeError` when
    ``table`` is no ``BackendTable``; then what
    :func:`hilclaw.journaled_tool.tool_function` raises for ``step`` and
    ``numbers``, and :class:`TypeError` when ``source``, ``check``,
    ``hw_profile_of`` or ``perform`` is not callable. Building calls none of
    the four, reads no file and asks the table nothing.

    The function returned takes one request and returns the ``result`` of the
    step, a ``dict``. It raises ``ToolFailure`` of kind ``invalid_request``
    with a message that names the member, and otherwise what ``check``,
    :func:`hilclaw.data_root_source.obtain`, ``hw_profile_of``,
    :func:`hilclaw.backends.select` and
    :func:`hilclaw.journaled_step.run_prepared` raise. It does not modify the
    request or the record.
    """
    backends._hw_tool(tool)
    if not isinstance(table, backends.BackendTable):
        raise TypeError(f"table must be a BackendTable, got {type(table).__name__}")

    def carry_out(data_root, run_id, identity, request):
        selected = []

        def select():
            hw_profile = hw_profile_of(data_root, run_id)
            selected.append(hw_profile)
            selected.append(backends.select(table, hw_profile, tool))

        return journaled_step.run_prepared(
            data_root,
            run_id,
            identity,
            lambda: perform(data_root, request, *selected),
            before_start=select,
        )

    return journaled_tool._built(
        step,
        numbers,
        carry_out,
        source=source,
        check=check,
        hw_profile_of=hw_profile_of,
        perform=perform,
    )
