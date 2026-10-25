import ast
import inspect
import re
from pathlib import Path

import pytest

from hilclaw import (
    build_log,
    check_failure,
    journaled_step,
    run_admission,
    run_failure,
    run_objective,
    run_operation,
    run_result,
    run_seed,
    tools,
)
from hilclaw.run_failure import (
    BACKEND_KINDS,
    KIND_BUILD_DIRECTORY_UNUSABLE,
    KIND_BUILD_INPUT_MISSING,
    KIND_BUILD_OUTPUT_MISSING,
    KIND_COMPILER_UNAVAILABLE,
    KIND_EXECUTABLE_UNSTARTABLE,
    KIND_KERNEL_SOURCE_UNREADABLE,
    KIND_NO_KERNEL_SOURCE,
    KIND_OPERATION_FAILURE_INVALID,
    KIND_SETTINGS_REFUSED,
    ended_with,
)

MARKER = "zq7-marker-zq7"
MESSAGE_LIMIT = 200
# Stand-ins of this file: no record gives either name a meaning.
EXAMPLE_KIND = "example_kind"
EXAMPLE_BACKEND_KIND = "example_backend_kind"
# The eight names as ADR-0068 decision 3 spells them, in the order of the rows.
THE_EIGHT = [
    "no_kernel_source",
    "kernel_source_unreadable",
    "build_directory_unusable",
    "settings_refused",
    "build_input_missing",
    "compiler_unavailable",
    "build_output_missing",
    "executable_unstartable",
]
# The kinds of the run tools' contract that are no backend kind (ADR-0068 decisions 3 and 4).
OTHER_KINDS_OF_THE_CONTRACT = [
    "seed_not_drawn",
    "objective_not_stated",
    "objective_not_covered",
    "op_signature_not_stated",
    "op_signature_not_covered",
    "n_max_not_stated",
    "operation_answer_invalid",
    "build_log_unwritable",
    "operation_failure_invalid",
]
NOT_RESERVED = [
    EXAMPLE_KIND,
    *OTHER_KINDS_OF_THE_CONTRACT,
    "draws_not_stated",
    "tolerance_not_stated",
    "blob_unreadable",
]
NEAR_MISSES = [
    "no_kernel_sources",
    "kernel_source_unreadable_",
    "settings_refuse",
    "build_output",
    "timing_build_input_missing",
    "no_timing_executable",
    "build_exit_status",
    "build_time_limit",
]


def failure(kind, message=MARKER):
    return tools.ToolFailure(kind, message)


def outside(raised):
    pair = ended_with(raised)
    assert type(pair) is tuple
    kind, message = pair
    assert type(kind) is str
    assert kind == "operation_failure_invalid"
    assert type(message) is str
    assert 0 < len(message) <= MESSAGE_LIMIT
    assert MARKER not in message
    return message


def imported_modules(path):
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


class Unprintable:
    payload = MARKER

    def __repr__(self):
        raise RuntimeError(MARKER)

    __str__ = __repr__
    __eq__ = __repr__
    __hash__ = __repr__
    __len__ = __repr__
    __bool__ = __repr__


class Text(str):
    pass


class ClosedKind(tools.ToolFailure):
    @property
    def kind(self):
        raise RuntimeError(MARKER)

    @kind.setter
    def kind(self, value):
        pass


class ClosedMessage(tools.ToolFailure):
    @property
    def message(self):
        raise RuntimeError(MARKER)

    @message.setter
    def message(self, value):
        pass


class InterruptedKind(tools.ToolFailure):
    @property
    def kind(self):
        raise KeyboardInterrupt

    @kind.setter
    def kind(self, value):
        pass


class CountedReads(tools.ToolFailure):
    reads = None

    def __getattribute__(self, name):
        reads = object.__getattribute__(self, "reads")
        if reads is not None:
            reads.append(name)
        return object.__getattribute__(self, name)


@pytest.mark.parametrize("kind", THE_EIGHT)
def test_each_of_the_eight_kinds_is_answered_as_it_was_raised(kind):
    raised = CountedReads(kind, MARKER)
    raised.reads = reads = []
    pair = ended_with(raised)
    assert reads == ["kind", "message"]
    raised.reads = None
    assert pair == (kind, MARKER)
    assert type(pair) is tuple
    assert type(pair[0]) is str
    assert type(pair[1]) is str
    assert ended_with(raised) == pair
    assert (raised.kind, raised.message, raised.args) == (kind, MARKER, pair)
    assert raised.__cause__ is None
    assert raised.__context__ is None
    assert tools.ToolFailure(*pair).error_object() == {
        "error": {"kind": kind, "message": MARKER}
    }
    failed = journaled_step.StepFailed({}, *pair)
    assert (failed.kind, failed.message) == pair


