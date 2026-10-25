from pathlib import Path

import numpy as np
import pytest
import test_model_forward as forward

from hilclaw import local_run
from hilclaw.local_run import RunResult
from hilclaw.model_binding import ModelDimensions
from hilclaw.model_forward_check import RopeConstants, Weights
from hilclaw.model_forward_run import (
    CALL_SITES,
    ForwardProgramResult,
    ForwardReport,
    encode_input,
    parse_report,
    run_forward_program,
)
from hilclaw.model_run import END_MARK, RunFailed
from hilclaw.rope_table import build

built = forward.built

DIMENSIONS = ModelDimensions(
    hidden=forward.D,
    intermediate=forward.F,
    vocabulary=forward.V,
    layers=forward.N,
    heads=forward.H,
    kv_heads=forward.H_KV,
    head_dim=forward.HEAD,
)
ROPE = RopeConstants(
    theta=10000.0,
    scale_factor=2.0,
    low_freq_factor=1.0,
    high_freq_factor=4.0,
    old_context_len=8,
)
EPS = 0.5
V = forward.V


def model_of(seed, prompt=3, given=3):
    model = forward.make_model(seed, prompt=prompt, given=given)
    model["rope"] = build(
        head_dim=forward.HEAD, positions=prompt + given - 1, **ROPE._asdict()
    )
    return model


def weights_of(model):
    layers = model["layers"]
    return Weights(
        embedding=model["embedding"],
        attention_norm=[layer["attention_norm"] for layer in layers],
        qkv=[layer["qkv"] for layer in layers],
        o=[layer["o"] for layer in layers],
        ffn_norm=[layer["ffn_norm"] for layer in layers],
        gate=[layer["gate"] for layer in layers],
        up=[layer["up"] for layer in layers],
        down=[layer["down"] for layer in layers],
        norm=model["norm"],
        lm_head=model["lm_head"],
    )


def libraries_of(passes, table=forward.SEPARATE_TABLE):
    return {site: [table[s]] * passes for s, site in enumerate(CALL_SITES)}


def arguments(model, **changes):
    tokens = [int(token) for token in model["tokens"]]
    values = {
        "eps": EPS,
        "rope": ROPE,
        "weights": weights_of(model),
        "prompt": tokens[: model["S"]],
        "given": tokens[model["S"] :],
        "lm_head_rows": "all",
        "libraries": libraries_of(model["G"]),
        "library_count": len(forward.SEPARATE),
    }
    values.update(changes)
    return values


def lengths(model, last=False):
    return {
        "prompt_length": model["S"],
        "generation_length": model["G"],
        "lm_head_rows": "last" if last else "all",
    }


def run_result(returncode=0, stdout=b"", timed_out=False):
    return RunResult(returncode, timed_out, stdout, b"err", ("x",), 0.25, 42)


def test_call_sites_are_in_the_order_of_the_program():
    assert CALL_SITES == forward.SITES


@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize("given", [1, 3])
def test_encode_input_writes_the_form_of_the_header_comment(last, given):
    model = model_of(21, given=given)
    rows = "last" if last else "all"
    data = encode_input(DIMENSIONS, **arguments(model, lm_head_rows=rows))
    table = forward.per_pass(forward.SEPARATE_TABLE, given)
    assert data == forward.encode(model, table, last)


def test_encode_input_orders_the_library_table_by_call_site_then_pass():
    model = model_of(22, given=2)
    libraries = {site: [s, 15 + s] for s, site in enumerate(CALL_SITES)}
    data = encode_input(
        DIMENSIONS, **arguments(model, libraries=libraries, library_count=30)
    )
    expected = [index for s in range(15) for index in (s, 15 + s)]
    assert data == forward.encode(model, expected)


def test_encode_input_converts_eps_to_its_nearest_binary32():
    model = model_of(23)
    data = encode_input(DIMENSIONS, **arguments(model, eps=1e-5))
    assert data[80:84] == np.array([1e-5], dtype=np.float32).tobytes()
    table = forward.per_pass(forward.SEPARATE_TABLE, 3)
    assert data == forward.encode(model, table, eps=np.float32(1e-5))


