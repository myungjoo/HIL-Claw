---
id: T-0349
title: Add hilclaw/run_commit.py — the read-only owed rule and the registry tool run.commit of ADR-0127 decision 4, in the default registry (ADR-0127 slice (1); PLAN P2-1)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-13, NFR-1, OD-8, S0, S1, S2]
dependsOn: [T-0348, T-0342]
touchesFiles:
  - hilclaw/run_commit.py
  - hilclaw/tools.py
  - tests/test_run_commit.py
  - tests/test___main__.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_tools.py
estimatedSize: {loc: 280, files: 2}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager prompt and round 0) is the first unchecked item of the P2 order (D18). This task is a slice of it, so the D18 rule for non-checklist work does not apply. The P2-5 run needs it: ADR-0127 (OD-8 sub-question ⑪, first-case runs) has the Round-Manager commit the data repository at every round end through one typed tool, `run.commit`. Without that tool, a five-round run leaves no history in `HIL-Claw-data`, which goes against #5 A-3.

This is slice (1) of ADR-0127 Consequences. It adds a new layer-2 module that holds two things: the rule of an owed round end as a read-only public function, and the commit made over that rule. The module adds the tool to `default_registry`. Slices (2) and (3) come later and are out of scope here. Slice (2) is the step-0 entry and the tool list in `orchestration/round-manager.md`. Slice (3) is owed P2 in `hilclaw/further_turn.py` and `hilclaw/turn_start.py`, which will call the read-only function added here, so this task keeps that function separate from the commit.

