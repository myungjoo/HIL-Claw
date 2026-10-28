from pathlib import Path

import pytest

from hilclaw import keys, layout
from hilclaw.layout import (
    ATTEMPT_ARTEFACTS,
    ATTEMPT_ROLES,
    BUILD_LOG_STEPS,
    LAYOUT_VERSION,
    OP_SIGNATURE_FILES,
    ROLES,
    RUN_FILES,
    InvalidPathValueError,
    attempt_artefact,
    attempt_dir,
    build_log_file,
    case_record,
    check_run_id,
    decision_log,
    hw_profile_dir,
    hw_profile_record,
    hypothesis_record,
    op_signature_dir,
    op_signature_file,
    role_dir,
    round_dir,
    run_dir,
    run_file,
    verdict_record,
)

# Synthetic values: no run, hardware or operation of a real instance.
ROOT = Path("synthetic-data-root")
RUN = "synthetic-run_01"
HW = "synthetic_accel-0123456789abcdef"
OP = "synthetic_kind-fedcba9876543210"
ADR_HW_NAME = "cpu_standin-b0d8610d8f470856"
ADR_OP_NAME = "gemm-c43e96fb16cc3f35"
HEX = "0123456789abcdef"

# Expected paths copied from ADR-0004 decisions 1 and 3 (round 7, candidate 3, attempt 2).
ATTEMPT = "runs/synthetic-run_01/rounds/0007/{}/candidates/03/attempts/02/{}"
ADR_RUN_FILES = {
    "STATE.json": "runs/synthetic-run_01/STATE.json",
    "instance.json": "runs/synthetic-run_01/instance.json",
    "events.ndjson": "runs/synthetic-run_01/events.ndjson",
    "artifacts.json": "runs/synthetic-run_01/artifacts.json",
}
ADR_ATTEMPT_ARTEFACTS = {
    "spec.json": ATTEMPT.format("coder", "spec.json"),
    "output": ATTEMPT.format("coder", "output"),
    "build.json": ATTEMPT.format("measure", "build.json"),
    "sim.json": ATTEMPT.format("measure", "sim.json"),
    "board.json": ATTEMPT.format("measure", "board.json"),
    "profile.json": ATTEMPT.format("measure", "profile.json"),
    "eval.json": ATTEMPT.format("eval", "eval.json"),
}
ADR_OP_FILES = {
    "op_signature.json": f"db/{HW}/{OP}/op_signature.json",
    "best.json": f"db/{HW}/{OP}/best.json",
    "technique_stats.json": f"db/{HW}/{OP}/technique_stats.json",
}


class StrSubclass(str):
    pass


class IntSubclass(int):
    pass


BAD_RUN_IDS = [
    "",
    "a" * 65,
    "NOT-DECIDED-HERE",
    "Synthetic",
    "_synthetic",
    "-synthetic",
    ".synthetic",
    "syn/thetic",
    "syn\\thetic",
    "syn.thetic",
    "syn:thetic",
    "syn thetic",
    ".",
    "..",
    "synthétic",
    "１run",
    "abc\n",
    None,
    b"abc",
    7,
    StrSubclass("abc"),
    Path("abc"),
]
BAD_ROUNDS = [-1, True, False, 1.0, "1", "0001", None, 2**53, IntSubclass(1)]
BAD_COUNTS = [0, -1, True, 1.0, "01", None, 2**53, IntSubclass(1)]
BAD_ROLES = ["", "builder", "Coder", "CODER", "coder/", "..", 1, None, ["coder"]]
BAD_KEY_NAMES = [
    "",
    "synthetic_accel",
    "synthetic_accel-",
    "synthetic_accel-" + HEX[:15],
    "synthetic_accel-" + HEX + "0",
    "synthetic_accel-" + HEX.upper(),
    "synthetic_accel-" + "g" * 16,
    "-" + HEX,
    "1accel-" + HEX,
    "a" * 33 + "-" + HEX,
    "Synthetic-" + HEX,
    "syn-thetic-" + HEX,
    "syn/thetic-" + HEX,
    "../accel-" + HEX,
    "..",
    HW + "\n",
    HW + "/..",
    "hw_profile.json",
    ".gitkeep",
    keys.Key(HW, "0" * 64, b"{}"),
    StrSubclass(HW),
    HW.encode(),
    None,
    7,
]


