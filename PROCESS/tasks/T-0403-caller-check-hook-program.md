---
id: T-0403
title: Add the caller check hook program of ADR-0146 and the holder lists and two new refusals of the shared agent-file reader in hilclaw/turn_permissions.py (ADR-0146 code slice 1; PLAN P2-4; not registered in any settings file)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-4, FR-9, FR-10, FR-11, OD-18, PLAN P2-4]
dependsOn: [T-0402]
touchesFiles: [hilclaw/caller_check.py, tests/test_caller_check.py, hilclaw/turn_permissions.py, tests/test_turn_permissions.py]
estimatedSize: {loc: 190, files: 2}   # non-test: hilclaw/caller_check.py (new, ~140 with docstrings) and hilclaw/turn_permissions.py (~50); test files are excluded from the cap (D4)
hq: []
---
## Why

PLAN P2-4 (runtime hooks) is a checklist item on the road to P2-5 (DRIVER §6, D18; PLAN P2 order: P2-1 to P2-4, P2-6, P2-7, then P2-5). ADR-0146 (landed on `main` as a368b11, T-0402) closes the caller-check part of OD-18 for the turn sessions of ADR-0120 decision 1. A `PreToolUse` command hook on every `mcp__hilclaw__` tool refuses a call when the calling agent does not hold the tool. The holder lists are the two sources ADR-0139 pre-approves from. The hook settings are written by the turn loop. Its Consequences name two code slices. This task is **slice 1, the hook program**. Slice 2 (the turn loop writes `.claude/settings.json`) is a separate task that comes after this one.

Today the Round-Manager *can* call `mcp__hilclaw__verdicts_write`, `correctness_check` or `coder_run`. Only its prompt stops it (ADR-0139 decision 5, ADR-0141 decision 5). ADR-0146 Context reads such a call as a write outside the main session's zone. FR-9 makes correctness a hard floor, so the check is needed before the first run (P2-5).

