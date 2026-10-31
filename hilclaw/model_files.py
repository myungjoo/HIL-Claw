"""Reader of a Hugging Face Llama model directory for the model executor (ADR-0191).

``ARCHITECTURE/decisions/ADR-0191-od31-hugging-face-model-files.md`` is the
rule. :func:`read` takes a directory on the runtime machine and returns what
:func:`hilclaw.model_forward_execute.execute` takes from its caller as model
parameters and weights (ADR-0166 decision 4):

* the dimensions, ``eps`` and the five RoPE constants, from ``config.json``;
* the weights, from ``model.safetensors``, or from
  ``model.safetensors.index.json`` and the shards it names, as bf16 patterns.

Its parts:

* :func:`read`: the reader.
* :class:`ModelFiles`: what :func:`read` returns.
* :class:`ModelFileError`: every refusal of a file's content, with a
  ``reason`` that is one of the module's constants, listed below.

**The arrays.** Each array of the result is a new native-order
``numpy.uint16`` array in the layout of ADR-0166 decision 4. A tensor's name
gives its field by the table of ADR-0191 decision 3. A PyTorch linear weight
``[out, in]`` is transposed to ``[in, out]``; the embedding table is not. The
stored Q and K projections go back from the half-split arrangement to the
adjacent pairs of ADR-0161 decision 5 (ADR-0191 decision 4), each on its own
head count and before ``qkv`` is joined in the column order Q, K, V. A bf16
tensor is handed over as its bit patterns, converted by nothing but byte order.

**The bounds.** A safetensors header is read only when its length is at most
100 000 000 bytes, the limit of the format's own library. All the headers and
every check of the tensors' names, ranges and shapes come before the first
tensor array is made, so an array's size has been matched against the bytes
the file holds.

What this module does not do: it reads no pickle file and no tokenizer file; it
writes nothing, copies nothing, keeps nothing between calls, starts nothing,
imports no package beyond NumPy and is registered as no tool. It gives no model
value a default: a value the file does not give is a refusal (HQ-0070; ADR-0176
decision 6). It converts no other element type to bf16.
"""

import json
import math
import os
import struct
from typing import NamedTuple

import numpy

from hilclaw import model_binding, rope_table
from hilclaw.model_binding import ModelDimensions
from hilclaw.model_forward_check import RopeConstants, Weights

NO_DIRECTORY = "no_directory"
NO_CONFIG = "no_config"
NO_WEIGHTS = "no_weights"
TWO_WEIGHT_FORMS = "two_weight_forms"
READ_FAILED = "read_failed"
MALFORMED_JSON = "malformed_json"
DUPLICATE_MEMBER = "duplicate_member"
MISSING_MEMBER = "missing_member"
WRONG_MEMBER_TYPE = "wrong_member_type"
UNSUPPORTED_MODEL = "unsupported_model"
TWO_ROPE_FORMS = "two_rope_forms"
BAD_CONSTANT = "bad_constant"
BAD_DIMENSIONS = "bad_dimensions"
HEADER_LENGTH = "header_length"
MALFORMED_HEADER = "malformed_header"
TRUNCATED = "truncated"
OFFSET_OUTSIDE = "offset_outside"
RANGE_OVERLAP = "range_overlap"
RANGE_UNCOVERED = "range_uncovered"
SHAPE_BYTES = "shape_bytes"
STORED_DTYPE = "stored_dtype"
SHARD_INDEX = "shard_index"
SHARD_PATH = "shard_path"
MISSING_TENSOR = "missing_tensor"
EXTRA_TENSOR = "extra_tensor"
TENSOR_SHAPE = "tensor_shape"
ABSENT_HEAD = "absent_head"
TIED_HEAD_DIFFERS = "tied_head_differs"

_MAX_JSON = 100_000_000
_CONFIG = "config.json"
_SINGLE = "model.safetensors"
_INDEX = "model.safetensors.index.json"
_METADATA = "__metadata__"
_HEAD = "lm_head.weight"
_EMBEDDING = "model.embed_tokens.weight"
_NORM = "model.norm.weight"
_LAYER = "model.layers.{}."
_ENTRY_MEMBERS = {"dtype", "shape", "data_offsets"}
_DIMENSION_MEMBERS = (
    ("hidden", "hidden_size"),
    ("intermediate", "intermediate_size"),
    ("vocabulary", "vocab_size"),
    ("layers", "num_hidden_layers"),
    ("heads", "num_attention_heads"),
    ("kv_heads", "num_key_value_heads"),
)
_ROPE_MEMBERS = (
    ("scale_factor", "factor"),
    ("low_freq_factor", "low_freq_factor"),
    ("high_freq_factor", "high_freq_factor"),
)
_COMPUTED_VALUES = (
    ("model_type", "llama"),
    ("attention_bias", False),
    ("mlp_bias", False),
    ("hidden_act", "silu"),
)
_PER_LAYER_TENSORS = 9
_OTHER_TENSORS = 2


