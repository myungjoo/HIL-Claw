import ast
import inspect
from pathlib import Path

import pytest

from hilclaw import run_parameters
from hilclaw.run_parameters import Bf16TimingParameters, TimingParameters

# Test values, not dimensions, a bound, a sample form or a seed of the package.
SIX = {"m": 4, "k": 5, "n": 6, "n_max": 9, "sample_form": "interval", "seed": 7}


def test_the_six_values_are_given_by_position_and_read_back_by_name():
    made = TimingParameters(4, 5, 6, 9, "interval", 7)
    assert (made.m, made.k, made.n, made.n_max, made.sample_form, made.seed) == (
        4,
        5,
        6,
        9,
        "interval",
        7,
    )
    assert len(made) == 6


def test_the_six_values_are_given_by_keyword_in_any_order():
    made = TimingParameters(seed=7, sample_form="interval", n_max=9, n=6, k=5, m=4)
    assert made == TimingParameters(4, 5, 6, 9, "interval", 7)
    assert made == TimingParameters(**SIX)
    assert TimingParameters(4, 5, 6, n_max=9, sample_form="interval", seed=7) == made


def test_equal_values_give_equal_instances_and_other_values_do_not():
    assert TimingParameters(**SIX) == TimingParameters(**SIX)
    assert hash(TimingParameters(**SIX)) == hash(TimingParameters(**SIX))
    for name, value in SIX.items():
        other = TimingParameters(**{**SIX, name: value * 2})
        assert other != TimingParameters(**SIX)


def test_the_fields_are_the_six_in_their_order():
    assert TimingParameters._fields == ("m", "k", "n", "n_max", "sample_form", "seed")
    m, k, n, n_max, sample_form, seed = TimingParameters(**SIX)
    assert (m, k, n, n_max, sample_form, seed) == (4, 5, 6, 9, "interval", 7)
    assert TimingParameters(1, 2, 3, 4, "x", 5) != TimingParameters(5, 4, 3, 2, "x", 1)


def test_nothing_is_checked_when_an_instance_is_built():
    made = TimingParameters(-1, 0, True, "1", None, 2**64)
    assert tuple(made) == (-1, 0, True, "1", None, 2**64)
    assert TimingParameters(2**70, 1, 1, 0, "reciprocal", -5).m == 2**70


@pytest.mark.parametrize("name", list(SIX))
def test_a_missing_value_is_refused(name):
    given = {key: value for key, value in SIX.items() if key != name}
    with pytest.raises(TypeError):
        TimingParameters(**given)


def test_too_few_and_too_many_values_are_refused():
    with pytest.raises(TypeError):
        TimingParameters()
    with pytest.raises(TypeError):
        TimingParameters(4, 5, 6, 9, "interval")
    with pytest.raises(TypeError):
        TimingParameters(4, 5, 6, 9, "interval", 7, "output")
    for extra in ("output_path", "bound", "objective", "n_min", "cv_max", "point"):
        with pytest.raises(TypeError):
            TimingParameters(**SIX, **{extra: 1})
    with pytest.raises(TypeError):
        TimingParameters(4, **SIX)


@pytest.mark.parametrize("name", [*SIX, "output_path"])
def test_a_field_cannot_be_assigned(name):
    made = TimingParameters(**SIX)
    with pytest.raises(AttributeError):
        setattr(made, name, 1)
    assert made == TimingParameters(**SIX)


def test_no_field_has_a_default():
    assert TimingParameters._field_defaults == {}
    parameters = inspect.signature(TimingParameters).parameters
    assert list(parameters) == list(SIX)
    for parameter in parameters.values():
        assert parameter.default is inspect.Parameter.empty, parameter


def test_the_module_has_the_type_and_imports_typing_only():
    public = {
        name
        for name, value in vars(run_parameters).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"Bf16TimingParameters", "TimingParameters"}
    assert TimingParameters.__module__ == "hilclaw.run_parameters"
    assert TimingParameters.__bases__ == (tuple,)
    assert Bf16TimingParameters.__module__ == "hilclaw.run_parameters"
    assert Bf16TimingParameters.__bases__ == (tuple,)
    found = set()
    source = Path(run_parameters.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or ""))
    assert found == {"typing"}


# The second type (ADR-0181 decision 4)

BF16 = {
    "kind": "rmsnorm",
    "dtype": "bf16",
    "dims": (4, 6),
    "n_max": 9,
    "sample_form": "interval",
    "seed": 7,
}


def test_the_bf16_values_are_given_by_position_and_read_back_by_name():
    made = Bf16TimingParameters("rmsnorm", "bf16", (4, 6), 9, "interval", 7)
    assert made._asdict() == BF16
    assert Bf16TimingParameters(**BF16) == made
    assert hash(Bf16TimingParameters(**BF16)) == hash(made)
    assert Bf16TimingParameters._fields == tuple(BF16)


@pytest.mark.parametrize(
    ("name", "other"),
    [
        ("kind", "swiglu"),
        ("dtype", "fp16"),
        ("dims", (6, 4)),
        ("n_max", 10),
        ("sample_form", "reciprocal"),
        ("seed", 8),
    ],
)
def test_bf16_values_that_differ_give_instances_that_differ(name, other):
    assert Bf16TimingParameters(**{**BF16, name: other}) != Bf16TimingParameters(**BF16)


def test_nothing_is_checked_when_a_bf16_instance_is_built():
    made = Bf16TimingParameters(None, 1, [0], "1", None, -1)
    assert tuple(made) == (None, 1, [0], "1", None, -1)


@pytest.mark.parametrize("name", list(BF16))
def test_a_missing_bf16_value_is_refused(name):
    with pytest.raises(TypeError):
        Bf16TimingParameters(**{k: v for k, v in BF16.items() if k != name})


@pytest.mark.parametrize("extra", ["output_path", "bound", "m", "draws"])
def test_a_further_bf16_value_is_refused(extra):
    with pytest.raises(TypeError):
        Bf16TimingParameters(**BF16, **{extra: 1})


def test_a_bf16_field_cannot_be_assigned_and_none_has_a_default():
    made = Bf16TimingParameters(**BF16)
    with pytest.raises(AttributeError):
        made.dims = (1, 1)
    assert Bf16TimingParameters._field_defaults == {}


def test_the_two_types_are_distinct_and_timing_parameters_keep_six():
    assert type(Bf16TimingParameters(**BF16)) is not TimingParameters
    assert TimingParameters._fields == ("m", "k", "n", "n_max", "sample_form", "seed")
