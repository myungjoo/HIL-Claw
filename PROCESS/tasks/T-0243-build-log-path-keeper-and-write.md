---
id: T-0243
title: Add the path of the compiler's log file to `hilclaw/layout.py` and a new module `hilclaw/build_log.py` holding the log keeper, the kind `build_log_unwritable` and the once-only write of the file (ADR-0078 decisions 2-4, 6, 7, code slice 1 of its Consequences), with tests; no change to `check_operation`, `check_ending`, `check_seed`, `check_tool`, `mock_check` or `clang_build`
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, FR-6, FR-9, OD-18, "#5 D12"]
dependsOn: [T-0242]
touchesFiles: [hilclaw/layout.py, hilclaw/build_log.py, tests/test_layout.py, tests/test_build_log.py]
estimatedSize: {loc: 180, files: 2}   # tests excluded from the cap (DRIVER §5, D4); the test files are expected to be longer
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. ADR-0078 (landed by T-0242, `main` at `e428f49`) answered OD-18 sub-question 18 part (na) for `correctness.check`: the log of every build whose compiler ended is kept as a tracked UTF-8 text file `runs/<run_id>/rounds/<RRRR>/measure/candidates/<CC>/attempts/<AA>/build-log-<step>-<EE>.txt`, written by the tool function from a log the operation hands to a fifth thing, the **log keeper**, before the end line; a failed write ends the step with the new kind `build_log_unwritable`. Its Consequences list four code slices. Doing them all at once touches six modules (`layout`, `check_operation`, `check_ending`, `check_seed`, `check_tool`, `mock_check`) plus `clang_build`, over the cap of DRIVER §5. This task is the first slice: the **pure parts that wire nothing** - the path function, the keeper and the write - so the next task only has to thread the keeper through the call and call the write.

It depends on no unanswered HQ: HQ-0021 (T-0210) concerns the run tools' timing build, HQ-0022 the JSON-text helper, HQ-0023..0025 the S6 metric, `injections` and `profiler.collect`. No design-level OD is decided here: ADR-0078 fixes what is fixed, and it leaves "its Python form, its name and how it reaches an operation and a script" to the code (decision 6). It ticks **no PLAN checkbox** (P1-1 stays open). No `claude` process is started or needed (D16): everything is pure Python over `tmp_path`.

Planner's notes (from the files at `e428f49`; the reviewer is asked to re-check each):
- Keeping `ATTEMPT_ARTEFACTS` and `_ARTEFACT_ROLE` unchanged avoids every existing pin in `tests/test_layout.py` (`test_public_name_lists_match_the_adr` compares `ATTEMPT_ARTEFACTS` with ADR-0004's seven names). The log file is not one of ADR-0004's artefacts (ADR-0078 decision 3: "no record of a result"), so a separate function is the natural form; the executor may choose otherwise only with a reason in the commit body and without weakening any existing assertion.
- `hilclaw/layout.py` imports only `hilclaw.keys`. `hilclaw/check_identity.py` (line 88) has `STEPS = (STEP_SIM, STEP_BOARD)` = `("correctness_check_sim", "correctness_check_board")`. Whether `layout` imports `check_identity` or holds its own closed list (with a test that the two agree) is the executor's choice; either way `<step>` must come from a closed list so that no separator enters the path (the module docstring's rule).
- `execution` in a request is an integer from 1 to `keys.MAX_INTEGER` (`hilclaw/check_definition.py` line 88); `layout._number(argument, value, 1, 2)` already formats "zero-padded to at least two digits, never truncated".
- `hilclaw/once_write.py` `write_once(path, content)` is the shared ADR-0014/0025/0029 once-only write (temporary `<final>.<token>.tmp`, flush, hard link, no replacing rename); it returns the `FileExistsError` when the final name is taken and raises the `OSError` of a failed step. `hilclaw/cases_file.py` lines 221-260 show how a module wraps it.
- `hilclaw/check_operation.py` `ask` (lines 168-229) answers any `Exception` an operation raises that is no `ToolFailure` with `operation_answer_invalid`. ADR-0078 decision 6 relies on exactly that for the keeper's refusals, so the keeper's refusal error must be an `Exception` and **not** a `hilclaw.tools.ToolFailure` (nor a `BaseException` outside `Exception`).

## Required Reading

