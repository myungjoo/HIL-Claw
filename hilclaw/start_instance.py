"""The start of a first-case instance: one function that checks, builds the id and writes.

``ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`` decision 2
makes the start of an instance of ADR-0076 decision 1 one deterministic
function of this package. This module is that function, :func:`start`. It
joins :func:`hilclaw.instance_start.prepare` (ADR-0076), the refusal of a
given id (ADR-0111 decision 2), :func:`hilclaw.run_id.new` (ADR-0027),
:func:`hilclaw.instance_file.write` (ADR-0025) and the stop on a taken name
(ADR-0109), and returns the id it built (ADR-0111 decision 3). It binds the
``accelerators`` of ``prepare`` to :data:`hilclaw.mock_backend.NAME` and each
target of :data:`hilclaw.targets.TABLE` whose ``instance_start`` is true,
read from the table when this module is imported (ADR-0193 decision 3; today
:data:`hilclaw.standin_profile.ACCELERATOR` and
:data:`hilclaw.targets.VIRTUAL_NPU`, ADR-0197 decision 1), and its ``covers``
to :func:`hilclaw.contract_table.start_covers`, which admits a contract only
when every tool round 0 calls admits it - the fp32 ``gemm`` contract of
ADR-0008 and the six bf16 contracts (ADR-0177 decision 2; ADR-0181 decision 8
item 4) - read at the target of the document's ``accelerator``
(:func:`hilclaw.targets.covers_at`; ADR-0197 decision 3), so that a record of
a contract that target does not serve is out of scope there. It takes the
candidate kind of ADR-0198 decision 7 as ``prepare`` reads it: a document of
``schema_version`` 2 naming ``compile_settings`` is written as an
``instance.json`` of version 2 with that member, one of version 1 naming no
kind or ``c_kernel`` as version 1 without it, and every other pair is
refused, never rewritten; the accelerators and ``covers`` are bound alike
for both kinds.

It takes given code as ADR-0200 decisions 5 and 6 order (slice 2 of its
decision 8): a start handed ``code_file``, the path of one C source file,
reads the file, checks it against the kernel-file limit of ADR-0055 decision
6 (:data:`hilclaw.bring_in.MAX_FILE_BYTES`), has ``prepare`` check the
document with the file's SHA-256 (so version 3 holds ``given_code``, for a
``c_kernel`` instance of one candidate per round only), and then writes in
the order of ADR-0200 decision 5: the blob, ``instance.json`` of version 3,
and the ``artifacts.json`` record of the blob (``type`` ``given_code``,
``round`` 0, class ``final``, :func:`hilclaw.artifacts.add_record`). A start
without ``code_file`` writes exactly what it wrote before.

Conventions of this module, not rules of a record:

* The input is a parsed ``instance.json`` document, exactly a ``dict``, and a
  ``data_root`` given by name, a ``str`` or a path used as
  :func:`hilclaw.instance_file.write` uses it. There is no ``run_id``
  parameter; no configuration and no environment variable is read.
* A document whose top level holds a member named ``run_id`` is a given id
  and is refused with :class:`GivenRunIdError`. This is a refusal of the
  start, not a rule of validity: :mod:`hilclaw.instance` still accepts such a
  file. The owner confirmed this reading (HQ-0032).
* The bytes are built before the id and the id is built after every check
  has passed, immediately before the write of ``instance.json`` (after the
  blob, with ``code_file``), so a refusal builds no id. The
  bytes are the JSON text of the prepared document with an indent of two
  spaces, its members in the order the document holds them, non-ASCII
  characters escaped and no NaN or infinity, encoded as UTF-8 without a byte
  order mark and followed by one line feed.
* The C file is read once, whole, before any check of the document, and the
  bytes read are the bytes hashed and stored: the blob is stored with
  :func:`hilclaw.cas.put_bytes` of those bytes rather than
  :func:`hilclaw.cas.put_file` of the path (ADR-0200 decision 5 names the
  latter), which would read the file a second time after the checks. No
  name, suffix or content of the file is checked; it is placed as
  ``given.c`` when it becomes an attempt's kernel (ADR-0200 decision 2).
* Every refusal comes before the first write: a C file that cannot be read
  or exceeds the limit, and every refusal of ``prepare`` or of the given id,
  leave the data root as they found it. The blob is the first write; a
  failure of ``instance.json`` after it leaves a blob no ``artifacts.json``
  names, which the CAS GC keeps (ADR-0195 decision 7).
* The reports are exceptions told apart from each other:
  :class:`GivenCodeFileError` (no :class:`OSError`), :class:`GivenRunIdError`,
  :class:`hilclaw.instance_start.MissingMembersError` (passed through),
  :class:`GivenCodeNotAdmittedError`, :class:`RunIdInUseError` (no
  :class:`OSError`), :class:`GivenCodeUnrecordedError` (no :class:`OSError`)
  and the
  :class:`OSError` of the file system (passed through). The
  :class:`ValueError` of :func:`json.dumps` for NaN or an infinity, which
  :func:`hilclaw.instance.validate` lets through in an undefined member, also
  passes through; it is no :class:`hilclaw.instance.InvalidInstanceError`.
  Their wording is this module's; no form of a user interface is chosen.

Its caller for the start by a person or a script is the command-line entry
:mod:`hilclaw.new_run` (ADR-0155); other callers stay open. What it does not
do: it is no FR-10 tool, is not registered in :mod:`hilclaw.tools` and has
no command-line or MCP entry of its own (ADR-0115 decision 3). It writes no
``STATE.json`` and no line of ``events.ndjson``, looks at no
``runs/<run_id>/`` before the write, takes no lock and makes no commit. It
reads no stored hw_profile record (⑱), checks no source commit (⑳) and fills
in no ``owner`` or ``project`` (㉛). It says nothing of a run directory
without ``instance.json``. It keeps nothing between calls.
"""

