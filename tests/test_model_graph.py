import copy
import json

import numpy as np
import pytest

from hilclaw import (
    model_binding,
    model_forward_check,
    model_forward_run,
    model_graph,
    rope_table,
)
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
        "scalars": {},
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
    ("missing_member", change(lambda doc: node(doc, "qkv").pop("scalars"))),
    ("contract_mismatch", site_member("norm", "scalars", {})),
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


def test_deeply_nested_repeats_are_malformed():
    nodes = [add("s", "x", "y", "z")]
    for level in range(400):
        nodes = [{"op": "repeat", "count": "A", "index": f"i{level}", "nodes": nodes}]
    buffers = [{"name": n, "shape": ["1"]} for n in ("x", "y", "z")]
    with pytest.raises(GraphFileError) as caught:
        read_text(json.dumps(graph_of(buffers, nodes)))
    assert caught.value.reason == "malformed"


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
    ("out_of_range", setter(["buffers", 1, "shape", 1], "D-1")),
    ("overlap", operand("rope_q", "out", "q_in")),
    ("overlap", operand("sdpa", "cache_v", "cache_k{layer}")),
    ("overlap", setter(["nodes", 1, "nodes", 2, "to"], "qkv_out")),
    ("overlap", setter(["nodes", 1, "nodes", 2, "to_stride"], "H*d-1")),
    ("bad_value", setter(["buffers", 0, "shape", 1], "D+1")),
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


CONTRACTS = {
    kind: model_graph._contract(kind).task_contract(*(2,) * len(members))
    for kind, members in (
        ("gemm", "mkn"),
        ("rmsnorm", "mn"),
        ("elementwise_add", "mn"),
        ("swiglu", "mn"),
        ("rope", "mhd"),
        ("sdpa_kv_cache", "mlhkd"),
    )
}
KIND_OF_SITE = dict(
    zip(
        model_forward_run.CALL_SITES,
        ("gemm",) * 6
        + ("rmsnorm",) * 3
        + ("elementwise_add",) * 2
        + ("swiglu",)
        + ("rope",) * 2
        + ("sdpa_kv_cache",),
        strict=True,
    )
)
ROPE = model_forward_check.RopeConstants(10000.0, 2.0, 1.0, 4.0, 8)


def kernel_of(kind, name=None):
    return model_binding.KernelReference((name or kind,), CONTRACTS[kind], ())


def every_binding(**changes):
    binding = {
        site: [model_binding.BindingEntry(kernel_of(kind), "every")]
        for site, kind in KIND_OF_SITE.items()
    }
    binding.update(changes)
    return {site: entries for site, entries in binding.items() if entries}


def forward_weights(dims):
    D, F, V, N = dims["D"], dims["F"], dims["V"], dims["N"]
    W, Hd = (dims["H"] + 2 * dims["H_kv"]) * dims["d"], dims["H"] * dims["d"]

    def zeros(*shape):
        return np.zeros(shape, dtype=np.uint16)

    return model_forward_check.Weights(
        embedding=zeros(V, D),
        attention_norm=[zeros(D) for _ in range(N)],
        qkv=[zeros(D, W) for _ in range(N)],
        o=[zeros(Hd, D) for _ in range(N)],
        ffn_norm=[zeros(D) for _ in range(N)],
        gate=[zeros(D, F) for _ in range(N)],
        up=[zeros(D, F) for _ in range(N)],
        down=[zeros(F, D) for _ in range(N)],
        norm=zeros(D),
        lm_head=zeros(D, V),
    )


def forward_check(dims, binding, S, G, lm_head_rows):
    return model_forward_check.check(
        model_dimensions(dims),
        binding,
        dtype="bf16",
        eps=0.5,
        rope=ROPE,
        weights=forward_weights(dims),
        prompt=[0] * S,
        given=None,
        generation_length=G,
        lm_head_rows=lm_head_rows,
    )


def call_list(check):
    return sorted((site, shape, kernel.sources) for site, shape, kernel in check.calls)