def test_encode_input_writes_arrays_in_row_major_order_whatever_their_memory_order():
    model = model_of(24)
    weights = weights_of(model)
    weights = weights._replace(
        embedding=np.asfortranarray(weights.embedding),
        qkv=[np.asfortranarray(array) for array in weights.qkv],
        lm_head=weights.lm_head.T.copy().T,
    )
    data = encode_input(DIMENSIONS, **arguments(model, weights=weights))
    assert data == encode_input(DIMENSIONS, **arguments(model))


def test_encode_input_accepts_tuples_and_leaves_its_arguments_unchanged():
    model = model_of(25)
    values = arguments(model)
    libraries = {site: tuple(indices) for site, indices in values["libraries"].items()}
    before = {site: indices for site, indices in libraries.items()}
    data = encode_input(
        DIMENSIONS,
        **{
            **values,
            "prompt": tuple(values["prompt"]),
            "given": tuple(values["given"]),
            "libraries": libraries,
        },
    )
    assert data == encode_input(DIMENSIONS, **values)
    assert libraries == before


def test_encode_input_refuses_the_generation_mode():
    with pytest.raises(ValueError, match="^given: is None"):
        encode_input(DIMENSIONS, **arguments(model_of(1), given=None))


@pytest.mark.parametrize("given", [7, "abc", b"ab", {1, 2}])
def test_encode_input_refuses_given_that_is_no_sequence(given):
    with pytest.raises(TypeError, match="^given: must be a sequence"):
        encode_input(DIMENSIONS, **arguments(model_of(1), given=given))


@pytest.mark.parametrize(
    ("changes", "text"),
    [
        ({"given": []}, "generation_length"),
        ({"prompt": []}, "prompt: is empty"),
        ({"prompt": [0, V]}, r"prompt\[1\]: token id"),
        ({"given": [0, 1, -1]}, r"given\[2\]: token id"),
        ({"eps": 0.0}, "eps: "),
        ({"eps": float("nan")}, "eps: "),
        ({"rope": ROPE._replace(theta=-1.0)}, "rope.theta: "),
        ({"rope": ROPE._replace(high_freq_factor=0.5)}, "rope.high_freq_factor: "),
        ({"lm_head_rows": "first"}, "lm_head_rows: "),
    ],
)
def test_encode_input_refuses_invalid_settings(changes, text):
    with pytest.raises(ValueError, match=text):
        encode_input(DIMENSIONS, **arguments(model_of(1), **changes))


def test_encode_input_joins_every_invalid_input_reason():
    values = arguments(model_of(1), eps=-1.0, prompt=[V])
    with pytest.raises(ValueError) as caught:
        encode_input(DIMENSIONS, **values)
    message = str(caught.value)
    assert message.startswith("eps: ")
    assert "; prompt[0]: token id" in message


@pytest.mark.parametrize(
    ("field", "change", "text"),
    [
        ("qkv", lambda w: [w[0], w[1][:, :-1]], r"weights.qkv\[1\]: has the shape"),
        (
            "embedding",
            lambda w: w.astype(np.float32),
            "weights.embedding: has the element",
        ),
        ("norm", lambda w: w.astype(">u2"), "weights.norm: has the element"),
        ("down", lambda w: w[:1], "weights.down: has 1 arrays"),
        ("lm_head", lambda w: w.T, "weights.lm_head: has the shape"),
    ],
)
def test_encode_input_refuses_wrong_weights(field, change, text):
    weights = weights_of(model_of(1))
    weights = weights._replace(**{field: change(getattr(weights, field))})
    with pytest.raises(ValueError, match=text):
        encode_input(DIMENSIONS, **arguments(model_of(1), weights=weights))


@pytest.mark.parametrize(
    ("changes", "parameter"),
    [
        ({"eps": 1}, "eps"),
        ({"rope": tuple(ROPE)}, "rope"),
        ({"rope": ROPE._replace(theta="1")}, "rope.theta"),
        ({"weights": {}}, "weights"),
        ({"prompt": "012"}, "prompt"),
        ({"prompt": [0, 1.0]}, "prompt"),
        ({"given": [True]}, "given"),
        ({"lm_head_rows": 1}, "lm_head_rows"),
    ],
)
def test_encode_input_passes_on_type_errors_of_the_check(changes, parameter):
    with pytest.raises(TypeError) as caught:
        encode_input(DIMENSIONS, **arguments(model_of(1), **changes))
    assert caught.value.parameter == parameter


