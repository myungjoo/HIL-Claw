---
id: T-0406
title: Add the round-budget check hook program of ADR-0147 as hilclaw/budget_check.py with its test file (ADR-0147 code slice 1; PLAN P2-4; not registered in any settings file)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-3, FR-4, NFR-5, OD-19, OD-18, "PLAN P2-4"]
dependsOn: [T-0405, T-0403]
touchesFiles: [hilclaw/budget_check.py, tests/test_budget_check.py]
estimatedSize: {loc: 150, files: 1}   # non-test: hilclaw/budget_check.py (new, ~150 with docstrings); the test file is excluded from the cap (D4)
hq: []
---
## Why

PLAN P2-4 (runtime hooks: PreToolUse budget and gate checks, PostToolUse journaling, Stop commit) is a checklist item in the group that PLAN's P2 header puts before P2-5. The D18 priority rule (DRIVER §6) therefore does not apply to it. ADR-0147 (landed on `main` as `afa64a2`, T-0405) closes the budget-check part of OD-19, and a part of OD-18, for the turn sessions of ADR-0120 decision 1. It adopts a second `PreToolUse` command hook on the two spending tools, `mcp__hilclaw__coder_run` and `mcp__hilclaw__correctness_check`. The hook reads the run that the request's `run_id` names, below a data root that the turn loop passes as a hook argument. It refuses the call when that run holds a `run_status`, is at its round budget, or cannot be read. ADR-0147 Consequences name two code slices. This task is **slice 1, the hook program**. Slice 2 (the turn loop writes the second `PreToolUse` entry with the data-root argument) is a separate task after this one.

No open HQ holds this slice:
- HQ-0053 (coder start): the hook only reads files, it does not start the coder;
- HQ-0021 and HQ-0026: `sim.run` and `board.run` are not in the constant of spending tools;
- HQ-0062 (items (lxi), (lxii)): these are runtime acceptance items and do not block code tested with fixtures (T-0405 Result).

Open PR #186 touches `hilclaw/start_instance.py` and three test files only, so it does not overlap.

**Test rule (ADR-0147 Consequences hands this question to the planner of slice 1).** Rules ① to ④ of CLAUDE.md "테스트 규칙" (DRIVER §5, D12) apply to this module. Rule ⑤ does not. This is the same reading as T-0403 (the caller check hook), whose reviewer accepted it as Info. The reasons:
- The module is a layer-2 module of `hilclaw/`, the package that rules ① to ④ name. CLAUDE.md "세 층 모델" counts hook entry points as layer 2.
- The CI job `Test presence (hilclaw)` fails any `hilclaw/*.py` that has no test file.
- Rule ⑤ and the owner's user-level rule cover the tools that **build** this repository. This hook is part of the **runtime product** that PLAN P2-4 asks for (FR-3, FR-4).
- If a reviewer reads rule ⑤ otherwise, that is a BLOCKED reason ("요구 불명확") for the owner. It is not a reason to drop the tests.

D16: nothing here starts `claude`. The hook is not registered in any settings file, either in this repository or in a session directory. Every test feeds the program fixture payloads and fixture run directories.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, the 2h30m limit, no force push) and §5 (lines 86-114). §5 covers the task format and the naming convention: branch `claude/T-0406-<slug>`, PR title containing `T-0406`, trailer `Task: T-0406`, and `Task: T-0406` as the PR body's last line. It also covers the D4 size cap, code-task test rules ① to ⑤ and the language line in `Result`. Both sections are mandatory for every task (§6).
- `CLAUDE.md`, 상시 규칙: "코멘트 최소화", "세 층 모델", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ① to ⑤, "미결은 발명하지 않는다".
- `ARCHITECTURE/decisions/ADR-0147-od19-first-case-spend-path-check.md`. The binding parts are:
  - decisions 2 to 5 (lines 47-100);
  - the Walk-through (lines 102-117);
  - Consequences slice 1 and the test-rule question (lines 138-141);
  - "The cost, plainly" (line 156).
  Skim Status and Context (lines 3-36).