def outcome_set(check):
    return {(o.kind, o.call_site, o.shape) for o in check.outcomes}


def entry(kind, shapes, name=None):
    return model_binding.BindingEntry(kernel_of(kind, name), shapes)


def binding_cases(dims, S, G, lm_head_rows):
    plan = resolve(
        LLAMA, dims, prompt_length=S, generation_length=G, lm_head_rows=lm_head_rows
    )
    exact = {}
    for site, shape, _ in model_graph.check_binding(plan, every_binding()).calls:
        exact.setdefault(site, []).append(shape)
    lm_head = [entry("gemm", tuple(exact["lm_head"][:1]), "first")]
    if exact["lm_head"][1:]:
        lm_head.append(entry("gemm", tuple(exact["lm_head"][1:]), "later"))
    unfit = model_binding.KernelReference(("q",), {"language": "c"}, ())
    return plan, {
        "every": every_binding(),
        "exact": every_binding(
            **{
                site: [entry(KIND_OF_SITE[site], tuple(shapes))]
                for site, shapes in exact.items()
            }
        ),
        "per_shape": every_binding(lm_head=lm_head),
        "missing_site": every_binding(sdpa=[]),
        "missing_shape": every_binding(
            sdpa=[entry("sdpa_kv_cache", tuple(exact["sdpa"][:1]))]
        ),
        "unfit": every_binding(norm=[entry("gemm", "every")]),
        "unfit_contract": every_binding(
            qkv=[model_binding.BindingEntry(unfit, "every")]
        ),
    }


@pytest.mark.parametrize("lm_head_rows", ["all", "last"])
@pytest.mark.parametrize("lengths", LENGTHS)
@pytest.mark.parametrize("dims", DIMENSION_SETS)
def test_binding_check_agrees_with_the_forward_check(dims, lengths, lm_head_rows):
    S, G = lengths
    plan, cases = binding_cases(dims, S, G, lm_head_rows)
    for name, binding in cases.items():
        ours = model_graph.check_binding(plan, binding)
        theirs = forward_check(dims, binding, S, G, lm_head_rows)
        assert ours.ok == theirs.ok, name
        assert call_list(ours) == call_list(theirs), name
        assert outcome_set(ours) == outcome_set(theirs), name
        assert ours.ok == (name in ("every", "exact", "per_shape")), name


def test_binding_check_binds_every_kernel_step():
    plan = resolve_llama(LLAMA_TEXT)
    check = model_graph.check_binding(plan, every_binding())
    bound = {(site, shape): k for site, shape, k in check.calls}
    for one in plan.passes:
        for step in one.steps:
            if isinstance(step, KernelStep):
                assert bound[(step.site, step.shape)].sources == (step.kind,)


@pytest.mark.parametrize(
    ("plan", "binding", "error", "parameter"),
    [
        ("plan", {}, TypeError, "plan"),
        (None, [], TypeError, "binding"),
        (None, {"nowhere": []}, ValueError, "binding"),
        (None, {"qkv": []}, ValueError, "binding"),
        (None, {"qkv": ["entry"]}, TypeError, "binding"),
        (None, {"qkv": [entry("gemm", ((1, 2),))]}, ValueError, "binding"),
    ],
)
def test_binding_check_refusals(plan, binding, error, parameter):
    if plan is None:
        plan = resolve_llama(LLAMA_TEXT)
    with pytest.raises(error) as caught:
        model_graph.check_binding(plan, binding)
    assert caught.value.parameter == parameter


def test_libraries_are_distinct_in_first_call_order():
    plan = resolve_llama(LLAMA_TEXT)
    check = model_graph.check_binding(plan, every_binding())
    kernels = model_graph.libraries(check)
    assert [k.sources[0] for k in kernels] == [
        "rmsnorm",
        "gemm",
        "rope",
        "sdpa_kv_cache",
        "elementwise_add",
        "swiglu",
    ]


