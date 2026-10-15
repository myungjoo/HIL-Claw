import ast
import inspect
from pathlib import Path

import pytest

from hilclaw import run_parameters
from hilclaw.run_parameters import TimingParameters

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
    assert public == {"TimingParameters"}
    assert TimingParameters.__module__ == "hilclaw.run_parameters"
    assert TimingParameters.__bases__ == (tuple,)
    found = set()
    source = Path(run_parameters.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or ""))
    assert found == {"typing"}