def rel(path, root=ROOT):
    return path.relative_to(root).as_posix()


def synthetic_hw_record():
    return {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev",
        "toolchain": {"synthetic_cc": "0.0"},
        "host": {"cpu": "synthetic-cpu", "os": "synthetic-os"},
        "hw_source": "in_house",
    }


def synthetic_op_record():
    return {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 2, "k": 3, "n": 5},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }


def every_path(root):
    paths = [run_dir(root, RUN), round_dir(root, RUN, 7), decision_log(root, RUN, 7)]
    paths.append(hypothesis_record(root, RUN, 7))
    paths.append(verdict_record(root, RUN, 7))
    paths += [run_file(root, RUN, name) for name in RUN_FILES]
    paths += [role_dir(root, RUN, 7, role) for role in ROLES]
    paths += [attempt_dir(root, RUN, 7, role, 3, 2) for role in ATTEMPT_ROLES]
    paths += [attempt_artefact(root, RUN, 7, 3, 2, name) for name in ATTEMPT_ARTEFACTS]
    paths += [build_log_file(root, RUN, 7, 3, 2, step, 1) for step in BUILD_LOG_STEPS]
    paths += [hw_profile_dir(root, HW), hw_profile_record(root, HW)]
    paths += [op_signature_dir(root, HW, OP)]
    paths += [op_signature_file(root, HW, OP, name) for name in OP_SIGNATURE_FILES]
    return paths


def test_layout_version_is_one():
    assert LAYOUT_VERSION == 1


def test_public_name_lists_match_the_adr():
    assert set(RUN_FILES) == set(ADR_RUN_FILES)
    assert set(ROLES) == {"decision", "coder", "measure", "eval"}
    assert set(ATTEMPT_ROLES) == {"coder", "measure", "eval"}
    assert set(ATTEMPT_ARTEFACTS) == set(ADR_ATTEMPT_ARTEFACTS)
    assert set(OP_SIGNATURE_FILES) == set(ADR_OP_FILES)


def test_run_dir():
    assert rel(run_dir(ROOT, RUN)) == "runs/synthetic-run_01"


@pytest.mark.parametrize(("name", "expected"), ADR_RUN_FILES.items())
def test_run_files(name, expected):
    assert rel(run_file(ROOT, RUN, name)) == expected


def test_round_dir():
    assert rel(round_dir(ROOT, RUN, 7)) == "runs/synthetic-run_01/rounds/0007"


@pytest.mark.parametrize("role", ["decision", "coder", "measure", "eval"])
def test_role_dir(role):
    expected = f"runs/synthetic-run_01/rounds/0007/{role}"
    assert rel(role_dir(ROOT, RUN, 7, role)) == expected


def test_decision_log_of_the_bring_up_round():
    expected = "runs/synthetic-run_01/rounds/0000/decision/decision.md"
    assert rel(decision_log(ROOT, RUN, 0)) == expected
    assert decision_log(ROOT, RUN, 0).parent == role_dir(ROOT, RUN, 0, "decision")


@pytest.mark.parametrize("number", [1, 7, 10000, keys.MAX_INTEGER])
def test_hypothesis_record_of_decision_1_of_adr_0059(number):
    expected = f"runs/synthetic-run_01/rounds/{number:04d}/decision/hypotheses.json"
    path = hypothesis_record(ROOT, RUN, number)
    assert rel(path) == expected
    assert path.parent == role_dir(ROOT, RUN, number, "decision")
    assert path.parent == decision_log(ROOT, RUN, number).parent


@pytest.mark.parametrize("number", [0, -1])
def test_round_zero_has_no_hypothesis_record(number):
    with pytest.raises(InvalidPathValueError, match=r"^round: must be an int from 1 "):
        hypothesis_record(ROOT, RUN, number)


@pytest.mark.parametrize("number", [1, 7, 10000, keys.MAX_INTEGER])
def test_verdict_record_of_decision_1_of_adr_0071(number):
    expected = f"runs/synthetic-run_01/rounds/{number:04d}/eval/verdicts.json"
    path = verdict_record(ROOT, RUN, number)
    assert rel(path) == expected
    assert path.parent == role_dir(ROOT, RUN, number, "eval")