**Test rule (ADR-0146 Consequences hands this to the planner of slice 1).** Rules ① to ④ of CLAUDE.md "테스트 규칙" (DRIVER §5, D12) apply to this module. Rule ⑤ does not. The planner's reasons:
- The module is a layer-2 module of `hilclaw/`, the package that rules ① to ④ name. CLAUDE.md "세 층 모델" counts hook entry points as layer 2. The CI job `Test presence (hilclaw)` fails any `hilclaw/*.py` that has no test file, so an untested module could not merge.
- Rule ⑤ and the owner's user-level rule are about the tools that **build** this repository: test code, CI workflows, the driver's helper scripts and hooks, and build or packaging scripts. The two hooks named as exceptions (`hilclaw/merge_guard.py`) are development-process hooks. This hook is part of the **runtime product** that PLAN P2-4 asks for (FR-4, FR-11). The runtime harness (`hilclaw/harness/`, e.g. T-0401's waiter) is tested on the same reading.
- If a reviewer reads rule ⑤ otherwise, that is a BLOCKED reason ("요구 불명확") for the owner. It is not a reason to drop the tests.

D16: nothing here starts `claude`. The hook is not registered in any settings file, either in this repository or in a session directory. Every test feeds the program fixture payloads and fixture agent files.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit, no force push) and §5 (task format; naming: branch `claude/T-0403-<slug>`, PR title with `T-0403`, trailer `Task: T-0403`, the PR body's last line `Task: T-0403`; D4 size cap; code-task test rules ① to ⑤; language line in `Result`). Both are mandatory for every task (§6).
- `CLAUDE.md`, 상시 규칙: "코멘트 최소화", "세 층 모델", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ① to ⑤, "미결은 발명하지 않는다".
- `ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md`, all of it (173 lines). The binding parts are decisions 2, 3, 5 and 6 (lines 42-91), the Walk-through (lines 93-107) and Consequences slice 1 (line 133).
- `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md` §3 (lines 59-66) and §5 (lines 74-80): what the shared reader refuses and how sub-agents get their tools.
- `hilclaw/turn_permissions.py` (200 lines, all) and `tests/test_turn_permissions.py` (387 lines; helpers `agents`, `agent`, `split`, `refused`, and the refusal tests from line 282 on).
- `hilclaw/merge_guard.py` lines 593-652 (`evaluate`, `main`). This is the only existing `PreToolUse` entry in the package and shows the stdin, exit-status and stderr pattern. Copy the pattern only. Do not import the module.
- `hilclaw/turn_loop.py` lines 84-90 and 160-170 (`_START`) and lines 222-235 (`_config_text`). These show how the server is started with `sys.executable -I -c <start text> <package dir>`. Slice 2 will start this hook the same way, so the hook's entry must work under `-I` with the package directory put first on `sys.path`.
- `hilclaw/mcp_front.py` line 47 (`SERVER_NAME`) and `hilclaw/tools.py` `default_registry` (from line 182): the registered tool names. Check that `blob_push` and `blob_fetch` are on no holder list.
- `orchestration/agents/evaluator.md` and `orchestration/agents/coder-driver.md`: frontmatter only.
- `.github/workflows/ci.yml` job `Test presence (hilclaw)` (from line 118). Read it only. Do not change it.

## Acceptance Criteria

### `hilclaw/turn_permissions.py` (the shared reader, ADR-0146 decision 3)
1. A new public function gives the holder lists from the same reader and refusals that `options` uses, read from the given session directory each time it is called. The proposed name is `holder_lists(session_dir)`; the executor may choose another name and records it in `Result`. It returns the main session's list, which is exactly the entries of `ROUND_MANAGER_TOOLS`. It also returns, for each agent `name`, the `mcp__hilclaw__` entries of that agent's `tools` list. Built-in entries (`Read`, `Grep`, `Glob`) are left out. The result is immutable or a fresh copy. The executor chooses its exact shape (for example a pair of a tuple and a `dict` of tuples) and documents it in a Doxygen-like docstring. The argument types and errors are those of `options`.
2. The reader gains two refusals, each a `ValueError` with a new fixed text. These refusals apply to `options` and to the new function alike, before anything is returned:
   - (a) two or more agent files with the same `name`;
   - (b) an agent file whose `name` is `general-purpose`.
   The existing `_NAME` form already excludes `Explore` and `Plan` (ADR-0146 decision 3). Add no other refusal.
3. `options` returns the same values as before for every input it accepted before, apart from the two new refusals. Every existing test in `tests/test_turn_permissions.py` passes unedited.
4. Module docstring:
   - "What is raised" gains the two refusals.
   - "Not done here: … no hook, …" is rewritten so it no longer says there is no hook. It should say that the module gives the holder lists the caller check hook of ADR-0146 reads, and that it writes no settings file and sets no deny rule.
   - Keep it short (CLAUDE.md "코멘트 최소화"; module docstrings are boilerplate and may stay long).

### `hilclaw/caller_check.py` (new; the hook program, ADR-0146 decisions 2, 5 and 6)
5. A public `main(...)` returns the exit status: `0` lets the call go on, `2` refuses it. The signature must let tests pass stdin bytes, a stderr stream and an environment mapping, each defaulting to the process's own. Return `0` with nothing printed when the call passes. Return `2` with exactly one line on stderr when the call is refused. Never return or print `"allow"`, a JSON decision, or anything on stdout (decision 2). The program writes no file, starts no process, calls no model and contacts no server (decision 5).
6. The decision follows ADR-0146 decision 6, row by row. Each row below has at least one test:
   - stdin that is not strict UTF-8 JSON, or not one JSON object; `hook_event_name` that is not exactly `PreToolUse`; `tool_name` missing or not a `str` → refuse.
   - A `tool_name` that does not start with `mcp__hilclaw__` (another server's tool or a built-in tool) → refuse.
   - Neither `agent_id` nor `agent_type` present → the main session; use the main session's holder list.
   - Both present, with `agent_type` a non-empty `str` naming exactly one agent file → use that agent's holder list.
   - Only one of the two fields present, or `agent_type` empty or not a `str`, or an `agent_type` that names no agent file (`general-purpose`, `Explore` and `Plan` included) → refuse.
   - `agent_type` naming two or more agent files → refuse. This is the reader's refusal of criterion 2(a), and it applies to every caller.
   - A tool on the caller's list → `0`. A tool not on it, including `mcp__hilclaw__blob_push` and `mcp__hilclaw__blob_fetch` for every real caller → refuse.
   - `CLAUDE_PROJECT_DIR` missing, empty, or not a directory; an agent file that cannot be read or that the reader refuses → refuse for **every** caller, the main session included. The session directory comes from `CLAUDE_PROJECT_DIR` only. The input's `cwd` is not used.
   - The type of `agent_id` is not fixed by ADR-0146. Record the choice in `Result` as a provisional choice for the reviewer, for example "present and a non-empty `str`".
   - Whether `mcp_server` is read is the slice's choice (decision 2). Not reading it is the planner's suggestion. Record the choice either way.
7. **Whole body guarded** (decision 5). Any `Exception` raised after the module is imported ends in `2` with the fixed line. This covers reading stdin, decoding, the reader and the program's own faults. A test forces an unexpected exception (for example by monkeypatching the holder-list function to raise `RuntimeError`) and gets `2`.
8. **The line** (decision 6) is one fixed text from the module. It says that the caller check refused the call because the calling agent does not hold the tool or could not be checked. It may name the tool, but only when `tool_name` fully matches `mcp__hilclaw__<name>` with `<name>` in the reader's `_MCP_TOOL` form. It shows nothing else of the input, of the environment or of any file, and in particular no path and no exception text. The executor chooses the wording. Tests check that a payload with a path-like `agent_type` and a long junk `tool_name` produces neither in the line.
9. **Entry under the turn loop's start form**. One test runs the program as slice 2 will: `subprocess.run([sys.executable, "-I", "-c", <a start text that inserts the package directory from argv into sys.path and runs hilclaw.caller_check.main>, <package dir>], input=<payload bytes>, env=<env with CLAUDE_PROJECT_DIR set to a tmp session>)`. It asserts exit `0` for a held call and `2` plus the line for a refused one. The start text lives in the test. The module may define a public constant holding it for slice 2; if it does, the test uses that constant. Record which in `Result`. No `if __name__ == "__main__"` is needed unless the executor wants one; if added, it is covered.
10. Docstrings follow the style of `hilclaw/turn_permissions.py`: a module docstring that says what ADR-0146 decided and what is only applied, the runtime acceptance items it rests on, (lvi) to (lx), each in one short line, and "not registered here; slice 2 writes the settings". Public functions get Doxygen-like docstrings. No multi-line comments.

### Tests (test rules ① to ④; files excluded from the size cap)
11. `tests/test_caller_check.py` (new) covers criteria 5 to 9:
    - happy cases: the main session with a tool of `ROUND_MANAGER_TOOLS`; the evaluator with `mcp__hilclaw__verdicts_write`; the coder-driver with `mcp__hilclaw__coder_run`. Use the real `orchestration/agents/` files copied into a tmp session, as `test_the_real_definition` does;
    - error, branch and negative cases: every row of criterion 6, the guard (7) and the line (8);
    - every row of the ADR-0146 Walk-through that the program can decide. The rows on an interpreter that cannot start or a timeout belong to `onFailure` (slice 2 / runtime item (lix)) and are not tested here;
    - a session with no `.claude/agents` directory: the main session passes with its own tools, and any sub-agent is refused.
12. `tests/test_turn_permissions.py`: add tests only, edit no existing test. Cover the new function (happy, both built-in-only and mcp-only agents, no agents directory, wrong type, each existing refusal reached through it at least once) and the two new refusals through both `options` and the new function. Assert the fixed texts.
13. Package coverage stays ≥ 80 % lines and ≥ 80 % functions (rule ①). Record both figures of the final head from the `Coverage gate (hilclaw)` job. Every public function of both touched modules has tests (rule ③). The new module has its test file (rule ④). Rule ⑤: no test of a test helper, CI workflow or script is added.
14. Python, standard library only (no new dependency; A-13). Record the language line in `Result` (DRIVER §5). Tests pass on Linux (CI) and on Windows (the driver's clone). Path handling must not assume POSIX separators.

### Process checks
15. Before each commit and before the merge, run from the repository root: `python -m pytest` exits 0 (record pass and skip counts on `origin/main` and on the final head), and `python -m ruff check .` and `python -m ruff format --check .` exit 0. Install nothing.
16. `git diff origin/main --stat` lists only files from `touchesFiles`. `git diff origin/main -- .claude .github orchestration ARCHITECTURE PROCESS` is empty. `git ls-files --eol` shows `i/lf` for the changed files. Record the non-test diff line count (cap 300 LOC / 5 files). If it is exceeded, propose a split in `Follow-ups` and finish only the current scope (DRIVER §5).
17. Draft PR → reviewer cycle with a fresh-context `dev-reviewer` running dev-code-review (at most 7 rounds). Ask the reviewer explicitly to:
    - (a) find payloads or environments that pass a call ADR-0146 decision 6 refuses;
    - (b) confirm the program never answers `"allow"` and never prints to stdout;
    - (c) confirm the guard turns every `Exception` into `2`;
    - (d) confirm `options` output is unchanged for previously accepted inputs;
    - (e) re-check the test-rule reading of Why, and each provisional choice (`agent_id` type, `mcp_server`, start-text constant, function name and shape).
    A finding starting with `SECURITY` is BLOCKED. Then CI green on the final head (`gh pr checks <PR> --watch`; record the check names and the run URL). Then squash-merge with `gh pr merge --squash --body` carrying the PR body whose last line is `Task: T-0403`, and delete the branch.

## Out of Scope

- Writing `.claude/settings.json`, the matcher text, `onFailure`, `timeout`, refusing a definition's own `settings.json`, any change to `hilclaw/turn_loop.py` or `hilclaw/turn_definition.py`. All of this is ADR-0146 slice 2, a separate task.
- Registering the hook anywhere. Any edit of `.claude/`, `.github/`, `orchestration/`, `ARCHITECTURE/`, `PROCESS/`, `CLAUDE.md`, `pyproject.toml`.
- Editing the "less exact" sentences of earlier ADRs (ADR-0146 Consequences). Those are document-mode edits and not in this task.
- Any other hook or check of OD-18 (budget, gates, journaling, Stop, `run_id` check, default-FAIL in general), sub-question ② (shell and command-line front), hooks of any other session.
- Starting `claude` (D16). Any runtime acceptance item (lvi)-(lx) (HQ-0061). The Round-Manager prompt.
- Checking `tools` entries against the registry (still form only, ADR-0139).

## Follow-ups

- (planner) ADR-0146 code slice 2, the settings write in the turn loop, after this lands. It uses this task's entry (and start-text constant, if one is added) and refuses a definition's own `settings.json`.
- (planner) The PLAN "보류" line "T-0379 follow-up — `turn_permissions.options`가 같은 `name`의 agent 파일 두 개를 거부하지 않는 점" is carried out by criterion 2(a) of this task, as ADR-0146 decision 3 requires. Whether that line is removed is not decided (PLAN 보류 절); the driver/owner may note it.

## Result

- **PR**: #235 (`claude/T-0403-caller-check-hook-program`), squash-merged into `main`. Branch commits: `1ddda5c` (implementation), `3200307` (round-1 nit: a test keeps `caller_check._NAMED` equal to the reader's `_MCP_TOOL` form), then this `Result` commit.
- **Review**: 2 rounds with a fresh-context `dev-reviewer` (opus, dev-code-review). Round 1 Approve with one Nit (fixed) and one Info; round 2 Approve, two Info items, no change asked. No `SECURITY` finding. The reviewer accepted the test-rule reading of Why (rules ① to ④ apply, ⑤ does not) and noted, as Info only, that the "hook 스크립트" wording of rule ⑤ could be read more widely; the owner may narrow it.
- **Language**: Python, standard library only — the hook uses the shared reader of `hilclaw/turn_permissions.py` itself (ADR-0146 decision 4), and the package is Python.
- **Choices recorded for the reviewer** (all accepted):
  - New function: `turn_permissions.holder_lists(session_dir)` returns `(main, agents)`: `main` is the tuple `ROUND_MANAGER_TOOLS`, `agents` a new `dict` mapping each agent `name` to a tuple of its `mcp__hilclaw__` entries in written order (built-ins left out). The new refusal texts are "two agent files have the same name" and "an agent file has the name of a built-in agent".
  - `agent_id` counts only as "present and a non-empty `str`"; presence of either field is by key (a `null` value is present).
  - `mcp_server` is not read; the prefix `mcp__hilclaw__` is relied on (decision 2).
  - An input with a repeated JSON key at any depth is refused (so a later duplicate cannot replace `tool_name` or the agent fields).
  - The line is `REFUSAL` ("caller check: the call[ of <tool>] was refused because the calling agent does not hold the tool or could not be checked"); the tool is named only when it fully matches `mcp__hilclaw__[a-z][a-z0-9_]*`.
  - The module defines the public start-text constant `caller_check.START`; the subprocess test (`test_started_as_the_turn_loop_will`) uses it with `sys.executable -I -c START <checkout_boundary.PACKAGE_DIRECTORY>`. No `__main__` block.
- **Tests**: `python -m pytest` on `origin/main` `9b32468`: 25894 passed, 789 skipped; on the final code head `3200307`: 26034 passed, 789 skipped (Windows). `ruff check .` and `ruff format --check .` clean. Changed files `i/lf`.
- **CI** on `3200307` (run https://github.com/myungjoo/HIL-Claw/actions/runs/39741695329): C gate (clang), Coverage gate (hilclaw), Python gate (3.11), Python gate (3.14), Test presence (hilclaw), sh gate (shellcheck) — all pass. Coverage gate: lines 8864/8900 = 99.59 %, functions 857/857 = 100.00 %.
- **Size**: non-test diff 205 lines in 2 files (`hilclaw/caller_check.py` +141, `hilclaw/turn_permissions.py` +51/−13), within the D4 cap. Code diff touches only `touchesFiles`; the one `PROCESS/` change is this `Result` section, written on the PR branch as the driver's executor prompt asked.
- **Follow-ups**: none new. Those in the task's Follow-ups stand (slice 2; the PLAN 보류 line on two files of one `name` is now carried out by criterion 2(a)).
