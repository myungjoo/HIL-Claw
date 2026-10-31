"""The reader of the environment variable that names the ``cpu_standin`` image (ADR-0144 slice (3)).

``ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md``
decision 5 decides that the user names the one image of the four first-case
builds and processes in one environment variable of the process that runs the
operation, and leaves the variable's name and its check to this code slice.
The name is :data:`ENV_IMAGE`; :func:`read_image` reads it. The module is
bound to no tool and no backend operation; :mod:`hilclaw.standin_check`,
:mod:`hilclaw.model_forward_container` and :mod:`hilclaw.model_instances` call
:func:`read_image`, and
:mod:`hilclaw.nightly` and :mod:`hilclaw.turn_loop` use :data:`ENV_IMAGE` alone.

It reads only that one variable, writes nothing, starts no program and names
no image. Its check is :func:`hilclaw.standin_container.check_image`, the one
:func:`hilclaw.standin_container.run_in_container` applies to its ``image``,
so a value the client would read as an option is refused. No grammar of image
references is parsed and neither a tag nor a digest is required: whether the
reference must be a digest is open with the recording of the image's
identity (OD-14 sub-question 1 (na)). A tag can be moved to another image
between two builds without any change of the variable (decision 5, "One
reference is not always one image").

What this module does not decide: what an operation answers, and with which
kind, when no image is named or the value is refused (ADR-0144 decision 7;
OD-18 sub-questions 18 and 19; HQ-0021, HQ-0026), so each reaches the caller
as a plain fact, ``None`` or :class:`ImageRefusedError`; and whether and where
the identity of the image used is recorded (OD-14 sub-question 1 (na)).
"""

import os
from collections.abc import Mapping

from hilclaw import standin_container

ENV_IMAGE = "HILCLAW_STANDIN_IMAGE"
_REFUSED = f"{ENV_IMAGE} must not begin with '-' or hold whitespace or a NUL character"


class ImageRefusedError(ValueError):
    """The variable holds a value the check refuses; the text never quotes it."""


def read_image(environ=None):
    """Return the image reference named by :data:`ENV_IMAGE`, or ``None``.

    ``environ`` (any mapping) defaults to ``os.environ``. ``None`` is
    returned when the variable is unset or empty, as an empty variable counts
    as unset in :mod:`hilclaw.config`. A value the check passes is returned
    unchanged. Raises :class:`TypeError` when ``environ`` is not a mapping or
    the value is not ``str`` (the text names only its type), and
    :class:`ImageRefusedError`, with a fixed text, for a value the check
    refuses.
    """
    if environ is None:
        environ = os.environ
    if not isinstance(environ, Mapping):
        raise TypeError(f"environ must be a mapping, not {type(environ).__name__}")
    value = environ.get(ENV_IMAGE)
    if value is None or value == "":
        return None
    try:
        standin_container.check_image(value)
    except ValueError:
        refused = True
    else:
        refused = False
    if refused:
        raise ImageRefusedError(_REFUSED)
    return value
