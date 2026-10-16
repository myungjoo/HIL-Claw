"""The check the start of a first-case instance makes before it writes ``instance.json``.

``ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md``
fixes, for the instances of its decision 1 (an ``hw_profile.record`` that
names ``cpu_standin`` or the mock as its ``accelerator``, and either no
stated ``op_signature`` or one that ADR-0041 decision 5 covers), that the
start requires the content to state ``op_signature``, ``objective``,
``candidates_per_round``, ``n_max``, ``draws`` and ``tolerance``; that it puts
the ``n_max`` default of ADR-0007 decision 8 into the content when none is
given and never replaces a given one; and that a refusal writes nothing and
reports every missing member in a fixed order (decisions 2 and 3). The module
renders that check:

* :data:`REPORT_ORDER`: the order of the report (ADR-0076 decision 3).
* :class:`OutOfScopeError`: a valid document outside decision 1.
* :class:`MissingMembersError`: the refusal of decision 3, with every missing
  member.
* :func:`prepare`: the document the start may hand on to be written.

Choices that are this module's own and no rule of a record:

* The check is made on a document, the parsed form of a content (a ``dict``),
  and returns a document. ADR-0076 decision 3 puts the check on the content
  held before step 1 of ADR-0025 and has the start put the default into that
  content; building JSON text is not done here, as :mod:`hilclaw.instance_file`
  builds none either. The validity the record names as
  :func:`hilclaw.instance.parse` is :func:`hilclaw.instance.validate` here,
  the document form of the same rules.
* The order is validity, then scope, then the filling-in of ``n_max``, then
  the required set. ADR-0076 decision 3 lists the filling-in before validity;
  for a valid document the outcome is the same, since a valid ``n_max`` added
  to it makes it neither valid nor invalid, and so a document outside
  decision 1 or an invalid one has nothing filled in.
* The names of the accelerators of decision 1 and "covered" reach
  :func:`prepare` from its caller, as ``accelerators`` and ``covers``: the
  names of ADR-0016 decisions 4 and 5 are
  :data:`hilclaw.mock_backend.NAME` and the ``ACCELERATOR`` of the module that
  builds the ``cpu_standin`` record, and the reading of ADR-0041 decision 5 is
  the ``covers`` of the contract module of the first case. Neither the
  ``cpu_standin`` record module nor the contract module is bound to a start of
  an instance, so this module imports neither and holds no accelerator name
  and no reading of "covered" of its own; the caller binds them.
* A ``covers`` that is not callable, an ``accelerators`` that is not exactly a
  ``tuple`` of exactly ``str`` items and an answer of ``covers`` whose type is
  not exactly ``bool`` are :class:`TypeError`; such an answer is never taken
  as "covered".
* :class:`OutOfScopeError` is no :class:`ValueError`, so it is not taken for an
  invalid document. Its messages and that of :class:`MissingMembersError` name
  members and constants only and show no value of the document.
* The default is :data:`hilclaw.harness.measurement.N_MAX_DEFAULT`, the value
  of ADR-0007 decision 8 as the package holds it; this module holds no number.

What the module does not do: it reads, writes and builds no file and no
bytes, and calls no writer. It names no component of the start and takes no
value from a user (OD-23, UC-1). It does not check ``source_commit``, the
budgets, ``owner``, ``project`` or ``injections``, compares no N with a range
or a cap, and does not check that the stated objective is covered (ADR-0076
Boundaries; ADR-0061 decision 4). It changes and stands in for no answer of a
tool (ADR-0076 decision 4) and raises no :class:`hilclaw.tools.ToolFailure`.
It keeps nothing between calls and imports no NumPy.
"""

from hilclaw import instance
from hilclaw.harness import measurement

#: The members a refusal reports, in the order of ADR-0076 decision 3. ``n_max`` is never missing.
REPORT_ORDER = (
    "op_signature",
    "objective",
    "candidates_per_round",
    "draws",
    "tolerance",
)

_NOT_THESE_ACCELERATORS = (
    "hw_profile.record.accelerator: names none of the accelerators of ADR-0076 decision 1; "
    "ADR-0076 requires and allows nothing of such an instance"
)
_NOT_COVERED = (
    "op_signature: the stated record is one ADR-0041 decision 5 does not cover; "
    "ADR-0076 requires and allows nothing of such an instance"
)


