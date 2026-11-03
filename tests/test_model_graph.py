import copy
import json

import pytest

from hilclaw import model_binding, model_forward_run, model_graph
from hilclaw.keys import MAX_INTEGER
from hilclaw.model_binding import ModelDimensions
from hilclaw.model_graph import (
    REASONS,
    CopyStep,
    EmbedStep,
    GraphFileError,
    KernelStep,
    Operand,
    read,
    read_text,
    resolve,
)

LLAMA_TEXT = model_graph.LLAMA_GRAPH.read_text(encoding="utf-8")
LLAMA = read(model_graph.LLAMA_GRAPH)
DIMENSION_SETS = (
    {"D": 8, "F": 12, "V": 10, "N": 2, "H": 4, "H_kv": 2, "d": 2},
    {"D": 6, "F": 5, "V": 7, "N": 3, "H": 6, "H_kv": 3, "d": 4},
    {"D": 4, "F": 9, "V": 11, "N": 2, "H": 8, "H_kv": 2, "d": 2},
)
LENGTHS = ((2, 3), (3, 4), (5, 3))


def model_dimensions(dims):
    return ModelDimensions(
        dims["D"], dims["F"], dims["V"], dims["N"], dims["H"], dims["H_kv"], dims["d"]
    )


def kernel(site, kind, shape, operands, scalars=()):
    return KernelStep(
        site, kind, shape, tuple(Operand(*o) for o in operands), tuple(scalars)
    )


def run_pass(dims, S, k, last):
    """The calls of run_pass in model_forward.c, written from its expressions."""
    D, F, V, N, H, H_kv, d = (dims[n] for n in ("D", "F", "V", "N", "H", "H_kv", "d"))
    W, Hd, KVd = (H + 2 * H_kv) * d, H * d, H_kv * d
    T, P = (S, 0) if k == 0 else (1, S + k - 1)
    eps = (("eps", "eps"),)
    steps = [EmbedStep("embedding", "x", T, D, P)]
    for layer in range(N):

        def w(name, layer=layer):
            return f"{name}[{layer}]"

        steps += [
            kernel(
                "attention_norm",
                "rmsnorm",
                (T, D),
                [("x", "x", 0), ("w", w("attention_norm"), 0), ("y", "normed", 0)],
                eps,
            ),
            kernel(
                "qkv",
                "gemm",
                (T, D, W),
                [("a", "normed", 0), ("b", w("qkv"), 0), ("c", "qkv_out", 0)],
            ),
            CopyStep("qkv_out", W, 0, "q_in", Hd, Hd, T),
            CopyStep("qkv_out", W, Hd, "k_in", KVd, KVd, T),
            CopyStep("qkv_out", W, Hd + KVd, "v_in", KVd, KVd, T),
            kernel(
                "rope_q",
                "rope",
                (T, H, d),
                [("x", "q_in", 0), ("freqs_cis", "rope", P * d), ("out", "q_rot", 0)],
            ),
            kernel(
                "rope_k",
                "rope",
                (T, H_kv, d),
                [("x", "k_in", 0), ("freqs_cis", "rope", P * d), ("out", "k_rot", 0)],
            ),
            kernel(
                "sdpa",
                "sdpa_kv_cache",
                (T, P + T, H, H_kv, d),
                [
                    ("q", "q_rot", 0),
                    ("k_new", "k_rot", 0),
                    ("v_new", "v_in", 0),
                    ("cache_k", w("cache_k"), 0),
                    ("cache_v", w("cache_v"), 0),
                    ("out", "attn", 0),
                ],
            ),
            kernel(
                "o",
                "gemm",
                (T, Hd, D),
                [("a", "attn", 0), ("b", w("o"), 0), ("c", "o_out", 0)],
            ),
            kernel(
                "attention_residual",
                "elementwise_add",
                (T, D),
                [("a", "x", 0), ("b", "o_out", 0), ("c", "h", 0)],
            ),
            kernel(
                "ffn_norm",
                "rmsnorm",
                (T, D),
                [("x", "h", 0), ("w", w("ffn_norm"), 0), ("y", "normed", 0)],
                eps,
            ),
            kernel(
                "gate",
                "gemm",
                (T, D, F),
                [("a", "normed", 0), ("b", w("gate"), 0), ("c", "gate_out", 0)],
            ),
            kernel(
                "up",
                "gemm",
                (T, D, F),
                [("a", "normed", 0), ("b", w("up"), 0), ("c", "up_out", 0)],
            ),
            kernel(
                "ffn_activation",
                "swiglu",
                (T, F),
                [("gate", "gate_out", 0), ("up", "up_out", 0), ("out", "act", 0)],
            ),
            kernel(
                "down",
                "gemm",
                (T, F, D),
                [("a", "act", 0), ("b", w("down"), 0), ("c", "down_out", 0)],
            ),
            kernel(
                "ffn_residual",
                "elementwise_add",
                (T, D),
                [("a", "h", 0), ("b", "down_out", 0), ("c", "x", 0)],
            ),
        ]
    steps.append(
        kernel(
            "norm",
            "rmsnorm",
            (T, D),
            [("x", "x", 0), ("w", "norm", 0), ("y", "normed", 0)],
            eps,
        )
    )
    m, start = (1, (T - 1) * D) if last else (T, 0)
    steps.append(
        kernel(
            "lm_head",
            "gemm",
            (m, D, V),
            [("a", "normed", start), ("b", "lm_head", 0), ("c", "logits", 0)],
        )
    )
    return steps


