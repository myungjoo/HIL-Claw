import ast
import inspect
from pathlib import Path

import pytest

from hilclaw import check_parameters
from hilclaw.check_parameters import BF16, Bf16CheckParameters, CheckParameters

# Test values, not a seed, a number of draws or dimensions of the package.
FIVE = {"seed": 7, "draws": 3, "m": 4, "k": 5, "n": 6}


def test_the_five_values_are_given_by_position_and_read_back_by_name():
    made = CheckParameters(7, 3, 4, 5, 6)
    assert (made.seed, made.draws, made.m, made.k, made.n) == (7, 3, 4, 5, 6)
    assert len(made) == 5


def test_the_five_values_are_given_by_keyword_in_any_order():
    made = CheckParameters(n=6, k=5, m=4, draws=3, seed=7)
    assert made == CheckParameters(7, 3, 4, 5, 6)
    assert made == CheckParameters(**FIVE)
    assert CheckParameters(7, 3, m=4, k=5, n=6) == made


def test_equal_values_give_equal_instances_and_other_values_do_not():
    assert CheckParameters(**FIVE) == CheckParameters(**FIVE)
    assert hash(CheckParameters(**FIVE)) == hash(CheckParameters(**FIVE))
    for name, value in FIVE.items():
        other = CheckParameters(**{**FIVE, name: value + 1})
        assert other != CheckParameters(**FIVE)


def test_the_fields_are_the_five_in_their_order():
    assert CheckParameters._fields == ("seed", "draws", "m", "k", "n")
    seed, draws, m, k, n = CheckParameters(**FIVE)
    assert (seed, draws, m, k, n) == (7, 3, 4, 5, 6)
    assert CheckParameters(1, 2, 3, 4, 5) != CheckParameters(5, 4, 3, 2, 1)


def test_nothing_is_checked_when_an_instance_is_built():
    made = CheckParameters(-1, 0, True, "1", None)
    assert tuple(made) == (-1, 0, True, "1", None)
    assert CheckParameters(2**64, 2**64, 2**70, 1, 1).seed == 2**64


@pytest.mark.parametrize("name", list(FIVE))
def test_a_missing_value_is_refused(name):
    given = {key: value for key, value in FIVE.items() if key != name}
    with pytest.raises(TypeError):
        CheckParameters(**given)


def test_too_few_and_too_many_values_are_refused():
    with pytest.raises(TypeError):
        CheckParameters()
    with pytest.raises(TypeError):
        CheckParameters(7, 3, 4, 5)
    with pytest.raises(TypeError):
        CheckParameters(7, 3, 4, 5, 6, 1e-5)
    with pytest.raises(TypeError):
        CheckParameters(**FIVE, rtol=1e-5)
    with pytest.raises(TypeError):
        CheckParameters(7, **FIVE)


@pytest.mark.parametrize("name", [*FIVE, "rtol"])
def test_a_field_cannot_be_assigned(name):
    made = CheckParameters(**FIVE)
    with pytest.raises(AttributeError):
        setattr(made, name, 1)
    assert made == CheckParameters(**FIVE)


def test_no_field_has_a_default():
    assert CheckParameters._field_defaults == {}
    parameters = inspect.signature(CheckParameters).parameters
    assert list(parameters) == list(FIVE)
    for parameter in parameters.values():
        assert parameter.default is inspect.Parameter.empty, parameter


def test_the_module_has_the_type_and_imports_typing_only():
    public = {
        name
        for name, value in vars(check_parameters).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"CheckParameters", "Bf16CheckParameters", "BF16"}
    assert CheckParameters.__module__ == "hilclaw.check_parameters"
    assert CheckParameters.__bases__ == (tuple,)
    found = set()
    source = Path(check_parameters.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or ""))
    assert found == {"typing"}


BF16_FIVE = {"seed": 7, "draws": 3, "kind": "gemm", "dtype": "bf16", "dims": (4, 5, 6)}


def test_the_bf16_type_holds_the_five_values_in_their_order():
    assert Bf16CheckParameters._fields == ("seed", "draws", "kind", "dtype", "dims")
    made = Bf16CheckParameters(**BF16_FIVE)
    assert tuple(made) == (7, 3, "gemm", "bf16", (4, 5, 6))
    assert made == Bf16CheckParameters(7, 3, "gemm", "bf16", (4, 5, 6))
    assert Bf16CheckParameters.__bases__ == (tuple,)
    assert BF16 == "bf16"


def test_the_bf16_type_is_no_check_parameters_and_differs_by_any_value():
    made = Bf16CheckParameters(**BF16_FIVE)
    assert type(made) is not CheckParameters
    other = Bf16CheckParameters(**{**BF16_FIVE, "kind": "rmsnorm", "dims": (4, 6)})
    assert other != made


def test_nothing_is_checked_when_a_bf16_instance_is_built():
    made = Bf16CheckParameters(-1, 0, "conv", "fp32", [True, 0])
    assert tuple(made) == (-1, 0, "conv", "fp32", [True, 0])


@pytest.mark.parametrize("name", list(BF16_FIVE))
def test_a_missing_bf16_value_is_refused(name):
    given = {key: value for key, value in BF16_FIVE.items() if key != name}
    with pytest.raises(TypeError):
        Bf16CheckParameters(**given)


def test_the_bf16_type_holds_the_five_dims_of_sdpa_kv_cache():
    made = Bf16CheckParameters(7, 3, "sdpa_kv_cache", "bf16", (1, 2, 4, 2, 4))
    assert made.dims == (1, 2, 4, 2, 4)
    assert made.kind == "sdpa_kv_cache"
