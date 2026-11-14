import ast
import inspect
from pathlib import Path

import pytest

from hilclaw import gemm_contract, gemm_cuda_contract, keys
from hilclaw.gemm_cuda_contract import (
    DTYPE,
    FIRST_SHAPES,
    KIND,
    LANGUAGE,
    LAYOUT,
    PROTOTYPE,
    covers,
    op_signature_record,
    task_contract,
)


def test_the_binding():
    assert (KIND, DTYPE, LAYOUT, LANGUAGE) == ("gemm", "fp32", "row_major", "cuda")


def test_the_prototype_is_the_declaration_of_adr_0207_decision_4():
    assert PROTOTYPE == (
        'extern "C" void hilclaw_gemm(size_t m, size_t k, size_t n, '
        "const float *a, const float *b, float *c);"
    )
    assert "restrict" not in PROTOTYPE


def test_the_shapes_record_and_covers_are_those_of_the_c_contract():
    assert FIRST_SHAPES is gemm_contract.FIRST_SHAPES
    assert op_signature_record is gemm_contract.op_signature_record
    assert covers is gemm_contract.covers


@pytest.mark.parametrize("shape", [(1, 2048, 8192), (5, 33, 7), (1, 1, 1)])
def test_the_task_contract_differs_from_the_c_one_in_language_and_prototype(shape):
    found = task_contract(*shape)
    c = gemm_contract.task_contract(*shape)
    assert list(found) == ["language", "prototype", "operands"]
    assert found["language"] == "cuda"
    assert found["prototype"] == PROTOTYPE
    assert found["operands"] == c["operands"]
    m, k, n = shape
    assert [operand["shape"] for operand in found["operands"]] == [
        [m, k],
        [k, n],
        [m, n],
    ]


def test_each_task_contract_is_new():
    first = task_contract(2, 3, 4)
    first["operands"][0]["shape"][0] = 99
    assert task_contract(2, 3, 4)["operands"][0]["shape"] == [2, 3]


def test_the_task_contract_has_the_parameters_m_k_n():
    assert list(inspect.signature(task_contract).parameters) == ["m", "k", "n"]


@pytest.mark.parametrize(
    "shape", [(0, 1, 1), (1, 0, 1), (1, 1, True), (1.0, 1, 1), (1, 1, 2**53)]
)
def test_a_refused_dimension_raises_as_the_c_contract_does(shape):
    with pytest.raises(keys.InvalidRecordError, match=r"^shape\."):
        task_contract(*shape)


def test_a_record_of_the_shape_is_covered_and_one_with_a_zero_is_not():
    record = op_signature_record(5, 33, 7)
    assert covers(record) is True
    assert covers(record | {"shape": {"m": 5, "k": 0, "n": 7}}) is False
    assert covers(record | {"dtype": "bf16"}) is False


def test_the_module_imports_the_c_contract_alone():
    tree = ast.parse(Path(gemm_cuda_contract.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported |= {f"{node.module}.{alias.name}" for alias in node.names}
    assert imported == {"hilclaw.gemm_contract"}