def binding_shape(dims, step, T, P):
    md = model_dimensions(dims)
    site = step.site
    if site in model_binding.CALL_SITES:
        return model_binding.gemm_shape(md, site, step.shape[0])
    if site in model_binding.RMSNORM_CALL_SITES:
        return model_binding.rmsnorm_shape(md, site, T)
    if site in model_binding.ELEMENTWISE_ADD_CALL_SITES:
        return model_binding.elementwise_add_shape(md, site, T)
    if site in model_binding.SWIGLU_CALL_SITES:
        return model_binding.swiglu_shape(md, site, T)
    if site in model_binding.ROPE_CALL_SITES:
        return model_binding.rope_shape(md, site, T)
    return model_binding.sdpa_shape(md, site, T, P + T)


def expected_elements(dims, S, G, last):
    """Element counts of read_inputs, read_weights and allocate_activations."""
    D, F, V, N, H, H_kv, d = (dims[n] for n in ("D", "F", "V", "N", "H", "H_kv", "d"))
    W, Hd, KVd, C = (H + 2 * H_kv) * d, H * d, H_kv * d, S + G - 1
    counts = {"embedding": V * D, "norm": D, "lm_head": D * V, "rope": C * d}
    for layer in range(N):
        per = {
            "attention_norm": D,
            "qkv": D * W,
            "o": Hd * D,
            "ffn_norm": D,
            "gate": D * F,
            "up": D * F,
            "down": F * D,
            "cache_k": C * KVd,
            "cache_v": C * KVd,
        }
        counts.update({f"{name}[{layer}]": n for name, n in per.items()})
    widths = {"x": D, "h": D, "normed": D, "qkv_out": W, "q_in": Hd, "k_in": KVd}
    widths |= {"v_in": KVd, "q_rot": Hd, "k_rot": KVd, "attn": Hd, "o_out": D}
    widths |= {"gate_out": F, "up_out": F, "act": F, "down_out": D}
    counts.update({name: S * width for name, width in widths.items()})
    counts["logits"] = (1 if last else S) * V
    return counts


