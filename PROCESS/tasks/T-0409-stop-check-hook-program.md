---
id: T-0409
title: Add the Stop check hook program of ADR-0148 as hilclaw/stop_check.py with its test file (ADR-0148 code slice 1; PLAN P2-4; not registered in any settings file)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-11, NFR-1, OD-18, "PLAN P2-4"]
dependsOn: [T-0408]
touchesFiles: [hilclaw/stop_check.py, tests/test_stop_check.py]
estimatedSize: {loc: 140, files: 1}   # non-test: hilclaw/stop_check.py (new, ~140 with docstrings); the test file is excluded from the cap (D4)
hq: []
---
## Why

PLAN P2-4 covers the runtime hooks: "PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제". It is a checklist item in the group that PLAN's P2 header puts before P2-5, so the D18 priority rule (DRIVER §6) does not apply to it.

ADR-0148 landed on `main` as `4dbe250` (T-0408). It adopts a `Stop` command hook for the turn sessions of the runs of ADR-0120 decision 1. When the main session finishes its reply, the hook does one of two things:
- it **refuses that one stop** (exit 2, one fixed line on standard error) when `hilclaw.run_commit.commit_owed` answers true for the session's run and `stop_hook_active` is exactly `false`;
- otherwise it **lets the stop through** (exit 0, nothing printed). This includes every case where it cannot tell.

The hook never commits. ADR-0148 Consequences name two code slices. This task is **slice 1, the hook program**. Slice 2 is a separate task after this one: `hilclaw/turn_loop.py` gains a required keyword-only `run_id`, writes the `Stop` entry with the run id and the data root as arguments, and `hilclaw/turn_start.py` passes its run id.

**This hook differs from the two existing hooks in two ways.** Do not copy those differences away from `hilclaw/budget_check.py`:
1. **Fault behaviour.** On any fault it **lets the stop through** (exit 0). `caller_check` and `budget_check` refuse on fault (ADR-0148 decision 5).
2. **It starts processes.** `commit_owed` runs the machine's `git`, read-only (decision 4).

**No open HQ holds this slice:**
- HQ-0063 (items (lxiii) to (lxvi)) holds runtime acceptance items. They do not block code tested with fixtures (T-0408 Result).
- HQ-0053, HQ-0021, HQ-0026 and HQ-0048 are unrelated.
- The gate part of P2-4 needs OD-3, which is owner-only. It is not touched here.

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED) touches `hilclaw/start_instance.py` and three test files only.

**Test rule.** ADR-0148 Consequences hands this question to the planner of slice 1. Rules ① to ④ of CLAUDE.md "테스트 규칙" (DRIVER §5, D12) apply to this module, and rule ⑤ does not. This is the reading of T-0403 and T-0406, which their reviewers accepted as Info. The reasons:
- The module is a layer-2 module of `hilclaw/`, the package that rules ① to ④ name. CLAUDE.md "세 층 모델" counts hook entry points as layer 2.
- The CI job `Test presence (hilclaw)` fails any `hilclaw/*.py` that has no test file.
- Rule ⑤ and the owner's user-level rule cover the tools that **build** this repository. This hook is part of the **runtime product** that PLAN P2-4 asks for (FR-11, NFR-1).
- If a reviewer reads rule ⑤ otherwise, that is a BLOCKED reason ("요구 불명확") for the owner. It is not a reason to drop the tests.

**D16.** Nothing here starts `claude`. The hook is not registered in any settings file, either in this repository or in a session directory. Every test feeds the program fixture payloads, with temporary git repositories as the data checkout. The tests do run the machine's `git`; that is a development-machine tool, which the existing `tests/test_run_commit.py` already uses.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0409-<slug>`, PR title containing `T-0409`, trailer `Task: T-0409`, `Task: T-0409` as the PR body's last line); the D4 size cap; code-task test rules ① to ⑤; the language line in `Result`.
- `CLAUDE.md`, 상시 규칙: "코멘트 최소화", "세 층 모델", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ① to ⑤, "미결은 발명하지 않는다".
- `ARCHITECTURE/decisions/ADR-0148-od18-first-case-stop-hook-commit.md`. The binding parts are:
  - decisions 1 to 5 (lines 55-109);
  - the Walk-through (lines 111-127);
  - Consequences slice 1 and the test-rule question (lines 148-151);
  - "The cost, plainly" (line 166).
  Read the Context fact rows H13 to H22 (lines 40-49), especially H14 (`stop_hook_active`) and H18 (exit 2 with a missing-file message on stderr is a non-blocking error). Skim Status (lines 3-22).