class ModelFileError(Exception):
    """A refusal of a model directory's content; ``reason`` is one of the module's constants."""

    def __init__(self, reason, message):
        super().__init__(f"{reason}: {message}")
        self.reason = reason


class ModelFiles(NamedTuple):
    """What :func:`read` returns.

    ``dimensions`` is a :class:`hilclaw.model_binding.ModelDimensions`,
    ``eps`` a ``float``, ``rope`` a
    :class:`hilclaw.model_forward_check.RopeConstants` and ``weights`` a
    :class:`hilclaw.model_forward_check.Weights` whose arrays are native-order
    ``numpy.uint16``.
    """

    dimensions: object
    eps: object
    rope: object
    weights: object


class _Tensor(NamedTuple):
    path: str
    shape: tuple
    offset: int


def read(directory):
    """Read a Hugging Face Llama model directory; return a :class:`ModelFiles`.

    ``directory`` is a ``str`` or a path object naming a directory on this
    machine; a symbolic link inside it is followed, since a Hugging Face cache
    directory holds its files that way. It reads ``config.json`` and exactly one
    of ``model.safetensors`` and ``model.safetensors.index.json`` with its
    shards; nothing else there is opened and nothing is written.

    Raises :class:`TypeError` (``parameter`` ``"directory"``) for an argument of
    another type, and :class:`ModelFileError` for a refusal: a directory, config
    or weights file that is missing, or two weight forms at once; a file that
    cannot be read; JSON that is malformed, larger than the bound or gives a
    member twice; a config member missing or of a wrong type, a stated value the
    forward pass does not compute, two RoPE blocks or two values of one RoPE
    member that differ, a constant
    :func:`hilclaw.rope_table.constant_refusals` or
    :func:`hilclaw.model_binding.rmsnorm_eps` refuses, or dimensions
    :func:`hilclaw.model_binding.check_dimensions` refuses or that do not fit
    one another; a header whose length, members, offsets, ranges, element type
    or shape's byte count is refused; a shard index that disagrees with its
    shards or names a path outside the directory; a tensor missing, extra or of
    a wrong shape; and a head the tying rule of ADR-0191 decision 5 refuses.
    """
    path = _path(directory)
    if not os.path.isdir(path):
        _refuse(NO_DIRECTORY, f"{path!r} is not a directory")
    config_path = os.path.join(path, _CONFIG)
    if not os.path.isfile(config_path):
        _refuse(NO_CONFIG, f"{config_path!r} is not a file")
    config = _json_file(config_path)
    dimensions = _dimensions(config)
    eps = _eps(config)
    rope = _rope(config)
    tied = _tied(config)
    tensors = _tensors(path)
    _check_tensors(tensors, dimensions, tied)
    return ModelFiles(dimensions, eps, rope, _weights(tensors, dimensions, tied))


def _refuse(reason, message):
    raise ModelFileError(reason, message) from None


def _path(directory):
    if isinstance(directory, (str, os.PathLike)):
        path = os.fspath(directory)
        if isinstance(path, str):
            return path
    error = TypeError(
        f"directory: must be a str or a path, got {type(directory).__name__}"
    )
    error.parameter = "directory"
    raise error


def _unique_members(pairs):
    members = {}
    for name, value in pairs:
        if name in members:
            _refuse(DUPLICATE_MEMBER, f"member {name!r} is given twice")
        members[name] = value
    return members


def _not_a_number(text):
    raise ValueError(f"{text} is not JSON")


def _parsed(data, label):
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_members,
            parse_constant=_not_a_number,
        )
    except (ValueError, RecursionError) as error:
        _refuse(MALFORMED_JSON, f"{label}: {error}")
    if not isinstance(value, dict):
        _refuse(MALFORMED_JSON, f"{label}: is not a JSON object")
    return value


def _json_file(path):
    try:
        if os.path.getsize(path) > _MAX_JSON:
            _refuse(MALFORMED_JSON, f"{path!r} exceeds {_MAX_JSON} bytes")
        with open(path, "rb") as file:
            data = file.read()
    except OSError as error:
        _refuse(READ_FAILED, f"{path!r}: {error}")
    return _parsed(data, repr(path))


