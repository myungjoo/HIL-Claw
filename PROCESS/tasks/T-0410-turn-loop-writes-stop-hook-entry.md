---
id: T-0410
title: Have the turn loop take the run id and write the Stop entry of ADR-0148 into the session's .claude/settings.json, and have turn_start pass its run id (ADR-0148 code slice 2; PLAN P2-4)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-11, NFR-1, OD-18, "PLAN P2-4"]
dependsOn: [T-0408, T-0409]
touchesFiles: [hilclaw/turn_loop.py, hilclaw/turn_start.py, hilclaw/stop_check.py, tests/test_turn_loop.py, tests/test_turn_start.py, tests/test_further_turn.py, tests/test_turn_definition.py]
estimatedSize: {loc: 70, files: 3}   # non-test: hilclaw/turn_loop.py (~50 with docstring), hilclaw/turn_start.py (~10, call and docstring), hilclaw/stop_check.py (docstring only, ~4); the four test files are excluded from the cap (D4)
hq: []
---
## Why

PLAN P2-4 covers the runtime hooks: "PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제". It is a checklist item in the group that PLAN's P2 header puts before P2-5, so the D18 priority rule (DRIVER §6) does not apply to it.

ADR-0148 (landed as `4dbe250`, T-0408) adopts a `Stop` command hook for the turn sessions of the runs of ADR-0120 decision 1. Its Consequences name two code slices:
- **Slice 1**, the hook program `hilclaw/stop_check.py`, landed as `fed5f9a` (T-0409, PR #239). It is not registered anywhere yet, so today no stop of a turn session is checked.
- **This task is slice 2**: `hilclaw.turn_loop.run` gains a required keyword-only `run_id`, checks it as `hilclaw.layout.check_run_id` does, and writes one `Stop` entry beside the two `PreToolUse` entries of the session's `.claude/settings.json`; `hilclaw/turn_start.py` passes its run id; the docstrings of both modules (and the "not registered here" paragraph of `stop_check`) are rewritten.

**No open HQ holds this slice.** HQ-0063 (ADR-0148 items (lxiii) to (lxvi)), HQ-0061 (ADR-0146 items (lvi) to (lx)) and HQ-0062 are runtime acceptance items; they do not block code tested with a stub `claude` (T-0407 and T-0409 read them so). HQ-0053, HQ-0021, HQ-0026 and HQ-0048 are unrelated.

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED by HQ-0032) touches only `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`.

**Why four test files.** `run_id` becomes a required keyword, so every call of `turn_loop.run` without it fails with `TypeError`. Besides `hilclaw/turn_start.py`, the only callers are tests: `tests/test_turn_loop.py` (the `go` helper), `tests/test_further_turn.py` (one call, near line 557) and `tests/test_turn_definition.py` (two calls, near lines 250 and 273). Those calls gain `run_id` and nothing else.

**Test rule.** `hilclaw/turn_loop.py`, `hilclaw/turn_start.py` and `hilclaw/stop_check.py` are modules of the layer-2 package, so rules ① to ④ of CLAUDE.md "테스트 규칙" apply (DRIVER §5, D12), as for T-0403, T-0404, T-0406, T-0407 and T-0409, whose reviewers accepted that reading. The stub `claude` scripts inside the test files are test fixtures: extending them is test code and gets no test of its own (rule ⑤).

**D16.** Nothing here starts `claude`. Every test uses the stub `claude` that the tests write. The hooks the stub runs are Python interpreters and the machine's `git`, not `claude`.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0410-<slug>`, PR title containing `T-0410`, trailer `Task: T-0410`, `Task: T-0410` as the PR body's last line); the D4 size cap; code-task test rules ① to ⑤; the language line in `Result`.
- `CLAUDE.md`, 상시 규칙: "코멘트 최소화", "세 층 모델", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ① to ⑤, "미결은 발명하지 않는다".
- `ARCHITECTURE/decisions/ADR-0148-od18-first-case-stop-hook-commit.md`. Binding parts:
  - decision 4 (lines 85-92), especially "The run" and "Delivery": no `matcher`, exec form, `args` = interpreter options, the start text, the package directory, the run id, the data root; a `timeout` well below the 600-second default; **no `onFailure`**; the loop reads nothing by the run id and compares it with nothing;
  - decision 5 (lines 94-109) and the Walk-through (lines 111-127), for the stub-level hook tests;
  - Consequences slice 2 (line 150), runtime items (lines 153-157) and the code line of "Less exact, not edited" (line 162).
  Skim Status (lines 3-22).
