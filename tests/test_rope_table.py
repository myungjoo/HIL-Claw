import ast
import decimal
import math
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import numpy
import pytest

from hilclaw import rope_table
from hilclaw.keys import MAX_INTEGER
from hilclaw.rope_table import build, frequencies

META = {
    "head_dim": 64,
    "theta": 500000,
    "scale_factor": 8,
    "low_freq_factor": 1,
    "high_freq_factor": 4,
    "old_context_len": 8192,
}
CONSTANTS = (
    "theta",
    "scale_factor",
    "low_freq_factor",
    "high_freq_factor",
    "old_context_len",
)
SIGNATURE = ("head_dim",) + CONSTANTS

# Computed at planning time with decimal at 60 and 90 digits and a float64 cross-check.
FIXED = {
    (1, 0): 0x3F0A5140,
    (1, 1): 0x3F576AA4,
    (127, 0): 0x3E6DEF8B,
    (127, 1): 0x3F78FE49,
    (2047, 0): 0x3E7FB55B,
    (2047, 1): 0xBF77E3C6,
    (2047, 30): 0xBF71E8D8,
    (2047, 31): 0x3EA78538,
    (2047, 36): 0x3F7CC1AE,
    (2047, 37): 0x3E227C93,
    (2047, 62): 0x3F7FFFFB,
    (2047, 63): 0x3A4A2867,
}

SMALL = [
    {
        "head_dim": 8,
        "theta": 10000,
        "scale_factor": 2.5,
        "low_freq_factor": 1,
        "high_freq_factor": 8,
        "old_context_len": 1000,
        "positions": 40,
    },
    {
        "head_dim": 2,
        "theta": 10000.0,
        "scale_factor": 3,
        "low_freq_factor": 1.5,
        "high_freq_factor": 5.0,
        "old_context_len": 20.0,
        "positions": 50,
    },
    {
        "head_dim": 2,
        "theta": 10000,
        "scale_factor": 0.75,
        "low_freq_factor": 1,
        "high_freq_factor": 2,
        "old_context_len": 1,
        "positions": 30,
    },
]

REFERENCE = decimal.Context(prec=70)


def reference_pi():
    with decimal.localcontext(REFERENCE) as context:
        context.prec += 2
        three = Decimal(3)
        lasts, t, s, n, na, d, da = 0, three, 3, 1, 0, 0, 24
        while s != lasts:
            lasts = s
            n, na = n + na, na + 8
            d, da = d + da, da + 32
            t = (t * n) / d
            s += t
        context.prec -= 2
        return +s


PI = reference_pi()


def reference_band(i, head_dim, theta, scale_factor, low, high, length):
    with decimal.localcontext(REFERENCE):
        f = Decimal(theta) ** (Decimal(-2 * i) / Decimal(head_dim))
        wavelength = 2 * PI / f
        length, low, high = Decimal(length), Decimal(low), Decimal(high)
        if wavelength > length / low:
            return "scaled", f / Decimal(scale_factor)
        if wavelength >= length / high:
            sigma = (length / wavelength - low) / (high - low)
            return "smooth", (1 - sigma) * f / Decimal(scale_factor) + sigma * f
        return "kept", f


def reference_g(i, constants):
    return reference_band(
        i, constants["head_dim"], *(constants[name] for name in CONSTANTS)
    )[1]


def reference_cos_sin(x):
    with decimal.localcontext(REFERENCE) as context:
        x = x - 2 * PI * (x / (2 * PI)).to_integral_value(decimal.ROUND_FLOOR)
        context.prec += 4
        results = []
        for start in (0, 1):
            term = Decimal(1) if start == 0 else x
            total, n, lasts = term, start, None
            while total != lasts:
                lasts = total
                n += 2
                term = -term * x * x / (n * (n - 1))
                total += term
            results.append(total)
        context.prec -= 4
        return +results[0], +results[1]


