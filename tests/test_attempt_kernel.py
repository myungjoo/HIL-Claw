import json
import os
from pathlib import Path

import numpy as np
import pytest
import test_kernel_source as kernel_sources
import test_model_forward as forward
import test_model_forward_execute as forward_execute
import test_model_reference as reference
import test_spec_file as spec_files
from test_model_reference import clang  # noqa: F401

from hilclaw import (
    attempt_kernel,
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    gemm_contract,
    kernel_source,
    layout,
    model_forward_execute,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    spec_file,
    standin_settings,
    swiglu_bf16_contract,
)
from hilclaw.attempt_kernel import (
    NO_SPEC_FILE,
    REASONS,
    SPEC_INVALID,
    SPEC_OTHER_ATTEMPT,
    SPEC_OTHER_VERSION,
    SPEC_UNREADABLE,
    AttemptKernelError,
    kernel_reference,
)
from hilclaw.kernel_source import (
    ATTEMPT_DIRECTORY_UNLISTABLE,
    ENTRY_KIND_UNDETERMINED,
    NO_ATTEMPT_DIRECTORY,
    NO_COMPILED_FILE,
    NO_OUTPUT_DIRECTORY,
    OUTPUT_DIRECTORY_UNLISTABLE,
    KernelSource,
    KernelSourceReadError,
)
from hilclaw.model_binding import KernelReference
from hilclaw.model_reference import compare, reference_logits

RUN = "synthetic-run-1"
FLAGS = ("-O2", "-ffp-contract=off")
CONTRACT_ARGUMENTS = {
    "gemm_fp32": (gemm_contract, (3, 5, 7)),
    "gemm_bf16": (gemm_bf16_contract, (1, 1, 1)),
    "rmsnorm": (rmsnorm_bf16_contract, (1, 1)),
    "add": (elementwise_add_bf16_contract, (1, 1)),
    "swiglu": (swiglu_bf16_contract, (1, 1)),
    "rope": (rope_bf16_contract, (1, 1, 2)),
    "sdpa": (sdpa_kv_cache_bf16_contract, (1, 1, 1, 1, 1)),
}
FORWARD_CONTRACT = {
    "gemm": "gemm_bf16",
    "rmsnorm": "rmsnorm",
    "add": "add",
    "swiglu": "swiglu",
    "rope": "rope",
    "sdpa": "sdpa",
}


def document(round=1, candidate=1, attempt=1, contract="gemm_fp32", run_id=RUN):
    module, arguments = CONTRACT_ARGUMENTS[contract]
    made = spec_files.minimal(op=module.op_signature_record(*arguments))
    made["id"].update(run_id=run_id, round=round, candidate=candidate, attempt=attempt)
    if candidate > 1:
        made["id"].update(
            candidates=candidate, relation="same_technique", variant="synthetic"
        )
    if attempt > 1:
        failure = {"attempt": attempt - 1, "stage": "compile", "report": "synthetic"}
        made["repair"] = {"failures": [failure]}
    made["task"]["contract"] = module.task_contract(*arguments)
    return made


def content_of(made):
    return (json.dumps(made, indent=2) + "\n").encode("utf-8")


def as_parsed(contract):
    return json.loads(json.dumps(contract))


def spec_path(root, round=1, candidate=1, attempt=1):
    return layout.attempt_artefact(root, RUN, round, candidate, attempt, "spec.json")


def output_path(root, round=1, candidate=1, attempt=1):
    return layout.attempt_artefact(root, RUN, round, candidate, attempt, "output")


def make_attempt(root, round=1, candidate=1, attempt=1, names=("k.c",), **changes):
    made = document(round, candidate, attempt, **changes)
    spec_file.write(root, content_of(made))
    output = output_path(root, round, candidate, attempt)
    output.mkdir()
    kernel_sources.write(output, *names)
    return made


