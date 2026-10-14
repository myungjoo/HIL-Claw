"""The draw of the seed of ``correctness.check``, and the step from a drawn seed to a result or an ending.

``ARCHITECTURE/decisions/ADR-0048-od18-correctness-check-seed-draw.md`` is
the rule for the draw; a decision cited by its number alone is one of that
record. The module renders, ahead of the tool function, the two parts of a
call that lie around the start line and need no log:

* :func:`draw`: the draw of decision 3. The source is asked once, and a
  seed it names is the seed of the call. A draw that yields no seed, because the
  source raised an error or because it returned what is no seed, is a tool
  failure of the kind :data:`KIND_SEED_NOT_DRAWN`, alike for both cases
  (decisions 4 and 5). No value stands in for a seed (decision 3). A raised
  request to end is not answered with the kind and passes through
  (decision 5).
* :data:`KIND_SEED_NOT_DRAWN`: the kind of decision 5, this tool's own and
  not reserved.
* The message says that the draw yielded no seed and which of the two cases
  it was, and carries nothing a source returned and nothing of what a source
  raised; the error of a source and its traceback are not handed on with the
  answer (decision 6).
* :func:`check`: from an admitted check, a drawn seed and an operation to
  the result or to what the step ends with. The check parameters are the
  five values of ADR-0043 decision 2: the seed of the call (ADR-0021
  decision 3), the number of draws (ADR-0046 decision 2) and the dimensions
  (ADR-0041 decision 2); the tolerance is that of ADR-0021 decision 4. The
  output path is handed on beside them, as the fourth thing of ADR-0056
  decision 3. The call of the operation and what becomes of its answer are
  those of :func:`hilclaw.check_ending.carry_out`.

Choices that are this module's own and no rule of a record:

* The names, and two functions with none that calls both. The draw lies
  before the start line (decision 3) and the operation is called after it
  (ADR-0040 decision 7, cited by decision 2), so the start line lies
  between the two. The order, which is
  :func:`hilclaw.check_admission.admit`, then :func:`draw`, then the start
  line, then :func:`check`, is the caller's to keep.
* How the two cases are told apart.
  :func:`hilclaw.harness.seed_source.draw` is handed a callable of this
  module that calls the source and remembers whether that call returned.
  The wording of the message of
  :class:`hilclaw.harness.seed_source.SeedSourceError` is not read.
* The two messages. Each is built when the module is imported and is at
  most 200 characters long. Decision 6 lets a message name the kind of the
  returned value or of the raised error; these name none, so no name that
  the code of a source chose is in them. Nothing may depend on the wording.
* Where a raised error ends and a raised request to end begins: where
  ``seed_source.draw`` has it, at :class:`Exception` (decision 5 leaves the
  line to the code).
* A ``source`` that is not callable is :class:`TypeError` and not the kind
  of this module: it is taken as a registry bound to something that is no
  source, not as a source that fails. ADR-0048 Limits leaves that line to
  the code.
* How the answer is kept free of what a source returned or raised, which
  is the rule of decision 6. The tool failure is raised after the handler
  has been left, and :func:`draw` binds neither the ``SeedSourceError`` nor
  what the source raised or returned, so neither its ``__cause__`` nor its
  ``__context__`` is one of them, and the frame of :func:`draw` in its
  traceback holds none of them.
* ``admitted`` is checked to be exactly a
  :class:`hilclaw.check_admission.Admitted`, before anything is called.
* The output path is the last parameter of :func:`check`. It is handed to
  ``carry_out`` as the same object and not checked, read or converted.

What the module does not do: it is no tool and no step and is bound to none.
It appends no line, so it does not by itself make the draw lie before a
start line. It binds no source and holds no default source; how a registry
or a test binds one is not decided here (ADR-0021 decision 3; decision 9).
It does not check that the call reached the draw, that is, that its
identity has no line and that none of the answers of moment 4 was given. It
says nothing of whether a seed is recorded, returned or kept after a check
(OD-16 sub-question 5); it writes the seed to no file and composes no
message that holds it. :func:`check` passes on, through ``carry_out``, the
message an operation raised with a backend kind as it was raised (ADR-0047
decision 4), so a seed in that message reaches the caller. By the records
such a message has no content that holds the seed (ADR-0047 decision 4,
citing ADR-0021 decision 3); nothing detects a message that breaks this.
:func:`check` validates no seed, no number of draws, no dimension, no
tolerance and no output path, and the module gives none a default. It
says nothing of what anybody does after an answer, of a repeated call or of
a retry. It is this tool's and gives no rule for another HW tool. It
reserves no kind. It keeps nothing between calls. It imports
:mod:`hilclaw.check_admission`, :mod:`hilclaw.check_ending`,
:mod:`hilclaw.check_parameters`, :mod:`hilclaw.harness.seed_source` and
:mod:`hilclaw.tools` and nothing else.
"""

from hilclaw import check_admission, check_ending, check_parameters, tools
from hilclaw.harness import seed_source