@pytest.mark.parametrize("kind", THE_EIGHT)
@pytest.mark.parametrize(
    "message",
    ["", "one line\nand another\r\n", "x" * 10_000, "the driver program"],
    ids=["empty", "newlines", "long", "driver"],
)
def test_the_message_of_a_backend_kind_is_not_checked(kind, message):
    assert ended_with(failure(kind, message)) == (kind, message)


@pytest.mark.parametrize("kind", THE_EIGHT)
def test_an_instance_of_a_subclass_with_one_of_the_eight_kinds_is_answered_alike(kind):
    class Narrower(tools.ToolFailure):
        pass

    assert ended_with(Narrower(kind, MARKER)) == (kind, MARKER)


def test_a_kind_no_record_names_is_answered_with_the_tools_own_kind():
    message = outside(failure(EXAMPLE_KIND))
    assert EXAMPLE_KIND not in message
    built = tools.ToolFailure(KIND_OPERATION_FAILURE_INVALID, message)
    assert built.error_object() == {
        "error": {"kind": "operation_failure_invalid", "message": message}
    }
    failed = journaled_step.StepFailed({}, *ended_with(failure(EXAMPLE_KIND)))
    assert (failed.kind, failed.message) == (KIND_OPERATION_FAILURE_INVALID, message)


@pytest.mark.parametrize("kind", OTHER_KINDS_OF_THE_CONTRACT)
def test_another_kind_of_the_run_tools_contract_is_outside_and_not_shown(kind):
    raised = CountedReads(kind, MARKER)
    raised.reads = reads = []
    message = outside(raised)
    assert reads == ["kind"]
    assert kind not in message
    assert message == outside(failure(EXAMPLE_KIND))


@pytest.mark.parametrize("reserved", sorted(tools.RESERVED_KINDS))
def test_a_reserved_kind_is_never_the_kind_of_the_pair(reserved):
    message = outside(failure(reserved))
    assert reserved in message
    assert message != outside(failure(EXAMPLE_KIND))
    others = tools.RESERVED_KINDS - {reserved}
    assert not [other for other in others if other in message]
    assert not [member for member in BACKEND_KINDS if member in message]


def test_each_reserved_kind_has_a_message_of_its_own():
    messages = {outside(failure(reserved)) for reserved in tools.RESERVED_KINDS}
    assert len(messages) == len(tools.RESERVED_KINDS)


@pytest.mark.parametrize("kind", [*NOT_RESERVED, *NEAR_MISSES])
def test_a_kind_that_is_not_reserved_is_not_shown(kind):
    message = outside(failure(kind))
    assert kind not in message
    assert message == outside(failure(EXAMPLE_KIND))
    assert not [reserved for reserved in tools.RESERVED_KINDS if reserved in message]
    assert not [member for member in BACKEND_KINDS if member in message]


def test_an_instance_of_a_subclass_outside_the_contract_is_answered_the_same():
    class Narrower(tools.ToolFailure):
        pass

    assert ended_with(Narrower(EXAMPLE_KIND, MARKER)) == ended_with(
        failure(EXAMPLE_KIND)
    )
    assert ended_with(Narrower(tools.KIND_STEP_OPEN, MARKER)) == ended_with(
        failure(tools.KIND_STEP_OPEN)
    )


@pytest.mark.parametrize("kind", [EXAMPLE_KIND, tools.KIND_STEP_OPEN, *THE_EIGHT])
def test_two_calls_answer_alike_and_leave_the_raised_object_as_it_was(kind):
    raised = failure(kind)
    before = (raised.kind, raised.message, raised.args, dict(vars(raised)))
    assert ended_with(raised) == ended_with(raised)
    assert (raised.kind, raised.message, raised.args, vars(raised)) == before
    assert raised.__cause__ is None
    assert raised.__context__ is None