- `hilclaw/budget_check.py` (147 lines, all). It is the model for the structure: `START`, `main(data, stderr, args)`, the strict parse (`_unique`, `_constant`), the guard, the fixed line, and the module docstring layout ("Decided by" / "Chosen here" / runtime items). Its outcome on fault is the **opposite** of this task's. You may import public names such as `caller_check.EVENT` only where they fit; this hook's event is `Stop`, not `PreToolUse`. Do not import private names.
- `hilclaw/caller_check.py` lines 1-62 (docstring, `EVENT`, `TOOL_PREFIX`, `START`).
- `hilclaw/run_commit.py`:
  - lines 1-45 (docstring);
  - 118-160 (the exception classes);
  - 170-213 (`owed_rounds`, `commit_owed` and what they raise);
  - 574-586 (`_git`: the environment it removes, `GIT_OPTIONAL_LOCKS=0`).
- `hilclaw/layout.py` lines 56-73 (`InvalidPathValueError`, `check_run_id`).
- `hilclaw/turn_loop.py` lines 40-60 (docstring on the hook entries) and 299-320 (`_entry`, `_settings_text`). This shows how slice 2 will start the program: `sys.executable -I -c <START> <package dir> <run id> <data root>` (ADR-0148 decision 4: "the start text of the program, the directory holding this package, the run id and the data root"). Read only; do not change it.
- `hilclaw/checkout_boundary.py` line 17 (`PACKAGE_DIRECTORY`).
- `orchestration/round-manager.md` lines 52-68 ("The end of a session"). The line of criterion 5 repeats its two exceptions. Read only.
- Tests to follow:
  - `tests/test_run_commit.py` lines 1-215: the `isolated_git` autouse fixture, `git`, `new_repository`, `root`, `write_instance`, `write_state`, `write_events`, `a_run` and `commit_by_hand`, which build a data checkout in which a commit is owed or not;
  - `tests/test_budget_check.py` lines 1-60 and 590-619 (fixtures, `started`, the subprocess tests).
  Copy what you need into the new test file. Do not import from another test module.
- `.github/workflows/ci.yml` job `Test presence (hilclaw)` (search for the job name). Read only.

## Acceptance Criteria

### `hilclaw/stop_check.py` (new; ADR-0148 decisions 3 to 5)
1. **`main`.** A public `main(...)` returns the exit status: `0` lets the stop through and `2` refuses it. The signature lets tests pass:
   - the stdin bytes;
   - a stderr stream;
   - the argument list after the package directory, which is exactly the run id and then the data root.

   Each defaults to the process's own (stdin bytes, `sys.stderr`, `sys.argv[1:]`).
   - On a pass, return `0` and print nothing anywhere.
   - On a refusal, return `2` with exactly one line on stderr.
   - Never print anything to stdout: no JSON, no `decision`, no `reason`, no `additionalContext` (decision 3).
   - It reads no environment variable for the run or the data root: not `CLAUDE_PROJECT_DIR`, `hilclaw.data_root_source` or `hilclaw.config`. Both come from the arguments only (decision 4).
   - It writes no file, makes no commit, calls no model and contacts no server. The only processes it starts are those `commit_owed` starts.