@pytest.mark.parametrize("number", [0, -1])
def test_round_zero_has_no_verdict_record(number):
    with pytest.raises(InvalidPathValueError, match=r"^round: must be an int from 1 "):
        verdict_record(ROOT, RUN, number)


@pytest.mark.parametrize("role", ["coder", "measure", "eval"])
def test_attempt_dir(role):
    expected = f"runs/synthetic-run_01/rounds/0007/{role}/candidates/03/attempts/02"
    assert rel(attempt_dir(ROOT, RUN, 7, role, 3, 2)) == expected


def test_spec_path_of_decision_3():
    expected = (
        "runs/synthetic-run_01/rounds/0007/coder/candidates/03/attempts/02/spec.json"
    )
    assert rel(attempt_artefact(ROOT, RUN, 7, 3, 2, "spec.json")) == expected


@pytest.mark.parametrize(("name", "expected"), ADR_ATTEMPT_ARTEFACTS.items())
def test_attempt_artefacts(name, expected):
    assert rel(attempt_artefact(ROOT, RUN, 7, 3, 2, name)) == expected


def test_knowledge_tree():
    assert rel(hw_profile_dir(ROOT, HW)) == f"db/{HW}"
    assert rel(hw_profile_record(ROOT, HW)) == f"db/{HW}/hw_profile.json"
    assert rel(op_signature_dir(ROOT, HW, OP)) == f"db/{HW}/{OP}"


@pytest.mark.parametrize("number", [1, 7, 10000, keys.MAX_INTEGER])
def test_case_record_of_decision_1_of_adr_0072(number):
    expected = f"db/{HW}/{OP}/case-synthetic-run_01-{number:04d}.json"
    path = case_record(ROOT, HW, OP, RUN, number)
    assert rel(path) == expected
    assert path.parent == op_signature_dir(ROOT, HW, OP)
    assert path.name.endswith(f"-{hypothesis_record(ROOT, RUN, number).parts[-3]}.json")


def test_case_record_of_the_adr_0072_example():
    run_id = "20261009t012331z-9f3a6c1e0b7d4a52"
    expected = f"db/{ADR_HW_NAME}/{ADR_OP_NAME}/case-{run_id}-0001.json"
    assert rel(case_record(ROOT, ADR_HW_NAME, ADR_OP_NAME, run_id, 1)) == expected


@pytest.mark.parametrize("number", [0, -1, *BAD_ROUNDS])
def test_round_zero_has_no_case_record(number):
    with pytest.raises(InvalidPathValueError, match=r"^round: must be an int from 1 "):
        case_record(ROOT, HW, OP, RUN, number)


@pytest.mark.parametrize("run_id", BAD_RUN_IDS)
def test_invalid_run_id_of_a_case_record_is_rejected(run_id):
    with pytest.raises(InvalidPathValueError, match=r"^run_id: must be "):
        case_record(ROOT, HW, OP, run_id, 1)


@pytest.mark.parametrize("name", BAD_KEY_NAMES)
def test_invalid_key_name_of_a_case_record_is_rejected(name):
    with pytest.raises(InvalidPathValueError, match=r"^hw_profile_key: must be "):
        case_record(ROOT, name, OP, RUN, 1)
    with pytest.raises(InvalidPathValueError, match=r"^op_signature: must be "):
        case_record(ROOT, HW, name, RUN, 1)


@pytest.mark.parametrize(("name", "expected"), ADR_OP_FILES.items())
def test_op_signature_files(name, expected):
    assert rel(op_signature_file(ROOT, HW, OP, name)) == expected


def test_attempt_dirs_differ_only_in_the_role_directory():
    base = round_dir(ROOT, RUN, 7)
    suffixes = set()
    for role in ATTEMPT_ROLES:
        path = attempt_dir(ROOT, RUN, 7, role, 3, 2)
        assert path.relative_to(base).parts[0] == role
        suffixes.add(path.relative_to(role_dir(ROOT, RUN, 7, role)).as_posix())
    assert suffixes == {"candidates/03/attempts/02"}