- `hilclaw/caller_check.py` (140 lines, all). It is the model for the structure: `main`, the guard, `_Refused`, the duplicate-key refusal, `START`, the fixed `REFUSAL` line, and the module docstring with its "Decided by" / "Chosen here" / runtime-items layout. Its public `EVENT` and `TOOL_PREFIX` may be imported. Do not import its private names.
- `hilclaw/run_file_tools.py` lines 197-231 (`read`). `hilclaw/layout.py` lines 56-73 (`InvalidPathValueError`, `check_run_id`).
- `hilclaw/run_state.py` lines 66-72 (`RunState`: `round`, `budget_spent`, `others`). `hilclaw/instance.py` lines 727-760 (`parse`; `round_budget` is `None` when the file does not state it).
- `hilclaw/further_turn.py` lines 94-150 (`classify`). It reads the same members in the same order: `run_status` in `others`, then `instance.json`'s `round_budget`. Read it only and do not change it.
- `hilclaw/turn_loop.py` lines 268-282 (`_settings_text`). This is how slice 2 will start the program: `sys.executable -I -c <START> <package dir>`, with the data-root argument appended after the package directory (ADR-0147 decision 4).
- `hilclaw/mcp_front.py` line 47 (`SERVER_NAME`), and how the front turns a registry name such as `coder.run` into the MCP tool name `coder_run` (search for where `.` is replaced). `hilclaw/tools.py` `default_registry` (from line 182).
- `tests/test_caller_check.py` lines 1-63 (fixtures, `payload`) and 465-485 (`started`, the subprocess test). `tests/test_further_turn.py` lines 1-40 (imports of `instance_file.write` and `run_state_file.replace`, used to build fixture runs).
- `.github/workflows/ci.yml` job `Test presence (hilclaw)` (from line 118). Read it only and do not change it.

## Acceptance Criteria

### `hilclaw/budget_check.py` (new; ADR-0147 decisions 3 to 5)
1. **Spending tools.** A public constant holds exactly the two tool names `mcp__hilclaw__coder_run` and `mcp__hilclaw__correctness_check`. Slice 2 builds the matcher from it (decision 4). The executor chooses the name and the type (a tuple is the suggestion). A test checks:
   - each entry is `caller_check.TOOL_PREFIX` plus the MCP name of a tool in `tools.default_registry()`;
   - the two entries are `coder.run` and `correctness.check`.
2. **`main`.** A public `main(...)` returns the exit status: `0` gives no decision, `2` refuses. The signature lets tests pass:
   - the stdin bytes;
   - a stderr stream;
   - the argument list after the package directory, with the data root as its one element.
   Each defaults to the process's own. On a pass, return `0` and print nothing. On a refusal, return `2` with exactly one line on stderr. Never return or print `"allow"`, `updatedInput`, a JSON decision, or anything on stdout (decision 3). The program writes no file, starts no process, calls no model and contacts no server (decision 4). It does not read `CLAUDE_PROJECT_DIR`, `hilclaw.data_root_source` or `hilclaw.config`: the data root comes from the argument only (decision 4).
