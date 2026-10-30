"""Model-level float64 reference and teacher-forced logit comparison of the bf16 forward pass (ADR-0176).

``ARCHITECTURE/decisions/ADR-0176-od31-model-level-reference-and-comparison.md``
is the rule (decisions 2 to 4, code slice 1), over the forward pass of
``ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md``. The owner's
answer to HQ-0071 fixes the parts this module follows: the reference of the
synthetic run is a NumPy float64 implementation, and the run is compared by
teacher forcing, row by row, element by element, with ``rtol`` and ``atol``
the caller gives and no default.

Its parts:

* :func:`reference_logits`: the float64 logits rows of one teacher-forced
  generation, from the arguments :func:`hilclaw.model_forward_execute.execute`
  takes in the given-sequence mode, ``generation_length`` excepted. With S the prompt's length and G the number of given tokens, the
  S + G - 1 fed tokens are the prompt and the given tokens but the last; the
  pass over them is computed once, causally, which gives at each position
  what ADR-0166's prefill and decode passes give there through the cache
  (ADR-0162 decisions 4 and 15). Every bf16 input is widened exactly
  (pattern ``p`` to the binary32 pattern ``p << 16``, then to float64) and
  every activation stays float64, with no rounding between operations. The
  RoPE rotation uses the binary32 table of :func:`hilclaw.rope_table.build`
  for positions 0 to S + G - 2, widened; RMSNorm uses the binary32 value of
  :func:`hilclaw.model_binding.rmsnorm_eps`; query head ``j`` attends with
  KV head ``j // (H // H_kv)`` over positions 0 to its own, scores scaled by
  ``1 / sqrt(head_dim)``. The rows are those the executor reports: all
  S + G - 1 positions for ``"all"``, positions S - 1 to S + G - 2 (the last
  row of each pass) for ``"last"``.
* :func:`compare`: the comparison of a
  :class:`hilclaw.model_forward_run.ForwardReport`'s logits with such rows.
  Element ``(r, c)`` passes exactly when the widened output is finite, the
  reference is finite and ``|output - reference| <= atol + rtol * |reference|``
  holds in float64.
* :class:`LogitComparison`: what :func:`compare` returns.

Conventions of this module (readings of ADR-0176, not rules of the record):

* The arguments :func:`reference_logits` shares with
  :func:`hilclaw.model_forward_check.check` are checked by that function at
  the dtype ``"bf16"``, with ``generation_length`` the length of ``given``
  and no binding: what it raises is passed on, and its ``"invalid_input"`` reasons,
  joined with ``"; "``, are raised as one :class:`ValueError`.
* ``given`` ``None`` raises :class:`ValueError`: a teacher-forced reference
  needs every fed token.
* A weight holding a NaN or infinity pattern is not refused; its effect on
  the reference propagates, and :func:`compare` fails each element whose
  reference is not finite.

What this module does not do: it builds, starts and runs nothing, and reads
and writes no file; it has no token selection rule and no generation mode,
which the forward program has (ADR-0176 decision 5): a generated run is
compared by passing its selected tokens as ``given``; it holds no tolerance value,
prompt, length or model parameter and gives none a default (HQ-0070); it
casts no array of its caller and keeps nothing between calls.
"""

import math
from typing import NamedTuple

import numpy as np

from hilclaw import model_binding, model_forward_check, rope_table
from hilclaw.model_forward_run import ForwardReport
from hilclaw.model_run import _is_sequence


class LogitComparison(NamedTuple):
    """Outcome of one :func:`compare` call.

    ``ok`` is true exactly when ``failed`` is 0. ``failed`` counts the
    elements that do not pass; ``non_finite`` the elements of the output that
    are NaN or an infinity and ``reference_non_finite`` those of the reference,
    each also counted in ``failed``. ``row_failures`` holds the count of
    failing elements of each row, in row order. ``first`` is ``(row, column)``
    of the first failing element in row-major order, or ``None``.
    """

    ok: bool
    failed: int
    non_finite: int
    reference_non_finite: int
    row_failures: tuple
    first: tuple | None