def test_every_file_of_a_round_has_exactly_one_role_directory_above_it():
    base = round_dir(ROOT, RUN, 7)
    files = [attempt_artefact(ROOT, RUN, 7, 3, 2, name) for name in ATTEMPT_ARTEFACTS]
    files.append(decision_log(ROOT, RUN, 7))
    files.append(hypothesis_record(ROOT, RUN, 7))
    files.append(verdict_record(ROOT, RUN, 7))
    for path in files:
        parts = path.relative_to(base).parts
        assert parts[0] in ROLES
        assert not set(parts[1:]) & set(ROLES)


def test_an_artefact_is_in_the_attempt_dir_of_its_role():
    roles = set()
    for name in ATTEMPT_ARTEFACTS:
        path = attempt_artefact(ROOT, RUN, 7, 3, 2, name)
        role = path.relative_to(round_dir(ROOT, RUN, 7)).parts[0]
        assert path.parent == attempt_dir(ROOT, RUN, 7, role, 3, 2)
        roles.add(role)
    assert roles == set(ATTEMPT_ROLES)


def test_names_derived_by_the_key_module_are_accepted():
    hw = keys.hw_profile_key(synthetic_hw_record()).name
    op = keys.op_signature_key(synthetic_op_record()).name
    assert rel(op_signature_dir(ROOT, hw, op)) == f"db/{hw}/{op}"
    assert rel(hw_profile_record(ROOT, hw)) == f"db/{hw}/hw_profile.json"


def test_example_names_of_adr_0001_are_accepted():
    expected = f"db/{ADR_HW_NAME}/{ADR_OP_NAME}/best.json"
    path = op_signature_file(ROOT, ADR_HW_NAME, ADR_OP_NAME, "best.json")
    assert rel(path) == expected


@pytest.mark.parametrize("prefix", ["a", "a" * 32, "a1_b"])
def test_key_name_prefix_lengths(prefix):
    name = f"{prefix}-{HEX}"
    assert hw_profile_dir(ROOT, name).name == name
    assert op_signature_dir(ROOT, HW, name).name == name


def test_key_name_digest_length_follows_the_key_module():
    name = "synthetic_accel-" + "a" * keys.NAME_DIGEST_LENGTH
    assert hw_profile_dir(ROOT, name).name == name


def test_data_root_as_str_and_as_path_give_the_same_result():
    assert every_path(str(ROOT)) == every_path(ROOT)


def test_relative_data_root_stays_relative():
    path = attempt_artefact("relative/root", RUN, 7, 3, 2, "spec.json")
    assert not path.is_absolute()
    assert (
        path.relative_to(Path("relative/root")).as_posix()
        == (ADR_ATTEMPT_ARTEFACTS["spec.json"])
    )
    assert run_dir("", RUN) == Path("runs") / RUN


def test_every_result_is_a_path_below_data_root(tmp_path):
    for path in every_path(tmp_path):
        assert isinstance(path, Path)
        assert path != tmp_path
        assert path.is_relative_to(tmp_path)
        assert ".." not in path.relative_to(tmp_path).parts


def test_building_paths_creates_nothing(tmp_path):
    every_path(tmp_path)
    every_path(tmp_path / "missing")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("number", "name"),
    [
        (0, "0000"),
        (1, "0001"),
        (9999, "9999"),
        (10000, "10000"),
        (keys.MAX_INTEGER, "9007199254740991"),
    ],
)
def test_round_number_form(number, name):
    assert round_dir(ROOT, RUN, number).name == name
    assert rel(round_dir(ROOT, RUN, number)) == f"runs/{RUN}/rounds/{name}"


@pytest.mark.parametrize(
    ("number", "name"),
    [
        (1, "01"),
        (9, "09"),
        (99, "99"),
        (100, "100"),
        (keys.MAX_INTEGER, str(2**53 - 1)),
    ],
)
def test_candidate_and_attempt_number_form(number, name):
    path = attempt_dir(ROOT, RUN, 0, "coder", number, 1)
    assert rel(path) == f"runs/{RUN}/rounds/0000/coder/candidates/{name}/attempts/01"
    path = attempt_dir(ROOT, RUN, 0, "coder", 1, number)
    assert rel(path) == f"runs/{RUN}/rounds/0000/coder/candidates/01/attempts/{name}"


