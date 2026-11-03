"""The read-only environment check of ADR-0194 decision 7 (PLAN P3-8).

Command line: ``python -m hilclaw.toolchain_check [<image> ...]``. Each
argument is the reference of an image already on the machine; an argument
that :func:`hilclaw.standin_container.check_image` refuses (``--help`` and
any other text that begins with ``-`` included) makes a bad usage. Nothing is
read from standard input.

**What it reads.** For each component of :data:`COMPONENTS` it starts the
component's own query, assembled and interpreted by that component's adapter
(``assemble_probe`` and ``interpret_probe`` of its module; no second list of
commands): on the host through :func:`hilclaw.local_run.run` under
:data:`HOST_TIME_LIMIT_S`, and in each named image, for the components that
are not ``host_only``, through
:func:`hilclaw.standin_container.run_in_container` under
:data:`IMAGE_TIME_LIMIT_S`, which starts the container with no network and
pull policy ``never`` (ADR-0144). Devices are read on the host only
(``host_only``), since a container is given none (ADR-0194 decision 2). A
component is added by an entry of :data:`COMPONENTS`; today the table holds
``clang`` of :mod:`hilclaw.clang_adapter`, ``nvcc`` and the host-only
device query ``nvidia-smi`` of :mod:`hilclaw.cuda_adapter`, and the QNN SDK's
``qnn-net-run`` of :mod:`hilclaw.qnn_adapter`.

**The report.** Standard output gets one JSON document followed by one LF:

* ``host``: an object keyed by component name;
* ``images``: an object keyed by image reference, in the order first named
  (a reference named twice is read once). Each value has ``state``,
  ``read`` when a container could be used for each component and
  ``unreadable`` otherwise; ``message``, ``null`` when ``read`` and a short
  text when ``unreadable``; and ``components``, an object keyed by component
  name, empty when ``unreadable``.

A component entry has ``state`` (``present``, ``absent`` or ``unreadable``),
``version`` (the version line when ``present``, else ``null``) and
``message`` (``null`` when ``present``, else a short fixed text). For the
device query, ``absent`` is either the query program missing or no device
(:data:`hilclaw.cuda_adapter.NO_DEVICE` as the message). The report
holds no path, environment value, token, command line or output of a child
other than the version line. It is no data-plane format and has no
``schema_version``; where it goes beyond standard output is not this
module's (ADR-0194 decision 7, OD-26).

**Exit statuses**, fixed:

* :data:`EXIT_READ` (0): the report was written and every entry is
  ``present`` or ``absent``; a missing component is a reported fact;
* :data:`EXIT_UNREADABLE` (10): the report was written and some component or
  image is ``unreadable``;
* :data:`EXIT_USAGE` (20): an argument was refused; nothing was started;
* :data:`EXIT_FAULT` (21): the command's own error (an exception not read as
  an entry) or a standard output it does not have or cannot write.

None of them is 1 or 2, the interpreter's. Standard error gets one fixed line,
``hilclaw.toolchain_check: usage: ...`` or ``hilclaw.toolchain_check: fault:
<class>`` (the class name, never the error's text), only when no report was
written.

**Read only.** It installs, pulls, downloads and updates nothing, starts no
``claude``, sets no environment variable and hands no ``env`` on. It writes
nothing but its report, with one exception: each container call is given a
fresh empty temporary directory to mount, which
:func:`hilclaw.standin_container.run_in_container` requires, and that
directory is removed before the call returns, whatever happened. On the
host, an exception of the query that the adapter does not read is the entry
``unreadable``; for an image, an exception of the container call or a result
the adapter leaves to the image (the client's own failure) makes the image
``unreadable``. Asking permission for what is missing is the runtime's
(FR-4, NFR-4), not this command's.
"""

import contextlib
import json
import sys
import tempfile
from typing import NamedTuple

from hilclaw import (
    clang_adapter,
    cuda_adapter,
    local_run,
    qnn_adapter,
    standin_container,
    vendor_adapter,
)

HOST_TIME_LIMIT_S = 30
IMAGE_TIME_LIMIT_S = 120
REMOVAL_TIME_LIMIT_S = 30
CLIENT = "docker"

EXIT_READ = 0
EXIT_UNREADABLE = 10
EXIT_USAGE = 20
EXIT_FAULT = 21

READ = "read"

_NOT_RUN = "the query could not be run"
_NO_CONTAINER = "no container of the image could be used"


class Component(NamedTuple):
    """One entry of :data:`COMPONENTS`: an adapter's probe pair and program.

    ``assemble(*, timeout_s, program)`` returns a
    :class:`hilclaw.vendor_adapter.RunCall`; ``interpret(answer, program)``
    reads a host answer and ``interpret_container(answer)`` a container
    answer, each as a :class:`hilclaw.vendor_adapter.Probe` or ``None``.
    ``program`` is handed to ``assemble``; ``host_only`` keeps the component
    out of images (a device query), whose ``interpret_container`` may then be
    ``None``.
    """

    assemble: object
    interpret: object
    interpret_container: object
    program: object
    host_only: bool = False