def test_encode_input_refuses_a_weight_that_is_not_an_array():
    weights = weights_of(model_of(1))._replace(norm=[0] * forward.D)
    with pytest.raises(TypeError) as caught:
        encode_input(DIMENSIONS, **arguments(model_of(1), weights=weights))
    assert caught.value.parameter == "weights.norm"


@pytest.mark.parametrize(
    ("dimensions", "error"),
    [
        (tuple(DIMENSIONS), TypeError),
        (DIMENSIONS._replace(heads=3), ValueError),
        (DIMENSIONS._replace(head_dim=3), ValueError),
        (DIMENSIONS._replace(layers=0), ValueError),
    ],
)
def test_encode_input_refuses_wrong_dimensions(dimensions, error):
    with pytest.raises(error):
        encode_input(dimensions, **arguments(model_of(1)))


@pytest.mark.parametrize(
    ("changes", "error", "text"),
    [
        ({"library_count": True}, TypeError, "library_count: must be an int"),
        ({"library_count": 6.0}, TypeError, "library_count: must be an int"),
        ({"library_count": 0}, ValueError, "library_count: must be from 1"),
        ({"library_count": 2**64}, ValueError, "library_count: must be from 1"),
        ({"libraries": [0] * 15}, TypeError, "libraries: must be a mapping"),
        (
            {"libraries": {**libraries_of(3), "embedding": [0, 0, 0]}},
            ValueError,
            "libraries: key 'embedding' is not a call site",
        ),
        (
            {"libraries": {s: v for s, v in libraries_of(3).items() if s != "sdpa"}},
            ValueError,
            "libraries: no entry for the call site 'sdpa'",
        ),
        (
            {"libraries": {**libraries_of(3), "qkv": "000"}},
            TypeError,
            r"libraries\['qkv'\]: must be a sequence",
        ),
        (
            {"libraries": {**libraries_of(3), "o": 0}},
            TypeError,
            r"libraries\['o'\]: must be a sequence",
        ),
        (
            {"libraries": {**libraries_of(3), "rope_q": [4, 4]}},
            ValueError,
            r"libraries\['rope_q'\]: has 2 entries, not one per pass \(3\)",
        ),
        (
            {"libraries": {**libraries_of(3), "norm": [1, False, 1]}},
            TypeError,
            r"libraries\['norm'\]\[1\]: must be an int",
        ),
        (
            {"libraries": {**libraries_of(3), "norm": [1, 1, 1.0]}},
            TypeError,
            r"libraries\['norm'\]\[2\]: must be an int",
        ),
        (
            {"libraries": {**libraries_of(3), "up": [0, 6, 0]}},
            ValueError,
            r"libraries\['up'\]\[1\]: index 6 is outside 0 to 5",
        ),
        (
            {"libraries": {**libraries_of(3), "up": [-1, 0, 0]}},
            ValueError,
            r"libraries\['up'\]\[0\]: index -1 is outside 0 to 5",
        ),
    ],
)
def test_encode_input_refuses_a_wrong_library_table(changes, error, text):
    with pytest.raises(error, match=text):
        encode_input(DIMENSIONS, **arguments(model_of(1), **changes))


@pytest.mark.parametrize("last", [False, True])
def test_parse_report_reads_a_complete_report(last):
    model = model_of(31, prompt=2, given=4)
    rows = 4 if last else 5
    logits = np.arange(rows * V, dtype=np.uint16).reshape(rows, V)
    logits[0, 0] = forward.NAN_BITS
    result = parse_report(
        forward.report(model, logits), DIMENSIONS, **lengths(model, last)
    )
    assert isinstance(result, ForwardReport)
    assert result.tokens.dtype == np.uint64
    assert np.array_equal(result.tokens, model["tokens"])
    assert result.logits.dtype == np.uint16
    assert np.array_equal(result.logits, logits)
    assert result.tokens.flags.owndata and result.logits.flags.owndata


@pytest.mark.parametrize(
    "cut", [lambda r: r[:-1], lambda r: r[:-5] + END_MARK, lambda r: r + b"\0"]
)
def test_parse_report_refuses_a_report_of_another_length(cut):
    model = model_of(32)
    good = forward.report(model, np.zeros((5, V), dtype=np.uint16))
    assert parse_report(good, DIMENSIONS, **lengths(model)) is not None
    assert parse_report(cut(good), DIMENSIONS, **lengths(model)) is None


