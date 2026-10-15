"""The draw of the timing seed of ``sim.run`` and ``board.run``.

``ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md`` is the
rule for the draw; a decision cited by its number alone is one of that
record. The module renders, ahead of the tool functions:

* :func:`draw`: the draw of decisions 2 and 3. The source is asked once, and
  a seed it names is the timing seed of the call. A draw that yields no seed,
  because the source raised an error or because it returned what is no seed,
  is a tool failure of the kind :data:`KIND_SEED_NOT_DRAWN`, alike for both
  cases (decision 4). No value stands in for a seed (decision 3). A raised
  request to end is not answered with the kind and passes through
  (decision 4).
* :data:`KIND_SEED_NOT_DRAWN`: the kind of decision 4, the run tools' own,
  not reserved, with the spelling and the meaning of the kind of
  ``correctness.check`` (:data:`hilclaw.check_seed.KIND_SEED_NOT_DRAWN`).
* The message says that the draw of the timing seed yielded no seed and
  which of the two cases it was, and carries nothing a source returned and
  nothing of what a source raised; the error of a source and its traceback
  are not handed on with the answer (decision 4, after ADR-0048 decision 6).

Choices that are this module's own and no rule of a record:

* The names, and the draw going through
  :func:`hilclaw.harness.seed_source.draw` directly rather than through
  :func:`hilclaw.check_seed.draw` (decision 2 leaves it to the code).
* How the two cases are told apart: ``seed_source.draw`` is handed a
  callable of this module that calls the source and remembers whether that
  call returned. The wording of the message of
  :class:`hilclaw.harness.seed_source.SeedSourceError` is not read.
* The two messages. Each is built when the module is imported and is at
  most 200 characters long. They name no type, so no name that the code of
  a source chose is in them. Nothing may depend on the wording.
* Where a raised error ends and a raised request to end begins: where
  ``seed_source.draw`` has it, at :class:`Exception`.
* A ``source`` that is not callable is :class:`TypeError` and not the kind:
  it is taken as a source bound to something that is no source, not as a
  source that fails.
* The tool failure is raised after the handler has been left, and
  :func:`draw` binds neither the ``SeedSourceError`` nor what the source
  raised or returned, so neither its ``__cause__`` nor its ``__context__``
  is one of them.

What the module does not do: it is no tool and no step and is bound to
none. The order is the caller's to keep: the draw comes after the last
answer of moment 4 and before the start line of moment 5 (decision 3); the
module appends no line and does not check that the call reached the draw,
that is, that its identity has no line and that none of the answers of
moment 4 was given. It binds no source and holds no default source. It
keeps nothing between calls, writes no file, prints nothing and composes no
message that holds the seed (decision 5). It reserves no kind. It imports
:mod:`hilclaw.harness.seed_source` and :mod:`hilclaw.tools` and nothing
else.
"""

from hilclaw import tools
from hilclaw.harness import seed_source

#: The kind of ADR-0064 decision 4: the draw of the timing seed yielded no seed. The run tools' own, not reserved.
KIND_SEED_NOT_DRAWN = "seed_not_drawn"

_NO_SEED = "the draw of the timing seed of the call yielded no seed: "
_SOURCE_FAILED = _NO_SEED + "the source of seeds raised an error"
_NAMED_NO_SEED = _NO_SEED + "the source of seeds returned what is no seed"


def draw(source):
    """Ask ``source`` once and return the timing seed of the call, or raise the tool failure of a draw that yields no seed.

    - ``source``: a seed source, a callable without arguments
      (:mod:`hilclaw.harness.seed_source`). Which source that is is the
      caller's to say.

    The parameter has no default. :class:`TypeError` is raised, and nothing
    is asked, when ``source`` is not callable; this is the module's own
    choice. The source is then asked exactly once, through
    :func:`hilclaw.harness.seed_source.draw`. Then:

    1. It returned a seed, exactly an ``int`` with 0 <= seed < 2**64: the
       same object is returned.
    2. It raised an :class:`Exception`, of any class, a
       :class:`hilclaw.tools.ToolFailure` included, or it cannot be called
       without arguments: :class:`hilclaw.tools.ToolFailure` of the kind
       :data:`KIND_SEED_NOT_DRAWN` (ADR-0064 decision 4).
    3. It returned what is no seed: a ``ToolFailure`` of the same kind.
    4. It raised a :class:`BaseException` that is no ``Exception``: it is
       not caught.

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