- `hilclaw/turn_loop.py` (463 lines, all). Note `_entry` (lines 299-307, it always writes `matcher` and `"onFailure": "block"`), `_settings_text` (lines 310-320), `run` (lines 417-463), the docstring sections "Decided by ADR-0146", "Decided by ADR-0147", "The hook settings", "What is raised" and the runtime-items paragraph.
- `hilclaw/turn_start.py` lines 1-20 (docstring on the one call of the loop), 100-115 (docstring tail), 237-275 (`_start`, `_looped`).
- `hilclaw/stop_check.py` lines 1-84 (docstring, `START`, `REFUSAL`, `EXIT_*`). Read only, except the paragraph at lines 42-44 ("This module is not registered here …"), which this task rewrites.
- `hilclaw/budget_check.py` lines 1-60 (how its docstring names the turn loop that registers it). Read only.
- `hilclaw/layout.py` lines 56-73 (`InvalidPathValueError`, `check_run_id`).
- Tests to follow:
  - `tests/test_turn_loop.py` lines 1-60 (constants), 62-181 (the `STUB` script and `Stub` class, which run the `PreToolUse` entries for `hook_inputs`), 183-260 (fixtures, `put`, `go`), 1000-1110 (`expected_settings`, `settings_text`, `hook_input`, `stated`, `hooks_run`) and the tests at about lines 1117-1431 (settings content, real data root, placeholders, hooks run as written);
  - `tests/test_stop_check.py` lines 75-180 (`isolated_git`, `git`, `head`, `new_repository`, `root`, `write_instance`, `write_state`, `write_events`, `a_run`, `commit_by_hand`): copy what you need into `tests/test_turn_loop.py` to build a data checkout in which a commit is owed or not. Do not import from another test module;
  - `tests/test_turn_start.py` lines 1-60, 85-275 (constants, `EDGE_IDS`, its own `STUB` and `Stub`), 443-512 (`start`, `go`) and 586-620 (run-id tests);
  - `tests/test_further_turn.py` around line 557 and `tests/test_turn_definition.py` around lines 248-285 (the other calls of `turn_loop.run`).
- `.github/workflows/ci.yml` jobs `Test presence (hilclaw)` and `Coverage gate (hilclaw)` (search for the job names). Read only.

## Acceptance Criteria

### `hilclaw/turn_loop.py` (ADR-0148 decision 4)
1. **`run_id`.** `run` gains a **required keyword-only** parameter `run_id`. It is checked with `hilclaw.layout.check_run_id` before the first turn, before any session directory is made and before `further_turn` is first called. A refused value raises `hilclaw.layout.InvalidPathValueError` (a `ValueError`) unchanged; a missing argument is Python's own `TypeError`. The loop reads no file by the run id, never compares it with the prompt or anything else, and does not put it into the prompt, the server configuration, the session's environment or any other place than the `Stop` entry's `args`.
2. **The `Stop` entry.** The settings text gains a second member of `hooks`: `"Stop"`, an array of exactly one entry with **no `matcher` member**, whose `hooks` array holds exactly one hook:
   - `"type": "command"`, `"command"` the absolute path of `sys.executable` (as `_entry` builds it);
   - `"args"`: `-I`, `-c`, `hilclaw.stop_check.START`, `checkout_boundary.PACKAGE_DIRECTORY`, the run id, and the **same real absolute data-root path** that the server entry's `env` and the budget entry's last argument hold;
   - a `"timeout"` well below 600 s. Suggested: a new public constant (for example `STOP_HOOK_TIMEOUT_S`) rather than reusing `HOOK_TIMEOUT_S`, since this hook runs `git` a few times (ADR-0148 item (lxv)); record the value and the reason as a provisional choice;
   - **no `onFailure` member** (it has no effect on `Stop`, H18).

   The two `PreToolUse` entries stay exactly as they are (same matchers, args, timeout, `onFailure`). The settings still hold nothing but `hooks`: no `permissions`, no `env`. `_entry` may be refactored so that it can build a hook without `matcher` and `onFailure`; the `PreToolUse` output must not change by a byte other than what JSON member order of the new `Stop` member adds.