def place_spec(root, content, round=1, candidate=1, attempt=1):
    path = spec_path(root, round, candidate, attempt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    output = output_path(root, round, candidate, attempt)
    output.mkdir()
    kernel_sources.write(output, "k.c")
    return path


def tree(root):
    snapshot = {}
    for directory, directories, files in os.walk(root):
        for name in directories + files:
            path = Path(directory) / name
            facts = os.lstat(path)
            snapshot[path] = (facts.st_mode, facts.st_size, facts.st_mtime_ns)
    return snapshot


def refused(root, reason, *arguments, flags=FLAGS):
    before = tree(root)
    with pytest.raises(AttemptKernelError) as raised:
        kernel_reference(root, *(arguments or (RUN, 1, 1, 1)), flags=flags)
    assert raised.value.reason == reason
    assert str(raised.value) == reason
    assert tree(root) == before
    return raised.value


def test_reasons_are_the_spec_outcomes_then_those_of_the_reader():
    assert REASONS == (
        "no_spec_file",
        "spec_unreadable",
        "spec_invalid",
        "spec_other_version",
        "spec_other_attempt",
        NO_ATTEMPT_DIRECTORY,
        NO_OUTPUT_DIRECTORY,
        NO_COMPILED_FILE,
        ATTEMPT_DIRECTORY_UNLISTABLE,
        OUTPUT_DIRECTORY_UNLISTABLE,
        ENTRY_KIND_UNDETERMINED,
    )
    assert len(set(REASONS)) == len(REASONS)
    assert issubclass(AttemptKernelError, Exception)
    assert not issubclass(AttemptKernelError, (OSError, ValueError))


@pytest.mark.parametrize("contract", sorted(CONTRACT_ARGUMENTS))
def test_the_reference_of_an_attempt(tmp_path, contract):
    made = make_attempt(tmp_path, names=("b.c", "a.c", "k.h"), contract=contract)
    before = tree(tmp_path)
    answer = kernel_reference(tmp_path, RUN, 1, 1, 1, flags=list(FLAGS))
    assert type(answer) is KernelReference
    output = output_path(tmp_path)
    assert answer.sources == (output / "a.c", output / "b.c")
    assert type(answer.sources) is tuple
    module, arguments = CONTRACT_ARGUMENTS[contract]
    assert answer.contract == made["task"]["contract"]
    assert answer.contract == as_parsed(module.task_contract(*arguments))
    assert answer.flags == FLAGS and type(answer.flags) is tuple
    assert tree(tmp_path) == before


def test_the_answer_is_what_the_reader_and_parse_give(tmp_path):
    make_attempt(tmp_path, names=("x.c", "y.h"))
    answer = kernel_reference(tmp_path, RUN, 1, 1, 1, flags=FLAGS)
    source = kernel_source.read_compiled_set(output_path(tmp_path))
    parsed = spec_file.parse(spec_path(tmp_path).read_bytes())
    assert answer == (
        source.compiled_set,
        parsed["task"]["contract"],
        FLAGS,
        source.headers,
    )


def test_the_headers_are_the_readers(tmp_path):
    make_attempt(tmp_path, names=("b.c", "a.c", "k.h"))
    answer = kernel_reference(tmp_path, RUN, 1, 1, 1, flags=FLAGS)
    output = output_path(tmp_path)
    assert answer.headers == (output / "k.h",)
    assert type(answer.headers) is tuple
    assert answer.sources == (output / "a.c", output / "b.c")


def test_several_headers_keep_the_readers_order(tmp_path):
    make_attempt(tmp_path, names=("k.c", "z.h", "a_1.h", "a-1.h", "a.h", "m.h"))
    answer = kernel_reference(tmp_path, RUN, 1, 1, 1, flags=FLAGS)
    source = kernel_source.read_compiled_set(output_path(tmp_path))
    assert answer.headers == source.headers
    assert [path.name for path in answer.headers] == [
        "a-1.h",
        "a.h",
        "a_1.h",
        "m.h",
        "z.h",
    ]


def test_an_attempt_without_headers_answers_no_header(tmp_path):
    make_attempt(tmp_path, names=("k.c",))
    answer = kernel_reference(tmp_path, RUN, 1, 1, 1, flags=FLAGS)
    assert answer.headers == () and type(answer.headers) is tuple


def test_the_flags_are_the_callers(tmp_path):
    make_attempt(tmp_path)
    standin = kernel_reference(tmp_path, RUN, 1, 1, 1, flags=standin_settings.FLAGS)
    assert standin.flags == standin_settings.FLAGS
    assert kernel_reference(tmp_path, RUN, 1, 1, 1, flags=()).flags == ()


def test_flags_have_no_default():
    with pytest.raises(TypeError):
        kernel_reference("root", RUN, 1, 1, 1)


def test_a_str_and_a_path_data_root_give_the_same_reference(tmp_path):
    make_attempt(tmp_path)
    by_path = kernel_reference(tmp_path, RUN, 1, 1, 1, flags=FLAGS)
    by_text = kernel_reference(str(tmp_path), RUN, 1, 1, 1, flags=FLAGS)
    assert by_path == by_text


def test_two_attempts_and_two_candidates_give_their_own_references(tmp_path):
    make_attempt(tmp_path, 2, 1, 1, names=("first.c",), contract="gemm_fp32")
    make_attempt(tmp_path, 2, 1, 2, names=("second.c",), contract="rmsnorm")
    make_attempt(tmp_path, 2, 2, 1, names=("third.c",), contract="sdpa")
    answers = {
        (candidate, attempt): kernel_reference(
            tmp_path, RUN, 2, candidate, attempt, flags=FLAGS
        )
        for candidate, attempt in ((1, 1), (1, 2), (2, 1))
    }
    assert answers[1, 1].sources == (output_path(tmp_path, 2, 1, 1) / "first.c",)
    assert answers[1, 2].sources == (output_path(tmp_path, 2, 1, 2) / "second.c",)
    assert answers[2, 1].sources == (output_path(tmp_path, 2, 2, 1) / "third.c",)
    for key, contract in (((1, 1), "gemm_fp32"), ((1, 2), "rmsnorm"), ((2, 1), "sdpa")):
        module, arguments = CONTRACT_ARGUMENTS[contract]
        assert answers[key].contract == as_parsed(module.task_contract(*arguments))


def test_several_compiled_files_keep_the_byte_order_of_names(tmp_path):
    names = ("z.c", "a_1.c", "a-1.c", "a.c", "a1.c", "m.h", "a.h")
    make_attempt(tmp_path, names=names)
    answer = kernel_reference(tmp_path, RUN, 1, 1, 1, flags=FLAGS)
    assert [path.name for path in answer.sources] == [
        "a-1.c",
        "a.c",
        "a1.c",
        "a_1.c",
        "z.c",
    ]


def test_no_attempt_directory(tmp_path):
    refused(tmp_path, NO_SPEC_FILE)


def test_no_spec_file(tmp_path):
    output = output_path(tmp_path)
    output.mkdir(parents=True)
    kernel_sources.write(output, "k.c")
    error = refused(tmp_path, NO_SPEC_FILE)
    assert isinstance(error.__cause__, FileNotFoundError)


def test_a_component_above_the_spec_that_is_a_file(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / RUN).write_bytes(b"")
    error = refused(tmp_path, NO_SPEC_FILE)
    assert isinstance(error.__cause__, (FileNotFoundError, NotADirectoryError))


def test_a_spec_that_is_a_directory_is_unreadable(tmp_path):
    spec_path(tmp_path).mkdir(parents=True)
    error = refused(tmp_path, SPEC_UNREADABLE)
    assert isinstance(error.__cause__, OSError)
    assert not isinstance(error.__cause__, (FileNotFoundError, NotADirectoryError))


@pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")
def test_an_unreadable_spec(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root reads a file of mode 0")
    make_attempt(tmp_path)
    path = spec_path(tmp_path)
    path.chmod(0)
    try:
        error = refused(tmp_path, SPEC_UNREADABLE)
    finally:
        path.chmod(0o644)
    assert isinstance(error.__cause__, PermissionError)


def test_a_failing_read_of_the_spec(tmp_path, monkeypatch):
    make_attempt(tmp_path)
    failure = OSError(5, "input/output error")

    def broken(*arguments, **keywords):
        raise failure

    monkeypatch.setattr(attempt_kernel, "open", broken, raising=False)
    error = refused(tmp_path, SPEC_UNREADABLE)
    assert error.__cause__ is failure


@pytest.mark.parametrize(
    "content",
    [b"", b"not json", b"[]", b"\xef\xbb\xbf{}", b'{"schema_version": 2}'],
)
def test_a_spec_that_parse_refuses(tmp_path, content):
    place_spec(tmp_path, content)
    error = refused(tmp_path, SPEC_INVALID)
    assert isinstance(error.__cause__, spec_file.InvalidSpecFileError)


def test_a_spec_with_a_broken_contract(tmp_path):
    made = document()
    del made["task"]["contract"]["prototype"]
    place_spec(tmp_path, content_of(made))
    refused(tmp_path, SPEC_INVALID)


@pytest.mark.parametrize("version", [1, 3])
def test_a_spec_of_another_version(tmp_path, version):
    made = document()
    made["schema_version"] = version
    place_spec(tmp_path, content_of(made))
    error = refused(tmp_path, SPEC_OTHER_VERSION)
    assert isinstance(error.__cause__, spec_file.UnsupportedVersionError)


@pytest.mark.parametrize(
    "named",
    [
        {"round": 2},
        {"candidate": 2},
        {"attempt": 2},
        {"run_id": "synthetic-run-2"},
    ],
)
def test_a_spec_whose_id_names_another_attempt(tmp_path, named):
    place_spec(tmp_path, content_of(document(**named)))
    error = refused(tmp_path, SPEC_OTHER_ATTEMPT)
    assert error.__cause__ is None


def test_a_spec_whose_run_id_has_no_path(tmp_path):
    place_spec(tmp_path, content_of(document(run_id="Synthetic Run")))
    error = refused(tmp_path, SPEC_OTHER_ATTEMPT)
    assert isinstance(error.__cause__, layout.InvalidPathValueError)


def test_no_output_directory(tmp_path):
    spec_file.write(tmp_path, content_of(document()))
    refused(tmp_path, NO_OUTPUT_DIRECTORY)


def test_an_output_with_no_admitted_compiled_file(tmp_path):
    make_attempt(tmp_path, names=("k.h", "K.c", "con.c", "k.cc", "k.txt"))
    refused(tmp_path, NO_COMPILED_FILE)


def test_an_output_that_is_a_symbolic_link(tmp_path):
    spec_file.write(tmp_path, content_of(document()))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    kernel_sources.write(elsewhere, "k.c")
    kernel_sources.symlink(output_path(tmp_path), elsewhere, directory=True)
    refused(tmp_path, NO_OUTPUT_DIRECTORY)


@pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")
def test_an_unreadable_output(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root lists a directory of mode 0")
    make_attempt(tmp_path)
    output = output_path(tmp_path)
    output.chmod(0)
    try:
        error = refused(tmp_path, OUTPUT_DIRECTORY_UNLISTABLE)
    finally:
        output.chmod(0o755)
    assert isinstance(error.__cause__, KernelSourceReadError)


@pytest.mark.parametrize(
    "failure",
    [
        ATTEMPT_DIRECTORY_UNLISTABLE,
        OUTPUT_DIRECTORY_UNLISTABLE,
        ENTRY_KIND_UNDETERMINED,
    ],
)
def test_every_reader_failure_is_wrapped(tmp_path, monkeypatch, failure):
    make_attempt(tmp_path)
    raised = KernelSourceReadError(failure)

    def failing(path):
        raise raised

    monkeypatch.setattr(kernel_source, "read_compiled_set", failing)
    error = refused(tmp_path, failure)
    assert error.__cause__ is raised


def test_an_attempt_directory_gone_after_the_spec_was_read(tmp_path, monkeypatch):
    make_attempt(tmp_path)
    asked = []

    def gone(path):
        asked.append(path)
        return KernelSource((), NO_ATTEMPT_DIRECTORY)

    monkeypatch.setattr(kernel_source, "read_compiled_set", gone)
    refused(tmp_path, NO_ATTEMPT_DIRECTORY)
    assert asked == [output_path(tmp_path)]


def test_the_spec_is_read_before_the_output(tmp_path, monkeypatch):
    place_spec(tmp_path, b"not json")
    monkeypatch.setattr(kernel_source, "read_compiled_set", pytest.fail)
    refused(tmp_path, SPEC_INVALID)


@pytest.mark.parametrize(
    ("arguments", "parameter", "kind"),
    [
        ((None, RUN, 1, 1, 1), "data_root", TypeError),
        ((b"root", RUN, 1, 1, 1), "data_root", TypeError),
        ((1, RUN, 1, 1, 1), "data_root", TypeError),
        (("ro\0ot", RUN, 1, 1, 1), "data_root", ValueError),
        (("root", None, 1, 1, 1), "run_id", ValueError),
        (("root", "Synthetic Run", 1, 1, 1), "run_id", ValueError),
        (("root", "", 1, 1, 1), "run_id", ValueError),
        (("root", RUN, "1", 1, 1), "round", ValueError),
        (("root", RUN, True, 1, 1), "round", ValueError),
        (("root", RUN, -1, 1, 1), "round", ValueError),
        (("root", RUN, 1.0, 1, 1), "round", ValueError),
        (("root", RUN, 2**53, 1, 1), "round", ValueError),
        (("root", RUN, 1, 0, 1), "candidate", ValueError),
        (("root", RUN, 1, -1, 1), "candidate", ValueError),
        (("root", RUN, 1, True, 1), "candidate", ValueError),
        (("root", RUN, 1, None, 1), "candidate", ValueError),
        (("root", RUN, 1, 1, 0), "attempt", ValueError),
        (("root", RUN, 1, 1, -2), "attempt", ValueError),
        (("root", RUN, 1, 1, False), "attempt", ValueError),
        (("root", RUN, 1, 1, "01"), "attempt", ValueError),
    ],
)
def test_a_malformed_argument(tmp_path, monkeypatch, arguments, parameter, kind):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(kind) as raised:
        kernel_reference(*arguments, flags=FLAGS)
    assert raised.value.parameter == parameter
    if kind is ValueError and parameter != "data_root":
        assert type(raised.value) is layout.InvalidPathValueError
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "flags", [None, "-O2", ("-O2", 2), ["-O2", b"-g"], {"-O2"}, iter(("-O2",))]
)
def test_malformed_flags(tmp_path, flags):
    make_attempt(tmp_path)
    before = tree(tmp_path)
    with pytest.raises(TypeError) as raised:
        kernel_reference(tmp_path, RUN, 1, 1, 1, flags=flags)
    assert raised.value.parameter == "flags"
    assert tree(tmp_path) == before


def test_flags_are_checked_before_anything_is_read(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel_source, "read_compiled_set", pytest.fail)
    with pytest.raises(TypeError) as raised:
        kernel_reference(tmp_path, RUN, 1, 1, 1, flags=None)
    assert raised.value.parameter == "flags"


def write_forward_attempts(root, header=None):
    for number, kind in enumerate(forward.KINDS, start=1):
        made = document(1, 1, number, contract=FORWARD_CONTRACT[kind])
        assert made["task"]["contract"] == forward_execute.CONTRACTS[kind]
        spec_file.write(root, content_of(made))
        output = output_path(root, 1, 1, number)
        output.mkdir()
        prelude = reference.REAL_PRELUDE
        if header is not None:
            (output / header).write_text(prelude, encoding="ascii", newline="\n")
            prelude = f'#include "{header}"\n'
        (output / f"{kind}.c").write_text(
            prelude + reference.REAL_SOURCES[kind],
            encoding="ascii",
            newline="\n",
        )


def attempt_binding(root):
    kernels = {
        kind: kernel_reference(root, RUN, 1, 1, number, flags=forward.KERNEL_FLAGS)
        for number, kind in enumerate(forward.KINDS, start=1)
    }
    return forward_execute.binding_of(kernels)


@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize(("seed", "prompt", "passes"), [(73, 3, 3), (76, 2, 4)])
def test_a_greedy_generation_whose_every_kernel_comes_from_an_attempt(
    clang,  # noqa: F811
    tmp_path,
    seed,
    prompt,
    passes,
    last,
):
    root = tmp_path / "data"
    root.mkdir()
    write_forward_attempts(root)
    binding = attempt_binding(root)
    sources = {
        entry.kernel.sources[0] for entries in binding.values() for entry in entries
    }
    assert len(sources) == len(forward.KINDS)
    assert all(path.parent.name == "output" for path in sources)
    model = reference.sharp_model(seed, prompt, passes)
    rows = "last" if last else "all"
    builds = tmp_path / "builds"
    builds.mkdir()
    result = model_forward_execute.execute(
        reference.DIMENSIONS,
        binding,
        **reference.arguments(model, lm_head_rows=rows, given=None),
        generation_length=model["G"],
        build_timeout_s=forward.BUILD_TIMEOUT,
        run_timeout_s=forward.RUN_TIMEOUT,
        program_flags=("-O2",),
        program_trailing_flags=("-ldl",),
        parent=builds,
    )
    assert result.check.ok, result.check.outcomes
    assert result.build_failed is None, result.build_failed
    assert result.run.failed is None, result.run.run.stderr
    report = result.run.report
    selected = [int(token) for token in report.tokens[prompt:]]
    assert len(set(selected)) > 1
    expected = reference_logits(
        reference.DIMENSIONS,
        **reference.arguments(model, given=selected, lm_head_rows=rows),
    )
    rtol, atol = reference.tolerance(expected)
    assert compare(report, expected, rtol=rtol, atol=atol).ok
    real = tmp_path / "real"
    real.mkdir()
    by_hand = reference.executed(real, model, rows, given=None)
    assert np.array_equal(report.tokens, by_hand.tokens)
    assert np.array_equal(report.logits, by_hand.logits)
