"""The "outside both checkouts" test shared by the modules that place a directory.

:mod:`hilclaw.scratch` (``ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md``
decision 3) and :mod:`hilclaw.selfcheck_session` refuse a directory that meets
a checkout: the directory that holds this package, :data:`PACKAGE_DIRECTORY`,
or a directory the caller names in ``keep_out``. This module holds that test.

Every path it is given is a ``str`` the caller has already checked; each is
compared by its real path as :func:`os.path.normcase` folds it. It raises no
error of its own other than the :class:`TypeError` of :func:`refuse_one_path`,
and prints nothing; how a refusal is reported stays with each caller.
"""

import itertools
import os

PACKAGE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def refuse_one_path(keep_out):
    """Raise :class:`TypeError` when ``keep_out`` is one path and not a sequence of paths."""
    if isinstance(keep_out, (str, bytes, os.PathLike)):
        raise TypeError("keep_out must be a sequence of paths, not one path")


def within(inner, outer):
    """Return whether the path ``inner`` is ``outer`` or lies below it, compared as given.

    The test is :func:`os.path.commonpath`; paths it cannot compare (on
    different drives, or one absolute and one relative) are not within each
    other.
    """
    try:
        return os.path.commonpath([inner, outer]) == outer
    except ValueError:
        return False


def meets_checkout(path, roots, *, containing):
    """Return whether ``path`` is or lies inside a checkout, or, with ``containing``, contains one.

    The checkouts are :data:`PACKAGE_DIRECTORY` and then each ``str`` of the
    iterable ``roots``, taken one at a time, so that a lazy ``roots`` stops
    being read at the first checkout met. Every operand is compared by
    :func:`os.path.normcase` of its :func:`os.path.realpath`.
    """
    folded = _folded(path)
    for root in itertools.chain((PACKAGE_DIRECTORY,), roots):
        root = _folded(root)
        if within(folded, root) or (containing and within(root, folded)):
            return True
    return False


def _folded(path):
    return os.path.normcase(os.path.realpath(path))
