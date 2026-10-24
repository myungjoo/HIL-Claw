import copy
import enum
import hashlib
import re
from types import MappingProxyType

import pytest

from hilclaw import keys
from hilclaw.keys import (
    InvalidRecordError,
    Key,
    canonical_form,
    directory_name,
    hw_profile_key,
    op_signature_key,
)

# Expected values copied from ADR-0001 decision 7, not from the implementation.
PLACEHOLDER = "NOT-DECIDED-HERE"
ADR_HW_CANONICAL = (
    b'{"accelerator":"cpu_standin","host":{"cpu":"NOT-DECIDED-HERE",'
    b'"os":"NOT-DECIDED-HERE"},"revision":"NOT-DECIDED-HERE","schema_version":1,'
    b'"toolchain":{"clang":"NOT-DECIDED-HERE"}}'
)
ADR_HW_DIGEST = "b0d8610d8f470856c134056a9541f60ce9e7a5c6bfabbeb9f1b784e57c495f9f"
ADR_HW_NAME = "cpu_standin-b0d8610d8f470856"
ADR_OP_CANONICAL = (
    b'{"dtype":"fp32","kind":"gemm","layout":"NOT-DECIDED-HERE","schema_version":1,'
    b'"shape":{"k":2048,"m":1,"n":8192}}'
)
ADR_OP_DIGEST = "c43e96fb16cc3f35b841657b1743ba0a1109fb053418b480abc1764c5befe923"
ADR_OP_NAME = "gemm-c43e96fb16cc3f35"

REMOVE = object()
MAX_INTEGER = 2**53 - 1

BAD_NAMES = ["", "Upper", "1digit", "with-hyphen", "a" * 33, "name\n", 7, None, b"a"]
BAD_STRINGS = ["", "s" * 256, "line\nbreak", "del\x7f", "café", 7, None, b"s"]
BAD_INTEGERS = [-1, 2**53, True, False, 1.0, "1", None]
NOT_SCALARS = [None, [1], (1,), {"nested": 1}, 1.5, True]
NOT_MAPS = [None, "text", 1, ["cpu", "os"], [("cpu", "x")]]
BAD_MEMBER_NAMES = ["", "Upper", "1digit", "with-hyphen", "a" * 33, 1, None]


def adr_hw(hw_source="external"):
    return {
        "schema_version": 1,
        "accelerator": "cpu_standin",
        "revision": PLACEHOLDER,
        "toolchain": {"clang": PLACEHOLDER},
        "host": {"cpu": PLACEHOLDER, "os": PLACEHOLDER},
        "hw_source": hw_source,
    }


def adr_op_key_fields():
    return {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 1, "k": 2048, "n": 8192},
        "dtype": "fp32",
        "layout": PLACEHOLDER,
    }


def synthetic_hw():
    return {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev-A",
        "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }


def synthetic_op():
    return {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 3, "k": 5, "n": 7},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }


def changed(record, path, value):
    result = copy.deepcopy(record)
    target = result
    for part in path[:-1]:
        target = target[part]
    if value is REMOVE:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return result


def test_adr_example_hw_side():
    key = hw_profile_key(adr_hw())
    assert key == Key(ADR_HW_NAME, ADR_HW_DIGEST, ADR_HW_CANONICAL)
    assert isinstance(key.canonical, bytes)
    assert hashlib.sha256(key.canonical).hexdigest() == key.digest


def test_adr_example_hw_side_is_the_same_for_both_hw_sources():
    assert hw_profile_key(adr_hw("external")) == hw_profile_key(adr_hw("in_house"))


def test_adr_example_op_side_canonical_form_and_derivation():
    canonical = canonical_form(adr_op_key_fields())
    assert canonical == ADR_OP_CANONICAL
    assert directory_name("gemm", canonical) == Key(
        ADR_OP_NAME, ADR_OP_DIGEST, ADR_OP_CANONICAL
    )


def test_adr_example_op_side_is_not_a_valid_record():
    with pytest.raises(InvalidRecordError, match="layout"):
        op_signature_key(adr_op_key_fields())


def test_adr_example_hw_side_through_canonical_form_and_directory_name():
    fields = adr_hw()
    del fields["hw_source"]
    assert directory_name("cpu_standin", canonical_form(fields)) == Key(
        ADR_HW_NAME, ADR_HW_DIGEST, ADR_HW_CANONICAL
    )


def test_valid_gemm_record():
    key = op_signature_key(synthetic_op())
    assert key.canonical == (
        b'{"dtype":"synthetic_dtype","kind":"gemm","layout":"synthetic_layout",'
        b'"schema_version":1,"shape":{"k":5,"m":3,"n":7}}'
    )
    assert key.digest == hashlib.sha256(key.canonical).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", key.digest)
    assert key.name == f"gemm-{key.digest[:16]}"


