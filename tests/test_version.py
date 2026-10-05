import tomllib
from pathlib import Path

import hilclaw

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_version_is_non_empty_string():
    assert isinstance(hilclaw.__version__, str)
    assert hilclaw.__version__


def test_version_matches_pyproject():
    with PYPROJECT.open("rb") as f:
        project = tomllib.load(f)["project"]
    assert hilclaw.__version__ == project["version"]
