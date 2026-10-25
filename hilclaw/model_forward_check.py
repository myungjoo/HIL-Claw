"""Whole-generation check of the bf16 forward pass of the model executor (ADR-0166 decision 6).

``ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`` is the rule.
Before anything is built, one check takes the model parameters (the
dimensions, the dtype, ``eps``, the RoPE constants), the weights, one binding
mapping over the fifteen call-site names of the six kinds, the prompt, the
given tokens, the generation length and ``lm_head_rows``. It splits the
binding by call site and runs **all six** checks of
:mod:`hilclaw.model_binding`, in the order :func:`~hilclaw.model_binding.check`,
:func:`~hilclaw.model_binding.check_rmsnorm`,
:func:`~hilclaw.model_binding.check_elementwise_add`,
:func:`~hilclaw.model_binding.check_swiglu`,
:func:`~hilclaw.model_binding.check_rope`,
:func:`~hilclaw.model_binding.check_sdpa`, with ``prompt_length`` the length of
the prompt for the five that take it. The join reports all outcomes, not the
first: this module's own ``"invalid_input"`` outcomes, then the six checks'
outcomes in that order; an ``"invalid_input"`` reason whose text equals an
earlier one's is given once, and reasons of different text for one cause are
all kept. The result is ``ok`` exactly when there is no outcome; then its
calls are the six checks' calls in the same order.

Its parts:

* :class:`RopeConstants`: the five RoPE constants of ADR-0166 decision 4,
  named as the arguments of :func:`hilclaw.rope_table.build`.
* :class:`Weights`: the weights of ADR-0166 decision 4.
* :func:`check`: the whole-generation check.

Conventions of this module (readings of decision 6, not rules of the record):

* A binding key that is none of the fifteen call-site names makes the binding
  malformed (:class:`ValueError`, ``parameter`` ``"binding"``). Each check
  gets the sub-mapping of the keys among its own call sites, an empty mapping
  when there is none, so a call site absent from the binding is reported by
  its check as ``"no_kernel"``.
* The six checks run first, so their :class:`TypeError` and
  :class:`ValueError` for a malformed argument (an odd ``head_dim`` from the
  RoPE check included) are raised unchanged before this module looks at
  ``eps``, ``rope`` and ``weights``, which it then refuses by type in that
  order.
* This module's own ``"invalid_input"`` outcomes come in this order: the
  generation mode (``given`` is ``None``: it has no token selection rule,
  ADR-0166 decision 7, OD-31 sub-question 6); ``eps`` refused by
  :func:`hilclaw.model_binding.rmsnorm_eps`; one per RoPE constant whose
  value :func:`hilclaw.rope_table.constant_refusals` refuses, in field
  order; the table size, ``positions * head_dim`` above 2**53 - 1 with
  ``positions`` = S + G - 1 (looked at only when the prompt is not empty and
  G is from 1 to 2**53 - 1); then the weights in field order, for a per-layer
  weight its array count and then each array in layer order, each array's
  shape and then, at the dtype ``"bf16"`` only, its element type.
* A weight is a :class:`numpy.ndarray`; a per-layer weight is a sequence
  (not an array) of them, one per layer. Its shape is compared with the one
  ADR-0166 decision 4 gives from the dimensions, which the six checks have
  already found valid; at ``"bf16"`` its element type must be
  ``numpy.uint16`` in native byte order (a bf16 pattern). At any other dtype the
  element types are not checked, since no operand gives one to compare with.

What this module does not do: it builds, loads and starts nothing, runs no
process and reads and writes no file; it builds no RoPE table and computes no
frequency; it has no token selection rule, no model-level reference and no
tolerance (OD-31 sub-question 6, HQ-0071); it gives no default to any model
parameter or RoPE constant (HQ-0070) and sets no cache capacity; it adds no
outcome kind to those of :mod:`hilclaw.model_binding`.

Every :class:`TypeError` or :class:`ValueError` raised here carries the
attribute ``parameter``. Arguments are not modified.
"""

import contextlib
from collections.abc import Mapping, Sequence
from typing import NamedTuple

import numpy

from hilclaw import keys, model_binding, rope_table

_PER_LAYER = ("attention_norm", "qkv", "o", "ffn_norm", "gate", "up", "down")


