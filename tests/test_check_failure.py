import ast
import inspect
import io
import re
import tokenize
from pathlib import Path

import pytest

from hilclaw import (
    check_admission,
    check_failure,
    check_operation,
    check_seed,
    journaled_step,
    tools,
)
from hilclaw.check_failure import (
    BACKEND_KINDS,
    KIND_KERNEL_SOURCE_UNREADABLE,
    KIND_NO_KERNEL_SOURCE,
    KIND_OPERATION_FAILURE_INVALID,
    ended_with,
)

MARKER = "zq7-marker-zq7"
MESSAGE_LIMIT = 200
# Stand-ins of this file: no record gives either name a meaning.
EXAMPLE_KIND = "example_kind"
EXAMPLE_BACKEND_KIND = "example_backend_kind"
# The two names as ADR-0056 decision 6 spells them.
THE_TWO = ["no_kernel_source", "kernel_source_unreadable"]
OTHER_KINDS_OF_THE_CONTRACT = [
    "operation_failure_invalid",
    "operation_answer_invalid",
    "seed_not_drawn",
    "op_signature_not_stated",
    "op_signature_not_covered",
    "draws_not_stated",
    "tolerance_not_stated",
]
NOT_RESERVED = [EXAMPLE_KIND, *OTHER_KINDS_OF_THE_CONTRACT, "blob_unreadable"]
NEAR_MISSES = [
    "no_kernel_sources",
    "no_kernel_sourc",
    "no_kernel_source_",
    "kernel_source_unreadabl",
    "kernel_source_unreadable_",
    "kernel_source",
    "no_kernel_source_unreadable",
]
# No name: a tool failure cannot be built with one, so the kind is replaced afterwards.
NO_NAMES = [
    "No_kernel_source",
    "NO_KERNEL_SOURCE",
    " no_kernel_source",
    "no_kernel_source\n",
    "no-kernel-source",
    "kernel_source_unreadable ",
    "Kernel_source_unreadable",
    "",
]
UNCHECKED_MESSAGES = [
    "nothing lies at /home/someone/data/runs/r1/rounds/0/candidates/1/attempts/1/output",
    "C:\\Users\\someone\\data\\runs\\r1 could not be listed",
    "one line\nand another\r\n",
    "x" * 10_000,
    "",
    "seed 7; stderr: Segmentation fault",
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


class EndingKind(tools.ToolFailure):
    @property
    def kind(self):
        raise SystemExit(3)

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


def test_a_kind_no_record_names_is_answered_with_the_tools_own_kind():
    message = outside(failure(EXAMPLE_KIND))
    assert EXAMPLE_KIND not in message
    assert ended_with(failure(EXAMPLE_KIND)) == (
        KIND_OPERATION_FAILURE_INVALID,
        message,
    )


def test_a_tool_failure_and_a_failed_step_can_be_built_from_the_pair():
    pair = ended_with(failure(EXAMPLE_KIND))
    built = tools.ToolFailure(*pair)
    assert built.error_object() == {
        "error": {"kind": "operation_failure_invalid", "message": pair[1]}
    }
    # The empty spend is this test's example, no rule.
    failed = journaled_step.StepFailed({}, *pair)
    assert (failed.kind, failed.message) == pair


@pytest.mark.parametrize("reserved", sorted(tools.RESERVED_KINDS))
def test_a_reserved_kind_is_never_the_kind_of_the_pair(reserved):
    message = outside(failure(reserved))
    assert reserved in message
    assert message != outside(failure(EXAMPLE_KIND))
    others = tools.RESERVED_KINDS - {reserved}
    assert not [other for other in others if other in message]


def test_the_thirteen_reserved_kinds_have_thirteen_messages():
    messages = {outside(failure(reserved)) for reserved in tools.RESERVED_KINDS}
    assert len(tools.RESERVED_KINDS) == 13
    assert len(messages) == 13


@pytest.mark.parametrize("kind", NOT_RESERVED)
def test_a_kind_that_is_not_reserved_is_not_shown(kind):
    message = outside(failure(kind))
    assert kind not in message
    assert message == outside(failure(EXAMPLE_KIND))
    assert not [reserved for reserved in tools.RESERVED_KINDS if reserved in message]


def test_an_instance_of_a_subclass_is_answered_the_same():
    class Narrower(tools.ToolFailure):
        pass

    assert ended_with(Narrower(EXAMPLE_KIND, MARKER)) == ended_with(
        failure(EXAMPLE_KIND)
    )
    assert ended_with(Narrower(tools.KIND_STEP_OPEN, MARKER)) == ended_with(
        failure(tools.KIND_STEP_OPEN)
    )


@pytest.mark.parametrize("kind", [EXAMPLE_KIND, tools.KIND_STEP_OPEN])
def test_two_calls_answer_alike_and_leave_the_raised_object_as_it_was(kind):
    raised = failure(kind)
    before = (raised.kind, raised.message, raised.args, dict(vars(raised)))
    assert ended_with(raised) == ended_with(raised)
    assert (raised.kind, raised.message, raised.args, vars(raised)) == before
    assert raised.__cause__ is None
    assert raised.__context__ is None


def test_the_kind_is_read_once_and_the_message_not_at_all():
    raised = CountedReads(EXAMPLE_KIND, MARKER)
    raised.reads = reads = []
    outside(raised)
    assert reads == ["kind"]


def test_the_backend_kinds_as_shipped_are_the_two_of_adr_0056():
    assert type(BACKEND_KINDS) is frozenset
    assert BACKEND_KINDS == frozenset(THE_TWO)
    assert len(BACKEND_KINDS) == 2
    assert check_failure.BACKEND_KINDS is BACKEND_KINDS
    assert KIND_NO_KERNEL_SOURCE == "no_kernel_source"
    assert KIND_KERNEL_SOURCE_UNREADABLE == "kernel_source_unreadable"
    assert (len(KIND_NO_KERNEL_SOURCE), len(KIND_KERNEL_SOURCE_UNREADABLE)) == (16, 24)
    with pytest.raises(AttributeError):
        BACKEND_KINDS.add(EXAMPLE_KIND)


@pytest.mark.parametrize("kind", THE_TWO)
def test_each_backend_kind_is_a_name_a_tool_failure_takes(kind):
    assert kind in BACKEND_KINDS
    (member,) = BACKEND_KINDS & {kind}
    assert type(member) is str
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", member)
    assert tools.ToolFailure(member, "x").kind == kind


def test_no_other_kind_of_the_contract_and_no_reserved_kind_is_a_backend_kind():
    assert not BACKEND_KINDS & tools.RESERVED_KINDS
    assert KIND_OPERATION_FAILURE_INVALID not in BACKEND_KINDS
    assert set(OTHER_KINDS_OF_THE_CONTRACT) == {
        KIND_OPERATION_FAILURE_INVALID,
        check_operation.KIND_OPERATION_ANSWER_INVALID,
        check_seed.KIND_SEED_NOT_DRAWN,
        *check_admission.KINDS,
    }
    assert not BACKEND_KINDS & set(OTHER_KINDS_OF_THE_CONTRACT)
    assert not BACKEND_KINDS & {EXAMPLE_KIND, EXAMPLE_BACKEND_KIND, *NEAR_MISSES}


@pytest.mark.parametrize("kind", THE_TWO)
def test_each_of_the_two_kinds_is_answered_as_it_was_raised(kind):
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


@pytest.mark.parametrize("kind", THE_TWO)
@pytest.mark.parametrize(
    "message",
    UNCHECKED_MESSAGES,
    ids=["posix-path", "windows-path", "newlines", "long", "empty", "seed-and-stderr"],
)
def test_the_message_of_a_backend_kind_is_not_checked(kind, message):
    pair = ended_with(failure(kind, message))
    assert pair == (kind, message)
    assert type(pair[1]) is str
    assert len(pair[1]) == len(message)


@pytest.mark.parametrize("kind", THE_TWO)
@pytest.mark.parametrize(
    "message",
    [None, 3, b"x", [MARKER], Text(MARKER), Unprintable()],
    ids=["none", "int", "bytes", "list", "str-subclass", "unprintable"],
)
def test_one_of_the_two_kinds_with_a_replaced_message_is_answered_as_outside(
    kind, message
):
    raised = failure(kind)
    raised.message = message
    text = outside(raised)
    assert kind not in text
    assert not [member for member in BACKEND_KINDS if member in text]
    assert text != outside(failure(EXAMPLE_KIND))
    assert raised.message is message


@pytest.mark.parametrize("kind", THE_TWO)
def test_one_of_the_two_kinds_whose_message_cannot_be_read_is_answered_as_outside(
    kind,
):
    text = outside(ClosedMessage(kind, MARKER))
    assert kind not in text
    replaced = failure(kind)
    replaced.message = None
    assert text == outside(replaced)


@pytest.mark.parametrize("kind", NEAR_MISSES)
def test_a_name_near_one_of_the_two_is_outside(kind):
    raised = CountedReads(kind, MARKER)
    raised.reads = reads = []
    message = outside(raised)
    assert reads == ["kind"]
    assert message == outside(failure(EXAMPLE_KIND))
    assert not [member for member in BACKEND_KINDS if member in message]


@pytest.mark.parametrize("kind", NO_NAMES)
def test_a_replaced_kind_that_is_no_name_is_outside(kind):
    with pytest.raises(ValueError):
        failure(kind)
    raised = failure(KIND_NO_KERNEL_SOURCE)
    raised.kind = kind
    assert outside(raised) == outside(failure(EXAMPLE_KIND))


@pytest.mark.parametrize("kind", THE_TWO)
def test_a_str_subclass_equal_to_one_of_the_two_is_outside(kind):
    assert Text(kind) in BACKEND_KINDS
    raised = failure(kind)
    raised.kind = Text(kind)
    message = outside(raised)
    assert kind not in message
    assert message != outside(failure(EXAMPLE_KIND))
    closed = ClosedMessage(kind, MARKER)
    closed.kind = Text(kind)
    assert outside(closed) == message


@pytest.mark.parametrize("kind", THE_TWO)
def test_an_instance_of_a_subclass_with_one_of_the_two_kinds_is_answered_alike(kind):
    class Narrower(tools.ToolFailure):
        pass

    assert ended_with(Narrower(kind, MARKER)) == (kind, MARKER)


def test_a_kind_that_cannot_be_read_is_outside_beside_the_two():
    message = outside(ClosedKind(KIND_NO_KERNEL_SOURCE, MARKER))
    assert message == outside(ClosedKind(EXAMPLE_KIND, MARKER))
    with pytest.raises(SystemExit):
        ended_with(EndingKind(KIND_KERNEL_SOURCE_UNREADABLE, MARKER))


def test_a_backend_kind_is_answered_as_it_was_raised(monkeypatch):
    monkeypatch.setattr(
        check_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND})
    )
    raised = failure(EXAMPLE_BACKEND_KIND)
    pair = ended_with(raised)
    assert pair == (EXAMPLE_BACKEND_KIND, MARKER)
    assert type(pair) is tuple
    assert type(pair[0]) is str
    assert type(pair[1]) is str
    assert ended_with(raised) == pair
    assert (raised.kind, raised.message) == pair
    tools.ToolFailure(*pair)
    journaled_step.StepFailed({}, *pair)