3. **Built once per loop, written in every turn.** The text is built once per call of `run` (as now), so every turn of one loop writes the same `Stop` entry. The existing placeholder refusal (`${CLAUDE_PROJECT_DIR}` and the others in the data root) applies unchanged and still raises before the first turn.
4. **Docstrings.** Rewrite the module docstring and `run`'s docstring:
   - a "**Decided by ADR-0148** and only applied here" paragraph: the `Stop` entry as in criterion 2, the run id as an argument checked as `check_run_id` does and used only there; and that ADR-0148 revises ADR-0146 decision 4 (as revised by ADR-0147 decision 4) to the two `PreToolUse` entries and this one `Stop` entry, and nothing else;
   - the "hook settings" choice: the new timeout and why;
   - "What is raised": the run-id error before the first turn;
   - the runtime-items paragraph: add ADR-0148 items (lxiii) to (lxvi), listed in `hilclaw.stop_check`, and that ADR-0146 (lvi), (lix) and (lx) apply to the `Stop` entry too, (lix) also to its run-id and data-root arguments;
   - `run`'s docstring names `run_id`.

   Keep the style of the existing paragraphs; no multi-line comments.

### `hilclaw/turn_start.py`
5. `_looped` passes the run id it already checked to `turn_loop.run` as `run_id`. The prompt is still built by `prompt(run_id)` and is unchanged. Update the docstring's account of the one call of the loop (lines 9-17) to name the run id. The paragraph "The run of a turn" stays true (ADR-0148 "Not less exact": the run id in the hook's arguments is no place, and the session is not given it); do not rewrite it beyond what is needed. No other behaviour of the entry changes: outcomes, statuses and lines are the same.

### `hilclaw/stop_check.py`
6. Docstring only: rewrite the paragraph at lines 42-44 so it says that `hilclaw.turn_loop` writes the `Stop` entry of the session's settings with the run id and the data root as its last two arguments (present tense). No code change; the tests of `tests/test_stop_check.py` stay as they are and pass.

### Tests (rules ① to ④; test files are excluded from the size cap)
7. **`tests/test_turn_loop.py`**:
   - `go` passes a valid `run_id` by default; `expected_settings`/`settings_text` take the run id and build the full expected object including the `Stop` member. The existing exact-content test then checks the whole file, and a test asserts the `Stop` entry has no `matcher` and its hook no `onFailure`, and its timeout is the new constant and below 600.
   - **Run id, happy**: each of `a`, `7`, `"a" * 64`, `a-b_c`, `run-`, `20261009t012331z-9f3a6c1e0b7d4a52` is accepted and appears unchanged as the second-to-last `Stop` arg; a prompt that does not contain the run id is accepted (no comparison).
   - **Run id, negative**: missing → `TypeError`; `None`, `1`, `b"run-a"`, `""`, `"Run-A"`, `"-a"`, `"a" * 65`, `"a/b"`, `"..\\a"`, `"a b"`, `"a\n"` → `InvalidPathValueError`. For each, no session directory is made, `further_turn` is never called and the stub is never started.
   - **Every turn** of a two-turn loop writes the same `Stop` entry.
   - **Real data root**: a relative data root and (where the platform allows) a symbolic link both give the real absolute path as the `Stop` entry's last arg, equal to the budget entry's last arg and the server `env` value.
   - **Stub runs the `Stop` entry as written.** Extend the `STUB` script and `Stub.install` with a list of stop inputs (for example `stop_inputs`). After the `PreToolUse` part, the stub runs each hook of `settings["hooks"]["Stop"]` (only when present) with each stop input on stdin, as it runs the `PreToolUse` hooks, and records status, stdout and stderr. Using a data root that is a temporary git repository built with the copied helpers (and the `isolated_git` environment, which must reach the hook process), assert:
     - a run owing a commit (for example a changed run file inside a round, or an untracked new run file) with `stop_hook_active` `false` → status 2, stderr exactly `stop_check.REFUSAL` plus a line end, stdout empty;
     - the same with `stop_hook_active` `true` → 0, nothing printed;
     - a run whose files are all committed → 0, nothing printed;
     - a data root that is a plain directory (not a git working tree) → 0, nothing printed;
     - a loop whose `run_id` names another run than the owed one → 0 (shows the run id travels to the hook).
     Skip a case only where the platform cannot set it up, with the reason in the skip text.
   - All existing tests keep passing; update only what the new parameter and the new member require.
