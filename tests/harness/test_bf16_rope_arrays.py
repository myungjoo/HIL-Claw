import math
import re
import struct
import types
import zlib

import numpy as np
import pytest

from hilclaw import keys, rope_bf16_contract, rope_table
from hilclaw.harness import (
    bf16_rope_arrays,
    bf16_verification_arrays,
    verification_arrays,
)
from hilclaw.harness.bf16_rope_arrays import (
    TABLE_CONSTANTS,
    Counts,
    VerificationArgumentError,
    check_value,
    count_failures,
    draw_x,
    reference,
    table_rows,
)

pytestmark = pytest.mark.filterwarnings("error")

MASK = 2**64 - 1
GOLDEN = 0x9E3779B97F4A7C15
SEEDS = [0, 1, 2**63, 2**64 - 1]
DRAWS = [0, 1, 2**64 - 2]
SHAPES = [(1, 1, 2), (3, 2, 4), (2, 5, 6)]
TABLE = {
    "theta": 500000.0,
    "scale_factor": 8.0,
    "low_freq_factor": 1.0,
    "high_freq_factor": 4.0,
    "old_context_len": 8192,
}
NAN = 0x7FC0
ATOL = 2**-8 + 2**-21

BAD_DIMS = [
    [1, 2, 4],
    (1, 2),
    (1, 2, 4, 1),
    (True, 2, 4),
    (1, 0, 4),
    (-1, 2, 4),
    (1, 2, 4.0),
    (1, 2, 3),
    None,
    "124",
    (1, 2, np.int64(4)),
]
BAD_STARTS = [-1, True, 0.0, 1.5, None, "0", np.int64(0)]
BAD_SEEDS = [-1, 2**64, 1.5, True, None, np.uint64(7)]
BAD_DRAWS = [-1, 2**64 - 1, 0.0, True, None, np.int64(0)]
BAD_TOLERANCES = [-1, -1e-9, math.nan, math.inf, True, "0.1", None, 10**400]


def mix(x):
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK
    return x ^ (x >> 31)


def pattern_at(seed, draw, element):
    base = mix((seed + (draw + 1) * GOLDEN) & MASK)
    index = mix((base + (element + 1) * GOLDEN) & MASK) >> 56
    sign, fraction = divmod(index, 128)
    return (0x8000 if sign else 0) + 0x3F00 + fraction


def built(d, positions):
    return rope_table.build(head_dim=d, positions=positions, **TABLE)


def value_of(pattern):
    return struct.unpack("=f", struct.pack("=I", int(pattern) << 16))[0]


def float_bits(value):
    return struct.unpack("=I", struct.pack("=f", value))[0]


def to_bf16(values):
    """Round float64 values to bf16 patterns, nearest with ties to even, through binary32."""
    bits = values.astype(np.float32).view(np.uint32).astype(np.uint64)
    rounded = (bits + 0x7FFF + ((bits >> 16) & 1)) >> 16
    return rounded.astype(np.uint16)


def arbitrary_rows(m, d):
    rng = np.random.default_rng(1234)
    return rng.uniform(-1.0, 1.0, size=(m, d)).astype(np.float32)