def test_another_kind_beside_a_backend_kind_is_still_outside(monkeypatch):
    monkeypatch.setattr(
        check_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND})
    )
    message = outside(failure(EXAMPLE_KIND))
    assert EXAMPLE_KIND not in message
    assert tools.KIND_STEP_OPEN in outside(failure(tools.KIND_STEP_OPEN))
    assert outside(failure("operation_failure_invalid")) == message


def test_the_message_of_a_backend_kind_is_read_once(monkeypatch):
    monkeypatch.setattr(
        check_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND})
    )
    raised = CountedReads(EXAMPLE_BACKEND_KIND, MARKER)
    raised.reads = reads = []
    assert ended_with(raised) == (EXAMPLE_BACKEND_KIND, MARKER)
    assert reads == ["kind", "message"]


@pytest.mark.parametrize(
    "message",
    [None, 3, b"x", [MARKER], Text(MARKER), Unprintable()],
    ids=["none", "int", "bytes", "list", "str-subclass", "unprintable"],
)
def test_a_backend_kind_with_a_replaced_message_is_answered_as_outside(
    monkeypatch, message
):
    monkeypatch.setattr(
        check_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND})
    )
    raised = failure(EXAMPLE_BACKEND_KIND)
    raised.message = message
    text = outside(raised)
    assert EXAMPLE_BACKEND_KIND not in text
    assert raised.message is message