class RopeConstants(NamedTuple):
    """The five RoPE constants of ADR-0166 decision 4, each an ``int`` or a ``float``, given by the caller.

    ``theta``, ``scale_factor``, ``low_freq_factor``, ``high_freq_factor``
    and ``old_context_len`` are θ, s, a, b and L of ADR-0161 decision 4, the
    arguments of :func:`hilclaw.rope_table.build`. None has a default.
    """

    theta: object
    scale_factor: object
    low_freq_factor: object
    high_freq_factor: object
    old_context_len: object


class Weights(NamedTuple):
    """The weights of ADR-0166 decision 4, made by the caller, each in the layout of the operand that receives it.

    With the dimensions' D, F, V, N, H, H_kv and d and W = (H + 2·H_kv)·d:
    ``embedding`` (V, D); the per-layer sequences of N arrays
    ``attention_norm`` (D,), ``qkv`` (D, W) with the Q, K and V ranges in
    that column order, ``o`` (H·d, D), ``ffn_norm`` (D,), ``gate`` and
    ``up`` (D, F), ``down`` (F, D); then ``norm`` (D,) and ``lm_head``
    (D, V). At ``"bf16"`` each array holds bf16 patterns as
    ``numpy.uint16``. None has a default.
    """

    embedding: object
    attention_norm: object
    qkv: object
    o: object
    ffn_norm: object
    gate: object
    up: object
    down: object
    norm: object
    lm_head: object


_CHECKS = (
    ("check", model_binding.CALL_SITES),
    ("check_rmsnorm", model_binding.RMSNORM_CALL_SITES),
    ("check_elementwise_add", model_binding.ELEMENTWISE_ADD_CALL_SITES),
    ("check_swiglu", model_binding.SWIGLU_CALL_SITES),
    ("check_rope", model_binding.ROPE_CALL_SITES),
    ("check_sdpa", model_binding.SDPA_CALL_SITES),
)
_CALL_SITES = tuple(site for _, sites in _CHECKS for site in sites)


def check(
    dimensions,
    binding,
    *,
    dtype,
    eps,
    rope,
    weights,
    prompt,
    given,
    generation_length,
    lm_head_rows,
):
    """Check a whole generation of the forward pass; return a :class:`hilclaw.model_binding.BindingCheck`.

    ``dimensions`` is a :class:`hilclaw.model_binding.ModelDimensions`;
    ``binding`` maps call sites of the six kinds to non-empty sequences of
    :class:`hilclaw.model_binding.BindingEntry`; ``dtype`` is the model's
    dtype; ``eps`` is exactly a ``float``; ``rope`` is a
    :class:`RopeConstants`; ``weights`` is a :class:`Weights`; ``prompt`` and
    ``given`` are sequences of token ids, ``given`` holding
    ``generation_length`` ids; ``lm_head_rows`` is ``"all"`` or ``"last"``.
    No argument has a default.

    Raised, in this order: :class:`TypeError` (``parameter`` ``"binding"``)
    for a ``binding`` that is not a mapping and :class:`ValueError` for a key
    that is none of the fifteen call sites; whatever the six checks raise,
    unchanged; then :class:`TypeError` for ``eps`` of a wrong type
    (``parameter`` ``"eps"``), ``rope`` that is not a :class:`RopeConstants`
    (``"rope"``) or holds a constant of a wrong type (``"rope.<field>"``),
    ``weights`` that is not a :class:`Weights` (``"weights"``), and a weight
    that is not an array or a per-layer weight that is not a sequence of
    arrays (``"weights.<field>"``).

    The outcomes are this module's own ``"invalid_input"`` outcomes, in the
    order of the module docstring, then those of the six checks in their
    order, with an ``"invalid_input"`` reason equal to an earlier one's
    dropped. ``calls`` is the six checks' ``calls`` concatenated, only when
    there is no outcome. Nothing is built, started or read.
    """
    with _parameter("binding"):
        if not isinstance(binding, Mapping):
            raise TypeError(f"must be a mapping, got {type(binding).__name__}")
        for site in binding:
            if site not in _CALL_SITES:
                raise ValueError(f"key {site!r} is not a call site of {_CALL_SITES}")
    results = []
    for name, sites in _CHECKS:
        function = getattr(model_binding, name)
        part = {site: binding[site] for site in sites if site in binding}
        if name == "check":
            result = function(
                dimensions,
                part,
                dtype=dtype,
                prompt=prompt,
                generation_length=generation_length,
                lm_head_rows=lm_head_rows,
                given=given,
            )
        else:
            result = function(
                dimensions,
                part,
                dtype=dtype,
                prompt_length=len(prompt),
                generation_length=generation_length,
            )
        results.append(result)

    reasons = [] if given is not None else [_GENERATION_MODE]
    reasons += _eps(eps)
    reasons += _rope(rope, dimensions.head_dim, len(prompt), generation_length)
    reasons += _weights(weights, dimensions, dtype)

    outcomes = []
    seen = set()
    for outcome in [
        model_binding.Outcome(model_binding.INVALID_INPUT, None, None, reason)
        for reason in reasons
    ] + [outcome for result in results for outcome in result.outcomes]:
        if outcome.kind == model_binding.INVALID_INPUT:
            if outcome.reason in seen:
                continue
            seen.add(outcome.reason)
        outcomes.append(outcome)
    ok = not outcomes
    calls = tuple(call for result in results for call in result.calls) if ok else ()
    return model_binding.BindingCheck(ok, tuple(outcomes), calls)


