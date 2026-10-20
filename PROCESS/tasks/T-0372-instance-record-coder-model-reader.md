---
id: T-0372
title: Carry the member `coder_model` of ADR-0136 into `hilclaw/instance.py` (ADR-0136 code slice 1) - check the form of the top-level member (a full Claude model name, may be absent) and add the reader `coder_model_of`; no default, nothing stands in, bound to no tool
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [NFR-5, FR-5, FR-13, OD-8, OD-23, "#5 A-8"]
dependsOn: [T-0371]
touchesFiles: [hilclaw/instance.py, hilclaw/instance_file.py, tests/test_instance.py, tests/test_instance_file.py]
estimatedSize: {loc: 170, files: 2}   # non-test: about 15 statement lines and about 150 docstring lines in instance.py, one docstring clause in instance_file.py; the two test files are excluded from the cap (D4)
hq: []
---
## Why

ADR-0136 (T-0371, landed as `4423c35`) records the owner's answer to HQ-0041 part (1): the coder model is an instance parameter, recorded in `instance.json`. Its Consequences name three code slices. **This task is slice 1**:

> `hilclaw/instance.py`: the member by decision 3, a reader `coder_model_of`, the docstring; with `tests/test_instance.py`.

Today a top-level `coder_model` of any value is passed over and returned in `Instance.others`. Nothing in the package can answer "which model does this run's coder call request". Slices 2 and 3 both depend on this slice:

- Slice 2, the default in `hilclaw/instance_start.py`, applies this check to a given value.
- Slice 3, the read in `hilclaw/coder_call.py`, uses the reader.

This is PLAN P2-2 (the coder-driver), a checklist item in the first group of the P2 order (PLAN P2 head, D18). It is therefore not subject to the D18 rule for work outside the checklist. P2-5 needs it: no coder call of the first run can start without a model to run the coder with (NFR-5).

Planner's judgements (from `main` `6e3e49a`; **the reviewer is asked to re-check each**):

- **The slice has the same shape as T-0143 (`draws`) and T-0168 (`objective`), one member later.** It adds:
  - one more name in `_DEFINED`;
  - a private check;
  - one more field of `Instance` after `objective` and before `others`;
  - one more reader that returns the field of what `read` returns.
- **No ADR is needed (DRIVER §9).** ADR-0136 decisions 2 to 4 fix the member's name, place and form, that it may be absent, that a present one must be valid, and that `schema_version` stays 1. This task decides only:
  - Python names;
  - the field's position;
  - the message text;
  - the treatment of a value built in memory.
