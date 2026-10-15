---
id: T-0206
title: Add hilclaw/mock_run.py, the mock's operation and default script of sim.run / board.run (ADR-0066 decisions 2 to 4)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, OD-13]
dependsOn: [T-0204, T-0205]
touchesFiles:
  - hilclaw/mock_run.py
  - tests/test_mock_run.py
estimatedSize: {loc: 150, files: 1}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` have six records: ADR-0061 (split), ADR-0062 (call identity), ADR-0063 (result members), ADR-0064 (timing seed), ADR-0065 (the form between the tool function and an operation) and ADR-0066 (the mock's side of that form; landed by T-0205 as `edf70d5`). Code exists for the objective admission (`hilclaw/run_objective.py`), the step values (`hilclaw/run_identity.py`), the result builder (`hilclaw/run_result.py`), the seed draw (`hilclaw/run_seed.py`), the judging of a report (`hilclaw/harness/timing.py` `judge_report`), the timing parameters (`hilclaw/run_parameters.py`) and the check of an operation's answer (`hilclaw/run_operation.py`).

ADR-0066 Consequences, "Code slice made possible", names the next code slice: **the mock's operation and default script of the run tools, and their tests**, in the manner of `hilclaw/mock_check.py` for `correctness.check`. It notes that `hilclaw/mock_backend.py` and its tests pin the call of an operation at two arguments and that of a script at three, "so that task names those assertions as permitted edits or uses another module". This task **uses another module** (`hilclaw/mock_run.py`), as `mock_check.py` did, and does not touch `mock_backend.py`. T-0205 Follow-ups and the 2026-10-15 journal name this as the next task. No ADR is needed: every design point is fixed by ADR-0066 or left to the code by it (ADR-0066 decisions 2 and 4, "What is fixed and what is the code task's").

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention: branch `claude/T-0206-<slug>`, `Task: T-0206` trailer in commits and as the last line of the PR body, size cap, D12 test rules).
- `CLAUDE.md` sections "상시 규칙" — the test rule (D12 ①-⑤), the language policy (record the language choice and its reason in one line of the commit body), the branch/merge procedure (code mode: Draft PR, review cycle, CI green, self squash-merge, delete branch), the comment-minimisation rule, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- `ARCHITECTURE/decisions/ADR-0066-od18-run-tools-mock-script.md` (165 lines): Status, Decision §1 to §6 (lines 22-94; §2 how the operation asks its script and "What is fixed and what is the code task's"; §3 the default answer and what it depends on; §4 the report lines, the reading of `n_min` from the source constant, the figure none, and "What is fixed and what is the code task's"; §5 what a script of a test can express), the Walk-through (lines 96-110), Limits (lines 112-121) and Consequences ("Code slice made possible", line 141).
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md` decisions 2 to 4 (the four things an operation is called with; the point is not handed; forms (A) and (B)).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` decisions 7 and 8 (lines 65-100; the replay and the report form).
- `hilclaw/mock_check.py` (whole; the analogue: `_Operation`, `operation`, `default_script`, the docstring structure "Choices that are this module's own" / "What the module does not do").
- `hilclaw/mock_backend.py` (whole; read only — `NAME`, the two-argument operation; not to be changed).
- `hilclaw/run_operation.py` lines 1-60 and `ask` (lines 332-393 of the file as it is today: what counts as (A)).
- `hilclaw/run_parameters.py` (whole).
- `hilclaw/harness/timing.py` lines 1-60 (the report form) and `parse_report` / `judge_report` (lines 193-253); `hilclaw/harness/measurement.py` lines 40-112 (`N_MIN`, `CV_MAX`, `stopping_state`).
- `hilclaw/backends.py` lines 30-60 (`HW_TOOLS`).
- `tests/test_mock_check.py` (skim the structure: operation pass-through tables, the default-script tests, the import check and the public-names check).

## Acceptance Criteria

1. **New module `hilclaw/mock_run.py`** (Python, as `mock_check.py`; the module name is the executor's choice, stated in the docstring if changed — keep `touchesFiles` in sync). Its module docstring cites ADR-0066 (a decision cited by number alone being one of that record), says which decisions it renders (2 to 4), lists every choice that is the module's own and no rule of a record, and says what the module does not do: no backend, no backend table, bound to no registry (ADR-0066 decision 5: when the default registry holds these operations is not decided); no fault injection (OD-18 ⑧, open); no tool function and no registration (⑲); no judging, no result, no line appended, no spend; nothing read at the output path; no clock, random source, counter, file or environment variable; no process; nothing kept between calls. It does not edit `hilclaw/mock_backend.py` or its tests.
2. **The operation** (ADR-0066 decision 2), e.g. `operation(tool, script)`:
   - `tool` is `"sim.run"` or `"board.run"`; anything else raises before anything is built (`TypeError` for a non-`str`, `ValueError` for any other string, `"correctness.check"` and `"profiler.collect"` included — the executor may choose the exact split and states it). `script` that is not callable raises `TypeError`. Building asks the script nothing.
   - The operation returned is called as `operation(request, hw_profile, parameters, output_path)` with exactly these four positional arguments (the shape `hilclaw.run_operation.ask` calls). It asks the script **exactly once** as `script(tool, request, hw_profile, parameters, output_path)` with the called tool and the four objects as the same objects, none derived, replaced, left out or added, and returns the object the script returned, whatever it is. It looks at none of the four and not at the answer, and catches nothing: a `hilclaw.tools.ToolFailure` of any kind and any other `BaseException` pass through unchanged.
   - A readable `repr` naming the mock and the tool, as `mock_check._Operation`.
   - Whether one script callable serves both tools, and the positions of the five things, are the module's own choices and are stated as such (ADR-0066 decision 2 leaves them to the code).
3. **The default script** (ADR-0066 decisions 3 and 4), e.g. `default_script(tool, request, hw_profile, parameters, output_path)`:
   - Returns exactly the pair `(report, None)`, a `tuple` of length 2, where `report` is exactly `bytes` holding the ASCII lines `resolution_ns 1`, then `N_MIN` lines `interval_ns 1000000`, then `stop converged`, each ended by one LF, and nothing else. `N_MIN` is read from `hilclaw.harness.measurement.N_MIN` of the same source commit (decision 4: "`n_min` is read from the source commit's constant"; which code reads it is the code task's). `CV_MAX` is not read.
   - Depends on nothing it is asked with: none of the five arguments is read, checked, converted or modified, whatever its type (decision 3: "The answer depends on nothing the script is asked with"). It raises nothing for any argument values, never answers (B), never raises a `ToolFailure` (decision 3, last bullet). The two tools get equal answers.
   - Whether the report is built once at import or per call is the executor's choice; if built at import, a test asserts that `N_MIN` and the report agree.
4. **New test file `tests/test_mock_run.py`** (D12 ②-④), covering at least:
   - happy: for each of the two tools, the operation asks the script once with the tool and the four objects as the same objects (identity checks) and returns the script's object as the same object; the default script's pair equals the exact expected bytes and `None`; `hilclaw.run_operation.ask(operation("sim.run", default_script), ...)` with a `TimingParameters` returns `Reported(report, None)` — the same for `board.run`.
   - the ADR-0066 decision 4 agreement: `hilclaw.harness.timing.judge_report(report, sample_form=..., n_max=...)` is completed and converged with `N_MIN` intervals of 1000000 and resolution 1, for both sample forms (`timing.SAMPLE_FORMS`) and for `n_max` in at least `{N_MIN, 10, 2**40}`; `parse_report` reads it.
   - branch: equal answers for both tools and for different requests, hw_profiles, timing parameters (different seed, dimensions, `n_max`, sample form) and output paths, including odd values (`None`, an object whose attribute access or `__eq__` raises, a path that does not exist) — showing nothing is read; the script answers of ADR-0066 decision 5 pass through the operation unchanged and `run_operation.ask` then classifies them: (B) string, a pair with a figure, an answer of neither form (→ `run_operation.OperationAnswerInvalid`), a `ToolFailure` (same object), `KeyboardInterrupt` / `SystemExit` (same object).
   - error/negative: non-callable script → `TypeError`; tool not `str`, an unknown string, `"correctness.check"`, `"profiler.collect"` → the documented error; building asks the script nothing; an operation called with three or five positional arguments or with a keyword → `TypeError` and the script is not asked.
   - No file written (`tmp_path` + `monkeypatch.chdir`); the module's imports are exactly the ones its docstring names; its public names are exactly the documented ones.
5. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally; the coverage gate of `hilclaw/` (line >= 80%, function >= 80%) holds; the test-existence check finds `tests/test_mock_run.py`; CI green on the PR.
6. Size: non-test change <= 300 LOC and <= 5 files (expected about 150 LOC in one non-test file, most of it docstrings). If exceeded, split per DRIVER §5 and record the split in Follow-ups.
7. No data-plane schema change: no member of a result, a line of `events.ndjson`, `STATE.json`, `instance.json`, a spec or a result file is added, removed or changed; no value of `error.kind` is added. If the design seems to need one, stop and return BLOCKED.
8. Nothing in this task starts `claude`, builds or runs a kernel, starts a compiler, or needs a board or an API key (D16). The default script starts no process.
9. Code mode per CLAUDE.md A-13: branch `claude/T-0206-run-tools-mock-script-code`, Draft PR whose title contains `T-0206` and whose body ends with `Task: T-0206`, fresh-context reviewer cycle (dev-code-review), CI green, `gh pr merge --squash --body <PR body>`, branch deleted. Fill `## Result` with the commit/PR, review rounds, the language line and any follow-ups.

## Out of Scope

- Any change to `hilclaw/mock_backend.py`, `hilclaw/mock_check.py`, `hilclaw/backends.py`, `hilclaw/run_*.py`, `hilclaw/harness/` or their tests; binding the operations into a backend, a backend table or the default registry.
- The tool functions of `sim.run` / `board.run`, their registration, start/end lines, the input schema and description; what the tool function does with a `ToolFailure` an operation raises and which backend kinds may stand on an end line (OD-18 ⑲ (가) to (라)); the spend (OD-2, OD-19).
- Fault injection in a live session (OD-18 ⑧); the operation of `cpu_standin` (OD-14); `profiler.collect`.
- Any `ARCHITECTURE/` edit, including the R7 minor T-0205 left on ADR-0066 decision 4 (iii) and the integrator's "less exact" sentence list of ADR-0066 Consequences.
- Any new dependency.

## Follow-ups

## Result
