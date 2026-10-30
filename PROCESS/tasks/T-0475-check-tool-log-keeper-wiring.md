---
id: T-0475
title: Thread the compiler-log keeper of `hilclaw/build_log.py` through the call of a `correctness.check` operation, write a handed log before the answer is judged and end the step with `build_log_unwritable` when that write fails, and have the mock's operation and default script take the keeper (ADR-0078 decisions 6 and 7, code slices 2 and 3 of its Consequences), with tests
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, FR-6, FR-9, OD-18, "#5 D12"]
dependsOn: []
touchesFiles: [hilclaw/check_operation.py, hilclaw/check_ending.py, hilclaw/check_seed.py, hilclaw/check_tool.py, hilclaw/mock_check.py, hilclaw/build_log.py, hilclaw/mock_backend.py, hilclaw/check_definition.py, tests/test_check_operation.py, tests/test_check_ending.py, tests/test_check_seed.py, tests/test_check_tool.py, tests/test_mock_check.py, tests/test_check_definition.py, tests/test_build_log.py]
estimatedSize: {loc: 280, files: 8}   # tests excluded from the cap (DRIVER §5, D4); most of the non-test lines are docstrings
hq: []
---
## Why

PLAN P1-1 is open. Its completion criterion (D18) asks that `correctness.check` work on `cpu_standin` and on the mock. ADR-0078 (accepted, OD-18 sub-question 18 part (na)) fixes that every operation of this tool hands the compiler's log of its build to a fifth thing it is called with, the **log keeper**, and that the tool function writes that log to `runs/<run_id>/rounds/<RRRR>/measure/candidates/<CC>/attempts/<AA>/build-log-<step>-<EE>.txt` before it judges the answer. A `cpu_standin` operation therefore cannot be bound to this tool until the call carries a keeper. ADR-0078 Consequences says: "The file of the log is no longer a stop" for that operation. T-0243 (PR #287, `be5020d3`) landed slice 1, the parts that wire nothing: `layout.build_log_file`, `layout.BUILD_LOG_STEPS` and the module `hilclaw/build_log.py` (`LogKeeper`, `HandOverRefused`, `KIND_BUILD_LOG_UNWRITABLE`, `BuildLogUnwritable`, `write`). This task does slices 2 and 3. They have to land together: once the call has five things, the mock's operation must accept five things too.

D18 check: this work falls inside P1-1's completion criterion, as argued above. It is also needed for P2-5. `hilclaw/spec_feedback.py` (ADR-0151 decision 3 check ⑩, wired since T-0416) appends the compiler log of a `compile` failure to the next round's spec when that file exists. Nothing writes that file until this task lands, so a coder in the first run would never see its compiler's diagnostics.

No HQ blocks this task. HQ-0026 (T-0243) is answered. The open HQs are runtime-acceptance items, HQ-0070 (RoPE) and HQ-0071 (model-level comparison), and none of them touches this tool. No design-level OD is decided here: ADR-0078 decision 6 leaves "its Python form, its name and how it reaches an operation and a script" to the code. No `claude` process, compiler or container is started or needed (D16). Everything runs over the mock and `tmp_path`.

Planner's notes. These are taken from the files at `f9fc4abd`. Re-check each one, because the text wins.
- The call chain today is `check_tool._perform` → `check_seed.check(operation, request, hw_profile, admitted, seed, output_path)` → `check_ending.carry_out(operation, request, hw_profile, parameters, output_path, *, rtol, atol)` → `check_operation.ask(...)`. `ask` calls `operation(request, hw_profile, parameters, output_path)` and then **judges in the same function** (`check_answer.from_answer`). ADR-0078 decision 7 puts the write **between** the operation's return or raise and the judging. So the write, or a callable that does it, has to run inside `ask`'s flow, or `ask` has to be split. Do not catch `BuildLogUnwritable` inside `ask` as an `Exception` of the operation: that would turn it into `operation_answer_invalid`.
- `carry_out` wraps the operation in a local `call` so that it can tell a `ToolFailure` the operation raised from one `ask` raised. Whatever wraps the operation now must keep that distinction.
- `_perform` builds the output path from the request. The build-log path needs `step` (`check_identity.step_of`, or the step `hw_tool` already resolved) and `request["execution"]`.
- `mock_backend.py` (module docstring) and `check_definition.default_table` (docstring) both say the operation "takes four arguments". `build_log.py` says it "is called by no tool yet".
- Several existing tests pin things this task must change: fake operations with four positional parameters, `script(tool, request, hw_profile, parameters, output_path)` with five, the import sets of the modules (`test_module_imports_the_three_only_and_has_no_entry` in `tests/test_check_operation.py` and `tests/test_check_ending.py`, `test_module_imports_the_five_only_and_has_no_entry` in `tests/test_check_seed.py`, `test_the_module_imports_the_harness_and_the_type_only_and_has_no_entry` in `tests/test_mock_check.py`, the `ast` import check near line 1093 of `tests/test_check_tool.py`), and docstring phrases. Acceptance criterion 12 lists exactly which edits are allowed.