#: The kind of ADR-0048 decision 5: the draw yielded no seed. The tool's own, not reserved.
KIND_SEED_NOT_DRAWN = "seed_not_drawn"

_NO_SEED = "the draw of the seed of the call yielded no seed: "
_SOURCE_FAILED = _NO_SEED + "the source of seeds raised an error"
_NAMED_NO_SEED = _NO_SEED + "the source of seeds returned what is no seed"


def draw(source):
    """Ask ``source`` once and return the seed of the call, or raise the tool failure of a draw that yields no seed.

    - ``source``: a seed source, a callable without arguments
      (:mod:`hilclaw.harness.seed_source`). Which source that is is the
      caller's to say.

    The parameter has no default. :class:`TypeError` is raised, and nothing
    is asked, when ``source`` is not callable; this is the module's own
    choice (see the module docstring). The source is then asked exactly
    once, through :func:`hilclaw.harness.seed_source.draw`. Then:

    1. It returned a seed, exactly an ``int`` with 0 <= seed < 2**64: the
       same object is returned.
    2. It raised an :class:`Exception`, of any class, a
       :class:`hilclaw.tools.ToolFailure` included, or it cannot be called
       without arguments: :class:`hilclaw.tools.ToolFailure` of the kind
       :data:`KIND_SEED_NOT_DRAWN` (ADR-0048 decisions 4 and 5).
    3. It returned what is no seed: a ``ToolFailure`` of the same kind.
    4. It raised a :class:`BaseException` that is no ``Exception``: it is
       not caught (ADR-0048 decision 5).

    In the cases 2 and 3 the source is not asked again, no other source is
    asked and no value is returned. The message is exactly a ``str`` of at
    most 200 characters and says which of the two cases it was. It shows
    nothing of what the source returned or raised, and no name of a type.
    Neither the ``__cause__`` nor the ``__context__`` of the tool failure
    is the error of the source or the exception of ``seed_source.draw``.

    Nothing is written, printed or kept, and two calls are independent.
    """
    if not callable(source):
        raise TypeError("source: must be callable")
    returned = False

    def ask():
        nonlocal returned
        named = source()
        returned = True
        return named

    try:
        return seed_source.draw(ask)
    except seed_source.SeedSourceError:
        message = _NAMED_NO_SEED if returned else _SOURCE_FAILED
    raise tools.ToolFailure(KIND_SEED_NOT_DRAWN, message)


def check(operation, request, hw_profile, admitted, seed, output_path):
    """Call ``operation`` once for an admitted check and a drawn seed and return the result, or raise what its step ends with.

    - ``operation``: an operation of ``correctness.check``, a callable.
    - ``request``, ``hw_profile``: the request and the hw_profile of the
      call. They are handed on as they are and not read.
    - ``admitted``: what the check takes from the content of
      ``instance.json``, exactly a
      :class:`hilclaw.check_admission.Admitted`.
    - ``seed``: the seed of the call, as :func:`draw` returned it.
    - ``output_path``: the output path of the call (ADR-0056 decision 3). It
      is handed on as it is and not read, whatever its type is.

    No parameter has a default. :class:`TypeError` is raised before
    anything is called when ``admitted`` is of another type; this is the
    module's own choice. The check parameters are then
    ``CheckParameters(seed, admitted.draws, admitted.m, admitted.k,
    admitted.n)`` (ADR-0043 decision 2), each of the five the object that
    was handed in, and what
    :func:`hilclaw.check_ending.carry_out` returns for ``operation``,
    ``request``, ``hw_profile``, these parameters, ``output_path``,
    ``admitted.rtol`` and ``admitted.atol`` is returned as it is.
    ``carry_out`` is called once.

    Everything ``carry_out`` raises passes through as the same object:
    :class:`hilclaw.check_ending.EndedWithoutOutcome`, a
    :class:`hilclaw.tools.ToolFailure` that the call of the operation did
    not raise, the :class:`TypeError` for an operation that is not
    callable, what the judging raises for a value it refuses, and a
    :class:`BaseException` that is no ``Exception``.

    No value is validated, derived, bounded or replaced here, the seed
    included. A ``seed`` that is no seed is met only by what ``carry_out``
    calls, as that code stands: the operation is handed it; the judging of
    returned ``bytes`` raises
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`
    for it, while a returned condition gives its result and an answer of
    neither form its ending without the seed being looked at. None of that
    is a rule of this function. No source is asked.

    No argument is modified or kept, and no file is read or written.
    """
    if type(admitted) is not check_admission.Admitted:
        raise TypeError("admitted: must be exactly a hilclaw.check_admission.Admitted")
    parameters = check_parameters.CheckParameters(
        seed, admitted.draws, admitted.m, admitted.k, admitted.n
    )
    return check_ending.carry_out(
        operation,
        request,
        hw_profile,
        parameters,
        output_path,
        rtol=admitted.rtol,
        atol=admitted.atol,
    )
