---
id: T-0415
title: Add hilclaw/spec_feedback.py - the feedback.attempts of a first-case round >= 1 spec, read from the earlier attempts' specs, the run's log and the compiler logs (ADR-0151 code slice 1; for PLAN P2-5)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-1, FR-5, FR-17, OD-6, "PLAN P2-5"]
dependsOn: [T-0414]
touchesFiles: [hilclaw/spec_feedback.py, tests/test_spec_feedback.py]
estimatedSize: {loc: 240, files: 1}
hq: []
---
## Why

**Where things stand** (as of `main` `2ca7ea8`):
- ADR-0151 (T-0414, landed as 3b0d3f5) decides the spec of the first coder call of a round >= 1 in a first-case run with one candidate per round.
- Its Consequences name two code slices. Slice 1 is a new module for the spec's `feedback.attempts` (decision 2 (d)). Slice 2 widens `spec.write` in `hilclaw/spec_tool.py` and calls slice 1. This task is slice 1.
- T-0414's Result names this module as the next task.

**D18 reading.** This is not a PLAN checklist item. It is the code of a landed record, so the priority rule of DRIVER §6 applies to it. It is needed for P2-5. P2-5 runs 5 rounds. Rounds 1 to 4 each need a spec before their coder call (ADR-0151 Status, "Not owner-only"). `spec.write` refuses every round >= 1 tuple until slice 2 lands, and slice 2 depends on this module. It is not input hardening, wording or a refactor. It adds behaviour the first run needs.

**Not crossed.** The task stays inside ADR-0151 decision 2 (d) and the checks ⑧ to ⑩ of its decision 3. It does not touch:
- the selection side: who chooses technique ids, `hypotheses.json`, `decision.md` (HQ-0048);
- the coder's start (HQ-0053);
- the run tools' operations and the code that writes the compiler log (HQ-0021, HQ-0026). This module only reads a compiler log file when one exists;
- injected cases (HQ-0031) and OpenMP (HQ-0034).

No data-plane member, file, kind value or version changes. The new kind `feedback_unreadable` is a tool-layer name (ADR-0151 decision 3, "Kinds").

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED by HQ-0032) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py` only.

**D16.** The tests use fixture files in `tmp_path` only. Nothing starts `claude` or a container, or needs a board or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0415-<slug>`, PR title with `T-0415`, trailer `Task: T-0415`, `Task: T-0415` as the last line of the PR body for the squash); size cap; code-task test rule; language line in `Result`;
  - §8 (lines 136-142): HQ form, used only if you return BLOCKED.
- `CLAUDE.md`, 상시 규칙: "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md`. This is the rule for this module:
  - decision 2 (d), lines 54-59: which attempts are shown, their order, `techniques`, `failure` (`stage`, `report`), no `profile`, which attempts are not shown, and the dependencies;
  - decision 3 table, line 71: checks ⑧, ⑨ and ⑩ with their kinds;
  - "Kinds" (line 74): `feedback_unreadable`; the four `run_file_*` kinds and `check_result_invalid`, reused;
  - Consequences, slice 1 (line 113);
  - Walk-through, lines 83-91.
- `ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md` decision 2: the form of a `feedback.attempts` entry. `spec.validate` in `hilclaw/spec.py` lines 265-288 (`_attempt`) is its code.
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`:
  - decision 2: when the file exists, and what a missing file means;
  - decision 3: the path `.../measure/candidates/<CC>/attempts/<AA>/build-log-<step>-<EE>.txt`;
  - decision 4: the bytes are UTF-8 without a byte order mark;
  - decision 5: what the log may hold.
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md` decisions 2 and 3: the standing rule.
- Code to reuse. Do not re-implement any of it:
  - `hilclaw/check_standing.py` (all): `standing(lines, step, round, candidate, attempt)` and `Standing`;
  - `hilclaw/checks_tool.py` lines 1-68 (module docstring), `log_lines` and `checks_of` (lines 219-306). Read the log with `log_lines`. Use `checks_of` for `run_file_invalid` on a bad step line, for `check_result_invalid`, and for the ordered end lines carrying `execution`;
  - `hilclaw/spec_file.py`: `parse` (line 205) and `final_name` (line 256), with the errors `InvalidSpecFileError` and `UnsupportedVersionError`;
  - `hilclaw/layout.py` lines 85-156: `round_dir`, `attempt_dir`, and the number format of `_number`;
  - `hilclaw/check_identity.py`: `STEP_SIM`, `STEP_BOARD`, `SIM`, `BOARD`;
  - `hilclaw/check_result.py` lines 52-61: `PASS`, `FAIL`, `BROKEN`, `CONDITIONS`;
  - `hilclaw/tools.py`: `ToolFailure` and the `KIND_RUN_FILE_*` constants;
  - `hilclaw/run_files.py`: `relative`, `NOT_THERE`.