@pytest.mark.parametrize(
    ("check", "error"),
    [("check", TypeError), (model_binding.BindingCheck(False, (), ()), ValueError)],
)
def test_libraries_refusals(check, error):
    with pytest.raises(error) as caught:
        model_graph.libraries(check)
    assert caught.value.parameter == "check"


def llama_inputs(**changes):
    dims = DIMENSION_SETS[0]
    weights = forward_weights(dims)
    provided = {"embedding": weights.embedding, "norm": weights.norm}
    provided["lm_head"] = weights.lm_head
    for name in ("attention_norm", "qkv", "o", "ffn_norm", "gate", "up", "down"):
        for i, array in enumerate(getattr(weights, name)):
            provided[f"{name}[{i}]"] = array
    values = {
        "scalars": {"eps": 0.5},
        "tables": {"rope": ROPE},
        "weights": provided,
        "prompt": [0, 1, 2],
        "given": [dims["V"] - 1] * 3,
    }
    values.update(changes)
    return values


def encoded(lm_head_rows="all", **changes):
    plan = resolve_llama(LLAMA_TEXT, lm_head_rows=lm_head_rows)
    check = model_graph.check_binding(plan, every_binding())
    return plan, model_graph.encode(plan, check, **llama_inputs(**changes))


def words(data, count, offset=0):
    return [int(w) for w in np.frombuffer(data, np.uint64, count, offset)]


@pytest.mark.parametrize("lm_head_rows", ["all", "last"])
@pytest.mark.parametrize("generation", [False, True])
def test_encode_follows_the_program_header(lm_head_rows, generation):
    plan, data = encoded(lm_head_rows, **({"given": None} if generation else {}))
    dims = DIMENSION_SETS[0]
    A, steps = len(plan.arrays), sum(len(p.steps) for p in plan.passes)
    output = [a.name for a in plan.arrays].index("logits")
    assert words(data, 8) == [A, 1, 3, 3, dims["V"], int(generation), output, dims["V"]]
    assert np.frombuffer(data, np.float32, 1, 64)[0] == 0.5
    tables = words(data, 3 * A + 6, 68)
    for i, array in enumerate(plan.arrays):
        size = 4 if array.kind == "table" else 2
        role = int(array.kind in ("state", "buffer"))
        assert tables[3 * i : 3 * i + 3] == [array.elements, size, role]
    passes = [w for p in plan.passes for w in (p.output_rows, len(p.steps))]
    assert tables[3 * A :] == passes
    tokens = 3 if generation else 6
    contents = sum(
        a.elements * (4 if a.kind == "table" else 2)
        for a in plan.arrays
        if a.kind in ("weight", "table")
    )
    at = 68 + 8 * (3 * A + 6)
    assert len(data) == at + 160 * steps + 8 * tokens + contents
    expected = [0, 1, 2] + ([] if generation else [dims["V"] - 1] * 3)
    assert words(data, tokens, at + 160 * steps) == expected
    embed = words(data, 20, at)
    assert embed[:5] == [0, 0, 3, dims["D"], 0]
    names = [a.name for a in plan.arrays]
    assert embed[7:11] == [names.index("embedding"), 0, names.index("x"), 0]
    norm = words(data, 20, at + 160)
    assert norm[:4] == [3, 0, 3, dims["D"]]
    assert norm[19] == 0


def test_encode_builds_the_rope_table():
    _, data = encoded()
    rope = rope_table.build(
        head_dim=DIMENSION_SETS[0]["d"], positions=5, **ROPE._asdict()
    )
    assert rope.tobytes() in data