def _member(config, name):
    if config.get(name) is None:
        _refuse(MISSING_MEMBER, f"config.json has no {name!r}")
    return config[name]


def _dimensions(config):
    for name, computed in _COMPUTED_VALUES:
        if config.get(name, computed) != computed:
            _refuse(UNSUPPORTED_MODEL, f"{name} is {config[name]!r}, not {computed!r}")
    values = {field: _member(config, name) for field, name in _DIMENSION_MEMBERS}
    head_dim = config.get("head_dim")
    if head_dim is None:
        head_dim = _derived_head_dim(values["hidden"], values["heads"])
    dimensions = ModelDimensions(head_dim=head_dim, **values)
    try:
        model_binding.check_dimensions(dimensions)
    except TypeError as error:
        _refuse(WRONG_MEMBER_TYPE, f"config.json: {error}")
    except ValueError as error:
        _refuse(BAD_DIMENSIONS, f"config.json: {error}")
    if dimensions.head_dim % 2:
        _refuse(BAD_DIMENSIONS, f"head_dim must be even, got {dimensions.head_dim}")
    return dimensions


def _derived_head_dim(hidden, heads):
    if type(hidden) is not int or type(heads) is not int:
        _refuse(WRONG_MEMBER_TYPE, f"hidden_size {hidden!r}, heads {heads!r}")
    if heads < 1 or hidden % heads:
        _refuse(BAD_DIMENSIONS, f"no head_dim; hidden_size {hidden}, heads {heads}")
    return hidden // heads


def _eps(config):
    eps = _member(config, "rms_norm_eps")
    try:
        model_binding.rmsnorm_eps(eps)
    except TypeError as error:
        _refuse(WRONG_MEMBER_TYPE, f"rms_norm_eps: {error}")
    except ValueError as error:
        _refuse(BAD_CONSTANT, f"rms_norm_eps: {error}")
    return eps


def _rope(config):
    block = _rope_block(config)
    rope_type = _one_value("rope_type", block.get("rope_type"), block.get("type"))
    if rope_type != "llama3":
        _refuse(UNSUPPORTED_MODEL, f"rope_type is {rope_type!r}, not 'llama3'")
    for source in (block, config):
        if source.get("partial_rotary_factor") not in (None, 1.0):
            _refuse(UNSUPPORTED_MODEL, "partial_rotary_factor is not 1")
    context = "original_max_position_embeddings"
    values = {
        "theta": _one_value(
            "rope_theta", block.get("rope_theta"), config.get("rope_theta")
        ),
        "old_context_len": _one_value(context, block.get(context), config.get(context)),
    }
    for field, name in _ROPE_MEMBERS:
        if block.get(name) is None:
            _refuse(MISSING_MEMBER, f"the RoPE parameters have no {name}")
        values[field] = block[name]
    try:
        refusals = rope_table.constant_refusals(**values)
    except TypeError as error:
        _refuse(WRONG_MEMBER_TYPE, f"RoPE constant {error.parameter}: {error}")
    if refusals:
        _refuse(BAD_CONSTANT, f"RoPE constants: {refusals}")
    return RopeConstants(**values)


def _rope_block(config):
    current = config.get("rope_parameters")
    legacy = config.get("rope_scaling")
    if current is not None and legacy is not None:
        _refuse(TWO_ROPE_FORMS, "config.json has both rope_parameters and rope_scaling")
    block = current if current is not None else legacy
    if block is None:
        _refuse(MISSING_MEMBER, "neither rope_parameters nor rope_scaling is given")
    if not isinstance(block, dict):
        _refuse(WRONG_MEMBER_TYPE, "the RoPE parameters are not a JSON object")
    return block


def _one_value(name, first, second):
    if first is None and second is None:
        _refuse(MISSING_MEMBER, f"no {name} is given")
    if first is not None and second is not None and first != second:
        _refuse(TWO_ROPE_FORMS, f"{name} is both {first!r} and {second!r}")
    return first if first is not None else second


def _tied(config):
    tied = _member(config, "tie_word_embeddings")
    if type(tied) is not bool:
        _refuse(WRONG_MEMBER_TYPE, f"tie_word_embeddings is {tied!r}")
    return tied


def _tensors(directory):
    single = os.path.join(directory, _SINGLE)
    index = os.path.join(directory, _INDEX)
    has_single, has_index = os.path.isfile(single), os.path.isfile(index)
    if has_single and has_index:
        _refuse(TWO_WEIGHT_FORMS, f"{directory!r} holds both {_SINGLE} and {_INDEX}")
    if has_single:
        return _header(single)
    if not has_index:
        _refuse(NO_WEIGHTS, f"{directory!r} holds neither {_SINGLE} nor {_INDEX}")
    return _shards(directory, index)