def reference_binary32(value):
    exact = Fraction(value)
    guess = numpy.float32(float(value))
    candidates = [
        numpy.nextafter(guess, numpy.float32(-2)),
        guess,
        numpy.nextafter(guess, numpy.float32(2)),
    ]

    def key(candidate):
        bits = int(candidate.view(numpy.uint32))
        return abs(Fraction(float(candidate)) - exact), bits & 1

    return int(min(candidates, key=key).view(numpy.uint32))


def reference_row(t, constants):
    bits = []
    for i in range(constants["head_dim"] // 2):
        if t == 0:
            bits += [0x3F800000, 0]
            continue
        with decimal.localcontext(REFERENCE):
            angle = t * reference_g(i, constants)
        bits += [reference_binary32(value) for value in reference_cos_sin(angle)]
    return bits


def row_bits(table, t):
    return [int(value) for value in table[t].view(numpy.uint32)]


def imported_modules(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            found.add(node.module)
            found |= {f"{node.module}.{alias.name}" for alias in node.names}
    return found


@pytest.fixture(scope="module")
def meta_table():
    return build(positions=2048, **META)


@pytest.fixture(scope="module")
def unscaled_table():
    return build(positions=2048, **{**META, "scale_factor": 1})


def test_the_fixed_values(meta_table):
    for (t, column), expected in FIXED.items():
        assert int(meta_table[t, column : column + 1].view(numpy.uint32)[0]) == expected


@pytest.mark.parametrize("t", [0, 1, 2, 127, 128, 1000, 2046, 2047])
def test_meta_rows_equal_the_reference(meta_table, t):
    assert row_bits(meta_table, t) == reference_row(t, META)


def test_scale_factor_32_rows_equal_the_reference():
    constants = {**META, "scale_factor": 32}
    table = build(positions=2048, **constants)
    for t in (1, 127, 2047):
        assert row_bits(table, t) == reference_row(t, constants)


@pytest.mark.parametrize("small", SMALL)
def test_small_tables_equal_the_reference_on_every_entry(small):
    constants = {key: value for key, value in small.items() if key != "positions"}
    table = build(**small)
    for t in range(small["positions"]):
        assert row_bits(table, t) == reference_row(t, constants)


def test_the_small_tables_cover_the_three_bands():
    bands = set()
    for small in SMALL:
        for i in range(small["head_dim"] // 2):
            bands.add(
                reference_band(
                    i, small["head_dim"], *(small[name] for name in CONSTANTS)
                )[0]
            )
    assert bands == {"scaled", "smooth", "kept"}


def test_row_zero_is_exactly_one_and_positive_zero(meta_table):
    assert all(meta_table[0, 0::2] == 1.0)
    assert set(meta_table[0, 1::2].view(numpy.uint32)) == {0}


def test_frequencies_match_the_reference():
    g = frequencies(**META)
    for i, value in enumerate(g):
        assert value == float(reference_g(i, META))


def test_the_bands_of_meta_constants():
    g = frequencies(**META)
    unscaled = frequencies(**{**META, "scale_factor": 1})
    assert len(g) == 32
    assert type(g) is tuple
    assert all(type(value) is float for value in g)
    assert g[0] == 1.0
    assert g[:15] == unscaled[:15]
    for i in range(18, 32):
        assert math.isclose(g[i], unscaled[i] / 8, rel_tol=0, abs_tol=math.ulp(g[i]))
    for i in range(15, 18):
        assert unscaled[i] / 8 < g[i] < unscaled[i]
    assert f"{g[31]:.4g}" == "3.767e-07"
    for i in range(32):
        assert reference_band(i, 64, *(META[name] for name in CONSTANTS))[0] == (
            "kept" if i < 15 else "smooth" if i < 18 else "scaled"
        )


def test_frequencies_are_what_build_uses(meta_table):
    g = frequencies(**META)
    rows = numpy.arange(2048, dtype=numpy.float64)[:, None] * numpy.array(g)
    assert numpy.max(numpy.abs(meta_table[:, 0::2] - numpy.cos(rows))) < 1e-6
    assert numpy.max(numpy.abs(meta_table[:, 1::2] - numpy.sin(rows))) < 1e-6


def test_another_theta_changes_the_table(meta_table):
    other = build(positions=4, **{**META, "theta": 10000})
    assert numpy.array_equal(build(positions=4, **META), meta_table[:4])
    assert not numpy.array_equal(other, meta_table[:4])
    assert numpy.array_equal(other[0], meta_table[0])


def test_no_scaling_changes_only_the_scaled_columns(meta_table, unscaled_table):
    assert numpy.array_equal(unscaled_table[:, :30], meta_table[:, :30])
    assert all(unscaled_table[2047, 30:] != meta_table[2047, 30:])


@pytest.mark.parametrize("t", [1, 1000, 2046])
def test_row_t_is_position_t(meta_table, t):
    assert row_bits(meta_table, t) == reference_row(t, META)
    assert row_bits(meta_table, t) != reference_row(t - 1, META)
    assert row_bits(meta_table, t) != reference_row(t + 1, META)


def test_columns_hold_cos_and_sin_of_one_angle(meta_table):
    row = meta_table[2047].astype(numpy.float64)
    cosines, sines = row[0::2], row[1::2]
    assert numpy.all(numpy.abs(cosines**2 + sines**2 - 1) <= 2**-22)
    g = frequencies(**META)
    for i in range(32):
        cosine, sine = reference_cos_sin(2047 * reference_g(i, META))
        assert (sines[i] < 0) == (sine < 0)
        assert (cosines[i] < 0) == (cosine < 0)
        assert sines[i] == pytest.approx(math.sin(2047 * g[i]), abs=1e-6)


def test_the_result_form(meta_table):
    assert type(meta_table) is numpy.ndarray
    assert meta_table.dtype == numpy.float32
    assert meta_table.shape == (2048, 64)
    assert meta_table.flags["C_CONTIGUOUS"]
    assert numpy.all(numpy.isfinite(meta_table))
    assert numpy.all(numpy.abs(meta_table) <= 1)


def test_a_new_array_each_call():
    first = build(positions=3, **META)
    first[:] = 7
    second = build(positions=3, **META)
    assert not numpy.shares_memory(first, second)
    assert numpy.all(second[0, 0::2] == 1.0)
    assert numpy.all(numpy.abs(second) <= 1)


def test_one_position():
    table = build(positions=1, **META)
    assert table.shape == (1, 64)
    assert row_bits(table, 0) == reference_row(0, META)


def test_low_precision_recomputes_and_still_equals_the_reference(monkeypatch):
    seen = []
    original = rope_table._frequency

    def spy(i, head_dim, constants, digits):
        seen.append(digits)
        return original(i, head_dim, constants, digits)

    monkeypatch.setattr(rope_table, "_DIGITS", 8)
    monkeypatch.setattr(rope_table, "_frequency", spy)
    small = SMALL[0]
    constants = {key: value for key, value in small.items() if key != "positions"}
    table = build(**small)
    for t in range(small["positions"]):
        assert row_bits(table, t) == reference_row(t, constants)
    assert frequencies(**constants) == tuple(
        float(reference_g(i, constants)) for i in range(4)
    )
    assert max(seen) > 16


def test_an_undecided_band_is_recomputed(monkeypatch):
    constants = {
        "head_dim": 2,
        "theta": 10000,
        "scale_factor": 2,
        "low_freq_factor": 1,
        "high_freq_factor": 4,
        "old_context_len": math.tau,
    }
    assert reference_band(0, 2, *(constants[name] for name in CONSTANTS))[0] == (
        "scaled"
    )
    assert frequencies(**constants) == (0.5,)
    monkeypatch.setattr(rope_table, "_DIGITS", 8)
    assert frequencies(**constants) == (0.5,)
    table = build(positions=5, **constants)
    for t in range(5):
        assert row_bits(table, t) == reference_row(t, constants)


@pytest.mark.parametrize(
    ("numerator", "expected"),
    [
        (2**53 + 1, 1.0),
        (2**53 + 3, 1.0 + 2**-51),
        (-(2**53 + 1), -1.0),
    ],
)
def test_a_binary64_tie_rounds_to_even(monkeypatch, numerator, expected):
    with decimal.localcontext(decimal.Context(prec=100)):
        value = Decimal(numerator) / Decimal(2**53)
    monkeypatch.setattr(rope_table, "_scaled", lambda *args: (value, value))
    assert frequencies(**{**META, "head_dim": 2}) == (expected,)


@pytest.mark.parametrize(
    ("numerator", "expected"),
    [
        (2**24 + 1, 1.0),
        (2**24 + 3, 1.0 + 2**-22),
    ],
)
def test_a_binary32_tie_rounds_to_even(monkeypatch, numerator, expected):
    with decimal.localcontext(decimal.Context(prec=100)):
        value = Decimal(numerator) / Decimal(2**24)
    monkeypatch.setattr(rope_table, "_BINARY64", rope_table._BINARY32)
    monkeypatch.setattr(rope_table, "_scaled", lambda *args: (value, value))
    assert frequencies(**{**META, "head_dim": 2}) == (expected,)


def test_frequencies_beyond_the_binary64_range():
    g = frequencies(**{**META, "head_dim": 2000, "theta": 5e-324})
    assert g[999] == math.inf
    assert math.isfinite(g[950])
    assert g[950] > 2**1000
    tiny = frequencies(**{**META, "head_dim": 2000, "theta": 1.7976931348623157e308})
    assert 0 < tiny[999] < 2**-1022
    assert tiny[999] == pytest.approx(
        math.exp(-(1998 / 2000) * math.log(1.7976931348623157e308) - math.log(8)),
        rel=1e-9,
    )


def test_a_large_angle_table_is_bounded():
    table = build(positions=3, **{**META, "head_dim": 4, "theta": 1e-300})
    assert numpy.all(numpy.abs(table) <= 1)
    assert numpy.abs(table[1:].astype(numpy.float64) ** 2).reshape(2, 2, 2).sum(
        axis=2
    ) == pytest.approx(1, abs=2**-22)


def call(function, **changes):
    arguments = dict(META)
    if function is build:
        arguments["positions"] = 4
    arguments.update(changes)
    return function(**arguments)


BAD_REALS = [
    (True, TypeError),
    ("1", TypeError),
    (None, TypeError),
    (1j, TypeError),
    (Decimal(1), TypeError),
    (0, ValueError),
    (0.0, ValueError),
    (-1, ValueError),
    (-2.5, ValueError),
    (math.nan, ValueError),
    (math.inf, ValueError),
    (-math.inf, ValueError),
]
BAD_HEAD_DIMS = [
    (True, TypeError),
    ("64", TypeError),
    (None, TypeError),
    (1j, TypeError),
    (64.0, TypeError),
    (0, ValueError),
    (1, ValueError),
    (63, ValueError),
    (-2, ValueError),
    (MAX_INTEGER + 1, ValueError),
]
BAD_POSITIONS = [
    (True, TypeError),
    ("4", TypeError),
    (None, TypeError),
    (1j, TypeError),
    (4.0, TypeError),
    (0, ValueError),
    (-1, ValueError),
    (MAX_INTEGER + 1, ValueError),
    (MAX_INTEGER // 64 + 1, ValueError),
]


@pytest.mark.parametrize("function", [frequencies, build])
@pytest.mark.parametrize("name", CONSTANTS)
@pytest.mark.parametrize(("value", "error"), BAD_REALS)
def test_bad_constants(function, name, value, error):
    with pytest.raises(error) as raised:
        call(function, **{name: value})
    assert raised.value.parameter == name


@pytest.mark.parametrize("function", [frequencies, build])
@pytest.mark.parametrize(("value", "error"), BAD_HEAD_DIMS)
def test_bad_head_dim(function, value, error):
    with pytest.raises(error) as raised:
        call(function, head_dim=value)
    assert raised.value.parameter == "head_dim"


@pytest.mark.parametrize(("value", "error"), BAD_POSITIONS)
def test_bad_positions(value, error):
    with pytest.raises(error) as raised:
        call(build, positions=value)
    assert raised.value.parameter == "positions"


def test_the_largest_positions_pass_the_check(monkeypatch):
    monkeypatch.setattr(rope_table.numpy, "empty", lambda *args, **kwargs: None)
    with pytest.raises(TypeError) as raised:
        call(build, positions=MAX_INTEGER // 64)
    assert not hasattr(raised.value, "parameter")


@pytest.mark.parametrize("function", [frequencies, build])
@pytest.mark.parametrize("high", [1, 1.0, 0.5])
def test_high_freq_factor_must_exceed_low_freq_factor(function, high):
    with pytest.raises(ValueError) as raised:
        call(function, high_freq_factor=high)
    assert raised.value.parameter == "high_freq_factor"


@pytest.mark.parametrize("function", [frequencies, build])
def test_the_first_bad_argument_is_reported(function):
    with pytest.raises(TypeError) as raised:
        call(function, head_dim=None, theta=None, old_context_len=0)
    assert raised.value.parameter == "head_dim"
    with pytest.raises(ValueError) as raised:
        call(function, low_freq_factor=0, high_freq_factor=None)
    assert raised.value.parameter == "low_freq_factor"
    if function is build:
        with pytest.raises(ValueError) as raised:
            call(function, old_context_len=-1, positions=0)
        assert raised.value.parameter == "old_context_len"


@pytest.mark.parametrize("function", [frequencies, build])
def test_a_missing_or_positional_argument(function):
    for name in SIGNATURE + (("positions",) if function is build else ()):
        arguments = dict(META, positions=4) if function is build else dict(META)
        del arguments[name]
        with pytest.raises(TypeError):
            function(**arguments)
    with pytest.raises(TypeError):
        function(64, 500000, 8, 1, 4, 8192)


def test_a_huge_int_constant_is_accepted():
    kept = frequencies(**{**META, "head_dim": 4, "old_context_len": 10**400})
    assert kept[0] == 1.0
    scaled = frequencies(
        **{
            **META,
            "head_dim": 4,
            "low_freq_factor": 10**400,
            "high_freq_factor": 10**400 + 1,
        }
    )
    assert scaled[0] == 1.0 / 8


def test_the_public_names_and_signatures():
    import inspect

    public = {name for name in vars(rope_table) if not name.startswith("_")}
    imported = {
        "contextlib",
        "decimal",
        "math",
        "Decimal",
        "numpy",
        "keys",
    }
    assert public - imported == {"frequencies", "build"}
    for function, names in (
        (frequencies, SIGNATURE),
        (build, SIGNATURE + ("positions",)),
    ):
        parameters = inspect.signature(function).parameters
        assert tuple(parameters) == names
        for parameter in parameters.values():
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
            assert parameter.default is inspect.Parameter.empty


def test_the_module_imports_and_text():
    own = Path(rope_table.__file__)
    text = own.read_text(encoding="utf-8")
    assert imported_modules(own) == {
        "contextlib",
        "decimal",
        "decimal.Decimal",
        "math",
        "numpy",
        "hilclaw",
        "hilclaw.keys",
    }
    for word in ("rope_bf16_contract", "model_binding", "500000", "8192"):
        assert word not in text
    assert "use_scaled" not in text
    assert "__main__" not in text


def test_the_module_is_named_by_no_other_module():
    own = Path(rope_table.__file__)
    for path in sorted(own.parent.rglob("*.py")):
        if path != own:
            assert "rope_table" not in path.read_text(encoding="utf-8"), path


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    frequencies(**META)
    build(positions=3, **META)
    with pytest.raises(ValueError):
        build(positions=0, **META)
    assert list(tmp_path.iterdir()) == []