Open HQs checked: HQ-0043 (#5 A-3, the commit of a turn cut short) does not block this slice. ADR-0127 decision 8 leaves that case open, and this tool makes no commit inside a round. HQ-0032, HQ-0040 and HQ-0041 concern other functions. The remaining open HQs are runtime-acceptance notices or concern other tasks.

ADR-0127 decision 4 says "an owed commit needs the key directory and `instance.json` gives none". This task reads that sentence as follows, and the reading needs no new decision. The key directory is needed only when the owed range *H*..*W* − 1 holds a round ≥ 1, because round 0 has no case (ADR-0072 decision 3; `hilclaw.layout.case_record`). "Gives none" covers three cases: `instance.json` is missing, it is not valid by `hilclaw.instance.read`, or it states no `op_signature`. If the reviewer finds this reading to be a choice that the ADR does not make, the executor stops and returns BLOCKED (`requirement-unclear`). It does not pick a different reading.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, code-task test rule).
- `CLAUDE.md`, "상시 규칙": the tool-layer language policy, the code-mode branch and merge procedure (A-13), the test rule (D12), "개발 드라이버와 런타임의 구분" (D16), and "코멘트 최소화".
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`: Decision §1, §2, §3, §4 (whole, with the table) and §5; §6 only for what the read-only function must serve later; the Walk-through; Consequences, slice (1); and the "Less exact" bullet on `hilclaw/events.py`, which is not edited here.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`: decisions 2 and 3. These are the model for a registry tool that is not an FR-10 tool and is not journaled.
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: decisions 3 and 4 (the data-root source, `run_id`).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: decision 4 (MCP name).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md`: decision 6 (torn tail).
- `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md`: decision 3, "Git" bullet (temporary files).
- `ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md`: decisions 1 and 3 (the case file's place, and no case for round 0).
- Code to read (model and APIs):
  - `hilclaw/run_file_tools.py`, whole: the closest model for definitions, request checking, `_RUN_ID_SCHEMA`, descriptions and failure kinds.
  - `hilclaw/tools.py`: `ToolFailure`, the `KIND_*` constants, `ToolDefinition` and `default_registry`.
  - `hilclaw/data_root_source.py`: `obtain`.
  - `hilclaw/run_state.py`: `parse`, `InvalidStateError`, `UnsupportedVersionError`.
  - `hilclaw/events.py`: `remove_torn_tail` and `CorruptEventsError`.
  - `hilclaw/instance.py`: `read`, `Instance` (`hw_profile_key`, `op_signature.key`), `MissingInstanceError`, `InvalidInstanceError`, `UnsupportedVersionError`.
  - `hilclaw/layout.py`: `check_run_id`, `run_dir`, `run_file`, `case_record`.
  - `hilclaw/config.py`: module docstring only (it "runs no `git`").
- Tests to read: `tests/test_run_file_tools.py` as the model. Also the places that list the default registry's tool names, so that the new tool is added there: `tests/test___main__.py`, `tests/test_blob_tools.py`, `tests/test_check_definition.py`, `tests/test_default_registry_schemas.py` (`ACCEPTED`), `tests/test_mcp_front.py` and `tests/test_tools.py`.

## Acceptance Criteria

1. **New module `hilclaw/run_commit.py`**, in Python. The executor records the choice and its reason in one line of the commit body, under the language policy. The module docstring states the ADR-0127 scope and the tool. It uses the `git` program of the machine through `subprocess`, with an argument list and no shell. It adds no package and no new external dependency. The module exposes at least:
   - **a read-only public function** that answers ADR-0127 decision 4's rule of an owed round end for `(data_root, run_id)`. It returns whether a round end is owed, and, when one is owed, the range *H*..*W* − 1. In every case it writes nothing to the working tree, the index or `HEAD`. It raises distinct exceptions, or returns a distinct outcome, for each of the following, so that slice (3) can tell them apart: no repository, `git` that cannot be run, and each `commit_refused` condition that decision 4 checks "at every call". The other `commit_refused` conditions are checked only when a round end is owed: a file that `HEAD` holds below `runs/<run_id>/` is missing from the working tree, `events.ndjson` is not a regular file, or the key directory is needed and missing;
   - **a function that returns the tool definition of `run.commit`**, bound to a data-root source, in the shape of `run_file_tools.definitions`. It raises `TypeError` for a source that is not callable.
2. **The tool `run.commit`** (MCP `mcp__hilclaw__run_commit`) follows ADR-0127 decision 4 and its table exactly:
   - The request is exactly `{"run_id": ...}`. Any other member, a missing member, or a `run_id` that `layout.check_run_id` refuses is `invalid_request`. The input schema has the same form as `run_file_tools` (`additionalProperties: false`, the same `run_id` pattern). The data root comes from `data_root_source.obtain(source)`, which is asked only after the request was checked; when it fails, the call ends with `no_data_root`.
   - The result is `{"committed": true|false}`.
   - **Nothing owed** gives `committed` false, and nothing is written or removed. This covers the case where neither the working tree nor `HEAD` holds the run's `STATE.json` (no run directory, or a fresh one), the case *W* = *H*, and a repository with no commit yet when the working tree has no `STATE.json` or *W* = 0.
   - **Owed** runs three steps in this order. (i) `events.remove_torn_tail` removes a torn tail. (ii) One commit is made. It holds, against `HEAD`, every new or changed file below `runs/<run_id>/`, plus the existing case files `case-<run_id>-<RRRR>.json` for each round *r* in *H*..*W* − 1 with *r* ≥ 1. The case-file paths are built with `layout.case_record` from `instance.json`'s `hw_profile_key` and `op_signature.key`, without listing the key directory. No other path's changes go in. Whatever else the index or working tree holds is left as it is after the call. A path that already sits in the index outside those paths stays staged and uncommitted. (iii) The result is `committed` true. With no `HEAD`, the commit made is the repository's first.
   - **Never taken in**: any path whose name ends with `.tmp`, whatever the ignore file says; any path the repository ignores; anything below `blobs/`. File content is not inspected.
   - **`no_repository`**: the data root is not the top directory of a git working tree. This includes a data root that sits below the top of another repository. The kind is also used when `git` cannot be run.
   - **`commit_refused`**, with nothing removed or committed. The conditions are exactly those of decision 4. Each is checked at the moment decision 4 gives for it.
   - **`commit_not_made`**: the torn-tail removal failed with an `OSError`, or `git` did not make the commit. `HEAD` is as it was before the call.
   - The commit message and author are not fixed by the ADR. The executor picks a fixed plain message. It sets no author: git's own identity resolution applies, and the tests supply an identity. Nothing reads the message.
   - The tool is not journaled, appends nothing to `events.ndjson`, and selects no backend.
   - The description text tells the model what the tool does, states that the data root is never part of the request, and lists its failure kinds, in the manner of `run_file_tools._DESCRIPTIONS`.
3. **`hilclaw/tools.py`**: `default_registry` registers `run.commit` from the new module, in the source only, and its docstring names the tool and ADR-0127. Building the registry still imports no NumPy (`tests/test_check_definition.py`).
4. **Tests** in a new file `tests/test_run_commit.py`. Each test runs against a temporary git repository created by the test, with an author identity set in that repository (or through the test's environment) and with global and system git configuration isolated from the machine (for example `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_NOSYSTEM`). No `claude` is started, stub or real. The tests must pass on Linux CI and on the local Windows machine. The tests cover at least:
   - happy: the round-0 end of a fresh run is committed with `instance.json`, `STATE.json` and `events.ndjson` (the Walk-through row "Round 0 ends"); a later round end commits only the changed files and the case files of *H*..*W* − 1; a second call afterwards gives `committed` false and creates no new commit; the first commit of a repository without `HEAD`;
   - branch: *W* = *H* gives no commit, also when files of the run changed inside the round; the case file of a round in the range is taken in when it exists and skipped when it does not; round 0 needs no key directory, even when `instance.json` states no `op_signature`; a torn tail is removed before the commit, and the committed `events.ndjson` ends with a line feed;
   - exclusion: a `STATE.json.<token>.tmp` in the run directory, an ignored path, a file below `blobs/`, another run's changed file and a changed `db/` file of the key directory that is not a case file of the range all stay out of the commit and are left unchanged; an entry that was already staged elsewhere stays staged;
   - negative and error: each `invalid_request` form; `no_data_root`; `no_repository` for a plain directory, for a data root below another repository's top, and for `git` that cannot be run (through a seam or `PATH`, not by uninstalling `git`); every `commit_refused` condition of decision 4, each checked to leave `HEAD`, the index and the torn tail as they were; `commit_not_made` when `git` refuses the commit (for example, no author identity, or a held `index.lock`), with `HEAD` unchanged;
   - the read-only function: the same states as above give the expected answer, and leave the working tree, the index and `HEAD` byte-for-byte as they were;
   - registry: `run.commit` is listed by `default_registry` and through the MCP front as `run_commit`. The listing tests in the six files of `touchesFiles` are updated, and `tests/test_default_registry_schemas.py` gets an `ACCEPTED` entry.
5. **D12**: line and function coverage of `hilclaw/` stays at 80 % or more. Every public function of `hilclaw/run_commit.py` is tested. The tests include negative cases. No test is added that targets test code, CI or hooks.
6. **No data-plane change**: no member, file, kind of event, value or version of `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json` or the case file is added, and no validator changes. If the work turns out to need one, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
7. Code mode (A-13): a Draft PR, the reviewer cycle with Approve, CI green, then squash-merge with the PR body ending in `Task: T-0349`, and the branch `claude/T-0349-run-commit-tool` deleted.
8. No `claude` process is started, and nothing runtime-only is required (D16). Runtime acceptance items (xv) and (xvi) of ADR-0127 stay with HQ-0044. The task does not try to close them.

## Out of Scope

- `orchestration/round-manager.md` (step 0 of "The entry of a turn", the tool list in "Your run", the call after the round-end write). These are ADR-0127 slice (2) and the slice that writes "The round steps".
- `hilclaw/further_turn.py` and `hilclaw/turn_start.py` (owed P2, step 1). This is ADR-0127 slice (3).
- The less-exact docstrings that ADR-0127 lists (`hilclaw/events.py`, `hilclaw/further_turn.py`, `hilclaw/turn_start.py`) and every ADR wording fix (D18 hold).
- `best.json`, `technique_stats.json` and key record files in the commit; push, remote and unpushed-count visibility; the Stop hook; the lock; removing a stale `git` lock; the commit of a turn cut short (HQ-0043).
- Any change to `hilclaw/config.py` or the `HIL-Claw-data` repository.

## Follow-ups

- Next slices (candidates; code mode; stub `claude` only): ADR-0127 slice (2), `orchestration/round-manager.md` step 0 and `mcp__hilclaw__run_commit` in "Your run"; then slice (3), owed P2 in `hilclaw/further_turn.py` and `hilclaw/turn_start.py` over the read-only function of this task.

## Result

- DONE. PR #199 (Draft → ready), squash-merged as 5507f98; branch claude/T-0349-run-commit-tool deleted. Review: 4 rounds by a context-isolated dev-reviewer, Approve (R1–R3 findings addressed in the PR; R4 no new findings). CI green on head d075f01 (Python 3.11/3.14, Coverage, Test presence, sh, C).
- Language: Python — the tool runs in-process in the package's Python registry and MCP front; git is driven through subprocess with an argument list, no new dependency.
- Added hilclaw/run_commit.py: owed_rounds(data_root, run_id) (read-only rule of ADR-0127 decision 4, returns range(H, W); distinct errors NoRepositoryError, GitNotRunError and one CommitRefusedError subclass per condition: WorkingStateError, HeadStateError, RoundBehindError, StateMissingError at every call; FileMissingError, EventsNotRegularError, NoKeyDirectoryError only when owed; key directory needed only for W >= 2), commit(data_root, run_id) (temporary index from HEAD, run paths and range case files via ls-files --cached --others --exclude-standard, *.tmp dropped, torn tail removed, write-tree/commit-tree, index lock held across a compare-and-swap update-ref, only committed index entries replaced, fallback git reset if the rename fails), and definition(source) for run.commit (mcp__hilclaw__run_commit; kinds invalid_request, no_data_root, no_repository, commit_refused, commit_not_made). A HEAD that resolves to no commit, or a broken branch ref, is HeadStateError; only an unborn branch counts as no HEAD. Fixed message, no author set; variables that point git at another repository are removed from git's environment.
- hilclaw/tools.py default_registry registers run.commit; the listing tests in six files and ACCEPTED in test_default_registry_schemas updated. tests/test_run_commit.py: 68 tests on temporary repositories with GIT_CONFIG_GLOBAL/GIT_CONFIG_NOSYSTEM isolated; coverage of run_commit.py 97 %. No claude started; no data-plane change. Runtime acceptance (xv), (xvi) stay with HQ-0044.
- Follow-ups: ADR-0127 slice (2) (round-manager.md step 0 and the tool list); slice (3) (owed P2 in further_turn/turn_start over owed_rounds); report a failed index replacement plus failed fallback reset (now silent, documented); ADR wording (D18 hold candidate): an ignore rule matching an untracked runs/<run_id>/STATE.json makes every call owed.