@pytest.mark.parametrize(
    "run_id",
    ["a", "7", "a" * 64, "0" * 64, "0synthetic", "syn_thetic-run", "a-_-_", "con"],
)
def test_valid_run_ids(run_id):
    assert check_run_id(run_id) is run_id
    assert rel(run_dir(ROOT, run_id)) == f"runs/{run_id}"


@pytest.mark.parametrize("run_id", BAD_RUN_IDS)
def test_invalid_run_id_is_rejected(run_id):
    calls = [
        lambda: check_run_id(run_id),
        lambda: run_dir(ROOT, run_id),
        lambda: run_file(ROOT, run_id, "STATE.json"),
        lambda: round_dir(ROOT, run_id, 0),
        lambda: role_dir(ROOT, run_id, 0, "coder"),
        lambda: decision_log(ROOT, run_id, 0),
        lambda: hypothesis_record(ROOT, run_id, 1),
        lambda: verdict_record(ROOT, run_id, 1),
        lambda: attempt_dir(ROOT, run_id, 0, "coder", 1, 1),
        lambda: attempt_artefact(ROOT, run_id, 0, 1, 1, "spec.json"),
    ]
    for call in calls:
        with pytest.raises(InvalidPathValueError, match=r"^run_id: must be "):
            call()


@pytest.mark.parametrize("number", BAD_ROUNDS)
def test_invalid_round_is_rejected(number):
    calls = [
        lambda: round_dir(ROOT, RUN, number),
        lambda: role_dir(ROOT, RUN, number, "coder"),
        lambda: decision_log(ROOT, RUN, number),
        lambda: hypothesis_record(ROOT, RUN, number),
        lambda: verdict_record(ROOT, RUN, number),
        lambda: attempt_dir(ROOT, RUN, number, "coder", 1, 1),
        lambda: attempt_artefact(ROOT, RUN, number, 1, 1, "spec.json"),
    ]
    for call in calls:
        with pytest.raises(InvalidPathValueError, match=r"^round: must be an int "):
            call()


@pytest.mark.parametrize("number", BAD_COUNTS)
def test_invalid_candidate_is_rejected(number):
    with pytest.raises(InvalidPathValueError, match=r"^candidate: must be an int "):
        attempt_dir(ROOT, RUN, 0, "coder", number, 1)
    with pytest.raises(InvalidPathValueError, match=r"^candidate: must be an int "):
        attempt_artefact(ROOT, RUN, 0, number, 1, "spec.json")


@pytest.mark.parametrize("number", BAD_COUNTS)
def test_invalid_attempt_is_rejected(number):
    with pytest.raises(InvalidPathValueError, match=r"^attempt: must be an int "):
        attempt_dir(ROOT, RUN, 0, "coder", 1, number)
    with pytest.raises(InvalidPathValueError, match=r"^attempt: must be an int "):
        attempt_artefact(ROOT, RUN, 0, 1, number, "spec.json")


@pytest.mark.parametrize("role", BAD_ROLES)
def test_invalid_role_is_rejected(role):
    with pytest.raises(InvalidPathValueError, match=r"^role: must be one of "):
        role_dir(ROOT, RUN, 0, role)
    with pytest.raises(InvalidPathValueError, match=r"^role: must be one of "):
        attempt_dir(ROOT, RUN, 0, role, 1, 1)


def test_decision_has_no_candidate_level():
    with pytest.raises(InvalidPathValueError, match=r"^role: .*got str 'decision'"):
        attempt_dir(ROOT, RUN, 0, "decision", 1, 1)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "spec",
        "SPEC.json",
        "decision.md",
        "STATE.json",
        "build.log",
        "coder/spec.json",
        "../spec.json",
        "output/",
        StrSubclass("spec.json"),
        Path("spec.json"),
        None,
        ["spec.json"],
    ],
)
def test_invalid_attempt_artefact_is_rejected(name):
    with pytest.raises(InvalidPathValueError, match=r"^name: must be one of "):
        attempt_artefact(ROOT, RUN, 0, 1, 1, name)


@pytest.mark.parametrize(
    "name",
    ["", "state.json", "spec.json", "rounds", "rounds/0000", "../STATE.json", None, 1],
)
def test_invalid_run_file_is_rejected(name):
    with pytest.raises(InvalidPathValueError, match=r"^name: must be one of "):
        run_file(ROOT, RUN, name)


