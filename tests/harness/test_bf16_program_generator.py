import builtins
import io
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import (
    clang_build,
    contract_table,
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    local_run,
    rmsnorm_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.harness import bf16_program_generator
from hilclaw.harness.bf16_program_generator import (
    GENERATED_KINDS,
    timing_name,
    timing_source,
    verification_name,
    verification_source,
)
from hilclaw.harness.bf16_timing import run_bf16_timing

DIRECTORY = Path(hilclaw.harness.__file__).parent
HEADERS = ("bf16_verification.h", "bf16_timing.h")

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

FUNCTIONS = (verification_name, timing_name, verification_source, timing_source)
FORMS = {
    "verification": (verification_name, verification_source),
    "timing": (timing_name, timing_source),
}

# kind: (contract, dimensions, first input, second input, output, element counts)
KINDS = {
    "gemm": (gemm_bf16_contract, "m k n", "a", "b", "c", ("m * k", "k * n", "m * n")),
    "rmsnorm": (rmsnorm_bf16_contract, "m n", "x", "w", "y", ("m * n", "n", "m * n")),
    "elementwise_add": (
        elementwise_add_bf16_contract,
        "m n",
        "a",
        "b",
        "c",
        ("m * n", "m * n", "m * n"),
    ),
    "swiglu": (
        swiglu_bf16_contract,
        "m n",
        "gate",
        "up",
        "out",
        ("m * n", "m * n", "m * n"),
    ),
}

DIMS = {
    "gemm": [(1, 1, 1), (2, 3, 4), (5, 1, 3), (1, 7, 2)],
    "rmsnorm": [(1, 1), (3, 5), (1, 9), (4, 1)],
    "elementwise_add": [(1, 1), (3, 5), (1, 9), (4, 1)],
    "swiglu": [(1, 1), (3, 5), (1, 9), (4, 1)],
}
SEEDS = [0, 7, 2**64 - 1]

TOO_LARGE = {
    "gemm": [
        (2**40, 2**40, 2**40),
        (2**62, 1, 1),
        (1, 2**62, 1),
        (2**63, 1, 1),
        (2**29, 2**29, 1),
    ],
    "rmsnorm": [(2**40, 2**40), (2**62, 1), (2**63, 1), (1, 2**62), (2**29, 2**29)],
    "elementwise_add": [(2**40, 2**40), (2**62, 1), (2**63, 1), (2**29, 2**29)],
    "swiglu": [(2**40, 2**40), (2**62, 1), (2**63, 1), (2**29, 2**29)],
}

REFUSED = [
    "rope",
    "sdpa_kv_cache",
    "conv2d",
    "",
    "GEMM",
    None,
    3,
    b"gemm",
    ("gemm",),
    type("Kind", (str,), {})("gemm"),
]

CRC = """\
static uint32_t crc(uint32_t value, const void *data, size_t bytes)
{
    const unsigned char *p = data;
    int bit;

    value = ~value;
    while (bytes-- > 0) {
        value ^= *p++;
        for (bit = 0; bit < 8; bit++)
            value = (value >> 1) ^ ((value & 1) != 0 ? UINT32_C(0xEDB88320) : 0);
    }
    return ~value;
}
"""

KERNEL = """\
#define _POSIX_C_SOURCE 200809L
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

@CRC@
@SIGNATURE@
{
    uint32_t scalar = 0;
    uint32_t first = crc(0, @FIRST@, (@FIRST_COUNT@) * 2);
    uint32_t second = crc(0, @SECOND@, (@SECOND_COUNT@) * 2);
    size_t i;

    @VOIDS@
@SCALAR@    @BODY@
}
"""

# name: body after the two digests are computed
BODIES = {
    "mixing": (
        'puts("kernel says hello");\n'
        "    for (i = 0; i < @OUTPUT_COUNT@; i++)\n"
        "        @OUTPUT@[i] = (uint16_t)(@OUTPUT@[i] ^ @FIRST@[i % (@FIRST_COUNT@)] ^"
        " (@SECOND@[i % (@SECOND_COUNT@)] << 1) ^ i ^ first ^ (second >> 3) ^ scalar"
        " ^ (@DIM_SUM@));\n"
    ),
    "silent": "(void)first;\n    (void)second;\n    (void)scalar;\n    (void)i;\n",
    "digest": (
        'fprintf(stderr, "digest @DIM_FORMAT@ %08lx %08lx %08lx\\n", @DIM_ARGS@,'
        " (unsigned long)first, (unsigned long)second, (unsigned long)scalar);\n"
        "    for (i = 0; i < @OUTPUT_COUNT@; i++)\n"
        "        @OUTPUT@[i] = 0;\n"
    ),
}

DIGEST = re.compile(rb"digest [0-9 ]+ [0-9a-f]{8} [0-9a-f]{8} [0-9a-f]{8}")


def kernel_source(kind, body):
    contract, dims, first, second, output, counts = KINDS[kind]
    names = dims.split()
    scalar = ""
    if kind == "rmsnorm":
        scalar = "    memcpy(&scalar, &eps, sizeof scalar);\n"
    replacements = {
        "@CRC@": CRC,
        "@SIGNATURE@": contract.PROTOTYPE.removesuffix(";"),
        "@VOIDS@": " ".join(f"(void){name};" for name in (*names, output)),
        "@SCALAR@": scalar,
        "@BODY@": BODIES[body],
        "@FIRST_COUNT@": counts[0],
        "@SECOND_COUNT@": counts[1],
        "@OUTPUT_COUNT@": counts[2],
        "@FIRST@": first,
        "@SECOND@": second,
        "@OUTPUT@": output,
        "@DIM_SUM@": " + ".join(f"{name} * {7 + i}" for i, name in enumerate(names)),
        "@DIM_FORMAT@": " ".join("%zu" for _ in names),
        "@DIM_ARGS@": ", ".join(names),
    }
    text = KERNEL
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def handwritten(form, kind):
    return DIRECTORY / FORMS[form][0](kind)


# Names and refusals


def test_generated_kinds_and_public_names():
    assert GENERATED_KINDS == ("gemm", "rmsnorm", "elementwise_add", "swiglu")
    assert type(GENERATED_KINDS) is tuple
    assert bf16_program_generator.__all__ == [
        "GENERATED_KINDS",
        "timing_name",
        "timing_source",
        "verification_name",
        "verification_source",
    ]


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_names_are_those_of_the_handwritten_programs(kind):
    assert verification_name(kind) == f"bf16_verification_{kind}.c"
    assert timing_name(kind) == f"bf16_timing_{kind}.c"
    assert (DIRECTORY / verification_name(kind)).is_file()
    assert (DIRECTORY / timing_name(kind)).is_file()


@pytest.mark.parametrize("function", FUNCTIONS, ids=lambda f: f.__name__)
@pytest.mark.parametrize("kind", REFUSED, ids=lambda value: repr(value))
def test_a_kind_outside_the_four_is_refused(function, kind):
    with pytest.raises(ValueError, match="^kind must be one of") as raised:
        function(kind)
    assert raised.value.parameter == "kind"


def test_the_two_handwritten_kinds_stay_in_the_table():
    kinds = {key[0] for key in contract_table.TABLE if key[1] == "bf16"}
    assert kinds - set(GENERATED_KINDS) == {"rope", "sdpa_kv_cache"}


# The text and what it is read from


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_source_is_ascii_and_declares_program_header_and_prototype(kind, form):
    text = FORMS[form][1](kind)
    assert type(text) is str
    text.encode("ascii")
    assert text.endswith("}\n")
    lines = text.splitlines()
    contract = KINDS[kind][0]
    assert contract.PROTOTYPE in lines
    assert f'#define PROGRAM "bf16_{form}_{kind}"' in lines
    assert f'#include "bf16_{form}.h"' in lines
    assert lines.index("#define _POSIX_C_SOURCE 200809L") < lines.index(
        f'#include "bf16_{form}.h"'
    )
    assert "<math.h>" not in text
    assert "generated by hilclaw.harness.bf16_program_generator" in text
    assert "ADR-0193 decision 6" in text
    assert f"hilclaw_{kind}_bf16(" in text
    for other in GENERATED_KINDS:
        if other != kind:
            assert f"hilclaw_{other}_bf16" not in text


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_command_lines_in_the_header_comment(kind):
    dims = " ".join(f"<{name}>" for name in KINDS[kind][1].split())
    assert f" *     {dims} <draws> <seed>\n" in verification_source(kind)
    timing = f" *     {dims} <n_min> <n_max> <cv_max> <sample_form> <seed>\n"
    assert timing in timing_source(kind)
    assert "(ADR-0163)" in verification_source(kind)
    assert "(ADR-0181 decision 2)" in timing_source(kind)


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_draw_lines_use_the_contracts_draw_bits(kind):
    contract, _, first, second, _, counts = KINDS[kind]
    first_bits, second_bits = contract.DRAW_BITS
    for text in (verification_source(kind), timing_source(kind)):
        assert f"draw_patterns({first}, {counts[0]}, base, 0, {first_bits});" in text
        offset = f"(uint64_t)({counts[0]})"
        wanted = f"draw_patterns({second}, {counts[1]}, base, {offset}, {second_bits});"
        assert wanted in text


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_the_scalar_is_compiled_in_from_the_contract(kind):
    for text in (verification_source(kind), timing_source(kind)):
        if kind == "rmsnorm":
            assert "UINT32_C(0x3727C5AC)" in text
            assert "memcpy(&eps, &eps_bits, sizeof eps);" in text
            assert "float_has_32_bits" in text
        else:
            assert "UINT32_C(" not in text
            assert "memcpy" not in text
            assert "float" not in text


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_a_changed_table_value_changes_the_text(kind, monkeypatch):
    contract = KINDS[kind][0]
    before = (verification_source(kind), timing_source(kind))
    monkeypatch.setattr(contract, "DRAW_BITS", (9, 9))
    after = (verification_source(kind), timing_source(kind))
    assert after != before
    assert all(", base, 0, 9);" in text for text in after)
    if kind == "rmsnorm":
        monkeypatch.setattr(contract, "EPS_BITS", 0x3F800000)
        assert "UINT32_C(0x3F800000)" in verification_source(kind)
        assert "UINT32_C(0x3F800000)" in timing_source(kind)


def test_the_size_check_of_the_two_inputs_together_is_kept_for_all_but_gemm():
    for kind in GENERATED_KINDS:
        _, _, first, second, _, _ = KINDS[kind]
        joint = f"{first}_bytes > SIZE_MAX - {second}_bytes"
        for text in (verification_source(kind), timing_source(kind)):
            assert (joint in text) == (kind != "gemm")


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_each_call_returns_the_same_new_text(kind):
    assert verification_source(kind) == verification_source(kind)
    assert timing_source(kind) == timing_source(kind)
    assert verification_source(kind) != timing_source(kind)


def test_the_source_functions_read_and_write_nothing(monkeypatch, tmp_path):
    def refused(*args, **kwargs):
        raise AssertionError("a file was opened")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(builtins, "open", refused)
    monkeypatch.setattr(io, "open", refused)
    monkeypatch.setattr(os, "open", refused)
    monkeypatch.setattr(Path, "read_text", refused)
    monkeypatch.setattr(Path, "read_bytes", refused)
    monkeypatch.setattr(subprocess, "Popen", refused)
    for kind in GENERATED_KINDS:
        for function in FUNCTIONS:
            function(kind)
    monkeypatch.undo()
    assert list(tmp_path.iterdir()) == []


def test_the_module_imports_no_numpy():
    code = (
        "import sys\n"
        "import hilclaw.harness.bf16_program_generator\n"
        "print(sorted(name for name in sys.modules if name.split('.')[0] == 'numpy'))\n"
    )
    found = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=DIRECTORY.parent.parent,
    )
    assert found.stdout.strip() == "[]"