- `hilclaw/spec_tool.py` lines 1-80 and its `_relative` and `_reported`: how a message names a path relative to the data root and reports an `OSError` without the absolute path. Follow the same message style.
- `tests/test_checks_tool.py` lines 1-60 and its log helpers: how tests write `events.ndjson` step lines.

## Acceptance Criteria

### The module `hilclaw/spec_feedback.py`
1. **Public surface.**
   - One function, for example `attempts(data_root, run_id, round)`. It returns the list of `feedback.attempts` entries of ADR-0151 decision 2 (d) for the spec of `(round, candidate 1, attempt 1)`.
   - One constant, `KIND_FEEDBACK_UNREADABLE = "feedback_unreadable"`.
   - `round` must be an `int` (not a `bool`) from 1 to `hilclaw.keys.MAX_INTEGER`. `run_id` must pass `layout.check_run_id`. A bad argument raises `TypeError` or `ValueError` (or the layout error). It is not a `ToolFailure`, because these are the caller's checks.
   - No registry entry and no command-line front. Slice 2 calls the function from `spec.write`.
2. **Check ⑧: which attempts are found.**
   - Look at candidate 1 of every round `q` with `0 <= q < round`.
   - **The work is bounded by the directories that exist, not by `round`.** For example, list `runs/<run_id>/rounds/` once and take only names that are exactly the `layout` formatting of an integer `q < round`. A request for round 2**53-1 must not loop over every round.
   - In each such round, list `rounds/<QQQQ>/coder/candidates/01/attempts/`. Take each entry whose name is exactly the `layout` formatting of an attempt number and that holds a `spec.json`. Ignore other names. Document that choice in the docstring.
   - Any missing directory on the way gives no attempt and is no failure. That includes the run directory below an existing data root.
   - Read each `spec.json` found and accept it only if all of these hold:
     - `spec_file.parse` accepts it;
     - `spec_file.final_name(data_root, document)` is its own path, which means its `id` is the attempt's tuple and run (ADR-0029 decision 3).
   - Raise `ToolFailure(KIND_FEEDBACK_UNREADABLE, ...)` for each of these:
     - a listing that fails for another reason than not-there;
     - a `spec.json` that is not a regular file or cannot be read;
     - a refusal of `parse`;
     - an `id` that does not match the path.

     The message starts with the path relative to the data root and never shows the absolute path.
   - Look at attempts in ascending `(round, attempt)`. The first failure decides.
3. **Check ⑨: the log.**
   - Only when ⑧ found at least one attempt, read the log with `checks_tool.log_lines`. Its kinds pass through unchanged: `run_file_missing`, `run_file_unreadable`, `run_file_invalid`, `run_file_unsupported`. A missing log below an existing data root holds no line, so every attempt is then `undetermined` and none is shown.
   - Then call `checks_tool.checks_of`. Its `inside` admits only these tuples: `step` in `STEP_SIM`/`STEP_BOARD`, a found round, candidate 1, and a found attempt. So `run_file_invalid` and `check_result_invalid` are raised as ADR-0131 decision 3 raises them.
   - Compute each found attempt's standing with `check_standing.standing` at each point.
4. **Which attempts are shown, and the entry form** (ADR-0151 decision 2 (d)):
   - Not shown: an attempt whose sim-point standing is `UNDETERMINED`.
   - Shown, each as `{"round", "candidate": 1, "attempt", "techniques", ["failure"]}`, in ascending `(round, attempt)`. There is never a `profile` member.
   - `techniques` is the `id` of each element of that attempt's own spec's `guidance.techniques`, in its order. Round 0's list is empty.
   - `failure` is present exactly when one of these holds:
     - sim is `NOT_VERIFIED`; the failed point is sim;
     - sim is `VERIFIED` and board is `NOT_VERIFIED`; the failed point is board.

     An attempt that is verified at sim and verified or undetermined at board has no `failure`.
   - **The deciding result** is the first end line, in line order, of the failed point for that attempt whose `result.outcome` is `fail` or `broken`. Take it from `checks_of`'s ordered elements.
   - `stage` is `"compile"` when the deciding result is `broken` with `condition` `build_exit_status` or `build_time_limit`. Otherwise it is `"sim"` or `"board"`, the failed point's name.
   - `report` is a fixed English sentence. It names:
     - the stage;
     - the deciding result's `outcome`;
     - for a broken result, its `condition` in words. Give each of `check_result.CONDITIONS` a phrase. A condition outside that tuple gets a generic phrase and is not echoed raw.

     The report holds **nothing else of the result**: no `counts`, `draws`, `tolerance`, `shape`, `max_abs_error` or any other member (ADR-0002 "No field carries verification inputs"; ADR-0151 decision 2 (d)).