def scalar_reference(x, rows):
    m, h, d = x.shape
    out = np.empty((m, h, d), dtype=np.float64)
    for i in range(m):
        for j in range(h):
            for p in range(d // 2):
                x0 = value_of(x[i, j, 2 * p])
                x1 = value_of(x[i, j, 2 * p + 1])
                c = float(rows[i, 2 * p])
                s = float(rows[i, 2 * p + 1])
                out[i, j, 2 * p] = x0 * c - x1 * s
                out[i, j, 2 * p + 1] = x0 * s + x1 * c
    return out


def test_public_names():
    assert bf16_rope_arrays.Counts is verification_arrays.Counts
    assert bf16_rope_arrays.VerificationArgumentError is (
        verification_arrays.VerificationArgumentError
    )
    assert set(bf16_rope_arrays.__all__) == {
        "TABLE_CONSTANTS",
        "Counts",
        "VerificationArgumentError",
        "check_value",
        "count_failures",
        "draw_x",
        "reference",
        "table_rows",
    }


def test_table_constants():
    assert isinstance(TABLE_CONSTANTS, types.MappingProxyType)
    assert dict(TABLE_CONSTANTS) == TABLE
    with pytest.raises(TypeError):
        TABLE_CONSTANTS["theta"] = 1.0


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("draw", DRAWS)
def test_draw_x_agrees_with_generator(shape, seed, draw):
    m, h, d = shape
    first, _ = bf16_verification_arrays.draw_inputs(
        "elementwise_add", (m * h, d), seed=seed, draw=draw
    )
    x = draw_x(shape, seed=seed, draw=draw)
    np.testing.assert_array_equal(x, first.reshape(m, h, d))


@pytest.mark.parametrize("seed", [0, 2**64 - 1])
@pytest.mark.parametrize("draw", [0, 2**64 - 2])
def test_draw_x_elements_from_formula(seed, draw):
    m, h, d = 2, 3, 4
    x = draw_x((m, h, d), seed=seed, draw=draw)
    assert x.dtype == np.uint16
    assert x.shape == (m, h, d)
    assert x.flags["C_CONTIGUOUS"]
    for i, j, k in [(0, 0, 0), (0, 2, 3), (1, 1, 2), (1, 2, 3)]:
        assert x[i, j, k] == pattern_at(seed, draw, (i * h + j) * d + k)


def test_draw_x_patterns_in_contract_set():
    x = draw_x((8, 4, 64), seed=7, draw=3)
    allowed = set(rope_bf16_contract.X_PATTERNS)
    assert set(np.unique(x).tolist()) <= allowed
    assert len(np.unique(x)) > 200


def test_draw_x_draws_differ():
    assert not np.array_equal(
        draw_x((2, 2, 8), seed=5, draw=0), draw_x((2, 2, 8), seed=5, draw=1)
    )


@pytest.mark.parametrize("shape", [(1, 1, 64), (3, 2, 64), (4, 1, 2), (2, 3, 6)])
def test_table_rows_start_zero(shape):
    m, _, d = shape
    rows = table_rows(shape, start=0)
    assert rows.dtype == np.float32
    assert rows.shape == (m, d)
    assert rows.flags["C_CONTIGUOUS"]
    assert np.all(rows[0, 0::2] == 1.0)
    assert np.all(rows[0, 1::2].view(np.uint32) == 0)
    np.testing.assert_array_equal(rows.view(np.uint32), built(d, m).view(np.uint32))


def test_table_rows_start_127():
    rows = table_rows((1, 8, 64), start=127)
    assert rows.shape == (1, 64)
    np.testing.assert_array_equal(
        rows.view(np.uint32), built(64, 128)[127:].view(np.uint32)
    )


def test_table_rows_middle_slice():
    rows = table_rows((3, 1, 6), start=5)
    np.testing.assert_array_equal(rows.view(np.uint32), built(6, 8)[5:].view(np.uint32))


def test_table_rows_fresh_array():
    first = table_rows((2, 1, 4), start=1)
    first[...] = 9.0
    second = table_rows((2, 1, 4), start=1)
    np.testing.assert_array_equal(
        second.view(np.uint32), built(4, 3)[1:].view(np.uint32)
    )
    assert not np.shares_memory(first, second)


def test_table_rows_one_build_per_call(monkeypatch):
    calls = []
    real = rope_table.build

    def counting(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(rope_table, "build", counting)
    table_rows((2, 1, 4), start=3)
    table_rows((2, 1, 4), start=3)
    assert calls == [dict(head_dim=4, positions=5, **TABLE)] * 2


def check_of(x, rows):
    return zlib.crc32(x.tobytes() + rows.tobytes())


def test_check_value_bytes():
    x = draw_x((2, 3, 4), seed=1, draw=0)
    rows = arbitrary_rows(2, 4)
    value = check_value(x, rows)
    assert type(value) is int
    assert value == check_of(x, rows)


def test_check_value_detects_changes():
    x = draw_x((2, 3, 4), seed=1, draw=0)
    rows = arbitrary_rows(2, 4)
    value = check_value(x, rows)
    changed = x.copy()
    changed[1, 2, 3] ^= 1
    assert check_value(changed, rows) != value
    flipped = rows.copy()
    flipped.view(np.uint32)[1, 2] ^= 1
    assert check_value(x, flipped) != value


def test_check_value_non_contiguous():
    x = draw_x((2, 3, 4), seed=2, draw=0)
    rows = arbitrary_rows(2, 4)
    wide_x = np.zeros((2, 3, 8), np.uint16)
    wide_x[..., ::2] = x
    wide_rows = np.zeros((2, 8), np.float32)
    wide_rows[:, ::2] = rows
    view_x, view_rows = wide_x[..., ::2], wide_rows[:, ::2]
    assert not view_x.flags["C_CONTIGUOUS"]
    assert not view_rows.flags["C_CONTIGUOUS"]
    assert check_value(view_x, view_rows) == check_value(x, rows)


def test_check_value_special_rows_by_bytes():
    x = draw_x((1, 1, 4), seed=0, draw=0)
    bits = np.array([[0x7FC00001, 0xFFC12345, 0x80000000, 0x7F800000]], np.uint32)
    rows = bits.view(np.float32)
    assert check_value(x, rows) == zlib.crc32(x.tobytes() + bits.tobytes())
    other = np.array([[0x7FC00002, 0xFFC12345, 0x00000000, 0x7F800000]], np.uint32)
    assert check_value(x, other.view(np.float32)) != check_value(x, rows)


def test_reference_row_zero_is_identity():
    x = draw_x((1, 4, 64), seed=3, draw=0)
    rows = table_rows((1, 4, 64), start=0)
    expected = bf16_verification_arrays.widen(x.reshape(4, 64)).reshape(1, 4, 64)
    result = reference(x, rows)
    assert result.dtype == np.float64
    assert result.shape == (1, 4, 64)
    np.testing.assert_array_equal(result, expected)


def test_reference_matches_scalar_loop():
    x = draw_x((3, 2, 6), seed=11, draw=4)
    rows = arbitrary_rows(3, 6)
    np.testing.assert_array_equal(reference(x, rows), scalar_reference(x, rows))


def test_reference_row_per_token_for_all_heads():
    m, h, d = 3, 4, 2
    x = np.full((m, h, d), 0x3F80, np.uint16)
    x[..., 1] = 0
    rows = np.array([[0.5, 0.25], [0.125, -1.0], [-0.75, 2.0]], np.float32)
    result = reference(x, rows)
    for i in range(m):
        for j in range(h):
            assert result[i, j, 0] == float(rows[i, 0])
            assert result[i, j, 1] == float(rows[i, 1])


def test_reference_nan_row_propagates_without_warning():
    x = draw_x((2, 2, 4), seed=0, draw=0)
    rows = arbitrary_rows(2, 4)
    rows[1, 0] = np.nan
    rows[1, 3] = np.inf
    result = reference(x, rows)
    assert np.all(np.isfinite(result[0]))
    assert np.all(np.isnan(result[1, :, 0]))
    assert np.all(np.isnan(result[1, :, 1]))
    assert not np.any(np.isfinite(result[1, :, 2:]))


def test_count_failures_bf16_rounding_passes():
    shape = (4, 3, 64)
    x = draw_x(shape, seed=9, draw=1)
    rows = table_rows((4, 1, 64), start=0)
    expected = reference(x, rows)
    output = to_bf16(expected)
    assert count_failures(output, expected, rtol=0, atol=ATOL) == Counts(0, 0)


def test_count_failures_nan_and_one_off():
    shape = (2, 2, 4)
    x = draw_x(shape, seed=1, draw=1)
    rows = arbitrary_rows(2, 4)
    expected = reference(x, rows)
    output = to_bf16(expected)
    output[0, 0, 0] = NAN
    output[1, 1, 3] = NAN
    assert count_failures(output, expected, rtol=0, atol=ATOL) == Counts(2, 2)
    output = to_bf16(expected)
    output[1, 0, 2] = to_bf16(np.array([expected[1, 0, 2] + 1.0]))[0]
    result = count_failures(output, expected, rtol=0, atol=ATOL)
    assert type(result) is Counts
    assert result == Counts(1, 0)


def test_count_failures_non_contiguous():
    expected = np.zeros((2, 2, 8), np.float64)[..., ::2]
    output = np.zeros((2, 2, 8), np.uint16)[..., ::2]
    assert count_failures(output, expected, rtol=0, atol=0) == Counts(0, 0)


def raises(name):
    return pytest.raises(
        VerificationArgumentError, match=rf"^{re.escape(name)}: must be "
    )


@pytest.mark.parametrize("dims", BAD_DIMS)
def test_bad_dims_refused_everywhere(dims, monkeypatch):
    monkeypatch.setattr(rope_table, "build", _not_called)
    for call in (
        lambda: table_rows(dims, start=0),
        lambda: draw_x(dims, seed=0, draw=0),
    ):
        with pytest.raises(
            VerificationArgumentError, match=r"^dims(\[\d\])?: must be "
        ):
            call()


def test_dims_messages():
    with raises("dims"):
        draw_x([1, 2, 4], seed=0, draw=0)
    with raises("dims"):
        draw_x((1, 2), seed=0, draw=0)
    with raises("dims[0]"):
        draw_x((True, 2, 4), seed=0, draw=0)
    with raises("dims[1]"):
        draw_x((1, 0, 4), seed=0, draw=0)
    with raises("dims[2]"):
        draw_x((1, 2, -4), seed=0, draw=0)
    with pytest.raises(
        VerificationArgumentError, match=r"^dims\[2\]: must be even, got int 3$"
    ):
        draw_x((1, 2, 3), seed=0, draw=0)
    with raises("dims[0]"):
        draw_x((0, 2, 3), seed=0, draw=0)


def _not_called(**kwargs):
    raise AssertionError("rope_table.build was called")


@pytest.mark.parametrize("start", BAD_STARTS)
def test_bad_start_refused(start, monkeypatch):
    monkeypatch.setattr(rope_table, "build", _not_called)
    with raises("start"):
        table_rows((1, 1, 2), start=start)


@pytest.mark.parametrize(
    ("dims", "start"),
    [
        ((1, 1, 2), keys.MAX_INTEGER // 2),
        ((3, 1, 64), keys.MAX_INTEGER // 64 - 2),
        ((1, 1, 2), 2**64),
    ],
)
def test_start_beyond_table_limit_refused_before_build(dims, start, monkeypatch):
    monkeypatch.setattr(rope_table, "build", _not_called)
    with raises("start"):
        table_rows(dims, start=start)


def test_start_at_table_limit_reaches_build(monkeypatch):
    seen = []

    def fake(**kwargs):
        seen.append(kwargs)
        return np.zeros((1, kwargs["head_dim"]), np.float32)

    monkeypatch.setattr(rope_table, "build", fake)
    start = (keys.MAX_INTEGER - 1) // 2 - 1
    assert (start + 1) * 2 <= keys.MAX_INTEGER
    table_rows((1, 1, 2), start=start)
    assert seen[0]["positions"] == start + 1


def test_start_is_keyword_only_without_default():
    with pytest.raises(TypeError):
        table_rows((1, 1, 2), 0)
    with pytest.raises(TypeError):
        table_rows((1, 1, 2))


@pytest.mark.parametrize("seed", BAD_SEEDS)
def test_bad_seed_refused(seed):
    with raises("seed"):
        draw_x((1, 1, 2), seed=seed, draw=0)


@pytest.mark.parametrize("draw", BAD_DRAWS)
def test_bad_draw_refused(draw):
    with raises("draw"):
        draw_x((1, 1, 2), seed=0, draw=draw)


GOOD_X = np.zeros((2, 3, 4), np.uint16)
GOOD_ROWS = np.zeros((2, 4), np.float32)
BAD_X = [
    GOOD_X.astype(np.int16),
    GOOD_X.astype(np.float32),
    GOOD_X.reshape(6, 4),
    GOOD_X.reshape(1, 2, 3, 4),
    np.zeros((2, 0, 4), np.uint16),
    GOOD_X.tolist(),
    None,
]
BAD_ROWS = [
    GOOD_ROWS.astype(np.float64),
    GOOD_ROWS.astype(np.uint32),
    GOOD_ROWS.reshape(2, 4, 1),
    GOOD_ROWS.reshape(8),
    np.zeros((0, 4), np.float32),
    GOOD_ROWS.tolist(),
    np.zeros((3, 4), np.float32),
    np.zeros((2, 6), np.float32),
]


@pytest.mark.parametrize("function", [check_value, reference])
@pytest.mark.parametrize("x", BAD_X)
def test_bad_x_refused(function, x):
    with raises("x"):
        function(x, GOOD_ROWS)


@pytest.mark.parametrize("function", [check_value, reference])
@pytest.mark.parametrize("rows", BAD_ROWS)
def test_bad_rows_refused(function, rows):
    with raises("rows"):
        function(GOOD_X, rows)


@pytest.mark.parametrize("rtol", BAD_TOLERANCES)
def test_bad_rtol_refused(rtol):
    with raises("rtol"):
        count_failures(None, None, rtol=rtol, atol=0)


@pytest.mark.parametrize("atol", BAD_TOLERANCES)
def test_bad_atol_refused(atol):
    with raises("atol"):
        count_failures(None, None, rtol=0, atol=atol)


GOOD_EXPECTED = np.zeros((2, 3, 4), np.float64)


@pytest.mark.parametrize(
    "output",
    [
        GOOD_X.astype(np.float32),
        GOOD_X.reshape(6, 4),
        np.zeros((2, 3, 0), np.uint16),
        GOOD_X.tolist(),
        np.zeros((2, 3, 6), np.uint16),
    ],
)
def test_bad_output_refused(output):
    with raises("output"):
        count_failures(output, GOOD_EXPECTED, rtol=0, atol=0)


@pytest.mark.parametrize(
    "expected",
    [
        GOOD_EXPECTED.astype(np.float32),
        GOOD_EXPECTED.reshape(6, 4),
        np.zeros((0, 3, 4), np.float64),
        None,
    ],
)
def test_bad_expected_refused(expected):
    with raises("expected"):
        count_failures(GOOD_X, expected, rtol=0, atol=0)