3. **Decision table.** The decision follows the table of ADR-0147 decision 5 row by row. Each row below has at least one test:
   - input that is not strict UTF-8 JSON, or not one JSON object → refuse;
   - `hook_event_name` that is not exactly `PreToolUse` → refuse;
   - `tool_name` that is not one of the two spending tools, including other `mcp__hilclaw__` tools and built-ins → refuse;
   - `tool_input` that is not an object; `run_id` missing, not a `str`, or refused by `hilclaw.layout.check_run_id` → refuse;
   - the data-root argument missing, or naming no directory → refuse. The suggestion is to also refuse a list that has more than one element; record the choice;
   - `STATE.json` missing, unreadable, invalid, of another version, or not a regular file → refuse. Use `hilclaw.run_file_tools.read`, so these are exactly the tool layer's four `run_file_*` situations;
   - `run_status` present in `STATE.json` with `"over"` or any other value or type → refuse. In this case `instance.json` is not read (decision 4, "instance.json when STATE.json holds no run_status");
   - no `run_status`, and `instance.json` missing, unreadable, invalid or of another version → refuse;
   - no `run_status`, and `instance.json` valid but stating no `round_budget` → `0` (OD-8 ㉙ (나) stays open; ADR-0122 decision 4);
   - no `run_status` and `round` ≥ `round_budget` → refuse. Test both the equal case and the greater case;
   - no `run_status` and `round` < `round_budget` → `0`.
   No member other than `run_status`, `round` and `round_budget` is interpreted. An unknown top-level member passes as it does for the parsers. No `budget_spent` amount, time or token count is read (decision 3). The program does not compare the request's `run_id` with the session's run (ADR-0146 Boundaries).
4. **Whole body guarded** (decision 4, as in ADR-0146 decision 5). Any `Exception` raised after the module is imported ends in `2` with the fixed line. This covers reading stdin, decoding, `ToolFailure`, `InvalidPathValueError`, `OSError` and the program's own faults. A test forces an unexpected exception and gets `2`, for example by monkeypatching `run_file_tools.read` to raise `RuntimeError`.
5. **The line** (decision 5) is one fixed text from the module. It says the budget check refused the call because the run is over, is at its round budget, or could not be checked. It may name the tool, but only when `tool_name` is one of the two spending tools. It shows no member, path, value, `run_id`, argument or exception text. Tests check that a payload with a path-like `run_id`, and a data-root argument with a distinctive path, put neither into the line.
6. **Entry under the turn loop's start form.** The module defines a public start-text constant (as `caller_check.START` does) that:
   - takes the package directory from `sys.argv`, as `caller_check.START` does;
   - passes the remaining arguments, which hold the data root, to `main`.
   One test runs `subprocess.run([sys.executable, "-I", "-c", <constant>, checkout_boundary.PACKAGE_DIRECTORY, <data root>], input=<payload bytes>, ...)`. It asserts:
   - exit `0` with empty stdout and stderr for a run below its budget;
   - exit `2` with exactly the line for a run that is over.
   A second subprocess case omits the data-root argument and asserts `2`.
