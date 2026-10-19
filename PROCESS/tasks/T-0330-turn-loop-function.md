---
id: T-0330
title: Add the turn loop of ADR-0118 decision 3 to hilclaw (one function that starts one Claude Code turn session per turn in a fresh session directory with the package's MCP front, until the caller's predicate says no further turn), tested only against a stub claude
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, NFR-1, NFR-7, OD-18, C-7]
dependsOn: [T-0329]
touchesFiles:
  - hilclaw/turn_loop.py
  - tests/test_turn_loop.py
estimatedSize: {loc: 260, files: 1}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first item of the P2 order (D18). It is a PLAN checklist item, so the D18 priority rule does not apply. P1 has nothing left that can be planned now:
- P0.5-4 waits on the owner's hook registration;
- the rest of P1-1 waits on HQ-0021, HQ-0025, HQ-0026 and OD-14 ①;
- P1-8's D18 completion criterion is the driver's to tick.

T-0329 landed ADR-0118. Its decision 3 says one function of `hilclaw/`, the **turn loop**, starts every turn session of a first-case run. Its Consequences name this as code slice (1): the loop takes from its caller a predicate, asked before every turn, until an OD-8 record defines the member that says a run is over, stopped or waiting. The loop is tested against a stub `claude` that the tests write (D16).

This task builds that function and the part of slice (2) that ADR-0118 fully decides: the session directory of decision 4 and the server configuration file of decision 6. Three things stay open and are taken from the caller:
- the definition copy, because the layout of `orchestration/` is the definition task's;
- the prompt;
- the predicate.

Nothing calls the function yet. No `claude` is started by the driver or the executor (D16). Only the tests' stub is run.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0330` trailer (also as the last line of the PR body), size cap, test rules.
- `CLAUDE.md`, these rules: "세 층 모델", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화", "미결은 발명하지 않는다".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`:
  - Decision 1 to 6 (lines 48-123);
  - Consequences "Code slices" and "Runtime acceptance items" (lines 154-167);
  - Boundaries (lines 186-200).
- `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`, decisions 2 and 3: what "deterministic, no judgement, no FR-10 tool" means.
- `hilclaw/selfcheck_session.py` (277 lines, read it all). It is the model for these:
  - a directory made outside both checkouts with `checkout_boundary`;
  - a configuration file under `mcpServers` named by file name alone with `--mcp-config` and `--strict-mcp-config`;
  - the Windows `.cmd` prompt limits;
  - removal with retries;
  - the docstring conventions.