@pytest.mark.parametrize("dims", DIMENSION_SETS)
@pytest.mark.parametrize("lengths", LENGTHS)
@pytest.mark.parametrize("lm_head_rows", ("all", "last"))
def test_llama_file_is_run_pass(dims, lengths, lm_head_rows):
    S, G = lengths
    last = lm_head_rows == "last"
    plan = resolve(
        LLAMA,
        dims,
        prompt_length=S,
        generation_length=G,
        lm_head_rows=lm_head_rows,
    )
    assert len(plan.passes) == G
    for k, one in enumerate(plan.passes):
        T, P = (S, 0) if k == 0 else (1, S + k - 1)
        assert (one.rows, one.position, one.output_rows) == (T, P, 1 if last else T)
        assert list(one.steps) == run_pass(dims, S, k, last)
        kernels = [s for s in one.steps if isinstance(s, KernelStep)]
        assert len(kernels) == 13 * dims["N"] + 2
        for step in kernels:
            assert step.shape == binding_shape(dims, step, T, P)
    elements = {a.name: a.elements for a in plan.arrays}
    assert elements == expected_elements(dims, S, G, last)
    kinds = {a.name: (a.kind, a.dtype, a.source) for a in plan.arrays}
    assert kinds["rope"] == ("table", "fp32", "rope")
    assert kinds["cache_k[1]"] == ("state", "bf16", None)
    assert kinds["qkv[0]"] == ("weight", "bf16", None)
    assert kinds["logits"] == ("buffer", "bf16", None)
    assert plan.scalars == ("eps",)
    assert plan.output == "logits"


def test_llama_sites_are_the_call_sites_of_the_forward_program():
    plan = resolve(
        LLAMA,
        DIMENSION_SETS[0],
        prompt_length=2,
        generation_length=2,
        lm_head_rows="all",
    )
    sites = {s.site for s in plan.passes[0].steps if isinstance(s, KernelStep)}
    assert sites == set(model_forward_run.CALL_SITES)


def test_read_from_path_text_and_bytes_agree(tmp_path):
    path = tmp_path / "graph.json"
    path.write_bytes(LLAMA_TEXT.encode("utf-8"))
    assert read(path) == read(str(path)) == read_text(LLAMA_TEXT) == LLAMA
    assert read_text(LLAMA_TEXT.encode("utf-8")) == LLAMA


def test_graph_is_immutable():
    assert isinstance(LLAMA.nodes, tuple)
    assert LLAMA.dimensions == ("D", "F", "V", "N", "H", "H_kv", "d")
    with pytest.raises(AttributeError):
        LLAMA.nodes = ()
    repeat = LLAMA.nodes[1]
    assert isinstance(repeat, model_graph.Repeat)
    assert (repeat.count, repeat.index) == ("N", "layer")
    assert repeat.nodes[0].operands[1][1] == model_graph.Reference(
        "attention_norm", "layer", None
    )
    lm_head = LLAMA.nodes[-1]
    assert lm_head.operands[0][1].start.text == "(T-R)*D"


def graph_of(buffers, nodes, dimensions=("A", "B")):
    return {
        "graph_format": 1,
        "dimensions": list(dimensions),
        "weights": [],
        "tables": [],
        "scalars": [],
        "state": [],
        "buffers": buffers,
        "nodes": nodes,
        "output": {"buffer": buffers[-1]["name"], "rows": "T"},
    }


def add(site, a, b, c, n="1"):
    return {
        "op": "kernel",
        "site": site,
        "kind": "elementwise_add",
        "shape": {"m": "1", "n": n},
        "operands": {"a": a, "b": b, "c": c},
    }


@pytest.mark.parametrize(
    ("text", "value"),
    (
        ("A+B*2", 3 + 5 * 2),
        ("(A+B)*2", (3 + 5) * 2),
        ("A*B-A*2", 3 * 5 - 3 * 2),
        ("A-(B-A)", 3 - (5 - 3)),
        ("A - B + 4", 3 - 5 + 4),
        ("((A))*(B+1)*2", 3 * 6 * 2),
        ("10-A-B", 10 - 3 - 5),
    ),
)
def test_expression_precedence_and_parentheses(text, value):
    buffers = [{"name": "a", "shape": [text]}, {"name": "b", "shape": ["1"]}]
    buffers.append({"name": "c", "shape": ["1"]})
    graph = read_text(json.dumps(graph_of(buffers, [add("s", "b", "a", "c")])))
    plan = resolve(
        graph,
        {"A": 3, "B": 5},
        prompt_length=1,
        generation_length=1,
        lm_head_rows="all",
    )
    assert plan.arrays[0].elements == value