2. **Decision table.** The decision follows the table of ADR-0148 decision 5 row by row. Each row below has at least one test.
   - Input that is not strict UTF-8 JSON, or is not one JSON object → `0`. Strict means a repeated key at any depth, or a `NaN`/`Infinity`/`-Infinity` constant, counts as not JSON, as in `budget_check` (suggested; record the choice).
   - `hook_event_name` not exactly `"Stop"` (for example `"SubagentStop"`, `"PreToolUse"`, missing, or not a `str`) → `0`.
   - `stop_hook_active` not exactly `false`. This covers `true`, missing, `null`, `0`, `"false"`, and any other type. The test must show that `0` and `0.0` do not count as `false` (use an identity or type check, not `== False`) → `0`.
   - An argument list other than exactly two elements → `0`.
   - A run id that `hilclaw.layout.check_run_id` refuses → `0`.
   - A data root that is not a `str` or names no directory → `0`.
   - `commit_owed` raises anything → `0`. Test with real temporary repositories:
     - a data root that is a plain directory, not a git working tree (`NoRepositoryError`);
     - a working-tree `STATE.json` that is invalid (`WorkingStateError`);
     - a tracked run file missing from the working tree (`FileMissingError`);
     - `git` that cannot be started (`GitNotRunError`): monkeypatch `run_commit.GIT` to a name that does not exist;
     - any other exception: monkeypatch `run_commit.commit_owed` to raise `RuntimeError`.
   - `commit_owed` answers false → `0`. Test two cases: a run whose files are all committed, and a repository that holds no directory for the run.
   - `commit_owed` answers true and `stop_hook_active` is `false` → `2` with the line. Test at least:
     - a round end owed (working `round` 1, nothing in `HEAD`, the key directory present as `run_commit` requires);
     - a changed run file inside a round;
     - an untracked new run file;
     - and, where the platform allows it, a stale `.git/index.lock` (Walk-through row "Entry step 0 fails with `commit_not_made`").
   - The same owed repository with `stop_hook_active` `true` → `0`.

   No input field other than `hook_event_name` and `stop_hook_active` is read. Tests show the outcome does not change when `transcript_path` or `last_assistant_message` is present, absent, or of the wrong type (decision 4). `commit_owed` is called **at most once** per run of `main`, and only after the input and arguments have passed every check above. A test counts the calls with a wrapper and checks that a non-`Stop` or non-`false` input makes none.
3. **No write.** One test checks that `main` changes nothing in the data checkout, whether it lets through or refuses. Compare `git status --porcelain=v1 -z --ignored`, the `HEAD` commit id and the bytes of `.git/index` before and after.
4. **Whole body guarded, letting through** (decision 5). Any `Exception` raised after the module is imported ends in `0` with nothing printed. This covers reading stdin, decoding, `InvalidPathValueError`, every `run_commit` error, `OSError` and the program's own faults. A test forces an unexpected exception and gets `0`. If writing the refusal line to stderr itself fails, `main` returns `0` (suggested, because exit 2 with no line would send the model back with no instruction; record the choice). A test covers that case with a stream whose `write` raises.
5. **The line** (decision 5) is one fixed text, a public constant of the module, written as one line. It says:
   - the stop was held because a commit of the run is owed;
   - call `mcp__hilclaw__run_commit` once, as "The end of a session" says, and then end;
   - if the prompt held no valid run id, or a call of `mcp__hilclaw__run_commit` has failed in this turn, end at once without calling it.

   Constraints:
   - It shows no path, member, value, run id, argument or exception text. Tests use a distinctive run id and a distinctive data-root path and check that neither appears in the line.
   - It must not read as a missing-file message (H18). It contains no "No such file or directory" and no other wording of a missing file, and a test asserts this.
   - Build the tool name from `caller_check.TOOL_PREFIX` and the MCP name of `run.commit` (`run_commit`). A test checks that the name in the line is `caller_check.TOOL_PREFIX` plus the MCP name of the `run.commit` tool of `tools.default_registry()`, where the front turns `.` into `_`.
6. **Entry under the turn loop's start form.** The module defines a public start-text constant, in the same form as `budget_check.START`. It takes the package directory from `sys.argv` and passes the remaining arguments to `main`. Subprocess tests run `subprocess.run([sys.executable, "-I", "-c", <constant>, checkout_boundary.PACKAGE_DIRECTORY, <run id>, <data root>], input=<payload bytes>, ...)` against temporary repositories and assert:
   - exit `2` with exactly the line on stderr and empty stdout, for an owed run with `stop_hook_active` `false`;
   - exit `0` with empty stdout and stderr, for a run that owes nothing;
   - exit `0` with empty stdout and stderr, for the same owed run with the data-root argument omitted.

   The `isolated_git` environment must reach the child (`-I` does not remove `GIT_*` variables).
