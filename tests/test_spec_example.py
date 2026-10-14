import codecs
import copy
from pathlib import Path

import pytest

from hilclaw import gemm_contract, keys, spec, spec_file

# ADR-0058 decision 4 and Example; values cited there, none of a real run or machine.
EXAMPLE = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "spec"
    / "gemm-485b9bc494d477eb.json"
)
PLACEHOLDER_TECHNIQUES = [{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}]

# ADR-0035 Example: a plainly fictitious machine.
HW_RECORD = {
    "schema_version": 1,
    "accelerator": "cpu_standin",
    "revision": "host",
    "toolchain": {"clang": "Example clang version 0.0.0 (fictitious-build 1)"},
    "host": {
        "cpu": "Example(R) Fictitious(TM) X-0000 CPU @ 0.00GHz",
        "os": "linux exampleos 0.0",
    },
    "hw_source": "external",
}


def content():
    return EXAMPLE.read_bytes()


def expected():
    op_record = gemm_contract.op_signature_record(1, 2048, 8192)
    return {
        "schema_version": spec.SCHEMA_VERSION,
        "id": {
            "run_id": "20261009t012331z-9f3a6c1e0b7d4a52",
            "round": 1,
            "candidate": 1,
            "attempt": 1,
            "candidates": 1,
            "relation": "single",
        },
        "hw_profile": {
            "key": keys.hw_profile_key(HW_RECORD).name,
            "record": copy.deepcopy(HW_RECORD),
        },
        "task": {
            "op_signature": {
                "key": keys.op_signature_key(op_record).name,
                "record": op_record,
            },
            "contract": gemm_contract.task_contract(1, 2048, 8192),
            "objective": {
                "objectives": [{"type": "latency_minimisation"}],
                "constraints": [],
            },
        },
        "guidance": {"techniques": []},
        "feedback": {"attempts": []},
    }


def substituted(document, op_shape, contract_shape, key_shape=None):
    result = copy.deepcopy(document)
    record = gemm_contract.op_signature_record(*op_shape)
    key_record = gemm_contract.op_signature_record(*(key_shape or op_shape))
    result["task"]["op_signature"] = {
        "key": keys.op_signature_key(key_record).name,
        "record": record,
    }
    result["task"]["contract"] = gemm_contract.task_contract(*contract_shape)
    return result


def test_t1_parse_accepts_the_bytes():
    document = spec_file.parse(content())
    assert isinstance(document, dict)


def test_t2_written_form():
    data = content()
    assert data.endswith(b"\n")
    assert b"\r" not in data
    assert not data.startswith(codecs.BOM_UTF8)


def test_t3_cited_keys():
    op_record = gemm_contract.op_signature_record(1, 2048, 8192)
    assert keys.op_signature_key(op_record).name == "gemm-485b9bc494d477eb"
    assert keys.hw_profile_key(HW_RECORD).name == "cpu_standin-8c0be275e5925ab0"
    assert spec.SCHEMA_VERSION == 2
    assert EXAMPLE.name == "gemm-485b9bc494d477eb.json"


def test_t3_document_equals_the_example():
    document = spec_file.parse(content())
    assert document == expected()
    assert document["schema_version"] == 2
    assert document["guidance"]["techniques"] == []
    assert "repair" not in document
    assert "ext" not in document
    assert "build" not in document["task"]
    assert "base" not in document["feedback"]


def test_t4_twelve_first_shapes():
    assert len(gemm_contract.FIRST_SHAPES) == 12
    assert len(set(gemm_contract.FIRST_SHAPES)) == 12


@pytest.mark.parametrize("shape", gemm_contract.FIRST_SHAPES)
def test_t4_each_first_shape_is_valid(shape):
    document = substituted(spec_file.parse(content()), shape, shape)
    spec.validate(document)
    assert document["task"]["op_signature"]["record"]["shape"] == dict(
        zip("mkn", shape, strict=True)
    )


def test_negative_key_of_another_shape_is_refused():
    document = substituted(
        spec_file.parse(content()), (32, 2048, 8192), (32, 2048, 8192), (1, 2048, 8192)
    )
    with pytest.raises(spec.InvalidSpecError):
        spec.validate(document)


def test_negative_contract_left_at_m_1_is_refused():
    document = substituted(
        spec_file.parse(content()), (512, 8192, 2048), (1, 8192, 2048)
    )
    with pytest.raises(spec.InvalidSpecError):
        spec.validate(document)


def test_negative_byte_order_mark_is_refused():
    with pytest.raises(spec_file.InvalidSpecFileError):
        spec_file.parse(codecs.BOM_UTF8 + content())


def test_negative_placeholder_technique_differs_from_the_example():
    document = spec_file.parse(content())
    document["guidance"]["techniques"] = copy.deepcopy(PLACEHOLDER_TECHNIQUES)
    assert document != expected()


def test_negative_changed_value_differs_from_the_example():
    document = spec_file.parse(content())
    document["id"]["run_id"] = "20261009t012331z-0000000000000000"
    assert document != expected()
