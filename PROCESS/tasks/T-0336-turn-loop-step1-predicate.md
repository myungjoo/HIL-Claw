---
id: T-0336
title: Add the turn loop's step-1 predicate of ADR-0121 decision 5 (states P1 to P4 of a first-case run, reading run_status), falling back to the caller's predicate in every other state
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-3, NFR-1, OD-8, OD-19, S0, S1]
dependsOn: [T-0330, T-0334, T-0335]
touchesFiles:
  - hilclaw/further_turn.py
  - tests/test_further_turn.py
estimatedSize: {loc: 150, files: 2}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18). This task is one of its slices, so the D18 priority rule does not apply. The P2-5 run (`cpu_standin` x GEMM, N=1, 5 rounds) needs a turn loop that knows by itself when to start a turn and when a run is over. Today `hilclaw.turn_loop.run` asks a caller-given `further_turn(previous)`, and no caller exists.

ADR-0121 (T-0335, main dc93d57..03d9770) decided, for the runs of ADR-0120 decision 1:
- a top-level `STATE.json` member `run_status`, a string, with one defined value `"over"`; it may be absent, and `schema_version` stays 1 (decision 2);
- a reader treats any present value other than `"over"`, including a non-string, as a value it does not know: it starts no turn and reports the value (decision 2);
- decision 5 gives step 1 of the turn loop four states, and only these:
  - P1: fresh run directory (ADR-0120 decision 4) -> a further turn;
  - P2: `STATE.json` valid, version 1, `run_status` `"over"` -> no further turn;
  - P3: `STATE.json` valid, version 1, `run_status` present with any other value -> no further turn, and the value is reported;
  - P4: `STATE.json` valid, version 1, no `run_status`, and `instance.json` valid, version 1, with `round_budget` -> a further turn, whatever `round` is.
- The loop compares no numbers and writes nothing. Every other state stays open, and there the code asks its caller's predicate (ADR-0121 decision 5, last bullet). This includes "what follows a failed turn" (OD-10, OD-17, OD-19, OD-27).

ADR-0121 Consequences names this code slice. It also states that what `hilclaw/run_state_file.py` accepts does not change, so this is no STATE schema change under A-13. The member is read from the `others` of `hilclaw.run_state.parse`.

**One code-level choice of this task**, for the reviewer to weigh. ADR-0121 says P1 and P4 say "a turn is due, not how often a failing one is retried". If P1 answered `True` after a failed turn, a round-0 turn that keeps failing would leave the directory fresh. The loop would then start turns without end and spend plan usage. So P1 and P4 answer `True` only before the first turn (`previous` is `None`) or after a turn whose exit status was 0. After any other exit status, the caller's predicate decides. P2 and P3 answer `False` whatever `previous` is. This is a reading of the ADR's "open" plus its fallback rule, not a new decision. If the reviewer finds it decides an OD (OD-10, OD-19), return BLOCKED (`requirement-unclear`) rather than inventing.

The loop's command-line entry is not part of this task. It needs the prompt, the definition source and the data root put together, so it is the next slice.

