---
id: T-0484
title: Add the tool `hypotheses.write`, the `technique-selector` definition and the round >= 1 selection steps of the Round-Manager (ADR-0132 Consequences slices 1 to 3; PLAN P2-6)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-11, FR-17, OD-23, OD-30, OD-18, S0, S1, "PLAN P2-6", "PLAN P2-1"]
dependsOn: []
touchesFiles:
  - hilclaw/hypotheses_write_tool.py
  - tests/test_hypotheses_write_tool.py
  - hilclaw/tools.py
  - hilclaw/hypotheses_file.py
  - hilclaw/hypotheses_cases.py
  - hilclaw/turn_permissions.py
  - hilclaw/turn_definition.py
  - orchestration/agents/technique-selector.md
  - orchestration/round-manager.md
  - tests/test_turn_definition.py
  - tests/test_turn_permissions.py
  - tests/test_caller_check.py
  - tests/test_tools.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_mcp_front.py
  - tests/test___main__.py
  - tests/test_default_registry_schemas.py
estimatedSize: {loc: 450, files: 9}   # tests excluded from the cap (DRIVER §5, D4/D20)
hq: []
---
## Why

PLAN P2-6 is "가설 레코드와 판정": the technique selection records a structured hypothesis record, and this reaches the layer-1 prompts (P2-1, P2-3). In the stated P2 order (P2-1 to P2-4, P2-6, P2-7, then P2-5), P2-1 cannot go on: its next work, the steps of a round >= 1, needs the selection side first (T-0483 Follow-ups). This is checklist work, so the D18 rule for work outside the checklist does not apply. P2-5 needs it: a first run's round 1 needs a hypothesis record before any spec write or coder call, and a case needs that record (ADR-0133 decision 4).

ADR-0132 (T-0361, landed on `main` 2026-10-26) decides the selection side for the runs of ADR-0120 decision 1. Its Consequences list four code slices. Under DRIVER §6 "task 단위" ③ (D20) the slices of one ADR are combined into one task when they fit the size cap together. This task holds slices 1 to 3:

1. **Slice 1**: the registry tool `hypotheses.write` (decision 4): a new module of `hilclaw/` and its test file, registered in `default_registry`, with the docstrings of `hilclaw/hypotheses_file.py` and `hilclaw/hypotheses_cases.py` brought up to date.
2. **Slice 2**: `orchestration/agents/technique-selector.md` (decision 7), with a test of its `tools` set. `turn_permissions` and the caller check take it up with no code change (ADR-0139 decision 3; ADR-0146 decision 3).
3. **Slice 3**: the steps of decision 6 in `orchestration/round-manager.md` for a round >= 1, and `mcp__hilclaw__hypotheses_read` in its tool sentences and in `ROUND_MANAGER_TOOLS`.

