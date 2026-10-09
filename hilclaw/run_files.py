"""The answer of a tool function for a frame file of a run that cannot be used (ADR-0019).

``ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md`` reserves four
kinds for what one call of a tool finds in a *frame file* of
``runs/<run_id>/`` (``STATE.json``, ``events.ndjson``, ``instance.json``) at
the lookup or at the selection, and ADR-0030 decision 4 has them answered also
at the read of the layout version stamp, which comes before both:
``run_file_missing``, ``run_file_unreadable``, ``run_file_invalid`` and
``run_file_unsupported`` (decisions 2 and 3). This module holds what every
such read shares: the name of the file in a message (decision 6), "not there"
told from the other failures of the file system (decision 4), and
:func:`reading`, which turns what one read raises into the tool failure of
its kind.

It is applied around one read, by the tool function that knows the moment:
never by class at the level of :func:`hilclaw.tools.call` (decision 5). Which
class of a reader is which kind is stated by the caller of :func:`reading`;
this module knows no reader.

Conventions of this module, which the record does not fix:

- "Not there" is a :class:`FileNotFoundError` or a :class:`NotADirectoryError`,
  as the readers tell it (a missing run directory, a file in the place of a
  directory above the frame file, a data root that is no existing directory).
- The message of a tool failure made here starts with the path of the frame
  file relative to the data root. A message of a reader that is stated to have
  that form is used as it is; for an :class:`OSError` the message is composed
  from the class and the text of the system, without the path the system gave.
- Whether the data root is an existing directory is asked once more, for the
  message of a file that is not there and for :func:`data_root_is_there`; a
  data root that cannot be asked counts as not there.

It reads no frame file, writes nothing and keeps nothing between calls. A
failed append of a step line is not answered here:
:mod:`hilclaw.journaled_step` gives it one of the two kinds of ADR-0026.
"""

import contextlib
import os

from hilclaw import tools

#: The classes of an :class:`OSError` that mean the path is not there.
NOT_THERE = (FileNotFoundError, NotADirectoryError)


def relative(run_id, name):
    """Return the path of the frame file ``name`` of the run ``run_id``, relative to the data root.

    The text ``runs/<run_id>/<name>`` with which a message names the file
    (ADR-0019 decision 6). Neither argument is checked.
    """
    return f"runs/{run_id}/{name}"


def data_root_is_there(data_root):
    """Return whether ``data_root`` is an existing directory now; never raises an :class:`OSError`."""
    return os.path.isdir(data_root)


def read_failure(data_root, run_id, name, error):
    """Return the tool failure for ``error``, an :class:`OSError` of the read of a frame file.

    A :class:`hilclaw.tools.ToolFailure` of kind ``run_file_missing`` when
    ``error`` is one of :data:`NOT_THERE`, the message saying whether the data
    root is still an existing directory, and of kind ``run_file_unreadable``
    for every other ``OSError`` (ADR-0019 decision 4). It is returned, not
    raised, and no cause is attached: the caller raises it ``from error``.
    Raises :class:`TypeError` when ``error`` is no ``OSError``.
    """
    if not isinstance(error, OSError):
        raise TypeError(f"error must be an OSError, got {type(error).__name__}")
    file = relative(run_id, name)
    if isinstance(error, NOT_THERE):
        found = "is missing"
        if not data_root_is_there(data_root):
            found += ": the data root is not an existing directory"
        return tools.ToolFailure(tools.KIND_RUN_FILE_MISSING, f"{file}: {found}")
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    message = f"{file}: could not be read: {reported}"
    return tools.ToolFailure(tools.KIND_RUN_FILE_UNREADABLE, message)


@contextlib.contextmanager
def reading(data_root, run_id, name, kinds):
    """Answer what the read of the frame file ``name`` raises inside the ``with`` block.

    ``kinds`` maps an exception class of the reader to one of the four kinds;
    the message of such an exception must already start with the relative
    path, and is used as it is. An exception that is an instance of one of
    these classes is raised again as a :class:`hilclaw.tools.ToolFailure` of
    the kind of the first such class, in the order of ``kinds``. Any other
    :class:`OSError` is raised again as :func:`read_failure` answers it. Each
    is chained to the exception it answers for.

    Everything else passes through unchanged, a ``ToolFailure`` and a
    :class:`BaseException` included. The block must hold the read and nothing
    that can raise these classes for another reason.
    """
    try:
        yield
    except tuple(kinds) as error:
        kind = next(kinds[known] for known in kinds if isinstance(error, known))
        raise tools.ToolFailure(kind, str(error)) from error
    except OSError as error:
        raise read_failure(data_root, run_id, name, error) from error
