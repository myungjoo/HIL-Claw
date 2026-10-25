---
id: T-0476
title: Add the module that maps a tool failure raised by an operation of `sim.run` or `board.run` to the `failure` of the step's end line (the eight backend kinds as raised, `operation_failure_invalid` for every other kind; ADR-0068 decisions 3 to 6), with tests; wire it into nothing
phase: P1
status: TODO
commitMode: code
coversReq: [FR-10, OD-18, "#5 D12"]
dependsOn: [T-0475]
touchesFiles: [hilclaw/run_failure.py, tests/test_run_failure.py]
estimatedSize: {loc: 170, files: 1}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
---
## Why

PLAN P1-1 is open. Its completion criterion (D18) needs `sim.run` and `board.run` to work on the mock and `cpu_standin` and to be registered. Neither is registered today: `hilclaw/tools.py` `default_registry` does not hold them. ADR-0106 Consequences names what still stands between the landed run-tool modules (`run_identity`, `run_definition`, `run_admission`, `run_objective`, `run_seed`, `run_parameters`, `run_operation`, `run_result`, `run_journal`) and two registered tools. One item on that list is "⑲ (나), with what the tool function does with a tool failure an operation raises". ADR-0068 (accepted 2026-10-26, landed by T-0210) answers that item. Its Consequences mark one code slice as **possible now**: "the run tools' handling of a tool failure an operation raises and their backend kinds, in the manner of `hilclaw/check_failure.py`". This task is that slice, as a pure module in the form `check_failure.ended_with` has for `correctness.check`. The module is called by nothing yet; the future tool function of the run tools will call it.

It comes after T-0475 only because both come from the same batch (DRIVER §6 "task 단위" ④); it does not depend on T-0475's content. It is not merged into T-0475. T-0475 already changes eight modules of another contract and an estimated ~280 lines. Adding this module, which is of a different tool's contract and ADR, would make a two-contract PR of about 450 lines. That size invites more review rounds than two small PRs.

No HQ blocks it: HQ-0021 is answered and its record has landed. No design-level OD is decided here. No `claude`, compiler or container is involved (D16).

## Required Reading

Line numbers are those of `main` at `f9fc4abd`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (task format, naming, size cap D4/D20, trailers, the test rules D12).
- CLAUDE.md, the whole file. Above all: "테스트 규칙", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0068-od18-run-tools-operation-tool-failure.md**: Status (lines 3-13); decision 3 (lines 56-67, the eight kinds and their names); decision 4 (lines 69-80, what the tool function does, which kinds are outside the contract, `operation_failure_invalid`, "Only the tool function raises"); decision 5 (lines 82-86); decision 6 (lines 88-91, the messages); the Walk-through rows for scripts (lines 111-135); Limits (lines 137-144); Consequences "Code" (line 169).
- ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md decisions 4 and 5 (lines 67-97): the model taken here.
- `hilclaw/check_failure.py` (whole, 185 lines). This is the model, and **it is not edited**.
- `tests/test_check_failure.py` (whole). This is the model of the tests.
- The run-tool kind constants: `hilclaw/run_admission.py` lines 65-80, `hilclaw/run_objective.py` lines 55-62, `hilclaw/run_seed.py` lines 55-62, `hilclaw/run_operation.py` lines 1-90; `hilclaw/build_log.py` `KIND_BUILD_LOG_UNWRITABLE`; `hilclaw/tools.py` `RESERVED_KINDS` and `ToolFailure`.

## Acceptance Criteria

1. A new module `hilclaw/run_failure.py` (you may choose another name; give the reason in the commit body) provides:
   - a constant for `operation_failure_invalid`;
   - a frozen set of the run tools' backend kinds, exactly the eight of ADR-0068 decision 3 (`no_kernel_source`, `kernel_source_unreadable`, `build_directory_unusable`, `settings_refused`, `build_input_missing`, `compiler_unavailable`, `build_output_missing`, `executable_unstartable`);
   - a function taking the raised `hilclaw.tools.ToolFailure` and returning the pair `(kind, message)` that the end line's `failure` holds.
   
   You may reuse the constants of `hilclaw/check_failure.py` by import. If you do, the module docstring says the spelling and the meaning are shared on purpose (ADR-0068 decision 3). If you do not, a test asserts that the two sets and the two `operation_failure_invalid` constants are equal. `hilclaw/check_failure.py` and its tests are not changed.
