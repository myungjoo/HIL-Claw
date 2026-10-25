import math
import re
import struct
import zlib

import numpy as np
import pytest

from hilclaw import sdpa_kv_cache_bf16_contract
from hilclaw.harness import (
    bf16_sdpa_kv_cache_arrays,
    bf16_verification_arrays,
    verification_arrays,
)
from hilclaw.harness.bf16_sdpa_kv_cache_arrays import (
    FILL,
    Counts,
    Inputs,
    VerificationArgumentError,
    allocation_after,
    allocation_before,
    check_value,
    count_cache_differences,
    count_failures,
    draw_inputs,
    reference,
)

pytestmark = pytest.mark.filterwarnings("error")

MASK = 2**64 - 1
GOLDEN = 0x9E3779B97F4A7C15
NAN = 0x7FC0
SEEDS = [0, 1, 2**63, 2**64 - 1]
DRAWS = [0, 1, 2**64 - 2]
# (m, l, h, h_kv, d): m = l = 1 with d = 1; P = 0 with h = h_kv; P = 3 with m = 1
# and h = 4*h_kv; P = 3 with m = 2; d = 1 with P = 1; P = 0 with h = 4*h_kv.
SHAPES = [
    (1, 1, 1, 1, 1),
    (2, 2, 2, 2, 3),
    (1, 4, 4, 1, 2),
    (2, 5, 4, 2, 3),
    (3, 4, 8, 2, 1),
    (3, 3, 4, 1, 2),
]
GOOD = (2, 5, 4, 2, 3)

BAD_DIMS = [
    ([2, 5, 4, 2, 3], "dims"),
    ((2, 5, 4, 2), "dims"),
    ((2, 5, 4, 2, 3, 1), "dims"),
    (None, "dims"),
    ((True, 5, 4, 2, 3), "dims[0]"),
    ((2, 0, 4, 2, 3), "dims[1]"),
    ((2, 5, -4, 2, 3), "dims[2]"),
    ((2, 5, 4, 2.0, 3), "dims[3]"),
    ((2, 5, 4, 2, np.int64(3)), "dims[4]"),
    ((2, 5, 4, 2, 0), "dims[4]"),
    ((3, 2, 4, 2, 3), "dims[1]"),
    ((2, 5, 3, 2, 3), "dims[2]"),
    ((2, 5, 1, 2, 3), "dims[2]"),
    ((0, 5, 3, 2, 3), "dims[0]"),
]
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


def value_of(pattern):
    return struct.unpack("=f", struct.pack("=I", int(pattern) << 16))[0]


def to_bf16(values):
    """Round float64 values to bf16 patterns, nearest with ties to even, through binary32."""
    bits = values.astype(np.float32).view(np.uint32).astype(np.uint64)
    rounded = (bits + 0x7FFF + ((bits >> 16) & 1)) >> 16
    return rounded.astype(np.uint16)


def sizes_of(shape):
    m, l, h, h_kv, d = shape
    cached = l - m
    return [m * h * d, m * h_kv * d, m * h_kv * d, cached * h_kv * d, cached * h_kv * d]


def expected_inputs(shape, seed, draw):
    m, l, h, h_kv, d = shape
    sizes = sizes_of(shape)
    sequence = bf16_verification_arrays.draw_inputs(
        "elementwise_add", (1, sum(sizes)), seed=seed, draw=draw
    )[0]
    parts = np.split(sequence.ravel(), np.cumsum(sizes)[:-1])
    shapes = [(m, h, d), (m, h_kv, d), (m, h_kv, d)] + [(l - m, h_kv, d)] * 2
    return [part.reshape(s) for part, s in zip(parts, shapes)]


def local_allocation(shape, cached, new=None):
    m, l, _, h_kv, d = shape
    rows = np.full((l + 2 * m, h_kv, d), NAN, np.uint16)
    rows[m : m + l - m] = cached
    if new is not None:
        rows[l : l + m] = new
    return rows