7. **Provisional choices to record in `Result`** for the reviewer:
   - the strict parse of criterion 2;
   - whether a relative data root is used as given. The suggestion is to use it as given, as `budget_check` does, with no refusal beyond the table;
   - the stderr-failure outcome of criterion 4;
   - the module name, the constant names, the `main` signature and the exact text of the line.
8. **Docstrings** follow the style of `hilclaw/budget_check.py`. The module docstring:
   - says what ADR-0148 decided and what is only applied;
   - states plainly that, unlike the two `PreToolUse` hooks, it lets the stop through on every fault and that it starts `git` through `commit_owed`;
   - lists the runtime acceptance items it rests on, each in one short line: ADR-0148 (lxiii) to (lxvi), and ADR-0146 (lvi), (lix) and (lx) as applied to the `Stop` entry (ADR-0148 Consequences);
   - says that this module is not registered here, and that slice 2 writes the settings entry and passes the run id and the data root.

   Public functions get Doxygen-like docstrings. No multi-line comments.

### Tests (test rules ① to ④; the file is excluded from the size cap)
9. `tests/test_stop_check.py` (new) covers criteria 1 to 6. Build data checkouts under `tmp_path` with `git` and the package's writers, as `tests/test_run_commit.py` does. Hand-written bytes are fine only for invalid files.
   - **Happy cases**: owed and refused; not owed and through.
   - **Error, branch and negative cases**: every row of criterion 2, the no-write check (criterion 3), the guard (criterion 4) and the line (criterion 5).
   - **Walk-through**: every row of the ADR-0148 Walk-through that the program alone can decide:
     - committed then stop;
     - stop without the call;
     - a second stop with `stop_hook_active` `true`;
     - stale lock;
     - `commit_refused`;
     - a run that is over and committed;
     - a round end committed;
     - `STATE.json` written after the end call.

     The rows on `StopFailure`, the hook timeout, sub-agents and the model's adherence are outside the program and are not tested here.
   - Skip a case only where the platform cannot set it up (as `test_run_commit.py` does for symbolic links and the executable bit), and say why in the skip reason.