def test_parse_report_refuses_a_report_without_the_end_mark():
    model = model_of(33)
    good = forward.report(model, np.zeros((3, V), dtype=np.uint16))
    assert parse_report(good, DIMENSIONS, **lengths(model, True)) is not None
    bad = good[:-4] + b"end\0"
    assert parse_report(bad, DIMENSIONS, **lengths(model, True)) is None
    assert parse_report(b"", DIMENSIONS, **lengths(model, True)) is None


@pytest.mark.parametrize("report", [bytearray(b"end\n"), memoryview(b"end\n"), "end"])
def test_parse_report_refuses_a_report_that_is_not_bytes(report):
    with pytest.raises(TypeError, match="^report: must be bytes"):
        parse_report(report, DIMENSIONS, **lengths(model_of(1)))


@pytest.mark.parametrize(
    ("dimensions", "changes", "error", "parameter"),
    [
        (DIMENSIONS, {"prompt_length": 0}, ValueError, "prompt_length"),
        (DIMENSIONS, {"generation_length": True}, TypeError, "generation_length"),
        (DIMENSIONS, {"lm_head_rows": "first"}, ValueError, "lm_head_rows"),
        (DIMENSIONS, {"lm_head_rows": None}, TypeError, "lm_head_rows"),
        (tuple(DIMENSIONS), {}, TypeError, "dimensions"),
    ],
)
def test_parse_report_refuses_wrong_arguments(dimensions, changes, error, parameter):
    with pytest.raises(error) as caught:
        parse_report(b"end\n", dimensions, **{**lengths(model_of(1)), **changes})
    assert caught.value.parameter == parameter


@pytest.fixture
def recorder(monkeypatch):
    def install(result):
        calls = []

        def recording(command, **keywords):
            calls.append((command, keywords))
            return result

        monkeypatch.setattr(local_run, "run", recording)
        return calls

    return install


def test_run_forward_program_hands_over_the_command_and_parses_the_report(recorder):
    model = model_of(41)
    logits = np.ones((5, V), dtype=np.uint16)
    calls = recorder(run_result(stdout=forward.report(model, logits)))
    result = run_forward_program(
        ["env", Path("prog")],
        Path("in.bin"),
        ["a.so", Path("b.so")],
        dimensions=DIMENSIONS,
        timeout_s=9,
        cwd="here",
        env={"A": "1"},
        **lengths(model),
    )
    assert isinstance(result, ForwardProgramResult)
    assert result.failed is None
    assert np.array_equal(result.report.tokens, model["tokens"])
    assert np.array_equal(result.report.logits, logits)
    assert result.run == run_result()
    assert calls == [
        (
            ("env", "prog", "in.bin", "a.so", "b.so"),
            {"timeout_s": 9, "cwd": "here", "env": {"A": "1"}},
        )
    ]


@pytest.mark.parametrize(
    ("result", "failed"),
    [
        (
            run_result(returncode=None, timed_out=True, stdout=b"end\n"),
            RunFailed.TIMEOUT,
        ),
        (run_result(returncode=5), RunFailed.EXIT_STATUS),
        (run_result(returncode=-6), RunFailed.EXIT_STATUS),
        (run_result(stdout=b"end\n"), RunFailed.REPORT_FORM),
    ],
)
def test_run_forward_program_names_the_failed_condition(recorder, result, failed):
    recorder(result)
    outcome = run_forward_program(
        "prog",
        "in.bin",
        ["a.so"],
        dimensions=DIMENSIONS,
        timeout_s=1,
        **lengths(model_of(1)),
    )
    assert outcome.failed is failed
    assert outcome.report is None
    assert outcome.run.stdout == b""


@pytest.mark.parametrize(
    ("program", "input_file", "libraries", "error", "text"),
    [
        (b"prog", "in", ["a"], TypeError, "program: must be a path or a sequence"),
        (7, "in", ["a"], TypeError, "program: must be a path or a sequence"),
        ([], "in", ["a"], ValueError, "program: command prefix is empty"),
        (["env", 3], "in", ["a"], TypeError, r"program\[1\]: must be str"),
        ("prog", b"in", ["a"], TypeError, "input_file: a bytes path"),
        ("prog", "in", "a.so", TypeError, "libraries: must be a sequence"),
        ("prog", "in", [], ValueError, "libraries: no library"),
        ("prog", "in", ["a", None], TypeError, r"libraries\[1\]: must be str"),
    ],
)
def test_run_forward_program_refuses_wrong_paths(
    recorder, program, input_file, libraries, error, text
):
    calls = recorder(run_result())
    with pytest.raises(error, match=text):
        run_forward_program(
            program,
            input_file,
            libraries,
            dimensions=DIMENSIONS,
            timeout_s=1,
            **lengths(model_of(1)),
        )
    assert calls == []


