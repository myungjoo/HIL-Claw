import math
import struct
import zlib

import numpy as np
import pytest

from hilclaw.harness import verification_arrays
from hilclaw.harness.verification_arrays import (
    Counts,
    VerificationArgumentError,
    check_tolerance,
    check_value,
    count_failures,
    draw_inputs,
    reference,
)

pytestmark = pytest.mark.filterwarnings("error")

MASK = 2**64 - 1
GOLDEN = 0x9E3779B97F4A7C15
SEEDS = [0, 1, 2**63, 2**64 - 1]
DRAWS = [0, 1, 2, 2**64 - 2]
SHAPE = (3, 4, 5)
SHAPES_WITH_ONE = [(1, 4, 5), (3, 1, 5), (3, 4, 1), (1, 1, 1)]
LARGE = (8, 16, 8)

BAD_DIMENSIONS = [0, -1, 1.0, "1", True, None, np.int64(3), np.array(3)]
BAD_SEEDS = [-1, 2**64, 1.5, True, None, np.uint64(7)]
BAD_DRAWS = [-1, 2**64 - 1, 0.0, True, None, np.int64(0)]
BAD_TOLERANCES = [
    -1,
    -1e-9,
    math.nan,
    math.inf,
    -math.inf,
    True,
    "0.1",
    None,
    np.float64(0.1),
    np.array(0.1),
    10**400,
    10**5000,
]


def mix(x):
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK
    return x ^ (x >> 31)


def drawn_bits(m, k, n, seed, draw):
    """Bit patterns of ``a`` and of ``b``, written from the header of the C program."""
    base = mix((seed + (draw + 1) * GOLDEN) & MASK)
    bits = []
    for element in range(m * k + k * n):
        word = mix((base + (element + 1) * GOLDEN) & MASK)
        bits.append((word & 1) << 31 | 126 << 23 | word >> 41)
    return bits[: m * k], bits[m * k :]


def pack(bits):
    return struct.pack(f"={len(bits)}I", *bits)


def as_floats(bits):
    return struct.unpack(f"={len(bits)}f", pack(bits))


def f32(rows):
    return np.array(rows, dtype=np.float32)


def f64(rows):
    return np.array(rows, dtype=np.float64)


def following(value):
    return np.nextafter(np.float32(value), np.float32(math.copysign(math.inf, value)))


@pytest.mark.parametrize("draw", DRAWS)
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("shape", [SHAPE, *SHAPES_WITH_ONE])
def test_draw_inputs_gives_the_bit_patterns_of_the_c_program(shape, seed, draw):
    m, k, n = shape
    a_bits, b_bits = drawn_bits(m, k, n, seed, draw)

    a, b = draw_inputs(m, k, n, seed=seed, draw=draw)

    assert (a.shape, b.shape) == ((m, k), (k, n))
    assert a.dtype == np.float32 and b.dtype == np.float32
    assert a.flags.c_contiguous and b.flags.c_contiguous
    assert a.tobytes() == pack(a_bits)
    assert b.tobytes() == pack(b_bits)
    for array in (a, b):
        assert np.isfinite(array).all()
        assert ((np.abs(array) >= 0.5) & (np.abs(array) < 1)).all()


def test_draw_inputs_gives_both_signs():
    a, b = draw_inputs(*LARGE, seed=7, draw=0)

    for array in (a, b):
        assert (array < 0).any() and (array > 0).any()


def test_draw_inputs_is_a_function_of_its_arguments():
    first = draw_inputs(*LARGE, seed=7, draw=3)
    again = draw_inputs(*LARGE, seed=7, draw=3)
    other_seed = draw_inputs(*LARGE, seed=8, draw=3)
    other_draw = draw_inputs(*LARGE, seed=7, draw=4)

    for mine, same, seed, draw in zip(first, again, other_seed, other_draw):
        assert mine.tobytes() == same.tobytes()
        assert mine.tobytes() != seed.tobytes()
        assert mine.tobytes() != draw.tobytes()


def test_draw_inputs_gives_arrays_that_do_not_overlap():
    a, b = draw_inputs(*SHAPE, seed=7, draw=0)
    kept = b.tobytes()

    a[...] = 0

    assert b.tobytes() == kept