# The contract constants are the bits of today's programs


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_the_contract_constants_are_the_bits_of_the_handwritten_programs(kind, form):
    contract = KINDS[kind][0]
    text = handwritten(form, kind).read_text(encoding="ascii")
    bits = re.findall(r"draw_patterns\(\w+, [^;]*, (\d+)\);", text)
    assert tuple(int(value) for value in bits) == contract.DRAW_BITS
    patterns = re.findall(r"UINT32_C\((0x[0-9A-F]{8})\)", text)
    if kind == "rmsnorm":
        assert [int(value, 16) for value in patterns] == [contract.EPS_BITS]
    else:
        assert patterns == []


# Equivalence with the handwritten programs (ADR-0193 decision 6 items 1 to 3)


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("the programs need a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_program_generator")
    generated = directory / "generated"
    generated.mkdir()
    for header in HEADERS:
        shutil.copyfile(DIRECTORY / header, generated / header)
    cache = {}

    def build(form, kind, origin, body):
        key = (form, kind, origin, body)
        if key not in cache:
            name, source = FORMS[form]
            program = DIRECTORY / name(kind)
            if origin == "generated":
                program = generated / name(kind)
                program.write_text(source(kind), encoding="ascii", newline="\n")
            stem = f"{form}-{kind}-{origin}-{body}"
            kernel = directory / f"{stem}-kernel.c"
            kernel.write_text(kernel_source(kind, body), encoding="ascii", newline="\n")
            output = directory / stem
            result = clang_build.build(
                (program, kernel),
                output,
                timeout_s=BUILD_TIMEOUT,
                flags=(*STRICT, "-O2"),
                trailing_flags=("-lm",),
            )
            assert result.ok, result.log
            cache[key] = output
        return cache[key]

    return build