import hashlib
import json

from hilclaw import (
    artifacts,
    bring_in,
    cas,
    contract_table,
    instance_file,
    instance_start,
    mock_backend,
    run_id,
    targets,
)

_ACCELERATORS = (mock_backend.NAME, *targets.instance_start_accelerators())


def _covers_of(document):
    # Read when prepare calls it, after the document is valid and in scope by its accelerator.
    def covered(record):
        accelerator = document["hw_profile"]["record"]["accelerator"]
        return targets.covers_at(contract_table.start_covers, accelerator)(record)

    return covered


#: The ``artifacts.json`` ``type`` of the given-code blob (ADR-0200 decision 5; HQ-0097 (b) (i)).
GIVEN_CODE_TYPE = "given_code"


class GivenCodeFileError(Exception):
    """The given C file cannot be read or exceeds :data:`hilclaw.bring_in.MAX_FILE_BYTES`.

    ``reason`` says which. Nothing was built or written. It is no
    :class:`OSError`, so it is not taken for a failure of the data root.
    """

    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"given code: {reason}; nothing was started")


class GivenCodeNotAdmittedError(Exception):
    """A start with given code that ADR-0200 decision 6 does not admit yet.

    The message names why: the candidate kind ``compile_settings`` (until
    slice 5 of ADR-0200 decision 8) or a ``candidates_per_round`` other than
    1. Nothing was built or written. The message shows no value of the
    document.
    """


class GivenCodeUnrecordedError(Exception):
    """The run was started but the record of its given code was not written.

    ``run_id`` is the id of the started run, whose ``instance.json`` and blob
    stay; ``reason`` names the failure of :func:`hilclaw.artifacts.add_record`
    (ADR-0200 decision 5). It is no :class:`OSError` and is raised ``from``
    that failure.
    """

    def __init__(self, built, reason):
        self.run_id = built
        self.reason = reason
        super().__init__(
            f"runs/{built}/artifacts.json: the run {built} was started, but the "
            f"record of its given code was not written: {reason}"
        )


class GivenRunIdError(Exception):
    """The refusal of ADR-0111 decision 2: the document gives a ``run_id``.

    Nothing was built or written. The message shows no value of the document.
    """

    def __init__(self):
        super().__init__(
            "instance: the start takes no run_id; it builds the id of the run "
            "itself, and nothing was started"
        )


class RunIdInUseError(Exception):
    """The stop of ADR-0109: the final name of the built id was found taken.

    ``run_id`` is the id the start built. The message names it and says that
    nothing was written under the name; it says nothing of the entry there.
    It is no :class:`OSError` and is raised ``from None``.
    """

    def __init__(self, built):
        self.run_id = built
        super().__init__(
            f"runs/{built}/instance.json: the run_id {built} the start built is "
            "in use; nothing was written under that name and nothing was started"
        )


