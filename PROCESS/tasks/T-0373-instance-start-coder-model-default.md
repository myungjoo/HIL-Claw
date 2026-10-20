---
id: T-0373
title: Fill in the Opus default of ADR-0136 in `hilclaw/instance_start.prepare` (ADR-0136 code slice 2) - when a document states no `coder_model`, the start's check puts in the full Opus name cited from F2; a given value is never replaced
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [NFR-5, FR-5, FR-13, OD-8, OD-23, "#5 A-8"]
dependsOn: [T-0371, T-0372]
touchesFiles: [hilclaw/instance_start.py, tests/test_instance_start.py]
estimatedSize: {loc: 50, files: 2}   # non-test: one constant with its doc line, one statement, and docstring sentences in instance_start.py; the test file is excluded from the cap (D4)
hq: []
---
## Why

ADR-0136 (T-0371, landed as `4423c35`) records the owner's answer to HQ-0041 part (1): "**Coder model**: an instance parameter. When the instance names none, the start applies Opus and records it in `instance.json`." Its Consequences name three code slices. Slice 1 (T-0372, PR #214, `d618457`) made `coder_model` a defined member of `instance.json` with a form check and the reader `coder_model_of`. **This task is slice 2**:

> `hilclaw/instance_start.py`: the fill-in of decision 4, with the constant cited from F2; with `tests/test_instance_start.py`. It comes after slice 1, whose check it applies to a given value. It must not overlap open PR #186 (`hilclaw/start_instance.py`) while that PR is open.

Today `prepare` fills in only `n_max`. A document that names no coder model is handed on to be written without one. Slice 3 (the read in `hilclaw/coder_call.py`) will refuse such a run with `coder_model_not_stated`, so without this slice no run the start prepares could reach a coder call.

This is PLAN P2-2 (the coder-driver), a checklist item in the first group of the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. P2-5 needs it: the first run's coder calls need a recorded model (NFR-5; ADR-0136 decision 4).

Planner's judgements (from `main` `ce60969`; **the reviewer is asked to re-check each**):

