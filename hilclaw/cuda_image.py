"""The reader of the environment variable that names the ``cuda_gpu`` image (ADR-0207 slice 5).

``ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md``
decision 7 decides that the builds and processes of the target ``cuda_gpu``
and its device query run in containers of one image with ``nvcc``, ``gcc``
and the CUDA runtime, and that the runtime names that image by an environment
variable, as :mod:`hilclaw.standin_image` names the ``cpu_standin`` image
(ADR-0144 decision 5). The name is :data:`ENV_IMAGE`; :func:`read_image`
reads it, with the same behaviour as :func:`hilclaw.standin_image.read_image`.

It reads only that one variable, writes nothing, starts no program and names
no image. Acquiring the image on a user's machine, and the NVIDIA Container
Toolkit that gives its containers the GPU, stay the user's permission
(NFR-4; FR-4; HQ-0094 (1)): the package pulls and installs nothing. Its check
is :func:`hilclaw.standin_container.check_image`, the one
:func:`hilclaw.standin_container.run_in_container` applies to its ``image``,
so a value the client would read as an option is refused. No grammar of
image references is parsed and neither a tag nor a digest is required.

What this module does not decide: what an operation answers when no image is
named or the value is refused, so each reaches the caller as a plain fact,
``None`` or :class:`ImageRefusedError`.
"""

import os
from collections.abc import Mapping

from hilclaw import standin_container

ENV_IMAGE = "HILCLAW_CUDA_IMAGE"
_REFUSED = f"{ENV_IMAGE} must not begin with '-' or hold whitespace or a NUL character"


class ImageRefusedError(ValueError):
    """The variable holds a value the check refuses; the text never quotes it."""


def read_image(environ=None):
    """Return the image reference named by :data:`ENV_IMAGE`, or ``None``.

    ``environ`` (any mapping) defaults to ``os.environ``. ``None`` is
    returned when the variable is unset or empty. A value the check passes is
    returned unchanged. Raises :class:`TypeError` when ``environ`` is not a
    mapping or the value is not ``str`` (the text names only its type), and
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
