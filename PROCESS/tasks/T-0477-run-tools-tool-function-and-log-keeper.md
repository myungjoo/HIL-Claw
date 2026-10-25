---
id: T-0477
title: Add the tool function of `sim.run` and `board.run` that joins the landed `run_*` modules, with the timing build's log keeper as the fifth thing of an operation and the mock's sixth (ADR-0108 code slices; ADR-0062 decision 6 order), with tests over the mock; register nothing
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, "#5 D12"]
dependsOn: []
touchesFiles: [hilclaw/run_tool.py, hilclaw/run_operation.py, hilclaw/mock_run.py, hilclaw/layout.py, hilclaw/build_log.py, tests/test_run_tool.py, tests/test_run_operation.py, tests/test_mock_run.py, tests/test_layout.py]
estimatedSize: {loc: 420, files: 5}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
---
## Why

PLAN P1-1 is open. Its completion criterion (D18) needs `sim.run` and `board.run` to work on the mock and on `cpu_standin` and to be registered as tools reachable through the MCP front. Today neither tool has a tool function: `hilclaw/tools.py` `default_registry` does not hold them, and nothing joins the landed run-tool modules (`run_identity`, `run_definition`, `run_admission`, `run_objective`, `run_seed`, `run_parameters`, `run_operation`, `run_result`, `run_journal`, `run_failure`).

ADR-0106 Consequences names what stands between those modules and two registered tools: "the tool function that joins the run tools' modules …; ⑲ (나) …; and the binding of a backend table and a source of seeds and the registration". ADR-0068 (landed by T-0210) answered ⑲ (나), and T-0476 landed its module `hilclaw/run_failure.py`. ADR-0108 Consequences lists code slices that "wait" only because "the run tools' tool functions are not written": a path for the run tools' log files, the keeper as a fifth thing of the call of an operation, the write and the kind `build_log_unwritable`, and the mock's operation and default script with the keeper. ADR-0062 decision 5 makes the `spend` the empty object, and ADR-0061 decision 3 says the tool function hands no setting to an operation, so the open source and values of the settings (⑲ (라)) and the container (OD-14) concern only the `cpu_standin` operation, not the tool function.

