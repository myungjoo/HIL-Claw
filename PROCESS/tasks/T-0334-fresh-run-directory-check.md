---
id: T-0334
title: Add hilclaw.fresh_run.is_fresh, the fresh-run-directory test of ADR-0120 decision 4 (instance.json and no other run-level file), for the turn loop's step-1 predicate and the round-0 entry
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, NFR-1, OD-8, S0, S1]
dependsOn: [T-0330, T-0333]
touchesFiles:
  - hilclaw/fresh_run.py
  - tests/test_fresh_run.py
estimatedSize: {loc: 80, files: 2}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18), and this task is one of its slices, so the D18 priority rule does not apply. The P2-5 run (`cpu_standin` x GEMM, N=1, 5 rounds) cannot start its round 0 until the loop and the Round-Manager can tell a run whose round 0 has not begun.

ADR-0120 (T-0333, main 1386ace) decided, for first-case runs:
- the Round-Manager of the round-0 turn writes the first `STATE.json`, and only into a **fresh** run directory;
- a fresh run directory (decision 4) is one that holds `instance.json` under its final name and no other file of the run tree: no `STATE.json`, `events.ndjson`, `artifacts.json` or `rounds/`. These are the run-level names of ADR-0004 decision 2, each at a known path, so telling it needs no listing;
- a fresh run directory is a started run whose round 0 has not begun, and the turn loop takes it up.

ADR-0120 Consequences names two code slices that need this test:
- slice (3), "the part of the loop's step-1 predicate for decision 4";
- slice (1)/(2), the round-0 entry, which writes the first file only into a fresh directory.

The rest of the predicate waits on the run-status member (rest of OD-8, OD-19). What follows a failed turn waits on OD-10, OD-17, OD-19 and OD-27. The means by which the Round-Manager reaches `replace` waits on OD-23 and OD-18. This task does none of these. It adds only the deterministic test of decision 4, which every one of those slices will call. No design OD is needed: decision 4 fixes the rule, and this task applies it.

Open Draft PR #186 (T-0324, BLOCKED on HQ-0032) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None of them is in this task's touchesFiles.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0334` trailer (also as the last line of the PR body), size cap, test rules.
- `CLAUDE.md`, these rules: "코멘트 최소화", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`:
  - Decision (lines 34-81), in particular decision 3 (lines 54-60, "a check of existence is all this decision asks") and decision 4 (lines 62-69);
  - Consequences, the slices list (lines 92-98).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: the tree (lines 25-60) and decision 2 (lines 80-85).
- `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md`: decision 4 "A leftover" (lines 60-66) and decision 6 "The first file" (lines 77-83).
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`: decision 2 (lines 29-40).
- Code:
  - `hilclaw/layout.py`: the module docstring, `RUN_FILES`, `check_run_id`, `run_dir`, `run_file` and `InvalidPathValueError` (lines 1-83);
  - `hilclaw/run_files.py`: `NOT_THERE` and the convention for "not there" (lines 1-45);
  - `hilclaw/turn_loop.py`: the module docstring (lines 1-90) and `run` (from line 257), for how `further_turn` is called;
  - `tests/test_run_files.py`, as the style of a test module.
- `.github/workflows/ci.yml`: the test-existence step (around line 127), which needs `tests/test_fresh_run.py`.

## Acceptance Criteria

1. **New module `hilclaw/fresh_run.py`** with one public function `is_fresh(data_root, run_id)` that returns a `bool`.
   - It is `True` exactly when both of these hold:
     - `layout.run_file(data_root, run_id, "instance.json")` is a regular file. The check is by `os.stat`, so a symbolic link to a regular file counts;
     - none of `STATE.json`, `events.ndjson`, `artifacts.json` (each through `layout.run_file`) or `layout.run_dir(data_root, run_id) / "rounds"` exists as an entry of any kind. This check is by `os.lstat`, so a broken link, a directory or a file in any of these places counts as present.
   - Paths come from `hilclaw.layout` only, and no path text is repeated.
2. **"Not there"** is an `OSError` in `hilclaw.run_files.NOT_THERE` (`FileNotFoundError`, `NotADirectoryError`), as `run_files` tells it.
   - Any other `OSError` of a check is raised unchanged.
   - An invalid `run_id` raises `layout.InvalidPathValueError` before anything is checked.
   - A missing data root, a missing `runs/` or a missing run directory each give `False`. So does a file in the place of a directory above `instance.json`.