def test_nested_repeat_with_index():
    document = graph_of(
        [{"name": "c", "shape": ["T"]}],
        [
            {
                "op": "repeat",
                "count": "A",
                "index": "i",
                "nodes": [
                    {
                        "op": "repeat",
                        "count": "B",
                        "index": "j",
                        "nodes": [add("s", "p{i}", "q{j}", "c")],
                    }
                ],
            }
        ],
    )
    document["weights"] = [
        {"name": "p", "shape": ["1"], "per": "A"},
        {"name": "q", "shape": ["1"], "per": "B"},
    ]
    plan = resolve(
        read_text(json.dumps(document)),
        {"A": 2, "B": 3},
        prompt_length=1,
        generation_length=2,
        lm_head_rows="last",
    )
    for one in plan.passes:
        assert [(s.operands[0].array, s.operands[1].array) for s in one.steps] == [
            (f"p[{i}]", f"q[{j}]") for i in range(2) for j in range(3)
        ]
    assert [a.name for a in plan.arrays] == [
        "p[0]",
        "p[1]",
        "q[0]",
        "q[1]",
        "q[2]",
        "c",
    ]


def llama_document():
    return json.loads(LLAMA_TEXT)


def layer(doc):
    return doc["nodes"][1]["nodes"]


def node(doc, site):
    for item in layer(doc) + doc["nodes"]:
        if item.get("site") == site:
            return item
    raise AssertionError(site)


def change(function):
    def make():
        doc = llama_document()
        function(doc)
        return json.dumps(doc)

    return make


def text(value):
    return lambda: value


def setter(path, value):
    def apply(doc):
        target = doc
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return change(apply)


def site_member(site, member, value):
    return change(lambda doc: node(doc, site).__setitem__(member, value))


def operand(site, name, value):
    return change(lambda doc: node(doc, site)["operands"].__setitem__(name, value))


def shape_member(site, name, value):
    return change(lambda doc: node(doc, site)["shape"].__setitem__(name, value))