def test_a_backend_kind_whose_message_cannot_be_read_is_answered_as_outside(
    monkeypatch,
):
    monkeypatch.setattr(
        check_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND})
    )
    text = outside(ClosedMessage(EXAMPLE_BACKEND_KIND, MARKER))
    assert EXAMPLE_BACKEND_KIND not in text


@pytest.mark.parametrize(
    "raised",
    [
        None,
        ValueError(MARKER),
        journaled_step.StepFailed({}, EXAMPLE_KIND, MARKER),
        check_operation.OperationAnswerInvalid(MARKER),
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
        "answer-invalid",
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
        b"step_open",
        [tools.KIND_STEP_OPEN],
        (EXAMPLE_KIND,),
        Text(tools.KIND_STEP_OPEN),
        Text(EXAMPLE_KIND),
        Unprintable(),
    ],
    ids=[
        "none",
        "int",
        "bytes",
        "list",
        "tuple",
        "str-subclass-reserved",
        "str-subclass-other",
        "unprintable",
    ],
)
def test_a_replaced_kind_is_answered_as_outside_and_not_shown(kind):
    raised = failure(EXAMPLE_KIND)
    raised.kind = kind
    message = outside(raised)
    assert EXAMPLE_KIND not in message
    assert not [reserved for reserved in tools.RESERVED_KINDS if reserved in message]
    assert message != outside(failure(EXAMPLE_KIND))
    assert raised.kind is kind