@pytest.mark.parametrize("draw", [0, 1, 2**64 - 3])
@pytest.mark.parametrize("seed", SEEDS)
def test_seed_plus_golden_is_the_next_draw(seed, draw):
    shifted = draw_inputs(*SHAPE, seed=(seed + GOLDEN) & MASK, draw=draw)
    following_draw = draw_inputs(*SHAPE, seed=seed, draw=draw + 1)

    for mine, theirs in zip(shifted, following_draw):
        assert mine.tobytes() == theirs.tobytes()


@pytest.mark.parametrize("name", ["m", "k", "n"])
@pytest.mark.parametrize("value", BAD_DIMENSIONS, ids=str)
def test_draw_inputs_refuses_a_dimension(name, value):
    dimensions = {"m": 3, "k": 4, "n": 5, name: value}

    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        draw_inputs(*dimensions.values(), seed=0, draw=0)


@pytest.mark.parametrize("value", BAD_SEEDS, ids=str)
def test_draw_inputs_refuses_a_seed(value):
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        draw_inputs(*SHAPE, seed=value, draw=0)


@pytest.mark.parametrize("value", BAD_DRAWS, ids=str)
def test_draw_inputs_refuses_a_draw(value):
    with pytest.raises(VerificationArgumentError, match="^draw: "):
        draw_inputs(*SHAPE, seed=0, draw=value)


def test_draw_inputs_has_no_default():
    with pytest.raises(TypeError):
        draw_inputs(*SHAPE, seed=0)
    with pytest.raises(TypeError):
        draw_inputs(*SHAPE, draw=0)
    with pytest.raises(TypeError):
        draw_inputs(*SHAPE, 0, 0)


