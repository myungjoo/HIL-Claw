import math
import struct
import zlib

import numpy as np
import pytest

from hilclaw import (
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    rmsnorm_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.harness import bf16_verification_arrays, verification_arrays
from hilclaw.harness.bf16_verification_arrays import (
    EPS_BITS,
    KINDS,
    Counts,
    VerificationArgumentError,
    check_value,
    count_failures,
    draw_inputs,
    reference,
    widen,
)

pytestmark = pytest.mark.filterwarnings("error")

MASK = 2**64 - 1
GOLDEN = 0x9E3779B97F4A7C15
SEEDS = [0, 1, 2**63, 2**64 - 1]
DRAWS = [0, 1, 2**64 - 2]
DIMS = {
    "gemm": (3, 4, 5),
    "rmsnorm": (3, 5),
    "elementwise_add": (3, 5),
    "swiglu": (3, 5),
}
DIMS_WITH_ONE = {
    "gemm": [(1, 4, 5), (3, 1, 5), (3, 4, 1), (1, 1, 1)],
    "rmsnorm": [(1, 5), (3, 1), (1, 1)],
    "elementwise_add": [(1, 5), (3, 1), (1, 1)],
    "swiglu": [(1, 5), (3, 1), (1, 1)],
}
LARGE = {
    "gemm": (16, 32, 16),
    "rmsnorm": (16, 32),
    "elementwise_add": (64, 64),
    "swiglu": (64, 64),
}
SETS = {
    "gemm": (gemm_bf16_contract.INPUT_PATTERNS, gemm_bf16_contract.INPUT_PATTERNS),
    "rmsnorm": (
        rmsnorm_bf16_contract.INPUT_PATTERNS,
        rmsnorm_bf16_contract.INPUT_PATTERNS,
    ),
    "elementwise_add": (
        elementwise_add_bf16_contract.INPUT_PATTERNS,
        elementwise_add_bf16_contract.INPUT_PATTERNS,
    ),
    "swiglu": (swiglu_bf16_contract.GATE_PATTERNS, swiglu_bf16_contract.UP_PATTERNS),
}
NAN = 0x7FC0
INF = 0x7F80

BAD_KINDS = ["GEMM", "rope", "", None, 1, b"gemm", ("gemm",)]
BAD_DIMENSIONS = [0, -1, 1.0, "1", True, None, np.int64(3), np.array(3)]
BAD_SEEDS = [-1, 2**64, 1.5, True, None, np.uint64(7)]
BAD_DRAWS = [-1, 2**64 - 1, 0.0, True, None, np.int64(0)]
BAD_TOLERANCES = [
    -1,
    -1e-9,
    math.nan,
    math.inf,
    True,
    "0.1",
    None,
    np.float64(0.1),
    10**400,
]


def mix(x):
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK
    return x ^ (x >> 31)


def pattern_of(index, bits):
    """The pattern of index ``index`` written from ADR-0163 decision 4's prose."""
    if bits == 8:
        sign, fraction = divmod(index, 128)
        return (0x8000 if sign else 0) + 0x3F00 + fraction
    sign, position = divmod(index, 512)
    return (0x8000 if sign else 0) + 0x3F00 + position


def drawn_patterns(kind, dims, seed, draw):
    """Scalar recomputation of the two operands' patterns, flattened."""
    if kind == "gemm":
        m, k, n = dims
        sizes = (m * k, k * n)
    else:
        m, n = dims
        sizes = (m * n, n if kind == "rmsnorm" else m * n)
    bits = (10 if kind == "swiglu" else 8, 8)
    base = mix((seed + (draw + 1) * GOLDEN) & MASK)
    out = ([], [])
    element = 0
    for operand in (0, 1):
        for _ in range(sizes[operand]):
            word = mix((base + (element + 1) * GOLDEN) & MASK)
            out[operand].append(pattern_of(word >> (64 - bits[operand]), bits[operand]))
            element += 1
    return out


def u16(rows):
    return np.array(rows, dtype=np.uint16)


def f64(rows):
    return np.array(rows, dtype=np.float64)


def bf16(value):
    """The bf16 pattern of a float that bf16 holds exactly."""
    bits = struct.unpack("=I", struct.pack("=f", value))[0]
    assert bits & 0xFFFF == 0
    return bits >> 16


def value_of(pattern):
    return struct.unpack("=f", struct.pack("=I", pattern << 16))[0]


def test_public_constants():
    assert KINDS == ("gemm", "rmsnorm", "elementwise_add", "swiglu")
    assert EPS_BITS == 0x3727C5AC
    assert bf16_verification_arrays.Counts is verification_arrays.Counts
    assert VerificationArgumentError is verification_arrays.VerificationArgumentError


def test_eps_bits_is_the_contract_eps():
    eps = struct.unpack("=f", struct.pack("=I", EPS_BITS))[0]

    assert eps == rmsnorm_bf16_contract.EPS
    assert eps != 1e-05


@pytest.mark.parametrize("index", range(256))
def test_mapping_of_b8_gives_the_contract_tuples(index):
    formula = 0x3F00 | (index & 0x7F) | ((index >> 7) << 15)

    assert formula == pattern_of(index, 8)
    assert formula == gemm_bf16_contract.INPUT_PATTERNS[index]
    assert formula == rmsnorm_bf16_contract.INPUT_PATTERNS[index]
    assert formula == elementwise_add_bf16_contract.INPUT_PATTERNS[index]
    assert formula == swiglu_bf16_contract.UP_PATTERNS[index]


def test_mapping_of_b10_gives_the_gate_tuple():
    for index in range(1024):
        formula = (0x3F00 + (index & 0x1FF)) | ((index >> 9) << 15)
        assert (
            formula
            == pattern_of(index, 10)
            == swiglu_bf16_contract.GATE_PATTERNS[index]
        )


def test_mapping_end_values():
    assert [value_of(pattern_of(r, 8)) for r in (0, 127, 128, 255)] == [
        0.5,
        0.99609375,
        -0.5,
        -0.99609375,
    ]
    assert [value_of(pattern_of(r, 10)) for r in (0, 511, 512, 1023)] == [
        0.5,
        7.96875,
        -0.5,
        -7.96875,
    ]


@pytest.mark.parametrize("draw", DRAWS)
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("kind", KINDS)
def test_draw_inputs_gives_the_scalar_recomputation(kind, seed, draw):
    for dims in (DIMS[kind], *DIMS_WITH_ONE[kind]):
        first_bits, second_bits = drawn_patterns(kind, dims, seed, draw)

        first, second = draw_inputs(kind, dims, seed=seed, draw=draw)

        assert first.ravel().tolist() == first_bits
        assert second.ravel().tolist() == second_bits


@pytest.mark.parametrize("kind", KINDS)
def test_draw_inputs_shapes_and_dtypes(kind):
    expected = {
        "gemm": lambda m, k, n: ((m, k), (k, n)),
        "rmsnorm": lambda m, n: ((m, n), (n,)),
        "elementwise_add": lambda m, n: ((m, n), (m, n)),
        "swiglu": lambda m, n: ((m, n), (m, n)),
    }[kind]
    for dims in (DIMS[kind], *DIMS_WITH_ONE[kind]):
        first, second = draw_inputs(kind, dims, seed=3, draw=0)

        assert (first.shape, second.shape) == expected(*dims)
        for array in (first, second):
            assert array.dtype == np.uint16
            assert array.dtype.isnative
            assert array.flags.c_contiguous


@pytest.mark.parametrize("kind", KINDS)
def test_draw_inputs_operands_do_not_overlap(kind):
    first, second = draw_inputs(kind, DIMS[kind], seed=7, draw=0)
    kept = second.tobytes()

    first[...] = 0

    assert second.tobytes() == kept


@pytest.mark.parametrize("kind", KINDS)
def test_draw_inputs_is_a_function_of_its_arguments(kind):
    dims = LARGE[kind]
    mine = draw_inputs(kind, dims, seed=7, draw=3)
    again = draw_inputs(kind, dims, seed=7, draw=3)
    other_draw = draw_inputs(kind, dims, seed=7, draw=4)
    other_seed = draw_inputs(kind, dims, seed=8, draw=3)

    for operand in (0, 1):
        assert mine[operand].tobytes() == again[operand].tobytes()
        assert mine[operand].tobytes() != other_draw[operand].tobytes()
        assert mine[operand].tobytes() != other_seed[operand].tobytes()


@pytest.mark.parametrize("kind", KINDS)
def test_draw_inputs_stays_in_each_operands_set(kind):
    first, second = draw_inputs(kind, LARGE[kind], seed=11, draw=0)

    for array, patterns in zip((first, second), SETS[kind]):
        assert set(array.ravel().tolist()) <= set(patterns)
        assert (array >= 0x8000).any() and (array < 0x8000).any()


def test_swiglu_gate_reaches_beyond_the_256_value_set():
    gate, up = draw_inputs("swiglu", LARGE["swiglu"], seed=5, draw=0)

    assert (gate & 0x7FFF >= 0x3F80).any()
    assert not (up & 0x7FFF >= 0x3F80).any()


def test_elementwise_add_operands_are_independent():
    a, b = draw_inputs("elementwise_add", (256, 256), seed=5, draw=0)

    negated = np.count_nonzero(b == (a ^ 0x8000))
    equal = np.count_nonzero(b == a)
    assert 0 < negated < a.size
    assert 0 < equal < a.size
    assert 128 < negated < 512


@pytest.mark.parametrize("kind", ["gemm", "rmsnorm"])
def test_other_operands_are_not_equal(kind):
    first, second = draw_inputs(kind, LARGE[kind], seed=5, draw=0)

    assert first.ravel()[: second.size].tobytes() != second.ravel().tobytes()


def test_seed_plus_golden_is_the_next_draw():
    shifted = draw_inputs("swiglu", (2, 3), seed=GOLDEN, draw=0)
    following = draw_inputs("swiglu", (2, 3), seed=0, draw=1)

    for mine, theirs in zip(shifted, following):
        assert mine.tobytes() == theirs.tobytes()


@pytest.mark.parametrize("value", BAD_KINDS, ids=str)
def test_draw_inputs_refuses_a_kind(value):
    with pytest.raises(VerificationArgumentError, match="^kind: "):
        draw_inputs(value, (3, 5), seed=0, draw=0)


@pytest.mark.parametrize(
    ("kind", "dims"),
    [
        ("gemm", (3, 5)),
        ("gemm", (3, 4, 5, 6)),
        ("rmsnorm", (3, 4, 5)),
        ("swiglu", (3,)),
        ("elementwise_add", ()),
        ("elementwise_add", [3, 5]),
        ("elementwise_add", None),
        ("elementwise_add", np.array([3, 5])),
    ],
    ids=str,
)
def test_draw_inputs_refuses_dims_of_the_wrong_form(kind, dims):
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        draw_inputs(kind, dims, seed=0, draw=0)


@pytest.mark.parametrize("value", BAD_DIMENSIONS, ids=str)
@pytest.mark.parametrize("kind", KINDS)
def test_draw_inputs_refuses_a_dimension(kind, value):
    for position in range(len(DIMS[kind])):
        dims = list(DIMS[kind])
        dims[position] = value
        with pytest.raises(VerificationArgumentError, match=rf"^dims\[{position}\]: "):
            draw_inputs(kind, tuple(dims), seed=0, draw=0)


@pytest.mark.parametrize("value", BAD_SEEDS, ids=str)
def test_draw_inputs_refuses_a_seed(value):
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        draw_inputs("gemm", (1, 1, 1), seed=value, draw=0)


@pytest.mark.parametrize("value", BAD_DRAWS, ids=str)
def test_draw_inputs_refuses_a_draw(value):
    with pytest.raises(VerificationArgumentError, match="^draw: "):
        draw_inputs("rmsnorm", (1, 1), seed=0, draw=value)


def test_draw_inputs_checks_kind_before_dims_and_has_no_default():
    with pytest.raises(VerificationArgumentError, match="^kind: "):
        draw_inputs("rope", None, seed=None, draw=None)
    with pytest.raises(TypeError):
        draw_inputs("gemm", (1, 1, 1), seed=0)
    with pytest.raises(TypeError):
        draw_inputs("gemm", (1, 1, 1), 0, 0)


@pytest.mark.parametrize("kind", KINDS)
def test_check_value_is_the_crc_of_first_then_second(kind):
    first_bits, second_bits = drawn_patterns(kind, DIMS[kind], 9, 2)
    packed = struct.pack(f"={len(first_bits)}H", *first_bits) + struct.pack(
        f"={len(second_bits)}H", *second_bits
    )

    value = check_value(*draw_inputs(kind, DIMS[kind], seed=9, draw=2))

    assert type(value) is int
    assert value == zlib.crc32(packed)


def test_check_value_of_a_hand_written_pair_changes_with_one_element():
    first = u16([[0x3F00, 0xBF80]])
    second = u16([0x3F7F, 0x3F01])
    value = check_value(first, second)

    assert value == zlib.crc32(struct.pack("=4H", 0x3F00, 0xBF80, 0x3F7F, 0x3F01))
    second[1] = 0x3F02
    assert check_value(first, second) != value
    assert check_value(second, first) != check_value(first, second)


def test_check_value_reads_a_non_contiguous_array_in_row_major_order():
    first = u16([[1, 2], [3, 4]]).T
    second = u16([5])

    assert check_value(first, second) == zlib.crc32(struct.pack("=5H", 1, 3, 2, 4, 5))


BAD_ARRAYS = [
    np.zeros((2, 2), dtype=np.float32),
    np.zeros((2, 2), dtype=np.int16),
    np.zeros((2, 2), dtype=">u2"),
    np.zeros((2, 0), dtype=np.uint16),
    np.zeros((0,), dtype=np.uint16),
    np.zeros((2, 2, 2), dtype=np.uint16),
    np.uint16(5),
    np.array(5, dtype=np.uint16),
    [[0x3F00]],
    None,
]


@pytest.mark.parametrize("value", BAD_ARRAYS, ids=repr)
def test_check_value_refuses_an_array(value):
    good = u16([0x3F00])
    with pytest.raises(VerificationArgumentError, match="^first: "):
        check_value(value, good)
    with pytest.raises(VerificationArgumentError, match="^second: "):
        check_value(good, value)


def test_widen_is_exact_for_every_pattern_of_the_sets():
    patterns = sorted(
        set(swiglu_bf16_contract.GATE_PATTERNS) | set(gemm_bf16_contract.INPUT_PATTERNS)
    )
    for pattern in patterns:
        assert widen(u16([pattern]))[0] == value_of(pattern)


def test_widen_of_hand_picked_patterns():
    result = widen(u16([[0x0000, 0x8000, 0x3F80, 0xC040], [0x0001, 0x7F7F, NAN, INF]]))

    assert result.dtype == np.float64 and result.shape == (2, 4)
    assert result[0].tolist() == [0.0, -0.0, 1.0, -3.0]
    assert math.copysign(1, result[0, 1]) == -1
    assert result[1, 0] == 2.0**-133
    assert result[1, 1] == value_of(0x7F7F)
    assert math.isnan(result[1, 2])
    assert result[1, 3] == math.inf
    assert widen(u16([0xFF80]))[0] == -math.inf


@pytest.mark.parametrize("value", BAD_ARRAYS, ids=repr)
def test_widen_refuses_an_array(value):
    with pytest.raises(VerificationArgumentError, match="^patterns: "):
        widen(value)


def test_reference_of_gemm():
    a = u16([[bf16(0.5), bf16(-0.75)], [bf16(1.0), bf16(2.0)]])
    b = u16([[bf16(0.5), bf16(1.5), bf16(-1.0)], [bf16(0.25), bf16(0.5), bf16(0.75)]])

    result = reference("gemm", a, b)

    assert result.dtype == np.float64
    assert result.tolist() == [[0.0625, 0.375, -1.0625], [1.0, 2.5, 0.5]]


def test_reference_of_elementwise_add_is_exact():
    a, b = draw_inputs("elementwise_add", (32, 32), seed=1, draw=0)

    result = reference("elementwise_add", a, b)

    exact = [
        value_of(x) + value_of(y)
        for x, y in zip(a.ravel().tolist(), b.ravel().tolist())
    ]
    assert result.ravel().tolist() == exact
    assert (result == 0).any()


def test_reference_of_rmsnorm_uses_the_widened_binary32_eps():
    x = u16([[bf16(0.5), bf16(-0.5)], [bf16(1.0), bf16(0.75)]])
    w = u16([bf16(2.0), bf16(-0.5)])
    eps = struct.unpack("=f", struct.pack("=I", EPS_BITS))[0]

    result = reference("rmsnorm", x, w)

    rows = [[0.5, -0.5], [1.0, 0.75]]
    weights = [2.0, -0.5]
    for i, row in enumerate(rows):
        scale = math.sqrt(sum(v * v for v in row) / 2 + eps)
        for j, v in enumerate(row):
            assert result[i, j] == pytest.approx(v * weights[j] / scale, rel=1e-15)
    decimal = math.sqrt(0.25 + 1e-05)
    assert result[0, 0] != 0.5 * 2.0 / decimal
    assert result[0, 0] == 0.5 * 2.0 / math.sqrt(0.25 + eps)


def test_reference_of_swiglu_uses_float64_exp():
    gate = u16([[bf16(-7.5), bf16(0.5), bf16(7.96875)]])
    up = u16([[bf16(0.75), bf16(-0.5), bf16(0.99609375)]])

    result = reference("swiglu", gate, up)

    for j, (g, u) in enumerate(((-7.5, 0.75), (0.5, -0.5), (7.96875, 0.99609375))):
        assert result[0, j] == g / (1 + math.exp(-g)) * u
    g32, u32 = widen(gate).astype(np.float32), widen(up).astype(np.float32)
    assert (g32 / (1 + np.exp(-g32)) * u32).astype(
        np.float64
    ).tolist() != result.tolist()


def test_reference_carries_a_nan_input_without_a_warning():
    for kind, first, second in (
        ("gemm", u16([[NAN]]), u16([[INF]])),
        ("rmsnorm", u16([[INF, 0x3F00]]), u16([0x3F00, 0x3F00])),
        ("elementwise_add", u16([[INF]]), u16([[0xFF80]])),
        ("swiglu", u16([[0xFF80]]), u16([[0x3F00]])),
    ):
        assert not np.isfinite(reference(kind, first, second)).all()


@pytest.mark.parametrize("value", BAD_KINDS, ids=str)
def test_reference_refuses_a_kind(value):
    with pytest.raises(VerificationArgumentError, match="^kind: "):
        reference(value, u16([[1]]), u16([[1]]))


@pytest.mark.parametrize(
    ("kind", "first", "second", "name"),
    [
        (
            "gemm",
            np.zeros((2, 3), dtype=np.uint16),
            np.zeros((2, 3), dtype=np.uint16),
            "second",
        ),
        (
            "gemm",
            np.zeros((3,), dtype=np.uint16),
            np.zeros((3, 2), dtype=np.uint16),
            "first",
        ),
        (
            "gemm",
            np.zeros((2, 3), dtype=np.uint16),
            np.zeros((3,), dtype=np.uint16),
            "second",
        ),
        (
            "rmsnorm",
            np.zeros((2, 3), dtype=np.uint16),
            np.zeros((2,), dtype=np.uint16),
            "second",
        ),
        (
            "rmsnorm",
            np.zeros((2, 3), dtype=np.uint16),
            np.zeros((1, 3), dtype=np.uint16),
            "second",
        ),
        (
            "elementwise_add",
            np.zeros((2, 3), dtype=np.uint16),
            np.zeros((3, 2), dtype=np.uint16),
            "second",
        ),
        (
            "swiglu",
            np.zeros((2, 3), dtype=np.uint16),
            np.zeros((2, 4), dtype=np.uint16),
            "second",
        ),
        (
            "swiglu",
            np.zeros((2, 3), dtype=np.uint16),
            np.zeros((3,), dtype=np.uint16),
            "second",
        ),
    ],
)
def test_reference_refuses_a_shape(kind, first, second, name):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        reference(kind, first, second)


@pytest.mark.parametrize("value", BAD_ARRAYS, ids=repr)
@pytest.mark.parametrize("kind", ["gemm", "swiglu"])
def test_reference_refuses_an_array(kind, value):
    good = u16([[0x3F00]])
    with pytest.raises(VerificationArgumentError, match="^first: "):
        reference(kind, value, good)
    with pytest.raises(VerificationArgumentError, match="^second: "):
        reference(kind, good, value)


def test_count_failures_passes_and_fails():
    output = u16([[bf16(1.0), bf16(0.5)], [bf16(-2.0), bf16(0.75)]])
    expected = f64([[1.0, 0.5], [-2.0, 0.75]])

    assert count_failures(output, expected, rtol=0, atol=0) == Counts(0, 0)
    off = f64([[1.0, 0.5], [-2.0, 0.76]])
    result = count_failures(output, off, rtol=0, atol=0.001)
    assert result == Counts(1, 0) and type(result) is Counts
    assert count_failures(output, off, rtol=0, atol=0.02) == Counts(0, 0)


def test_count_failures_atol_zero_against_rtol_only():
    output = u16([[bf16(1.0), bf16(-0.5)]])
    expected = f64([[1.001, -0.5005]])

    assert count_failures(output, expected, rtol=0, atol=0) == Counts(2, 0)
    assert count_failures(output, expected, rtol=0.002, atol=0) == Counts(0, 0)
    assert count_failures(output, f64([[0.0, -0.5]]), rtol=0.5, atol=0) == Counts(1, 0)


def test_count_failures_counts_the_nan_fill_and_infinities():
    output = u16([[NAN, INF, 0xFF80, bf16(1.0)]])
    expected = f64([[1.0, 1.0, 1.0, 1.0]])

    assert count_failures(output, expected, rtol=1e300, atol=1e300) == Counts(3, 3)


def test_count_failures_with_an_infinite_expected():
    output = u16([[INF, bf16(1.0)]])

    assert count_failures(
        output, f64([[math.inf, math.inf]]), rtol=0, atol=1
    ) == Counts(2, 1)


def test_count_failures_refuses_a_shape():
    with pytest.raises(VerificationArgumentError, match="^output: "):
        count_failures(u16([[1, 2]]), f64([[1.0], [2.0]]), rtol=0, atol=0)


@pytest.mark.parametrize("value", BAD_ARRAYS, ids=repr)
def test_count_failures_refuses_an_output(value):
    with pytest.raises(VerificationArgumentError, match="^output: "):
        count_failures(value, f64([[1.0]]), rtol=0, atol=0)


@pytest.mark.parametrize(
    "value",
    [
        u16([[1]]),
        np.zeros((1, 1), dtype=np.float32),
        np.zeros(1),
        np.zeros((1, 0)),
        None,
    ],
    ids=repr,
)
def test_count_failures_refuses_an_expected(value):
    with pytest.raises(VerificationArgumentError, match="^expected: "):
        count_failures(u16([[1]]), value, rtol=0, atol=0)


@pytest.mark.parametrize("name", ["rtol", "atol"])
@pytest.mark.parametrize("value", BAD_TOLERANCES, ids=str)
def test_count_failures_refuses_a_tolerance_before_the_arrays(name, value):
    tolerance = {"rtol": 0, "atol": 0, name: value}

    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        count_failures(None, None, **tolerance)


def test_count_failures_has_no_default():
    with pytest.raises(TypeError):
        count_failures(u16([[1]]), f64([[1.0]]), rtol=0)
    with pytest.raises(TypeError):
        count_failures(u16([[1]]), f64([[1.0]]), 0, 0)


def test_an_argument_error_names_the_argument_and_shows_no_element():
    with pytest.raises(VerificationArgumentError) as caught:
        widen(np.zeros((2, 3), dtype=np.float32))

    assert str(caught.value) == (
        "patterns: must be a uint16 array of one or two dimensions, none of them 0, "
        "got a float32 array of shape (2, 3)"
    )
    with pytest.raises(VerificationArgumentError) as caught:
        reference("rmsnorm", u16([[1, 2]]), u16([[1, 2]]))
    assert str(caught.value) == (
        "second: must be a uint16 array of one dimension, none of them 0, "
        "got a uint16 array of shape (1, 2)"
    )
    with pytest.raises(VerificationArgumentError) as caught:
        draw_inputs("gemm", (1, 2), seed=0, draw=0)
    assert str(caught.value) == "dims: must be a tuple of 3 ints for gemm, got tuple"
