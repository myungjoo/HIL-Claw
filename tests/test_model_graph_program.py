import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import test_model_forward as forward
import test_model_forward_execute as execute_tests
import test_model_forward_run as forward_run

from hilclaw import model_build, model_graph
from hilclaw.local_run import run
from hilclaw.model_binding import BindingEntry, KernelReference

BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60
END = b"end\n"
LLAMA = model_graph.read(model_graph.LLAMA_GRAPH)
FEED_FORWARD = model_graph.read(
    Path(__file__).with_name("model_graph_feed_forward.json")
)
LLAMA_DIMENSIONS = {
    "D": forward.D,
    "F": forward.F,
    "V": forward.V,
    "N": forward.N,
    "H": forward.H,
    "H_kv": forward.H_KV,
    "d": forward.HEAD,
}
FF_DIMENSIONS = {"E": 6, "U": 10, "K": 7, "L": 3}
LIBRARY_OF_KIND = {
    "gemm": "gemm",
    "rmsnorm": "rmsnorm",
    "elementwise_add": "add",
    "swiglu": "swiglu",
    "rope": "rope",
    "sdpa_kv_cache": "sdpa",
}


def contract(kind):
    return execute_tests.CONTRACTS[LIBRARY_OF_KIND[kind]]


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("the graph program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("graph")
    programs = {}
    for name, function in (
        ("model_graph", model_build.build_graph_program),
        ("model_forward", model_build.build_forward_program),
    ):
        programs[name] = directory / name
        result = function(programs[name], timeout_s=BUILD_TIMEOUT, flags=("-O2",))
        assert result.ok, result.log
    libraries = {}

    def library(name):
        if name not in libraries:
            if name == "no_entry":
                text = "int other_entry(int x)\n{\n    return x + 1;\n}\n"
            else:
                text = forward.PRELUDE + "".join(forward.LIBRARIES[name])
            source = directory / f"{name}.c"
            source.write_text(text, encoding="ascii", newline="\n")
            output = directory / f"lib{name}.so"
            result = model_build.build_kernel_library(
                source, output, timeout_s=BUILD_TIMEOUT, flags=forward.KERNEL_FLAGS
            )
            assert result.ok, result.log
            libraries[name] = str(output)
        return libraries[name]

    return programs, library


def kernel(name, kind):
    return KernelReference((name,), contract(kind), ())


def binding_for(plan, choose):
    """``choose(site, kind, pass_index, shape)`` names the library of a call."""
    shapes = {}
    for p, one in enumerate(plan.passes):
        for step in one.steps:
            if isinstance(step, model_graph.KernelStep):
                name = choose(step.site, step.kind, p, step.shape)
                shapes.setdefault(step.site, {}).setdefault((name, step.kind), [])
                if step.shape not in shapes[step.site][(name, step.kind)]:
                    shapes[step.site][(name, step.kind)].append(step.shape)
    return {
        site: [BindingEntry(kernel(n, k), tuple(s)) for (n, k), s in by.items()]
        for site, by in shapes.items()
    }


def by_kind(site, kind, p, shape):
    return LIBRARY_OF_KIND[kind]


def one_library(site, kind, p, shape):
    return "all"


def per_pass(site, kind, p, shape):
    if site == "o" and p > 0:
        return "gemm_offset"
    return LIBRARY_OF_KIND[kind]


def llama_weights(model):
    weights = {"embedding": model["embedding"], "norm": model["norm"]}
    weights["lm_head"] = model["lm_head"]
    for layer, values in enumerate(model["layers"]):
        for name, array in values.items():
            weights[f"{name}[{layer}]"] = array
    return weights


def graph_input(plan, binding, weights, prompt, given, tables=None):
    check = model_graph.check_binding(plan, binding)
    assert check.ok, check.outcomes
    data = model_graph.encode(
        plan,
        check,
        scalars={"eps": float(forward.EPS)},
        tables={"rope": forward_run.ROPE} if tables is None else tables,
        weights=weights,
        prompt=prompt,
        given=given,
    )
    return data, [k.sources[0] for k in model_graph.libraries(check)]


def forward_table(plan, binding, names):
    check = model_graph.check_binding(plan, binding)
    bound = {(site, shape): k.sources[0] for site, shape, k in check.calls}
    table = {}
    for p, one in enumerate(plan.passes):
        for step in one.steps:
            if isinstance(step, model_graph.KernelStep):
                table[(step.site, p)] = names.index(bound[(step.site, step.shape)])
    return [table[(site, p)] for site in forward.SITES for p in range(len(plan.passes))]


def start(built, tmp_path, program, data, names):
    programs, library = built
    path = tmp_path / f"{program}.bin"
    path.write_bytes(data)
    return run(
        [programs[program], str(path), *(library(name) for name in names)],
        timeout_s=RUN_TIMEOUT,
    )


def llama_case(seed, last, generation, choose, S=3, G=3):
    model = forward_run.model_of(seed, prompt=S, given=G)
    plan = model_graph.resolve(
        LLAMA,
        LLAMA_DIMENSIONS,
        prompt_length=S,
        generation_length=G,
        lm_head_rows="last" if last else "all",
    )
    tokens = [int(t) for t in model["tokens"]]
    binding = binding_for(plan, choose)
    data, names = graph_input(
        plan,
        binding,
        llama_weights(model),
        tokens[:S],
        None if generation else tokens[S:],
    )
    return model, plan, binding, data, names


@pytest.mark.parametrize("generation", [False, True])
@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize("choose", [one_library, by_kind, per_pass])
def test_llama_graph_reports_equal_the_forward_program_byte_for_byte(
    built, tmp_path, generation, last, choose
):
    model, plan, binding, data, names = llama_case(21, last, generation, choose)
    table = forward_table(plan, binding, names)
    forward_data = forward.encode(model, table, last, generation=generation)
    graph = start(built, tmp_path, "model_graph", data, names)
    reference = start(built, tmp_path, "model_forward", forward_data, names)
    assert reference.returncode == 0, reference.stderr
    assert graph.returncode == 0, graph.stderr
    assert graph.stdout == reference.stdout
    assert graph.stderr == b""
    mode = "generation" if generation else "given"
    assert model_graph.parse_report(graph.stdout, plan, mode=mode) is not None


def test_the_per_pass_binding_changes_the_report(built, tmp_path):
    reports = []
    for choose in (by_kind, per_pass):
        _, _, _, data, names = llama_case(22, False, False, choose)
        result = start(built, tmp_path, "model_graph", data, names)
        assert result.returncode == 0, result.stderr
        reports.append(result.stdout)
    assert reports[0] != reports[1]
    assert "gemm_offset" in names


def test_a_longer_prompt_and_more_passes(built, tmp_path):
    model, plan, binding, data, names = llama_case(23, False, False, by_kind, S=5, G=4)
    table = forward_table(plan, binding, names)
    reference = start(
        built, tmp_path, "model_forward", forward.encode(model, table), names
    )
    graph = start(built, tmp_path, "model_graph", data, names)
    assert graph.returncode == 0, graph.stderr
    assert graph.stdout == reference.stdout


def ff_model(seed, S, G):
    generator = np.random.default_rng(seed)
    E, U, K, L = (FF_DIMENSIONS[n] for n in ("E", "U", "K", "L"))
    weights = {"embedding": forward.bf16_values(generator, (K, E))}
    for layer in range(L):
        weights[f"norm[{layer}]"] = forward.bf16_values(generator, (E,))
        weights[f"gate[{layer}]"] = forward.bf16_values(generator, (E, U))
        weights[f"up[{layer}]"] = forward.bf16_values(generator, (E, U))
        weights[f"down[{layer}]"] = forward.bf16_values(generator, (U, E))
    weights["final_norm"] = forward.bf16_values(generator, (E,))
    weights["head"] = forward.bf16_values(generator, (E, K))
    tokens = [int(t) for t in generator.integers(0, K, size=S + G)]
    return weights, tokens


def ff_recompute(weights, tokens, S, G, last, select):
    tokens = list(tokens)
    rows = []
    for p in range(G):
        T, P = (S, 0) if p == 0 else (1, S + p - 1)
        x = weights["embedding"][np.array(tokens[P : P + T], dtype=np.intp)]
        for layer in range(FF_DIMENSIONS["L"]):
            normed = forward.rmsnorm(x, weights[f"norm[{layer}]"], forward.EPS)
            gate = forward.gemm(normed, weights[f"gate[{layer}]"])
            up = forward.gemm(normed, weights[f"up[{layer}]"])
            act = forward.swiglu(gate, up)
            x = forward.add(x, forward.gemm(act, weights[f"down[{layer}]"]))
        normed = forward.rmsnorm(x, weights["final_norm"], forward.EPS)
        if last:
            normed = normed[-1:]
        rows.append(forward.gemm(normed, weights["head"]))
        if select:
            tokens[S + p] = forward.choose(rows[-1][-1])
    return np.concatenate(rows), tokens


@pytest.mark.parametrize("generation", [False, True])
@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize("choose", [one_library, by_kind])
def test_feed_forward_graph_equals_the_recomputation_bit_for_bit(
    built, tmp_path, generation, last, choose
):
    S, G = 4, 3
    weights, tokens = ff_model(31, S, G)
    plan = model_graph.resolve(
        FEED_FORWARD,
        FF_DIMENSIONS,
        prompt_length=S,
        generation_length=G,
        lm_head_rows="last" if last else "all",
    )
    data, names = graph_input(
        plan,
        binding_for(plan, choose),
        weights,
        tokens[:S],
        None if generation else tokens[S:],
        tables={},
    )
    result = start(built, tmp_path, "model_graph", data, names)
    assert result.returncode == 0, result.stderr
    logits, expected = ff_recompute(weights, tokens, S, G, last, generation)
    rows = G if last else S + G - 1
    assert logits.shape == (rows, FF_DIMENSIONS["K"])
    assert not np.any(logits == forward.NAN_BITS)
    report = model_graph.parse_report(
        result.stdout, plan, mode="generation" if generation else "given"
    )
    assert np.array_equal(report.logits, logits)
    assert [int(t) for t in report.tokens] == expected


def test_feed_forward_graph_has_no_attention():
    kinds = {
        step.kind
        for step in model_graph.resolve(
            FEED_FORWARD,
            FF_DIMENSIONS,
            prompt_length=2,
            generation_length=1,
            lm_head_rows="all",
        )
        .passes[0]
        .steps
        if isinstance(step, model_graph.KernelStep)
    }
    assert kinds == {"rmsnorm", "gemm", "swiglu", "elementwise_add"}
    assert set(FF_DIMENSIONS).isdisjoint(LLAMA_DIMENSIONS)


def header_size(plan):
    return 64 + 4 * len(plan.scalars) + 24 * len(plan.arrays) + 16 * len(plan.passes)


def step_word(plan, pass_index, site, word, nth=0):
    at = header_size(plan)
    for p, one in enumerate(plan.passes):
        for step in one.steps:
            if (
                p == pass_index
                and isinstance(step, model_graph.KernelStep)
                and step.site == site
            ):
                if nth == 0:
                    return at + 8 * word
                nth -= 1
            at += 160
    raise KeyError(site)


def token_word(plan, index):
    steps = sum(len(p.steps) for p in plan.passes)
    return header_size(plan) + 160 * steps + 8 * index


def patched(data, at, value):
    return data[:at] + np.array([value], dtype=np.uint64).tobytes() + data[at + 8 :]


def assert_failed(result, status, text):
    assert result.returncode == status, result.stderr
    assert result.stdout == b""
    assert result.stderr.startswith(b"model_graph: ")
    assert result.stderr.count(b"\n") == 1
    assert text in result.stderr


@pytest.fixture(scope="module")
def case():
    return llama_case(24, False, False, by_kind)


@pytest.mark.parametrize(
    ("change", "text"),
    [
        (lambda d: d[:-1], b"too short for the length its header gives"),
        (lambda d: d + b"\0", b"bytes follow the last array"),
        (lambda d: d[:20], b"too short for the header"),
    ],
)
def test_input_length_refusals(built, tmp_path, case, change, text):
    _, _, _, data, names = case
    assert_failed(start(built, tmp_path, "model_graph", change(data), names), 5, text)


def test_library_index_out_of_range(built, tmp_path, case):
    _, plan, _, data, names = case
    data = patched(data, step_word(plan, 2, "o", 1), len(names))
    result = start(built, tmp_path, "model_graph", data, names)
    assert_failed(result, 5, b"a library index is out of range")


def test_library_without_the_entry_point_at_a_decode_pass(built, tmp_path):
    def choose(site, kind, p, shape):
        return "no_entry" if site == "sdpa" and p == 2 else LIBRARY_OF_KIND[kind]

    _, _, _, data, names = llama_case(25, False, False, choose)
    result = start(built, tmp_path, "model_graph", data, names)
    assert result.returncode == 6, result.stderr
    assert result.stdout == b""
    assert b"has no hilclaw_sdpa_kv_cache_bf16" in result.stderr


@pytest.mark.parametrize(
    ("word", "value"),
    [(8, 10**9), (10, 2**63), (7, 999)],
)
def test_operand_offset_or_array_past_its_array(built, tmp_path, case, word, value):
    _, plan, _, data, names = case
    data = patched(data, step_word(plan, 1, "qkv", word), value)
    result = start(built, tmp_path, "model_graph", data, names)
    assert result.returncode == 5, result.stderr
    assert b"operand" in result.stderr


def test_a_shape_word_past_its_array(built, tmp_path, case):
    _, plan, _, data, names = case
    data = patched(data, step_word(plan, 0, "gate", 2), 100)
    result = start(built, tmp_path, "model_graph", data, names)
    assert_failed(result, 5, b"an operand range runs past its array")


def test_overlapping_operands(built, tmp_path, case):
    _, plan, _, data, names = case
    at = step_word(plan, 0, "attention_residual", 11)
    data = patched(data, at, int(np.frombuffer(data, np.uint64, 1, at - 32)[0]))
    result = start(built, tmp_path, "model_graph", data, names)
    assert_failed(result, 5, b"two operands of a step overlap")


@pytest.mark.parametrize(
    ("word", "value", "text"),
    [
        (0, 99, b"unknown op"),
        (2, 0, b"a shape word is 0"),
        (19, 5, b"a scalar index is out of range"),
    ],
)
def test_step_refusals(built, tmp_path, case, word, value, text):
    _, plan, _, data, names = case
    data = patched(data, step_word(plan, 0, "ffn_norm", word), value)
    assert_failed(start(built, tmp_path, "model_graph", data, names), 5, text)


def test_rope_with_an_odd_d(built, tmp_path, case):
    _, plan, _, data, names = case
    data = patched(data, step_word(plan, 0, "rope_q", 4), 3)
    result = start(built, tmp_path, "model_graph", data, names)
    assert_failed(result, 5, b"outside its kind's range")


@pytest.mark.parametrize("index", [0, 4])
def test_token_id_not_below_the_vocabulary(built, tmp_path, case, index):
    _, plan, _, data, names = case
    data = patched(data, token_word(plan, index), forward.V)
    result = start(built, tmp_path, "model_graph", data, names)
    assert_failed(result, 5, b"a token id is not below V")


@pytest.mark.parametrize(
    ("word", "value", "text"),
    [
        (0, 0, b"a header count is 0"),
        (5, 2, b"out of range"),
        (6, 10**6, b"out of range"),
    ],
)
def test_header_refusals(built, tmp_path, case, word, value, text):
    _, _, _, data, names = case
    data = patched(data, 8 * word, value)
    assert_failed(start(built, tmp_path, "model_graph", data, names), 5, text)


def test_a_size_that_cannot_be_held(built, tmp_path, case):
    _, _, _, data, names = case
    data = patched(data, 8, 2**62)
    assert_failed(start(built, tmp_path, "model_graph", data, names), 3, b"size")


def test_an_eps_that_is_not_above_zero(built, tmp_path, case):
    _, _, _, data, names = case
    data = data[:64] + np.array([-1.0], dtype=np.float32).tobytes() + data[68:]
    result = start(built, tmp_path, "model_graph", data, names)
    assert_failed(result, 5, b"a scalar is not finite or not above 0")


@pytest.mark.parametrize(
    ("script", "pass_index"), [("nan_prefill", 0), ("nan_decode", 1)]
)
def test_a_nan_in_the_selection_row(built, tmp_path, script, pass_index):
    def choose(site, kind, p, shape):
        return f"scripted_{script}" if site == "lm_head" else LIBRARY_OF_KIND[kind]

    _, _, _, data, names = llama_case(26, True, True, choose)
    result = start(built, tmp_path, "model_graph", data, names)
    assert result.returncode == 7, result.stderr
    assert f"pass {pass_index}: the selection row holds a NaN".encode() in result.stderr
    assert not result.stdout.endswith(END)


@pytest.mark.parametrize("count", [0, 1])
def test_wrong_argument_count(built, tmp_path, case, count):
    programs, _ = built
    path = tmp_path / "input.bin"
    path.write_bytes(case[3])
    result = run([programs["model_graph"], str(path)][: count + 1], timeout_s=30)
    assert_failed(result, 2, b"usage")


def test_input_that_is_a_directory(built, tmp_path, case):
    programs, library = built
    result = run([programs["model_graph"], str(tmp_path), library("all")], timeout_s=30)
    assert_failed(result, 5, b"is not a regular file")


def test_a_kernel_that_aborts_leaves_no_end_mark(built, tmp_path):
    def choose(site, kind, p, shape):
        return "swiglu_abort" if kind == "swiglu" else LIBRARY_OF_KIND[kind]

    _, _, _, data, names = llama_case(27, False, False, choose)
    result = start(built, tmp_path, "model_graph", data, names)
    assert result.returncode != 0
    assert not result.stdout.endswith(END)


def test_kernel_output_goes_to_standard_error(built, tmp_path):
    def choose(site, kind, p, shape):
        return "add_printing" if kind == "elementwise_add" else LIBRARY_OF_KIND[kind]

    _, _, _, data, names = llama_case(28, False, False, choose)
    result = start(built, tmp_path, "model_graph", data, names)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b"kernel says hello\n" * (2 * forward.N * 3)
    assert result.stdout.endswith(END)


def nth_step_word(plan, pass_index, k, word):
    before = sum(len(p.steps) for p in plan.passes[:pass_index])
    return header_size(plan) + 160 * (before + k) + 8 * word


def array_index(plan, name):
    return [a.name for a in plan.arrays].index(name)


def array_word(plan, name, word):
    return 64 + 4 * len(plan.scalars) + 24 * array_index(plan, name) + 8 * word


def pass_word(plan, pass_index, word):
    return (
        64 + 4 * len(plan.scalars) + 24 * len(plan.arrays) + 16 * pass_index + 8 * word
    )


def embed_weight_with_fewer_rows(plan):
    return nth_step_word(plan, 0, 0, 7), array_index(plan, "norm")


def embed_weight_at_an_offset(plan):
    return nth_step_word(plan, 0, 0, 8), 1


def embed_of_a_token_not_yet_known(plan):
    return nth_step_word(plan, 1, 0, 4), plan.passes[0].rows + 1


def embed_into_its_own_weight(plan):
    return nth_step_word(plan, 0, 0, 9), array_index(plan, "embedding")


def bf16_operand_on_the_table(plan):
    return step_word(plan, 0, "qkv", 9), array_index(plan, "rope")


def table_operand_on_a_bf16_array(plan):
    return step_word(plan, 0, "rope_q", 9), array_index(plan, "norm")


def sdpa_heads_not_a_multiple(plan):
    return step_word(plan, 0, "sdpa", 5), 3


def sdpa_l_below_m(plan):
    return step_word(plan, 0, "sdpa", 3), 1


def output_on_a_weight(plan):
    return 48, array_index(plan, "embedding")


def output_on_the_table(plan):
    return 48, array_index(plan, "rope")


def pass_without_output_rows(plan):
    return pass_word(plan, 1, 0), 0


def pass_rows_past_the_output(plan):
    return pass_word(plan, 0, 0), plan.passes[0].rows + 1


def pass_without_steps(plan):
    return pass_word(plan, 2, 1), 0


def array_of_no_elements(plan):
    return array_word(plan, "norm", 0), 0


def array_of_element_size_3(plan):
    return array_word(plan, "norm", 1), 3


def array_role_2(plan):
    return array_word(plan, "norm", 2), 2


def filled_array_of_4_byte_elements(plan):
    return array_word(plan, "x", 1), 4


@pytest.mark.parametrize(
    ("change", "text"),
    [
        (embed_weight_with_fewer_rows, b"an embed weight has fewer than V rows"),
        (embed_weight_at_an_offset, b"an embed weight has fewer than V rows"),
        (embed_of_a_token_not_yet_known, b"an embed reads a token not yet known"),
        (embed_into_its_own_weight, b"two operands of a step overlap"),
        (bf16_operand_on_the_table, b"an operand array has the wrong element size"),
        (table_operand_on_a_bf16_array, b"an operand array has the wrong element size"),
        (sdpa_heads_not_a_multiple, b"a shape is outside its kind's range"),
        (sdpa_l_below_m, b"a shape is outside its kind's range"),
        (output_on_a_weight, b"the output array is not a filled bf16 array"),
        (output_on_the_table, b"the output array is not a filled bf16 array"),
        (pass_without_output_rows, b"a pass has no steps or its output rows run"),
        (pass_rows_past_the_output, b"a pass has no steps or its output rows run"),
        (pass_without_steps, b"a pass has no steps or its output rows run"),
        (array_of_no_elements, b"an array record is out of range"),
        (array_of_element_size_3, b"an array record is out of range"),
        (array_role_2, b"an array record is out of range"),
        (filled_array_of_4_byte_elements, b"an array record is out of range"),
    ],
)
def test_refusals_that_keep_steps_inside_their_arrays(
    built, tmp_path, case, change, text
):
    _, plan, _, data, names = case
    at, value = change(plan)
    data = patched(data, at, value)
    assert_failed(start(built, tmp_path, "model_graph", data, names), 5, text)


def test_an_output_row_wider_than_the_vocabulary_when_generating(built, tmp_path):
    _, _, _, data, names = llama_case(29, False, True, by_kind)
    data = patched(data, 56, forward.V + 1)
    result = start(built, tmp_path, "model_graph", data, names)
    assert_failed(result, 5, b"the mode, the output array or its row width")


def test_the_same_change_in_the_given_mode_is_accepted_by_the_header(
    built, tmp_path, case
):
    _, _, _, data, names = case
    data = patched(data, 56, forward.V + 1)
    result = start(built, tmp_path, "model_graph", data, names)
    assert_failed(result, 5, b"a pass has no steps or its output rows run")