def test_encode_uses_the_library_of_each_pass():
    plan = resolve_llama(LLAMA_TEXT)
    exact = {}
    for site, shape, _ in model_graph.check_binding(plan, every_binding()).calls:
        exact.setdefault(site, []).append(shape)
    o = [
        entry("gemm", tuple(exact["o"][:1])),
        entry("gemm", tuple(exact["o"][1:]), "later"),
    ]
    check = model_graph.check_binding(plan, every_binding(o=o))
    data = model_graph.encode(plan, check, **llama_inputs())
    names = [k.sources[0] for k in model_graph.libraries(check)]
    at = 68 + 8 * (3 * len(plan.arrays) + 6)
    seen = []
    for p, one in enumerate(plan.passes):
        for step in one.steps:
            if isinstance(step, KernelStep) and step.site == "o":
                seen.append((p, names[words(data, 2, at)[1]]))
            at += 160
    assert {name for p, name in seen if p == 0} == {"gemm"}
    assert {name for p, name in seen if p > 0} == {"later"}


ENCODE_REFUSALS = (
    ("scalars", TypeError, {"scalars": [0.5]}),
    ("scalars", ValueError, {"scalars": {}}),
    ("scalars", ValueError, {"scalars": {"eps": 0.5, "other": 1.0}}),
    ("scalars", ValueError, {"scalars": {"eps": -1.0}}),
    ("tables", ValueError, {"tables": {}}),
    ("tables", TypeError, {"tables": None}),
    ("tables", TypeError, {"tables": {"rope": ROPE._asdict()}}),
    ("tables", ValueError, {"tables": {"rope": ROPE._replace(theta=-1.0)}}),
    ("weights", ValueError, {"weights": {}}),
    ("weights", TypeError, {"weights": 3}),
    ("prompt", TypeError, {"prompt": "abc"}),
    ("prompt", ValueError, {"prompt": [0, 1]}),
    ("prompt", TypeError, {"prompt": [0, 1, 2.0]}),
    ("prompt", TypeError, {"prompt": [0, 1, True]}),
    ("prompt", ValueError, {"prompt": [0, 1, 10]}),
    ("prompt", ValueError, {"prompt": [0, -1, 2]}),
    ("given", ValueError, {"given": [0, 1]}),
    ("given", ValueError, {"given": [0, 1, 10]}),
    ("given", TypeError, {"given": 5}),
)


@pytest.mark.parametrize(("parameter", "error", "changes"), ENCODE_REFUSALS)
def test_encode_refusals(parameter, error, changes):
    with pytest.raises(error) as caught:
        encoded(**changes)
    assert caught.value.parameter == parameter


@pytest.mark.parametrize(
    ("name", "value", "error"),
    [
        ("qkv[1]", None, ValueError),
        ("extra", np.zeros(1, dtype=np.uint16), ValueError),
        ("norm", [0] * 8, TypeError),
        ("norm", np.zeros(8, dtype=np.int16), ValueError),
        ("norm", np.zeros(8, dtype=np.float32), ValueError),
        ("norm", np.zeros(9, dtype=np.uint16), ValueError),
        ("qkv[0]", np.zeros((8, 32, 1), dtype=np.uint16), ValueError),
    ],
)
def test_encode_refuses_weights(name, value, error):
    weights = llama_inputs()["weights"]
    if value is None:
        del weights[name]
    else:
        weights[name] = value
    with pytest.raises(error) as caught:
        encoded(weights=weights)
    assert caught.value.parameter == "weights"


def changed_plan(function):
    doc = llama_document()
    function(doc)
    plan = resolve_llama(json.dumps(doc))
    return plan, model_graph.check_binding(plan, every_binding())


def wider_output(doc):
    doc["weights"][-1]["shape"] = ["D", "V+1"]
    doc["buffers"][-1]["shape"] = ["R", "V+1"]
    node(doc, "lm_head")["shape"]["n"] = "V+1"


def test_encode_refuses_an_output_wider_than_the_vocabulary_when_generating():
    plan, check = changed_plan(wider_output)
    values = llama_inputs(given=None)
    values["weights"]["lm_head"] = np.zeros((8, 11), dtype=np.uint16)
    with pytest.raises(ValueError) as caught:
        model_graph.encode(plan, check, **values)
    assert caught.value.parameter == "given"
    values["given"] = [0, 1, 2]
    assert model_graph.encode(plan, check, **values)