@pytest.mark.parametrize(
    "raised",
    [
        None,
        ValueError(MARKER),
        journaled_step.StepFailed({}, EXAMPLE_KIND, MARKER),
        EXAMPLE_KIND,
        tools.ToolFailure,
        (EXAMPLE_KIND, MARKER),
        {"kind": EXAMPLE_KIND, "message": MARKER},
        Unprintable(),
    ],
    ids=[
        "none",
        "value-error",
        "step-failed",
        "str",
        "the-class",
        "tuple",
        "dict",
        "unprintable",
    ],
)
def test_what_is_no_tool_failure_is_refused(raised):
    with pytest.raises(TypeError) as caught:
        ended_with(raised)
    assert type(caught.value) is TypeError
    assert MARKER not in str(caught.value)


def test_a_missing_or_surplus_argument_is_refused():
    with pytest.raises(TypeError):
        ended_with()
    with pytest.raises(TypeError):
        ended_with(failure(EXAMPLE_KIND), failure(EXAMPLE_KIND))
    with pytest.raises(TypeError):
        ended_with(failure(EXAMPLE_KIND), spend={})


@pytest.mark.parametrize(
    "kind",
    [
        None,
        3,
        b"no_kernel_source",
        [tools.KIND_STEP_OPEN],
        Text(tools.KIND_STEP_OPEN),
        Text(EXAMPLE_KIND),
        Text(KIND_NO_KERNEL_SOURCE),
        Unprintable(),
    ],
    ids=[
        "none",
        "int",
        "bytes",
        "list",
        "str-subclass-reserved",
        "str-subclass-other",
        "str-subclass-backend",
        "unprintable",
    ],
)
def test_a_replaced_kind_is_answered_as_outside_and_not_shown(kind):
    raised = failure(KIND_NO_KERNEL_SOURCE)
    raised.kind = kind
    message = outside(raised)
    assert not [reserved for reserved in tools.RESERVED_KINDS if reserved in message]
    assert not [member for member in BACKEND_KINDS if member in message]
    assert message != outside(failure(EXAMPLE_KIND))
    assert raised.kind is kind
    assert raised.message == MARKER


@pytest.mark.parametrize("kind", THE_EIGHT)
@pytest.mark.parametrize(
    "message",
    [None, 3, b"x", [MARKER], Text(MARKER), Unprintable()],
    ids=["none", "int", "bytes", "list", "str-subclass", "unprintable"],
)
def test_one_of_the_eight_kinds_with_a_replaced_message_is_answered_as_outside(
    kind, message
):
    raised = failure(kind)
    raised.message = message
    text = outside(raised)
    assert not [member for member in BACKEND_KINDS if member in text]
    assert text != outside(failure(EXAMPLE_KIND))
    assert raised.message is message
    assert text == outside(ClosedMessage(kind, MARKER))


def test_a_replaced_message_is_not_read_for_a_kind_outside_the_contract():
    raised = failure(EXAMPLE_KIND)
    raised.message = Unprintable()
    assert outside(raised) == outside(failure(EXAMPLE_KIND))
    assert outside(ClosedMessage(tools.KIND_STEP_OPEN, MARKER)) == outside(
        failure(tools.KIND_STEP_OPEN)
    )


@pytest.mark.parametrize("kind", [EXAMPLE_KIND, KIND_NO_KERNEL_SOURCE])
def test_a_kind_that_cannot_be_read_is_answered_as_outside(kind):
    message = outside(ClosedKind(kind, MARKER))
    assert kind not in message
    assert message != outside(failure(EXAMPLE_KIND))
    replaced = failure(kind)
    replaced.kind = None
    assert message == outside(replaced)


@pytest.mark.parametrize("kind", [EXAMPLE_KIND, KIND_SETTINGS_REFUSED])
def test_an_interrupt_out_of_a_read_is_not_caught(kind):
    with pytest.raises(KeyboardInterrupt):
        ended_with(InterruptedKind(kind, MARKER))


def test_a_backend_kind_is_read_from_the_modules_own_set(monkeypatch):
    monkeypatch.setattr(run_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND}))
    assert ended_with(failure(EXAMPLE_BACKEND_KIND)) == (EXAMPLE_BACKEND_KIND, MARKER)
    assert outside(failure(KIND_NO_KERNEL_SOURCE)) == outside(failure(EXAMPLE_KIND))
    assert check_failure.BACKEND_KINDS == frozenset(THE_EIGHT)