2. The mapping follows ADR-0068 decision 4:
   - A raised backend kind gives the raised kind and the raised message, as they are.
   - Every other kind gives `operation_failure_invalid` and a message of the module. "Every other kind" means a reserved kind, `seed_not_drawn`, `objective_not_stated`, `objective_not_covered`, `op_signature_not_stated`, `op_signature_not_covered`, `n_max_not_stated`, `operation_answer_invalid`, `build_log_unwritable`, `operation_failure_invalid` itself, or any other name.
   - A `kind` (or, for a backend kind, a `message`) that cannot be read as exactly a `str` gives `operation_failure_invalid` and a message of the module, as `check_failure` does.
   - A non-`ToolFailure` argument raises `TypeError`. A `BaseException` that is no `Exception` out of an attribute read is not caught.
3. The messages follow ADR-0068 decision 6. The message of `operation_failure_invalid` says that the operation raised a tool failure of a kind the contract does not let a backend raise. It may name the raised kind only where that kind is a reserved kind or a kind of the run tools' contract; whether it does is your choice, stated in the docstring. It never shows the raised message or any other raised kind. Every message is a constant built at import time and has a bounded length.
4. The module docstring follows the house style of `check_failure.py`:
   - it cites ADR-0068 by decision;
   - "Choices that are this module's own and no rule of a record" names, at least, how the raised object is read and what the message names;
   - "What the module does not do" says that it is no tool or step, is called by no tool function yet, appends no line, states no spend, writes no compiler log (ADR-0108 decision 7 comes first in the future tool function and is not this module's), and gives no rule for `correctness.check` or `profiler.collect`.
   
   It imports only `hilclaw.tools` and, if criterion 1 reuses them, `hilclaw.check_failure`.
5. Tests in a new `tests/test_run_failure.py` (D12):
   - Happy: each of the eight backend kinds with its message passes through. The pair can build a `ToolFailure`.
   - Branch: every kind listed in criterion 2 as outside the contract, each reserved kind of `tools.RESERVED_KINDS` (parametrised), and an arbitrary name, each gives `operation_failure_invalid`. The message never contains the raised message or an arbitrary raised kind.
   - Negative: a non-`ToolFailure` (`None`, an `Exception`, a `dict`) raises `TypeError`. A `kind` replaced after construction by a non-`str` gives `operation_failure_invalid`. A backend kind whose `message` was replaced by a non-`str` gives `operation_failure_invalid`. A `kind` property raising an `Exception` gives `operation_failure_invalid`, and one raising `KeyboardInterrupt` passes through.
   - Pins: the backend-kind set equals the eight names in criterion 1, and its intersection with `tools.RESERVED_KINDS` and with the other run-tool kind constants is empty. The module imports only what criterion 4 allows (as `tests/test_check_failure.py` pins its own).
   - The argument is not modified.
6. `python -m pytest`, `ruff check .` and `ruff format --check .` pass. The `hilclaw/` coverage gate holds. **No existing test is edited.**
7. The commit body names the language (Python) and the reason in one line. The PR body ends with `Task: T-0476`.

## Out of Scope

- The tool function of `sim.run` / `board.run`, its registration, its keeper and timing-build log (ADR-0108), and a counterpart of `check_ending.carry_out`. Their form follows T-0475's form and the tool-function work.
- The three pieces ADR-0068 decision 8 leaves open: the container's situations, errors of two rows, and the sorting of kinds for ADR-0140.
- Any change to `hilclaw/check_failure.py`, `ARCHITECTURE/`, ADR text, settings or dependencies.
- Starting `claude`, a compiler or a container (D16).

## Follow-ups

- (code, later; planner) The run tools' tool function joining the landed `run_*` modules with this module and the keeper of ADR-0108, then binding and registration. Before planning it, re-read ADR-0106 and ADR-0108 Consequences for what still stands.

## Result
