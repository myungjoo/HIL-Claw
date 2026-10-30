"""Whether the host ``clang`` builds and starts an OpenMP program. Test code, not a test file.

The tests that really build with :data:`hilclaw.standin_settings.FLAGS` call
:func:`need`: they are skipped only where no usable clang with the runtime
exists, and never on the CI gate (ADR-0188).
"""

import functools
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from hilclaw import clang_build, standin_openmp, standin_settings


@functools.lru_cache(maxsize=1)
def missing():
    """Return why the host ``clang`` is not usable with the set, or ``None``."""
    if shutil.which("clang") is None:
        return "clang is not on PATH"
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / standin_openmp.SOURCE_NAME
        source.write_bytes(standin_openmp.SOURCE)
        output = Path(directory) / standin_openmp.EXECUTABLE_NAME
        built = clang_build.build(
            source,
            output,
            timeout_s=120,
            flags=standin_settings.FLAGS,
            trailing_flags=standin_settings.TRAILING_FLAGS,
        )
        if not built.ok:
            return "the host clang builds no OpenMP program"
        started = subprocess.run([output], capture_output=True, check=False, timeout=60)
        if started.returncode != 0:
            return "the host clang's OpenMP program does not run"
    return None


def need():
    """Skip the calling test where :func:`missing` says so; fail it on the CI gate."""
    reason = missing()
    if reason is None:
        return
    if os.environ.get("GITHUB_ACTIONS") == "true":
        pytest.fail(f"{reason} on the CI runner")
    pytest.skip(reason)
