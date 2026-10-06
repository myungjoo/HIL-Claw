"""Loader of ``hilclaw.config.json``, the binding of this source checkout to the data repository.

The file sits at the root of the source repository and names the data
repository (``HIL-Claw-data``) in its ``data_repo`` object::

    {"data_repo": {"url": "<git remote>", "local_path": "<checkout directory>"}}

Each of the two values can be overridden by an environment variable,
:data:`ENV_URL` and :data:`ENV_LOCAL_PATH`; a variable that is unset or empty
leaves the value of the file in place. Unknown keys are ignored.

This module only reads that one file and the environment. It does not check
that the checkout exists, runs no ``git`` and writes nothing.
"""

import json
import os
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "hilclaw.config.json"
ENV_URL = "HILCLAW_DATA_REPO_URL"
ENV_LOCAL_PATH = "HILCLAW_DATA_REPO_LOCAL_PATH"


class DataRepo(NamedTuple):
    """The data repository: its git remote and the absolute path of its local checkout."""

    url: str
    local_path: Path


class ConfigError(ValueError):
    """The config file cannot be read, or a value it must supply is missing or malformed."""


def load_data_repo(config_path=None, environ=None):
    """Return the :class:`DataRepo` described by the config file and the environment.

    ``config_path`` (``str`` or ``os.PathLike``) defaults to
    :data:`DEFAULT_CONFIG_PATH`; ``environ`` (any mapping) defaults to
    ``os.environ``. ``url`` is returned as given. ``local_path`` has ``~``
    expanded and is made absolute and normalised without touching the file
    system: a relative path from the file is taken from the directory of the
    config file, one from the environment from the current working directory.

    Raises :class:`ConfigError`, naming the file and the key, when the file is
    missing, unreadable, not UTF-8, not JSON or not an object, when ``data_repo`` is
    not an object, when a value in the file is not a non-empty string (even if
    the environment overrides it), or when a key is in neither place.
    """
    path = Path(DEFAULT_CONFIG_PATH if config_path is None else config_path)
    if environ is None:
        environ = os.environ
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ConfigError(f"{path}: not valid UTF-8: {e}") from e
    except (OSError, ValueError) as e:
        raise ConfigError(
            f"{path}: cannot read: {getattr(e, 'strerror', None) or e}"
        ) from e
    try:
        document = json.loads(text)
    except ValueError as e:
        raise ConfigError(f"{path}: not valid JSON: {e}") from e
    if not isinstance(document, dict):
        raise ConfigError(f"{path}: the top level must be an object")
    section = document.get("data_repo", {})
    if not isinstance(section, dict):
        raise ConfigError(f"{path}: data_repo: must be an object")
    url, _ = _pick(path, section, "url", environ, ENV_URL)
    local, overridden = _pick(path, section, "local_path", environ, ENV_LOCAL_PATH)
    base = "" if overridden else os.path.dirname(os.path.abspath(path))
    local = os.path.abspath(os.path.join(base, os.path.expanduser(local)))
    return DataRepo(url, Path(local))


def _pick(path, section, key, environ, variable):
    if key in section and (not isinstance(section[key], str) or not section[key]):
        raise ConfigError(f"{path}: data_repo.{key}: must be a non-empty string")
    if environ.get(variable):
        return environ[variable], True
    if key not in section:
        raise ConfigError(
            f"{path}: data_repo.{key}: missing, and {variable} is not set"
        )
    return section[key], False