READ_REFUSALS = (
    ("malformed", text("{")),
    ("malformed", text(b"\xef\xbb\xbf" + LLAMA_TEXT.encode("utf-8"))),
    ("malformed", text(b"\xff" + LLAMA_TEXT.encode("utf-8"))),
    ("malformed", text(LLAMA_TEXT.replace('"output"', '"graph_format": 1, "output"'))),
    ("malformed", text(LLAMA_TEXT.replace('"graph_format": 1', '"graph_format": NaN'))),
    ("malformed", text(LLAMA_TEXT.replace('"graph_format": 1', '"graph_format": -0'))),
    ("malformed", text("[" * 100000)),
    ("not_object", text("[]")),
    ("missing_member", change(lambda doc: doc.pop("output"))),
    ("missing_member", change(lambda doc: layer(doc)[0].pop("op"))),
    ("missing_member", change(lambda doc: node(doc, "qkv").pop("site"))),
    ("missing_member", change(lambda doc: doc["output"].pop("rows"))),
    ("missing_member", change(lambda doc: doc["weights"][0].pop("per"))),
    ("unknown_member", setter(["extra"], 1)),
    ("unknown_member", site_member("qkv", "fused", True)),
    ("unknown_member", setter(["buffers", 0, "per"], None)),
    ("unknown_member", operand("lm_head", "a", {"of": "normed", "start": "0", "x": 1})),
    ("wrong_type", setter(["dimensions"], "D")),
    ("wrong_type", setter(["buffers", 0, "shape"], [])),
    ("wrong_type", setter(["buffers", 0, "shape"], [2])),
    ("wrong_type", setter(["buffers", 0, "name"], "1x")),
    ("wrong_type", setter(["buffers", 0], ["x"])),
    ("wrong_type", setter(["nodes"], [])),
    ("wrong_type", setter(["nodes", 1, "nodes", 0], "kernel")),
    ("wrong_type", operand("qkv", "a", 3)),
    ("wrong_type", operand("qkv", "a", "normed{")),
    ("wrong_type", setter(["nodes", 0, "out"], {"of": "x", "start": "0"})),
    ("wrong_type", site_member("qkv", "shape", ["T", "D", "F"])),
    ("wrong_type", site_member("qkv", "site", "qkv site")),
    ("bad_format", setter(["graph_format"], 2)),
    ("bad_format", setter(["graph_format"], True)),
    ("bad_format", setter(["graph_format"], "1")),
    ("bad_expression", shape_member("qkv", "n", "D/2")),
    ("bad_expression", shape_member("qkv", "n", "Q")),
    ("bad_expression", shape_member("qkv", "n", "")),
    ("bad_expression", shape_member("qkv", "n", "D+" * 200 + "D")),
    ("bad_expression", shape_member("qkv", "n", "(D")),
    ("bad_expression", shape_member("qkv", "n", "D)")),
    ("bad_expression", shape_member("qkv", "n", "D+")),
    ("bad_expression", shape_member("qkv", "n", "D D")),
    ("bad_expression", shape_member("qkv", "n", "-D")),
    ("bad_expression", shape_member("qkv", "n", "eps")),
    ("bad_expression", setter(["buffers", 0, "shape", 0], "P")),
    ("bad_expression", setter(["weights", 0, "shape", 0], "C")),
    ("bad_expression", setter(["state", 0, "shape", 0], "T")),
    ("bad_expression", setter(["output", "rows"], "layer")),
    ("duplicate_name", setter(["dimensions", 1], "D")),
    ("duplicate_name", setter(["buffers", 0, "name"], "eps")),
    ("duplicate_name", setter(["dimensions", 0], "T")),
    ("duplicate_name", setter(["state", 1, "name"], "cache_k")),
    ("duplicate_name", setter(["nodes", 1, "index"], "x")),
    ("duplicate_name", setter(["nodes", 1, "index"], "C")),
    (
        "duplicate_name",
        change(
            lambda doc: doc["nodes"][1].__setitem__(
                "nodes",
                [{"op": "repeat", "count": "N", "index": "layer", "nodes": layer(doc)}],
            )
        ),
    ),
    ("undeclared_name", operand("qkv", "a", "nothing")),
    ("undeclared_name", operand("qkv", "a", "D")),
    ("undeclared_name", setter(["weights", 1, "per"], "Z")),
    ("undeclared_name", setter(["weights", 1, "per"], ["N"])),
    ("undeclared_name", setter(["nodes", 2, "scalars", "eps"], "nope")),
    ("undeclared_name", setter(["nodes", 2, "scalars", "eps"], "D")),
    ("undeclared_name", setter(["nodes", 0, "weight"], "x")),
    ("undeclared_name", setter(["nodes", 1, "nodes", 2, "from"], "rope")),
    ("unknown_op", setter(["nodes", 1, "nodes", 0, "op"], "fuse")),
    ("unknown_op", setter(["nodes", 1, "nodes", 0, "op"], 3)),
    ("duplicate_site", site_member("o", "site", "qkv")),
    ("duplicate_site", site_member("lm_head", "site", "attention_norm")),
    ("bad_index", operand("qkv", "b", "qkv")),
    ("bad_index", operand("lm_head", "b", "lm_head{layer}")),
    ("bad_index", operand("norm", "w", "attention_norm{layer}")),
    ("bad_index", operand("qkv", "b", "qkv{other}")),
    ("bad_index", setter(["nodes", 1, "count"], "H")),
    ("bad_repeat_count", setter(["nodes", 1, "count"], "Q")),
    ("bad_repeat_count", setter(["nodes", 1, "count"], "eps")),
    ("bad_repeat_count", setter(["nodes", 1, "count"], 2)),
    ("unknown_source", setter(["tables", 0, "source"], "alibi")),
    ("unknown_source", setter(["tables", 0, "source"], ["rope"])),
    ("bad_output", setter(["output", "buffer"], "lm_head")),
    ("bad_output", setter(["output", "buffer"], "nothing")),
    ("bad_output", setter(["output", "buffer"], 1)),
    ("unknown_kind", site_member("qkv", "kind", "conv")),
    ("unknown_kind", site_member("qkv", "kind", 1)),
    ("contract_mismatch", change(lambda doc: node(doc, "qkv")["shape"].pop("k"))),
    ("contract_mismatch", shape_member("qkv", "l", "T")),
    ("contract_mismatch", operand("qkv", "d", "x")),
    ("contract_mismatch", change(lambda doc: node(doc, "norm").pop("scalars"))),
    ("contract_mismatch", site_member("qkv", "scalars", {"eps": "eps"})),
    ("operand_mismatch", operand("rope_q", "freqs_cis", "x")),
    ("operand_mismatch", operand("rope_q", "x", "rope")),
    ("operand_mismatch", operand("qkv", "c", "lm_head")),
    ("operand_mismatch", operand("sdpa", "cache_k", "rope")),
    ("operand_mismatch", setter(["nodes", 0, "weight"], "norm")),
)


