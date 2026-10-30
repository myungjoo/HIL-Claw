import ast
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    contract_table,
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    gemm_contract,
    keys,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.contract_table import (
    TABLE,
    Entry,
    check_covers,
    covers,
    entry,
    run_covers,
    start_covers,
    task_contract,
)

CONTRACTS = (
    gemm_contract,
    gemm_bf16_contract,
    rmsnorm_bf16_contract,
    elementwise_add_bf16_contract,
    swiglu_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
)
SHAPES = {
    gemm_contract: gemm_contract.FIRST_SHAPES,
    **{contract: contract.SHAPES for contract in CONTRACTS[1:]},
}
PREDICATES = (covers, check_covers, run_covers, start_covers)


def named(contract):
    return contract.__name__.rsplit(".", 1)[1]


def first(contract):
    return contract.op_signature_record(*SHAPES[contract][0])


# The table


def test_the_table_lists_the_seven_contracts_keyed_by_their_binding():
    assert list(TABLE) == [
        ("gemm", "fp32", "row_major", "c"),
        ("gemm", "bf16", "row_major", "c"),
        ("rmsnorm", "bf16", "row_major", "c"),
        ("elementwise_add", "bf16", "row_major", "c"),
        ("swiglu", "bf16", "row_major", "c"),
        ("rope", "bf16", "row_major", "c"),
        ("sdpa_kv_cache", "bf16", "row_major", "c"),
    ]
    for (kind, dtype, layout, language), found in TABLE.items():
        assert type(found) is Entry
        assert (found.contract.KIND, found.contract.DTYPE) == (kind, dtype)
        assert (found.contract.LAYOUT, found.contract.LANGUAGE) == (layout, language)
    assert [found.contract for found in TABLE.values()] == list(CONTRACTS)


def test_at_most_one_entry_per_kind_dtype_and_layout():
    triples = [key[:3] for key in TABLE]
    assert len(set(triples)) == len(triples)


def test_the_flags_of_this_slice():
    assert TABLE[("gemm", "fp32", "row_major", "c")] == Entry(gemm_contract, True, True)
    for contract in CONTRACTS[1:]:
        found = TABLE[
            (contract.KIND, contract.DTYPE, contract.LAYOUT, contract.LANGUAGE)
        ]
        assert (found.checked, found.timed) == (True, True)


def test_the_table_cannot_be_changed():
    with pytest.raises(TypeError):
        TABLE[("gemm", "fp16", "row_major", "c")] = Entry(gemm_contract, True, True)


def test_another_language_names_no_entry():
    assert ("gemm", "fp32", "row_major", "cuda") not in TABLE
    assert all(key[3] == "c" for key in TABLE)


# Happy: each of the seven contracts


@pytest.mark.parametrize("contract", CONTRACTS, ids=named)
def test_each_contract_covers_its_shapes(contract):
    for shape in SHAPES[contract]:
        record = contract.op_signature_record(*shape)
        assert entry(record).contract is contract
        assert covers(record) is True
        assert task_contract(record) == contract.task_contract(*shape)


@pytest.mark.parametrize("contract", CONTRACTS, ids=named)
def test_the_task_contract_passes_the_shape_in_parameter_order(contract):
    parameters = list(inspect.signature(contract.task_contract).parameters)
    shape = tuple(range(2, 2 + len(parameters)))
    if contract is rope_bf16_contract:
        shape = (3, 5, 8)
    if contract is sdpa_kv_cache_bf16_contract:
        shape = (2, 5, 6, 3, 4)
    record = contract.op_signature_record(*shape)
    assert task_contract(record) == contract.task_contract(*shape)


def test_the_four_predicates_of_fp32_gemm():
    record = first(gemm_contract)
    assert [predicate(record) for predicate in PREDICATES] == [True] * 4


@pytest.mark.parametrize("contract", CONTRACTS[1:], ids=named)
def test_the_four_predicates_of_a_bf16_contract(contract):
    record = first(contract)
    answers = [predicate(record) for predicate in PREDICATES]
    assert answers == [True, True, True, True]
    for answer in answers:
        assert type(answer) is bool


def test_a_predicate_follows_the_flags(monkeypatch):
    record = first(rmsnorm_bf16_contract)
    key = ("rmsnorm", "bf16", "row_major", "c")
    table = dict(TABLE)
    table[key] = Entry(rmsnorm_bf16_contract, checked=True, timed=False)
    monkeypatch.setattr(contract_table, "TABLE", table)
    assert (check_covers(record), run_covers(record), start_covers(record)) == (
        True,
        False,
        False,
    )
    table[key] = Entry(rmsnorm_bf16_contract, checked=True, timed=True)
    assert (check_covers(record), run_covers(record), start_covers(record)) == (
        True,
        True,
        True,
    )