def _shards(directory, index):
    weight_map = _json_file(index).get("weight_map")
    if not isinstance(weight_map, dict):
        _refuse(SHARD_INDEX, f"{index!r} has no weight_map object")
    for name, shard in weight_map.items():
        if not isinstance(shard, str):
            _refuse(SHARD_INDEX, f"tensor {name!r} names the shard {shard!r}")
        if not _plain_file_name(shard):
            _refuse(SHARD_PATH, f"tensor {name!r} names the path {shard!r}")
    tensors = {}
    for shard in sorted(set(weight_map.values())):
        path = os.path.join(directory, shard)
        if not os.path.isfile(path):
            _refuse(SHARD_INDEX, f"the shard {shard!r} is not a file")
        held = _header(path)
        for name in held:
            if weight_map.get(name) != shard:
                _refuse(SHARD_INDEX, f"{shard!r} holds {name!r} against the index")
        tensors.update(held)
    for name, shard in weight_map.items():
        if name not in tensors:
            _refuse(SHARD_INDEX, f"{shard!r} does not hold {name!r}")
    return tensors


def _plain_file_name(name):
    return name not in ("", ".", "..") and not any(mark in name for mark in "/\\:\0")


def _header(path):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as file:
            prefix = file.read(8)
            if len(prefix) < 8:
                _refuse(TRUNCATED, f"{path!r} has no header length")
            length = struct.unpack("<Q", prefix)[0]
            if length > _MAX_JSON:
                _refuse(HEADER_LENGTH, f"{path!r} states a header of {length} bytes")
            data = file.read(length)
    except OSError as error:
        _refuse(READ_FAILED, f"{path!r}: {error}")
    if len(data) < length:
        _refuse(TRUNCATED, f"{path!r} ends inside its header")
    try:
        header = _parsed(data, repr(path))
    except ModelFileError as error:
        if error.reason == MALFORMED_JSON:
            _refuse(MALFORMED_HEADER, str(error))
        raise
    base = 8 + length
    return _entries(header, path, base, size - base)


def _entries(header, path, base, data_size):
    tensors = {}
    ranges = []
    for name, entry in header.items():
        if name == _METADATA:
            if not isinstance(entry, dict) or not all(
                isinstance(value, str) for value in entry.values()
            ):
                _refuse(MALFORMED_HEADER, f"{path!r}: {_METADATA}")
            continue
        if not isinstance(entry, dict) or set(entry) != _ENTRY_MEMBERS:
            _refuse(MALFORMED_HEADER, f"{path!r}: entry of {name!r}")
        shape, begin, end = _entry_values(entry, name, path)
        if entry["dtype"] != "BF16":
            _refuse(STORED_DTYPE, f"{name!r} is stored as {entry['dtype']!r}, not BF16")
        if begin < 0 or begin > end or end > data_size:
            _refuse(OFFSET_OUTSIDE, f"{name!r}: [{begin}, {end}] of {data_size} bytes")
        ranges.append((begin, end, name))
        tensors[name] = (shape, begin, end)
    _check_ranges(ranges, data_size, path)
    result = {}
    for name, (shape, begin, end) in tensors.items():
        if 2 * math.prod(shape) != end - begin:
            _refuse(SHAPE_BYTES, f"{name!r}: shape {shape}, {end - begin} bytes")
        result[name] = _Tensor(path, shape, base + begin)
    return result


def _entry_values(entry, name, path):
    shape, offsets = entry["shape"], entry["data_offsets"]
    well_formed = (
        isinstance(entry["dtype"], str)
        and isinstance(shape, list)
        and all(type(extent) is int and extent >= 0 for extent in shape)
        and isinstance(offsets, list)
        and len(offsets) == 2
        and all(type(offset) is int for offset in offsets)
    )
    if not well_formed:
        _refuse(MALFORMED_HEADER, f"{path!r}: entry of {name!r}")
    return tuple(shape), offsets[0], offsets[1]


def _check_ranges(ranges, data_size, path):
    position = 0
    for begin, end, name in sorted(ranges):
        if begin < position:
            _refuse(RANGE_OVERLAP, f"{path!r}: {name!r} overlaps another")
        if begin > position:
            _refuse(RANGE_UNCOVERED, f"{path!r}: bytes {position} to {begin}")
        position = end
    if position != data_size:
        _refuse(RANGE_UNCOVERED, f"{path!r}: bytes {position} to {data_size}")


