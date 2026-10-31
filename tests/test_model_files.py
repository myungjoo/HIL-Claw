import json
import os
import struct

import numpy as np
import pytest
import test_model_forward as forward
import test_model_forward_run as forward_run
import test_model_reference as model_reference_tests

from hilclaw import model_binding, model_files, model_forward_check, model_reference
from hilclaw.model_binding import ModelDimensions
from hilclaw.model_files import ModelFileError, ModelFiles, read
from hilclaw.model_forward_check import RopeConstants, Weights
from hilclaw.rope_table import build

D, F, V, N = forward.D, forward.F, forward.V, forward.N
H, H_KV, HEAD = forward.H, forward.H_KV, forward.HEAD
DIMENSIONS = forward_run.DIMENSIONS
ROPE = forward_run.ROPE
EPS = forward_run.EPS
SCORE_BOUND = 1e-11
MEMBER = "model.layers.0.self_attn.q_proj.weight"


def permute(w, heads, dim1, dim2):
    """The upstream converter's permute, in NumPy."""
    return (
        w.reshape(heads, dim1 // heads // 2, 2, dim2)
        .transpose(0, 2, 1, 3)
        .reshape(dim1, dim2)
    )


def stored_of(weights, *, head=True):
    """The tensors of a Hugging Face file for executor-layout weights, in its arrangement."""
    q_width, kv_width = H * HEAD, H_KV * HEAD
    tensors = {
        "model.embed_tokens.weight": weights.embedding,
        "model.norm.weight": weights.norm,
    }
    for n in range(N):
        prefix = f"model.layers.{n}."
        qkv = weights.qkv[n]
        q, k = qkv[:, :q_width].T, qkv[:, q_width : q_width + kv_width].T
        tensors |= {
            prefix + "input_layernorm.weight": weights.attention_norm[n],
            prefix + "self_attn.q_proj.weight": permute(q, H, q_width, D),
            prefix + "self_attn.k_proj.weight": permute(k, H_KV, kv_width, D),
            prefix + "self_attn.v_proj.weight": qkv[:, q_width + kv_width :].T,
            prefix + "self_attn.o_proj.weight": weights.o[n].T,
            prefix + "post_attention_layernorm.weight": weights.ffn_norm[n],
            prefix + "mlp.gate_proj.weight": weights.gate[n].T,
            prefix + "mlp.up_proj.weight": weights.up[n].T,
            prefix + "mlp.down_proj.weight": weights.down[n].T,
        }
    if head:
        tensors["lm_head.weight"] = weights.lm_head.T
    return tensors


def config_of(dimensions=DIMENSIONS, **changes):
    config = {
        "model_type": "llama",
        "hidden_size": dimensions.hidden,
        "intermediate_size": dimensions.intermediate,
        "vocab_size": dimensions.vocabulary,
        "num_hidden_layers": dimensions.layers,
        "num_attention_heads": dimensions.heads,
        "num_key_value_heads": dimensions.kv_heads,
        "head_dim": dimensions.head_dim,
        "rms_norm_eps": EPS,
        "rope_theta": ROPE.theta,
        "rope_scaling": {
            "factor": ROPE.scale_factor,
            "low_freq_factor": ROPE.low_freq_factor,
            "high_freq_factor": ROPE.high_freq_factor,
            "original_max_position_embeddings": ROPE.old_context_len,
            "rope_type": "llama3",
        },
        "tie_word_embeddings": False,
    }
    for name, value in changes.items():
        if value is ...:
            del config[name]
        else:
            config[name] = value
    return config


def header_and_data(tensors, dtype="BF16"):
    header, data, position = {}, [], 0
    for name, array in tensors.items():
        values = array.ravel().tolist()
        raw = struct.pack(f"<{len(values)}H", *values)
        header[name] = {
            "dtype": dtype,
            "shape": list(array.shape),
            "data_offsets": [position, position + len(raw)],
        }
        data.append(raw)
        position += len(raw)
    return header, b"".join(data)


def write_raw(path, header_text, data=b"", length=None):
    encoded = header_text.encode("utf-8")
    prefix = struct.pack("<Q", len(encoded) if length is None else length)
    path.write_bytes(prefix + encoded + data)


def write_file(path, tensors, change=None, data_change=None):
    header, data = header_and_data(tensors)
    header["__metadata__"] = {"format": "pt"}
    if change:
        change(header)
    if data_change:
        data = data_change(data)
    write_raw(path, json.dumps(header), data)


def write_config(directory, config):
    (directory / "config.json").write_text(json.dumps(config), encoding="utf-8")


def write_single(directory, tensors, config=None, change=None, data_change=None):
    write_config(directory, config if config is not None else config_of())
    write_file(directory / "model.safetensors", tensors, change, data_change)
    return directory


def write_sharded(directory, tensors, config=None, map_change=None):
    write_config(directory, config if config is not None else config_of())
    names = list(tensors)
    shards = {
        "model-00001-of-00002.safetensors": names[::2],
        "model-00002-of-00002.safetensors": names[1::2],
    }
    weight_map = {}
    for shard, held in shards.items():
        write_file(directory / shard, {name: tensors[name] for name in held})
        weight_map |= dict.fromkeys(held, shard)
    if map_change:
        map_change(weight_map)
    index = {"metadata": {"total_size": 0}, "weight_map": weight_map}
    (directory / "model.safetensors.index.json").write_text(
        json.dumps(index), encoding="utf-8"
    )
    return directory


@pytest.fixture
def model():
    return forward_run.model_of(71, prompt=3, given=3)


@pytest.fixture
def weights(model):
    return forward_run.weights_of(model)


@pytest.fixture
def tensors(weights):
    return stored_of(weights)


def assert_same_weights(left, right):
    for name in Weights._fields:
        one, other = getattr(left, name), getattr(right, name)
        if isinstance(one, np.ndarray):
            one, other = [one], [other]
        assert len(one) == len(other)
        for a, b in zip(one, other):
            assert a.dtype == np.uint16 and a.dtype.isnative
            assert a.shape == b.shape
            assert np.array_equal(a, b), name


def check_reasons(result, model):
    tokens = [int(token) for token in model["tokens"]]
    outcome = model_forward_check.check(
        result.dimensions,
        {},
        dtype="bf16",
        eps=result.eps,
        rope=result.rope,
        weights=result.weights,
        prompt=tokens[: model["S"]],
        given=tokens[model["S"] :],
        generation_length=model["G"],
        lm_head_rows="all",
    )
    return [
        item.reason
        for item in outcome.outcomes
        if item.kind == model_binding.INVALID_INPUT
    ]


def refused(directory, reason):
    with pytest.raises(ModelFileError) as caught:
        read(directory)
    assert caught.value.reason == reason
    assert str(caught.value).startswith(reason)


@pytest.mark.parametrize("write", [write_single, write_sharded])
def test_reads_a_model_with_a_stored_head(tmp_path, model, weights, tensors, write):
    result = read(write(tmp_path, tensors))
    assert isinstance(result, ModelFiles)
    assert result.dimensions == DIMENSIONS
    assert result.eps == EPS and type(result.eps) is float
    assert result.rope == ROPE
    assert_same_weights(result.weights, weights)
    assert check_reasons(result, model) == []


@pytest.mark.parametrize("write", [write_single, write_sharded])
def test_tied_absent_head_is_the_transposed_embedding(tmp_path, model, weights, write):
    tied = weights._replace(lm_head=weights.embedding.T.copy())
    directory = write(
        tmp_path, stored_of(tied, head=False), config_of(tie_word_embeddings=True)
    )
    result = read(directory)
    assert_same_weights(result.weights, tied)
    assert check_reasons(result, model) == []


def test_tied_present_head_equal_to_the_embedding_is_read(tmp_path, weights):
    tied = weights._replace(lm_head=weights.embedding.T.copy())
    directory = write_single(
        tmp_path, stored_of(tied), config_of(tie_word_embeddings=True)
    )
    assert_same_weights(read(directory).weights, tied)


def test_tied_present_head_that_differs_is_refused(tmp_path, tensors):
    directory = write_single(tmp_path, tensors, config_of(tie_word_embeddings=True))
    refused(directory, model_files.TIED_HEAD_DIFFERS)


def test_absent_head_with_tying_off_is_refused(tmp_path, weights):
    directory = write_single(tmp_path, stored_of(weights, head=False))
    refused(directory, model_files.ABSENT_HEAD)


def half_split(x, table_row):
    half = x.shape[-1] // 2
    cos, sin = table_row[0::2], table_row[1::2]
    first, second = x[..., :half], x[..., half:]
    return np.concatenate(
        (first * cos - second * sin, second * cos + first * sin), axis=-1
    )


def pair_rule(x, table_row):
    cos, sin = table_row[0::2], table_row[1::2]
    out = np.empty(x.shape)
    out[..., 0::2] = x[..., 0::2] * cos - x[..., 1::2] * sin
    out[..., 1::2] = x[..., 0::2] * sin + x[..., 1::2] * cos
    return out


def scores(q, k):
    return np.array([q[j] @ k[j // (H // H_KV)] for j in range(H)])


def test_stored_order_gives_the_same_scores_as_the_pair_rule(
    tmp_path, weights, tensors
):
    result = read(write_single(tmp_path, tensors)).weights
    assert_same_weights(result, weights)
    table = build(head_dim=HEAD, positions=9, **ROPE._asdict()).astype(np.float64)
    x = np.random.default_rng(5).uniform(-1, 1, D)
    q_width, kv_width = H * HEAD, H_KV * HEAD
    stored_q = forward.widen(tensors[MEMBER]).astype(np.float64)
    stored_k = forward.widen(tensors["model.layers.0.self_attn.k_proj.weight"]).astype(
        np.float64
    )
    stored_q = (stored_q @ x).reshape(H, HEAD)
    stored_k = (stored_k @ x).reshape(H_KV, HEAD)
    product = x @ forward.widen(result.qkv[0]).astype(np.float64)
    read_q = product[:q_width].reshape(H, HEAD)
    read_k = product[q_width : q_width + kv_width].reshape(H_KV, HEAD)
    assert not np.allclose(stored_q, read_q)
    separated = False
    for query in range(9):
        for key in range(query):
            q_row, k_row = table[query], table[key]
            upstream = scores(half_split(stored_q, q_row), half_split(stored_k, k_row))
            executor = scores(pair_rule(read_q, q_row), pair_rule(read_k, k_row))
            unrestored = scores(pair_rule(stored_q, q_row), pair_rule(stored_k, k_row))
            assert np.max(np.abs(upstream)) > 1e-3
            assert np.max(np.abs(upstream - executor)) <= SCORE_BOUND * np.max(
                np.abs(upstream)
            )
            separated |= bool(np.max(np.abs(upstream - unrestored)) > 1e-3)
    assert separated


@pytest.mark.parametrize("rows", ["all", "last"])
def test_whole_pass_equals_the_starting_weights(tmp_path, model, tensors, rows):
    result = read(write_single(tmp_path, tensors))
    arguments = model_reference_tests.arguments(model, lm_head_rows=rows)
    expected = model_reference.reference_logits(DIMENSIONS, **arguments)
    arguments |= {"eps": result.eps, "rope": result.rope, "weights": result.weights}
    actual = model_reference.reference_logits(result.dimensions, **arguments)
    assert np.array_equal(actual, expected)


def legacy_with_type(config):
    block = dict(config["rope_scaling"])
    block["type"] = block.pop("rope_type")
    return config | {"rope_scaling": block}


def current_form(config):
    block = config.pop("rope_scaling") | {"rope_theta": config.pop("rope_theta")}
    return config | {"rope_parameters": block}


def current_with_theta_outside(config):
    return config | {"rope_parameters": config.pop("rope_scaling")}


def context_outside(config):
    block = dict(config["rope_scaling"])
    length = block.pop("original_max_position_embeddings")
    return config | {"rope_scaling": block, "original_max_position_embeddings": length}


def context_both_equal(config):
    return config | {"original_max_position_embeddings": ROPE.old_context_len}


@pytest.mark.parametrize(
    "form",
    [
        legacy_with_type,
        current_form,
        current_with_theta_outside,
        context_outside,
        context_both_equal,
    ],
)
def test_each_form_of_the_constants(tmp_path, tensors, form):
    result = read(write_single(tmp_path, tensors, form(config_of())))
    assert result.rope == ROPE
    assert isinstance(result.rope, RopeConstants)


def test_head_dim_absent_is_hidden_over_heads(tmp_path):
    dimensions = ModelDimensions(8, 12, 10, 1, 4, 2, 2)
    generator = np.random.default_rng(3)

    def tensor(*shape):
        return generator.integers(0x3F00, 0x4000, shape, dtype=np.uint16)

    prefix = "model.layers.0."
    tensors = {
        "model.embed_tokens.weight": tensor(10, 8),
        "model.norm.weight": tensor(8),
        prefix + "input_layernorm.weight": tensor(8),
        prefix + "self_attn.q_proj.weight": tensor(8, 8),
        prefix + "self_attn.k_proj.weight": tensor(4, 8),
        prefix + "self_attn.v_proj.weight": tensor(4, 8),
        prefix + "self_attn.o_proj.weight": tensor(8, 8),
        prefix + "post_attention_layernorm.weight": tensor(8),
        prefix + "mlp.gate_proj.weight": tensor(12, 8),
        prefix + "mlp.up_proj.weight": tensor(12, 8),
        prefix + "mlp.down_proj.weight": tensor(8, 12),
        "lm_head.weight": tensor(10, 8),
    }
    config = config_of(dimensions, head_dim=...)
    result = read(write_single(tmp_path, tensors, config))
    assert result.dimensions == dimensions
    assert result.weights.qkv[0].shape == (8, 16)


def test_little_endian_bytes_reach_native_patterns(tmp_path, tensors):
    tensors["model.norm.weight"] = tensors["model.norm.weight"].copy()
    tensors["model.norm.weight"][0] = 0x1234
    directory = write_single(tmp_path, tensors)
    assert b"\x34\x12" in (directory / "model.safetensors").read_bytes()
    norm = read(directory).weights.norm
    assert norm[0] == 0x1234
    assert norm.dtype == np.uint16 and norm.dtype.isnative


def test_transposed_arrays_are_c_contiguous_and_writeable(tmp_path, tensors):
    result = read(write_single(tmp_path, tensors)).weights
    for array in (result.o[0], result.gate[0], result.qkv[0], result.lm_head):
        assert array.flags["C_CONTIGUOUS"]
        assert array.flags["WRITEABLE"]


def test_directory_of_a_path_object_and_of_a_str(tmp_path, tensors):
    write_single(tmp_path, tensors)
    assert read(str(tmp_path)).dimensions == read(tmp_path).dimensions


@pytest.mark.parametrize("value", [None, 3, b"bytes"])
def test_directory_of_a_wrong_type_is_a_type_error(value):
    with pytest.raises(TypeError) as caught:
        read(value)
    assert caught.value.parameter == "directory"


def test_missing_directory(tmp_path):
    refused(tmp_path / "absent", model_files.NO_DIRECTORY)


def test_missing_config(tmp_path, tensors):
    write_file(tmp_path / "model.safetensors", tensors)
    refused(tmp_path, model_files.NO_CONFIG)


def test_missing_weights_and_no_pickle_is_read(tmp_path):
    write_config(tmp_path, config_of())
    (tmp_path / "pytorch_model.bin").write_bytes(b"not read")
    refused(tmp_path, model_files.NO_WEIGHTS)


def test_two_weight_forms_are_refused(tmp_path, tensors):
    write_sharded(tmp_path, tensors)
    write_file(tmp_path / "model.safetensors", tensors)
    refused(tmp_path, model_files.TWO_WEIGHT_FORMS)


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (b"{not json", model_files.MALFORMED_JSON),
        (b"[1, 2]", model_files.MALFORMED_JSON),
        (b'{"a": NaN}', model_files.MALFORMED_JSON),
        (b"\xff\xfe", model_files.MALFORMED_JSON),
        (b'{"a": 1, "a": 2}', model_files.DUPLICATE_MEMBER),
    ],
)
def test_malformed_config(tmp_path, tensors, data, reason):
    write_single(tmp_path, tensors)
    (tmp_path / "config.json").write_bytes(data)
    refused(tmp_path, reason)


def test_json_larger_than_the_bound(tmp_path, tensors, monkeypatch):
    write_single(tmp_path, tensors)
    monkeypatch.setattr(model_files, "_MAX_JSON", 4)
    refused(tmp_path, model_files.MALFORMED_JSON)


@pytest.mark.parametrize(
    "member",
    [
        "hidden_size",
        "intermediate_size",
        "vocab_size",
        "num_hidden_layers",
        "num_attention_heads",
        "num_key_value_heads",
        "rms_norm_eps",
        "tie_word_embeddings",
        "rope_theta",
    ],
)
def test_missing_config_member(tmp_path, tensors, member):
    write_single(tmp_path, tensors, config_of(**{member: ...}))
    refused(tmp_path, model_files.MISSING_MEMBER)


@pytest.mark.parametrize(
    "member",
    [
        "factor",
        "low_freq_factor",
        "high_freq_factor",
        "original_max_position_embeddings",
        "rope_type",
    ],
)
def test_missing_rope_member(tmp_path, tensors, member):
    config = config_of()
    del config["rope_scaling"][member]
    write_single(tmp_path, tensors, config)
    refused(tmp_path, model_files.MISSING_MEMBER)


def test_no_rope_block_is_missing(tmp_path, tensors):
    write_single(tmp_path, tensors, config_of(rope_scaling=...))
    refused(tmp_path, model_files.MISSING_MEMBER)


def rope_block_change(**changes):
    config = config_of()
    config["rope_scaling"] |= changes
    return config


@pytest.mark.parametrize(
    ("config", "reason"),
    [
        (config_of(hidden_size="8"), model_files.WRONG_MEMBER_TYPE),
        (config_of(hidden_size=8.0), model_files.WRONG_MEMBER_TYPE),
        (config_of(head_dim=..., hidden_size="8"), model_files.WRONG_MEMBER_TYPE),
        (config_of(rms_norm_eps=1), model_files.WRONG_MEMBER_TYPE),
        (config_of(tie_word_embeddings=1), model_files.WRONG_MEMBER_TYPE),
        (config_of(rope_theta="x"), model_files.WRONG_MEMBER_TYPE),
        (config_of(rope_scaling=[1]), model_files.WRONG_MEMBER_TYPE),
        (rope_block_change(factor=True), model_files.WRONG_MEMBER_TYPE),
        (config_of(rms_norm_eps=-1.0), model_files.BAD_CONSTANT),
        (config_of(rope_theta=-1.0), model_files.BAD_CONSTANT),
        (rope_block_change(high_freq_factor=0.5), model_files.BAD_CONSTANT),
        (config_of(num_key_value_heads=3), model_files.BAD_DIMENSIONS),
        (config_of(head_dim=3), model_files.BAD_DIMENSIONS),
        (config_of(hidden_size=0), model_files.BAD_DIMENSIONS),
        (config_of(head_dim=..., hidden_size=9), model_files.BAD_DIMENSIONS),
        (config_of(head_dim=..., num_attention_heads=0), model_files.BAD_DIMENSIONS),
        (config_of(model_type="gpt2"), model_files.UNSUPPORTED_MODEL),
        (config_of(attention_bias=True), model_files.UNSUPPORTED_MODEL),
        (config_of(mlp_bias=True), model_files.UNSUPPORTED_MODEL),
        (config_of(hidden_act="relu"), model_files.UNSUPPORTED_MODEL),
        (rope_block_change(rope_type="default"), model_files.UNSUPPORTED_MODEL),
        (config_of(partial_rotary_factor=0.5), model_files.UNSUPPORTED_MODEL),
        (rope_block_change(partial_rotary_factor=0.5), model_files.UNSUPPORTED_MODEL),
        (
            config_of(rope_parameters={"rope_type": "llama3"}),
            model_files.TWO_ROPE_FORMS,
        ),
        (config_of(original_max_position_embeddings=9), model_files.TWO_ROPE_FORMS),
    ],
)
def test_refused_config_values(tmp_path, tensors, config, reason):
    write_single(tmp_path, tensors, config)
    refused(tmp_path, reason)


@pytest.fixture
def no_array(monkeypatch):
    def fail(*_arguments, **_keywords):
        raise AssertionError("a tensor array was made")

    monkeypatch.setattr(model_files.numpy, "fromfile", fail)


def change_entry(**changes):
    def change(header):
        header[MEMBER] |= changes

    return change


def share_a_range(header):
    header[MEMBER]["data_offsets"] = header["model.norm.weight"]["data_offsets"]


def begin_inside_the_previous(header):
    begin, end = header["model.norm.weight"]["data_offsets"]
    header["model.norm.weight"]["data_offsets"] = [begin - 2, end]


def hole(header):
    for entry in header.values():
        if "data_offsets" in entry and entry["data_offsets"][0]:
            begin, end = entry["data_offsets"]
            entry["data_offsets"] = [begin + 2, end + 2]


def wrong_metadata(header):
    header["__metadata__"] = {"format": 3}


def extra_entry_member(header):
    header[MEMBER]["other"] = 1


@pytest.mark.parametrize(
    ("change", "data_change", "reason"),
    [
        (change_entry(data_offsets=[-2, 2]), None, model_files.OFFSET_OUTSIDE),
        (change_entry(data_offsets=[8, 4]), None, model_files.OFFSET_OUTSIDE),
        (change_entry(data_offsets=[0, 10**12]), None, model_files.OFFSET_OUTSIDE),
        (None, lambda data: data[:-2], model_files.OFFSET_OUTSIDE),
        (share_a_range, None, model_files.RANGE_OVERLAP),
        (begin_inside_the_previous, None, model_files.RANGE_OVERLAP),
        (hole, lambda data: data + b"\0\0", model_files.RANGE_UNCOVERED),
        (None, lambda data: data + b"\0\0", model_files.RANGE_UNCOVERED),
        (change_entry(shape=[2, 2]), None, model_files.SHAPE_BYTES),
        (change_entry(shape=[2**40, 2**40]), None, model_files.SHAPE_BYTES),
        (change_entry(dtype="F32"), None, model_files.STORED_DTYPE),
        (change_entry(dtype="bf16"), None, model_files.STORED_DTYPE),
        (change_entry(dtype=3), None, model_files.MALFORMED_HEADER),
        (change_entry(shape="8"), None, model_files.MALFORMED_HEADER),
        (change_entry(shape=[8.0]), None, model_files.MALFORMED_HEADER),
        (change_entry(shape=[-1]), None, model_files.MALFORMED_HEADER),
        (change_entry(shape=[True]), None, model_files.MALFORMED_HEADER),
        (change_entry(data_offsets=[0]), None, model_files.MALFORMED_HEADER),
        (change_entry(data_offsets=[0.0, 2]), None, model_files.MALFORMED_HEADER),
        (wrong_metadata, None, model_files.MALFORMED_HEADER),
        (extra_entry_member, None, model_files.MALFORMED_HEADER),
    ],
)
def test_header_refusals_come_before_any_array(
    tmp_path, tensors, no_array, change, data_change, reason
):
    write_single(tmp_path, tensors, None, change, data_change)
    refused(tmp_path, reason)


@pytest.mark.parametrize(
    ("write", "reason"),
    [
        (lambda path: path.write_bytes(b"\0\0"), model_files.TRUNCATED),
        (lambda path: write_raw(path, "{}", length=50), model_files.TRUNCATED),
        (
            lambda path: write_raw(path, "{}", length=10**8 + 1),
            model_files.HEADER_LENGTH,
        ),
        (lambda path: write_raw(path, "{bad"), model_files.MALFORMED_HEADER),
        (lambda path: write_raw(path, "[]"), model_files.MALFORMED_HEADER),
        (lambda path: write_raw(path, '{"a": Infinity}'), model_files.MALFORMED_HEADER),
        (
            lambda path: write_raw(
                path,
                '{"a": {"dtype": "BF16", "shape": [], "data_offsets": [0, 2]},'
                ' "a": {"dtype": "BF16", "shape": [], "data_offsets": [0, 2]}}',
                b"\0\0",
            ),
            model_files.DUPLICATE_MEMBER,
        ),
    ],
)
def test_file_level_refusals(tmp_path, no_array, write, reason):
    write_config(tmp_path, config_of())
    write(tmp_path / "model.safetensors")
    refused(tmp_path, reason)


def test_missing_tensor(tmp_path, tensors, no_array):
    del tensors[MEMBER]
    tensors["other"] = np.zeros(1, dtype=np.uint16)
    write_single(tmp_path, tensors)
    refused(tmp_path, model_files.MISSING_TENSOR)


def test_extra_tensor(tmp_path, tensors, no_array):
    tensors["model.layers.0.self_attn.q_proj.bias"] = np.zeros(16, dtype=np.uint16)
    write_single(tmp_path, tensors)
    refused(tmp_path, model_files.EXTRA_TENSOR)


def test_a_layer_count_beyond_the_tensors_is_refused_without_listing_them(
    tmp_path, tensors, no_array
):
    write_single(tmp_path, tensors, config_of(num_hidden_layers=2**50))
    refused(tmp_path, model_files.MISSING_TENSOR)


@pytest.mark.parametrize(
    "name", [MEMBER, "lm_head.weight", "model.norm.weight", "model.embed_tokens.weight"]
)
def test_wrong_tensor_shape(tmp_path, tensors, no_array, name):
    tensors[name] = tensors[name].reshape(-1)
    if name == "model.norm.weight":
        tensors[name] = tensors[name][:-1]
    write_single(tmp_path, tensors)
    refused(tmp_path, model_files.TENSOR_SHAPE)


def assign_to_the_other_shard(weight_map):
    weight_map["model.norm.weight"] = next(
        shard
        for shard in set(weight_map.values())
        if shard != weight_map["model.norm.weight"]
    )


@pytest.mark.parametrize(
    ("map_change", "reason"),
    [
        (
            lambda m: m.update(absent="model-00001-of-00002.safetensors"),
            model_files.SHARD_INDEX,
        ),
        (lambda m: m.pop(MEMBER), model_files.SHARD_INDEX),
        (assign_to_the_other_shard, model_files.SHARD_INDEX),
        (lambda m: m.update({MEMBER: "missing.safetensors"}), model_files.SHARD_INDEX),
        (lambda m: m.update({MEMBER: 3}), model_files.SHARD_INDEX),
        (
            lambda m: m.update({MEMBER: "../outside.safetensors"}),
            model_files.SHARD_PATH,
        ),
        (
            lambda m: m.update({MEMBER: "..\\outside.safetensors"}),
            model_files.SHARD_PATH,
        ),
        (lambda m: m.update({MEMBER: os.path.abspath("x")}), model_files.SHARD_PATH),
        (lambda m: m.update({MEMBER: ".."}), model_files.SHARD_PATH),
        (lambda m: m.update({MEMBER: ""}), model_files.SHARD_PATH),
    ],
)
def test_shard_index_refusals(tmp_path, tensors, no_array, map_change, reason):
    write_sharded(tmp_path, tensors, map_change=map_change)
    refused(tmp_path, reason)


def test_index_with_no_weight_map(tmp_path, no_array):
    write_config(tmp_path, config_of())
    (tmp_path / "model.safetensors.index.json").write_text("{}", encoding="utf-8")
    refused(tmp_path, model_files.SHARD_INDEX)


def test_read_failure_of_a_header(tmp_path, tensors, monkeypatch):
    write_single(tmp_path, tensors)
    real = os.path.getsize

    def fail(path):
        if str(path).endswith(".safetensors"):
            raise OSError("denied")
        return real(path)

    monkeypatch.setattr(model_files.os.path, "getsize", fail)
    refused(tmp_path, model_files.READ_FAILED)


def test_read_failure_of_a_config(tmp_path, tensors, monkeypatch):
    write_single(tmp_path, tensors)

    def fail(_path):
        raise OSError("denied")

    monkeypatch.setattr(model_files.os.path, "getsize", fail)
    refused(tmp_path, model_files.READ_FAILED)


def test_read_failure_of_a_tensor(tmp_path, tensors, monkeypatch):
    write_single(tmp_path, tensors)

    def fail(*_arguments, **_keywords):
        raise OSError("denied")

    monkeypatch.setattr(model_files.numpy, "fromfile", fail)
    refused(tmp_path, model_files.READ_FAILED)


def test_a_file_cut_after_its_header_was_read(tmp_path, tensors, monkeypatch):
    write_single(tmp_path, tensors)
    monkeypatch.setattr(
        model_files.numpy,
        "fromfile",
        lambda *_arguments, **_keywords: np.zeros(0, dtype=np.uint16),
    )
    refused(tmp_path, model_files.TRUNCATED)


def test_nothing_is_written(tmp_path, tensors):
    write_single(tmp_path, tensors)
    before = sorted((path.name, path.stat().st_mtime_ns) for path in tmp_path.iterdir())
    read(tmp_path)
    assert sorted((p.name, p.stat().st_mtime_ns) for p in tmp_path.iterdir()) == before
