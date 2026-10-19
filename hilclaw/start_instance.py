"""The start of a first-case instance: one function that checks, builds the id and writes.

``ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`` decision 2
makes the start of an instance of ADR-0076 decision 1 one deterministic
function of this package. This module is that function, :func:`start`. It
joins :func:`hilclaw.instance_start.prepare` (ADR-0076), the refusal of a
given id (ADR-0111 decision 2), :func:`hilclaw.run_id.new` (ADR-0027),
:func:`hilclaw.instance_file.write` (ADR-0025) and the stop on a taken name
(ADR-0109), and returns the id it built (ADR-0111 decision 3). It binds the
``accelerators`` of ``prepare`` to :data:`hilclaw.mock_backend.NAME` and
:data:`hilclaw.standin_profile.ACCELERATOR` and its ``covers`` to
:func:`hilclaw.gemm_contract.covers`.

Conventions of this module, not rules of a record:

* The input is a parsed ``instance.json`` document, exactly a ``dict``, and a
  ``data_root`` given by name, a ``str`` or a path used as
  :func:`hilclaw.instance_file.write` uses it. There is no ``run_id``
  parameter; no configuration and no environment variable is read.
* A document whose top level holds a member named ``run_id`` is a given id
  and is refused with :class:`GivenRunIdError`. This is a refusal of the
  start, not a rule of validity: :mod:`hilclaw.instance` still accepts such a
  file.
* The bytes are built before the id and the id is built after every check
  has passed, immediately before the write, so a refusal builds no id. The
  bytes are the JSON text of the prepared document with an indent of two
  spaces, its members in the order the document holds them, non-ASCII
  characters escaped and no NaN or infinity, encoded as UTF-8 without a byte
  order mark and followed by one line feed.
* The reports are exceptions told apart from each other:
  :class:`GivenRunIdError`, :class:`hilclaw.instance_start.MissingMembersError`
  (passed through), :class:`RunIdInUseError` (no :class:`OSError`) and the
  :class:`OSError` of the file system (passed through). Their wording is this
  module's; no form of a user interface is chosen.

What it does not do: it binds no caller (OD-23, UC-1); it is no FR-10 tool,
is not registered in :mod:`hilclaw.tools` and has no command-line or MCP
entry (ADR-0115 decision 3). It writes no ``STATE.json`` and no line of
``events.ndjson``, looks at no ``runs/<run_id>/`` before the write, takes no
lock and makes no commit. It reads no stored hw_profile record (⑱), checks no
source commit (⑳) and fills in no ``owner`` or ``project`` (㉛). It says
nothing of a run directory without ``instance.json``. It keeps nothing
between calls.
"""

import json

from hilclaw import (
    gemm_contract,
    instance_file,
    instance_start,
    mock_backend,
    run_id,
    standin_profile,
)

_ACCELERATORS = (mock_backend.NAME, standin_profile.ACCELERATOR)


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


def start(document, *, data_root):
    """Start the instance ``document`` under ``data_root``; return the ``run_id`` it built.

    In this order:

    1. What :func:`hilclaw.instance_start.prepare` raises for the type, the
       validity and the scope of ``document`` passes through unchanged.
    2. :class:`GivenRunIdError` when the top level of ``document`` holds
       ``run_id``, before any :class:`hilclaw.instance_start.MissingMembersError`.
    3. :class:`hilclaw.instance_start.MissingMembersError` passes through
       unchanged.
    4. The bytes of the prepared document are built; what :func:`json.dumps`
       raises for a value it cannot write passes through unchanged.
    5. One id is built by :func:`hilclaw.run_id.new` and the bytes are handed
       to :func:`hilclaw.instance_file.write` under it.
    6. :class:`RunIdInUseError` with that id when the write finds the name
       taken; nothing is retried and no other id is built. Every other
       exception of the write passes through unchanged.
    7. Otherwise the id is returned.

    Nothing is built or written before step 5. ``document`` is never modified.
    """
    try:
        prepared = instance_start.prepare(
            document, accelerators=_ACCELERATORS, covers=gemm_contract.covers
        )
    except instance_start.MissingMembersError:
        if "run_id" in document:
            raise GivenRunIdError() from None
        raise
    if "run_id" in document:
        raise GivenRunIdError()
    content = json.dumps(prepared, indent=2, allow_nan=False).encode() + b"\n"
    built = run_id.new()
    try:
        instance_file.write(data_root, built, content)
    except instance_file.NameTakenError:
        raise RunIdInUseError(built) from None
    return built
