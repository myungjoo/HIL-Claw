"""The six bf16 instance documents of P2-15, written from the owner's values.

Command line: ``python -m hilclaw.model_instances <values file> <output directory>``.
No option exists and nothing is read from standard input. A person runs it
before :mod:`hilclaw.new_run`; it starts no run and no ``claude``, is no FR-10
tool, and has no registry entry and no MCP name.

**The values file**, one JSON object decoded under the rules of
:mod:`hilclaw.new_run`. Every member is required and none has a default
(HQ-0066 (2); PROCESS/tasks/T-0530). An unknown member is refused::

    {
      "n_max": <int>, "draws": <int>, "round_budget": <int>,
      "kinds": {
        "gemm": {"m": <int>, "k": <int>, "n": <int>, "rtol": <number>, "atol": <number>},
        "rmsnorm": {"m": <int>, "n": <int>, "rtol": <number>, "atol": <number>},
        "elementwise_add": {"m": <int>, "n": <int>, "rtol": <number>, "atol": <number>},
        "swiglu": {"m": <int>, "n": <int>, "rtol": <number>, "atol": <number>},
        "rope": {"m": <int>, "h": <int>, "d": <int>, "rtol": <number>, "atol": <number>},
        "sdpa_kv_cache": {"m": <int>, "l": <int>, "h": <int>, "h_kv": <int>, "d": <int>,
                          "rtol": <number>, "atol": <number>}
      }
    }

The kinds and their shape members come from the bf16 entries of
:data:`hilclaw.contract_table.TABLE`. A value's range is that of the contract's
``op_signature_record`` and of :func:`hilclaw.instance_start.prepare`.

**One call**, in this order, the first failure ending it with nothing written:
the two arguments; the file; the kinds, members and shapes; the output
directory; no output file already there; ``HILCLAW_STANDIN_IMAGE``; the hw_profile
record, obtained once as :func:`hilclaw.nightly.local_profile` obtains it, which
starts one container of that image; the other values through ``prepare`` with
the start's own accelerators and predicate; the files, each opened so that it
cannot overwrite, and those of this call removed again when a later one fails.

**What it writes**: ``<kind>.json`` for each kind, a document in the form of
:func:`hilclaw.nightly.instance_document`: ``candidates_per_round`` 1 and the
objective ``latency_minimisation`` with no constraint (ADR-0189).

**What the caller is told**, through the process only: one compact ASCII JSON
line on standard output, whose ``outcome`` names the kind. ``reason`` is free
text and is never parsed.

=======================  ======  =============================================
``outcome``              status  further members
=======================  ======  =============================================
``written``              0       ``files``: the paths, in the order of ``KINDS``
``refused_values``       11      ``reason``
``no_standin_image``     12      ``reason``
``hw_profile``           13      ``reason``
``output_exists``        14      ``files``: the paths already there
``no_output_directory``  15      ``reason``
``file_system``          16      ``reason``
``bad_usage``            20      ``reason``
``unreadable_input``     21      ``reason``
``bad_input``            22      ``reason``
``fault``                24      ``fault``: the class name of the exception
=======================  ======  =============================================

Standard error gets nothing for a kind. A process without a standard output,
and a line that cannot be written, are said there with the status 24.
:class:`KeyboardInterrupt` and :class:`SystemExit` are not caught.
"""

import contextlib
import inspect
import json
import os
import sys
import types
from pathlib import Path

from hilclaw import (
    contract_table,
    instance,
    instance_start,
    keys,
    nightly,
    standin_image,
    tools,
)
from hilclaw.new_run import _described, _parsed, _standard, _told
from hilclaw.start_instance import _ACCELERATORS

_DTYPE = "bf16"
_TOLERANCE = ("rtol", "atol")
_COMMON = ("n_max", "draws", "round_budget")
_TOP = (*_COMMON, "kinds")

CONTRACTS = types.MappingProxyType(
    {
        entry.contract.KIND: entry.contract
        for entry in contract_table.TABLE.values()
        if entry.contract.DTYPE == _DTYPE
    }
)
"""Kind to contract module, for each bf16 entry of the contract table."""

KINDS = tuple(CONTRACTS)
"""The kinds, in the order of the contract table."""

EXIT_STATUS = {
    "written": 0,
    "refused_values": 11,
    "no_standin_image": 12,
    "hw_profile": 13,
    "output_exists": 14,
    "no_output_directory": 15,
    "file_system": 16,
    "bad_usage": 20,
    "unreadable_input": 21,
    "bad_input": 22,
    "fault": 24,
}


class RefusedValuesError(ValueError):
    """The values file breaks a rule; the message names the place."""


def _members(place, given, wanted):
    if type(given) is not dict:
        raise RefusedValuesError(f"{place}: must be an object")
    missing = [name for name in wanted if name not in given]
    unknown = [name for name in given if name not in wanted]
    if missing or unknown:
        raise RefusedValuesError(f"{place}: missing {missing}, unknown {unknown}")


def _shape_names(contract):
    return tuple(inspect.signature(contract.op_signature_record).parameters)


