---
id: T-0386
title: Give every turn session of hilclaw.turn_loop the environment of ADR-0141 decision 4 (MCP idle check off, background tasks off, auto-backgrounding removed) (ADR-0141 Consequences slice 2; PLAN P2-2)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-5, OD-23, OD-18, S0, S1]
dependsOn: [T-0384, T-0385]
touchesFiles:
  - hilclaw/turn_loop.py
  - tests/test_turn_loop.py
estimatedSize: {loc: 60, files: 1}
hq: []
---
## Why

PLAN P2-2 (the coder-driver, "OD-23 종결 필요(§9 ADR 경로)") is a checklist item; in the P2 order of the PLAN P2 head it comes before P2-5, so the D18 rule for work outside the checklist does not apply. ADR-0141 (T-0384, landed as 3815c42) lists four code slices in order. Slice 1 (the registry tool `coder.run`) landed as T-0385 (PR #222, 90935b1). This task is **slice 2**: the turn loop starts every turn session with `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` set to `0` and `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` set to `1`, both replacing any value the caller had, and with `CLAUDE_AUTO_BACKGROUND_TASKS` removed (ADR-0141 decision 4). A long `coder.run` call is then not cut off by the MCP idle window, and the coder-driver's delegation runs in the foreground, which slices 3 and 4 rely on.

Open HQs checked: HQ-0053 (slice (d), the coder's container sign-in) is not crossed; nothing here starts a container or names anything of the coder's `claude -p`. HQ-0056 holds the runtime acceptance items (xli)-(xliii) of ADR-0141; this task does not close them and must not claim that a real session behaves as the stub does. HQ-0041 (2) is not crossed. No value of `MCP_TOOL_TIMEOUT`, `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` or `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` is chosen (ADR-0141 decision 4; OD-14). Nothing of the unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0361-*` or `claude/T-0375-*` is relied on. The files do not overlap open draft PR #186 (T-0324: `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": the language policy, the test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`. This is the specification. Read closely: the Context bullet "The turn session" and rows M1, M2, M6, M7, M8 and M9 of its table; **decision 4** in full (the three variables, "What can still override it", "Its reach, confined", the stall timer and ceiling that are *not* set, and why the process environment is chosen over the definition's settings file); the Walk-through row "A call that runs 3 hours without a progress notification"; Consequences **slice 2**; the "Less exact, not edited" bullet on ADR-0118 decision 6 and the `hilclaw/turn_loop.py` docstring; and runtime acceptance items (xli) and (xlii).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: decision 6 (the server configuration and the session's environment) and item (v), to know what the docstring now says differently.
- `hilclaw/turn_loop.py`, the whole file: the module docstring (in particular "The command line" paragraph, "the environment of the calling process unchanged", and "Runtime acceptance items it depends on"), `_turn` and `run`.
- `hilclaw/selfcheck_session.py` lines 15-25 and 100-110: the self-check session keeps the environment of the calling process unchanged, which ADR-0141 decision 4 leaves as it is ("The runtime self-check's session … is unchanged").
- `tests/test_turn_loop.py`, the whole file: `STUB` (the stub `claude` that records what it was started with), `Stub`, the fixtures `stub` and `only_the_stub`, `go`, `expected_argv`, and `test_server_entry_starts_the_front_from_elsewhere` (which builds a server environment from `os.environ`).

## Acceptance Criteria

1. **The environment** (ADR-0141 decision 4). Every turn session that `hilclaw.turn_loop.run` starts gets the environment of the calling process, as read at that turn, with:
   - `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` set to `"0"`, replacing any value the caller had;
   - `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` set to `"1"`, replacing any value the caller had;
   - `CLAUDE_AUTO_BACKGROUND_TASKS` absent, whatever value the caller had (and no error if the caller had none).
   Nothing else of the environment is added, removed or changed. The calling process's own `os.environ` is not modified. The server entry in the `--mcp-config` file (its `env` is still exactly the data-root variable), the command line, the working directory, standard input and the handling of standard output and standard error are unchanged. No value of `MCP_TOOL_TIMEOUT`, `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` or `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` is set or removed. No settings file is written into the session directory or anywhere else.
2. **Form of the code**: the variable names and values are module constants of `hilclaw/turn_loop.py`; whether they are public, and their names, are the executor's choice, stated in the docstring if public and tested if public. The environment is built by tested code in this module, beside the command line (ADR-0141 decision 4, "The process environment is chosen"). The comparison of variable names is exact (no case folding); the executor states in `## Result` whether Windows' case-insensitive environment needs any handling and, if a choice is made, tests it on the platform where it applies (a test may be skipped where it cannot apply).
3. **Module docstring** of `hilclaw/turn_loop.py`: a short paragraph "**Decided by ADR-0141**" in the manner of the ADR-0118 and ADR-0139 paragraphs, naming decision 4 and the three variables. The sentence "it gets the environment of the calling process unchanged" becomes accurate (the environment of the calling process with those three changes). The runtime acceptance list gains ADR-0141's (xli) and (xlii) (by number, not restated), and says that the stub shows nothing of a real session. Nothing else of the docstring changes, and no other module's docstring changes (the self-check session's environment stays unchanged).
4. **Tests** in `tests/test_turn_loop.py`. The stub `claude` (`STUB`) additionally records the values of the three variables, and of one unrelated variable the test sets, as it sees them (a stub written by the test is not a child session, D16). No real `claude` is started, no container is run. They pass on Linux CI and on the local Windows machine. They cover at least:
   - **happy**: with none of the three variables set in the calling process, each of two turns sees `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` `"0"`, `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` `"1"` and no `CLAUDE_AUTO_BACKGROUND_TASKS`; an unrelated variable set by the test (for example via `monkeypatch.setenv`) reaches the session unchanged.
   - **branch (replacement)**: with the caller's `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` set to another value (for example `"60000"`), `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` set to `"0"` and `CLAUDE_AUTO_BACKGROUND_TASKS` set to `"1"`, the session sees `"0"`, `"1"` and the third absent.
   - **branch (read at each turn)**: a change of the caller's environment between two turns (made by `further_turn`) of an unrelated variable is seen by the second turn, and the three variables are still as AC 1 says at the second turn — or, if the executor builds the environment once per `run`, that choice is stated in the docstring and tested instead.
   - **negative**: after `run` returns (and after it raises, for example with `ClaudeNotFoundError` at a later turn), the calling process's `os.environ` still holds the caller's original values of the three variables; the server entry's `env` is still exactly `{config.ENV_LOCAL_PATH: <real data root>}` (the existing `test_configuration_content` stays green); no file other than the definition's and `CONFIG_FILE` is in the session directory when the stub starts (no settings file was written).
   - the existing tests of `tests/test_turn_loop.py`, `tests/test_turn_start.py`, `tests/test_fresh_run.py` and `tests/test_further_turn.py` stay green unchanged, except where `STUB`'s new record requires adjusting an assertion on the record's members.
5. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more; ② the tests include happy, error and branch cases and negative cases; ③ every public function of `hilclaw/turn_loop.py` stays tested; ④ no new module is added, so no new test file is required; ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
6. **No data-plane change**: no member, file, kind of event, value or version of `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json`, `spec.json` or any other data-plane file is added or changed, and no validator changes. If the work turns out to need one, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
7. **Size**: the non-test change stays within the D4 cap (≤ 300 LOC, ≤ 5 files); it is expected to be well under.
8. **Language**: Python. The executor records the choice and one reason in the commit body and in `## Result` (CLAUDE.md language policy).
9. **Code mode (A-13)**: a Draft PR whose title contains `T-0386`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0386`, and the branch `claude/T-0386-turn-session-environment` deleted.
10. No `claude` process is started (only the test's stub), no container is started, and nothing runtime-only is required (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/`: no ADR, register row, proposal section or scenario note. The "less exact, not edited" sentences of ADR-0141 Consequences (ADR-0118 decision 6, R7, item (v); ADR-0010 decision 8) are not edited.
- Slice 3: `orchestration/agents/coder-driver.md`, the `hilclaw/turn_permissions.py` docstring, and `tests/test_turn_definition.py` / `tests/test_turn_permissions.py`.
- Slice 4: `orchestration/round-manager.md` and its test.
- The runtime self-check session (`hilclaw/selfcheck_session.py`) and its environment; the MCP front's protocol behaviour (no progress notifications); a per-server `timeout` in the `--mcp-config` entry; any `settings.json` of the definition (PLAN P2-4).
- Any value of `MCP_TOOL_TIMEOUT`, of the stall timer or of the background-wait ceiling; any time limit of a turn or a call (OD-14, OD-19).
- Slice (d) and everything of HQ-0053; the files of open PR #186.

## Follow-ups

- Next for the planner: ADR-0141 Consequences slice 3 (`orchestration/agents/coder-driver.md` with its test, and the `hilclaw/turn_permissions.py` docstring), then slice 4 (step 2 of "The round steps" in `orchestration/round-manager.md` and the moved stop, with its test).

## Result

DONE. PR #223 squash-merged as 1d83884 after 2 review rounds (round 1 Approve with one docstring-reflow nit, fixed; round 2 Approve). Local tests (full suite 25795 passed, 520 skipped, run with `--basetemp` under `%LOCALAPPDATA%` because a marker lies above the default temp dir) and all PR CI checks green, coverage gate included.

- `hilclaw/turn_loop.py`: private constants `_ENV_SET` (`CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` `"0"`, `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` `"1"`) and `_ENV_REMOVED` (`CLAUDE_AUTO_BACKGROUND_TASKS`); `_environment()` copies `os.environ` at every turn, applies them and is passed as `env=` to the session. `os.environ`, the server entry, the command line, cwd and the standard streams are unchanged; no settings file; no limit variable touched. Docstring: "Decided by ADR-0141" paragraph, the environment sentence made accurate, acceptance items (xli) and (xlii) added with the note that the stub shows nothing of a real session. The constants are private, so they are not named in the docstring; the tests use the literal variable names.
- `tests/test_turn_loop.py`: the stub records the three variables, an unrelated one and the three left-alone limit variables; tests for happy (two turns), replacement, read at each turn, the caller's environment after a later turn raises `ClaudeNotFoundError`, no settings file, and lower-case names on Windows.
- Windows case: name comparison is exact. CPython's `os.environ` on Windows stores keys upper-cased, so a caller's lower-case spelling (for example `claude_auto_background_tasks`) is already the upper-case key in the copy and is replaced or removed; no extra handling is needed. `test_lower_case_names_on_windows` checks this and runs on Windows only (skipped elsewhere).
- Language: Python, because the turn loop is an existing Python module of the tool layer and the change is confined to it.
- Runtime acceptance items (xli) and (xlii) (HQ-0056) are not closed by this task.