Open Draft PR #186 (T-0324, BLOCKED on HQ-0032) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None of them is in this task's touchesFiles.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0336` trailer (also as the last line of the PR body), size cap, test rules.
- `CLAUDE.md`, these rules: "코멘트 최소화", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`:
  - Decision 1 and 2 (lines 35-46);
  - Decision 5 with its table (lines 73-86);
  - Consequences, first two bullets (lines 105-108).
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`: decision 4 (lines 62-69).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: decision 3 (lines 67-90).
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`: decisions 2 and 3 (lines 29-56).
- Code:
  - `hilclaw/turn_loop.py`: the module docstring (lines 1-90) and `run` (from line 257), for how `further_turn` is called and how its answer is checked;
  - `hilclaw/fresh_run.py` (whole file): `is_fresh`;
  - `hilclaw/run_journal.py`: `MissingStateError` and `read_state` (lines 52-88);
  - `hilclaw/run_state.py`: module docstring, `RunState`, `parse` (lines 1-105);
  - `hilclaw/instance.py`: the error classes (lines 597-613) and `read` (lines 848-883);
  - `tests/test_fresh_run.py` and `tests/test_run_state_file.py`, as the style of a test module and for how to make a valid `STATE.json` (`hilclaw.run_state_file.replace`). Find how existing tests build a valid `instance.json` in `tests/test_instance.py` or `tests/test_instance_file.py`.

## Acceptance Criteria

1. **New module `hilclaw/further_turn.py`.** The names below are a suggestion. The executor may rename them if the docstrings say what each one is.
   - `RUN_STATUS = "run_status"` and `OVER = "over"`.
   - `classify(data_root, run_id)` returns a small `NamedTuple`, for example `Finding(case, value)`. `case` is one of five module constants: `FRESH` (P1), `OVER_CASE` (P2), `UNKNOWN_STATUS` (P3, and `value` is the member's value as parsed), `DUE` (P4) and `OPEN` (every other state). `value` is `None` except for P3.
   - `predicate(data_root, run_id, *, fallback, report)` returns a callable `further_turn(previous)` that `hilclaw.turn_loop.run` can take. `fallback` and `report` must be callable. If not, it raises `TypeError` at once, before any file is read. An invalid `run_id` raises `hilclaw.layout.InvalidPathValueError` at once too.
2. **`classify` rules**, in this order:
   - **P1**: `hilclaw.fresh_run.is_fresh(data_root, run_id)` is `True` -> `FRESH`.
   - Otherwise `hilclaw.run_journal.read_state(data_root, run_id)`:
     - `MissingStateError`, `run_state.InvalidStateError` or `run_state.UnsupportedVersionError` -> `OPEN`.
     - `run_status` in `others` equal to the string `"over"` (exactly that `str`) -> `OVER_CASE` (P2).
     - `run_status` present with any other value (another string, `null`, a number, `true`, an object, a list) -> `UNKNOWN_STATUS`, carrying that value (P3).
     - `run_status` absent: `hilclaw.instance.read(data_root, run_id)`.
       - `MissingInstanceError`, `InvalidInstanceError` or `UnsupportedVersionError` -> `OPEN`.
       - A `round_budget` of `None` -> `OPEN` (㉙ (나)).
       - A `round_budget` that is an `int` -> `DUE` (P4). `round` is not compared with it.
   - Any other `OSError` is raised unchanged and is not turned into a case. This includes a data root that is no existing directory, which `read_state` reports as `FileNotFoundError` or `NotADirectoryError`.
3. **`further_turn(previous)` rules.** It calls `classify` afresh at every call and keeps nothing between calls.
   - `OVER_CASE` -> `False`.
   - `UNKNOWN_STATUS` -> calls `report(value)` once, then returns `False`. If `report` raises, the exception passes through.
   - `FRESH` or `DUE`: `previous` `None` or `0` -> `True`. Any other `previous` -> the answer of `fallback(previous)`, returned unchanged (the loop checks it is a `bool`).
   - `OPEN` -> the answer of `fallback(previous)`, returned unchanged.
   - `fallback` and `report` are not called in any other case.
4. **No more than ADR-0121 decision 5.**
   - It writes, creates and removes nothing in the run, and it lists no directory.
   - It compares no number. It does not interpret `round`, `budget_spent` or any other member.
   - It is no FR-10 tool and is not registered in `hilclaw.tools`.
   - It may import `hilclaw.turn_loop` only for documentation or typing, or not at all; `turn_loop` is not changed.
   - It does not prevent two loops on one run (rest of OD-17).
   - It does not run the loop and has no command-line entry.
5. **Docstrings.** The module docstring says, briefly:
   - that it applies ADR-0121 decision 5 (with ADR-0120 decision 4 for P1) for the runs of ADR-0120 decision 1;
   - the code-level choice on `previous` from Why, with its reason;
   - what stays open, each with its OD: a run without `round_budget` (OD-8 ㉙ (나)); missing, invalid or other-version files beyond P1 (OD-8); what follows a failed turn (OD-10, OD-17, OD-19, OD-27); the lock of two loops (rest of OD-17); ⑪ (a run over whose commit is owed); the command-line entry (next slice).

   Each public function's docstring states its rule and what it raises. Follow CLAUDE.md "코멘트 최소화": no other comments.
6. **Tests `tests/test_further_turn.py`**, using `tmp_path` only. Make files with `hilclaw.run_state_file.replace` (with `others`), `hilclaw.instance_file.write` or the existing test builders. Under D12 they cover:
   - **happy**:
     - P1: a fresh directory gives `FRESH`, and `further_turn(None)` gives `True`.
     - P2: `run_status` `"over"` gives `OVER_CASE` and `False`, for `previous` `None`, `0` and `1`.
     - P4: no `run_status` and `round_budget` 5 gives `DUE`. `further_turn` is `True` for `previous` `None` and `0`, also when `round` is 0, 4, 5 or 9 (no comparison).
   - **branch**:
     - P3, parametrised over `"stopped"`, `"Over"`, `""`, `None`, `1`, `True`, `{}` and `[]`: gives `UNKNOWN_STATUS` with that value. `further_turn` calls `report` once with it and returns `False`.
     - `OPEN`, each case calls `fallback` with `previous` and returns its answer (`True` in one test and `False` in another):
       - `STATE.json` missing but other run files present (for example `events.ndjson`);
       - `STATE.json` invalid (bad JSON; a directory in its place);
       - `STATE.json` of `schema_version` 2;
       - `instance.json` missing, invalid or of another version beside a valid `STATE.json` without `run_status`;
       - `instance.json` without `round_budget`.
     - P1 and P4 with `previous` `1`, `-9` and `2` call `fallback` with that value and return its answer.
     - `fallback` and `report` are not called in P2, nor in P1 or P4 with `previous` `None` or `0` (a recording stub).
     - The answer changes between calls when the files change, for example fresh -> P4 -> P2, which shows nothing is kept.
   - **negative and error**:
     - `predicate` with a non-callable `fallback` or `report` raises `TypeError` and reads no file (patch `classify` or `is_fresh` to fail if called);
     - an invalid `run_id` (empty, upper-case, `..`, non-`str`) raises `InvalidPathValueError`, from `predicate` and from `classify`;
     - a `PermissionError` from the `STATE.json` read (monkeypatched) is raised unchanged;
     - a data root that does not exist raises `FileNotFoundError`;
     - an exception from `report` or `fallback` passes through.
   - **with the loop**: `hilclaw.turn_loop.run(further_turn=predicate(...), ...)` on a run in P2 returns an empty tuple and starts no process. Do not put a `claude` on the `PATH` for this test; patch `shutil.which` to fail the test if it is called.
   - **no side effect**: the run directory's entries and bytes are the same before and after `classify` and `further_turn`.
   - Coverage of `hilclaw/` stays at or above 80 % line and 80 % function, and the CI test-existence step passes.
7. **D16.** No test and no step starts `claude` (no subcommand, no flag), real or stub. Nothing needs a board, an accelerator or an API key.
8. **Scope.**
   - `git diff --stat origin/main` lists only touchesFiles, plus this task file's Result.
   - No edit to:
     - `ARCHITECTURE/`, `orchestration/`, `PROCESS/` (other than this file's Result), `.claude/`, `CLAUDE.md`, README or CI;
     - any existing module or test, including `hilclaw/turn_loop.py` (its docstring's "no command-line entry, which waits on the OD-8 member…" stays as is), `hilclaw/run_state.py`, `hilclaw/run_state_file.py`, `hilclaw/fresh_run.py` and `hilclaw/instance.py`.
   - No new dependency. No data-plane change: no member, file, kind, value or version, and no change to what any validator accepts.
9. **Merge (code mode, CLAUDE.md A-13).**
   - Branch `claude/T-0336-turn-loop-step1-predicate`, with a Draft PR whose title holds `T-0336` and whose body ends with `Task: T-0336`.
   - Context-isolated reviewer cycle (dev-code-review), at most 7 rounds, until Approve. CI green.
   - Then `gh pr merge --squash --body` with that body, and delete the branch.
   - In Result: the language chosen (Python) with a one-line reason.

## Out of Scope

- The loop's command-line entry: data root from `hilclaw.config`, prompt, `put_definition` from `hilclaw.turn_definition.put`, and how the result is reported.
- Writing `run_status` (the Round-Manager's write; ADR-0121 decision 3), the round-0 text of `orchestration/round-manager.md`, and how the Round-Manager reaches `replace` (OD-23, OD-18).
- What follows a failed turn beyond handing it to `fallback` (OD-10, OD-17, OD-19, OD-27), OD-8 ⑪, ㉙ (나), OD-18 ⑯ (가), and HQ-0032's question.
- Edits to ADR-0121, to the earlier records and docstrings it lists as less exact, or to the OD-28 register row. Anything in PLAN's 보류 section. Anything blocked by HQ-0013..HQ-0035.

## Follow-ups

- The loop's command-line entry, composing `turn_loop.run`, `turn_definition.put`, this predicate and `hilclaw.config`. Its tests use a stub `claude` only (D16). When it lands, the `turn_loop.py` docstring sentence on the missing entry can be corrected in the same task.
- The remaining P2-1 slices: OD-18 ⑯ (가), OD-8 ⑪, how the Round-Manager reaches `replace` (OD-23, OD-18), then the round-0 part of the Round-Manager prompt.

## Result

- Language: Python, because the predicate composes the existing Python readers (`fresh_run`, `run_journal`, `instance`) and is called in-process by `hilclaw.turn_loop.run`.
- Added `hilclaw/further_turn.py` (`classify`, `predicate`, `Finding`, the five case constants, `RUN_STATUS`, `OVER`) and `tests/test_further_turn.py`. Local: ruff check/format clean, full pytest green, `hilclaw/further_turn.py` 100 % line coverage, `hilclaw/` total 98 %.
- The loop test is skipped where a marker (for example a stray `CLAUDE.md` in the system temporary directory, as on this machine) lies above the test's temporary directory, as `tests/test_turn_loop.py` does; it was run locally with a marker-free `--basetemp` and passed.
- Follow-up for the command-line entry slice: a turn that exits with 0 and leaves the run unchanged (no first `STATE.json` in P1, no `round` moved in P4) is answered with a further turn again by this predicate, as ADR-0121 decision 5 has it; the entry must not assume this predicate bounds plan usage (OD-10, OD-19).
- PR #192 (squash-merged). Review: 2 rounds, Approve (round 1 Approve with one Minor and two Nits: the exit-0 docstring note and follow-up added, a duplicate test dropped, the public-name test kept; round 2 Approve, no findings). The reviewer found the code-level choice on `previous` decides no OD (OD-10, OD-19): it hands the open case to the caller's predicate.