3. **No more than decision 4.**
   - It opens, reads, writes, creates, lists and removes nothing. It reads no content of `instance.json`: no layout stamp and no validation, since ㉗ (가) stays open (ADR-0120 decision 3).
   - A leftover of ADR-0013 decision 4 or ADR-0025 decision 6 does not change the answer, because only known paths are checked.
   - It keeps nothing between calls, is no FR-10 tool and is not registered in `hilclaw.tools`. It does not import `hilclaw.turn_loop`, and `turn_loop` is not changed.
4. **The module docstring** says, briefly:
   - that it applies ADR-0120 decision 4 for the runs of ADR-0076 decision 1;
   - what it does not decide, each with its OD: what a directory with `instance.json`, other files and no `STATE.json` means; what a turn does in a non-fresh run; the rest of the loop's predicate (OD-8, OD-19); a failed turn (OD-10, OD-17, OD-19, OD-27); how the Round-Manager reaches `replace` (OD-23, OD-18); the layout stamp (㉗ (가)).

   The function docstring states the rule and the exceptions. Follow CLAUDE.md "코멘트 최소화": no other comments.
5. **Tests `tests/test_fresh_run.py`**, using `tmp_path` only. Under D12 they cover:
   - **happy**: only `instance.json` gives `True`. So does `instance.json` beside a leftover-shaped temporary file in the run directory.
   - **branch**: each of the four other entries present gives `False`, parametrised over `STATE.json`, `events.ndjson`, `artifacts.json` and `rounds`. Also `False` for:
     - `rounds` as a file and as a directory;
     - `instance.json` as a directory;
     - no `instance.json` and no other file;
     - no run directory;
     - no `runs/`;
     - no data root;
     - `runs/<run_id>` as a file.
   - **links**, each skipped where the platform cannot make symbolic links: `instance.json` as a link to a regular file gives `True`; `STATE.json` as a broken link gives `False`.
   - **negative and error**:
     - an invalid `run_id` (empty, upper-case, `..`, non-`str`) raises `InvalidPathValueError`;
     - a `PermissionError` from `os.stat` or `os.lstat` (monkeypatched) is raised unchanged, not turned into `False`;
     - a `NotADirectoryError` from the patched call gives `False`.
   - **no side effect**: the directory's entries are the same before and after a call. The function returns exactly a `bool`.
   - Coverage of `hilclaw/` stays at or above 80 % line and 80 % function, and the CI test-existence step passes.
6. **D16.** No test and no step starts `claude` (no subcommand, no flag). Nothing needs a board, an accelerator or an API key.
7. **Scope.**
   - `git diff --stat origin/main` lists only touchesFiles, plus this task file's Result.
   - No edit to:
     - `ARCHITECTURE/`, `orchestration/`, `PROCESS/` (other than this file's Result), `.claude/`, `CLAUDE.md`, README or CI;
     - any existing module or test, including `hilclaw/layout.py`, `hilclaw/turn_loop.py` and `hilclaw/run_state_file.py`.
   - No new dependency, and no data-plane change (no member, file, kind, value or version).
8. **Merge (code mode, CLAUDE.md A-13).**
   - Branch `claude/T-0334-fresh-run-directory-check`, with a Draft PR whose title holds `T-0334` and whose body ends with `Task: T-0334`.
   - Context-isolated reviewer cycle (dev-code-review), at most 7 rounds, until Approve. CI green.
   - Then `gh pr merge --squash --body` with that body, and delete the branch.
   - In Result: the language chosen (Python) with a one-line reason.

## Out of Scope

- The round-0 text of `orchestration/round-manager.md`, a helper that writes the first `STATE.json`, the turn loop's command-line entry and a full `further_turn` predicate. These are the next slices, each waiting on the ODs named in Why.
- What a non-fresh directory without `STATE.json` means (ADR-0120 decision 4, open), the run-status member, OD-8 ⑪, OD-18 ⑯ (가), and HQ-0032's question.
- Edits to ADR-0120 or to the earlier records it makes less exact. Anything in PLAN's 보류 section. Anything blocked by HQ-0021..HQ-0029, HQ-0031, HQ-0032 or HQ-0034.

## Follow-ups

- The round-0 entry of `orchestration/round-manager.md` (ADR-0120 slice (1)), calling this test before the first write. It still waits on how the Round-Manager reaches `replace` (OD-23, OD-18), on ⑪, on OD-18 ⑯ (가) and on the baseline's record.
- The full step-1 predicate and the loop's command-line entry, waiting on the run-status member (rest of OD-8, OD-19).

## Result