def both(built, form, kind, body, *arguments):
    return [
        local_run.run(
            (built(form, kind, origin, body), *map(str, arguments)),
            timeout_s=RUN_TIMEOUT,
        )
        for origin in ("handwritten", "generated")
    ]


def assert_same(runs):
    old, new = runs
    assert old.timed_out is False
    assert new.timed_out is False
    assert new.returncode == old.returncode
    assert new.stdout == old.stdout
    assert new.stderr == old.stderr


@pytest.mark.parametrize("body", ["mixing", "silent"])
@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_verification_reports_are_equal_byte_for_byte(built, kind, body):
    for dims in DIMS[kind]:
        for seed in SEEDS:
            for draws in (1, 3):
                runs = both(built, "verification", kind, body, *dims, draws, seed)
                assert_same(runs)
                assert runs[0].returncode == 0, runs[0]
                m_n = dims[0] * dims[-1]
                assert len(runs[0].stdout) == draws * (4 + 2 * m_n) + 4
                assert runs[0].stdout.endswith(b"end\n")


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_verification_reports_differ_by_seed(built, kind):
    dims = DIMS[kind][1]
    reports = {
        both(built, "verification", kind, "mixing", *dims, 2, seed)[1].stdout
        for seed in SEEDS
    }
    assert len(reports) == len(SEEDS)


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_timing_digests_are_equal_and_both_reports_are_judged(built, kind):
    for dims in DIMS[kind][:2]:
        for seed in SEEDS:
            digests = []
            for origin in ("handwritten", "generated"):
                result = run_bf16_timing(
                    built("timing", kind, origin, "digest"),
                    kind,
                    dims,
                    sample_form="interval",
                    seed=seed,
                    timeout_s=RUN_TIMEOUT,
                    n_max=10,
                )
                assert result.broken is None, result.run
                lines = [
                    line
                    for line in result.run.stderr.splitlines()
                    if line.startswith(b"digest ")
                ]
                assert len(lines) == 1 + len(result.intervals_ns)
                assert all(DIGEST.fullmatch(line) for line in lines)
                assert len(set(lines)) == 1
                digests.append(lines[0])
            assert digests[0] == digests[1]
            assert digests[0].startswith(
                b"digest " + " ".join(map(str, dims)).encode() + b" "
            )


def command_lines(form, kind):
    dims = ("3",) * len(KINDS[kind][1].split())
    rest = ("2", "7") if form == "verification" else ("2", "4", "0.05", "interval", "7")
    good = (*dims, *rest)
    yield ()
    yield good[:-1]
    yield (*good, "1")
    for index in range(len(dims)):
        for value in ("0", "x", "-1", "+1", "01", "", "1" * 30):
            yield (*good[:index], value, *good[index + 1 :])
    for dims in TOO_LARGE[kind]:
        yield (*map(str, dims), *rest)


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_refused_command_lines_give_the_same_status_and_message(built, kind, form):
    seen = set()
    for arguments in command_lines(form, kind):
        runs = both(built, form, kind, "silent", *arguments)
        assert_same(runs)
        assert runs[0].returncode in (2, 3), (arguments, runs[0])
        assert runs[0].stdout == b""
        assert runs[0].stderr.startswith(f"bf16_{form}_{kind}: ".encode())
        assert runs[0].stderr.count(b"\n") == 1
        seen.add((runs[0].returncode, runs[0].stderr.split(b":")[1]))
    assert (3, b" sizes") in seen
    assert (3, b" malloc") in seen
    assert (2, b" usage") in seen