def reference_logits(dimensions, *, eps, rope, weights, prompt, given, lm_head_rows):
    """Return the float64 logits rows of one teacher-forced generation, shape (rows, V).

    ``dimensions`` is a :class:`hilclaw.model_binding.ModelDimensions`;
    ``eps`` is exactly a ``float``; ``rope`` is a
    :class:`hilclaw.model_forward_check.RopeConstants`; ``weights`` is a
    :class:`hilclaw.model_forward_check.Weights` of ``numpy.uint16`` arrays of
    bf16 patterns; ``prompt`` and ``given`` are sequences of ``int`` token ids;
    ``lm_head_rows`` is ``"all"`` or ``"last"``. No argument has a default.
    The rows are S + G - 1 for ``"all"`` and G for ``"last"``, in the order of
    a :class:`hilclaw.model_forward_run.ForwardReport`.

    Raised before anything is computed: :class:`ValueError` for ``given``
    ``None`` and :class:`TypeError` for ``given`` that is no sequence; then
    what :func:`hilclaw.model_forward_check.check` raises, and
    :class:`ValueError` with its ``"invalid_input"`` reasons. The arguments
    are not modified.
    """
    if given is None:
        raise ValueError(
            "given: is None; the teacher-forced reference needs the given tokens"
        )
    if not _is_sequence(given):
        raise TypeError(f"given: must be a sequence, got {type(given).__name__}")
    result = model_forward_check.check(
        dimensions,
        {},
        dtype="bf16",
        eps=eps,
        rope=rope,
        weights=weights,
        prompt=prompt,
        given=given,
        generation_length=len(given),
        lm_head_rows=lm_head_rows,
    )
    reasons = [
        outcome.reason
        for outcome in result.outcomes
        if outcome.kind == model_binding.INVALID_INPUT
    ]
    if reasons:
        raise ValueError("; ".join(reasons))
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return _forward(dimensions, eps, rope, weights, prompt, given, lm_head_rows)


def compare(report, expected, *, rtol, atol):
    """Compare a report's logits with reference rows; return a :class:`LogitComparison`.

    ``report`` is a :class:`hilclaw.model_forward_run.ForwardReport` whose
    ``logits`` is a two-dimensional ``numpy.uint16`` array of bf16 patterns;
    ``expected`` is a ``numpy.float64`` array of the same shape, as
    :func:`reference_logits` returns for the arguments of the run. ``rtol`` and
    ``atol`` are each an ``int`` or a ``float``, finite and not negative; they
    have no default. The predicate is the one of the module docstring.

    Raised, in this order: :class:`TypeError` or :class:`ValueError` for
    ``rtol``, then ``atol`` (``parameter`` the argument's name); then
    :class:`TypeError` for a ``report`` that is no
    :class:`~hilclaw.model_forward_run.ForwardReport` or whose ``logits`` is
    not a two-dimensional ``uint16`` array (``parameter`` ``"report"``) and
    for ``expected`` that is not a two-dimensional ``float64`` array
    (``parameter`` ``"expected"``); then :class:`ValueError` for shapes that
    differ (``parameter`` ``"report"``). Nothing is modified.
    """
    _tolerance("rtol", rtol)
    _tolerance("atol", atol)
    if not isinstance(report, ForwardReport):
        _fail(
            TypeError, "report", f"must be a ForwardReport, got {type(report).__name__}"
        )
    _matrix("report", "logits", report.logits, np.uint16)
    _matrix("expected", "expected", expected, np.float64)
    if report.logits.shape != expected.shape:
        _fail(
            ValueError,
            "report",
            f"logits has the shape {report.logits.shape}, "
            f"not that of expected, {expected.shape}",
        )
    output = _wide(report.logits)
    finite = np.isfinite(output)
    reference_finite = np.isfinite(expected)
    with np.errstate(over="ignore", invalid="ignore"):
        within = np.abs(output - expected) <= float(atol) + float(rtol) * np.abs(
            expected
        )
    failing = ~(finite & reference_finite & within)
    failed = int(np.count_nonzero(failing))
    first = None
    if failed:
        row, column = np.unravel_index(int(np.argmax(failing)), failing.shape)
        first = (int(row), int(column))
    return LogitComparison(
        failed == 0,
        failed,
        int(np.count_nonzero(~finite)),
        int(np.count_nonzero(~reference_finite)),
        tuple(int(count) for count in np.count_nonzero(failing, axis=1)),
        first,
    )


