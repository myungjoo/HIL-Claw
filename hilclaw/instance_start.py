"""The check the start of a first-case instance makes before it writes ``instance.json``.

``ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md``
fixes, for the instances of its decision 1 (an ``hw_profile.record`` that
names ``cpu_standin`` or the mock as its ``accelerator``, and either no
stated ``op_signature`` or one that ADR-0041 decision 5 covers; widened by
``ARCHITECTURE/decisions/ADR-0197-od32-virtual-npu-oracle-and-instance-start.md``
decision 1 to ``virtual_npu`` and the contracts it serves), that the
start requires the content to state ``op_signature``, ``objective``,
``candidates_per_round``, ``n_max``, ``draws`` and ``tolerance``; that it puts
the ``n_max`` default of ADR-0007 decision 8 into the content when none is
given and never replaces a given one; and that a refusal writes nothing and
reports every missing member in a fixed order (decisions 2 and 3).
``ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md`` decision 4
adds, at the step where ``n_max`` is filled in, that the start puts the full
name of the Opus model into the content when it states no ``coder_model`` and
never replaces a given one.
``ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md``
decision 7 has the start take ``candidate_kind``: a content that names
``compile_settings`` is written as version 2 with that member, one that names
no kind or ``c_kernel`` as version 1 without it; the required set and its
scope are the same for both.
``ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md`` decision 6
has the start take ``given_code``: a start handed the hash of a given C file
writes version 3 with that member. The module renders that check:

* :data:`CODER_MODEL_DEFAULT`: the full Opus name the start fills in
  (ADR-0136 decision 4).
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
  :func:`hilclaw.instance.parse` is :func:`hilclaw.instance.validate_kinded`
  here, the document form of the rules of versions 1 and 2.
* The kind is stated by the content, with its version, and the start sets
  neither: ``schema_version`` 2 with ``candidate_kind`` ``compile_settings``
  is a version-2 instance, and ``schema_version`` 1 without the member is a
  C kernel instance. ``schema_version`` 1 with ``candidate_kind``
  ``c_kernel`` names the kind a version-1 file states by lacking the member,
  so the member is left out of the returned document and nothing else
  changes; this is the only member the start removes. Every other pair is
  contradictory or names no kind of the list and is refused as
  :func:`hilclaw.instance.validate_kinded` refuses it, never rewritten:
  version 1 with another kind, version 2 with ``c_kernel``, another kind or
  none.
* The hash of given code reaches :func:`prepare` from its caller, as
  ``given_code``, never from the document: a document holding
  ``given_code`` or stating ``schema_version`` 3 is refused as
  :func:`hilclaw.instance.validate_kinded` refuses it, with a hash or
  without one, so version 3 is set by the start only, from the hash of the
  file its caller stores. What ADR-0200 decision 6 does not admit yet with
  given code (``compile_settings``, more than one candidate per round) is
  refused by that caller, :func:`hilclaw.start_instance.start`, not here.
* The order is validity, then scope, then the filling-in of ``n_max`` and
  ``coder_model``, then the required set. ADR-0076 decision 3 lists the
  filling-in before validity; for a valid document the outcome is the same,
  since adding a valid ``n_max`` or ``coder_model`` does not change whether a
  document is valid; and an invalid document or one outside decision 1 has
  nothing filled in. ``coder_model`` is never missing, so
  :data:`REPORT_ORDER` does not name it (ADR-0136 decision 4).
* The names of the accelerators of decision 1 and "covered" reach
  :func:`prepare` from its caller, as ``accelerators`` and ``covers``: the
  names are :data:`hilclaw.mock_backend.NAME` and those of the target table
  whose ``instance_start`` is true (ADR-0193 decision 3; ADR-0197 decision 1),
  and for a run of the coder's round loop whose ``coder_loop`` is true as well
  (ADR-0207 decision 3),
  and the reading of ADR-0041 decision 5 is the start's predicate of the
  contract table (ADR-0177 decision 2) read at the target of the document's
  ``accelerator`` (ADR-0197 decision 3). This
  module imports neither the ``cpu_standin`` record module nor the contract
  table and holds no accelerator name and no reading of "covered" of its
  own; the caller binds them.
* A ``covers`` that is not callable, an ``accelerators`` that is not exactly a
  ``tuple`` of exactly ``str`` items and an answer of ``covers`` whose type is
  not exactly ``bool`` are :class:`TypeError`; such an answer is never taken
  as "covered".
* :class:`OutOfScopeError` is no :class:`ValueError`, so it is not taken for an
  invalid document. Its messages and that of :class:`MissingMembersError` name
  members and constants only and show no value of the document.
* The default is :data:`hilclaw.harness.measurement.N_MAX_DEFAULT`, the value
  of ADR-0007 decision 8 as the package holds it; this module holds no number.
  The coder model default is this module's :data:`CODER_MODEL_DEFAULT`, cited
  from F2 of ADR-0136 with the date it was read. It lives here and not in
  :mod:`hilclaw.instance`, since only the start applies the default and no
  reader substitutes one. A later task may replace it with a newer Opus name
  without a new record; a file once written keeps its value (ADR-0136
  decision 4).

What the module does not do: it reads, writes and builds no file and no
bytes, and calls no writer. It names no component of the start and takes no
value from a user (OD-23, UC-1). It does not check ``source_commit``, the
budgets, ``owner``, ``project`` or ``injections``, compares no N with a range
or a cap, and does not check that the stated objective is covered (ADR-0076
Boundaries; ADR-0061 decision 4). It changes and stands in for no answer of a
tool (ADR-0076 decision 4) and raises no :class:`hilclaw.tools.ToolFailure`.
It keeps nothing between calls and imports no NumPy. It resolves no model
alias, checks no model name against a list of offered models and tries no
model against any service; how the start learns of a given ``coder_model``
stays open (ADR-0136 decision 4, HQ-0032).
"""