def test_a_replaced_kind_is_answered_alike_beside_a_backend_kind(monkeypatch):
    monkeypatch.setattr(
        check_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND})
    )
    raised = failure(EXAMPLE_BACKEND_KIND)
    raised.kind = Text(EXAMPLE_BACKEND_KIND)
    assert EXAMPLE_BACKEND_KIND not in outside(raised)
    raised.kind = Unprintable()
    outside(raised)


def test_a_replaced_message_is_not_read_for_a_kind_outside_the_contract():
    raised = failure(EXAMPLE_KIND)
    raised.message = Unprintable()
    assert outside(raised) == outside(failure(EXAMPLE_KIND))
    assert outside(ClosedMessage(tools.KIND_STEP_OPEN, MARKER)) == outside(
        failure(tools.KIND_STEP_OPEN)
    )


def test_a_kind_that_cannot_be_read_is_answered_as_outside():
    message = outside(ClosedKind(EXAMPLE_KIND, MARKER))
    assert EXAMPLE_KIND not in message
    assert message != outside(failure(EXAMPLE_KIND))


def test_a_request_to_end_out_of_a_read_is_not_caught():
    with pytest.raises(SystemExit):
        ended_with(EndingKind(EXAMPLE_KIND, MARKER))


def test_the_kind_is_a_name_and_not_reserved():
    assert KIND_OPERATION_FAILURE_INVALID == "operation_failure_invalid"
    assert type(KIND_OPERATION_FAILURE_INVALID) is str
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", KIND_OPERATION_FAILURE_INVALID)
    assert KIND_OPERATION_FAILURE_INVALID not in tools.RESERVED_KINDS
    assert (
        KIND_OPERATION_FAILURE_INVALID != check_operation.KIND_OPERATION_ANSWER_INVALID
    )
    tools.ToolFailure(KIND_OPERATION_FAILURE_INVALID, "x")


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside(failure(EXAMPLE_KIND))
    outside(failure(tools.KIND_STEP_OPEN))
    outside(ClosedKind(EXAMPLE_KIND, MARKER))
    tampered = failure(EXAMPLE_KIND)
    tampered.kind = None
    outside(tampered)
    with pytest.raises(TypeError):
        ended_with(None)
    for kind in THE_TWO:
        assert ended_with(failure(kind)) == (kind, MARKER)
        outside(ClosedMessage(kind, MARKER))
    monkeypatch.setattr(
        check_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND})
    )
    ended_with(failure(EXAMPLE_BACKEND_KIND))
    outside(ClosedMessage(EXAMPLE_BACKEND_KIND, MARKER))
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_tools_only_and_has_no_entry():
    own = Path(check_failure.__file__)
    assert imported_modules(own) == {"hilclaw", "hilclaw.tools"}
    assert not hasattr(check_failure, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_the_text_and_the_code_hold_none_of_the_kept_out_strings():
    own = Path(check_failure.__file__)
    text = own.read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "standin_profile" not in text
    code = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type in (tokenize.NAME, tokenize.STRING)
        and not token.string.startswith('"""')
    ]
    for kept_out in (
        "point",
        "sim",
        "board",
        "correctness_check_sim",
        "correctness_check_board",
        "tolerance_not_stated",
        "operation_answer_invalid",
    ):
        assert not [string for string in code if kept_out in string], kept_out
    spelt = [string for string in code if "operation_failure_invalid" in string]
    assert spelt == ['"operation_failure_invalid"']
    for kind in THE_TWO:
        assert [string for string in code if kind in string] == [f'"{kind}"']
    assert not [name for name in imported_modules(own) if "kernel_source" in name]


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(check_failure).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "KIND_OPERATION_FAILURE_INVALID",
        "KIND_NO_KERNEL_SOURCE",
        "KIND_KERNEL_SOURCE_UNREADABLE",
        "BACKEND_KINDS",
        "ended_with",
    }
    parameters = list(inspect.signature(ended_with).parameters.values())
    assert [parameter.name for parameter in parameters] == ["raised"]
    assert parameters[0].default is inspect.Parameter.empty
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