class OutOfScopeError(Exception):
    """A valid document outside ADR-0076 decision 1; the message names why.

    Why is either the accelerator of ``hw_profile.record`` or a stated
    ``op_signature`` that the ``covers`` handed to :func:`prepare` does not
    cover.
    Nothing is required of such a document here and nothing is allowed.
    """


class MissingMembersError(Exception):
    """The refusal of ADR-0076 decision 3: the document lacks members the start requires.

    ``missing`` is a non-empty ``tuple`` of every missing member name, in the
    order of :data:`REPORT_ORDER`. The message lists the same names in the
    same order and shows no value of the document.
    """

    def __init__(self, missing):
        self.missing = tuple(missing)
        super().__init__(
            "instance: the start requires "
            + ", ".join(self.missing)
            + "; the content states none of these"
        )


def prepare(document, *, accelerators, covers):
    """Return the document the start of the instance may hand on to be written.

    - ``document``: a parsed ``instance.json``, exactly a ``dict``.
    - ``accelerators``: the names of the accelerators of ADR-0076 decision 1,
      exactly a ``tuple`` of exactly ``str`` items: the ``cpu_standin`` and the
      mock names (ADR-0016 decisions 4 and 5).
    - ``covers``: the predicate of ADR-0041 decision 5, a callable that is
      handed an op_signature record and returns ``True`` when it is covered
      and ``False`` when it is not.

    ``accelerators`` and ``covers`` are given by name and have no default. In
    this order:

    1. :class:`TypeError` when the type of ``document`` is not exactly
       ``dict``, then when ``accelerators`` is not as above, then when
       ``covers`` is not callable.
    2. :func:`hilclaw.instance.validate`; what it raises passes through
       unchanged. A given ``n_max`` that breaks ADR-0023 is refused there and
       never replaced by the default.
    3. :class:`OutOfScopeError` when ``hw_profile.record.accelerator`` is none
       of ``accelerators``, or when an ``op_signature`` is stated and
       ``covers``, called once with its record, returns ``False``. What
       ``covers`` raises passes through unchanged, and an answer that is not
       exactly a ``bool`` is :class:`TypeError`. ``covers`` is not called for
       a document without ``op_signature`` or with another accelerator.
    4. A new top-level ``dict`` holding every member of ``document`` as given,
       those :mod:`hilclaw.instance` does not define included, and, when
       ``n_max`` is absent, ``n_max`` set to
       :data:`hilclaw.harness.measurement.N_MAX_DEFAULT`. Nothing else is
       added, removed or changed.
    5. :class:`MissingMembersError` when any member of :data:`REPORT_ORDER` is
       absent from it, with every absent one.
    6. Otherwise that ``dict`` is returned; it passes
       :func:`hilclaw.instance.validate`.

    ``document`` is never modified. The returned ``dict`` is a new object, but
    the values of its members are the objects ``document`` holds, shared and
    not copied.
    """
    if type(document) is not dict:
        raise TypeError(
            f"document must be exactly a dict, got {type(document).__name__}"
        )
    if type(accelerators) is not tuple or any(
        type(name) is not str for name in accelerators
    ):
        raise TypeError("accelerators: must be exactly a tuple of exactly str items")
    if not callable(covers):
        raise TypeError("covers: must be callable")
    instance.validate(document)
    if document["hw_profile"]["record"]["accelerator"] not in accelerators:
        raise OutOfScopeError(_NOT_THESE_ACCELERATORS)
    if "op_signature" in document:
        covered = covers(document["op_signature"]["record"])
        if type(covered) is not bool:
            raise TypeError("covers: must return exactly a bool")
        if not covered:
            raise OutOfScopeError(_NOT_COVERED)
    prepared = dict(document)
    prepared.setdefault("n_max", measurement.N_MAX_DEFAULT)
    missing = tuple(name for name in REPORT_ORDER if name not in prepared)
    if missing:
        raise MissingMembersError(missing)
    return prepared