8. **`tests/test_turn_start.py`**: a test shows that the run id given on the command line reaches `turn_loop.run` as `run_id`, unchanged, for each of `EDGE_IDS` (for example by wrapping `turn_loop.run` with a recorder that calls the real one, or by having the stub record the settings file and reading the `Stop` args), and that the `Stop` entry's last arg is the real path of the data root the source gave. A run id refused with `bad_usage` never reaches the loop (an existing test may already show this; extend it if not). All existing tests keep passing.
9. **`tests/test_further_turn.py`** and **`tests/test_turn_definition.py`**: the existing calls of `turn_loop.run` gain a valid `run_id` and nothing else; their assertions are unchanged. In `test_passes_the_callable_check_of_the_turn_loop` the expected `ValueError` "the prompt" must still be the one raised (so the call passes a valid `run_id`).
10. Package coverage stays ≥ 80 % lines and ≥ 80 % functions (rule ①); record both figures of the final head from the `Coverage gate (hilclaw)` job. Every public function of the touched modules keeps tests (rule ③). Rule ⑤: add no test of a test helper or the stub.
11. Python, standard library only; no new dependency (A-13). Record the language line in `Result` (DRIVER §5). Tests pass on Linux (CI) and on Windows (the driver's clone); path handling must not assume POSIX separators.

### Provisional choices to record in `Result`
12. The name and value of the `Stop` timeout constant and its reason; where in `run` the run id is checked relative to the other argument checks; how `_entry` was changed (if at all); the JSON member order of `hooks`.

### Process checks
13. Before each commit and before the merge, run from the repository root and make sure each exits 0: `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`. Record the pytest pass and skip counts on `origin/main` and on the final head. Install nothing.
14. Check the diff against `origin/main`:
    - `git diff origin/main --stat` lists only files from `touchesFiles`, plus this task file's `Result` if the executor prompt has it written on the branch;
    - `git diff origin/main -- .claude .github orchestration ARCHITECTURE` is empty;
    - `git ls-files --eol` shows `i/lf` for the touched files.
    Record the non-test diff line count (cap: 300 LOC, 5 files). If exceeded, propose a split in `Follow-ups` and finish only the current scope (DRIVER §5).
15. Open a Draft PR and run the reviewer cycle with a fresh-context `dev-reviewer` running dev-code-review, at most 7 rounds. Ask the reviewer explicitly to:
    - (a) compare the written `Stop` entry with ADR-0148 decision 4 member by member (no `matcher`, no `onFailure`, `args` order, real absolute data root, timeout below 600 s) and confirm the two `PreToolUse` entries are unchanged;
    - (b) confirm the run id is checked before any directory, call or start, and used nowhere but the `Stop` args;
    - (c) confirm `turn_start` passes the same run id it puts into the prompt and that no outcome, status or line of the entry changed;
    - (d) confirm the stub-level hook tests really run `stop_check.START` from the written settings with the run id and data root as written;
    - (e) re-check the test-rule reading in Why and each provisional choice of criterion 12.
    A finding that starts with `SECURITY` is BLOCKED. After the review, get CI green on the final head with `gh pr checks <PR> --watch`, and record the check names and the run URL. Then squash-merge with `gh pr merge --squash --body`, using the PR body whose last line is `Task: T-0410`, and delete the branch.

## Out of Scope

- Any change of `hilclaw/stop_check.py` beyond the docstring paragraph of criterion 6, and any change of `hilclaw/run_commit.py`, `hilclaw/layout.py`, `hilclaw/caller_check.py`, `hilclaw/budget_check.py`, `hilclaw/further_turn.py`, `hilclaw/turn_definition.py` or any other module. If one of them turns out to need a change, stop and return BLOCKED with the reason.
- A `SubagentStop`, `SessionEnd` or `StopFailure` entry (ADR-0148 decision 3, Alternatives), `PostToolUse` journaling, gates (OD-3), the retry of a failed `run.commit` (OD-17), the push (#5 A-3), default-FAIL in general.
- Placeholder refusal for `PACKAGE_DIRECTORY` or `sys.executable` (PLAN "보류", T-0407 follow-up); rejecting a definition's `settings.local.json` (PLAN "보류", T-0404 follow-up).
- Editing the "Less exact, not edited" sentences of ADR-0148 in `ARCHITECTURE/` or `orchestration/` (document-mode work).
- Any edit of `.claude/`, `.github/`, `orchestration/`, `ARCHITECTURE/`, `CLAUDE.md` or `pyproject.toml`.
- Starting `claude` (D16), and the runtime acceptance items (lxiii) to (lxvi) (HQ-0063) and ADR-0146 (lvi), (lix), (lx) (HQ-0061).

## Follow-ups

- (planner) With this slice, ADR-0148's code slices are done. The next P2-4 parts (`PostToolUse` journaling, the rest of OD-18) need their own ADR under DRIVER §9; gates need OD-3, which is owner-only.

## Result