def test_valid_hw_record_with_every_field():
    record = synthetic_hw()
    record["ext"] = {"synthetic_units": 4, "synthetic_stepping": "s0"}
    record["label"] = "synthetic profile for tests"
    key = hw_profile_key(record)
    assert key.canonical == (
        b'{"accelerator":"synthetic_accel",'
        b'"ext":{"synthetic_stepping":"s0","synthetic_units":4},'
        b'"host":{"cpu":"synthetic cpu","os":"synthetic os"},'
        b'"revision":"synthetic-rev-A","schema_version":1,'
        b'"toolchain":{"synthetic_cc":"0.0.1-synthetic"}}'
    )
    assert key.name == f"synthetic_accel-{key.digest[:16]}"


def test_name_charset_and_length_for_the_longest_prefix():
    prefix = "a" * 32
    for key in (
        directory_name(prefix, b"{}"),
        hw_profile_key(changed(synthetic_hw(), ["accelerator"], prefix)),
    ):
        assert len(key.name) == 49
        assert re.fullmatch(r"[a-z][a-z0-9_-]*", key.name)
        assert key.name == f"{prefix}-{key.digest[:16]}"


def test_member_order_does_not_change_the_key():
    hw = synthetic_hw()
    hw["host"]["synthetic_memory"] = 16
    hw["toolchain"]["synthetic_rt"] = "2"
    reordered = {name: hw[name] for name in reversed(list(hw))}
    reordered["host"] = dict(reversed(list(hw["host"].items())))
    reordered["toolchain"] = dict(reversed(list(hw["toolchain"].items())))
    assert list(reordered) != list(hw)
    assert hw_profile_key(reordered) == hw_profile_key(hw)

    op = synthetic_op()
    reordered = {name: op[name] for name in reversed(list(op))}
    reordered["shape"] = {"n": 7, "k": 5, "m": 3}
    assert op_signature_key(reordered) == op_signature_key(op)


def test_attributes_do_not_change_the_key():
    hw = synthetic_hw()
    labelled = changed(hw, ["label"], "a synthetic label")
    other_source = changed(hw, ["hw_source"], "external")
    assert hw_profile_key(labelled) == hw_profile_key(hw)
    assert hw_profile_key(other_source) == hw_profile_key(hw)
    assert b"label" not in hw_profile_key(labelled).canonical
    assert b"hw_source" not in hw_profile_key(hw).canonical

    op = synthetic_op()
    labelled = changed(op, ["label"], "a synthetic label")
    assert op_signature_key(labelled) == op_signature_key(op)
    assert b"label" not in op_signature_key(labelled).canonical


def test_absent_ext_is_left_out_of_the_canonical_form():
    assert b"ext" not in hw_profile_key(synthetic_hw()).canonical
    assert b"ext" not in op_signature_key(synthetic_op()).canonical


@pytest.mark.parametrize(
    "path, value",
    [
        (["revision"], "synthetic-rev-B"),
        (["accelerator"], "synthetic_other"),
        (["toolchain", "synthetic_cc"], "0.0.2-synthetic"),
        (["toolchain", "synthetic_rt"], "1"),
        (["host", "cpu"], "another synthetic cpu"),
        (["host", "os"], "another synthetic os"),
        (["host", "synthetic_memory"], 16),
        (["ext"], {"synthetic_units": 4}),
    ],
)
def test_every_hw_key_field_change_gives_another_name(path, value):
    base = hw_profile_key(synthetic_hw())
    other = hw_profile_key(changed(synthetic_hw(), path, value))
    assert other.name != base.name
    assert other.digest != base.digest
    assert other.canonical != base.canonical


def test_hw_ext_value_change_gives_another_name():
    one = changed(synthetic_hw(), ["ext"], {"synthetic_units": 4})
    two = changed(synthetic_hw(), ["ext"], {"synthetic_units": 5})
    assert hw_profile_key(one).name != hw_profile_key(two).name


@pytest.mark.parametrize(
    "path, value",
    [
        (["shape", "m"], 4),
        (["shape", "k"], 6),
        (["shape", "n"], 8),
        (["dtype"], "synthetic_other"),
        (["layout"], "synthetic_other"),
        (["ext"], {"synthetic_flag": "on"}),
    ],
)
def test_every_op_key_field_change_gives_another_name(path, value):
    base = op_signature_key(synthetic_op())
    other = op_signature_key(changed(synthetic_op(), path, value))
    assert other.name != base.name
    assert other.digest != base.digest


def test_string_and_integer_host_members():
    record = synthetic_hw()
    record["host"]["synthetic_memory"] = 34359738368
    record["host"]["synthetic_board"] = "rev 2"
    assert (
        b'"synthetic_board":"rev 2","synthetic_memory":34359738368'
        in hw_profile_key(record).canonical
    )
    record["host"]["cpu"] = 7
    assert b'"cpu":7' in hw_profile_key(record).canonical


@pytest.mark.parametrize("value", [0, 1, MAX_INTEGER])
def test_integer_limits(value):
    expected = f'{{"v":{value}}}'.encode()
    assert canonical_form({"v": value}) == expected
    record = changed(synthetic_op(), ["shape", "m"], value)
    assert f'"m":{value},'.encode() in op_signature_key(record).canonical
    record = changed(synthetic_hw(), ["ext"], {"v": value})
    assert expected in hw_profile_key(record).canonical


@pytest.mark.parametrize("value", ["s", "s" * 255, " ", "~"])
def test_string_limits(value):
    assert canonical_form({"v": value}) == f'{{"v":"{value}"}}'.encode()
    assert hw_profile_key(changed(synthetic_hw(), ["revision"], value))
    assert hw_profile_key(changed(synthetic_hw(), ["label"], value))
    assert op_signature_key(changed(synthetic_op(), ["label"], value))


@pytest.mark.parametrize("name", ["a", "a" * 32, "a0_", "z9"])
def test_name_limits(name):
    assert canonical_form({name: 1}) == f'{{"{name}":1}}'.encode()
    assert directory_name(name, b"x").name.startswith(f"{name}-")
    assert hw_profile_key(changed(synthetic_hw(), ["accelerator"], name))
    assert hw_profile_key(changed(synthetic_hw(), ["toolchain", name], "1"))
    assert op_signature_key(changed(synthetic_op(), ["dtype"], name))
    assert op_signature_key(changed(synthetic_op(), ["layout"], name))


def test_strings_are_escaped_only_for_quote_and_backslash():
    value = 'a "q" b\\c d/e'
    expected = rb'{"v":"a \"q\" b\\c d/e"}'
    assert canonical_form({"v": value}) == expected
    record = changed(synthetic_hw(), ["revision"], value)
    assert rb'"revision":"a \"q\" b\\c d/e"' in hw_profile_key(record).canonical


def test_every_printable_ascii_character_is_written_literally():
    value = "".join(chr(c) for c in range(0x20, 0x7F))
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    assert canonical_form({"v": value}) == f'{{"v":"{escaped}"}}'.encode("ascii")


def test_canonical_form_sorts_nested_maps_and_uses_no_whitespace():
    fields = {"b": {"z": 1, "a": {"y": "s", "x": 0}}, "a": "t"}
    assert canonical_form(fields) == b'{"a":"t","b":{"a":{"x":0,"y":"s"},"z":1}}'
    assert canonical_form({}) == b"{}"


def test_canonical_form_knows_no_field_names():
    assert canonical_form({"hw_source": "anything", "schema_version": 2}) == (
        b'{"hw_source":"anything","schema_version":2}'
    )


def test_read_only_mappings_are_accepted():
    hw = synthetic_hw()
    frozen = MappingProxyType(
        {**hw, "host": MappingProxyType(hw["host"]), "ext": MappingProxyType({"e": 1})}
    )
    assert hw_profile_key(frozen) == hw_profile_key(changed(hw, ["ext"], {"e": 1}))
    op = synthetic_op()
    frozen = MappingProxyType({**op, "shape": MappingProxyType(op["shape"])})
    assert op_signature_key(frozen) == op_signature_key(op)
    nested = MappingProxyType({"a": MappingProxyType({"b": 1})})
    assert canonical_form(nested) == b'{"a":{"b":1}}'


def test_input_records_are_not_modified():
    for function, record in (
        (hw_profile_key, changed(synthetic_hw(), ["ext"], {"e": 1})),
        (hw_profile_key, changed(synthetic_hw(), ["label"], "synthetic")),
        (op_signature_key, changed(synthetic_op(), ["ext"], {"e": "x"})),
        (canonical_form, {"b": {"c": 1}, "a": "s"}),
    ):
        before = copy.deepcopy(record)
        order = list(record)
        function(record)
        assert record == before
        assert list(record) == order


def test_error_is_a_value_error_that_names_field_and_rule():
    assert issubclass(InvalidRecordError, ValueError)
    with pytest.raises(InvalidRecordError) as error:
        hw_profile_key(changed(synthetic_hw(), ["host", "cpu"], ""))
    assert str(error.value).startswith("host.cpu: must be a string of 1 to 255")
    with pytest.raises(InvalidRecordError) as error:
        canonical_form({"a": {"b": {"c": 1.5}}})
    assert str(error.value).startswith("a.b.c: must be a string, an integer or a map")


def test_public_constants():
    assert keys.SCHEMA_VERSION == 1
    assert keys.MAX_INTEGER == 9007199254740991
    assert keys.NAME_DIGEST_LENGTH == 16
    assert keys.HW_SOURCES == ("external", "in_house")


@pytest.mark.parametrize("function", [hw_profile_key, op_signature_key, canonical_form])
@pytest.mark.parametrize("record", NOT_MAPS)
def test_record_that_is_not_a_mapping(function, record):
    with pytest.raises(InvalidRecordError, match="^record: must be a map"):
        function(record)


@pytest.mark.parametrize(
    "field",
    ["schema_version", "accelerator", "revision", "toolchain", "host", "hw_source"],
)
def test_hw_missing_required_field(field):
    with pytest.raises(InvalidRecordError, match=f"^{field}: required field"):
        hw_profile_key(changed(synthetic_hw(), [field], REMOVE))


@pytest.mark.parametrize(
    "field", ["schema_version", "kind", "shape", "dtype", "layout"]
)
def test_op_missing_required_field(field):
    with pytest.raises(InvalidRecordError, match=f"^{field}: required field"):
        op_signature_key(changed(synthetic_op(), [field], REMOVE))


@pytest.mark.parametrize(
    "field", ["tool_chain", "kind", "hwsource", "Label", "", 1, None]
)
def test_hw_unknown_field(field):
    with pytest.raises(InvalidRecordError, match="unknown field"):
        hw_profile_key(changed(synthetic_hw(), [field], "synthetic"))


@pytest.mark.parametrize("field", ["lay_out", "accelerator", "hw_source", "", 1, None])
def test_op_unknown_field(field):
    with pytest.raises(InvalidRecordError, match="unknown field"):
        op_signature_key(changed(synthetic_op(), [field], "external"))


@pytest.mark.parametrize(
    "function, record",
    [(hw_profile_key, synthetic_hw()), (op_signature_key, synthetic_op())],
)
@pytest.mark.parametrize("version", [2, 0, -1, True, "1", 1.0, None, [1], {"v": 1}])
def test_schema_version_must_be_the_integer_one(function, record, version):
    with pytest.raises(
        InvalidRecordError, match="^schema_version: must be the integer 1"
    ):
        function(changed(record, ["schema_version"], version))


@pytest.mark.parametrize("value", BAD_NAMES + [["a"], {"a": 1}])
def test_fields_that_must_be_names(value):
    with pytest.raises(InvalidRecordError, match="^accelerator: must be a name"):
        hw_profile_key(changed(synthetic_hw(), ["accelerator"], value))
    for field in ("kind", "dtype", "layout"):
        with pytest.raises(InvalidRecordError, match=f"^{field}: must be a name"):
            op_signature_key(changed(synthetic_op(), [field], value))
    with pytest.raises(InvalidRecordError, match="^prefix: must be a name"):
        directory_name(value, b"{}")


@pytest.mark.parametrize("value", BAD_STRINGS + [["s"], {"s": 1}, 1.5, True])
def test_fields_that_must_be_strings(value):
    for path in (["revision"], ["toolchain", "synthetic_cc"], ["label"]):
        with pytest.raises(
            InvalidRecordError, match=f"^{'.'.join(path)}: must be a string"
        ):
            hw_profile_key(changed(synthetic_hw(), path, value))
    with pytest.raises(InvalidRecordError, match="^label: must be a string"):
        op_signature_key(changed(synthetic_op(), ["label"], value))


@pytest.mark.parametrize(
    "value", ["", "s" * 256, "line\nbreak", "tab\t", "del\x7f", "nul\x00", "café", "あ"]
)
def test_strings_outside_the_value_set(value):
    with pytest.raises(InvalidRecordError, match="^v: must be a string of 1 to 255"):
        canonical_form({"v": value})
    for path in (["host", "cpu"], ["host", "synthetic_extra"], ["ext"]):
        record = changed(
            synthetic_hw(), path, {"v": value} if path == ["ext"] else value
        )
        with pytest.raises(InvalidRecordError, match="must be a string of 1 to 255"):
            hw_profile_key(record)
    with pytest.raises(
        InvalidRecordError, match="^ext.v: must be a string of 1 to 255"
    ):
        op_signature_key(changed(synthetic_op(), ["ext"], {"v": value}))


@pytest.mark.parametrize("value", BAD_INTEGERS + [[1], {"m": 1}, 1.5])
def test_shape_members_must_be_integers(value):
    for member in ("m", "k", "n"):
        with pytest.raises(
            InvalidRecordError, match=f"^shape.{member}: must be an integer"
        ):
            op_signature_key(changed(synthetic_op(), ["shape", member], value))


@pytest.mark.parametrize("value", [-1, 2**53, 2**64])
def test_integers_outside_the_range(value):
    with pytest.raises(InvalidRecordError, match="^v: must be an integer from 0"):
        canonical_form({"v": value})
    with pytest.raises(InvalidRecordError, match="^host.v: must be an integer from 0"):
        hw_profile_key(changed(synthetic_hw(), ["host", "v"], value))
    with pytest.raises(InvalidRecordError, match="^ext.v: must be an integer from 0"):
        op_signature_key(changed(synthetic_op(), ["ext"], {"v": value}))


@pytest.mark.parametrize("value", NOT_SCALARS)
def test_map_members_that_must_be_scalars(value):
    for path in (["host", "cpu"], ["host", "os"], ["host", "synthetic_extra"]):
        with pytest.raises(InvalidRecordError, match="must be a string or an integer"):
            hw_profile_key(changed(synthetic_hw(), path, value))
    with pytest.raises(
        InvalidRecordError, match="^ext.v: must be a string or an integer"
    ):
        hw_profile_key(changed(synthetic_hw(), ["ext"], {"v": value}))
    with pytest.raises(
        InvalidRecordError, match="^ext.v: must be a string or an integer"
    ):
        op_signature_key(changed(synthetic_op(), ["ext"], {"v": value}))


@pytest.mark.parametrize("value", [1, 0, 2**53, True, None, ["1"], {"v": "1"}, 1.5])
def test_toolchain_version_must_be_a_string(value):
    with pytest.raises(
        InvalidRecordError, match="^toolchain.synthetic_cc: must be a string"
    ):
        hw_profile_key(changed(synthetic_hw(), ["toolchain", "synthetic_cc"], value))


@pytest.mark.parametrize("value", NOT_MAPS)
def test_fields_that_must_be_maps(value):
    for field in ("toolchain", "host", "ext"):
        with pytest.raises(InvalidRecordError, match=f"^{field}: must be a map"):
            hw_profile_key(changed(synthetic_hw(), [field], value))
    for field in ("shape", "ext"):
        with pytest.raises(InvalidRecordError, match=f"^{field}: must be a map"):
            op_signature_key(changed(synthetic_op(), [field], value))


def test_empty_toolchain():
    with pytest.raises(
        InvalidRecordError, match="^toolchain: must be a map with at least"
    ):
        hw_profile_key(changed(synthetic_hw(), ["toolchain"], {}))


@pytest.mark.parametrize("member", ["cpu", "os"])
def test_host_without_a_required_member(member):
    with pytest.raises(InvalidRecordError, match=f"^host.{member}: required member"):
        hw_profile_key(changed(synthetic_hw(), ["host", member], REMOVE))


def test_empty_host():
    with pytest.raises(InvalidRecordError, match="^host.cpu: required member"):
        hw_profile_key(changed(synthetic_hw(), ["host"], {}))


def test_empty_ext():
    with pytest.raises(InvalidRecordError, match="^ext: must be a map with at least"):
        hw_profile_key(changed(synthetic_hw(), ["ext"], {}))
    with pytest.raises(InvalidRecordError, match="^ext: must be a map with at least"):
        op_signature_key(changed(synthetic_op(), ["ext"], {}))


@pytest.mark.parametrize("name", BAD_MEMBER_NAMES)
def test_member_names_must_be_names(name):
    for field in ("toolchain", "host", "ext"):
        record = synthetic_hw()
        record.setdefault(field, {})[name] = "synthetic"
        with pytest.raises(
            InvalidRecordError, match=f"^{field}: member name: must be a name"
        ):
            hw_profile_key(record)
    for field, value in (("shape", 1), ("ext", "synthetic")):
        record = synthetic_op()
        record.setdefault(field, {})[name] = value
        with pytest.raises(
            InvalidRecordError, match=f"^{field}: member name: must be a name"
        ):
            op_signature_key(record)
    with pytest.raises(
        InvalidRecordError, match="^record: member name: must be a name"
    ):
        canonical_form({name: 1})
    with pytest.raises(InvalidRecordError, match="^a: member name: must be a name"):
        canonical_form({"a": {name: 1}})


@pytest.mark.parametrize(
    "value",
    [
        PLACEHOLDER,
        "External",
        "IN_HOUSE",
        "in-house",
        "",
        "vendor",
        None,
        1,
        True,
        ["external"],
        {"external": 1},
    ],
)
def test_hw_source_must_be_one_of_the_two_values(value):
    with pytest.raises(
        InvalidRecordError, match="^hw_source: must be external or in_house"
    ):
        hw_profile_key(changed(synthetic_hw(), ["hw_source"], value))


def test_adr_hw_example_with_its_placeholder_hw_source_is_rejected():
    with pytest.raises(InvalidRecordError, match="^hw_source"):
        hw_profile_key(adr_hw(PLACEHOLDER))


@pytest.mark.parametrize(
    "shape",
    [
        {},
        {"m": 1, "k": 2},
        {"m": 1, "n": 2},
        {"k": 1, "n": 2},
        {"m": 1, "k": 2, "n": 3, "extra": 4},
        {"m": 1, "k": 2, "o": 3},
    ],
)
def test_gemm_shape_members_are_exactly_m_k_n(shape):
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members k, m, n",
    ):
        op_signature_key(changed(synthetic_op(), ["shape"], shape))


@pytest.mark.parametrize("kind", ["sdpa", "conv", "gemm2", "g"])
def test_unknown_kind_is_rejected(kind):
    with pytest.raises(
        InvalidRecordError,
        match="^kind: must be a known kind: elementwise_add, gemm, rmsnorm, rope, swiglu",
    ):
        op_signature_key(changed(synthetic_op(), ["kind"], kind))


def synthetic_rmsnorm_op():
    return dict(synthetic_op(), kind="rmsnorm", shape={"m": 3, "n": 7})


def test_rmsnorm_record_is_accepted():
    key = op_signature_key(synthetic_rmsnorm_op())
    assert key.name.startswith("rmsnorm-")
    assert hashlib.sha256(key.canonical).hexdigest() == key.digest


def test_rmsnorm_record_of_adr_0158_has_its_canonical_form_and_name():
    record = {
        "schema_version": 1,
        "kind": "rmsnorm",
        "shape": {"m": 1, "n": 2048},
        "dtype": "bf16",
        "layout": "row_major",
    }
    key = op_signature_key(record)
    assert key.canonical == (
        b'{"dtype":"bf16","kind":"rmsnorm","layout":"row_major",'
        b'"schema_version":1,"shape":{"m":1,"n":2048}}'
    )
    assert key.digest == (
        "57f1bdf44f626c31e71beef7ba688a245eca699394fdbc732d48fffe1b0de702"
    )
    assert key.name == "rmsnorm-57f1bdf44f626c31"


@pytest.mark.parametrize(
    "shape",
    [
        {},
        {"m": 1},
        {"n": 2},
        {"m": 1, "n": 2, "k": 3},
        {"m": 1, "k": 2, "n": 3},
        {"m": 1, "o": 2},
    ],
)
def test_rmsnorm_shape_members_are_exactly_m_n(shape):
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members m, n",
    ):
        op_signature_key(changed(synthetic_rmsnorm_op(), ["shape"], shape))


def test_gemm_still_needs_k_beside_m_and_n():
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members k, m, n",
    ):
        op_signature_key(changed(synthetic_op(), ["shape"], {"m": 3, "n": 7}))


def test_unknown_kind_message_lists_all_known_kinds():
    with pytest.raises(
        InvalidRecordError,
        match="^kind: must be a known kind: elementwise_add, gemm, rmsnorm, rope, swiglu, got",
    ):
        op_signature_key(changed(synthetic_op(), ["kind"], "sdpa"))


def synthetic_elementwise_add_op():
    return dict(synthetic_op(), kind="elementwise_add", shape={"m": 3, "n": 7})


def test_elementwise_add_record_is_accepted():
    key = op_signature_key(synthetic_elementwise_add_op())
    assert key.name.startswith("elementwise_add-")
    assert hashlib.sha256(key.canonical).hexdigest() == key.digest


def test_elementwise_add_record_of_adr_0159_has_its_canonical_form_and_name():
    record = {
        "schema_version": 1,
        "kind": "elementwise_add",
        "shape": {"m": 1, "n": 2048},
        "dtype": "bf16",
        "layout": "row_major",
    }
    key = op_signature_key(record)
    assert key.canonical == (
        b'{"dtype":"bf16","kind":"elementwise_add","layout":"row_major",'
        b'"schema_version":1,"shape":{"m":1,"n":2048}}'
    )
    assert key.digest == (
        "1af54bf2a0744c6977bb2d6411d15fb0a9cbdf0a997e159879d84bfe21708bce"
    )
    assert key.name == "elementwise_add-1af54bf2a0744c69"


@pytest.mark.parametrize(
    "shape",
    [
        {},
        {"m": 1},
        {"n": 2},
        {"m": 1, "n": 2, "k": 3},
        {"m": 1, "k": 2, "n": 3},
        {"m": 1, "o": 2},
    ],
)
def test_elementwise_add_shape_members_are_exactly_m_n(shape):
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members m, n",
    ):
        op_signature_key(changed(synthetic_elementwise_add_op(), ["shape"], shape))


def test_other_kinds_keep_their_members_beside_elementwise_add():
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members k, m, n",
    ):
        op_signature_key(changed(synthetic_op(), ["shape"], {"m": 3, "n": 7}))
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members m, n",
    ):
        op_signature_key(
            changed(synthetic_rmsnorm_op(), ["shape"], {"m": 1, "k": 2, "n": 3})
        )
    assert op_signature_key(synthetic_op()).name.startswith("gemm-")
    assert op_signature_key(synthetic_rmsnorm_op()).name.startswith("rmsnorm-")


def synthetic_swiglu_op():
    return dict(synthetic_op(), kind="swiglu", shape={"m": 3, "n": 7})


def test_swiglu_record_is_accepted():
    key = op_signature_key(synthetic_swiglu_op())
    assert key.name.startswith("swiglu-")
    assert hashlib.sha256(key.canonical).hexdigest() == key.digest


def test_swiglu_record_of_adr_0160_has_its_canonical_form_and_name():
    record = {
        "schema_version": 1,
        "kind": "swiglu",
        "shape": {"m": 1, "n": 8192},
        "dtype": "bf16",
        "layout": "row_major",
    }
    key = op_signature_key(record)
    assert key.canonical == (
        b'{"dtype":"bf16","kind":"swiglu","layout":"row_major",'
        b'"schema_version":1,"shape":{"m":1,"n":8192}}'
    )
    assert key.digest == (
        "7b82bc7d69cda1e0fd3794adbe3bce2274830ff1c53b3c20997ae095e352dc29"
    )
    assert key.name == "swiglu-7b82bc7d69cda1e0"


@pytest.mark.parametrize(
    "shape",
    [
        {},
        {"m": 1},
        {"n": 2},
        {"m": 1, "n": 2, "k": 3},
        {"m": 1, "k": 2, "n": 3},
        {"m": 1, "o": 2},
    ],
)
def test_swiglu_shape_members_are_exactly_m_n(shape):
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members m, n",
    ):
        op_signature_key(changed(synthetic_swiglu_op(), ["shape"], shape))


def test_other_kinds_keep_their_members_beside_swiglu():
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members k, m, n",
    ):
        op_signature_key(changed(synthetic_op(), ["shape"], {"m": 3, "n": 7}))
    for op in (synthetic_rmsnorm_op(), synthetic_elementwise_add_op()):
        with pytest.raises(
            InvalidRecordError,
            match="^shape: must be a map with exactly the members m, n",
        ):
            op_signature_key(changed(op, ["shape"], {"m": 1, "k": 2, "n": 3}))
        assert op_signature_key(op).name.startswith(op["kind"] + "-")
    assert op_signature_key(synthetic_op()).name.startswith("gemm-")


def synthetic_rope_op():
    return dict(synthetic_op(), kind="rope", shape={"m": 3, "h": 5, "d": 2})


def test_rope_record_is_accepted():
    key = op_signature_key(synthetic_rope_op())
    assert key.name.startswith("rope-")
    assert hashlib.sha256(key.canonical).hexdigest() == key.digest


def test_rope_record_of_adr_0161_has_its_canonical_form_and_name():
    record = {
        "schema_version": 1,
        "kind": "rope",
        "shape": {"m": 1, "h": 8, "d": 64},
        "dtype": "bf16",
        "layout": "row_major",
    }
    key = op_signature_key(record)
    assert key.canonical == (
        b'{"dtype":"bf16","kind":"rope","layout":"row_major",'
        b'"schema_version":1,"shape":{"d":64,"h":8,"m":1}}'
    )
    assert key.digest == (
        "c797475e043d41569f5a69878631c9c59bde735b28fc614aab427b1d9cd4006a"
    )
    assert key.name == "rope-c797475e043d4156"


@pytest.mark.parametrize(
    "shape",
    [
        {},
        {"m": 1, "h": 2},
        {"m": 1, "h": 2, "d": 4, "n": 5},
        {"m": 1, "k": 2, "n": 3},
        {"m": 1, "n": 2},
        {"m": 1, "h": 2, "k": 4},
    ],
)
def test_rope_shape_members_are_exactly_m_h_d(shape):
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members d, h, m",
    ):
        op_signature_key(changed(synthetic_rope_op(), ["shape"], shape))


@pytest.mark.parametrize("d", [1, 3, 63, 0])
def test_rope_record_with_an_odd_or_zero_d_is_accepted_by_the_keys(d):
    record = changed(synthetic_rope_op(), ["shape"], {"m": 3, "h": 5, "d": d})
    assert op_signature_key(record).name.startswith("rope-")


def test_other_kinds_keep_their_members_beside_rope():
    rope_shape = {"m": 1, "h": 2, "d": 4}
    with pytest.raises(
        InvalidRecordError,
        match="^shape: must be a map with exactly the members k, m, n",
    ):
        op_signature_key(changed(synthetic_op(), ["shape"], rope_shape))
    for op in (
        synthetic_rmsnorm_op(),
        synthetic_elementwise_add_op(),
        synthetic_swiglu_op(),
    ):
        with pytest.raises(
            InvalidRecordError,
            match="^shape: must be a map with exactly the members m, n",
        ):
            op_signature_key(changed(op, ["shape"], rope_shape))
        assert op_signature_key(op).name.startswith(op["kind"] + "-")
    assert op_signature_key(synthetic_op()).name.startswith("gemm-")


@pytest.mark.parametrize("canonical", ["{}", bytearray(b"{}"), None, {"a": 1}])
def test_directory_name_needs_bytes(canonical):
    with pytest.raises(TypeError, match="canonical must be bytes"):
        directory_name("gemm", canonical)


@pytest.mark.parametrize(
    "value", [1.0, 0.5, float("nan"), None, True, False, [1], (1,), {1, 2}, b"s"]
)
def test_canonical_form_rejects_values_outside_the_value_set(value):
    with pytest.raises(
        InvalidRecordError, match="^v: must be a string, an integer or a map"
    ):
        canonical_form({"v": value})
    with pytest.raises(
        InvalidRecordError, match="^a.v: must be a string, an integer or a map"
    ):
        canonical_form({"a": {"v": value}})


class Shouting(str):
    def __str__(self):
        return "../SHOUT"

    def __format__(self, spec):
        return "../SHOUT"


class StrKind(str, enum.Enum):
    GEMM = "gemm"


class IntSize(enum.IntEnum):
    ONE = 1


@pytest.mark.parametrize("value", [Shouting("gemm"), StrKind.GEMM])
def test_str_subclasses_are_rejected(value):
    with pytest.raises(InvalidRecordError, match="^prefix: must be a name"):
        directory_name(value, b"{}")
    with pytest.raises(InvalidRecordError, match="^accelerator: must be a name"):
        hw_profile_key(changed(synthetic_hw(), ["accelerator"], value))
    with pytest.raises(InvalidRecordError, match="^revision: must be a string"):
        hw_profile_key(changed(synthetic_hw(), ["revision"], value))
    with pytest.raises(InvalidRecordError, match="^host.cpu: must be a string or"):
        hw_profile_key(changed(synthetic_hw(), ["host", "cpu"], value))
    with pytest.raises(InvalidRecordError, match="^host: member name: must be a name"):
        hw_profile_key(changed(synthetic_hw(), ["host", value], "synthetic"))
    for field in ("kind", "dtype", "layout"):
        with pytest.raises(InvalidRecordError, match=f"^{field}: must be a name"):
            op_signature_key(changed(synthetic_op(), [field], value))
    with pytest.raises(InvalidRecordError, match="^v: must be a string, an integer"):
        canonical_form({"v": value})
    with pytest.raises(InvalidRecordError, match="^record: member name: must be"):
        canonical_form({value: 1})


