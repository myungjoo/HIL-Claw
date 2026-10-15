"""The request side of the identity of a call of ``correctness.check``: the point and the ``step``.

``ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md`` is
the rule; a decision cited by its number alone is one of that record. The
module renders, ahead of the tool function, what its decisions 3, 4 and 5 and
decisions 2 and 3 of
``ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md``
fix of a request:

* :data:`MEMBER`, :data:`SIM`, :data:`BOARD`: "The member is named ``point``,
  and its two values are the strings ``"sim"``, for the sim point, and
  ``"board"``, for the board point" (decision 4).
* :data:`STEP_SIM`, :data:`STEP_BOARD`, :data:`STEPS`: "The values are
  ``correctness_check_sim`` for the check at the sim point and
  ``correctness_check_board`` for the check at the board point" (decision 3).
* :data:`NUMBERS`: "All three numbers are required" (decision 5).
* :data:`MEMBERS`: "A request of this tool has exactly the six members
  ``run_id``, ``round``, ``candidate``, ``attempt``, ``execution`` and
  ``point`` [...] and no other" (ADR-0069 decision 2).
* :func:`check`: "A request without it, or with another value, is a refused
  request" and "The value is compared as it is, and nothing is normalised"
  (decision 4); "A request with a member no record names is a refused
  request", for every value it carries, ``null`` included (ADR-0069
  decision 3).
* :func:`step_of`: "the tool function takes the ``step`` of a call from the
  checked value of the member of decision 4" (decision 3).

Choices that are this module's own and no rule of a record:

* :data:`STEPS` is a ``tuple`` in the order sim, board. The order means
  nothing. :data:`MEMBERS` is a ``tuple`` in the order of ADR-0040
  decision 5; its order means nothing either.
* A ``request`` whose type is not exactly ``dict`` is refused with the same
  kind. In a tool function the check of the frame refuses it first; the
  choice keeps the two functions total.
* A value of ``point`` whose type is not exactly ``str``, an instance of a
  subclass of ``str`` included, is "another value". It is refused without
  calling any code of the value: it is not compared, hashed or printed.
* A key whose type is not exactly ``str``, an instance of a subclass of
  ``str`` included, is a member no record names. Every key is looked at
  before ``point`` is looked up, so the lookup meets keys of type ``str``
  only, and no code of a key is called.
* Of the faults of one request, the first named here is the one refused:
  a request that is no ``dict``; then the first member no record names, in
  the order of the request; then ``point``. A request with ``Point`` and
  without ``point`` is refused for ``Point``.
* The message of a refusal of ``point`` is one of four texts built when the
  module is imported, at most 100 characters long. It starts with the name
  of the member, and where a value was given it names the two values of
  decision 4. It shows nothing of the value that was given, not even its
  type. Nothing may depend on its wording beyond the name of the member at
  its start.
* The message of a refusal of a member no record names starts with the name
  the request gave it when that name is 1 to 32 characters of ``A-Z``,
  ``a-z``, ``0-9``, ``_``, ``.`` and ``-``, and with the fixed text
  ``(a name not shown)`` otherwise, so that it shows no control character
  and no long name. It goes on to name the six members of :data:`MEMBERS`,
  is at most 160 characters long and shows nothing of the value of the
  member, not even its type.

What the module does not do: it is no tool and no step and is bound to none.
It builds no identity and checks none of ``run_id``, ``execution`` and the
numbers: the frame does. The input schema and the description of the tool
(ADR-0069 decisions 4 and 5) are :mod:`hilclaw.check_definition`'s. It reads
no file and no log. It does not say at which point an attempt is checked, in
which order, or who may raise ``execution``. Whether an operation is handed
the point is another record's (ADR-0043). It is this tool's and gives no rule
for the ``step`` values of another tool (decision 3). It keeps nothing between
calls. It imports :mod:`re` and :mod:`hilclaw.tools` and nothing else.
"""

import re

from hilclaw import tools

#: The name of the request member that states the execution point (ADR-0040 decision 4).
MEMBER = "point"
#: The value of :data:`MEMBER` for the sim point (ADR-0040 decision 4).
SIM = "sim"
#: The value of :data:`MEMBER` for the board point (ADR-0040 decision 4).
BOARD = "board"