@pytest.mark.parametrize(
    "name",
    ["", "hw_profile.json", "Best.json", "eval.json", "../best.json", None, 1],
)
def test_invalid_op_signature_file_is_rejected(name):
    with pytest.raises(InvalidPathValueError, match=r"^name: must be one of "):
        op_signature_file(ROOT, HW, OP, name)


@pytest.mark.parametrize("name", BAD_KEY_NAMES)
def test_invalid_hw_profile_key_is_rejected(name):
    calls = [
        lambda: hw_profile_dir(ROOT, name),
        lambda: hw_profile_record(ROOT, name),
        lambda: op_signature_dir(ROOT, name, OP),
        lambda: op_signature_file(ROOT, name, OP, "best.json"),
    ]
    for call in calls:
        with pytest.raises(InvalidPathValueError, match=r"^hw_profile_key: must be "):
            call()


@pytest.mark.parametrize("name", BAD_KEY_NAMES)
def test_invalid_op_signature_is_rejected(name):
    with pytest.raises(InvalidPathValueError, match=r"^op_signature: must be "):
        op_signature_dir(ROOT, HW, name)
    with pytest.raises(InvalidPathValueError, match=r"^op_signature: must be "):
        op_signature_file(ROOT, HW, name, "best.json")


def test_error_is_a_value_error_and_shows_a_bounded_value():
    assert issubclass(InvalidPathValueError, ValueError)
    with pytest.raises(InvalidPathValueError) as caught:
        check_run_id("X" * 10_000)
    message = str(caught.value)
    assert message.startswith("run_id: must be a str matching [a-z0-9][a-z0-9_-]{0,63}")
    assert "got str 'XXX" in message
    assert len(message) < 200


def test_error_names_the_type_of_a_rejected_subclass():
    with pytest.raises(InvalidPathValueError, match="got StrSubclass 'abc'"):
        check_run_id(StrSubclass("abc"))
    with pytest.raises(InvalidPathValueError, match="got bool True"):
        round_dir(ROOT, RUN, True)


def test_module_defines_no_reader_writer_or_entry_point():
    defined = {
        name
        for name, value in vars(layout).items()
        if getattr(value, "__module__", None) == layout.__name__
        and not name.startswith("_")
    }
    assert defined == {
        "InvalidPathValueError",
        "attempt_artefact",
        "attempt_dir",
        "build_log_file",
        "case_record",
        "check_run_id",
        "decision_log",
        "hw_profile_dir",
        "hw_profile_record",
        "hypothesis_record",
        "op_signature_dir",
        "op_signature_file",
        "role_dir",
        "round_dir",
        "run_dir",
        "run_file",
        "verdict_record",
    }


# Expected paths copied from the Walk-through of ADR-0078.
ADR_0078_SIM = (
    "runs/r1/rounds/0003/measure/candidates/02/attempts/01/"
    "build-log-correctness_check_sim-01.txt"
)
ADR_0078_BOARD = (
    "runs/r1/rounds/0003/measure/candidates/02/attempts/01/"
    "build-log-correctness_check_board-01.txt"
)


def test_build_log_file_of_the_adr_0078_walk_through():
    sim = build_log_file(ROOT, "r1", 3, 2, 1, "correctness_check_sim", 1)
    board = build_log_file(ROOT, "r1", 3, 2, 1, "correctness_check_board", 1)
    assert rel(sim) == ADR_0078_SIM
    assert rel(board) == ADR_0078_BOARD


def test_build_log_steps_are_those_of_correctness_check_and_the_run_tools():
    from hilclaw import check_identity, run_identity

    assert BUILD_LOG_STEPS == check_identity.STEPS + run_identity.STEPS
    assert BUILD_LOG_STEPS == (
        "correctness_check_sim",
        "correctness_check_board",
        "correctness_check_bf16_sim",
        "correctness_check_bf16_board",
        "sim_run_timing",
        "board_run_timing",
    )


# Expected paths copied from the Walk-through of ADR-0108 (decision 3).
ADR_0108_SIM = (
    "runs/r1/rounds/0003/measure/candidates/02/attempts/01/"
    "build-log-sim_run_timing-01.txt"
)
ADR_0108_BOARD = (
    "runs/r1/rounds/0003/measure/candidates/02/attempts/01/"
    "build-log-board_run_timing-01.txt"
)