Line numbers are those of `main` at `e428f49`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8` (the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (task format, naming, size cap D4, trailers, the test rules D12).
- CLAUDE.md, the whole file; above all "테스트 규칙", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode, all steps); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md** (149 lines): decision 2 (lines 32-37: every build whose compiler ended; an empty log is kept as an empty file), decision 3 (lines 39-46: the path and the name, `<EE>` rule, flat name, `.txt`, allowed characters), decision 4 (lines 48-53: UTF-8 without BOM, nothing added/removed/changed, no final newline added, no size bound), decision 6 (lines 64-79: the keeper - at most once, before the operation returns or raises; what reaches it afterwards is not written; refuses a second hand-over, a value that is no text and a text that cannot be encoded as UTF-8, by an error raised in the operation; holds and writes nothing; "its Python form, its name and how it reaches an operation and a script" are the code's), decision 7 (lines 81-90: the write of ADR-0029 decisions 4-6, missing directories up to the attempt directory may be created; a failed write or a taken name gives the kind `build_log_unwritable`; the message shows no path, no text of an error and no byte of the log), Walk-through (lines 92-103), Consequences code slices (line 125).
- ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md decisions 4-6 (lines 48-73); ADR-0004-od8-data-plane-layout.md decisions 3 and 9 (lines 86-97, 131-145).
- `hilclaw/layout.py` (whole, 221 lines) - the house style: closed lists, `_one_of`, `_number`, `InvalidPathValueError`, pure functions returning `Path` below `data_root`.
- `hilclaw/once_write.py` (whole, 86 lines); `hilclaw/cases_file.py` lines 1-80 and 221-260 (module docstring sections "Choices that are this module's own" / "What the module does not do", and the wrapping of `write_once`).
- `hilclaw/check_operation.py` lines 1-80 and 168-229 (how a raised `Exception` becomes `operation_answer_invalid`; the house style of an exception class with `kind` and `message`); `hilclaw/check_identity.py` lines 76-93; `hilclaw/tools.py` lines 60-90 (`ToolFailure`).
- `tests/test_layout.py` (whole) and `tests/test_once_write.py` (how the once-only write is tested on this machine, including Windows).

## Acceptance Criteria

Path (ADR-0078 decision 3):
1. `hilclaw/layout.py` gains one public function (name is the executor's; e.g. `build_log`) taking `data_root, run_id, round, candidate, attempt, step, execution` and returning `attempt_dir(data_root, run_id, round, "measure", candidate, attempt) / f"build-log-{step}-{EE}.txt"`, where `<EE>` is `execution` zero-padded to at least two digits and never truncated. `step` must be one of exactly `correctness_check_sim` and `correctness_check_board`; `execution` an exact `int` from 1 to `keys.MAX_INTEGER`; every other argument is checked as `attempt_dir` checks it. A violation raises `InvalidPathValueError` naming the argument. The docstring of the module and of the function are updated (the function's docstring cites ADR-0078 decision 3 and says the file is not one of `ATTEMPT_ARTEFACTS`).
2. `ATTEMPT_ARTEFACTS`, `_ARTEFACT_ROLE`, `LAYOUT_VERSION` and every existing function stay as they are.
3. Tests in `tests/test_layout.py` (additions only; adding the new name to the import block and the new path to the `every_path` helper is allowed): the Walk-through path `runs/r1/rounds/0003/measure/candidates/02/attempts/01/build-log-correctness_check_sim-01.txt` and its `board` twin; `execution` 1, 99, 100 and `keys.MAX_INTEGER` (written in full); negative cases - `step` not in the list (another `step` of the package, `""`, a value with `/`, `..`, upper case, a non-`str`), `execution` 0, -1, `MAX_INTEGER + 1`, `True`, `1.0`, `"1"`; the file's parent equals the measure attempt directory; the name matches none of `ATTEMPT_ARTEFACTS` and holds only lowercase ASCII letters, digits, `_`, `-` and one dot; if the step list is held in `layout`, a test that it equals `check_identity.STEPS`. **No existing assertion is edited or removed.**

Keeper (ADR-0078 decision 6), in the new module `hilclaw/build_log.py`:
4. A class (the keeper) made by the tool function for one call: an operation hands the log over by one method (name is the executor's) taking one text. It refuses, by raising an exception of this module that is an `Exception` and **no** `hilclaw.tools.ToolFailure`: a second hand-over (whether or not the first was accepted is the executor's choice, stated in the docstring); a value that is not exactly a `str`; a `str` that cannot be encoded as UTF-8 (a lone surrogate). The refusal's message shows no byte of the handed value.
5. The tool function's side: a way to close the keeper when the operation came back, after which a hand-over is refused (or ignored - executor's choice, stated) and never changes what is held; and a way to read what is held: the text, or a distinct "nothing handed over" value (`None` is acceptable). An empty `str` is a valid hand-over and is held as an empty text, distinct from "nothing handed over" (decision 2).
6. The keeper writes nothing, reads no file, and its `repr` shows none of the held text.

Kind and write (ADR-0078 decisions 4 and 7):
7. A module constant for the kind, exactly `"build_log_unwritable"`, and an exception class carrying `kind` and `message` in the manner of `check_operation.OperationAnswerInvalid` (exact `str` message, composed by this module; no amount). It is no `ToolFailure`.
8. A write function taking the final path (as the new `layout` function returns it) and the held text: the bytes written are exactly `text.encode("utf-8")` - no BOM, no added newline, no line-end conversion; an empty text gives an empty file. It uses `hilclaw.once_write.write_once`. Missing directories up to the attempt directory may be created (decision 7); whether it creates them is the executor's choice, stated in the docstring; if it does, it creates at most `path.parent` and its missing parents (the measure attempt directory chain), nothing beside them.
9. When the final name is taken, or any `OSError` arises in creating directories or in `write_once`, the function raises the exception of criterion 7 with the kind `build_log_unwritable`; the file under a taken name is left as it was found. Its message shows **no path, no text of an error and no byte of the log**; neither its `__cause__` nor its `__context__` carries the `OSError` (use `from None` or raise outside the handler). A `TypeError` for a non-`str` text, and what `layout` raises, pass through unchanged.
10. The module docstring follows the house style ("Choices that are this module's own and no rule of a record", "What the module does not do": it wires nothing into `correctness.check`, is called by no tool yet, writes no end line, states no spend, and composes no message that holds a path). It imports only what it uses among `hilclaw.once_write` and the standard library (and `hilclaw.layout` only if needed).

Tests (D12), `tests/test_build_log.py`:
11. Happy: a handed log is held and written with exact bytes (ASCII, multi-byte UTF-8, U+FFFD, CR/LF kept as given, no trailing newline); an empty log gives an empty file; nothing handed gives "nothing held"; the write creates the missing measure attempt directory below a `tmp_path` data root (if the executor chose to create it); no `*.tmp` remains after success.
12. Error and negative: second hand-over; non-`str` values (`bytes`, `None`, `int`, a `str` subclass); a lone surrogate; hand-over after closing; the exception of criterion 4 is no `ToolFailure` and is an `Exception`; a taken final name (the existing file left byte-for-byte as it was) gives `build_log_unwritable`; an `OSError` from the file system (e.g. a regular file where a directory is needed, or `write_once` monkeypatched to raise) gives `build_log_unwritable` whose message holds neither the path nor the `OSError` text nor any log byte, and whose `__cause__`/`__context__` is `None`; `repr` of the keeper hides the text.
13. Every public function and class of `hilclaw/build_log.py` and the new `layout` function are tested; `python -m pytest`, `ruff check .` and `ruff format --check .` pass; the `hilclaw/` coverage gate (line and function ≥ 80%) holds.
14. **Existing tests are not edited**, except additions to `tests/test_layout.py` as in criterion 3. If an existing test fails because of this change, stop and report BLOCKED (requirement unclear) rather than editing it.
15. The commit body names the language (Python) and the reason in one line; the PR body ends with `Task: T-0243`.

## Out of Scope

- Wiring: the fifth argument of `check_operation.ask`, `check_ending.carry_out`, `check_seed.check`, the write in `check_tool._perform`, the mock's operation and default script asked with the keeper (code slices 2 and 3 of ADR-0078 Consequences; next task).
- `hilclaw/clang_build.py` losing the log on an `OSError` from moving the artefact or removing its temporary file (code slice 4).
- Any change to `hilclaw/check_failure.py` `BACKEND_KINDS` (the new kind is the tool's own, not a backend kind; a backend raising it is already answered `operation_failure_invalid`).
- A size bound of the file (open under OD-18 ⑱ (na)); the timing build of `sim.run` / `board.run` (⑲ (da)); who commits the file (OD-17).
- Any edit of `ARCHITECTURE/`, of ADR text, or of the data repository; any new dependency.
- Starting `claude`, a compiler or any runtime-only resource (D16).

## Follow-ups

- (code, next-task candidate T-0244) Thread the keeper through `check_operation.ask` (fifth thing), `check_ending.carry_out`, `check_seed.check`, `check_tool._perform` (make the keeper, close it when the operation came back, write before judging, `build_log_unwritable` in place of the answer, a raised request to end passes and writes nothing) and `mock_check` (operation and script asked with the keeper; the default script hands nothing), with tests over the mock using a script that hands a log. Before planning it, list the existing tests that pin the four-argument call (`tests/test_check_operation.py`, `tests/test_check_ending.py`, `tests/test_check_seed.py`, `tests/test_check_tool.py`, `tests/test_mock_check.py`, and any test of the default registry) as editable in that task.
- (code, later) `hilclaw/clang_build.py` keeps the log on an `OSError` from moving the artefact or removing its temporary file, or the case is registered (ADR-0078 Consequences slice 4).

## Result