def scalar_reference(shape, inputs):
    m, l, h, h_kv, d = shape
    cached = l - m
    k = np.concatenate([inputs.cached_k, inputs.k_new])
    v = np.concatenate([inputs.cached_v, inputs.v_new])
    out = np.empty((m, h, d))
    for i in range(m):
        for j in range(h):
            g = j // (h // h_kv)
            scores = []
            for t in range(cached + i + 1):
                total = 0.0
                for e in range(d):
                    total += value_of(inputs.q[i, j, e]) * value_of(k[t, g, e])
                scores.append(total / math.sqrt(d))
            top = max(scores)
            weights = [math.exp(s - top) for s in scores]
            norm = sum(weights)
            for e in range(d):
                out[i, j, e] = (
                    sum(w * value_of(v[t, g, e]) for t, w in enumerate(weights)) / norm
                )
    return out


def raises(name):
    return pytest.raises(
        VerificationArgumentError, match=rf"^{re.escape(name)}: must be "
    )


def good_arrays(shape=GOOD):
    inputs = draw_inputs(shape, seed=3, draw=0)
    return (
        inputs,
        allocation_before(shape, inputs.cached_k),
        allocation_before(shape, inputs.cached_v),
    )


def test_public_names():
    assert bf16_sdpa_kv_cache_arrays.Counts is verification_arrays.Counts
    assert bf16_sdpa_kv_cache_arrays.VerificationArgumentError is (
        verification_arrays.VerificationArgumentError
    )
    assert set(bf16_sdpa_kv_cache_arrays.__all__) == {
        "FILL",
        "Counts",
        "Inputs",
        "VerificationArgumentError",
        "allocation_after",
        "allocation_before",
        "check_value",
        "count_cache_differences",
        "count_failures",
        "draw_inputs",
        "reference",
    }
    assert FILL == 0x7FC0
    assert Inputs._fields == ("q", "k_new", "v_new", "cached_k", "cached_v")


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("draw", DRAWS)
def test_draw_inputs_agree_with_generator(shape, seed, draw):
    inputs = draw_inputs(shape, seed=seed, draw=draw)
    assert isinstance(inputs, Inputs)
    for got, want in zip(inputs, expected_inputs(shape, seed, draw)):
        assert got.shape == want.shape
        np.testing.assert_array_equal(got, want)


@pytest.mark.parametrize("seed", [0, 2**64 - 1])
@pytest.mark.parametrize("draw", [0, 2**64 - 2])
def test_draw_inputs_elements_from_formula(seed, draw):
    m, l, h, h_kv, d = shape = (2, 5, 4, 2, 3)
    inputs = draw_inputs(shape, seed=seed, draw=draw)
    offsets = [int(o) for o in np.cumsum([0, *sizes_of(shape)])]
    for array, offset in zip(inputs, offsets):
        assert array.dtype == np.uint16
        assert array.flags["C_CONTIGUOUS"]
        rows, heads, _ = array.shape
        for i, j, e in [(0, 0, 0), (rows - 1, heads - 1, d - 1), (rows - 1, 0, 1)]:
            index = offset + (i * heads + j) * d + e
            assert array[i, j, e] == pattern_at(seed, draw, index)
    assert inputs.q.shape == (m, h, d)
    assert inputs.k_new.shape == inputs.v_new.shape == (m, h_kv, d)
    assert inputs.cached_k.shape == inputs.cached_v.shape == (l - m, h_kv, d)


def test_draw_inputs_patterns_in_value_set():
    inputs = draw_inputs((16, 48, 8, 2, 16), seed=7, draw=3)
    allowed = set(sdpa_kv_cache_bf16_contract.INPUT_PATTERNS)
    patterns = set(np.concatenate([a.ravel() for a in inputs]).tolist())
    assert patterns <= allowed
    assert len(patterns) > 200


def test_draw_inputs_views_of_one_buffer_without_overlap():
    inputs = draw_inputs(GOOD, seed=1, draw=0)
    bases = {id(array.base) for array in inputs}
    assert len(bases) == 1
    for a in range(5):
        for b in range(a + 1, 5):
            assert not np.shares_memory(inputs[a], inputs[b])


@pytest.mark.parametrize("shape", [(2, 2, 2, 2, 3), (3, 3, 4, 1, 2), (1, 1, 1, 1, 1)])
def test_draw_inputs_at_p_zero_have_empty_cached(shape):
    _, _, _, h_kv, d = shape
    inputs = draw_inputs(shape, seed=0, draw=0)
    assert inputs.cached_k.shape == inputs.cached_v.shape == (0, h_kv, d)
    assert inputs.cached_k.dtype == np.uint16
    assert inputs.cached_k.flags["C_CONTIGUOUS"]


