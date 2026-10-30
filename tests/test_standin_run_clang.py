import json
import os
import shutil
import subprocess

import first_run_stubs as stubs
import openmp_clang
import pytest

from hilclaw import (
    keys,
    layout,
    rope_bf16_contract,
    run_state,
    standin_image,
    standin_profile,
    tools,
)
from hilclaw.journal import EMPTY

CLANG = shutil.which("clang")
UNSHARE = shutil.which("unshare")
RUN = "run-a"
CALL = {"run_id": RUN, "round": 0, "candidate": 1, "attempt": 1, "execution": 1}
DIMS = {"m": 1, "h": 2, "d": 4}
KERNEL = (
    "#include <stddef.h>\n"
    "#include <stdint.h>\n"
    f"{rope_bf16_contract.PROTOTYPE}\n"
    f"{rope_bf16_contract.PROTOTYPE.removesuffix(';')}\n"
    "{\n"
    "    size_t i;\n"
    "    (void)freqs_cis;\n"
    "    for (i = 0; i < m * h * d; i++)\n"
    "        out[i] = x[i];\n"
    "}\n"
)

if not hasattr(os, "getuid"):
    pytest.skip("the stand-in containers need os.getuid", allow_module_level=True)
if CLANG is None:
    pytest.skip("this test needs a host clang", allow_module_level=True)


@pytest.fixture(autouse=True)
def usable_clang():
    openmp_clang.need()


def working_unshare():
    if UNSHARE is None:
        return None
    probe = subprocess.run(
        [UNSHARE, *stubs.NAMESPACE, "/bin/sh", "-c", 'test "$$" -eq 1'],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=60,
    )
    return UNSHARE if probe.returncode == 0 else None


def a_run(root):
    profile = {
        "schema_version": 1,
        "accelerator": standin_profile.ACCELERATOR,
        "revision": "test-revision",
        "toolchain": {"clang": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }
    record = rope_bf16_contract.op_signature_record(**DIMS)
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
        "op_signature": {"key": keys.op_signature_key(record).name, "record": record},
        "n_max": 6,
        "objective": {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [],
        },
        "draws": 1,
        "tolerance": {"rtol": 0.25, "atol": 3.0},
    }
    run = root / "runs" / RUN
    run.mkdir(parents=True)
    (run / "instance.json").write_text(json.dumps(document), encoding="utf-8")
    (run / "STATE.json").write_bytes(run_state.dump(0, EMPTY))


def test_a_rope_program_with_a_kernel_is_built_and_timed_through_a_stub_docker(
    tmp_path, monkeypatch
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "docker.ndjson"
    stubs.install(
        bin_dir,
        {
            "docker_log": str(log),
            "clang": CLANG,
            "unshare": working_unshare(),
            "git": shutil.which("git") or "git",
        },
    )
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(standin_image.ENV_IMAGE, "registry.example/hilclaw-clang:1")
    root = tmp_path / "data"
    a_run(root)
    output = layout.attempt_artefact(root, RUN, 0, 1, 1, "output")
    output.mkdir(parents=True)
    (output / "rope.c").write_text(KERNEL, encoding="ascii", newline="\n")

    result = tools.call(tools.default_registry(lambda: root), "board.run", dict(CALL))

    assert result["outcome"] in ("converged", "not_converged")
    assert result["contract_key"] == {
        "kind": "rope",
        "dtype": "bf16",
        "layout": "row_major",
    }
    assert result["shape"] == DIMS
    assert result["unit"] == "ns"
    assert type(result["memory_bytes"]) is int
    entries = stubs.read_log(log)
    assert [entry["container"] for entry in entries] == ["build", "build", "timing"]
    assert [entry["status"] for entry in entries] == [0, 0, 0]