def start(document, *, data_root, code_file=None):
    """Start the instance ``document`` under ``data_root``; return the ``run_id`` it built.

    ``code_file`` is ``None`` or the path of the given C file, a ``str`` or a
    path, given by name. In this order:

    1. With ``code_file``: the file is read whole; :class:`GivenCodeFileError`
       when it cannot be read (an :class:`OSError`, or the
       :class:`ValueError` of a path holding NUL) or holds more than
       :data:`hilclaw.bring_in.MAX_FILE_BYTES` bytes. Its SHA-256 is handed
       to ``prepare`` as ``given_code``.
    2. What :func:`hilclaw.instance_start.prepare` raises for the type, the
       validity, the candidate kind and the scope of ``document`` passes
       through unchanged. The kind and the version are the document's
       (ADR-0198 decision 7): ``schema_version`` 2 with ``candidate_kind``
       ``compile_settings`` is written as version 2 with the member, version
       1 without ``candidate_kind`` as version 1, and version 1 with
       ``candidate_kind`` ``c_kernel`` as version 1 without the member. Any
       other pair (version 1 with another kind, version 2 with ``c_kernel``,
       another kind or none) is
       :class:`hilclaw.instance.InvalidInstanceError`, and a version other
       than 1 and 2 :class:`hilclaw.instance.UnsupportedVersionError`; the
       start sets and changes no version and no kind, but for version 3
       with ``code_file``. A document that holds ``given_code`` or states
       version 3 is refused so, with ``code_file`` or without it.
       ``prepare`` is handed ``given_code`` only with ``code_file``.
    3. :class:`GivenRunIdError` when the top level of ``document`` holds
       ``run_id``, before any :class:`hilclaw.instance_start.MissingMembersError`.
    4. :class:`hilclaw.instance_start.MissingMembersError` passes through
       unchanged; then, with ``code_file``,
       :class:`GivenCodeNotAdmittedError` when the prepared document names
       ``compile_settings`` or a ``candidates_per_round`` other than 1.
    5. The bytes of the prepared document are built; what :func:`json.dumps`
       raises for a value it cannot write passes through unchanged.
    6. With ``code_file``: the bytes read are stored by
       :func:`hilclaw.cas.put_bytes` under ``data_root``; its
       :class:`OSError` passes through unchanged.
    7. One id is built by :func:`hilclaw.run_id.new` and the bytes are handed
       to :func:`hilclaw.instance_file.write` under it.
    8. :class:`RunIdInUseError` with that id when the write finds the name
       taken; nothing is retried and no other id is built. Every other
       exception of the write passes through unchanged.
    9. With ``code_file``: the blob is recorded in the run's
       ``artifacts.json`` (``type`` :data:`GIVEN_CODE_TYPE`, ``round`` 0,
       class ``final``); any :class:`Exception` of that is
       :class:`GivenCodeUnrecordedError` with the id, and the blob and
       ``instance.json`` stay.
    10. Otherwise the id is returned.

    Nothing is written before step 6 and no id is built before step 7.
    ``document`` is never modified.
    """
    code = None if code_file is None else _read_code(code_file)
    given_code = None if code is None else hashlib.sha256(code).hexdigest()
    try:
        prepared = instance_start.prepare(
            document,
            accelerators=_ACCELERATORS,
            covers=_covers_of(document),
            **({} if given_code is None else {"given_code": given_code}),
        )
    except instance_start.MissingMembersError:
        if "run_id" in document:
            raise GivenRunIdError() from None
        raise
    if "run_id" in document:
        raise GivenRunIdError()
    if given_code is not None:
        _admit(prepared)
    content = json.dumps(prepared, indent=2, allow_nan=False).encode() + b"\n"
    ref = None if code is None else cas.put_bytes(data_root, code)
    built = run_id.new()
    try:
        instance_file.write(data_root, built, content)
    except instance_file.NameTakenError:
        raise RunIdInUseError(built) from None
    if ref is not None:
        try:
            artifacts.add_record(
                data_root,
                built,
                ref,
                type=GIVEN_CODE_TYPE,
                round=0,
                retention_class="final",
            )
        except Exception as e:
            raise GivenCodeUnrecordedError(built, _described(e)) from e
    return built


def _admit(prepared):
    if "candidate_kind" in prepared:
        raise GivenCodeNotAdmittedError(
            "candidate_kind: given code is started for a c_kernel instance only; "
            "compile_settings with given code waits on slice 5 of ADR-0200 decision 8"
        )
    if prepared["candidates_per_round"] != 1:
        raise GivenCodeNotAdmittedError(
            "candidates_per_round: given code is started with one candidate per "
            "round only (ADR-0200 decision 6)"
        )


def _described(error):
    return f"{type(error).__name__}: {error}"


def _read_code(code_file):
    try:
        with open(code_file, "rb") as f:
            code = f.read(bring_in.MAX_FILE_BYTES + 1)
    except (OSError, ValueError) as e:
        raise GivenCodeFileError(f"the file cannot be read ({_described(e)})") from None
    if len(code) > bring_in.MAX_FILE_BYTES:
        raise GivenCodeFileError(
            f"the file holds more than {bring_in.MAX_FILE_BYTES} bytes "
            "(ADR-0055 decision 6)"
        )
    return code