from hilclaw import instance
from hilclaw.harness import measurement

#: Full name F2 (https://docs.claude.com/en/docs/claude-code/model-config, read 2026-10-21) gives for ``opus``; ADR-0136 decision 4.
CODER_MODEL_DEFAULT = "claude-opus-5-5"

#: The members a refusal reports, in the order of ADR-0076 decision 3. ``n_max`` and ``coder_model`` are never missing.
REPORT_ORDER = (
    "op_signature",
    "objective",
    "candidates_per_round",
    "draws",
    "tolerance",
)

_C_KERNEL, *_ = instance.CANDIDATE_KINDS

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
    Nothing is required of such a document here and nothing is allowed. It is
    no refusal of the start: what the start does with such a document stays
    open (ADR-0076 decision 1 and Boundaries).
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


def prepare(document, *, accelerators, covers, given_code=None):
    """Return the document the start of the instance may hand on to be written.

    - ``document``: a parsed ``instance.json``, exactly a ``dict``.
    - ``accelerators``: the names of the accelerators of ADR-0076 decision 1
      as ADR-0197 decision 1 widens it, exactly a ``tuple`` of exactly ``str``
      items.
    - ``covers``: the predicate of ADR-0041 decision 5, a callable that is
      handed an op_signature record and returns ``True`` when it is covered
      and ``False`` when it is not.
    - ``given_code``: ``None``, or the SHA-256 hex digest of the given C file
      that the caller stores (ADR-0200 decision 6).

    ``accelerators`` and ``covers`` are given by name and have no default;
    ``given_code`` is given by name. In this order:

    1. :class:`TypeError` when the type of ``document`` is not exactly
       ``dict``, then when ``accelerators`` is not as above, then when
       ``covers`` is not callable.
    2. The kind (ADR-0198 decision 7): when ``schema_version`` is exactly
       the ``int`` 1 and ``candidate_kind`` exactly the ``str``
       ``c_kernel``, the document checked and handed on from here is
       ``document`` without ``candidate_kind``; otherwise it is ``document``.
    3. :func:`hilclaw.instance.validate_kinded`; what it raises passes
       through unchanged. A version other than 1 and 2 is
       :class:`hilclaw.instance.UnsupportedVersionError`; version 1 holding
       ``candidate_kind`` (other than step 2's) and version 2 lacking it or
       holding ``c_kernel`` or a value outside
       :data:`hilclaw.instance.CANDIDATE_KINDS` are
       :class:`hilclaw.instance.InvalidInstanceError`, so no version or kind
       is ever set or changed by the start. A given ``n_max`` that breaks
       ADR-0023, or a given ``coder_model`` that breaks ADR-0136 decision 3,
       is refused there and never replaced by the default.
    4. :class:`OutOfScopeError` when ``hw_profile.record.accelerator`` is none
       of ``accelerators``, or when an ``op_signature`` is stated and
       ``covers``, called once with its record, returns ``False``. What
       ``covers`` raises passes through unchanged, and an answer that is not
       exactly a ``bool`` is :class:`TypeError`. ``covers`` is not called for
       a document without ``op_signature`` or with another accelerator.
       The scope is the same for both versions.
    5. A new top-level ``dict`` holding every member of the document of step
       2 as given, those :mod:`hilclaw.instance` does not define included,
       in their order, and, when
       ``n_max`` is absent, ``n_max`` set to
       :data:`hilclaw.harness.measurement.N_MAX_DEFAULT`, and, when
       ``coder_model`` is absent, ``coder_model`` set to
       :data:`CODER_MODEL_DEFAULT` (ADR-0136 decision 4). Nothing else is
       added, removed or changed.
    6. :class:`MissingMembersError` when any member of :data:`REPORT_ORDER` is
       absent from it, with every absent one; the required set is the same
       for both versions.
    7. With ``given_code``: ``schema_version`` of that ``dict`` becomes 3
       in its place, ``given_code`` is added as its last member and the
       ``dict`` is checked by :func:`hilclaw.instance.validate_given`, whose
       :class:`hilclaw.instance.InvalidInstanceError` for a ``given_code``
       that is no such digest passes through unchanged.
    8. Otherwise that ``dict`` is returned; it passes
       :func:`hilclaw.instance.validate_given`. Without ``given_code`` it
       is the ``dict`` of before ADR-0200: it passes
       :func:`hilclaw.instance.validate_kinded`, and a returned version-1
       ``dict`` also passes :func:`hilclaw.instance.validate`.

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
    document = _without_c_kernel(document)
    instance.validate_kinded(document)
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
    prepared.setdefault("coder_model", CODER_MODEL_DEFAULT)
    missing = tuple(name for name in REPORT_ORDER if name not in prepared)
    if missing:
        raise MissingMembersError(missing)
    if given_code is not None:
        prepared["schema_version"] = instance.GIVEN_SCHEMA_VERSION
        prepared["given_code"] = given_code
        instance.validate_given(prepared)
    return prepared


def _without_c_kernel(document):
    version = document.get("schema_version")
    kind = document.get("candidate_kind")
    if not (type(version) is int and version == instance.SCHEMA_VERSION):
        return document
    if not (type(kind) is str and kind == _C_KERNEL):
        return document
    return {name: value for name, value in document.items() if name != "candidate_kind"}