5. **Check ⑩: compiler logs.**
   - Only for `stage` `"compile"`, read `layout.attempt_dir(data_root, run_id, q, "measure", 1, a) / f"build-log-{step}-{execution:02d}.txt"`. `step` and `execution` are those of the deciding result (ADR-0078 decision 3; `:02d` writes a larger number in full).
   - When the file exists and is not empty, append its text to the sentence, separated so that the sentence stays first. Decode strictly as UTF-8 without a byte order mark (ADR-0078 decision 4).
   - A missing file is no failure, and the report is the sentence alone. An empty file gives the same report.
   - Raise `feedback_unreadable` for any other failure: not a regular file, an `OSError`, or bytes that are not UTF-8 or that start with a BOM. The message starts with the relative path.
   - Do all of ⑩ after all of ⑨.
6. **Purity.** Nothing is created, written or kept between calls. `STATE.json`, `instance.json`, `decision/hypotheses.json` and `decision.md` are not read. No argument is modified.
7. **Docstrings.**
   - The module docstring states:
     - the rule (ADR-0151 decision 2 (d) and checks ⑧ to ⑩);
     - the choices that are the module's own (name handling in listings, report sentences, strict decoding, the generic phrase);
     - that nothing calls it until slice 2 (`spec.write`) lands.
   - The public function has a Doxygen-like docstring: arguments, return value, and each kind raised.
   - Keep inline comments to a minimum (CLAUDE.md).
8. **Language**: Python. Record the reason in one line in the commit body and in `Result` (CLAUDE.md language policy).

### Tests `tests/test_spec_feedback.py` (fixture files only)
9. **Happy paths.** Each test checks the exact entry list, and that a version-2 spec document holding that list as `feedback.attempts` passes `hilclaw.spec.validate`. Build that document like `tests/test_spec_tool.py` does, or minimally.
   - Round 1 after a round 0 attempt that passed at sim and board: one entry, `techniques` `[]`, no `failure`.
   - Round 1 after a round 0 attempt broken with `build_exit_status`, with a compiler log file: `stage` `compile`, and the report is the sentence followed by the log text. Repeat with the log missing, then with the log empty: the sentence alone.
   - Round 4 as in ADR-0151's Walk-through, row 3:
     - round 1 with techniques `["a", "b"]` and a `fail` at sim, giving `stage` `sim`;
     - round 2 `undetermined` at sim, not shown;
     - round 3 verified at sim with no board line, shown without `failure`.

     The order and the techniques must be exact.
   - A board failure after a sim pass: `stage` `board`. A broken board result with `build_time_limit`: `stage` `compile`, and the board step's log name is read.
   - Several executions at one point: the first fail/broken line in line order decides, and its `execution` names the log file.
10. **Branch cases.**
    - No run directory: `[]`.
    - Rounds directory present but no attempts: `[]`.
    - Attempts found but no log: `[]`.
    - Round directories at or above `round` are ignored.
    - Non-attempt names (`tmp`, `1`, `001`) are ignored.
    - An attempt directory without `spec.json` is ignored.
    - A huge `round` (2**53-1) returns promptly.
    - A class (i) failure line alone at sim gives undetermined, not shown.
11. **Negative and error cases.** Each gets its kind, and a message with a relative path and no absolute path:
    - a `spec.json` that is not JSON, of version 1, a directory, or with an `id` of another attempt or run: `feedback_unreadable`;
    - an unreadable listing: `feedback_unreadable`. Simulate it with monkeypatch if permissions are unreliable on the CI or on Windows;
    - a damaged log line: `run_file_invalid`;
    - a log line of another version: `run_file_unsupported`;
    - a result without `outcome` on an admitted line: `check_result_invalid`;
    - a compiler log that is a directory, not UTF-8, or starts with a BOM: `feedback_unreadable`;
    - bad arguments: `round` 0, `True`, `-1`, `2**53`, a `str`; a bad `run_id`;
    - a report never contains `counts`, `draws`, `tolerance`, `shape` or `max_abs_error` values, even when the result holds them;
    - nothing is created below the data root (compare the tree before and after);
    - **check order**: a bad `spec.json` is reported before a damaged log, and a damaged log before a bad compiler log.
12. **Gates.**
    - `python -m pytest` passes.
    - `python -m ruff check .` and `python -m ruff format --check .` are clean.
    - The coverage gate in `.github/workflows/` is met: line >= 80% and function >= 80% for `hilclaw/`. The new module itself should be near 100%.
    - Every public function of the new module is tested (CLAUDE.md test rule ③). The test file exists (rule ④).