def test_draw_inputs_draws_differ():
    first = draw_inputs(GOOD, seed=5, draw=0)
    second = draw_inputs(GOOD, seed=5, draw=1)
    assert not np.array_equal(first.q, second.q)


@pytest.mark.parametrize("shape", SHAPES)
def test_allocations_match_local_construction(shape):
    m, l, _, h_kv, d = shape
    inputs = draw_inputs(shape, seed=11, draw=1)
    before = allocation_before(shape, inputs.cached_k)
    after = allocation_after(shape, inputs.cached_v, inputs.v_new)
    for result in (before, after):
        assert result.dtype == np.uint16
        assert result.shape == (l + 2 * m, h_kv, d)
        assert result.flags["C_CONTIGUOUS"]
    np.testing.assert_array_equal(before, local_allocation(shape, inputs.cached_k))
    np.testing.assert_array_equal(
        after, local_allocation(shape, inputs.cached_v, inputs.v_new)
    )
    assert (before[:m] == FILL).all()
    assert (before[l:] == FILL).all()
    assert (after[:m] == FILL).all()
    assert (after[l + m :] == FILL).all()
    np.testing.assert_array_equal(after[m:l], inputs.cached_v)
    for i in range(m):
        np.testing.assert_array_equal(after[m + (l - m) + i], inputs.v_new[i])


def test_allocations_are_fresh_per_call():
    inputs = draw_inputs(GOOD, seed=2, draw=0)
    first = allocation_before(GOOD, inputs.cached_k)
    first[:] = 0
    assert (allocation_before(GOOD, inputs.cached_k)[0] == FILL).all()
    after = allocation_after(GOOD, inputs.cached_k, inputs.k_new)
    after[:] = 0
    again = allocation_after(GOOD, inputs.cached_k, inputs.k_new)
    assert (again[0] == FILL).all()
    assert not np.shares_memory(again, inputs.cached_k)
    assert not np.shares_memory(again, inputs.k_new)


def test_allocation_before_at_p_zero_holds_no_drawn_data():
    shape = (3, 3, 4, 1, 2)
    inputs = draw_inputs(shape, seed=4, draw=0)
    assert (allocation_before(shape, inputs.cached_k) == FILL).all()


@pytest.mark.parametrize("shape", SHAPES)
def test_check_value_is_crc_of_the_five_arrays(shape):
    inputs, cache_k, cache_v = good_arrays(shape)
    data = b"".join(
        a.tobytes() for a in (inputs.q, inputs.k_new, inputs.v_new, cache_k, cache_v)
    )
    value = check_value(shape, inputs.q, inputs.k_new, inputs.v_new, cache_k, cache_v)
    assert type(value) is int
    assert value == zlib.crc32(data)


@pytest.mark.parametrize("shape", SHAPES)
def test_check_value_matches_program_expectation(shape):
    q, k_new, v_new, cached_k, cached_v = expected_inputs(shape, 11, 1)
    data = b"".join(
        a.tobytes()
        for a in (
            q,
            k_new,
            v_new,
            local_allocation(shape, cached_k),
            local_allocation(shape, cached_v),
        )
    )
    (packed,) = struct.unpack("=I", struct.pack("=I", zlib.crc32(data)))
    inputs = draw_inputs(shape, seed=11, draw=1)
    value = check_value(
        shape,
        inputs.q,
        inputs.k_new,
        inputs.v_new,
        allocation_before(shape, inputs.cached_k),
        allocation_before(shape, inputs.cached_v),
    )
    assert value == packed


# GOOD has m = 2 and l = 5: allocation rows 0 and 8 are guard rows, row 2 is operand
# row 0 (drawn) and row 5 is operand row P (filled).
@pytest.mark.parametrize(
    ("position", "row"),
    [(0, 0), (0, -1), (1, 0), (1, -1), (2, 0), (2, -1)]
    + [(position, row) for position in (3, 4) for row in (0, 2, 5, 8)],
)
def test_check_value_changes_with_one_element(position, row):
    inputs, cache_k, cache_v = good_arrays()
    arrays = [inputs.q.copy(), inputs.k_new.copy(), inputs.v_new.copy()]
    arrays += [cache_k, cache_v]
    original = check_value(GOOD, *arrays)
    arrays[position][row, 0, 0] ^= 1
    assert check_value(GOOD, *arrays) != original