10. Package coverage stays ≥ 80 % lines and ≥ 80 % functions (rule ①). Record both figures of the final head from the `Coverage gate (hilclaw)` job. Every public function of the new module has tests (rule ③), and the module has its test file (rule ④). Rule ⑤: add no test of a test helper, CI workflow or script.
11. Python, standard library only: no new dependency (A-13). Record the language line in `Result` (DRIVER §5). Tests pass on Linux (CI) and on Windows (the driver's clone). Path handling must not assume POSIX separators.

### Process checks
12. Before each commit and before the merge, run these from the repository root and make sure each exits 0: `python -m pytest`, `python -m ruff check .` and `python -m ruff format --check .`. Record the pytest pass and skip counts on `origin/main` and on the final head. Install nothing.
13. Check the diff against `origin/main`:
    - `git diff origin/main --stat` lists only files from `touchesFiles`, plus this task file's `Result` if the executor prompt has it written on the branch;
    - `git diff origin/main -- .claude .github orchestration ARCHITECTURE` is empty;
    - `git ls-files --eol` shows `i/lf` for the new files.

    Record the non-test diff line count (cap: 300 LOC, 5 files). If it is exceeded, propose a split in `Follow-ups` and finish only the current scope (DRIVER §5).
14. Open a Draft PR and run the reviewer cycle with a fresh-context `dev-reviewer` running dev-code-review, for at most 7 rounds. Ask the reviewer explicitly to:
    - (a) find inputs, arguments or repositories that get a refusal where ADR-0148 decision 5 lets the stop through, or the reverse;
    - (b) confirm nothing is ever printed to stdout and that a pass prints nothing at all;
    - (c) confirm the guard turns every `Exception` into `0`;
    - (d) confirm the run id and the data root come only from the arguments, and that only `hook_event_name` and `stop_hook_active` are read from the input;
    - (e) confirm the hook writes nothing into the data checkout;
    - (f) re-check the test-rule reading in Why and each provisional choice of criterion 7.

    A finding that starts with `SECURITY` is BLOCKED. After the review, get CI green on the final head with `gh pr checks <PR> --watch`, and record the check names and the run URL. Then squash-merge with `gh pr merge --squash --body`, using the PR body whose last line is `Task: T-0409`, and delete the branch.

## Out of Scope

- **ADR-0148 slice 2**, a separate task: writing the `Stop` entry, its `timeout`, the run-id parameter of `hilclaw.turn_loop.run`, the change to `hilclaw/turn_start.py`, and the docstrings of both modules.
- Any change to `hilclaw/run_commit.py`, `hilclaw/layout.py`, `hilclaw/caller_check.py`, `hilclaw/budget_check.py`, `hilclaw/turn_loop.py` or any other existing module. If `commit_owed` turns out to need a change, stop and return BLOCKED with the reason.
- Registering the hook anywhere.
- Any edit of `.claude/`, `.github/`, `orchestration/`, `ARCHITECTURE/`, `CLAUDE.md` or `pyproject.toml`.
- Editing the "Less exact, not edited" sentences listed by ADR-0148. That is document-mode work.
- A `SubagentStop`, `SessionEnd` or `StopFailure` hook, `PostToolUse` journaling, gates (OD-3), the retry of a failed `run.commit` (OD-17), the push (#5 A-3) and default-FAIL in general (ADR-0148 Boundaries).
- Starting `claude` (D16), and the runtime acceptance items (lxiii) to (lxvi) (HQ-0063).

## Follow-ups

- (planner) ADR-0148 code slice 2 comes after this lands:
  - `hilclaw/turn_loop.py` gains the required keyword-only `run_id`, checks it as `check_run_id` does, and writes the `Stop` entry (no `matcher`, exec form, no `onFailure`, a `timeout` well below 600 s) from this module's start-text constant, with the run id and the real absolute data root as the last two `args`;
  - `hilclaw/turn_start.py` passes its run id;
  - tests check the written file against a stub `claude`;
  - the docstrings of both modules are rewritten (ADR-0148 Consequences slice 2).

## Result

- **Outcome**: DONE. PR #239 (https://github.com/myungjoo/HIL-Claw/pull/239) squash-merged as `fed5f9a` with `--body` (last line `Task: T-0409`); branch `claude/T-0409-stop-check-hook-program` deleted.
- **Review**: 2 rounds with a fresh-context `dev-reviewer`. Round 1 Request changes (Medium: `print(file=None)` fell back to stdout with no stderr, fixed with `stream.write` and a `sys.stderr = None` test; Low: partial-line write, same fix; Low: environment test set an unread variable, now sets `config.ENV_LOCAL_PATH`/`config.ENV_URL`). Round 2 Approve (Info only, no SECURITY). The Why reading of the test rules (① to ④ apply, ⑤ does not) was accepted as Info.
- **CI** (head `c29600a`, run https://github.com/myungjoo/HIL-Claw/actions/runs/39788266358): all six checks green; coverage lines 99.60%, functions 100.00%; `hilclaw/stop_check.py` 100% lines.
- **Local** (Windows): 26278 passed, 819 skipped on the final head; `ruff check .` and `ruff format --check .` clean.
- **Diff**: `hilclaw/stop_check.py` (+141, the only non-test file) and `tests/test_stop_check.py` (+707, 106 tests).
- **Language**: Python, standard library only; the hook calls `run_commit.commit_owed` and `layout.check_run_id` directly (ADR-0148 decision 4). No new dependency.
- **Provisional choices**: constants `EXIT_PASS = 0`, `EXIT_REFUSE = 2`, `EVENT = "Stop"`, `COMMIT_TOOL`, `START`, `REFUSAL`; `main(data=None, stderr=None, args=None)`; strict parse (repeated key, NaN/Infinity constants or a UTF-8 BOM let the stop through); `stop_hook_active` must be `is False`; `commit_owed` must answer exactly `True`; a stderr write/flush failure lets the stop through.
- No `claude` was started (D16).
- **Follow-ups**: (planner) ADR-0148 code slice 2 as listed above. (candidate, reviewer Info) `hilclaw/budget_check.py` `main` still uses `print(..., file=stream)`, which would put its refusal line on stdout with no stderr; a small task could switch it to `stream.write`.