def test_the_contract_module_is_asked_at_each_call(monkeypatch):
    asked = []

    def recorded(record):
        asked.append(record)
        return False

    monkeypatch.setattr(gemm_contract, "covers", recorded)
    record = first(gemm_contract)
    assert check_covers(record) is False
    assert asked == [record]


# Branch: same kind, other dtype; same dtype, other kind


def test_same_kind_other_dtype_goes_to_the_other_entry():
    fp32 = gemm_contract.op_signature_record(1, 2048, 8192)
    bf16 = gemm_bf16_contract.op_signature_record(1, 2048, 8192)
    assert entry(fp32).contract is gemm_contract
    assert entry(bf16).contract is gemm_bf16_contract
    assert task_contract(fp32)["prototype"] == gemm_contract.PROTOTYPE
    assert task_contract(bf16)["prototype"] == gemm_bf16_contract.PROTOTYPE
    assert check_covers(fp32) and check_covers(bf16)
    assert start_covers(fp32) and start_covers(bf16)
    fp16 = bf16 | {"dtype": "fp16"}
    assert not run_covers(fp16) and not start_covers(fp16)


def test_same_dtype_other_kind_goes_to_the_other_entry():
    rms = rmsnorm_bf16_contract.op_signature_record(1, 2048)
    add = elementwise_add_bf16_contract.op_signature_record(1, 2048)
    assert entry(rms).contract is rmsnorm_bf16_contract
    assert entry(add).contract is elementwise_add_bf16_contract
    assert task_contract(rms) != task_contract(add)


# Negative


def with_changes(record, **changes):
    return record | changes


NOT_COVERED = {
    "fp16_gemm": with_changes(first(gemm_contract), dtype="fp16"),
    "fp32_rmsnorm": with_changes(first(rmsnorm_bf16_contract), dtype="fp32"),
    "col_major_gemm": with_changes(first(gemm_contract), layout="col_major"),
    "col_major_rope": with_changes(first(rope_bf16_contract), layout="col_major"),
    "zero_m": with_changes(first(gemm_bf16_contract), shape={"m": 0, "k": 1, "n": 1}),
    "odd_rope_d": with_changes(
        first(rope_bf16_contract), shape={"m": 1, "h": 2, "d": 3}
    ),
    "sdpa_l_below_m": with_changes(
        first(sdpa_kv_cache_bf16_contract),
        shape={"m": 4, "l": 3, "h": 4, "h_kv": 2, "d": 2},
    ),
    "sdpa_h_not_a_multiple": with_changes(
        first(sdpa_kv_cache_bf16_contract),
        shape={"m": 1, "l": 1, "h": 5, "h_kv": 2, "d": 2},
    ),
}


@pytest.mark.parametrize("record", NOT_COVERED.values(), ids=list(NOT_COVERED))
def test_a_record_no_entry_covers(record):
    assert entry(record) is None
    for predicate in PREDICATES:
        assert predicate(record) is False
    with pytest.raises(ValueError, match="not covered") as caught:
        task_contract(record)
    assert type(caught.value) is ValueError


INVALID = {
    "not_a_mapping": ["gemm"],
    "none": None,
    "unknown_kind": with_changes(first(gemm_contract), kind="conv2d"),
    "bool_dimension": with_changes(
        first(gemm_contract), shape={"m": True, "k": 1, "n": 1}
    ),
    "float_dimension": with_changes(
        first(rmsnorm_bf16_contract), shape={"m": 1.0, "n": 2}
    ),
    "wrong_members": with_changes(
        first(rope_bf16_contract), shape={"m": 1, "k": 2, "n": 3}
    ),
}


@pytest.mark.parametrize("record", INVALID.values(), ids=list(INVALID))
def test_an_invalid_record_is_refused_by_every_function(record):
    for function in (entry, task_contract, *PREDICATES):
        with pytest.raises(keys.InvalidRecordError):
            function(record)


def test_a_record_is_not_modified():
    record = first(sdpa_kv_cache_bf16_contract)
    before = repr(record)
    for function in (entry, task_contract, *PREDICATES):
        function(record)
    assert repr(record) == before


# The module


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(contract_table).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "Entry",
        "TABLE",
        "check_covers",
        "covers",
        "entry",
        "run_covers",
        "start_covers",
        "task_contract",
    }


def test_the_module_imports_the_contract_modules_and_no_numpy():
    own = Path(contract_table.__file__)
    tree = ast.parse(own.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported |= {f"{node.module}.{alias.name}" for alias in node.names}
    assert imported == {"collections", "inspect", "types", "hilclaw.keys"} | {
        f"hilclaw.{named(contract)}" for contract in CONTRACTS
    }
    code = (
        "import sys\n"
        "import hilclaw.contract_table\n"
        "print(sorted(name for name in sys.modules if name.split('.')[0] == 'numpy'))\n"
    )
    found = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=own.parent.parent,
    )
    assert found.stdout.strip() == "[]"