#: The ``step`` of a check at the sim point (ADR-0040 decision 3).
STEP_SIM = "correctness_check_sim"
#: The ``step`` of a check at the board point (ADR-0040 decision 3).
STEP_BOARD = "correctness_check_board"
#: The ``step`` values of this tool, each once.
STEPS = (STEP_SIM, STEP_BOARD)

#: The numbers a request of this tool requires (ADR-0040 decision 5), as a builder of :mod:`hilclaw.journaled_tool` takes them.
NUMBERS = ("round", "candidate", "attempt")
#: The members of a request of this tool, each once; no other is taken (ADR-0069 decision 2).
MEMBERS = ("run_id", *NUMBERS, "execution", MEMBER)

_STEP_OF = {SIM: STEP_SIM, BOARD: STEP_BOARD}
_ACCEPTED = f'{MEMBER}: must be "{SIM}" or "{BOARD}", '
_NO_OBJECT = f"{MEMBER}: cannot be read, the request is no object"
_MISSING = f"{MEMBER}: is required"
_NO_STRING = _ACCEPTED + "got a value that is not exactly a string"
_OTHER = _ACCEPTED + "got another string"
_SHOWN = re.compile(r"[A-Za-z0-9_.-]{1,32}")
_NOT_SHOWN = "(a name not shown)"
_UNNAMED = (
    ": is no member of a request of this tool, which takes "
    f"{', '.join(MEMBERS[:-1])} and {MEMBERS[-1]} only"
)


def check(request):
    """Check the member list and the member ``point`` of ``request``; return ``None`` or refuse.

    - ``request``: the request of a call of ``correctness.check``.

    The parameter has no default. This is the convention of the ``check`` of
    :func:`hilclaw.journaled_tool.tool_function`. It is one part of the tool's
    own check and not the whole of it: the five members of the frame are
    checked by the builder before this function is called.

    Raises :class:`hilclaw.tools.ToolFailure` of kind
    :data:`hilclaw.tools.KIND_INVALID_REQUEST`, with a message that starts
    with the name of the member (see the module docstring), when

    1. the request has a key that is not exactly one of :data:`MEMBERS`,
       compared as it is, case-sensitive, whatever its value, ``None``
       included (ADR-0069 decision 3);
    2. the request has no member ``point`` (ADR-0040 decision 4);
    3. its value is not exactly :data:`SIM` or :data:`BOARD`: it is compared
       as it is, case-sensitive, and nothing is normalised (decision 4);
    4. the value is not exactly a ``str``, ``request`` is not exactly a
       ``dict``, or a key is not exactly a ``str``. The treatment of a key or
       a value that cannot come out of JSON is the module's own choice (see
       the module docstring).

    Of the values, only that of ``point`` is looked at. The request is not
    modified, no code of a key or of a value is called, and no file is read
    or written.
    """
    _step(request)


def step_of(request):
    """Return the ``step`` of the call ``request`` asks for (ADR-0040 decision 3).

    - ``request``: the request of a call of ``correctness.check``.

    The parameter has no default. Returns :data:`STEP_SIM` for a request whose
    ``point`` is :data:`SIM` and :data:`STEP_BOARD` for one whose ``point`` is
    :data:`BOARD`, and no other value. For every request :func:`check`
    refuses it raises the same ``ToolFailure``, with the same kind and
    message.

    No value but that of ``point`` is read: two requests it does not refuse
    that differ in anything else have the same ``step``. The identity of the
    call is formed by the builder and not here. The request is not modified.
    """
    return _step(request)


def _step(request):
    if type(request) is not dict:
        _refuse(_NO_OBJECT)
    for key in request:
        if type(key) is not str or key not in MEMBERS:
            _refuse(_unnamed(key))
    if MEMBER not in request:
        _refuse(_MISSING)
    value = request[MEMBER]
    if type(value) is not str:
        _refuse(_NO_STRING)
    if value not in _STEP_OF:
        _refuse(_OTHER)
    return _STEP_OF[value]


def _unnamed(key):
    shown = type(key) is str and _SHOWN.fullmatch(key)
    return (key if shown else _NOT_SHOWN) + _UNNAMED


def _refuse(message):
    raise tools.ToolFailure(tools.KIND_INVALID_REQUEST, message)