## Required Reading

Line numbers are those of `main` at `f9fc4abd`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8` (the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (task format, naming, size cap D4/D20, trailers, the test rules D12).
- CLAUDE.md, the whole file. Above all: "테스트 규칙", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode, all steps); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md**:
  - decision 2 (lines 32-37: which logs are kept; an empty log is kept as an empty file; the mock's default script hands nothing);
  - decision 6 (lines 64-79: the keeper, at most once, before the operation returns or raises; what reaches it afterwards is not written; refusals answered `operation_answer_invalid`; the mock's script is asked with six things);
  - decision 7 (lines 81-90: the order — operation, write if a log was handed, judge, end line; a raised request to end passes through and nothing is written; a failed write gives `build_log_unwritable` in place of whatever the operation returned or raised; the message rule);
  - Walk-through (lines 92-103);
  - Consequences slices (2) and (3) (line 125).
- ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md decisions 4 and 5. ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md decisions 3 and 4. ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md decision 6 (the row ⑥ of its order table, line 117).
- `hilclaw/build_log.py` (whole, 194 lines); `hilclaw/layout.py` lines 40-60 and 161-176 (`BUILD_LOG_STEPS`, `build_log_file`).
- `hilclaw/check_operation.py` (whole, 229 lines); `hilclaw/check_ending.py` (whole, 178 lines); `hilclaw/check_seed.py` lines 1-98 and 147-202; `hilclaw/check_tool.py` (whole, 184 lines); `hilclaw/mock_check.py` (whole, 159 lines); `hilclaw/check_definition.py` lines 1-60 and 107-157; `hilclaw/mock_backend.py` lines 1-30; `hilclaw/check_identity.py` lines 76-110; `hilclaw/hw_tool.py` lines 160-235 (what `perform` is handed).
- `hilclaw/spec_feedback.py` lines 30-35 and 170-190 (the reader of the file this task makes appear).
- The tests of the touched modules (listed in `touchesFiles`). Read how they build fake operations and scripts before changing anything.

## Acceptance Criteria

Call and keeper (ADR-0078 decision 6):
1. An operation of `correctness.check` is called with **five** things: the four of ADR-0056 decision 3 as today, and the keeper. A fifth positional argument is the expected form. If you choose another form, give the reason in the commit body. `check_tool`'s step makes one new `build_log.LogKeeper` per call. A call answered before the operation is reached (the lookup, admission, the seed draw) makes none or leaves it unused.
2. The keeper is closed once the operation came back by returning or by raising anything, a `BaseException` included. It is closed before the held log is read. A hand-over after that point is refused by the keeper and is never written.
3. A `HandOverRefused` that the operation lets pass is answered like any other `Exception` of the operation: `operation_answer_invalid`. The existing rule of `ask` stays as it is.

Write and order (ADR-0078 decision 7):
4. When the operation returned, or raised an `Exception` (a `ToolFailure` included), and the keeper holds a log, the tool function writes it with `build_log.write` to `layout.build_log_file(data_root, run_id, round, candidate, attempt, step, execution)` of the call. It does this **before** the answer is judged and before the end line. This holds for a returned report, a returned condition, a value of neither form, a raised error and a raised tool failure of any kind.
5. When nothing was handed over, no file is written and no directory is created for it. When an empty text was handed over, an empty file is written.
6. When the write raises `BuildLogUnwritable`, the step ends with a `failure` of kind `build_log_unwritable` and the message of that exception. This replaces whatever the operation returned or raised: no result is made, and no `from_answer` and no `ended_with` result reaches the end line. The `spend` is the empty object, as for every other failure of this tool. The identity is ended. The same request afterwards gets the stored failure and makes no second write.
7. When the operation raised a `BaseException` that is no `Exception` (a request to end), nothing is written, the exception passes through unchanged, and no end line is appended (the identity stays open, as today).
8. When judging raises for a value it refuses (the paths that pass through `ask` today), the file has already been written, and that error still passes through as today.
9. A log handed over with a write that succeeds changes nothing else. The result, or the `failure` of `ask`/`ended_with`, is exactly what it is today.

Mock (ADR-0078 decision 6 and Consequences slice 3):
10. `mock_check.operation(script)` returns an operation that takes the five things and asks `script("correctness.check", request, hw_profile, parameters, output_path, keeper)`. `mock_check.default_script` takes these six and hands nothing over. Its answer is unchanged (ADR-0044 decision 3). The default registry's `correctness.check` keeps its answers, and a run at the mock with the default script leaves no build-log file.

Docstrings:
11. Update the docstrings of every touched module and function so that they describe the five things, the keeper and the write with its order. This includes `build_log.py` (no longer "called by no tool yet"), `mock_backend.py` and `check_definition.default_table` ("four arguments"). Cite ADR-0078 by decision. Keep the house style ("Choices that are this module's own…", "What the module does not do"). No message composed by this code shows a path, the text of an error or a byte of a log.

Tests (D12):
12. **Existing tests may be edited only as follows.** A fake operation or script may gain the keeper parameter. An import-set or public-name pin may gain the newly imported modules or new public names. An assertion on a docstring phrase may be changed where criterion 11 changes that phrase. Nothing else in an existing test may be weakened or removed. If any other existing test fails, stop and report BLOCKED (requirement unclear) rather than edit it.
13. New tests, over the mock with test scripts that hand a log and with a `tmp_path` data root, through the registered tool or through `check_tool.tool_function`, and also at the level of each changed function:
    - Happy path, for both `sim` and `board`: the file appears at the Walk-through path (`runs/r1/rounds/0003/measure/candidates/02/attempts/01/build-log-correctness_check_sim-01.txt`) with exactly the handed bytes; a handed empty log gives an empty file; no handed log gives no file; `execution` 2 gives the `-02` name.
    - Branch, one test for each answer form with a handed log: a returned report, a returned condition, a value of neither form, a raised `Exception`, a raised backend kind, and a raised kind outside the contract. Each writes the file and keeps its usual answer.
    - Error: a taken final name, and a file system refusal (for example a regular file where the measure attempt directory must be, or `build_log.write` monkeypatched to raise `BuildLogUnwritable`). Each gives a tool failure `build_log_unwritable`, an end line with that `failure` and no `result`, a repeated request answered from the line, and a pre-existing file left byte-for-byte.
    - Negative: a hand-over after the operation came back (from a thread or a kept reference) is refused and not written; a second hand-over inside the operation, let pass, gives `operation_answer_invalid` with the first log written; a `bytes` log, let pass, gives `operation_answer_invalid` and no file; a `KeyboardInterrupt` raised after handing a log leaves no file and no end line.
    - Every public function whose signature changed is tested.
14. `python -m pytest`, `ruff check .` and `ruff format --check .` pass. The `hilclaw/` coverage gate (line and function ≥ 80%) holds.
15. The commit body names the language (Python) and the reason in one line. The PR body ends with `Task: T-0475`.

## Out of Scope

- `hilclaw/clang_build.py` losing the log on an `OSError` from moving the artefact or removing its temporary file (ADR-0078 slice 4). It is deferred under D18 and is not done here.
- The `cpu_standin` operation of `correctness.check` and its registration in the backend table.
- The run tools (`sim.run`, `board.run`): their keeper and timing-build log (ADR-0108), and what their tool function does with a raised tool failure (ADR-0068; T-0476).
- `hilclaw/spec_feedback.py` forming the build-log name itself instead of calling `layout.build_log_file` (a refactor; deferred).
- A size bound of the file (⑱ (na)); who commits it (OD-17); `hilclaw/check_failure.py` `BACKEND_KINDS`.
- Any edit of `ARCHITECTURE/`, of ADR text, of the data repository or of settings files; any new dependency.
- Starting `claude`, a compiler, a container or any runtime-only resource (D16).

## Follow-ups

- (code, later) ADR-0108 slices for `sim.run` / `board.run`: the keeper as the fifth thing of `run_operation.ask` and the timing-build log file. Model them on the form this task chooses.

## Result

DONE — PR #289 squash-merged as 77566a1b after 1 review round (Approve), CI green. Language: Python (existing `hilclaw/` package). Follow-up already listed above (ADR-0108 keeper for `sim.run`/`board.run`), left to the planner.