@pytest.mark.parametrize(("reason", "make"), READ_REFUSALS)
def test_read_refusals(reason, make):
    with pytest.raises(GraphFileError) as caught:
        read_text(make())
    assert caught.value.reason == reason
    assert str(caught.value).startswith(caught.value.path + ": ")
    assert caught.value.path.startswith("$")


def test_refusal_names_the_json_path():
    with pytest.raises(GraphFileError) as caught:
        read_text(operand("qkv", "a", "nothing")())
    assert caught.value.path == "$.nodes[1].nodes[1].operands.a"


def test_unchanged_document_reads():
    assert read_text(change(lambda doc: None)()) == LLAMA


def test_scalars_may_be_left_out_or_empty():
    assert read_text(site_member("qkv", "scalars", {})()) == LLAMA


def test_unreadable(tmp_path):
    for path in (tmp_path / "missing.json", tmp_path):
        with pytest.raises(GraphFileError) as caught:
            read(path)
        assert caught.value.reason == "unreadable"


@pytest.mark.parametrize(
    ("function", "parameter"), ((read, "path"), (read_text, "text"))
)
def test_reader_argument_types(function, parameter):
    with pytest.raises(TypeError) as caught:
        function(3)
    assert caught.value.parameter == parameter


def resolve_llama(text, dims=None, S=3, G=3, lm_head_rows="all"):
    return resolve(
        read_text(text),
        dims or DIMENSION_SETS[0],
        prompt_length=S,
        generation_length=G,
        lm_head_rows=lm_head_rows,
    )


RESOLVE_REFUSALS = (
    ("bad_value", setter(["buffers", 0, "shape", 0], "T-T")),
    ("bad_value", setter(["buffers", 0, "shape"], ["D", "D-V"])),
    (
        "bad_value",
        setter(["weights", 0, "shape", 0], "V*V*V*V*V*V*V*V*V*V*V*V*V*V*V*V*V"),
    ),
    ("bad_value", shape_member("rope_q", "d", "d+1")),
    ("bad_value", shape_member("qkv", "k", "D-D")),
    ("bad_value", setter(["nodes", 1, "nodes", 2, "columns"], "0")),
    ("bad_value", setter(["nodes", 1, "nodes", 2, "to_stride"], "H-H")),
    ("bad_value", setter(["output", "rows"], "R-R")),
    (
        "out_of_range",
        operand("rope_q", "freqs_cis", {"of": "rope", "start": "(P+1)*d"}),
    ),
    ("out_of_range", operand("lm_head", "a", {"of": "normed", "start": "(T-R-1)*D"})),
    ("out_of_range", operand("lm_head", "a", {"of": "normed", "start": "(T-R)*D+1"})),
    ("out_of_range", shape_member("sdpa", "l", "P+T+1")),
    ("out_of_range", setter(["nodes", 1, "nodes", 4, "from_start"], "H*d+H_kv*d+1")),
    ("out_of_range", setter(["nodes", 1, "nodes", 4, "from_start"], "0-1")),
    ("out_of_range", setter(["nodes", 1, "nodes", 2, "to_stride"], "H*d+1")),
    ("out_of_range", setter(["buffers", 0, "shape", 1], "D-1")),
    ("overlap", operand("rope_q", "out", "q_in")),
    ("overlap", operand("sdpa", "cache_v", "cache_k{layer}")),
    ("overlap", setter(["nodes", 1, "nodes", 2, "to"], "qkv_out")),
)


