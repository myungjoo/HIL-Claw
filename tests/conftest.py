import types

import pytest

from hilclaw import coder_runtime

_RUNTIME_TESTS = "test_coder_runtime"


def _refused(*args, **kwargs):
    pytest.fail("a test started the container client of hilclaw.coder_runtime")


@pytest.fixture(autouse=True)
def no_container_client(request, monkeypatch):
    """Keep every test outside the runtime's own from starting ``docker``.

    A test that means to reach :class:`hilclaw.coder_runtime.DockerRuntime`
    replaces ``local_run`` or ``subprocess`` of that module itself.
    """
    if request.module.__name__.rpartition(".")[2] == _RUNTIME_TESTS:
        return
    monkeypatch.setattr(coder_runtime, "local_run", types.SimpleNamespace(run=_refused))
    monkeypatch.setattr(
        coder_runtime,
        "subprocess",
        types.SimpleNamespace(Popen=_refused, DEVNULL=coder_runtime.subprocess.DEVNULL),
    )