def _check_tensors(tensors, d, tied):
    required = _OTHER_TENSORS + d.layers * _PER_LAYER_TENSORS
    if required > len(tensors):
        _refuse(MISSING_TENSOR, f"{required} tensors needed, {len(tensors)} held")
    shapes = _stored_shapes(d)
    for name in shapes:
        if name not in tensors:
            _refuse(MISSING_TENSOR, f"no tensor {name!r}")
    for name, tensor in tensors.items():
        if name == _HEAD:
            expected = (d.vocabulary, d.hidden)
        elif name in shapes:
            expected = shapes[name]
        else:
            _refuse(EXTRA_TENSOR, f"the forward pass has no use for {name!r}")
        if tensor.shape != expected:
            _refuse(TENSOR_SHAPE, f"{name!r}: {tensor.shape}, not {expected}")
    if _HEAD not in tensors and not tied:
        _refuse(ABSENT_HEAD, f"no {_HEAD!r}, and tie_word_embeddings is false")


def _stored_shapes(d):
    q_width, kv_width = d.heads * d.head_dim, d.kv_heads * d.head_dim
    shapes = {_EMBEDDING: (d.vocabulary, d.hidden), _NORM: (d.hidden,)}
    for layer in range(d.layers):
        prefix = _LAYER.format(layer)
        shapes[prefix + "input_layernorm.weight"] = (d.hidden,)
        shapes[prefix + "self_attn.q_proj.weight"] = (q_width, d.hidden)
        shapes[prefix + "self_attn.k_proj.weight"] = (kv_width, d.hidden)
        shapes[prefix + "self_attn.v_proj.weight"] = (kv_width, d.hidden)
        shapes[prefix + "self_attn.o_proj.weight"] = (d.hidden, q_width)
        shapes[prefix + "post_attention_layernorm.weight"] = (d.hidden,)
        shapes[prefix + "mlp.gate_proj.weight"] = (d.intermediate, d.hidden)
        shapes[prefix + "mlp.up_proj.weight"] = (d.intermediate, d.hidden)
        shapes[prefix + "mlp.down_proj.weight"] = (d.hidden, d.intermediate)
    return shapes


def _array(tensor):
    count = math.prod(tensor.shape)
    try:
        array = numpy.fromfile(tensor.path, "<u2", count, offset=tensor.offset)
    except OSError as error:
        _refuse(READ_FAILED, f"{tensor.path!r}: {error}")
    if array.size != count:
        _refuse(TRUNCATED, f"{tensor.path!r} ends inside a tensor")
    return array.astype(numpy.uint16).reshape(tensor.shape)


def _adjacent_pairs(stored, heads, head_dim):
    return (
        stored.reshape(heads, 2, head_dim // 2, -1)
        .transpose(0, 2, 1, 3)
        .reshape(stored.shape)
    )


def _in_out(array):
    return array.T.copy()


def _weights(tensors, d, tied):
    def layer_array(layer, name):
        return _array(tensors[_LAYER.format(layer) + name + ".weight"])

    def joined(layer):
        q = _adjacent_pairs(layer_array(layer, "self_attn.q_proj"), d.heads, d.head_dim)
        k = layer_array(layer, "self_attn.k_proj")
        k = _adjacent_pairs(k, d.kv_heads, d.head_dim)
        v = layer_array(layer, "self_attn.v_proj")
        return _in_out(numpy.concatenate((q, k, v)))

    def each(function, *name):
        return tuple(function(layer, *name) for layer in range(d.layers))

    def linear(layer, name):
        return _in_out(layer_array(layer, name))

    embedding = _array(tensors[_EMBEDDING])
    return Weights(
        embedding=embedding,
        attention_norm=each(layer_array, "input_layernorm"),
        qkv=each(joined),
        o=each(linear, "self_attn.o_proj"),
        ffn_norm=each(layer_array, "post_attention_layernorm"),
        gate=each(linear, "mlp.gate_proj"),
        up=each(linear, "mlp.up_proj"),
        down=each(linear, "mlp.down_proj"),
        norm=_array(tensors[_NORM]),
        lm_head=_head(tensors, embedding, tied),
    )


def _head(tensors, embedding, tied):
    if _HEAD not in tensors:
        return _in_out(embedding)
    head = _array(tensors[_HEAD])
    if tied and not numpy.array_equal(head, embedding):
        _refuse(TIED_HEAD_DIFFERS, f"tied, and {_HEAD!r} differs from {_EMBEDDING!r}")
    return _in_out(head)