This task writes that tool function and the ADR-0108 slices, in the form the check already has (`hilclaw/check_tool.py`, `hilclaw/check_ending.py`, `hilclaw/check_operation.py`, `hilclaw/mock_check.py`). Per D20 ③ the ADR-0108 slices are merged into this task: alone they are well under half the cap, and the tool function is their only caller. The binding of the default table, the source of seeds and the registration are left to T-0478, because no record yet decides them for the run tools (ADR-0070 decision 3 left "when the default registry holds the mock with those operations" to the run tools' records).

No HQ blocks it. No design-level OD is decided here: every rule comes from an accepted record. No `claude`, compiler or container is started (D16): the tests use only the mock.

## Required Reading

Line numbers are those of `main` at `e375a388`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-115: task format, naming, size cap D4/D20, trailers, the test rules D12).
- CLAUDE.md, the whole file. Above all: "테스트 규칙", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **The order of a call**: ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md decisions 2 to 6 and the Walk-through (lines 37-113). ADR-0067-od18-run-tools-admission-kinds.md decision 5 (lines 69-91, the order of ④ and the draw). ADR-0064-od13-run-tools-timing-seed.md decisions 2 and 3 (the draw is per call, before the start line).
- **The split and the result**: ADR-0061-od18-run-tools-split.md decisions 3, 4, 6 and 7 (lines 49-97). ADR-0063-od18-run-tools-result-members.md decisions 2 to 9 and the Walk-through (lines 37-169): `outcome`, the `condition` of a broken result and its order, `ceiling` and `bound`.
- **The operation form**: ADR-0065-od18-run-tools-operation-form.md decisions 2, 4, 5, 7 and 8 (lines 33-116).
- **The log**: ADR-0108-od18-run-tools-timing-build-compiler-log.md decisions 2, 3, 5, 7 and 8, the Walk-through and Consequences (lines 35-134).
- **A raised tool failure**: ADR-0068-od18-run-tools-operation-tool-failure.md decisions 4, 5 and 7, the Walk-through and Consequences "Code" (lines 69-135, 166-169).
- **The mock**: ADR-0066-od18-run-tools-mock-script.md decisions 2, 3 and 6 (lines 33-57, 80-96).
- The models, **not edited**: `hilclaw/check_tool.py` (whole), `hilclaw/check_ending.py` (whole), `hilclaw/check_operation.py` (the keeper's close and write), `hilclaw/mock_check.py` (the operation with the keeper), and their tests `tests/test_check_tool.py`, `tests/test_check_ending.py` (the fixtures that build a data root, a run and a registry over the mock).
- The modules joined (whole): `hilclaw/run_identity.py`, `hilclaw/run_definition.py`, `hilclaw/run_admission.py`, `hilclaw/run_objective.py`, `hilclaw/run_seed.py`, `hilclaw/run_parameters.py`, `hilclaw/run_operation.py`, `hilclaw/run_result.py`, `hilclaw/run_journal.py`, `hilclaw/run_failure.py`, `hilclaw/mock_run.py`, `hilclaw/build_log.py`; `hilclaw/hw_tool.py` (`tool_function`, `stepped_tool_function`, lines 157-338); `hilclaw/harness/timing.py` (`judge_report`, `Judgement`, `Broken`, lines 102-255); `hilclaw/layout.py` (`BUILD_LOG_STEPS`, `attempt_dir`, `build_log_file`, lines 40-176).

## Acceptance Criteria

1. **Log path.** `hilclaw.layout.build_log_file` also forms the path of a run tool's file, `<measure attempt dir>/build-log-<step>-<EE>.txt`, for the `step` values `sim_run_timing` and `board_run_timing` (ADR-0108 decision 3). Its docstring and `BUILD_LOG_STEPS` (or a new constant) say so. Every other `step` is still refused.
2. **The keeper reaches an operation.** `hilclaw.run_operation.ask` calls an operation with five things: the four of ADR-0065 decision 2 and the log keeper (ADR-0108 decision 5). After the operation came back, by returning or by raising, the keeper is closed and what it holds is available to the caller, in the manner of `hilclaw.check_operation.ask`. Whether `ask` itself writes the file (as `check_operation.ask` does) or the tool function writes it is your choice; give the reason in the module docstring. The rule of ADR-0108 decision 7 holds either way: when a log was handed over, the file is written before the answer is judged, whatever the operation returned or raised but a request to end; a raised request to end passes through and nothing is written. A refused hand-over that the operation lets pass is `operation_answer_invalid` (ADR-0108 decision 5). The module docstring stops saying "four things".
3. **The mock.** `hilclaw.mock_run.operation` builds an operation called with the five things, which asks its script once with six: the tool and the five, the keeper last (ADR-0108 decision 8). `default_script` takes the six, hands over no log and keeps its answer. The docstrings stop saying "four things".
4. **The tool function.** A new module (suggested `hilclaw/run_tool.py`; you may choose another name or split it in two in the manner of `check_tool`/`check_ending`, and give the reason in the commit body) provides a function that, given the tool name (`"sim.run"` or `"board.run"`), the data-root source, a backend table, a source of seeds and the predicate "covered", returns the tool function of that tool. Building it reads no file, calls none of the sources and asks the table nothing. A call follows ADR-0062 decision 6 with ADR-0067 decision 5:
   - ① the frame check and `run_definition.check` (a member no record names is `invalid_request`); the `step` is `run_identity.step_of(tool)`;
   - ②, ⓢ and ③ as `hilclaw.hw_tool` has them (the data root, the layout stamp, the lookup; a stored result or failure is answered again and nothing runs; an open identity is `step_open`);
   - ④ one read of `instance.json`, the selection (`no_backend`, `not_offered`), then `run_admission.admit` with the predicate;
   - the draw by `run_seed.draw` (`seed_not_drawn` with no line), the output path of the attempt (ADR-0061 decision 3; formed as `check_tool` forms its own), and the `run_parameters.TimingParameters` of the six values;
   - ⑤ the start line;
   - ⑥ the operation through `run_operation.ask` with a new keeper; the log written if handed over; then (A) judged with `harness.timing.judge_report` using the `sample_form` and `n_max` handed over, giving `run_result.completed` (converged or not converged) or `run_result.broken` with the condition ADR-0063 decision 3 gives for the judgement; (B) giving `run_result.broken` with that condition; the verdict where a `bound` is stated (ADR-0063 decision 7);
   - ⑦ the end line, with `spend` the empty object, and either the result or a `failure`: `operation_answer_invalid` (neither form), the pair `run_failure.ended_with` gives (a raised tool failure), or `build_log_unwritable` (a handed-over log that could not be written, in place of every other answer; ADR-0108 decision 7).
   The run tools' own kind `build_log_unwritable` is a constant of the run tools' contract, equal in spelling to `hilclaw.build_log.KIND_BUILD_LOG_UNWRITABLE` (ADR-0108 decision 7 "defined again by this contract"); a test holds the two equal. No message shows a path, an error text, a byte of a log or the seed (ADR-0108 decision 7; ADR-0061 decision 7).
5. **Imports.** Importing the new module, `run_operation` or `mock_run` imports no NumPy. If `harness.timing` is imported, it is imported where `check_definition` imports the check's modules (inside functions) or it is shown not to import NumPy; a test pins whichever holds.
6. **Docstrings** follow the house style of `check_tool.py`: cite each record by decision; "Choices that are this module's own and no rule of a record"; "What the module does not do" — it registers nothing, binds no default table or source of seeds (T-0478), has no `cpu_standin` operation, states no spend axis and bounds no log size (ADR-0108 decision 6).
7. **Tests** (D12), through a tool function built in the test over a backend table holding the mock under `hilclaw.mock_backend.NAME` with `mock_run` operations bound to test scripts, and a run whose `instance.json` names the mock, in the manner of `tests/test_check_tool.py`:
   - Happy: the default script gives a completed, converged result for `sim.run`; `board.run` with the same request is another identity with its own result; the same request again returns the stored result and runs nothing; `execution` 2 runs again. The end lines hold `step` `sim_run_timing` / `board_run_timing` and the empty `spend`.
   - Branch: a report that does not converge; each condition of the form (B) gives a broken result with that condition; a report that `judge_report` finds broken gives the condition ADR-0063 decision 3 maps it to; with a stated `bound` and a figure the `ceiling` is `within` or `over`, with no figure `not_judged`, with no `bound` `not_stated`. A script that hands over a log leaves the file at the path of criterion 1 with the log's text, for a returned (A), a returned (B) and a raised tool failure.
   - Error: a raised backend kind ends the step with that kind and message; a raised reserved kind, a run-tool kind and an arbitrary kind end it with `operation_failure_invalid`; a value of neither form and a raised `Exception` end it with `operation_answer_invalid`; a log handed over whose write fails (the attempt directory is a file, or the name is taken) ends it with `build_log_unwritable` in place of each of those answers; a raised `KeyboardInterrupt` passes through, writes no file and leaves the identity open (`step_open` next time).
   - Negative: a request with a sixth member, without `execution`, or with `execution` 0 is `invalid_request` with no line; a run at `cpu_standin` or at another `accelerator` is `no_backend`; an `instance.json` with no op_signature, an uncovered one, no `n_max`, no objective or an uncovered objective gives the kind of ADR-0067 decision 5 in its order, with no seed drawn and no line; a source of seeds that raises or returns no seed is `seed_not_drawn` with no line; a second hand-over and a non-text hand-over are refused in the operation; the builder refuses a tool name other than the two and non-callable sources.
   - The timing parameters handed to the script equal the run's `shape`, `n_max`, the sample form `"interval"` and the drawn seed; the output path is the attempt's.
   - The changed tests of `run_operation`, `mock_run` and `layout` cover the five and six things and the new `step` values; every public function of a touched module is tested.
8. `python -m pytest`, `ruff check .` and `ruff format --check .` pass. The `hilclaw/` coverage gate (line and function ≥ 80%) holds. Existing tests are edited only where the four-to-five change requires it.
9. The commit body names the language (Python) and the reason in one line. The PR body ends with `Task: T-0477`.

## Out of Scope

- The default table, the source of seeds and the predicate bound for the default registry, the tool definitions and the registration in `default_registry`, and the ADR-0077 accepted requests: T-0478.
- The `cpu_standin` operation of either run tool (ADR-0068 decision 8, ADR-0144 decision 7, OD-14, ⑲ (라)).
- A size bound of the log (ADR-0108 decision 6); the result files `sim.json`/`board.json` (PLAN P1-8); ⑳; a spend axis.
- Any change to `hilclaw/check_*.py`, `hilclaw/mock_check.py`, `ARCHITECTURE/`, `orchestration/`, settings or dependencies. Editing the less-exact sentences ADR-0108 and ADR-0068 Consequences list (D18: wording clean-up).
- Starting `claude`, a compiler or a container (D16).

## Follow-ups

- (T-0478) The registration ADR and code for both run tools.
- (later; planner) The `cpu_standin` operation of `sim.run` and `board.run`, which P1-1's completion criterion also needs; before planning it, re-read ADR-0068 decision 8 and Consequences, ADR-0144 decision 7 and ADR-0107/0116/0117 Consequences for what still stops it.

## Result