COMPONENTS = {
    "clang": Component(
        assemble=clang_adapter.assemble_probe,
        interpret=clang_adapter.interpret_probe,
        interpret_container=clang_adapter.interpret_container_probe,
        program=clang_adapter.PROGRAM,
    ),
    "nvcc": Component(
        assemble=cuda_adapter.assemble_probe,
        interpret=cuda_adapter.interpret_probe,
        interpret_container=cuda_adapter.interpret_container_probe,
        program=cuda_adapter.PROGRAM,
    ),
    "nvidia-smi": Component(
        assemble=cuda_adapter.assemble_device_probe,
        interpret=cuda_adapter.interpret_device_probe,
        interpret_container=None,
        program=cuda_adapter.DEVICE_PROGRAM,
        host_only=True,
    ),
    "qnn-net-run": Component(
        assemble=qnn_adapter.assemble_probe,
        interpret=qnn_adapter.interpret_probe,
        interpret_container=qnn_adapter.interpret_container_probe,
        program=qnn_adapter.VERSION_PROGRAM,
    ),
}


def _entry(found):
    return {
        "state": found.state,
        "version": found.version,
        "message": None if found.state == vendor_adapter.PRESENT else found.message,
    }


def _unreadable(message):
    return {"state": vendor_adapter.UNREADABLE, "version": None, "message": message}


def _host_entry(component):
    call = component.assemble(timeout_s=HOST_TIME_LIMIT_S, program=component.program)
    try:
        answer = local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)
    except Exception as error:  # noqa: BLE001
        answer = error
    found = component.interpret(answer, call.command[0])
    if found is None:
        return _unreadable(_NOT_RUN)
    return _entry(found)


def _image_probe(image, component, client):
    call = component.assemble(timeout_s=IMAGE_TIME_LIMIT_S, program=component.program)
    with tempfile.TemporaryDirectory(prefix="hilclaw-toolchain-check-") as empty:
        try:
            answer = standin_container.run_in_container(
                image,
                empty,
                call.command[0],
                call.command[1:],
                timeout_s=call.timeout_s,
                removal_timeout_s=REMOVAL_TIME_LIMIT_S,
                client=client,
            )
        except Exception as error:  # noqa: BLE001
            answer = error
    return component.interpret_container(answer)


def _image_entry(image, components, client):
    found = {}
    for name, component in components.items():
        if component.host_only:
            continue
        probe = _image_probe(image, component, client)
        if probe is None:
            return {
                "state": vendor_adapter.UNREADABLE,
                "message": _NO_CONTAINER,
                "components": {},
            }
        found[name] = _entry(probe)
    return {"state": READ, "message": None, "components": found}


def check(images=(), *, components=None, client=CLIENT):
    """Read the host and each of ``images`` and return the report as a ``dict``.

    ``images`` is a sequence of image references, each checked by
    :func:`hilclaw.standin_container.check_image` before anything is started
    (its :class:`TypeError` or :class:`ValueError` is passed on).
    ``components`` defaults to :data:`COMPONENTS`; ``client`` is the
    container runtime's program handed to
    :func:`hilclaw.standin_container.run_in_container`. Nothing is written to
    a stream. An exception outside the queries (of an ``assemble`` part, an
    ``interpret`` part or the temporary directory) is passed on.
    """
    if isinstance(images, (str, bytes)):
        raise TypeError(
            f"images must be a sequence of str, not one {type(images).__name__}"
        )
    images = list(dict.fromkeys(images))
    for image in images:
        standin_container.check_image(image)
    components = COMPONENTS if components is None else components
    host = {name: _host_entry(component) for name, component in components.items()}
    read = {image: _image_entry(image, components, client) for image in images}
    return {"host": host, "images": read}


def exit_status(report):
    """Return :data:`EXIT_UNREADABLE` when an entry or image of ``report`` is ``unreadable``, else :data:`EXIT_READ`."""
    entries = list(report["host"].values())
    for image in report["images"].values():
        entries.append(image)
        entries.extend(image["components"].values())
    if any(entry["state"] == vendor_adapter.UNREADABLE for entry in entries):
        return EXIT_UNREADABLE
    return EXIT_READ


def _standard(name):
    return getattr(getattr(sys, name), "buffer", None)


def _say(stderr, text):
    with contextlib.suppress(OSError, ValueError):
        if stderr is not None:
            line = f"hilclaw.toolchain_check: {text}\n"
            stderr.write(line.encode("ascii", "backslashreplace"))
            stderr.flush()


def main(argv=None, *, stdout=None, stderr=None, components=None, client=CLIENT):
    """Read the machine and the named images, write the report and return the exit status.

    ``argv`` defaults to ``sys.argv[1:]``: the image references. ``stdout``
    and ``stderr`` are binary streams and default to the standard ones; a
    missing ``stdout`` is a fault found before anything is started.
    ``components`` and ``client`` are as in :func:`check`. Returns one of the
    four exit statuses of the module; no :class:`Exception` leaves the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    try:
        for image in args:
            standin_container.check_image(image)
    except (TypeError, ValueError):
        _say(stderr, "usage: python -m hilclaw.toolchain_check [<image> ...]")
        return EXIT_USAGE
    try:
        if stdout is None:
            raise OSError("standard output is closed")
        report = check(args, components=components, client=client)
        status = exit_status(report)
        document = (json.dumps(report, ensure_ascii=True) + "\n").encode("ascii")
        if stdout.write(document) != len(document):
            raise OSError("standard output took a part of the report")
        stdout.flush()
    except Exception as fault:  # noqa: BLE001
        _say(stderr, f"fault: {type(fault).__name__}")
        return EXIT_FAULT
    return status


if __name__ == "__main__":
    raise SystemExit(main())