7. **Provisional choices to record in `Result`** for the reviewer:
   - an input with a repeated JSON key at any depth is refused, as in `caller_check` (suggested);
   - whether a relative data-root argument is used as given or refused (decision 5's table names only "missing, or naming no directory"; the suggestion is to add no refusal beyond the table and to say so);
   - the constant names, the start-text constant, and the `main` signature.
8. **Docstrings** follow the style of `hilclaw/caller_check.py`. The module docstring:
   - says what ADR-0147 decided and what is only applied;
   - lists the runtime acceptance items it rests on: ADR-0147 (lxi) and (lxii), and ADR-0146 (lvi) and (lviii) to (lx) as applied to the second entry (ADR-0147 Consequences), each in one short line;
   - says that this module is not registered here, and that slice 2 writes the settings entry and passes the data root.
   Public functions get Doxygen-like docstrings. No multi-line comments.

### Tests (test rules ① to ④; the file is excluded from the size cap)
9. `tests/test_budget_check.py` (new) covers criteria 1 to 7. Build the fixture runs under `tmp_path` with the package's writers, `hilclaw.instance_file.write` and `hilclaw.run_state_file.replace`, the way `tests/test_further_turn.py` does. Do not hand-write JSON where a writer exists. Hand-written bytes are fine only for invalid or other-version files.
   - **Happy cases**: `correctness_check` and `coder_run`, each on a run with `round_budget` 5 and `round` 0 (no decision); a valid `instance.json` with no `round_budget` (no decision).
   - **Error, branch and negative cases**: every row of criterion 3, the guard (criterion 4) and the line (criterion 5).
   - **Walk-through**: every row of the ADR-0147 Walk-through that the program can decide. The rows on the interpreter failing to start, `onFailure`, the command-line front and the delegation not being checked are outside the program and are not tested here.
10. Package coverage stays ≥ 80 % lines and ≥ 80 % functions (rule ①). Record both figures of the final head from the `Coverage gate (hilclaw)` job. Every public function of the new module has tests (rule ③), and the module has its test file (rule ④). Rule ⑤: add no test of a test helper, CI workflow or script.
11. Python, standard library only: no new dependency (A-13). Record the language line in `Result` (DRIVER §5). Tests pass on Linux (CI) and on Windows (the driver's clone), and path handling must not assume POSIX separators.

### Process checks
12. Before each commit and before the merge, run these from the repository root and make sure they exit 0: `python -m pytest`, `python -m ruff check .` and `python -m ruff format --check .`. Record the pytest pass and skip counts on `origin/main` and on the final head. Install nothing.
13. Check the diff against `origin/main`:
    - `git diff origin/main --stat` lists only files from `touchesFiles`;
    - `git diff origin/main -- .claude .github orchestration ARCHITECTURE PROCESS` is empty, apart from this task file's `Result` if the executor prompt has it written on the branch;
    - `git ls-files --eol` shows `i/lf` for the new files.
    Record the non-test diff line count (cap: 300 LOC, 5 files). If it is exceeded, propose a split in `Follow-ups` and finish only the current scope (DRIVER §5).
14. Open a Draft PR and run the reviewer cycle with a fresh-context `dev-reviewer` running dev-code-review, for at most 7 rounds. Ask the reviewer explicitly to:
    - (a) find payloads, arguments or run directories that get no decision where ADR-0147 decision 5 refuses;
    - (b) confirm the program never answers `"allow"` and never prints to stdout;
    - (c) confirm the guard turns every `Exception` into `2`;
    - (d) confirm the data root comes only from the argument;
    - (e) re-check the test-rule reading in Why and each provisional choice of criterion 7.
    A finding that starts with `SECURITY` is BLOCKED.
    After the review, get CI green on the final head with `gh pr checks <PR> --watch`, and record the check names and the run URL. Then squash-merge with `gh pr merge --squash --body`, using the PR body whose last line is `Task: T-0406`, and delete the branch.

## Out of Scope

- Writing the second `PreToolUse` entry, its matcher text, `timeout` and `onFailure`, the data-root argument in the settings, and any change to `hilclaw/turn_loop.py` or its docstring. All of this is ADR-0147 slice 2, a separate task.
- Any change to `hilclaw/caller_check.py`, `hilclaw/run_file_tools.py`, `hilclaw/further_turn.py`, or any other existing module.
- Registering the hook anywhere. Any edit of `.claude/`, `.github/`, `orchestration/`, `ARCHITECTURE/`, `CLAUDE.md` or `pyproject.toml`.
- Editing the "less exact" sentences of earlier ADRs, and the ADR-0147 decision 4 citation nit already in PLAN 보류. Both are document-mode work.
- `sim.run` or `board.run` in the spending list (HQ-0021, HQ-0026), the `run_id`-against-session check, other budget axes, gates, caps, PostToolUse journaling and the Stop hook (ADR-0147 Boundaries).
- Starting `claude` (D16), and the runtime acceptance items (lxi) and (lxii) (HQ-0062).

## Follow-ups

- (planner) ADR-0147 code slice 2 comes after this lands. `hilclaw/turn_loop.py` writes the two `PreToolUse` entries, the second from this module's start-text constant and spending-tool constant, with the real absolute data root as the last `args` element. Its tests check the written file against a stub `claude`, and the `turn_loop` docstring "It holds one ``PreToolUse`` entry" is rewritten. T-0405 Result notes that slice 2 may weigh refusing a data root whose path holds a hook placeholder such as `${CLAUDE_PLUGIN_ROOT}` (reviewer Info, not decided).

## Result