def op_records(values):
    """Return the op_signature record of each kind of the parsed values file, by kind.

    Raises :class:`RefusedValuesError` for a missing or unknown member or kind,
    a member that is not of the kind's contract, and a shape the contract does
    not cover. ``values`` is not modified.
    """
    _members("values", values, _TOP)
    _members("kinds", values["kinds"], KINDS)
    records = {}
    for kind, contract in CONTRACTS.items():
        names = _shape_names(contract)
        given = values["kinds"][kind]
        _members(f"kinds.{kind}", given, (*names, *_TOLERANCE))
        try:
            record = contract.op_signature_record(*(given[name] for name in names))
        except keys.InvalidRecordError as e:
            raise RefusedValuesError(f"kinds.{kind}: {e}") from e
        if not contract.covers(record):
            raise RefusedValuesError(f"kinds.{kind}: the contract does not cover it")
        records[kind] = record
    return records


def documents(values, hw_profile):
    """Return the instance document of each kind of the parsed values file, by kind.

    ``hw_profile`` is a hw_profile record. Each document is one
    :func:`hilclaw.instance_start.prepare` accepts under the start's own
    accelerators and predicate, and it is returned as built, so the start fills
    in what it fills in. Raises :class:`RefusedValuesError` as :func:`op_records`
    does and for a value ``prepare`` refuses.
    """
    made = {}
    for kind, record in op_records(values).items():
        given = values["kinds"][kind]
        try:
            document = nightly.instance_document(
                hw_profile,
                record,
                n_max=values["n_max"],
                draws=values["draws"],
                tolerance={name: given[name] for name in _TOLERANCE},
                round_budget=values["round_budget"],
            )
            instance_start.prepare(
                document,
                accelerators=_ACCELERATORS,
                covers=contract_table.start_covers,
            )
        except (
            keys.InvalidRecordError,
            instance.InvalidInstanceError,
            instance_start.OutOfScopeError,
        ) as e:
            raise RefusedValuesError(f"kinds.{kind}: {e}") from e
        made[kind] = document
    return made


def _write(directory, made):
    written = []
    try:
        for kind, document in made.items():
            path = directory / f"{kind}.json"
            text = json.dumps(document, indent=2, allow_nan=False) + "\n"
            with open(path, "xb") as handle:
                written.append(path)
                handle.write(text.encode("ascii"))
    except OSError:
        for path in written:
            with contextlib.suppress(OSError):
                path.unlink()
        raise
    return [str(path) for path in written]


def _profile(profile, environ):
    try:
        image = standin_image.read_image(environ)
    except (TypeError, standin_image.ImageRefusedError) as e:
        return None, _told("no_standin_image", _described(e))
    if image is None:
        return None, _told("no_standin_image", f"{standin_image.ENV_IMAGE} is not set")
    try:
        record = nightly.local_profile(image, profile)
        keys.hw_profile_key(record)
    except nightly.PROFILE_FAILURES as e:
        return None, _told("hw_profile", _described(e))
    return record, None


def _run(args, profile, environ):
    if len(args) != 2:
        count = len(args)
        return _told(
            "bad_usage", f"usage: expected a file and a directory, got {count}"
        )
    values, refused = _parsed(args[0])
    if refused is not None:
        return refused
    try:
        op_records(values)
    except RefusedValuesError as e:
        return _told("refused_values", str(e))
    directory = Path(args[1])
    if not directory.is_dir():
        return _told("no_output_directory", f"no directory {args[1]}")
    there = [directory / f"{kind}.json" for kind in KINDS]
    there = [str(path) for path in there if os.path.lexists(path)]
    if there:
        return {"outcome": "output_exists", "files": there}
    record, refused = _profile(profile, environ)
    if refused is not None:
        return refused
    try:
        made = documents(values, record)
    except RefusedValuesError as e:
        return _told("refused_values", str(e))
    try:
        return {"outcome": "written", "files": _write(directory, made)}
    except FileExistsError as e:
        return {"outcome": "output_exists", "files": [e.filename]}
    except OSError as e:
        return _told("file_system", _described(e))


def _say(stderr, text):
    with contextlib.suppress(Exception):
        if stderr is not None:
            line = f"hilclaw.model_instances: {text}".replace("\r", " ").replace(
                "\n", " "
            )
            stderr.write((line + "\n").encode("utf-8", "backslashreplace"))
            stderr.flush()


def main(argv=None, *, profile=None, environ=None, stdout=None, stderr=None):
    """Write the six documents the two arguments name; return the exit status.

    ``argv`` defaults to ``sys.argv[1:]``. ``profile`` is the hw_profile reader
    :func:`hilclaw.nightly.local_profile` takes, and ``environ`` the mapping the
    image is read from (default ``os.environ``). ``stdout`` and ``stderr`` are
    binary streams and default to the standard ones. Returns the status of the
    module docstring's table; no :class:`Exception` leaves the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    if stdout is None:
        _say(stderr, "fault: there is no standard output; nothing was written")
        return EXIT_STATUS["fault"]
    try:
        told = _run(args, profile, environ)
    except Exception as e:  # noqa: BLE001
        told = {"outcome": "fault", "fault": type(e).__name__}
    try:
        line = tools.encode(told)
        if stdout.write(line) != len(line):
            raise OSError("it took a part of the line")
        stdout.flush()
    except Exception as e:  # noqa: BLE001
        _say(stderr, f"cannot write standard output: {_described(e)}")
        return EXIT_STATUS["fault"]
    return EXIT_STATUS[told["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())