_GENERATION_MODE = (
    "given: is None; the generation mode has no token selection rule "
    "(OD-31 sub-question 6)"
)


def _eps(eps):
    try:
        model_binding.rmsnorm_eps(eps)
    except ValueError as error:
        return [f"eps: {error}"]
    return []


def _rope(rope, head_dim, prompt_length, generation_length):
    with _parameter("rope"):
        if not isinstance(rope, RopeConstants):
            raise TypeError(f"must be a RopeConstants, got {type(rope).__name__}")
    try:
        refusals = rope_table.constant_refusals(**rope._asdict())
    except TypeError as error:
        error.parameter = f"rope.{error.parameter}"
        raise
    reasons = [f"rope.{name}: {reason}" for name, reason in refusals]
    if prompt_length and 1 <= generation_length <= keys.MAX_INTEGER:
        positions = prompt_length + generation_length - 1
        if positions * head_dim > keys.MAX_INTEGER:
            reasons.append(
                "rope: positions * head_dim must be at most 2**53 - 1, "
                f"got {positions} * {head_dim}"
            )
    return reasons


def _weights(weights, dimensions, dtype):
    with _parameter("weights"):
        if not isinstance(weights, Weights):
            raise TypeError(f"must be a Weights, got {type(weights).__name__}")
    shapes = _shapes(dimensions)
    element = dtype == "bf16"
    reasons = []
    for name, value in zip(Weights._fields, weights):
        label = f"weights.{name}"
        if name not in _PER_LAYER:
            with _parameter(label):
                _array(value, "")
            reasons += _array_reasons(value, label, shapes[name], element)
            continue
        with _parameter(label):
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                raise TypeError(
                    f"must be a sequence of numpy.ndarray, got {type(value).__name__}"
                )
            arrays = tuple(value)
            for layer, array in enumerate(arrays):
                _array(array, f"layer {layer}: ")
        if len(arrays) != dimensions.layers:
            reasons.append(
                f"{label}: has {len(arrays)} arrays, layers is {dimensions.layers}"
            )
        for layer, array in enumerate(arrays):
            reasons += _array_reasons(array, f"{label}[{layer}]", shapes[name], element)
    return reasons


def _shapes(d):
    width = (d.heads + 2 * d.kv_heads) * d.head_dim
    return {
        "embedding": (d.vocabulary, d.hidden),
        "attention_norm": (d.hidden,),
        "qkv": (d.hidden, width),
        "o": (d.heads * d.head_dim, d.hidden),
        "ffn_norm": (d.hidden,),
        "gate": (d.hidden, d.intermediate),
        "up": (d.hidden, d.intermediate),
        "down": (d.intermediate, d.hidden),
        "norm": (d.hidden,),
        "lm_head": (d.hidden, d.vocabulary),
    }


def _array(value, prefix):
    if not isinstance(value, numpy.ndarray):
        raise TypeError(f"{prefix}must be a numpy.ndarray, got {type(value).__name__}")


def _array_reasons(array, label, shape, element):
    reasons = []
    if array.shape != shape:
        reasons.append(f"{label}: has the shape {array.shape}, not {shape}")
    if element and array.dtype != numpy.uint16:
        reasons.append(f"{label}: has the element type {array.dtype}, not uint16")
    return reasons


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise
