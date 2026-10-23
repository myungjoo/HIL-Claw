---
id: T-0374
title: Read `coder_model` at the coder call in `hilclaw/coder_call.py` (ADR-0136 code slice 3) - the run's `instance.json` is read after `no_data_root` and before `output_exists`, the four `run_file_*` kinds and the new kind `coder_model_not_stated` join `FAILURE_KINDS`, and the value is handed to the seam `runtime.run`
phase: P1
status: DONE
commitMode: code
coversReq: [NFR-5, FR-5, FR-13, OD-8, OD-23, "#5 A-8"]
dependsOn: [T-0371, T-0372, T-0373]
touchesFiles: [hilclaw/coder_call.py, tests/test_coder_call.py]
estimatedSize: {loc: 90, files: 2}   # non-test: about 15 statement lines and about 70 docstring lines in coder_call.py; the test file is excluded from the cap (D4)
hq: []
---
## Why

ADR-0136 (T-0371, landed as `4423c35`) records the owner's answer to HQ-0041 part (1): the coder model is an instance parameter recorded in `instance.json`. Its Consequences name three code slices:

- Slice 1 (T-0372, PR #214, `d618457`): the member `coder_model` in `hilclaw/instance.py` with its form check and the reader `coder_model_of`.
- Slice 2 (T-0373, PR #215, `cf73e1c`): the Opus default `CODER_MODEL_DEFAULT` filled in by `hilclaw/instance_start.prepare`.
- **This task is slice 3**:

> `hilclaw/coder_call.py`: the read and the kinds of decision 5, and the hand-over of the value to the seam (the form of the hand-over is the code task's); with `tests/test_coder_call.py`. It comes after slice 1, and slice (d) comes after it (decision 4).

Today `hilclaw.coder_call.call` reads no `instance.json`. Nothing tells the seam `runtime.run` which model the coder runs with, so slice (d) (the real runtime that starts `claude -p`) has no value to pass. ADR-0136 decision 4 says slice (d) lands no earlier than this read.

This is PLAN P2-2 (the coder-driver), a checklist item in the first group of the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. P2-5 needs it: the first run's coder calls must run with the recorded model (NFR-5; ADR-0136 decisions 5 and 7).

Planner's judgements (from `main` `15892a6`; **the reviewer is asked to re-check each**):

- **No ADR is needed (DRIVER §9).** ADR-0136 decision 5 fixes:
  - that the request does not change;
  - that the function reads the run's `instance.json` at each call, as a whole, and keeps nothing between calls;
  - the place of the read (right after `no_data_root`, before `output_exists`, so before `no_container_runtime`, creating nothing);
  - the kinds and their order: `run_file_missing`, `run_file_unreadable`, `run_file_invalid`, `run_file_unsupported`, then `coder_model_not_stated`;
  - that the rest of ADR-0126 decision 3's order is unchanged.
  
  Decision 6 fixes that the call passes the recorded value and no other: no fallback, no alias, no default, no rewrite of the file. Consequences slice 3 leaves the form of the hand-over to this code task. This task decides only: the constant's name, the means of the read, the form of the hand-over, the messages, the docstring text and the tests.
- **Data-plane schema change (A-13 BLOCKED reason) does not apply.** No file of the data plane is written or changed. ADR-0136's A-13 reading says `coder_model_not_stated` "names a failure of the call, not a value of the data plane".
- **No open HQ is crossed.**
  - HQ-0040 (Q1 of ADR-0126, the front of the coder call): ADR-0136 Boundaries says "under either form the model reaches the function the same way, from the file". This task adds no front and no tool, and registers nothing.
  - HQ-0041 part (2) (the token axis): not touched.
  - HQ-0032 (PR #186, the start function): not touched.
- **No file overlap with PR #186** (`hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`). No unlanded `claude/T-*` branch touches `hilclaw/coder_call.py` or `hilclaw/run_file_tools.py` (checked on `15892a6`).
- **The seam's signature changes, and that is allowed.** `runtime.run` is the seam of slice (d), which does not exist yet. Nothing in the package calls `call` (its docstring: "Nothing calls it yet"). The only implementations of the seam are the stubs in `tests/test_coder_call.py`.
- **Known risk, accepted.** ADR-0136 is inside its 7-day objection window (notice posted 2026-10-20 on #5). Slices 1 and 2 landed inside it as well. An objection creates a reverting task, and this change is reverted with it. Say so in one line of the commit body.

All verification uses tests on this machine with stub runtimes. No `claude` is started, and no model name is tried against any service (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (executor procedure, resume rule, the 2h30m limit);
  - §5 (task format, `T-NNNN` naming: branch `claude/T-0374-<slug>`, trailer `Task: T-0374`, PR body last line; size cap D4; code-task test rules D12; the language line in `Result`);
  - §3 "BLOCKED 사유" paragraph and §9.
- `CLAUDE.md`, 상시 규칙: "도구 계층 언어 정책"; "브랜치·merge 절차" (code mode; BLOCKED reasons); "테스트 규칙" ① to ⑤; "코멘트 최소화"; "미결은 발명하지 않는다"; "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (procedure) and `.claude/skills/dev-code-review/SKILL.md` (what the reviewer checks).
- **`ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md`**:
  - Status (lines 3-15);
  - decision 3 (lines 54-67: what a valid value is, and that a present invalid member makes the file invalid);
  - decision 4 (lines 69-82: in particular "A valid file without the member states no coder model. No reader substitutes a value, not the default included");
  - **decision 5 (lines 84-92: the read, its place, the kinds and their order)**;
  - **decision 6 (lines 94-104: the Walk-through, rows 4 to 7)**;
  - decision 7 (lines 106-108: what the value is for; how it reaches `claude -p` is slice (d)'s);
  - Alternatives rows (e) and (f) (lines 122-125);
  - Consequences slice 3 (line 132) and the "Less exact, not edited" list (lines 133-140, in particular line 140 on this module's docstring);
  - Boundaries (lines 150-157).
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md` decision 3 (lines 43-59: the request, the result, the failure kinds in the order of their checks) and decision 7 (lines 76-80). Read only.
- `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md` decisions 2 to 4 (lines 30-83: the four reserved kinds and which situation gets which). Read only.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` decision 3 (lines 43-63: how it widened ADR-0019 to `instance.read`). Read only.
- **`hilclaw/coder_call.py`** (265 lines), all of it.
- `hilclaw/run_file_tools.py`: `_INSTANCE_FILE`, `_PARSING` and `read` (around lines 178-231). This function already reads `instance.json` once and raises the four `run_file_*` kinds, with messages that begin with the file's path relative to the data root. Read only.
- `hilclaw/run_files.py`: `relative`, `read_failure` and `reading` (lines 47-110). Read only.
- `hilclaw/case_tool.py` around line 235: an existing caller of `run_file_tools.read(data_root, run_id, "instance.json")`. Read only.
- `hilclaw/tools.py` lines 25-60: the `KIND_RUN_FILE_*` constants and `RESERVED_KINDS`. Read only.
- `hilclaw/instance.py`: the module docstring paragraph "Of the coder model …", the `Instance` field `coder_model`, and `coder_model_of`. Read only.
- `hilclaw/instance_start.py`: `CODER_MODEL_DEFAULT` and the module docstring sentences on it. Read only; it must not be imported by `coder_call`.
- **`tests/test_coder_call.py`** (677 lines), all of it: the helpers `request`, `document`, `FakeRuntime`, the fixtures, `failure`, `assert_nothing_started`, and every test. In particular, read `test_the_kinds_are_names_and_only_two_are_reserved` and `test_the_module_starts_no_process_and_has_no_front`.
- PROCESS/tasks/T-0373-instance-start-coder-model-default.md, `## Acceptance Criteria` and `## Result`: slice 2's choices, including the test value `"claude-test-model-1"`.
- Read only: `.github/workflows/ci.yml` (the jobs; `Coverage gate (hilclaw)`) and `pyproject.toml`.
- Issue #5: every comment after the ADR-0136 §9 notice (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`).
  - If the owner has objected to ADR-0136, or has said anything about how the coder call learns or passes the model, do not start: return BLOCKED ("requirement unclear") and quote the comment.
  - If the owner has answered HQ-0040 (the front of the coder call), do not start: return BLOCKED and quote the answer, because the planner must re-check this slice against it.
  - Any other owner answer does not stop this task; name it in `## Result`.

## Acceptance Criteria

ADR-0136 decisions 5 to 7 fix the rules. The constant's name, the means of the read, the form of the hand-over, the messages, the docstring text and every case the record does not mention are **this task's choices**. State each, with one line of reason, in the commit body, the PR body and `## Result`. Where a criterion below disagrees with the record, **the record wins**: follow the record and say so in `## Result`.

### Files

- Edit only `hilclaw/coder_call.py` and `tests/test_coder_call.py`.
- **Nothing else changes.** In particular these stay as they are:
  - `hilclaw/instance.py`, `hilclaw/instance_start.py` (slices 1 and 2, done);
  - `hilclaw/run_file_tools.py`, `hilclaw/run_files.py`, `hilclaw/tools.py`, `hilclaw/scratch.py`, `hilclaw/bring_in.py`;
  - every file of PR #186;
  - `orchestration/`, `pyproject.toml`, `.github/`, every ADR and the OD register.
- If you conclude another file must change, return BLOCKED with the reason.
- Python, because the module exists in Python. Write that in one line of the commit body and of `## Result`.

### The read (ADR-0136 decision 5)

- `call` reads the run's `instance.json` once per call, under the data root the source returned, **right after the data root is obtained and before the output check** (`_refuse_existing_output`).
- Recommended means: `hilclaw.run_file_tools.read(data_root, run_id, "instance.json")`.
  - It reads the file as a whole, as `instance.read` does.
  - It already raises `ToolFailure` of the four kinds of ADR-0019 decision 2, and its messages begin with the path relative to the data root.
  - If you choose another means (for example `instance.read` with this module's own mapping), the four kinds, their meaning and their messages must be the same as those of `run_file_tools.read`. Say why in `## Result`.
- **Mapping** (from `run_file_tools.read` / `run_files.read_failure`):

  | Situation | Kind |
  |---|---|
  | no `instance.json` (no run directory included) | `run_file_missing` |
  | another failing read | `run_file_unreadable` |
  | a place that holds no regular file, or content that `instance.parse` refuses (including a present `coder_model` that breaks ADR-0136 decision 3) | `run_file_invalid` |
  | another `schema_version` | `run_file_unsupported` |

- **A valid file without the member** raises `ToolFailure` of the new kind `coder_model_not_stated`. Recommended constant: `KIND_CODER_MODEL_NOT_STATED = "coder_model_not_stated"`.
  - Its message names the file by its path relative to the data root and says that it states no `coder_model`. Recommended: `runs/<run_id>/instance.json: states no coder_model`, built with `hilclaw.run_files.relative`.
  - **No default stands in**: no Opus name, no import of `hilclaw.instance_start`, no constant of this module (ADR-0136 decision 4: "No reader substitutes a value, not the default included"; Alternatives row (e)).
- None of these five failures:
  - asks `runtime.available()`;
  - creates a scratch;
  - runs the runtime;
  - lists the attempt directory.
  
  Nothing is created.
- **Order** (ADR-0126 decision 3 with ADR-0136 decision 5): `invalid_request`, `no_data_root`, the four `run_file_*` kinds, `coder_model_not_stated`, then everything else unchanged from `output_exists` on.
  - A bad request is still refused before the source is asked.
  - A failing source is still `no_data_root` before the file is read.
  - A missing or invalid `instance.json` wins over an existing `output`, a missing spec, an invalid spec and no container runtime.
- **Nothing is kept between calls.** A file rewritten between two calls is seen at the second call. The module holds no cache and no module-level state.
- The value is the `str` the file states, unchanged: not lower-cased, not stripped, not resolved, not checked against a list.

### `FAILURE_KINDS`

- Insert, right after `tools.KIND_NO_DATA_ROOT` and before `KIND_OUTPUT_EXISTS`, in this order:
  - `tools.KIND_RUN_FILE_MISSING`;
  - `tools.KIND_RUN_FILE_UNREADABLE`;
  - `tools.KIND_RUN_FILE_INVALID`;
  - `tools.KIND_RUN_FILE_UNSUPPORTED`;
  - `KIND_CODER_MODEL_NOT_STATED`.
  
  Use the `tools` constants, not new string literals, for the four.
- The rest of the tuple and its order do not change. The kinds stay unique, and each is accepted by `tools.ToolFailure`.
- `coder_model_not_stated` is not a reserved kind (it is not in `tools.RESERVED_KINDS`, and `tools.py` does not change).

### The hand-over to the seam (ADR-0136 decision 7, Consequences slice 3)

- `runtime.run` receives the value read in this call. Recommended form: a keyword argument, `runtime.run(scratch_root, coder_model=value)`.
  - A keyword makes a seam that does not take the value fail at once with a `TypeError`. That error propagates after the scratch's removal was tried, as every exception of `runtime.run` but `CoderNotStartedError` already does.
  - If you choose another form, say why in `## Result`.
- The value handed is exactly the one read at this call's read. No fallback, no alias and no second value (ADR-0136 decision 6, last row).
- `runtime.available()` stays as it is: it takes no argument.
- The module still composes no prompt, writes no `claude` flag, starts no process and does not say how the value reaches `claude -p`. That is slice (d)'s (ADR-0136 decision 7).

### What must not change

- These stay as they are:
  - the request (exactly `run_id`, `round`, `candidate`, `attempt`; ADR-0136 decision 5);
  - the result `{"taken": [...], "scratch_removed": bool}`;
  - the signature of `call` (no new argument, no default runtime);
  - every existing kind constant and every existing message byte for byte;
  - `CoderNotStartedError`;
  - the scratch removal rules.
- No failure text holds a path of the data root (the `failure` helper's check covers the new kinds too).
- The module's code (names and string literals; a docstring may cite the record) holds no `claude-` model name and no alias. Use an AST scan of string constants outside docstrings, as T-0372 and T-0373 did.

### Docstrings

CLAUDE.md "코멘트 최소화" applies: no multi-line comments. Docstrings may be as long as needed.

- Module docstring:
  - Name ADR-0136 decision 5 beside ADR-0126 decision 3: the call reads the run's `instance.json` and refuses a run that states no `coder_model`.
  - Describe the seam's `runtime.run` with the new argument: the full model name the run's file states, which the coder's `claude -p` is asked to run with; how it reaches that process is slice (d)'s (ADR-0136 decision 7).
  - Correct the sentences that ADR-0136 Consequences line 140 says stay true only until this slice ("lists the kinds the code has", "reads no `instance.json`"). If any sentence says the call reads no run file, correct it.
  - "What this module is not" gains: it applies no default and resolves no alias; whether the model that actually ran differs from the requested one is not seen here (ADR-0136 Boundaries).
- `call` docstring: the kinds in their new order, with the four `run_file_*` kinds and `coder_model_not_stated` between `no_data_root` and `output_exists`. Add the read to "Nothing is created and the runtime is not run before this point". Describe the new argument of `runtime.run`.
- The `#:` line of `FAILURE_KINDS` still says "in the order of its checks"; cite ADR-0136 decision 5 beside ADR-0126 decision 3.

### Tests (`tests/test_coder_call.py`)

These follow CLAUDE.md 테스트 규칙.

- **Permitted edits of existing tests**, only where the read or the hand-over makes them necessary:
  - a fixture or helper that writes a valid synthetic `instance.json` for `RUN_ID` (with a synthetic `coder_model` of valid form that is not an Opus or Sonnet name, for example `"claude-test-model-1"`). Make it the default of the `data_root` fixture, or of a fixture the existing tests already use, so that existing tests reach the checks they test.
    - Build the content in this test file. Do not import a helper from another test module.
    - Check it with `hilclaw.instance.parse` in one test.
  - `FakeRuntime.run` takes the new argument and records it;
  - `test_the_kinds_are_names_and_only_two_are_reserved`: its reserved set becomes the two plus the four `run_file_*` kinds, and its name may change to say so. Its other assertions (uniqueness, the first two, the last) stay.
  - List every edited existing assertion in `## Result`. No existing assertion is weakened. If an existing test fails for another reason, do not edit it: return BLOCKED with the output.
- **Happy path**: the stub runtime receives `coder_model` equal to the value the file states. Cover several valid values, including `claude-opus-5-5` and a value that is not an Opus name. The result is unchanged.
- **Read per call**: rewrite `instance.json` with another valid `coder_model` between two calls (with the output removed in between, or with two tuples); the second call hands the new value.
- **Negative, each with `assert_nothing_started`, no `output` created, and no data-root path in the message**:
  - no `instance.json` (and no run directory) gives `run_file_missing`;
  - `instance.json` is a directory gives `run_file_invalid`;
  - a symbolic link gives `run_file_invalid` (skip as the existing link test does where links are refused);
  - empty content, content that is no JSON, and content with an invalid `coder_model` (for example `opus`, `default`, `claude-opus-5-5[1m]`, `""`, `5`, `null`) give `run_file_invalid`;
  - another `schema_version` gives `run_file_unsupported`;
  - a read that fails with an `OSError` other than "not there" gives `run_file_unreadable` (monkeypatch, as the existing spec-read tests do);
  - a valid file without `coder_model` gives `coder_model_not_stated`, the runtime is never asked (`available` not called), and no default is handed.
- **Branches (order)**:
  - a bad request still wins over a missing `instance.json`, and the source is not asked;
  - a failing source is still `no_data_root`, and the file is not read;
  - a missing `instance.json` wins over an existing `output`;
  - a missing `instance.json` wins over a missing spec and an invalid spec;
  - `coder_model_not_stated` wins over an existing `output`, a missing spec and no container runtime.
- **Seam**: a runtime whose `run` takes only `scratch_root` gets a `TypeError` that propagates, and the scratch's removal was tried (as `test_another_exception_of_run_propagates_after_removal` does).
- **Module checks**:
  - `FAILURE_KINDS` holds the five new kinds at positions 2 to 6, in the order above;
  - `KIND_CODER_MODEL_NOT_STATED == "coder_model_not_stated"` and it is not reserved;
  - the module does not import `hilclaw.instance_start`;
  - no string constant of the module's code outside docstrings starts with `claude-` or equals `opus`, `sonnet` or `default`;
  - the existing "starts no process and has no front" test stays unedited and passes.
- `hilclaw/` line and function coverage stays at or above 80 %. `hilclaw/coder_call.py` should stay at 100 %.
- Run locally: `python -m pytest`, `ruff check` and `ruff format --check`. CI must be green before the squash-merge.

### Process

- Code mode (CLAUDE.md A-13): branch `claude/T-0374-<slug>`; Draft PR with `T-0374` in the title; context-isolated reviewer cycle (at most 7 rounds) to Approve; CI green; `gh pr merge --squash --body` with the PR body, whose last line is `Task: T-0374`; delete the branch.
- No `claude` is started at any point (D16).

## Out of Scope

- Slice (d) of ADR-0049: the real runtime, its image, container flags, sign-in, permission mode, prompt, time limit and output stream, and how the value reaches `claude -p` (flag, environment variable or other).
- What the model that actually ran was (`modelUsage`, remapping, fallback; ADR-0136 Boundaries; runtime acceptance items (xxxi) and (xxxii), HQ-0052).
- The token axis (HQ-0041 part (2)) and `ARCHITECTURE/SpendAxes.md`.
- Either front of the coder call (HQ-0040): no tool, no registration, no entry point.
- The models of every other agent.
- `hilclaw/instance.py`, `hilclaw/instance_start.py`, `hilclaw/run_file_tools.py` and every file of PR #186.
- Every less-exact sentence of earlier records: the ADR-0136 Consequences list, including ADR-0126 decision 3's table, which gains these kinds, and ADR-0019 decision 2's "only at the lookup or the selection". If you find another, list it in `## Result` and do not edit it (D18 hold).

## Follow-ups

- ADR-0049 slice (d) (planner's view, next P2-2 piece): the real runtime behind `runtime.available()` / `runtime.run(scratch_root, coder_model=...)`. Its design points (image, flags, sign-in, permission mode, prompt, time limit, output stream, how the model reaches `claude -p`) are left by ADR-0126 Consequences and ADR-0136 Boundaries to a later record, so the planner must check whether a record (ADR) task comes first and whether any point is owner-only.
- Carried from T-0370, for the `orchestration/round-manager.md` slice that replaces the explicit stop (not this task): "One round at most" still says the session ends after the write that ends its round, while the closing steps now put `run.commit` after it.

## Result

- **Status**: DONE. PR #216 (https://github.com/myungjoo/HIL-Claw/pull/216) squash-merged as `91fec46`; branch `claude/T-0374-coder-call-reads-coder-model` deleted.
- **Review**: 2 rounds with the context-isolated `dev-reviewer`; Approve in both. Round 1 re-checked the planner's judgements (no ADR needed, no data-plane schema change, no open HQ crossed, no overlap with PR #186, seam signature change allowed) and raised two optional nits: three failure tests did not check the `runs/<run_id>/instance.json: ` prefix (fixed in `5cb84be`); the long `#:` line above `FAILURE_KINDS` (not changed, ruff clean). Round 2 raised one optional nit on `FakeRuntime(available=False)` in an order test (not changed; the order is still shown and another test checks the runtime is never asked).
- **Language**: Python, because the module exists in Python.
- **Choices**:
  - The read uses `run_file_tools.read(data_root, run_id, "instance.json")`, which already raises the four `run_file_*` kinds with relative-path messages.
  - Constant `KIND_CODER_MODEL_NOT_STATED = "coder_model_not_stated"`, not reserved; `tools.py` unchanged. Message `runs/<run_id>/instance.json: states no coder_model`, built with `run_files.relative`.
  - Hand-over by keyword `runtime.run(scratch_root, coder_model=value)`; a seam that does not take it fails with `TypeError` after the scratch removal was tried. `runtime.available()` unchanged.
  - `_stated_coder_model` runs right after `data_root_source.obtain`, before `_refuse_existing_output`. `FAILURE_KINDS` gains the four `run_file_*` kinds and `KIND_CODER_MODEL_NOT_STATED` at positions 2 to 6; the rest is unchanged.
  - Docstrings cite ADR-0136 decision 5 beside ADR-0126 decision 3; no default, no alias; how the value reaches `claude -p` is slice (d)'s (decision 7). The commit body states the change is reverted with ADR-0136 on an owner objection within the 7-day window.
- **Files**: only `hilclaw/coder_call.py` and `tests/test_coder_call.py`.
- **Edited existing tests** (none weakened): the `data_root` fixture writes a valid synthetic `instance.json` with `coder_model` `"claude-test-model-1"`; `document()` takes its hw record from a new module constant `HW`; `FakeRuntime.run` takes and records `coder_model`; `test_a_spec_whose_id_names_another_tuple_is_invalid` writes `instance.json` for its run id; `test_the_kinds_are_names_and_only_two_are_reserved` renamed `..._only_two_and_the_run_file_four_are_reserved` with the four `run_file_*` kinds added to its reserved set.
- **New tests**: happy path with four model names; re-read at every call; `run_file_missing` (file and run directory); `run_file_invalid` (directory, symlink, empty, non-JSON, `[]`, six bad `coder_model` values); `run_file_unsupported`; `run_file_unreadable`; `coder_model_not_stated` with the runtime never asked; the failure order against bad request, failing source, existing `output`, missing/invalid spec and no container runtime; the seam `TypeError`; kind positions, the constant, and an AST scan (no `instance_start` import, no model-name string constants).
- **Verification**: `python -m pytest` 25015 passed, 728 skipped; `ruff check` and `ruff format --check` clean; coverage 97 % for `hilclaw/`, 100 % for `hilclaw/coder_call.py`. CI on `5cb84be`: all 6 checks green. No `claude` started; no model name tried against any service (D16).
- **Owner answers on #5**: none after the ADR-0136 notice; no objection and no HQ-0040 answer.
- **Follow-ups**: ADR-0049 slice (d), the real runtime behind `runtime.available()` / `runtime.run(scratch_root, coder_model=...)` (the planner checks whether an ADR task must come first). Less-exact sentences in earlier records stay in the D18 hold line from T-0371 (notably ADR-0126 decision 3's table now lacks the five kinds).