def test_check_value_of_non_contiguous_view():
    inputs, cache_k, cache_v = good_arrays()
    wide = np.zeros(inputs.q.shape + (2,), np.uint16)
    wide[..., 0] = inputs.q
    view = wide[..., 0]
    assert not view.flags["C_CONTIGUOUS"]
    plain = check_value(GOOD, inputs.q, inputs.k_new, inputs.v_new, cache_k, cache_v)
    assert check_value(GOOD, view, inputs.k_new, inputs.v_new, cache_k, cache_v) == (
        plain
    )


@pytest.mark.parametrize("shape", [(2, 2, 2, 2, 3), (3, 3, 4, 1, 2), (1, 1, 1, 1, 1)])
def test_reference_at_p_zero_row_zero_is_v_new(shape):
    _, _, h, h_kv, _ = shape
    inputs = draw_inputs(shape, seed=9, draw=0)
    result = reference(shape, *inputs)
    for j in range(h):
        g = j // (h // h_kv)
        wide = [value_of(p) for p in inputs.v_new[0, g, :]]
        assert result[0, j, :].tolist() == wide


@pytest.mark.parametrize("shape", SHAPES)
def test_reference_against_scalar_loop(shape):
    inputs = draw_inputs(shape, seed=13, draw=2)
    result = reference(shape, *inputs)
    assert result.dtype == np.float64
    assert result.shape == (shape[0], shape[2], shape[4])
    np.testing.assert_allclose(
        result, scalar_reference(shape, inputs), rtol=0, atol=1e-12
    )