def test_the_backend_kinds_as_shipped_are_the_eight_of_adr_0068_decision_3():
    assert type(BACKEND_KINDS) is frozenset
    assert BACKEND_KINDS == frozenset(THE_EIGHT)
    assert len(BACKEND_KINDS) == 8
    assert [
        KIND_NO_KERNEL_SOURCE,
        KIND_KERNEL_SOURCE_UNREADABLE,
        KIND_BUILD_DIRECTORY_UNUSABLE,
        KIND_SETTINGS_REFUSED,
        KIND_BUILD_INPUT_MISSING,
        KIND_COMPILER_UNAVAILABLE,
        KIND_BUILD_OUTPUT_MISSING,
        KIND_EXECUTABLE_UNSTARTABLE,
    ] == THE_EIGHT
    assert BACKEND_KINDS == check_failure.BACKEND_KINDS
    assert BACKEND_KINDS is not check_failure.BACKEND_KINDS
    with pytest.raises(AttributeError):
        BACKEND_KINDS.add(EXAMPLE_KIND)


@pytest.mark.parametrize("kind", THE_EIGHT)
def test_each_backend_kind_is_a_name_a_tool_failure_takes(kind):
    (member,) = BACKEND_KINDS & {kind}
    assert type(member) is str
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", member)
    assert tools.ToolFailure(member, "x").kind == kind


def test_no_reserved_kind_and_no_other_kind_of_the_run_tools_is_a_backend_kind():
    assert not BACKEND_KINDS & tools.RESERVED_KINDS
    assert set(OTHER_KINDS_OF_THE_CONTRACT) == {
        KIND_OPERATION_FAILURE_INVALID,
        run_operation.KIND_OPERATION_ANSWER_INVALID,
        run_seed.KIND_SEED_NOT_DRAWN,
        build_log.KIND_BUILD_LOG_UNWRITABLE,
        *run_admission.KINDS,
        *run_objective.KINDS,
    }
    assert not BACKEND_KINDS & set(OTHER_KINDS_OF_THE_CONTRACT)
    assert not BACKEND_KINDS & set(run_result.CONDITIONS)
    assert not BACKEND_KINDS & {EXAMPLE_KIND, EXAMPLE_BACKEND_KIND, *NEAR_MISSES}


def test_the_kind_is_that_of_correctness_check_and_not_reserved():
    assert KIND_OPERATION_FAILURE_INVALID == "operation_failure_invalid"
    assert (
        KIND_OPERATION_FAILURE_INVALID == check_failure.KIND_OPERATION_FAILURE_INVALID
    )
    assert type(KIND_OPERATION_FAILURE_INVALID) is str
    assert KIND_OPERATION_FAILURE_INVALID not in tools.RESERVED_KINDS
    assert KIND_OPERATION_FAILURE_INVALID not in BACKEND_KINDS
    tools.ToolFailure(KIND_OPERATION_FAILURE_INVALID, "x")


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside(failure(EXAMPLE_KIND))
    outside(failure(tools.KIND_STEP_OPEN))
    outside(ClosedKind(EXAMPLE_KIND, MARKER))
    for kind in THE_EIGHT:
        assert ended_with(failure(kind)) == (kind, MARKER)
        outside(ClosedMessage(kind, MARKER))
    with pytest.raises(TypeError):
        ended_with(None)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_check_failure_and_the_tools_only_and_has_no_entry():
    own = Path(run_failure.__file__)
    assert imported_modules(own) == {
        "hilclaw",
        "hilclaw.check_failure",
        "hilclaw.tools",
    }
    assert not hasattr(run_failure, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(run_failure).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "KIND_OPERATION_FAILURE_INVALID",
        "KIND_NO_KERNEL_SOURCE",
        "KIND_KERNEL_SOURCE_UNREADABLE",
        "KIND_BUILD_DIRECTORY_UNUSABLE",
        "KIND_SETTINGS_REFUSED",
        "KIND_BUILD_INPUT_MISSING",
        "KIND_COMPILER_UNAVAILABLE",
        "KIND_BUILD_OUTPUT_MISSING",
        "KIND_EXECUTABLE_UNSTARTABLE",
        "BACKEND_KINDS",
        "ended_with",
    }
    parameters = list(inspect.signature(ended_with).parameters.values())
    assert [parameter.name for parameter in parameters] == ["raised"]
    assert parameters[0].default is inspect.Parameter.empty
