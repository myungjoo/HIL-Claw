"""The data-root source of a tool function (ADR-0015 decision 3).

A *data-root source* is a callable without arguments that returns the data
root or fails. A tool function that needs the data plane is built with one in
reach and calls :func:`obtain` with it, after it has checked its request. The
source is asked at each call that needs the data root and its answer is not
kept; the data root is never a member of a request. :func:`configured` is the
source of the two fronts of the package.
"""

import os
from pathlib import Path

from hilclaw import config, tools


def configured():
    """Return the data root that the configuration names now.

    It is ``hilclaw.config.load_data_repo().local_path``, read from the default
    configuration file and the environment at each call. Raises
    :class:`hilclaw.config.ConfigError` as the loader does and does not check
    that the directory exists.
    """
    return config.load_data_repo().local_path


def obtain(source):
    """Ask ``source`` once and return the data root it names as a :class:`pathlib.Path`.

    ``source`` returns a ``str`` or an ``os.PathLike`` that names an existing
    directory; the path is used as given, not resolved. Raises
    :class:`hilclaw.tools.ToolFailure` of kind ``no_data_root`` when the source
    raises an :class:`Exception` (the failure is chained to it), returns
    anything else or an empty ``str``, or names what is no existing directory.
    Nothing is created, read or written. Raises :class:`TypeError` when
    ``source`` is not callable.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")
    try:
        named = source()
    except Exception as e:
        raise tools.ToolFailure(
            tools.KIND_NO_DATA_ROOT,
            f"the data-root source failed: {type(e).__name__}: {e}",
        ) from e
    try:
        text = os.fspath(named) if isinstance(named, (str, os.PathLike)) else None
    except TypeError:
        text = None
    if not isinstance(text, str) or not text:
        raise tools.ToolFailure(
            tools.KIND_NO_DATA_ROOT,
            f"the data-root source named no path: {type(named).__name__} {named!r}",
        )
    if not os.path.isdir(text):
        raise tools.ToolFailure(
            tools.KIND_NO_DATA_ROOT,
            f"the data root is not an existing directory: {text}",
        )
    return Path(text)