def test_reference_head_mapping():
    shape = (2, 5, 8, 2, 3)
    inputs = draw_inputs(shape, seed=1, draw=0)
    base = reference(shape, *inputs)
    for g in range(2):
        k_new, v_new = inputs.k_new.copy(), inputs.v_new.copy()
        k_new[:, g, :] = 0x3F7F
        v_new[:, g, :] ^= 0x8000
        changed = reference(shape, inputs.q, k_new, v_new, *inputs[3:])
        differs = [not np.array_equal(base[:, j], changed[:, j]) for j in range(8)]
        assert differs == [j // 4 == g for j in range(8)]


def test_reference_causal_mask():
    shape = (3, 5, 4, 2, 3)
    inputs = draw_inputs(shape, seed=2, draw=0)
    base = reference(shape, *inputs)
    k_new, v_new = inputs.k_new.copy(), inputs.v_new.copy()
    k_new[-1] ^= 0x8000
    v_new[-1] ^= 0x8000
    changed = reference(shape, inputs.q, k_new, v_new, *inputs[3:])
    np.testing.assert_array_equal(changed[:-1], base[:-1])
    assert not np.array_equal(changed[-1], base[-1])


def test_reference_uses_cached_rows():
    shape = (1, 4, 4, 1, 2)
    inputs = draw_inputs(shape, seed=3, draw=0)
    base = reference(shape, *inputs)
    cached_v = inputs.cached_v.copy()
    cached_v ^= 0x8000
    changed = reference(shape, *inputs[:4], cached_v)
    assert not np.array_equal(changed, base)


def test_reference_propagates_nan_without_warning():
    shape = (2, 3, 2, 1, 2)
    inputs = draw_inputs(shape, seed=0, draw=0)
    q = inputs.q.copy()
    q[1, 0, 0] = NAN
    v_new = inputs.v_new.copy()
    v_new[0, 0, 1] = NAN
    result = reference(shape, q, inputs.k_new, v_new, *inputs[3:])
    assert np.isnan(result[1, 0]).all()
    assert np.isnan(result[:, :, 1]).all()
    assert np.isfinite(result[0, :, 0]).all()


def test_count_failures_passes_rounded_reference():
    inputs = draw_inputs(GOOD, seed=6, draw=0)
    expected = reference(GOOD, *inputs)
    output = to_bf16(expected)
    assert count_failures(output, expected, rtol=0, atol=2**-8) == Counts(0, 0)


def test_count_failures_counts_nan_and_one_out_of_tolerance():
    inputs = draw_inputs(GOOD, seed=6, draw=0)
    expected = reference(GOOD, *inputs)
    output = to_bf16(expected)
    output[0, 0, 0] = NAN
    output[1, 3, 2] = NAN
    assert count_failures(output, expected, rtol=0, atol=2**-8) == Counts(2, 2)
    output = to_bf16(expected)
    output[1, 2, 0] ^= 0x8000
    counts = count_failures(output, expected, rtol=0, atol=2**-8)
    assert counts == Counts(1, 0)
    assert type(counts.failed) is int


@pytest.mark.parametrize("shape", [(1, 4, 4, 1, 2), (2, 5, 4, 2, 3), (3, 3, 4, 1, 2)])
def test_count_cache_differences(shape):
    m, l, _, _, _ = shape
    inputs = draw_inputs(shape, seed=8, draw=0)
    after = allocation_after(shape, inputs.cached_k, inputs.k_new)
    assert count_cache_differences(shape, after, after.copy()) == 0
    rows = [0, l + m]
    if l > m:
        rows.append(m)
    rows.append(l)
    for row in rows:
        reported = after.copy()
        reported[row, -1, -1] ^= 1
        assert count_cache_differences(shape, reported, after) == 1
    before = allocation_before(shape, inputs.cached_k)
    expected = int(np.count_nonzero(inputs.k_new != FILL))
    assert expected == inputs.k_new.size
    assert count_cache_differences(shape, before, after) == expected


def test_count_cache_differences_compares_patterns_not_values():
    shape = (1, 1, 1, 1, 2)
    left = np.full((3, 1, 2), NAN, np.uint16)
    assert count_cache_differences(shape, left, left.copy()) == 0
    right = left.copy()
    right[0, 0, 0] = 0x7FC1
    assert count_cache_differences(shape, left, right) == 1
    zeros = np.zeros((3, 1, 2), np.uint16)
    negative = zeros.copy()
    negative[2, 0, 1] = 0x8000
    assert count_cache_differences(shape, zeros, negative) == 1


def calls(dims):
    inputs, cache_k, cache_v = good_arrays()
    return [
        lambda: draw_inputs(dims, seed=0, draw=0),
        lambda: allocation_before(dims, inputs.cached_k),
        lambda: allocation_after(dims, inputs.cached_k, inputs.k_new),
        lambda: check_value(
            dims, inputs.q, inputs.k_new, inputs.v_new, cache_k, cache_v
        ),
        lambda: reference(dims, *inputs),
        lambda: count_cache_differences(dims, cache_k, cache_v),
    ]


@pytest.mark.parametrize(("dims", "name"), BAD_DIMS)
@pytest.mark.parametrize("index", range(6))
def test_bad_dims_refused(dims, name, index):
    with raises(name):
        calls(dims)[index]()


def test_dims_messages():
    with pytest.raises(VerificationArgumentError) as info:
        draw_inputs((3, 2, 4, 2, 3), seed=0, draw=0)
    assert str(info.value) == "dims[1]: must be at least dims[0] (3), got int 2"
    with pytest.raises(VerificationArgumentError) as info:
        draw_inputs((2, 5, 3, 2, 3), seed=0, draw=0)
    assert str(info.value) == "dims[2]: must be a multiple of dims[3] (2), got int 3"


def test_dims_checked_before_arrays():
    with raises("dims"):
        check_value((1, 2), None, None, None, None, None)
    with raises("dims[1]"):
        reference((2, 1, 1, 1, 1), None, None, None, None, None)


@pytest.mark.parametrize("seed", BAD_SEEDS)
def test_bad_seed_refused(seed):
    with raises("seed"):
        draw_inputs(GOOD, seed=seed, draw=0)


@pytest.mark.parametrize("draw", BAD_DRAWS)
def test_bad_draw_refused(draw):
    with raises("draw"):
        draw_inputs(GOOD, seed=0, draw=draw)


def bad_variants(array):
    return [
        array.astype(np.int16),
        array.astype(np.float32),
        array[:-1],
        array.reshape(array.shape[0], -1),
        array.tolist(),
        None,
    ]


@pytest.mark.parametrize("position", range(5))
@pytest.mark.parametrize("variant", range(6))
def test_bad_check_value_arrays_refused(position, variant):
    inputs, cache_k, cache_v = good_arrays()
    arrays = [inputs.q, inputs.k_new, inputs.v_new, cache_k, cache_v]
    arrays[position] = bad_variants(arrays[position])[variant]
    name = ("q", "k_new", "v_new", "cache_k", "cache_v")[position]
    with raises(name):
        check_value(GOOD, *arrays)


@pytest.mark.parametrize("position", range(5))
@pytest.mark.parametrize("variant", range(6))
def test_bad_reference_arrays_refused(position, variant):
    arrays = list(draw_inputs(GOOD, seed=0, draw=0))
    arrays[position] = bad_variants(arrays[position])[variant]
    with raises(Inputs._fields[position]):
        reference(GOOD, *arrays)


def test_zero_dimension_refused_outside_cached():
    shape = (2, 2, 2, 2, 3)
    inputs = draw_inputs(shape, seed=0, draw=0)
    empty = np.zeros((0, 2, 3), np.uint16)
    with raises("q"):
        reference(shape, np.zeros((0, 2, 3), np.uint16), *inputs[1:])
    with raises("k_new"):
        reference(shape, inputs.q, empty, *inputs[2:])
    with raises("new"):
        allocation_after(shape, inputs.cached_k, empty)
    assert reference(shape, *inputs).shape == (2, 2, 3)


def test_bad_allocation_arguments_refused():
    inputs = draw_inputs(GOOD, seed=3, draw=0)
    short = inputs.cached_k[:-1]
    for function in (allocation_before, allocation_after):
        args = (inputs.k_new,) if function is allocation_after else ()
        with raises("cached"):
            function(GOOD, short, *args)
        with raises("cached"):
            function(GOOD, inputs.cached_k.astype(np.int32), *args)
        with raises("cached"):
            function(GOOD, inputs.cached_k.tolist(), *args)
    with raises("new"):
        allocation_after(GOOD, inputs.cached_k, inputs.k_new[:-1])
    with raises("new"):
        allocation_after(GOOD, inputs.cached_k, inputs.q)
    with raises("cached"):
        allocation_after(GOOD, short, None)


def test_bad_cache_difference_arguments_refused():
    _, cache_k, cache_v = good_arrays()
    with raises("reported"):
        count_cache_differences(GOOD, cache_k[:-1], cache_v)
    with raises("reported"):
        count_cache_differences(GOOD, cache_k.astype(np.float64), cache_v)
    with raises("expected"):
        count_cache_differences(GOOD, cache_k, cache_v[1:])
    with raises("expected"):
        count_cache_differences(GOOD, cache_k, cache_v.tolist())


@pytest.mark.parametrize("rtol", BAD_TOLERANCES)
def test_bad_rtol_refused(rtol):
    with raises("rtol"):
        count_failures(None, None, rtol=rtol, atol=0)


@pytest.mark.parametrize("atol", BAD_TOLERANCES)
def test_bad_atol_refused(atol):
    with raises("atol"):
        count_failures(None, None, rtol=0, atol=atol)


GOOD_OUTPUT = np.zeros((2, 4, 3), np.uint16)
GOOD_EXPECTED = np.zeros((2, 4, 3), np.float64)


@pytest.mark.parametrize(
    "output",
    [
        GOOD_OUTPUT.astype(np.float32),
        GOOD_OUTPUT.reshape(8, 3),
        np.zeros((2, 4, 0), np.uint16),
        GOOD_OUTPUT.tolist(),
        None,
        np.zeros((2, 4, 6), np.uint16),
        np.zeros((1, 4, 3), np.uint16),
    ],
)
def test_bad_output_refused(output):
    with raises("output"):
        count_failures(output, GOOD_EXPECTED, rtol=0, atol=0)


@pytest.mark.parametrize(
    "expected",
    [
        GOOD_EXPECTED.astype(np.float32),
        GOOD_EXPECTED.reshape(8, 3),
        np.zeros((0, 4, 3), np.float64),
        None,
    ],
)
def test_bad_expected_refused(expected):
    with raises("expected"):
        count_failures(GOOD_OUTPUT, expected, rtol=0, atol=0)