@pytest.mark.parametrize(("reason", "make"), RESOLVE_REFUSALS)
@pytest.mark.parametrize("lm_head_rows", ("all", "last"))
def test_resolve_refusals(reason, make, lm_head_rows):
    with pytest.raises(GraphFileError) as caught:
        resolve_llama(make(), lm_head_rows=lm_head_rows)
    assert caught.value.reason == reason
    assert str(caught.value).startswith(caught.value.path + ": ")


def resolve_ranges(width, starts):
    a, b, c = ({"of": "a", "start": start} for start in starts)
    document = graph_of([{"name": "a", "shape": ["6"]}], [add("s", a, b, c, width)])
    return resolve(
        read_text(json.dumps(document)),
        {"A": 1, "B": 1},
        prompt_length=1,
        generation_length=1,
        lm_head_rows="all",
    )


def test_disjoint_ranges_of_one_buffer_are_accepted():
    plan = resolve_ranges("2", ("0", "2", "4"))
    assert [o.offset for o in plan.passes[0].steps[0].operands] == [0, 2, 4]


@pytest.mark.parametrize("starts", (("0", "1", "4"), ("0", "3", "2"), ("4", "0", "4")))
def test_partly_overlapping_ranges_of_one_buffer_are_refused(starts):
    with pytest.raises(GraphFileError) as caught:
        resolve_ranges("2", starts)
    assert caught.value.reason == "overlap"


def test_every_reason_is_exercised():
    seen = {reason for reason, _ in READ_REFUSALS + RESOLVE_REFUSALS}
    assert seen | {"unreadable"} == set(REASONS)


@pytest.mark.parametrize(
    ("changes", "parameter", "error"),
    (
        ({"graph": {}}, "graph", TypeError),
        ({"dimensions": [("D", 8)]}, "dimensions", TypeError),
        ({"dimensions": {"D": 8}}, "dimensions", ValueError),
        ({"dimensions": dict(DIMENSION_SETS[0], Z=1)}, "dimensions", ValueError),
        ({"dimensions": dict(DIMENSION_SETS[0], D=True)}, "dimensions", TypeError),
        ({"dimensions": dict(DIMENSION_SETS[0], D=0)}, "dimensions", ValueError),
        (
            {"dimensions": dict(DIMENSION_SETS[0], D=MAX_INTEGER + 1)},
            "dimensions",
            ValueError,
        ),
        ({"prompt_length": "3"}, "prompt_length", TypeError),
        ({"prompt_length": 0}, "prompt_length", ValueError),
        ({"generation_length": 0}, "generation_length", ValueError),
        ({"generation_length": 2.0}, "generation_length", TypeError),
        ({"lm_head_rows": "first"}, "lm_head_rows", ValueError),
        ({"lm_head_rows": None}, "lm_head_rows", ValueError),
    ),
)
def test_resolve_argument_errors(changes, parameter, error):
    arguments = {
        "graph": LLAMA,
        "dimensions": DIMENSION_SETS[0],
        "prompt_length": 3,
        "generation_length": 3,
        "lm_head_rows": "all",
    }
    arguments.update(changes)
    graph, dims = arguments.pop("graph"), arguments.pop("dimensions")
    with pytest.raises(error) as caught:
        resolve(graph, dims, **arguments)
    assert caught.value.parameter == parameter


def test_resolve_does_not_modify_its_arguments():
    dims = dict(DIMENSION_SETS[0])
    before = copy.deepcopy(dims)
    resolve(LLAMA, dims, prompt_length=1, generation_length=1, lm_head_rows="last")
    assert dims == before


def test_single_pass_generation():
    plan = resolve(
        LLAMA,
        DIMENSION_SETS[1],
        prompt_length=1,
        generation_length=1,
        lm_head_rows="all",
    )
    assert len(plan.passes) == 1
    assert {a.name: a.elements for a in plan.arrays}["rope"] == DIMENSION_SETS[1]["d"]