### Process
13. Before review, `git diff origin/main --stat` lists only `touchesFiles`. Record the non-test LOC; the cap is 300 LOC in 5 files, tests excluded. If the module outgrows the cap, propose a split in `Follow-ups` and finish the current scope.
14. Open a Draft PR (title with `T-0415`). Run the `dev-reviewer` cycle (dev-code-review) for at most 7 rounds. Ask the reviewer explicitly to check:
    - (a) every rule of criteria 2 to 5 against ADR-0151 decision 2 (d) and decision 3 ⑧ to ⑩;
    - (b) that no report can carry a verification input or a result member other than `outcome` and `condition`;
    - (c) that `log_lines`, `checks_of` and `standing` are reused, not re-implemented;
    - (d) that nothing of HQ-0048, HQ-0053, HQ-0021 or HQ-0026 is decided.

    A finding that starts with `SECURITY` is BLOCKED.
15. With CI green and Approve, squash-merge with `gh pr merge --squash --body` (PR body ending in `Task: T-0415`) and delete the branch. Record the PR, the merge commit, the review rounds and the language reason in `Result`.

## Out of Scope

- `hilclaw/spec_tool.py` and `hilclaw/catalog.py`, and their docstrings: the request member `techniques`, check ⑦, the catalog kinds, and the call of this module. That is slice 2, the next task.
- Any registry, MCP or command-line exposure of this module.
- `profile`, `feedback.base`, repair specs, N > 1, ranking (OD-7), and lineage (OD-20).
- Writing compiler logs (ADR-0078 code, HQ-0026), `cpu_standin` check operations (HQ-0021), the selection side (HQ-0048), and the coder's start (HQ-0053).
- Any data-plane schema change; edits of `ARCHITECTURE/`, `orchestration/`, `catalog/`, `.claude/`, `.github/`, `PROCESS/` (other than this task's `Result`), settings files and `HIL-Claw-data`.

## Follow-ups

- (planner) Slice 2 of ADR-0151: `hilclaw/spec_tool.py` + `tests/test_spec_tool.py`. It adds the request member `techniques` (required exactly for round >= 1), check ⑦ through `hilclaw.catalog`, the kinds `catalog_unusable`, `technique_unknown` and `technique_not_applicable`, and the call of this module for ⑧ to ⑩. It updates the docstrings of `spec_tool.py` and `catalog.py`.

## Result

- **Outcome**: DONE. PR #242 squash-merged into `main` as `e17b52e`; branch `claude/T-0415-spec-feedback-attempts` deleted; squash message ends with `Task: T-0415`.
- **Review**: 3 rounds (dev-reviewer, Approve each round, no SECURITY). R1 Low: three compile-log tests compared only part of the result (fixed `d40345c`). R2 Low: two board tests and the order test likewise (fixed `f5f373d`). R3: two Nits left as they are (redundant `named and` in `_failure`; one duplicate `startswith` assertion in a test).
- **CI**: green on `f5f373d` (Python gate 3.11/3.14, Coverage gate, Test presence, C gate, sh gate). Local: full suite passed, ruff check/format clean, `hilclaw/` coverage 97%, new module 100%.
- **Language**: Python - the module reuses the Python readers already in `hilclaw/` (spec file, log, standing).
- **Size**: 289 non-test LOC in one file; only the two `touchesFiles` changed.
- **What landed**: `hilclaw/spec_feedback.py` with `attempts(data_root, run_id, round)` and `KIND_FEEDBACK_UNREADABLE` (ADR-0151 decision 2 (d), checks 8-10). Check 8 lists `rounds/` once and takes only exact `layout` names; each spec must pass `spec_file.parse` and `final_name`. Check 9 reuses `checks_tool.log_lines`, `checks_tool.checks_of`, `check_standing.standing`. Check 10 runs after all of 9, decodes the compiler log strictly as UTF-8 and refuses a BOM. The report is one fixed sentence (stage, point, `outcome`, a fixed phrase per `CONDITIONS` value; an unknown condition gets a generic phrase and is not echoed). No registry entry, no CLI front, no caller yet.
- **Not decided**: nothing of HQ-0048, HQ-0053, HQ-0021, HQ-0026; no data-plane change (reviewer confirmed).
- **Follow-up**: ADR-0151 slice 2 (already in Follow-ups): `hilclaw/spec_tool.py` + `tests/test_spec_tool.py` - request member `techniques`, check 7 via `hilclaw.catalog`, the three catalog kinds, calling `spec_feedback.attempts` for checks 8-10, docstring updates in `spec_tool.py` and `catalog.py`.