Slice 4 (the lookup read tool in the selector's list, and the selector recording `cases_read`) waits on the record of ADR-0132 decision 5 (PLAN P2-7) and is not in this task.

No record leaves a design choice of these slices open beyond what ADR-0132 decision 4 "Left to the code slice" names (the module, the description and input schema, and the encoding of `record`). This task makes those three choices. If you find another choice open, stop and return BLOCKED with the reason. Do not write an ADR.

Runtime acceptance: ADR-0132 items (xxiii) and (xxiv) become checkable once slices 1 and 2 land. The planner returned them to the driver with this task (source T-0361 / ADR-0132), so do not return them again. Name a new runtime acceptance item in `## Result` only if your change creates a fact that only a live session can confirm and that (xxiii), (xxiv) and the items of ADR-0139 and ADR-0146 do not cover (DRIVER §8, D22).

## Required Reading

Line numbers are those of `main` at `769b2e9d`; the text wins. Read Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 73: executor procedure, landed check, resume rule, time limit) and **§5** (lines 87-116: task format, naming, size cap D4/D20, trailers, the test rules D12, the pinning-list rule D21).
- CLAUDE.md, the whole file. Above all: "개발 드라이버와 런타임의 구분" (no `claude`, container or board is started on this machine; tests use stubs and fixture files only), "테스트 규칙", "브랜치·merge 절차" (this task is code mode), "코멘트 최소화", "도구 계층 언어 정책".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **The record**: ARCHITECTURE/decisions/ADR-0132-od23-first-case-selection.md, the whole file (157 lines). Above all decisions 3, 4, 6 and 7, the Walk-through and Consequences.
- **Records it cites, the parts named**:
  - ADR-0128 decision 6 (`verdicts.write`: the pattern of a writing registry tool) and decision 7 (the evaluator's definition);
  - ADR-0133 decision 3 (`case.write`'s `round_not_current` precondition);
  - ADR-0015 decisions 2 to 4 (reserved kinds, the data root never a request member, `run_id`);
  - ADR-0019 decisions 2 and 3 (the `run_file_*` kinds);
  - ADR-0073 decisions 1 to 3 (the lookup and the rules between files);
  - ADR-0112 decisions 1 to 3 (rules of conduct of the selection role);
  - ADR-0123 decisions 2 and 4 (a delegation names the run id and no place);
  - ADR-0129 decisions 3 and 4 (`hypotheses.read` and its kinds);
  - ADR-0139 decisions 3 to 5 (the derived pre-approved list; built-in set);
  - ADR-0143 decisions 2 and 7 (every end calls `run.commit`; the stop's commit);
  - ADR-0146 decisions 2, 3 and 6 (the caller check).
- **Code (models and the modules this task uses)**:
  - `hilclaw/verdicts_tool.py`: the module docstring (encoding rule of `record`, lines 16-21), `definition`, `_input_schema`, `_checked`, `_write`. This is the model for the new module.
  - `hilclaw/case_tool.py` `_write` (from line 224): the `round_not_current` check over `run_file_tools.read(data_root, run_id, "STATE.json")`.
  - `hilclaw/hypotheses_tool.py` (`hypotheses.read`, its kinds).
  - `hilclaw/hypotheses_file.py`: the module docstring, `parse`, `final_name`, `write` and its errors (`InvalidHypothesisFileError`, `UnsupportedVersionError`, `NameTakenError`, `WrittenFormError`).
  - `hilclaw/hypotheses_cases.py`: `check`, `check_run`, `MismatchError`.
  - `hilclaw/case_lookup.py` `find` and `lookup` (lines 101-170).
  - `hilclaw/run_file_tools.py` `read` (line 197); `hilclaw/data_root_source.py` `obtain`.
  - `hilclaw/tools.py` `default_registry` (from line 182) and its docstring.
  - `hilclaw/turn_permissions.py`: the module docstring and `ROUND_MANAGER_TOOLS` (line 96).
  - `hilclaw/caller_check.py`: the module docstring (read only; no code change expected).
  - `hilclaw/turn_definition.py`: the module docstring, lines 1-78.
- **Definition (whole)**: `orchestration/round-manager.md`; `orchestration/agents/evaluator.md` (the model for the new file: it holds `Read`, `Grep`, `Glob` and typed tools, and corrects and resends on `invalid_request`/`verdicts_mismatch`); `orchestration/agents/coder-driver.md`; `orchestration/agents/experiment-runner.md`.
- **Tests (whole)**: `tests/test_verdicts_tool.py` (the model for the new test file), `tests/test_turn_definition.py`, `tests/test_turn_permissions.py`, `tests/test_caller_check.py`, `tests/test_default_registry_schemas.py`.

## Acceptance Criteria

1. **Slice 1: the tool `hypotheses.write`** in a new module `hilclaw/hypotheses_write_tool.py` (the module is this task's choice; a different name is allowed if you state why in `## Result` and update `touchesFiles` accordingly). It follows ADR-0132 decision 4 exactly:
   - `NAME = "hypotheses.write"`; MCP name `hypotheses_write`. A `definition(source)` returning one `tools.ToolDefinition`, raising `TypeError` for a source that is not callable, as `verdicts_tool.definition` does.
   - **Request**: exactly `run_id` and `record`, both required; any other member, or one missing, is `invalid_request`. The input schema states `run_id` with the run-id pattern used by the other tools and `record` as `{"type": "object"}`, `additionalProperties: false`.
   - **Encoding of `record`**: the fixed rule of `verdicts_tool` (`json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)`, then one line feed, UTF-8 without BOM). A value `json.dumps` refuses, or a string UTF-8 cannot encode, is `invalid_request`. State the rule in the module docstring.
   - **Checks, in this order, each with its kind**:
     1. the request, then the bytes by `hilclaw.hypotheses_file.parse` (every refusal of `parse`, round 0 and another `schema_version` among them), then the record's `run_id` equal to the request's: `invalid_request`;
     2. the data root: `no_data_root` (`data_root_source.obtain`), asked only after check 1 passed;
     3. the run's `STATE.json` by `run_file_tools.read`: the four `run_file_*` kinds; its `round` not equal to the record's `round`: `round_not_current`, reusing `case_tool.KIND_ROUND_NOT_CURRENT`;
     4. **only when the record's `cases_read` holds at least one entry**: the run's `instance.json` by `run_file_tools.read` (the four `run_file_*` kinds); then `case_lookup.find` with the stated `hw_profile`, the stated `op_signature` record (or `None`) and the run id, where any `OSError` is `cases_unreadable`; then `hypotheses_cases.check`, where `MismatchError` is `cases_mismatch`. The lookup's reports are not judged (ADR-0132 decision 4 names no kind for them);
     5. the write by `hypotheses_file.write`: `NameTakenError` is `hypotheses_exist` (nothing replaced, the file under the name not read); any other `OSError` is `hypotheses_not_written`.
   - **Result**: the empty object `{}`.
   - New kind constants `KIND_CASES_UNREADABLE = "cases_unreadable"`, `KIND_CASES_MISMATCH = "cases_mismatch"`, `KIND_HYPOTHESES_EXIST = "hypotheses_exist"`, `KIND_HYPOTHESES_NOT_WRITTEN = "hypotheses_not_written"`. No `hypotheses_*` kind of ADR-0129 is reused. Every message starts with the file's path relative to the data root where a file is concerned, as in `case_tool`.
   - Nothing is created before check 5. Not journaled: it appends no line to `events.ndjson`, selects no backend and takes no lock.
   - It holds no rule beyond `parse` and (check 4) `hypotheses_cases.check`: not ADR-0112's rules, not ADR-0075 decision 3's rules between files, not `candidates` against the specs, not a `ref` against the tree.
   - The module docstring states what ADR-0132 decision 4 states, citing it, in the style of `verdicts_tool.py`; no multi-line comments in code (CLAUDE.md).
2. **Registration**: `default_registry` in `hilclaw/tools.py` registers `hypotheses_write_tool.definition(data_root_source)`. Its docstring gains one sentence: `hypotheses.write` (`hilclaw.hypotheses_write_tool.definition`, ADR-0132 decision 4), with which the technique-selector writes a round's `decision/hypotheses.json`. Building the registry still calls no source and imports no NumPy.
3. **Docstrings made less exact by slice 1** (ADR-0132 Consequences): in `hilclaw/hypotheses_file.py`, "and is no tool" and "Which agent writes the file and when ... are open" now say that `hypotheses.write` calls `write` for the technique-selector (ADR-0132 decisions 2 and 4); what follows a taken name for that tool is `hypotheses_exist`; the second-write meaning stays open (OD-17). In `hilclaw/hypotheses_cases.py`, "It does not decide who calls it or when, whether a write is refused on a mismatch" now says `hypotheses.write` holds `check` before the write for a record with `cases_read` and refuses a mismatch (ADR-0132 decision 4); the carriage of the lookup's reports stays open. Change no code of either module.
4. **Slice 2: `orchestration/agents/technique-selector.md`** per ADR-0132 decisions 3, 5 and 7:
   - **Frontmatter**: exactly the keys `name`, `description` and `tools`. `name` is `technique-selector`. `tools` is exactly `Read, Grep, Glob, mcp__hilclaw__state_read, mcp__hilclaw__instance_read, mcp__hilclaw__hypotheses_read, mcp__hilclaw__checks_read, mcp__hilclaw__hypotheses_write`. No `model`, `permissionMode`, `background` or other member. No `Write`, `Edit`, `NotebookEdit`, `Bash`, `Agent`, `Skill`, `mcp__hilclaw__timings_compare`. LF line endings.
   - **Body**, in the sections of `evaluator.md` / `coder-driver.md` (what you are given, fixed rules, your report). It states, each with its citation:
     - the delegation message names the run id and the round, and no place (decision 7; ADR-0123 decision 2);
     - every request carries the run id it was given;
     - it writes the hypothesis record of the round it was given, and nothing by any means but `mcp__hilclaw__hypotheses_write`;
     - on `invalid_request` or `cases_mismatch` it corrects the record and sends it again; on any other kind it sends nothing further, reports the kind and ends;
     - it writes no `cases_read` and no `case` basis entry while no lookup tool is in its list (decision 5);
     - it keeps ADR-0112 decisions 2 and 3 as rules of conduct: a system hypothesis in every round where one can be recorded, and the owner's pace for untested written inputs. State these as ADR-0112 states them; do not paraphrase beyond the record;
     - it requests no check, measurement, spec or coder call;
     - the report: one final text message, one line per tool request naming the tool and the result or the failure kind, and for a written record one line per hypothesis `id` with its `tested_by`.
   - Use no wording that the records do not support.
5. **Slice 3: the Round-Manager** (`orchestration/round-manager.md`), per ADR-0132 decision 6 and decision 7 last bullet:
   - **New round >= 1 steps after step 1** (`key.store`), numbered beside the round-0 steps as you choose (for example steps marked "**Round >= 1 only.**"); the sentence "In a round ≥ 1 there is no step 2" is rewritten to fit:
     - delegate to `technique-selector` with the `Agent` tool and wait for its report; the message names your run id and the round, and no place (ADR-0132 decisions 6 and 7; ADR-0123 decisions 2 and 4); report what it reports in one line;
     - when it has returned, whatever its report says, call `mcp__hilclaw__hypotheses_read` with your run id and the round;
     - when that call fails with any kind, report the kind in one line and come to the stop (ADR-0132 decision 6; ADR-0143 decisions 2 and 7);
     - when it returns the round's record, the round's further steps (spec write, coder delegation) are not yet defined: come to the stop and report in one line that the following steps of round `<round>` are not yet defined.
   - **"Your run"**: widen the `Agent` bullet to the `technique-selector` delegation; add a bullet that `mcp__hilclaw__hypotheses_read`, your run id as `run_id`, is used only to read the round's hypothesis record in that step (ADR-0132 decision 6; ADR-0129 decision 3); add "Do not call `mcp__hilclaw__hypotheses_write` yourself" (ADR-0132 decision 3). Write no hypothesis record by any other means.
   - **The stop** paragraph: in rounds >= 1 it now follows the selection steps (a failed read, or the read record with no further step defined), not step 1. Its `run.commit`, "write nothing further" and "the round is not ended" parts stay. "Later slices of the definition replace this stop in rounds ≥ 1" stays true and stays. The first sentence of "The closing steps of a round" stays correct; check it.
   - The list of ends in "The end of a session" stays correct; check it, change it only if the new steps make it wrong.
6. **`ROUND_MANAGER_TOOLS`** in `hilclaw/turn_permissions.py` gains `"mcp__hilclaw__hypotheses_read"` (ADR-0132 decision 6, citing ADR-0139 decision 3). No other code change in `turn_permissions.py`, `caller_check.py` or `budget_check.py`. If a test shows the derivation or the caller check does not take up the new agent file unchanged, stop and return BLOCKED with the reason. Update a docstring sentence of `turn_permissions.py` or `caller_check.py` only where it lists the main session's tools or the agents and is now wrong.
7. **`hilclaw/turn_definition.py` docstring**: the *prompt* bullet says that in a round >= 1 a turn delegates the selection to the technique-selector after the key store, reads the round's record with `hypotheses.read`, and then stops (the later steps are not yet defined); the roster paragraph adds the technique-selector's definition (ADR-0132 decision 7); "Not done here" is narrowed accordingly. No code change.
8. **Tests** (code mode; D12 applies; test files are outside the size cap):
   - **New `tests/test_hypotheses_write_tool.py`**, with fixture files under `tmp_path` only:
     - happy path: a valid round-1 record with no `cases_read` is written byte for byte by the fixed encoding and returns `{}`; through `tools.call(default_registry(...), "hypotheses.write", ...)` and the MCP name `hypotheses_write`;
     - an `injected` entry with its `injection` is admitted as `hilclaw.hypotheses` admits it;
     - every kind in its order, one test each, and that an earlier check wins over a later one: a missing or extra member, a non-object `record`, a NaN in `record`, a lone surrogate, a round-0 record, another `schema_version`, a record whose `run_id` differs from the request's (all `invalid_request`, the source never asked); `no_data_root`; each of the four `run_file_*` kinds for `STATE.json`; `round_not_current` for a record of another round;
     - check 4 skipped when `cases_read` is absent or empty (no `instance.json` needed, nothing of `db/` read); check 4 made: a record whose `cases_read` names a stored valid case and whose `case` basis names one of its hypothesis ids is written; a `cases_read` naming no stored case is `cases_mismatch`; a `case` basis naming an id the case does not hold is `cases_mismatch`; a missing or invalid `instance.json` gives its `run_file_*` kind; an `OSError` in the lookup (for example by monkeypatching the listing) is `cases_unreadable`;
     - a taken name is `hypotheses_exist` and the existing file is unchanged; another `OSError` of the write (monkeypatched) is `hypotheses_not_written`;
     - nothing is created by any refused call before check 5;
     - `definition` with a non-callable source raises `TypeError`;
     - every public name of the module is exercised.
   - `tests/test_turn_definition.py`: the technique-selector frontmatter (key set, `name`, exact `tools` set, every `mcp__hilclaw__` name served by `default_registry`, no forbidden tool, no `\r`); the body names `hypotheses_write`, `invalid_request`, `cases_mismatch`, `tested_by`, and the rule of no `cases_read`; the prompt delegates to `technique-selector` in a round >= 1, calls `hypotheses_read` after it, comes to the stop on a failed read, and still says the later steps of a round >= 1 are not yet defined; `hypotheses_write` appears in the prompt only in a sentence starting "Do not call " (as `board_run` is checked); negative: the prompt does not let a round >= 1 reach a spec write or coder delegation.
   - `tests/test_caller_check.py`: with the real definition put by the existing fixture, a `mcp__hilclaw__hypotheses_write` call by agent type `technique-selector` is let through; the same call from the main session and from `evaluator`, `coder-driver` and `experiment-runner` is refused; `mcp__hilclaw__hypotheses_read` from the main session is now let through (it is in `ROUND_MANAGER_TOOLS`).
   - **Pinning assertions you will touch** (DRIVER §5 D21 allows these edits as far as they reflect the new tool, the new agent file and the new `ROUND_MANAGER_TOOLS` entry; list each in the PR body):
     - the registry name lists: `tests/test_tools.py` (the list near line 490), `tests/test_blob_tools.py` `test_the_default_registry_holds_the_definitions` (line 176) and `test_the_mcp_front_lists_the_blob_tools_among_the_fixed_set` (line 707), `tests/test_check_definition.py` (lines 130, 430, 467, 757), `tests/test_mcp_front.py` (the map near line 28 and lines 466, 516, 969, 1070), `tests/test___main__.py` (the list near line 27 and the docstring at line 218);
     - `tests/test_default_registry_schemas.py` `ACCEPTED`: one accepted request for `hypotheses.write`;
     - `tests/test_turn_permissions.py`: `FIXED` (line 22) gains `mcp__hilclaw__hypotheses_read`; `test_the_real_definition` (line 260) gains `Agent(technique-selector)` and `mcp__hilclaw__hypotheses_write` in the allowed list, the built-in set stays `"Agent,Glob,Grep,Read"`; `test_holder_lists_the_real_definition` (line 403) gains `"technique-selector"` with its tool tuple;
     - `tests/test_turn_definition.py`: `test_the_repository_definition_by_default` (line 114) and `test_the_repository_definition_holds_the_prompt_and_the_three_agents` (line 130; renaming it to four agents is allowed).
   - **Assertions that pin the old prompt text** change only because slice 3 replaces the text they pin: `test_the_prompt_keeps_the_stop_in_later_rounds` (line 579), `test_the_prompt_reaches_the_closing_steps_from_round_0_only` (line 645) and `test_the_stop_commits_and_leaves_round_0_open` (line 696) where they read "follows step 1" or "no step 2". State each change and its reason in the PR body. Every other existing assertion stays as it is.
   - Run the full local suite (`pytest`), `ruff check` and `ruff format --check`; coverage of `hilclaw/` stays at line >= 80% and function >= 80%. CI must be green before the squash-merge.
9. **Result.** In `## Result`, write: the language (Python for the tool; Markdown for the definitions) and the reason in one line; the module name and the encoding chosen; every prompt sentence rewritten or added, quoted briefly, with the decision it follows; the test assertions changed (as in the PR body); and the record sentences this task makes less exact but that you did not edit. Candidates to check, not edit: the ADR-0132 Consequences "Less exact, not edited" list (ADR-0059 Boundaries, ADR-0073 Boundaries, ADR-0129 decision 4, ADR-0139 decisions 1 and 3, ADR-0146 decision 1); `hilclaw/case_lookup.py` docstring ("does not decide which agent performs the lookup"); ADR-0132 Consequences "Today no run reaches round 1" (ADR-0142 decision 7 is now past).

## Out of Scope

- Slice 4: any lookup read tool, any `cases_read` written by the selector (ADR-0132 decision 5; PLAN P2-7).
- Any round >= 1 step after the read of the record: spec write, coder delegation, checks, measurement, verdicts, the technique ids of a spec (ADR-0132 Boundaries; ADR-0151; later P2-1 work).
- Any hook on the order of decision 6 or on a request's `run_id` (rest of OD-18; P2-4). Any check of ADR-0112's or ADR-0075's rules between files.
- `decision/decision.md` and any writer of it.
- Editing any ADR, `ARCHITECTURE/` file, `README.md`, `catalog/`, `.claude/settings.json` or `.claude/settings.local.json`. Any change to the data plane (no member, file, path, version or validator changes) — such a change would be a BLOCKED reason (CLAUDE.md A-13).
- Any new external dependency.
- Starting `claude`, Docker or `clang` on this machine (D16). An end-to-end round 1 through a stub `claude` is P2-5's verification, not this task's.

## Follow-ups

- (planner) Slice 4 of ADR-0132 waits on the record of the lookup read tool (ADR-0132 decision 5; PLAN P2-7).
- (planner) The rest of P2-1 for rounds >= 1 (the coder-driver's round >= 1 delegation, the checks, the measurement and the verdicts before the closing steps) needs a record of those steps (ADR-0132 Boundaries; ADR-0151; ADR-0140).

## Result