def test_encode_refuses_a_plan_without_embed():
    plan, check = changed_plan(lambda doc: doc["nodes"].pop(0))
    with pytest.raises(ValueError) as caught:
        model_graph.encode(plan, check, **llama_inputs())
    assert caught.value.parameter == "plan"


def test_encode_refuses_a_check_of_another_plan():
    plan = resolve_llama(LLAMA_TEXT)
    check = model_graph.check_binding(resolve_llama(LLAMA_TEXT, S=4), every_binding())
    with pytest.raises(ValueError) as caught:
        model_graph.encode(plan, check, **llama_inputs())
    assert caught.value.parameter == "check"


@pytest.mark.parametrize(
    ("plan", "check", "error", "parameter"),
    [
        ("plan", None, TypeError, "plan"),
        (None, "check", TypeError, "check"),
        (None, model_binding.BindingCheck(False, (), ()), ValueError, "check"),
    ],
)
def test_encode_argument_types(plan, check, error, parameter):
    real = resolve_llama(LLAMA_TEXT)
    plan = real if plan is None else plan
    if check is None:
        check = model_graph.check_binding(real, every_binding())
    with pytest.raises(error) as caught:
        model_graph.encode(plan, check, **llama_inputs())
    assert caught.value.parameter == parameter


@pytest.mark.parametrize("lm_head_rows", ["all", "last"])
@pytest.mark.parametrize("mode", ["given", "generation"])
def test_parse_report(lm_head_rows, mode):
    plan = resolve_llama(LLAMA_TEXT, lm_head_rows=lm_head_rows)
    V = DIMENSION_SETS[0]["V"]
    rows = 5 if lm_head_rows == "all" else 3
    tokens = np.arange(6, dtype=np.uint64)
    logits = np.arange(rows * V, dtype=np.uint16).tobytes()
    if mode == "given":
        report = tokens.tobytes() + logits + b"end\n"
    else:
        report = tokens[:3].tobytes() + logits + tokens[3:].tobytes() + b"end\n"
    parsed = model_graph.parse_report(report, plan, mode=mode)
    assert parsed.tokens.tolist() == list(range(6))
    assert parsed.logits.shape == (rows, V)
    assert parsed.logits.tobytes() == logits
    assert model_graph.parse_report(report[:-1], plan, mode=mode) is None
    assert model_graph.parse_report(report[:-4] + b"END\n", plan, mode=mode) is None


@pytest.mark.parametrize(
    ("report", "plan", "mode", "error", "parameter"),
    [
        (b"", "plan", "given", TypeError, "plan"),
        (b"", None, "other", ValueError, "mode"),
        ("text", None, "given", TypeError, "report"),
    ],
)
def test_parse_report_refusals(report, plan, mode, error, parameter):
    plan = resolve_llama(LLAMA_TEXT) if plan is None else plan
    with pytest.raises(error) as caught:
        model_graph.parse_report(report, plan, mode=mode)
    assert caught.value.parameter == parameter


def test_arrays_carry_their_evaluated_shape():
    plan = resolve_llama(LLAMA_TEXT, lm_head_rows="last")
    shapes = {a.name: a.shape for a in plan.arrays}
    dims = DIMENSION_SETS[0]
    assert shapes["qkv[1]"] == (dims["D"], (dims["H"] + 2 * dims["H_kv"]) * dims["d"])
    assert shapes["logits"] == (1, dims["V"])
    assert shapes["rope"] == (5, dims["d"])
    assert shapes["cache_k[0]"] == (5, dims["H_kv"], dims["d"])


def test_encode_refuses_a_table_that_is_not_two_dimensional():
    plan, check = changed_plan(
        lambda doc: doc["tables"][0].__setitem__("shape", ["C", "d", "1"])
    )
    with pytest.raises(ValueError) as caught:
        model_graph.encode(plan, check, **llama_inputs())
    assert caught.value.parameter == "tables"