def test_run_forward_program_checks_the_lengths_before_starting(recorder):
    calls = recorder(run_result())
    with pytest.raises(ValueError):
        run_forward_program(
            "prog",
            "in",
            ["a"],
            dimensions=DIMENSIONS,
            timeout_s=1,
            prompt_length=0,
            generation_length=1,
            lm_head_rows="all",
        )
    assert calls == []


def start(
    built, tmp_path, data, names, model, last=False, timeout_s=forward.RUN_TIMEOUT
):
    program, library = built
    path = tmp_path / "input.bin"
    path.write_bytes(data)
    return run_forward_program(
        program,
        path,
        [library(name) for name in names],
        dimensions=DIMENSIONS,
        timeout_s=timeout_s,
        **lengths(model, last),
    )


@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize(("seed", "prompt", "given"), [(51, 3, 3), (52, 2, 5)])
def test_a_generation_equals_the_recomputation_bit_for_bit(
    built, tmp_path, last, seed, prompt, given
):
    model = model_of(seed, prompt=prompt, given=given)
    rows = "last" if last else "all"
    data = encode_input(DIMENSIONS, **arguments(model, lm_head_rows=rows))
    result = start(built, tmp_path, data, forward.SEPARATE, model, last)
    assert result.failed is None, result.run.stderr
    expected = forward.generate(model, last)
    assert not np.any(expected == forward.NAN_BITS)
    assert np.array_equal(result.report.tokens, model["tokens"])
    assert np.array_equal(result.report.logits, expected)
    assert result.run.stderr == b""


def test_one_library_for_every_call_site_and_pass(built, tmp_path):
    model = model_of(53)
    libraries = {site: [0, 0, 0] for site in CALL_SITES}
    data = encode_input(
        DIMENSIONS, **arguments(model, libraries=libraries, library_count=1)
    )
    result = start(built, tmp_path, data, ["all"], model)
    assert result.failed is None, result.run.stderr
    assert np.array_equal(result.report.logits, forward.generate(model))


def test_a_run_that_times_out(built, tmp_path):
    _, library = built
    path = tmp_path / "input.bin"
    path.write_bytes(b"")
    result = run_forward_program(
        ["/bin/sh", "-c", "sleep 30", "sh"],
        path,
        [library("all")],
        dimensions=DIMENSIONS,
        timeout_s=0.5,
        **lengths(model_of(1)),
    )
    assert result.failed is RunFailed.TIMEOUT
    assert result.report is None


def test_a_run_with_a_non_zero_exit_status(built, tmp_path):
    model = model_of(54)
    data = encode_input(DIMENSIONS, **arguments(model))
    result = start(built, tmp_path, data[:-1], forward.SEPARATE, model)
    assert result.failed is RunFailed.EXIT_STATUS
    assert result.run.returncode == 5
    assert b"too short for the length" in result.run.stderr


def test_a_kernel_that_aborts(built, tmp_path):
    model = model_of(55)
    libraries = libraries_of(3)
    libraries["ffn_activation"] = [6, 6, 6]
    data = encode_input(
        DIMENSIONS, **arguments(model, libraries=libraries, library_count=7)
    )
    names = [*forward.SEPARATE, "swiglu_abort"]
    result = start(built, tmp_path, data, names, model)
    assert result.failed is RunFailed.EXIT_STATUS
    assert result.run.returncode != 0
    assert result.run.stdout == b""


def test_a_run_whose_report_is_incomplete(built, tmp_path):
    _, library = built
    path = tmp_path / "input.bin"
    path.write_bytes(b"")
    result = run_forward_program(
        ["/bin/sh", "-c", "printf 'end\\n'", "sh"],
        path,
        [library("all")],
        dimensions=DIMENSIONS,
        timeout_s=forward.RUN_TIMEOUT,
        **lengths(model_of(1)),
    )
    assert result.failed is RunFailed.REPORT_FORM
    assert result.run.returncode == 0