- `hilclaw/selfcheck_server.py` lines 110-130 and 182-201: `_START` and `server_entry`. These show how a server started from any working directory finds this package.
- `hilclaw/checkout_boundary.py` (56 lines).
- `hilclaw/mcp_front.py` lines 1-60 and 205-246: the package's MCP front, `main` and `SERVER_NAME`.
- `hilclaw/config.py` lines 1-60: `ENV_LOCAL_PATH` and how the data root is read.
- `tests/test_selfcheck_session.py` lines 200-300: the stub-`claude` fixture pattern (PATH set to the stub's directory, a POSIX `sh` launcher or a Windows `.cmd` launcher, a record of every start).

## Acceptance Criteria

1. **Session entry check.**
   - Run `gh pr list`.
   - Open Draft PR #186 (T-0324) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`; this task touches none of them.
   - If any open PR edits a file of touchesFiles, stop and report.

2. **New module `hilclaw/turn_loop.py`** (Python; give the reason in one line of the commit body). It has one public entry `run(*, further_turn, put_definition, prompt, data_root, parent=None, keep_out=())`. It repeats the steps of ADR-0118 decision 3:
   - **(1) Ask the caller.** Call `further_turn(previous)`. `previous` is `None` before the first turn, and after a turn it is the exit status of the last turn session (an `int`). Return when the answer is `False`. An answer that is not a `bool` raises `TypeError`, and no further turn starts. The loop decides nothing about a failed turn: retry, stop, wait and notify stay open (ADR-0118 decision 3, OD-10/17/19/27). It only passes the status on.
   - **(2) Prepare the session directory.**
     - Make a new directory per turn with `tempfile.mkdtemp` under `parent` (default: the system temporary directory). Per turn is this task's choice, which ADR-0118 decision 4 leaves to the code; give the reason in the module docstring.
     - Then call `put_definition(session_dir)` with the directory as a `pathlib.Path`.
     - Then write the server configuration file (below), created exclusively. If `put_definition` already made that name, refuse it with `ValueError`; no session starts.
   - **(3) Start one turn session.** The command line is exactly `claude -p <prompt> --mcp-config <CONFIG_FILE> --strict-mcp-config`:
     - `claude` is resolved on `PATH` at each turn;
     - the configuration file is named by file name alone;
     - the working directory is the session directory, standard input is closed (`DEVNULL`), and the environment is inherited unchanged;
     - the loop does not read standard output or standard error.
     - No permission, model, turn-limit, setting-source or bypass flag is passed: how a turn session gets its permissions is open (ADR-0118 decision 4, "Workspace trust"). Name this in the docstring.
   - **(4) Wait** until the process has ended, with no time limit of the loop's own: a turn limit is OD-19's or OD-14's.
   - **(5) Remove** the session directory whatever happened, an exception included. Retry briefly as `selfcheck_session._remove` does. Then go back to (1).
   - Two turn sessions are never running at once.

3. **Return value.** A tuple with one record per turn session started, in order. Each record holds `exit_status` (`int`) and `removed` (`bool`). An immutable `NamedTuple` is fine.

4. **The place of the session directory** (ADR-0118 decision 4). These checks run before anything is made, on real paths. Each refusal raises `ValueError` with a fixed text and starts no turn:
   - `parent` is refused if it is, lies inside or contains the directory that holds this package, the real path of `data_root`, or any directory of `keep_out`. Use `checkout_boundary`; `keep_out` given as one path raises `TypeError` as `refuse_one_path` does.
   - `parent` is refused if it, or any ancestor of it, holds an entry named `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, or `.claude`. The one exception is `.claude` when it is the runtime user's own configuration directory, `Path.home() / ".claude"` compared by real path.
   - The check is made once per `run` call, before the first turn, and again before each turn. A file placed between turns is then found.

5. **The server configuration file** (ADR-0118 decision 6).
   - `CONFIG_FILE` is a module constant. It is not `.mcp.json` (decision 6).
   - It holds one JSON object `{"mcpServers": {SERVER_NAME: entry}}`, where `SERVER_NAME` is `hilclaw.mcp_front.SERVER_NAME`.
   - The entry has exactly `command`, `args` and `env`:
     - `command` is `sys.executable`;
     - `args` is `-I`, `-c`, and a start text like `selfcheck_server._START` that puts the package directory first on `sys.path` and runs `hilclaw.mcp_front.main`, so that the server finds this package from the session directory;
     - `env` is exactly `{config.ENV_LOCAL_PATH: <real absolute data_root>}`.
   - Giving the data root through the environment is this task's choice, which ADR-0118 decision 6 leaves to the code. Give the reason in the docstring: the server names the same data root whatever its working directory is.
   - `data_root` must be a `str` or path object naming an existing directory. Otherwise raise `TypeError` or `ValueError` before any turn.
   - If the interpreter does not know its own path, raise `RuntimeError`.

6. **Argument checks**, all made before the first turn, each raising `TypeError` or `ValueError`:
   - `further_turn` and `put_definition` must be callable;
   - `prompt` must be a non-empty `str` of one line of the characters `selfcheck_session` allows: ASCII letters, digits, spaces, `.`, `,` and `_`. Say why in the docstring: on Windows `claude` may be a `.cmd` script.
   - If `claude` is not found on `PATH` at a turn, raise a module exception (a subclass of `RuntimeError` or `LookupError`, your pick) after removing that turn's directory. The turns already run are lost to the caller then; say so in the docstring.
   - An exception raised by `further_turn` or `put_definition` propagates, after that turn's directory is removed.

7. **Docstring.** A module docstring in the style of `selfcheck_session.py`. It names what is decided by ADR-0118 and what is this module's choice. It also lists what is not done:
   - no lock against two loops on one run (#4 §2e, OD-17);
   - no command-line entry, which waits on the OD-8 member; this is a Follow-up;
   - no definition layout;
   - no permissions;
   - no round-0 step and no self-check before a turn (OD-18 ⑯ (가));
   - no retry policy, no data-plane write and no caller.
   It ends with the runtime acceptance items it depends on: ADR-0118 (i), (iv), (v), (vi). Keep comments in the code minimal (CLAUDE.md).

8. **Tests `tests/test_turn_loop.py`**, against a stub `claude` written by the tests only, in the fixture pattern of `tests/test_selfcheck_session.py`. PATH holds only the stub's directory. The stub records its argv, its working directory, the files it sees there and the configuration file content, then exits with a status from its scenario. Include at least:
   - **happy:**
     - two turns, then the predicate says stop: two records, the statuses passed to the predicate in order (`None`, then the first status), and the exact argv;
     - the working directory is a fresh directory per turn, holds what `put_definition` wrote, and is gone afterwards;
     - the configuration content, with `env` holding the real data root;
     - a predicate that says `False` at once starts no session and makes no directory.
   - **branch:**
     - a non-zero exit status of the stub is passed to the predicate and the loop goes on when it answers `True`;
     - `keep_out` empty versus given;
     - `parent` default versus given.
   - **error and negative:**
     - a non-bool predicate answer;
     - non-callable `further_turn` or `put_definition`;
     - a bad prompt: empty, multi-line, a disallowed character, not a `str`;
     - a `data_root` that is missing, not a directory or of a wrong type;
     - `keep_out` given as one path;
     - a `parent` inside the package directory, inside `data_root` or inside a `keep_out` directory, and one that contains the data root;
     - a `CLAUDE.md`, `AGENTS.md` or foreign `.claude` in an ancestor of `parent` (use a `tmp_path` subtree), and the user's own `~/.claude` accepted (monkeypatch `Path.home`);
     - a marker file placed between turns, which stops the second turn;
     - `put_definition` creating `CONFIG_FILE`;
     - `put_definition` raising: propagates, directory removed;
     - `claude` missing on `PATH`;
     - the `RuntimeError` when `sys.executable` is empty.
   - The server entry's start text runs `hilclaw.mcp_front` from another working directory: start it with `subprocess`, closed standard input, and assert exit status 0.
   - Every public function and the module are covered. Package coverage stays at least 80% line and function (D12). `ruff` passes.

9. **Scope and size.**
   - `git diff --stat origin/main` lists only touchesFiles.
   - At most about 300 changed lines outside the test file.
   - No edit to any other module, `ARCHITECTURE/`, `orchestration/` (not created), `.claude/`, `CLAUDE.md`, `pyproject.toml`, CI or `PROCESS/` (besides this task file's Result).
   - No new dependency.
   - No data-plane schema change: no member, file, kind or version.

10. **D16.** No real `claude` is started by the executor or the reviewer (no subcommand, no flag). Only the test-written stub runs. No board, accelerator or API key is required.

11. **Merge.** Code mode under CLAUDE.md A-13:
    - branch `claude/T-0330-turn-loop-function`;
    - Draft PR titled with `T-0330`, the PR body ending with `Task: T-0330`;
    - context-isolated reviewer cycle (dev-code-review, at most 7 rounds) until Approve;
    - CI green;
    - `gh pr merge --squash --body` with that body, then delete the branch.

## Out of Scope

- The command-line entry of the loop and any caller. The start function of ADR-0115 (PR #186).
- The Round-Manager definition, the layout of `orchestration/` and which file becomes `CLAUDE.md` or `.claude/...` in the session directory.
- Permissions, allowlists, trust records, `--settings`, `--allowedTools` and the permission mode.
- The lock of #4 §2e, retry or backoff after a failed turn, time limits, budgets and notifications.
- Round 0, the self-check before a turn, and any `STATE.json` member.
- Anything held in PLAN's 보류 section, and anything blocked by HQ-0021, HQ-0025, HQ-0026, HQ-0032 or HQ-0034.

## Follow-ups

- Next P2-1 slices:
  - the Round-Manager definition under `orchestration/`, with its layout and the `put_definition` that copies it into the session directory (code mode, as ADR-0118 Consequences notes);
  - the round-0 procedure.
- The loop's command-line entry, once an OD-8 record defines the `STATE.json` member that says a run is over, stopped or waiting (ADR-0118 decision 3). Until then a caller supplies the predicate.

## Result
- Outcome: DONE. PR #189 squash-merged as fcc98b7 (branch `claude/T-0330-turn-loop-function` deleted). Review: 2 rounds, Approve in both. Round 1 had one nit, fixed in round 2: the docstring now says that `Turn.exit_status` is negative on POSIX for a session ended by a signal. CI green: Python 3.11/3.14, Coverage, C, sh and Test presence gates.
- Language: Python. The loop joins existing Python modules of the package (`checkout_boundary`, `config`, `mcp_front`), and pytest tests it.
- Files: `hilclaw/turn_loop.py` (301 lines), `tests/test_turn_loop.py` (631 lines). Line coverage of `turn_loop.py` is 100% locally. Ruff passes.
- Choices made in the module:
  - one session directory per turn;
  - the data root reaches the server through `HILCLAW_DATA_REPO_LOCAL_PATH`;
  - `CONFIG_FILE = "hilclaw-turn.mcp-config.json"`;
  - `ClaudeNotFoundError(LookupError)`;
  - a `parent` that is not an existing directory is refused with `ValueError` before the first turn.
- Environment note: this machine's system temp directory holds a stray `claude.md`. On a case-insensitive file system it counts as `CLAUDE.md`, so the module refuses places under that directory, as designed. The test file therefore skips itself when a marker lies above pytest's temporary directory. It was run locally with `--basetemp` under `%LOCALAPPDATA%`, and CI (Linux) runs it unskipped. `test_own_claude_directory_accepted` also skips wherever the real `~/.claude` lies above the base temp.
- Follow-ups: none new. The Follow-ups section above stands: the definition under `orchestration/` with its `put_definition`, the round-0 procedure, and the command-line entry once the OD-8 member exists.