def _forward(dimensions, eps, rope, weights, prompt, given, lm_head_rows):
    d = dimensions
    prompt_length = len(prompt)
    positions = prompt_length + len(given) - 1
    fed = np.array([*prompt, *given][:positions], dtype=np.intp)
    table = rope_table.build(
        head_dim=d.head_dim, positions=positions, **rope._asdict()
    ).astype(np.float64)
    cos, sin = table[:, np.newaxis, 0::2], table[:, np.newaxis, 1::2]
    epsilon = model_binding.rmsnorm_eps(eps)
    q_width, kv_width = d.heads * d.head_dim, d.kv_heads * d.head_dim
    group = d.heads // d.kv_heads
    scale = 1 / math.sqrt(d.head_dim)
    future = np.triu(np.ones((positions, positions), dtype=bool), 1)
    x = _wide(weights.embedding)[fed]
    for layer in range(d.layers):
        normed = _rmsnorm(x, _wide(weights.attention_norm[layer]), epsilon)
        qkv = normed @ _wide(weights.qkv[layer])
        q = _rotate(qkv[:, :q_width].reshape(positions, d.heads, d.head_dim), cos, sin)
        k = _rotate(
            qkv[:, q_width : q_width + kv_width].reshape(
                positions, d.kv_heads, d.head_dim
            ),
            cos,
            sin,
        )
        v = qkv[:, q_width + kv_width :].reshape(positions, d.kv_heads, d.head_dim)
        attention = np.empty((positions, d.heads, d.head_dim))
        for head in range(d.heads):
            kv_head = head // group
            scores = (q[:, head, :] @ k[:, kv_head, :].T) * scale
            scores[future] = -np.inf
            scores -= scores.max(axis=1, keepdims=True)
            weights_of_row = np.exp(scores)
            weights_of_row /= weights_of_row.sum(axis=1, keepdims=True)
            attention[:, head, :] = weights_of_row @ v[:, kv_head, :]
        h = x + attention.reshape(positions, q_width) @ _wide(weights.o[layer])
        normed = _rmsnorm(h, _wide(weights.ffn_norm[layer]), epsilon)
        gate = normed @ _wide(weights.gate[layer])
        up = normed @ _wide(weights.up[layer])
        x = h + (gate / (1 + np.exp(-gate)) * up) @ _wide(weights.down[layer])
    normed = _rmsnorm(x, _wide(weights.norm), epsilon)
    if lm_head_rows == "last":
        normed = normed[prompt_length - 1 :]
    return normed @ _wide(weights.lm_head)


def _wide(patterns):
    words = np.asarray(patterns, dtype=np.uint16).astype(np.uint32) << 16
    return words.view(np.float32).astype(np.float64)


def _rmsnorm(x, w, epsilon):
    return x * w / np.sqrt(np.mean(x * x, axis=1, keepdims=True) + epsilon)


def _rotate(x, cos, sin):
    first, second = x[..., 0::2], x[..., 1::2]
    out = np.empty(x.shape)
    out[..., 0::2] = first * cos - second * sin
    out[..., 1::2] = first * sin + second * cos
    return out


def _tolerance(name, value):
    if type(value) not in (int, float):
        _fail(TypeError, name, f"must be an int or a float, got {type(value).__name__}")
    try:
        valid = 0 <= float(value) < math.inf
    except OverflowError:
        valid = False
    if not valid:
        _fail(ValueError, name, f"must be finite and not negative, got {value!r}")


def _matrix(parameter, name, value, dtype):
    if not isinstance(value, np.ndarray) or value.ndim != 2 or value.dtype != dtype:
        shown = (
            f"{value.dtype} array of {value.ndim} dimensions"
            if isinstance(value, np.ndarray)
            else type(value).__name__
        )
        _fail(
            TypeError,
            parameter,
            f"{name} must be a two-dimensional {np.dtype(dtype).name} array, got {shown}",
        )


def _fail(error_class, parameter, message):
    error = error_class(f"{parameter}: {message}")
    error.parameter = parameter
    raise error