def test_an_argument_error_is_a_value_error_that_shows_no_array_element():
    array = f32([[0.625, 0.75]])

    with pytest.raises(VerificationArgumentError) as caught:
        draw_inputs(array, 4, 5, seed=0, draw=0)

    assert isinstance(caught.value, ValueError)
    assert str(caught.value) == (
        "m: must be an int of at least 1, got a float32 array of shape (1, 2)"
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_check_value_is_the_crc_of_the_bytes_of_a_then_b(seed):
    m, k, n = SHAPE
    a_bits, b_bits = drawn_bits(m, k, n, seed, 1)

    value = check_value(*draw_inputs(m, k, n, seed=seed, draw=1))

    assert type(value) is int
    assert value == zlib.crc32(pack(a_bits) + pack(b_bits))


def test_check_value_of_a_hand_written_pair():
    a = f32([[1.0, -2.0], [0.5, 3.0]])
    b = f32([[4.0, -0.0], [0.25, 8.0]])
    packed = struct.pack("=8f", 1.0, -2.0, 0.5, 3.0, 4.0, -0.0, 0.25, 8.0)

    assert check_value(a, b) == zlib.crc32(packed)
    assert check_value(b, a) != zlib.crc32(packed)


def test_check_value_reads_an_array_that_is_not_contiguous_in_row_major_order():
    a = f32([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    b = f32([[7.0, 8.0], [9.0, 10.0]])
    transposed = np.asfortranarray(a)
    assert not transposed.flags.c_contiguous

    assert check_value(transposed, b) == check_value(a, b)
    assert check_value(a, f32([[7.0, 0.0, 8.0], [9.0, 0.0, 10.0]])[:, ::2]) == (
        check_value(a, b)
    )


@pytest.mark.parametrize("shape", [SHAPE, *SHAPES_WITH_ONE])
def test_reference_is_the_float64_product_of_the_drawn_inputs(shape):
    m, k, n = shape
    a_bits, b_bits = drawn_bits(m, k, n, 11, 2)
    a_values, b_values = as_floats(a_bits), as_floats(b_bits)

    result = reference(*draw_inputs(m, k, n, seed=11, draw=2))

    assert result.dtype == np.float64
    assert result.shape == (m, n)
    for i in range(m):
        for j in range(n):
            terms = [a_values[i * k + p] * b_values[p * n + j] for p in range(k)]
            assert result[i, j] == pytest.approx(math.fsum(terms), rel=0, abs=1e-13)


def test_reference_of_a_hand_written_pair_is_exact():
    a = f32([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    b = f32([[1.0, -1.0], [0.5, 2.0], [-2.0, 0.25]])

    result = reference(a, b)

    assert result.tolist() == [[-4.0, 3.75], [-5.5, 7.5]]


def test_reference_is_computed_after_widening():
    value = 1 + 2**-23
    a = f32([[value]])
    exact = 1 + 2**-22 + 2**-46

    result = reference(a, a)

    assert float(a[0, 0]) == value
    assert result[0, 0] == exact
    assert float(np.float32(exact)) != exact


@pytest.mark.parametrize("function", [check_value, reference])
@pytest.mark.parametrize(
    ("a", "b", "name"),
    [
        (f64([[1.0, 2.0]]), f32([[1.0], [2.0]]), "a"),
        (f32([[1.0, 2.0]]), f64([[1.0], [2.0]]), "b"),
        (f32([1.0, 2.0]), f32([[1.0], [2.0]]), "a"),
        (f32([[1.0, 2.0]]), f32([1.0, 2.0]), "b"),
        (f32([[[1.0, 2.0]]]), f32([[1.0], [2.0]]), "a"),
        (f32([[1.0, 2.0]]), f32([[1.0, 2.0]]), "b"),
        (f32([[1.0, 2.0]]), f32([[1.0], [2.0], [3.0]]), "b"),
        (np.zeros((0, 2), dtype=np.float32), f32([[1.0], [2.0]]), "a"),
        (f32([[1.0, 2.0]]), np.zeros((2, 0), dtype=np.float32), "b"),
        (
            f32([[1.0, 2.0]]).astype(np.dtype(np.float32).newbyteorder()),
            f32([[1.0]]),
            "a",
        ),
        ([[1.0, 2.0]], f32([[1.0], [2.0]]), "a"),
        (f32([[1.0, 2.0]]), None, "b"),
        (np.float32(1.0), f32([[1.0]]), "a"),
    ],
)
def test_check_value_and_reference_refuse_an_operand(function, a, b, name):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        function(a, b)


@pytest.mark.parametrize(("rtol", "atol"), [(0, 0), (0, 1), (1, 0), (0.0, 1e300)])
def test_check_tolerance_accepts_a_valid_tolerance(rtol, atol):
    assert check_tolerance(rtol, atol) is None


@pytest.mark.parametrize("value", BAD_TOLERANCES, ids=range(len(BAD_TOLERANCES)))
def test_a_tolerance_is_refused(value):
    output, expected = f32([[1.0]]), f64([[1.0]])

    with pytest.raises(VerificationArgumentError, match="^rtol: "):
        check_tolerance(value, 0.5)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        check_tolerance(0.5, value)
    with pytest.raises(VerificationArgumentError, match="^rtol: "):
        count_failures(output, expected, rtol=value, atol=0.5)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        count_failures(output, expected, rtol=0.5, atol=value)


def test_a_tolerance_has_no_default():
    output, expected = f32([[1.0]]), f64([[1.0]])

    with pytest.raises(TypeError):
        check_tolerance(0.5)
    with pytest.raises(TypeError):
        count_failures(output, expected, rtol=0.5)
    with pytest.raises(TypeError):
        count_failures(output, expected, atol=0.5)
    with pytest.raises(TypeError):
        count_failures(output, expected, 0.5, 0.5)


def test_the_rounded_reference_passes_under_a_tolerance_with_atol():
    expected = reference(*draw_inputs(*LARGE, seed=5, draw=0))

    counts = count_failures(expected.astype(np.float32), expected, rtol=1e-6, atol=1e-6)

    assert counts == Counts(failed=0, non_finite=0)
    assert type(counts.failed) is int and type(counts.non_finite) is int


@pytest.mark.parametrize(
    ("reference_value", "rtol", "atol", "bound"),
    [
        (2.0, 0.25, 0, 2.5),
        (2.0, 0.25, 0, 1.5),
        (-2.0, 0.25, 0, -2.5),
        (-2.0, 0.25, 0, -1.5),
        (1.0, 0, 0.25, 1.25),
        (1.0, 0, 0.25, 0.75),
        (0.0, 0.5, 0.25, 0.25),
        (0.0, 0.5, 0.25, -0.25),
        (2.0, 0.25, 0.25, 2.75),
        (2.0, 0.25, 0.25, 1.25),
        (-2.0, 0.25, 0.25, -2.75),
    ],
)
def test_the_bound_passes_and_the_next_float32_beyond_it_fails(
    reference_value, rtol, atol, bound
):
    expected = f64([[reference_value]])
    step = bound - reference_value
    beyond = np.nextafter(np.float32(bound), np.float32(bound + step))

    on = count_failures(f32([[bound]]), expected, rtol=rtol, atol=atol)
    off = count_failures(f32([[beyond]]), expected, rtol=rtol, atol=atol)

    assert on == Counts(0, 0)
    assert off == Counts(1, 0)


@pytest.mark.parametrize("wrong", [0, 1, 3, 6])
def test_failed_counts_the_elements_outside_the_tolerance(wrong):
    expected = f64([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    output = expected.astype(np.float32)
    output.reshape(-1)[:wrong] += 1.0

    assert count_failures(output, expected, rtol=0, atol=0.5) == Counts(wrong, 0)


@pytest.mark.parametrize(("rtol", "atol"), [(0, 0), (0.0, 0.0), (0, 1), (1, 0)])
def test_an_exact_output_passes_under_any_tolerance(rtol, atol):
    expected = f64([[1.5, -0.25, 0.0], [0.0, 1024.0, -3.0]])
    output = f32([[1.5, -0.25, -0.0], [0.0, 1024.0, -3.0]])

    assert count_failures(output, expected, rtol=rtol, atol=atol) == Counts(0, 0)


def test_integer_tolerances_count_as_their_values():
    expected = f64([[2.0, 2.0, 2.0]])
    output = f32([[4.0, following(4.0), 0.0]])

    assert count_failures(output, expected, rtol=1, atol=0) == Counts(1, 0)
    assert count_failures(output, expected, rtol=0, atol=1) == Counts(3, 0)


@pytest.mark.parametrize(("rtol", "atol"), [(0, 0), (1e-6, 1e-6), (1e300, 1e300)])
def test_every_non_finite_element_fails_under_every_tolerance(rtol, atol):
    expected = f64([[0.0, 1e30, -1e30], [0.0, 0.0, 0.0]])
    output = f32([[math.nan, math.inf, -math.inf], [0.0, 0.0, 0.0]])

    counts = count_failures(output, expected, rtol=rtol, atol=atol)

    assert counts == Counts(failed=3, non_finite=3)


def test_a_finite_element_outside_the_tolerance_is_counted_in_failed_only():
    expected = f64([[0.0, 0.0], [0.0, 0.0]])
    output = f32([[math.nan, 5.0], [0.0, -math.inf]])

    assert count_failures(output, expected, rtol=0.5, atol=1.0) == Counts(3, 2)


def test_a_reference_that_is_not_finite_gets_no_special_case():
    output = f32([[1.0, 1.0, 1.0, math.inf]])
    expected = f64([[math.nan, math.inf, -math.inf, math.inf]])

    assert count_failures(output, expected, rtol=0, atol=1.0) == Counts(4, 1)
    assert count_failures(output, expected, rtol=1, atol=0) == Counts(2, 1)


@pytest.mark.parametrize("shape", SHAPES_WITH_ONE)
def test_count_failures_at_a_dimension_of_one(shape):
    expected = reference(*draw_inputs(*shape, seed=3, draw=1))
    output = expected.astype(np.float32)

    assert count_failures(output, expected, rtol=1e-6, atol=1e-6) == Counts(0, 0)
    output[0, 0] = math.nan
    assert count_failures(output, expected, rtol=1e-6, atol=1e-6) == Counts(1, 1)


@pytest.mark.parametrize(
    ("output", "expected", "name"),
    [
        (f64([[1.0, 2.0]]), f64([[1.0, 2.0]]), "output"),
        (f32([[1.0, 2.0]]), f32([[1.0, 2.0]]), "expected"),
        (f32([1.0, 2.0]), f64([[1.0, 2.0]]), "output"),
        (f32([[1.0, 2.0]]), f64([1.0, 2.0]), "expected"),
        (f32([[1.0, 2.0]]), f64([[1.0], [2.0]]), "output"),
        (f32([[1.0, 2.0]]), f64([[1.0, 2.0, 3.0]]), "output"),
        (np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2)), "output"),
        ([[1.0, 2.0]], f64([[1.0, 2.0]]), "output"),
        (f32([[1.0, 2.0]]), None, "expected"),
    ],
)
def test_count_failures_refuses_an_array(output, expected, name):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        count_failures(output, expected, rtol=0.5, atol=0.5)


def test_the_constants_are_those_of_the_c_header():
    assert verification_arrays.GOLDEN == GOLDEN
    assert verification_arrays.SEED_LIMIT == MASK + 1