- **Data-plane schema change (A-13 BLOCKED reason) does not apply.** The owner authorised the member ("records it in `instance.json`", HQ-0041). ADR-0136's A-13 reading recorded it along the D6 route. This task implements that record and adds nothing to it. The set of valid version-1 contents becomes narrower exactly as ADR-0136 says, and no such file exists in a data plane.
- **No open HQ is crossed.**
  - HQ-0040 (the front of the call) and HQ-0032 (PR #186, the start function): this slice neither starts nor calls anything.
  - HQ-0041 part (2) (the token axis): not touched.
- **No overlap with PR #186.** PR #186 (`hilclaw/start_instance.py` and three test files) is a different file set. The unlanded branch `claude/T-0233-*` (BLOCKED) also edits `hilclaw/instance.py` and `tests/test_instance.py`. Do not take its content, and note it in `## Result`.
- **Known risk, accepted.** ADR-0136 is inside its 7-day objection window (notice posted 2026-10-21). Code slices have landed inside such windows before (T-0101, T-0143). An objection creates a reverting task, and this change is reverted with it. Say so in one line of the commit body.

All verification uses tests on this machine. No `claude` is started, and no model name is tried against any service (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (executor procedure, resume rule, the 2h30m limit);
  - §5 (task format, `T-NNNN` naming: branch `claude/T-0372-<slug>`, trailer `Task: T-0372`, PR body last line; size cap D4; code-task test rules D12; the language line in `Result`);
  - §3 "BLOCKED 사유" paragraph and §9.
- `CLAUDE.md`, 상시 규칙:
  - "도구 계층 언어 정책";
  - "브랜치·merge 절차" (code mode; BLOCKED reasons);
  - "테스트 규칙" ① to ⑤;
  - "코멘트 최소화";
  - "미결은 발명하지 않는다";
  - "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (procedure) and `.claude/skills/dev-code-review/SKILL.md` (what the reviewer checks).
- **`ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md`**:
  - Status (lines 3-15);
  - decision 2 (lines 47-52);
  - **decision 3 (lines 54-67: the form, what is not a value, form check only, a present member must be valid)**;
  - decision 4 (lines 69-82: absent is valid, `schema_version` stays 1, no reader substitutes a value; only the start applies the default, which is slice 2 and not this task);
  - decision 5 (lines 84-92: the coder call's read and kinds, slice 3 and not this task);
  - the Walk-through (lines 96-104);
  - Consequences, slice 1 (lines 129-132);
  - Boundaries.
- `ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md` decision 2: the open top level, the unsupported version checked before any other member, what makes a file invalid. Read only.
- **`hilclaw/instance.py`** (1375 lines), all of it:
  - the module docstring: the first line and the record/reader list paragraph; "Conventions of this module, which the twelve records do not fix"; the order of the checks; the per-member convention bullets; the "defines no member besides …" sentence; the closing "Of the …" paragraphs per member, with `owner`/`project` (a `str` member) and `objective` as the nearest models;
  - `_DEFINED`, `InvalidInstanceError`, `Instance`, `parse` (its list of names that stay in `others`), `validate` (its record list and counts), `read`, `hw_profile_of` (its list of members whose invalidity makes it raise), `owner_of`, `objective_of`, `_fail`, `_checked`, `_string`.
- `hilclaw/instance_file.py` lines 66-72: the sentence that lists the members a valid content may lack and attributes the later ones to their records.
- **`tests/test_instance.py`** (8872 lines):
  - lines 1-260: the imports, the helpers, and `test_the_public_names` (the public names, `Instance._fields`, `_field_defaults`, the reader signature loop);
  - every positional `Instance(...)` comparison (search `Instance(`; there are none in any other test file);
  - `test_nothing_of_the_module_holds_a_tolerance_value`, which lists every module-level `int` and `float`;
  - `READERS` (about line 4405), `INVALID_FILES` (about line 4470) and the parametrised error cases of `read` after them;
  - `EVERY_MEMBER` and `assert_the_other_members_are_stated` (about line 5091);
  - **the `owner`/`project` block and the `objective` block (from about line 8061) as the nearest models**.
  - Search by name if line numbers have moved.
- `tests/test_instance_file.py` lines 1-145 (`written`, `FULL`, `CONTENTS`, `REFUSED`) and the cases they parametrise.
- PROCESS/tasks/T-0143-instance-record-draws-reader.md and PROCESS/tasks/T-0168-instance-record-objective-reader.md, `## Acceptance Criteria` and `## Result`: the same module, the same kind of slice, and the review findings these slices drew.
- Read only: `.github/workflows/ci.yml` (the jobs; `Coverage gate (hilclaw)`) and `pyproject.toml` (Python >= 3.11; pinned ruff and pytest).
- Issue #5: every comment after the ADR-0136 §9 notice (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`).
  - If the owner has objected to ADR-0136, or has said anything about the form of the coder model value, do not start: return BLOCKED ("requirement unclear") and quote the comment.
  - Any other owner answer does not stop this task; name it in `## Result`.

## Acceptance Criteria

ADR-0136 decisions 2 to 4 fix the rules. The names, the field's position, the message and every case the record does not mention are **this task's choices**. State each, with one line of reason, in the commit body, the PR body and `## Result`. Where a criterion below disagrees with the record, **the record wins**: follow the record and say so in `## Result`.

### Files

- Edit only these four:
  - `hilclaw/instance.py`;
  - `hilclaw/instance_file.py` (the one docstring clause of lines 66-72 only);
  - `tests/test_instance.py`;
  - `tests/test_instance_file.py`.
- **Nothing else changes.** In particular these stay as they are:
  - `hilclaw/instance_start.py` (slice 2);
  - `hilclaw/coder_call.py` (slice 3);
  - `hilclaw/start_instance.py` (PR #186);
  - `hilclaw/tools.py` and every other module;
  - `orchestration/`, `pyproject.toml`, `.github/`, every ADR and the OD register.
- If you conclude another file must change, return BLOCKED with the reason.
- Python, because the module exists in Python. Write that in one line of the commit body and of `## Result`.

### What must not change

- These stay as they are:
  - `SCHEMA_VERSION` (1);
  - the rules of the thirteen existing members, **their messages byte for byte**, and the order in which they are checked;
  - the signatures of `parse`, `validate`, `read` and every existing reader;
  - `Tolerance`, `OpSignature`, `layout_version_of`, `_STATED_LAYOUT`.
- A content without the member is valid exactly when it was valid before.
- A top-level member of a nearby name stays undefined, is passed over and is returned in `others`. Examples: `model`, `coderModel`, `Coder_Model`, `coder_models`, `coder`, and a `coder` object holding `model`.
- No statement of `hilclaw/instance_file.py` changes.
- No existing assertion is weakened. **Existing tests may be edited only where the new field, the new public name or the new defined member makes it necessary.** These edits are permitted:
  - in `tests/test_instance.py`:
    - `test_the_public_names`;
    - `READERS`;
    - `INVALID_FILES` (new rows only);
    - every positional `Instance(...)` comparison (one more `None`, or the tuple constants that feed them);
    - helpers that list every member or every reader, only where a new case needs it;
  - in `tests/test_instance_file.py`: `FULL` and `REFUSED`.
- List every edited existing assertion in `## Result`. If an existing test fails for any other reason, do not edit it: return BLOCKED with the output.

### The validity of the member (ADR-0136 decision 3)

- `coder_model` joins `_DEFINED`, so it is no longer returned in `others`.
- A present member is valid exactly when all of these hold:
  - it is exactly a `str` (for a value built in memory, a subclass of `str` is not one);
  - its length is at most 64;
  - it begins with `claude-`;
  - one or more characters follow that prefix, each an ASCII lowercase letter, a digit or `-`;
  - it does not end with `-`.
- **Valid values** include: `claude-opus-5-5`, `claude-sonnet-4-5-20250929`, `claude-x`, and a 64-character name of the form.
- **Not values**:
  - the alias `opus`;
  - `best`;
  - `default`;
  - `claude-` alone;
  - `claude-opus-5-5-` (trailing `-`);
  - `claude-opus-5-5[1m]`;
  - `Claude-opus-5-5` and `claude-Opus-5-5` (upper case);
  - a name with a space, `.`, `_`, `/` or `:`;
  - a non-ASCII lowercase letter (for example `claude-opüs`);
  - a 65-character name of the form;
  - an inference-profile ARN;
  - `""`, `5`, `true`, `null`, an array and an object.
- **No list of offered models.** The check is of form only (ADR-0136 decision 3). The module holds no model name in its code: no `claude-opus-5-5` literal and no other full name. The default is slice 2's.
- A present and invalid member raises `InvalidInstanceError` naming the place `coder_model`. Nothing is returned, so no member of that content is used, and nothing is repaired.
  - Recommended message, in the manner of `_string`: `coder_model: must be a str of at most 64 characters, "claude-" followed by lowercase ASCII letters, digits and "-", not ending with "-", got <type name>`.
  - A `str` is shown as the module already shows every `str` (`reprlib.repr`).
- The member is checked after `objective`, in the order in which the records defined the members. Another `schema_version` is still `UnsupportedVersionError` before the member is looked at. The text rules (a member name twice, an integer too long for the interpreter) stay text rules.
- A content without the member is valid and states no coder model: the field is `None`.
  - **No value stands in**: no Opus name, no alias, no constant of this module, nothing derived from another member or another run (ADR-0136 decision 4: "No reader substitutes a value, not the default included").
  - No function has a default argument, and no named tuple has a field default.
- The value is handed out as the `str` of the file, unchanged: not lower-cased, not stripped, not resolved.
- Recommended shape:
  - a field `coder_model: str | None` of `Instance` after `objective` and before `others` (`others` stays last);
  - a private check beside `_string`, with the 64 bound as a literal inside it, so that `test_nothing_of_the_module_holds_a_tolerance_value` stays unedited unless you justify otherwise;
  - no new import outside the standard library and the existing ones.
- The module's **code** (names and string literals; a docstring may cite the record) holds none of these:
  - `coder_model_not_stated`;
  - `run_file_` kinds;
  - `ToolFailure`;
  - an Opus or Sonnet name.

### The reader

- Add a public reader `coder_model_of(data_root, run_id)` beside the others. It returns the field of what `read` returns: the `str` the file states at that call, or `None` for a valid file without the member.
- It raises what `read` raises, unchanged. For a missing file, an unreadable file, an invalid file or a file of another version, no model is returned and none is inferred.
- It:
  - takes no further argument;
  - has no default;
  - keeps nothing between calls (a file changed between two calls is seen at the second);
  - opens only the instance file of the run it is asked about;
  - is called from nowhere in the package;
  - raises no `ToolFailure` and gives "not stated" no kind. `coder_model_not_stated` is the coder call's, in slice 3.

### Docstrings

CLAUDE.md "코멘트 최소화" applies: no multi-line comments. Docstrings of the public API may be as long as needed.

- **`hilclaw/instance.py` module docstring:**
  - Name ADR-0136 in the first line and in the first paragraph, with what it fixes for this file: the member `coder_model`, in which a run states the full name of the Claude model its coder calls request (decisions 2 and 3); that a valid file may lack it, that a present one must be valid, and that nothing stands in for an absent one (decision 4).
  - Add the new reader to the list of functions that read a run's file, and to the sentence that says no reader is bound to a tool.
  - Correct every count the change makes wrong. Check each sentence for what it counts: "which the twelve records do not fix", "no member besides …", the order of the checks, and the record lists in `InvalidInstanceError` and `validate`.
  - Add one conventions bullet that keeps the record's rule apart from the module's conventions, as the existing member bullets do.
  - Add a closing paragraph "Of the coder model …". It says the module:
    - gives what the file states and nothing else;
    - holds no default and substitutes none: the Opus default is applied by the start (ADR-0136 decision 4, a later slice), never by a reader;
    - checks the form only, not whether a model is offered: a misspelt name of the right form is valid (decision 3, "The cost");
    - states the model the call *requests*, not the one that ran (decision 3);
    - gives "not stated" no kind, and is bound to no tool. The coder call's read of the member and its kinds are ADR-0136 decision 5 and are not done here.
- `hilclaw/instance_file.py`: add `coder_model` to the clause that lists the members a valid content may lack, and attribute it to ADR-0136. Change no other sentence.

### Tests

These follow CLAUDE.md 테스트 규칙 and use the `objective` and `owner` blocks as models.

- **Happy path:**
  - a content with each valid value above is parsed, and `coder_model_of` returns it unchanged;
  - the member is accepted at any place among the other members;
  - a content with every member defined is accepted.
- **Absent:** a content without the member gives `None` from `parse` and from `coder_model_of`, and nothing stands in.
- **Negative:**
  - every "not value" above raises `InvalidInstanceError` naming `coder_model`, through `parse`, through `validate` (including a `str` subclass built in memory) and through `read`/`coder_model_of`;
  - an invalid `coder_model` makes `hw_profile_of` and the other readers raise too, as `INVALID_FILES` does for the other members.
- **Branches:**
  - another `schema_version` is reported before the member is looked at;
  - the first broken rule is reported when an earlier member is also broken;
  - the member name twice at the top level is a text error;
  - nearby names are passed over and returned in `others`.
- **Reader properties:**
  - no state is kept (rewrite the file between two calls);
  - the reader opens only the asked run's file;
  - it is called from nowhere in the package (search the package source);
  - the signature has no default.
- **Module checks:**
  - no Opus or Sonnet name occurs as a string literal in the module's code (an AST scan of string constants outside docstrings, in the manner of the existing "nothing of the module stands in" cases);
  - the module still imports what it imported before and nothing more.
- **`tests/test_instance_file.py`:** `FULL` gains a valid `coder_model`; `REFUSED` gains one invalid `coder_model` row. Add a case that a content with an invalid `coder_model` is not written.
- `hilclaw/` line and function coverage stays at or above 80 %. `hilclaw/instance.py` should stay at 100 %.
- Run locally: `python -m pytest`, `ruff check` and `ruff format --check`. CI must be green before the squash-merge.

### Process

- Code mode (CLAUDE.md A-13):
  - branch `claude/T-0372-<slug>`;
  - Draft PR with `T-0372` in the title;
  - context-isolated reviewer cycle (at most 7 rounds) to Approve;
  - CI green;
  - `gh pr merge --squash --body` with the PR body, whose last line is `Task: T-0372`;
  - delete the branch.
- No `claude` is started at any point (D16).

## Out of Scope

- The Opus default and the constant cited from F2 (`hilclaw/instance_start.py`, ADR-0136 slice 2).
- The read at the coder call, `coder_model_not_stated`, the `run_file_*` kinds at that read, and the hand-over to the seam (`hilclaw/coder_call.py`, slice 3).
- Slice (d) and its design points: how the value reaches `claude -p`, and the image, flags, sign-in, permission mode, prompt, time limit and output stream.
- The token axis (HQ-0041 part (2)) and any row of `ARCHITECTURE/SpendAxes.md`.
- `hilclaw/start_instance.py` and every file of PR #186. The content of the unlanded `claude/T-0233-*` branch.
- The models of every other agent.
- Every less-exact sentence of earlier records or docstrings outside the two docstrings named above. If you find one, list it in `## Result` and do not edit it (D18 hold).

## Follow-ups

- ADR-0136 slice 2 (planner's view, next P2-2 task): the fill-in in `hilclaw/instance_start.py` at the `n_max` step. A module constant holds the full Opus name cited from F2 with the date it was read (`claude-opus-5-5`, read 2026-10-21). A given value is never replaced. Tests go in `tests/test_instance_start.py`. It must not overlap PR #186 while that PR is open.
- ADR-0136 slice 3: the read in `hilclaw/coder_call.py`, after `no_data_root` and before `output_exists`, with the four `run_file_*` kinds and the new kind `coder_model_not_stated`, and the hand-over to the seam.
- Carried from T-0370, for the `orchestration/round-manager.md` slice that replaces the explicit stop (not this task): "One round at most" still says the session ends after the write that ends its round, while the closing steps now put `run.commit` after it.

## Result