- **Same shape as the existing `n_max` fill-in, one member later.** One module constant, one `setdefault` beside the `n_max` one, docstring sentences, tests.
- **No ADR is needed (DRIVER §9).** ADR-0136 decision 4 fixes: the value (the full name of the Opus model F2 lists for `opus` on the Anthropic API, `claude-opus-5-5` on 2026-10-21); the step (where `n_max` is filled in: after validity and scope, before the required set); that a given value is never replaced; that an invalid given value makes the content invalid; and that the report order of ADR-0076 decision 3 is unchanged. It also says "The code task that sets the package's constant cites F2 with the date it was read." This task decides only the constant's name and place, the docstring text and the tests.
- **Data-plane schema change (A-13 BLOCKED reason) does not apply.** No member, rule or version changes; ADR-0136 recorded the member along the D6 route and slice 1 implemented its rule. This slice only fills in a value the record names.
- **No open HQ is crossed.**
  - HQ-0032 (PR #186, the start function, how the start learns of a given id): ADR-0136 decision 4 says "How the start learns of a given value is not decided here". This slice does not decide it either: `prepare` takes a document, as today, and fills in what the document lacks.
  - HQ-0040 (the front of the coder call) and HQ-0041 part (2) (the token axis): not touched.
- **No file overlap with PR #186** (`hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`). PR #186 calls `instance_start.prepare`, so after this change its bytes gain a `coder_model` member when it is rebased; that is that PR's concern when HQ-0032 is answered. Do not edit any file of PR #186; name this in `## Result`.
- **Known risk, accepted.** ADR-0136 is inside its 7-day objection window (notice posted 2026-10-20T16:53Z on #5). Code slices have landed inside such windows before (T-0143, T-0372). An objection creates a reverting task, and this change is reverted with it. Say so in one line of the commit body.

All verification uses tests on this machine. No `claude` is started, and no model name is tried against any service (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (executor procedure, resume rule, the 2h30m limit);
  - §5 (task format, `T-NNNN` naming: branch `claude/T-0373-<slug>`, trailer `Task: T-0373`, PR body last line; size cap D4; code-task test rules D12; the language line in `Result`);
  - §3 "BLOCKED 사유" paragraph and §9.
- `CLAUDE.md`, 상시 규칙: "도구 계층 언어 정책"; "브랜치·merge 절차" (code mode; BLOCKED reasons); "테스트 규칙" ① to ⑤; "코멘트 최소화"; "미결은 발명하지 않는다"; "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (procedure) and `.claude/skills/dev-code-review/SKILL.md` (what the reviewer checks).
- **`ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md`**:
  - Status (lines 3-15) and Context F2 (lines 24-30);
  - decision 3 (lines 54-67: the form; a present member must be valid);
  - **decision 4 (lines 69-82: the value that stands for Opus, the constant cited from F2 with the date read, a written file keeps its value, how the start fills it in, given values never replaced, the report order unchanged, how the start learns of a given value not decided)**;
  - the Walk-through rows 1-3 (lines 96-100);
  - Consequences, slice 2 (line 131) and the "Less exact, not edited" list (lines 133-140);
  - Boundaries (lines 150-157).
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md` decisions 1 to 3 (the scope, the `n_max` fill-in, the report order). Read only.
- `ARCHITECTURE/decisions/ADR-0023-od8-instance-record-n-max.md` decision 4 (a later change of the default changes no written file). Read only.
- **`hilclaw/instance_start.py`** (178 lines), all of it.
- `hilclaw/instance.py`: the module docstring paragraph on the coder model ("Of the coder model …"), `_coder_model` and `coder_model_of` (search by name). Read only; it must not change.
- `hilclaw/harness/measurement.py` around `N_MAX_DEFAULT` (line 47): how the package holds the other default and documents it. Read only.
- **`tests/test_instance_start.py`** (524 lines), all of it: the helpers `document`, `without`, `call`, `refused`; every test that compares the prepared document with the given one; `test_the_module_holds_no_number_of_its_own`; `test_public_names_of_the_module`; `test_the_module_imports_neither_the_standin_nor_the_contract_module`.
- `tests/test_instance.py`: the `coder_model` block added by T-0372 (search `coder_model`), for the valid and invalid values already used. Read only.
- PROCESS/tasks/T-0372-instance-record-coder-model-reader.md, `## Acceptance Criteria` and `## Result`: slice 1's choices (the rule, the message, the field).
- Read only: `.github/workflows/ci.yml` (the jobs; `Coverage gate (hilclaw)`) and `pyproject.toml`.
- Issue #5: every comment after the ADR-0136 §9 notice (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`).
  - If the owner has objected to ADR-0136, or has said anything about the default model, its form or where the start applies it, do not start: return BLOCKED ("requirement unclear") and quote the comment.
  - Any other owner answer does not stop this task; name it in `## Result`.

## Acceptance Criteria

ADR-0136 decision 4 fixes the rules. The constant's name, its place, the docstring text and every case the record does not mention are **this task's choices**. State each, with one line of reason, in the commit body, the PR body and `## Result`. Where a criterion below disagrees with the record, **the record wins**: follow the record and say so in `## Result`.

### Files

- Edit only `hilclaw/instance_start.py` and `tests/test_instance_start.py`.
- **Nothing else changes.** In particular these stay as they are: `hilclaw/instance.py` (slice 1, done); `hilclaw/coder_call.py` (slice 3); `hilclaw/harness/measurement.py`; every file of PR #186 (`hilclaw/start_instance.py`, `tests/test_start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`); `orchestration/`, `pyproject.toml`, `.github/`, every ADR and the OD register.
- If you conclude another file must change, return BLOCKED with the reason.
- Python, because the module exists in Python. Write that in one line of the commit body and of `## Result`.

### The constant

- Add one public module constant to `hilclaw/instance_start.py` holding exactly `"claude-opus-5-5"`. Recommended name: `CODER_MODEL_DEFAULT` (parallel to `N_MAX_DEFAULT`).
- Its `#:` doc line cites F2 (https://docs.claude.com/en/docs/claude-code/model-config) with the date it was read (2026-10-21) and ADR-0136 decision 4. One line, no multi-line comment.
- It is the only model name in the package outside docstrings. Do not add an alias, a list of models, or a second name.
- Why here and not in `hilclaw/instance.py`: ADR-0136 decision 4 says only the start applies the default and "No reader substitutes a value, not the default included"; T-0372 kept every model name out of `hilclaw/instance.py`. State this in `## Result`.

### The fill-in (ADR-0136 decision 4)

- In `prepare`, at step 4 (where `n_max` is filled in): when `coder_model` is absent from the document, the new `dict` gets `coder_model` set to the constant. Recommended: one `prepared.setdefault("coder_model", CODER_MODEL_DEFAULT)` beside the `n_max` one.
- **A given value is never replaced.** A valid given value (for example `claude-sonnet-4-5-20250929`, `claude-x`) is returned as given, the same object.
- **A given invalid value** (for example `opus`, `default`, `claude-opus-5-5[1m]`, `""`, `5`, `None`, `Claude-opus-5-5`) raises what `hilclaw.instance.validate` raises (`InvalidInstanceError` naming `coder_model`), unchanged, at step 2; nothing is filled in and the default never stands in. This comes from slice 1's check; this task adds no check of its own.
- **Order unchanged**: type errors, then validity, then scope, then the fill-ins, then the required set. A document of another `schema_version`, an invalid document and a document out of scope get nothing filled in. `coder_model` is never reported as missing, and `REPORT_ORDER` does not change (ADR-0136 decision 4: "the report order of ADR-0076 decision 3 is unchanged").
- A refusal for missing members raises `MissingMembersError` exactly as today; its message still names members only and shows no value, so it names no model.
- The returned `dict` passes `hilclaw.instance.validate`, and `hilclaw.instance.parse` of its JSON gives `coder_model` equal to the constant (or the given value).
- `document` is still never modified; values are still shared, not copied.
- Nothing else changes: `REPORT_ORDER`, `OutOfScopeError`, `MissingMembersError`, every message byte for byte, the signature of `prepare` (no new argument, no default).

### Docstrings

CLAUDE.md "코멘트 최소화" applies: no multi-line comments. Docstrings may be as long as needed.

- Module docstring:
  - Name ADR-0136 decision 4 in the first paragraph beside ADR-0076: the start puts the full Opus name into the content when it states no `coder_model` and never replaces a given one.
  - Add the constant to the list of what the module renders.
  - The order bullet ("validity, then scope, then the filling-in of `n_max`, then the required set") includes the `coder_model` fill-in.
  - The default bullet ("this module holds no number") gains a sentence: the coder model default is this module's constant, cited from F2 with the date it was read; a later task may replace it with a newer Opus name without a new record, and a written file keeps its value (ADR-0136 decision 4).
  - "What the module does not do": it resolves no alias, checks no model against a list of offered models and tries no model against any service; how the start learns of a given value stays open (ADR-0136 decision 4, HQ-0032).
- `prepare` docstring step 4 names the `coder_model` fill-in; step 2 says a given `coder_model` that breaks ADR-0136 decision 3 is refused there and never replaced.

### Tests (`tests/test_instance_start.py`)

These follow CLAUDE.md 테스트 규칙.

- **Permitted edits of existing tests**, only where the fill-in makes them necessary:
  - the `document` helper may gain a `coder_model` parameter whose default is a **test value** of valid form that is not an Opus or Sonnet name (for example `"claude-test-model-1"`, next to the other `TEST_*` constants), so that the existing equality assertions stay true unedited; or the comparisons that now differ may be edited. Choose one and say why in `## Result`;
  - `test_public_names_of_the_module` gains the constant's name.
  - List every edited existing assertion in `## Result`. No existing assertion is weakened. If an existing test fails for another reason, do not edit it: return BLOCKED with the output.
- **Happy path**: for each accelerator of `ACCELERATORS`, a document without `coder_model` returns a `dict` whose `coder_model` is the constant, and is equal to the given document plus that one member; `instance.parse` of its JSON gives the constant through `coder_model`. With both `n_max` and `coder_model` absent, both are filled in and nothing else is added.
- **The constant**: is exactly a `str` equal to `"claude-opus-5-5"`; a document holding it is valid under `instance.validate`.
- **Given values**: a valid given value (several, including one that is not an Opus name) is returned unchanged and is the same object; never replaced by the constant.
- **Negative**: each invalid given value above raises `InvalidInstanceError` naming `coder_model`, the given document is unchanged, and nothing is filled in.
- **Branches**: a document out of scope (another accelerator; an uncovered `op_signature`) raises `OutOfScopeError` and the given document gains no `coder_model`; a document of another version raises `UnsupportedVersionError` before anything; a document lacking required members raises `MissingMembersError` whose `missing` never includes `coder_model` and whose message holds no model name; `REPORT_ORDER` does not contain `coder_model`.
- **Module checks**: the module still imports only `hilclaw.instance` and `hilclaw.harness.measurement` (existing test, unedited); still holds no `int` constant (existing test, unedited); the only string constant of the module's code (outside docstrings) that starts with `claude-` is the constant's value (an AST scan of string constants).
- `hilclaw/` line and function coverage stays at or above 80 %. `hilclaw/instance_start.py` should stay at 100 %.
- Run locally: `python -m pytest`, `ruff check` and `ruff format --check`. CI must be green before the squash-merge.

### Process

- Code mode (CLAUDE.md A-13): branch `claude/T-0373-<slug>`; Draft PR with `T-0373` in the title; context-isolated reviewer cycle (at most 7 rounds) to Approve; CI green; `gh pr merge --squash --body` with the PR body, whose last line is `Task: T-0373`; delete the branch.
- No `claude` is started at any point (D16).

## Out of Scope

- The read at the coder call, `coder_model_not_stated`, the `run_file_*` kinds at that read, and the hand-over to the seam (`hilclaw/coder_call.py`, ADR-0136 slice 3).
- How the start learns of a given value or id (HQ-0032), the start function and every file of PR #186.
- Slice (d): how the value reaches `claude -p`; image, flags, sign-in, permission mode, prompt, time limit, output stream.
- The token axis (HQ-0041 part (2)) and `ARCHITECTURE/SpendAxes.md`.
- The models of every other agent.
- Every less-exact sentence of earlier records (ADR-0136 Consequences list, including ADR-0076 decision 3 and ADR-0115 decision 2, whose order gains one fill-in). If you find another, list it in `## Result` and do not edit it (D18 hold).

## Follow-ups

- ADR-0136 slice 3 (planner's view, next P2-2 task): the read in `hilclaw/coder_call.py`, after `no_data_root` and before `output_exists`, with the four `run_file_*` kinds and the new kind `coder_model_not_stated` inserted into `FAILURE_KINDS`, and the hand-over of the value to the seam; with `tests/test_coder_call.py`.
- Carried from T-0370, for the `orchestration/round-manager.md` slice that replaces the explicit stop (not this task): "One round at most" still says the session ends after the write that ends its round, while the closing steps now put `run.commit` after it.

## Result