def test_str_subclass_as_hw_source_is_rejected():
    class Source(str):
        pass

    with pytest.raises(InvalidRecordError, match="^hw_source: must be external or"):
        hw_profile_key(changed(synthetic_hw(), ["hw_source"], Source("external")))


def test_int_subclasses_are_rejected():
    with pytest.raises(InvalidRecordError, match="^shape.m: must be an integer"):
        op_signature_key(changed(synthetic_op(), ["shape", "m"], IntSize.ONE))
    with pytest.raises(InvalidRecordError, match="^host.v: must be a string or"):
        hw_profile_key(changed(synthetic_hw(), ["host", "v"], IntSize.ONE))
    with pytest.raises(InvalidRecordError, match="^schema_version: must be the int"):
        op_signature_key(changed(synthetic_op(), ["schema_version"], IntSize.ONE))
    with pytest.raises(InvalidRecordError, match="^v: must be a string, an integer"):
        canonical_form({"v": IntSize.ONE})


def test_maps_nested_too_deeply_are_rejected():
    itself = {}
    itself["a"] = itself
    with pytest.raises(InvalidRecordError, match="^record: maps are nested too deep"):
        canonical_form(itself)
    deep = {"v": 1}
    for _ in range(100_000):
        deep = {"a": deep}
    with pytest.raises(InvalidRecordError, match="^record: maps are nested too deep"):
        canonical_form(deep)


def test_directory_name_rejects_a_bytes_subclass():
    class Other(bytes):
        pass

    with pytest.raises(TypeError, match="canonical must be bytes, not Other"):
        directory_name("gemm", Other(b"{}"))


def test_error_message_stays_short_for_large_and_deep_values():
    with pytest.raises(InvalidRecordError) as error:
        hw_profile_key(changed(synthetic_hw(), ["revision"], "s" * 1_000_000))
    assert str(error.value).startswith("revision: must be a string of 1 to 255")
    assert len(str(error.value)) < 200
    deep = []
    for _ in range(100_000):
        deep = [deep]
    for function, record, path in (
        (hw_profile_key, changed(synthetic_hw(), ["revision"], deep), "revision"),
        (hw_profile_key, changed(synthetic_hw(), ["host"], deep), "host"),
        (hw_profile_key, changed(synthetic_hw(), ["hw_source"], deep), "hw_source"),
        (op_signature_key, changed(synthetic_op(), ["shape"], deep), "shape"),
        (op_signature_key, changed(synthetic_op(), ["layout"], deep), "layout"),
        (canonical_form, {"v": deep}, "v"),
        (canonical_form, deep, "record"),
    ):
        with pytest.raises(InvalidRecordError) as error:
            function(record)
        assert str(error.value).startswith(f"{path}: must be ")
        assert len(str(error.value)) < 200
    with pytest.raises(InvalidRecordError, match="^prefix: must be a name") as error:
        directory_name(deep, b"{}")
    assert len(str(error.value)) < 200
    with pytest.raises(InvalidRecordError, match="unknown field") as error:
        op_signature_key(changed(synthetic_op(), ["f" * 1_000_000], 1))
    assert len(str(error.value)) < 200


@pytest.mark.parametrize(
    "path",
    [
        ["toolchain", "synthetic_rt"],
        ["host", "synthetic_memory"],
        ["ext", "b"],
        ["ext"],
    ],
)
def test_removing_a_hw_key_field_member_gives_another_name(path):
    record = synthetic_hw()
    record["toolchain"]["synthetic_rt"] = "1"
    record["host"]["synthetic_memory"] = 16
    record["ext"] = {"a": 1, "b": 2}
    assert (
        hw_profile_key(changed(record, path, REMOVE)).name
        != hw_profile_key(record).name
    )


@pytest.mark.parametrize("path", [["ext", "b"], ["ext"]])
def test_removing_an_op_key_field_member_gives_another_name(path):
    record = changed(synthetic_op(), ["ext"], {"a": 1, "b": 2})
    other = op_signature_key(changed(record, path, REMOVE))
    assert other.name != op_signature_key(record).name


def test_str_subclass_as_field_name_is_rejected():
    for function, record in (
        (hw_profile_key, synthetic_hw()),
        (op_signature_key, synthetic_op()),
    ):
        value = record.pop("schema_version")
        record[Shouting("schema_version")] = value
        with pytest.raises(InvalidRecordError, match="unknown field"):
            function(record)