def test_build_log_file_of_the_adr_0108_walk_through():
    sim = build_log_file(ROOT, "r1", 3, 2, 1, "sim_run_timing", 1)
    board = build_log_file(ROOT, "r1", 3, 2, 1, "board_run_timing", 1)
    assert rel(sim) == ADR_0108_SIM
    assert rel(board) == ADR_0108_BOARD
    assert build_log_file(ROOT, "r1", 3, 2, 1, "sim_run_timing", 12).name == (
        "build-log-sim_run_timing-12.txt"
    )


@pytest.mark.parametrize(
    ("number", "name"),
    [
        (1, "01"),
        (99, "99"),
        (100, "100"),
        (keys.MAX_INTEGER, "9007199254740991"),
    ],
)
def test_build_log_execution_number_form(number, name):
    path = build_log_file(ROOT, RUN, 7, 3, 2, "correctness_check_board", number)
    assert path.name == f"build-log-correctness_check_board-{name}.txt"


@pytest.mark.parametrize("step", BUILD_LOG_STEPS)
def test_build_log_file_is_in_the_measure_attempt_dir(step):
    path = build_log_file(ROOT, RUN, 7, 3, 2, step, 4)
    assert path.parent == attempt_dir(ROOT, RUN, 7, "measure", 3, 2)
    assert path.parent == attempt_artefact(ROOT, RUN, 7, 3, 2, "build.json").parent
    assert rel(path) == ATTEMPT.format("measure", f"build-log-{step}-04.txt")


@pytest.mark.parametrize("step", BUILD_LOG_STEPS)
def test_build_log_name_is_no_artefact_and_has_only_allowed_characters(step):
    name = build_log_file(ROOT, RUN, 7, 3, 2, step, keys.MAX_INTEGER).name
    assert name not in ATTEMPT_ARTEFACTS
    assert name.count(".") == 1
    assert set(name) <= set("abcdefghijklmnopqrstuvwxyz0123456789_-.")


@pytest.mark.parametrize(
    "step",
    [
        "correctness_check",
        "sim_run",
        "board_run",
        "sim.run",
        "board.run",
        "sim_run_timing ",
        "SIM_RUN_TIMING",
        "timing",
        "coder_generate",
        "",
        "correctness_check_sim/..",
        "../correctness_check_sim",
        "..",
        "CORRECTNESS_CHECK_SIM",
        "Correctness_check_sim",
        "correctness_check_sim ",
        StrSubclass("correctness_check_sim"),
        b"correctness_check_sim",
        None,
        1,
    ],
)
def test_invalid_build_log_step_is_rejected(step):
    with pytest.raises(InvalidPathValueError, match=r"^step: must be one of "):
        build_log_file(ROOT, RUN, 7, 3, 2, step, 1)


@pytest.mark.parametrize(
    "number", [0, -1, keys.MAX_INTEGER + 1, True, False, 1.0, "1", None, IntSubclass(1)]
)
def test_invalid_build_log_execution_is_rejected(number):
    with pytest.raises(
        InvalidPathValueError, match=r"^execution: must be an int from 1 "
    ):
        build_log_file(ROOT, RUN, 7, 3, 2, "correctness_check_sim", number)


def test_build_log_file_checks_the_attempt_as_attempt_dir_does():
    step = "correctness_check_sim"
    with pytest.raises(InvalidPathValueError, match=r"^run_id: "):
        build_log_file(ROOT, "Bad", 7, 3, 2, step, 1)
    with pytest.raises(InvalidPathValueError, match=r"^round: "):
        build_log_file(ROOT, RUN, -1, 3, 2, step, 1)
    with pytest.raises(InvalidPathValueError, match=r"^candidate: "):
        build_log_file(ROOT, RUN, 7, 0, 2, step, 1)
    with pytest.raises(InvalidPathValueError, match=r"^attempt: "):
        build_log_file(ROOT, RUN, 7, 3, True, step, 1)
    assert rel(build_log_file(ROOT, RUN, 0, 1, 1, step, 1)).startswith(
        f"runs/{RUN}/rounds/0000/measure/"
    )
