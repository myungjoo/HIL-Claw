---
id: T-0404
title: Have the turn loop write the session directory's .claude/settings.json with the caller check hook of ADR-0146, refusing a definition's own settings.json (ADR-0146 code slice 2; PLAN P2-4)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-4, FR-9, FR-10, FR-11, OD-18, PLAN P2-4]
dependsOn: [T-0402, T-0403]
touchesFiles: [hilclaw/turn_loop.py, tests/test_turn_loop.py, hilclaw/caller_check.py]
estimatedSize: {loc: 110, files: 2}   # non-test: hilclaw/turn_loop.py (~100 with docstring) and hilclaw/caller_check.py (docstring, ~3); test files are excluded from the cap (D4)
hq: []
---
## Why

PLAN P2-4 (runtime hooks) is a checklist item on the road to P2-5 (DRIVER §6, D18; PLAN P2 order: P2-1 to P2-4, P2-6, P2-7, then P2-5). ADR-0146 (landed as a368b11, T-0402) closes the caller-check part of OD-18 for the turn sessions of ADR-0120 decision 1. Its Consequences name two code slices. Slice 1, the hook program `hilclaw/caller_check.py`, landed as 131a775 (T-0403, PR #235). This task is **slice 2, the settings write**. The turn loop writes the session directory's `.claude/settings.json` after the definition is put, so a turn session runs the hook. Until this lands, nothing names the hook program. The Round-Manager can then still call `verdicts_write`, `correctness_check` or `coder_run` against its definition, and ADR-0146 Context reads that as a gap before the first run (FR-9 floor).

Test rule: `hilclaw/turn_loop.py` is a module of the layer-2 package, so rules ① to ④ of CLAUDE.md "테스트 규칙" apply (DRIVER §5, D12). Rule ⑤ does not apply. This task changes no hook script, CI workflow or test helper as its subject. The stub `claude` the tests already write stays a test fixture.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, time cap) and §5 (lines 86-114: task format, naming convention, size cap, test rules).
- `CLAUDE.md` "테스트 규칙", "개발 드라이버와 런타임의 구분" and "코멘트 최소화".
- `ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md`: Context rows H3, H5, H6 (lines 27, 29, 30); Decision §2 (lines 42-50), §4 (lines 61-68), §5 (lines 70-73) and §6 (lines 75-91); Consequences slice 2 (line 134) and the "Less exact" list (lines 142-150).
- `hilclaw/turn_loop.py` (whole file, 357 lines). Read especially `_config_text`, `_turn` and `run`, and the docstring sections "Decided by …", "What is raised", "Not done here" and "Runtime acceptance items".
- `hilclaw/caller_check.py` lines 1-63 (docstring, `START`, `TOOL_PREFIX`, `EXIT_PASS`, `EXIT_REFUSE`, `ENV_PROJECT_DIR`).
- `hilclaw/turn_definition.py` lines 1-100. `put` removes `.claude/settings.json` when `orchestration/` has no `settings.json`, and copies it when present. It refuses a session `.claude` that is no plain directory. `LAYOUT` keeps the key `settings.json`.
- `hilclaw/turn_permissions.py` lines 1-80. It reads only `.claude/agents/`, and its docstring says "it writes no settings file". That stays true.
- `tests/test_turn_loop.py` lines 1-280 (the stub `claude`, fixtures `stub`, `only_the_stub`, `put`, `put_agent`, `go`, `expected_argv`) and lines 905-930 (`test_no_settings_file_is_written`, which this task replaces).

## Acceptance Criteria

1. **The written file.** In `hilclaw/turn_loop.py`, each turn follows `put_definition(...)` and the existing check that `CONFIG_FILE` is not taken. Before `turn_permissions.options` and before the process starts, the loop writes `<session>/.claude/settings.json` (UTF-8, created with exclusive create, mode `"x"`). The file is exactly one JSON object with one member, `hooks`, and it has no `permissions` and no `env` (ADR-0146 decision 4; ADR-0139 decision 8). Its shape:
   `{"hooks": {"PreToolUse": [{"matcher": M, "hooks": [{"type": "command", "command": C, "args": A, "timeout": T, "onFailure": "block"}]}]}}`.
   - `M` is a regular expression anchored to the prefix: `"^" + caller_check.TOOL_PREFIX`. It must hold a character outside the exact-match set of H2, so that Claude Code reads it as a regular expression (`^` does this).
   - `C` is `os.path.abspath(sys.executable)`. The existing `RuntimeError` for an empty `sys.executable` still applies.
   - `A` is `["-I", "-c", caller_check.START, checkout_boundary.PACKAGE_DIRECTORY]` (the server entry's form).
   - `T` is a module constant in seconds, well below 600. The planner proposes 30. Record the value chosen, and why, in `Result`.
   - Check the placement of `onFailure` and `timeout` inside the command hook object against the `hooks` page that ADR-0146 H3/H5 cite (https://code.claude.com/docs/en/hooks). Reading that page is allowed; running `claude` is not. If the page puts them elsewhere, follow the page and say so in `Result`.
   - Build the text once in `run` with the server configuration, as `_config_text` is built, and write the same text in every turn.
2. **`.claude` itself.** When `<session>/.claude` does not exist, the loop creates it as a plain directory. A definition with no agents may leave it absent; `put_agent` in the tests already creates it. When it exists and is a symbolic link, a junction, or no directory, the loop raises `ValueError` with a fixed text before writing anything into it. A real-path comparison is one way to catch a junction on Windows.
3. **A definition's own settings.** When `<session>/.claude/settings.json` already exists (any kind of entry, by `os.path.lexists`) after `put_definition`, the turn is refused: `ValueError` with a fixed text, for example "the definition holds the hook settings file". Nothing is merged or overwritten, and no process starts (ADR-0146 decision 4). The directory is still removed, as for the other refusals. `LAYOUT` in `hilclaw/turn_definition.py` keeps its `settings.json` key, and `turn_definition.py` is not edited. The planner takes this choice, which ADR-0146 decision 4 leaves to the code slice: the loop's check covers every `put_definition`, and `turn_definition`'s "no settings, hooks or permissions" stays true of the copy.
4. **Docstrings.**
   - `hilclaw/turn_loop.py`: the opening paragraph names the settings file among what the loop writes. A new "**Decided by ADR-0146** and only applied here" paragraph states decision 4 as applied. Name the timeout value and the anchored matcher under "Choices of this module". "What is raised" gains the two new `ValueError`s (criteria 2 and 3). "Runtime acceptance items" gains ADR-0146's (lvi) to (lx) by number, with a one-line pointer to `hilclaw.caller_check`, which lists them. No other sentence is changed unless it becomes false.
   - `hilclaw/caller_check.py`: the sentence "Not registered here: no settings file names this program; slice 2 of ADR-0146 writes the settings." becomes a short sentence saying that `hilclaw.turn_loop` writes the settings that name this program. Nothing else in that file changes.
5. **Tests** in `tests/test_turn_loop.py` (stub `claude` only; never a real one, D16):
   - Extend the stub so that it also records the text of `.claude/settings.json` in its cwd, or `None` when the file is absent.
   - *Happy*: the recorded text parses to exactly the object of criterion 1. `command` equals the absolute `sys.executable` and is the same interpreter as the server entry's `command`. `args[2]` is `caller_check.START`, and the top-level keys are only `hooks`. The file is written in every turn of a two-turn loop, and the parent directory is empty afterwards. `test_no_settings_file_is_written` and the two listing asserts at lines 273 and 924 are updated to the new listing (`.claude` added).
   - *Hook runs as written*: a test has the stub run the recorded hook entry itself. It runs `command` with `args` as the argument vector, with no shell, `CLAUDE_PROJECT_DIR` set to the session directory and a fixture `PreToolUse` input on standard input. The stub records the exit statuses. A main-session call (no agent fields) of `mcp__hilclaw__state_write` gives `caller_check.EXIT_PASS`. One of `mcp__hilclaw__verdicts_write` gives `caller_check.EXIT_REFUSE`. With `put_agent`, a sub-agent call of a tool in that agent's `tools` gives a pass, and a call of a tool outside it gives a refusal. This hook process is a Python interpreter, not `claude`; the `only_the_stub` guard is unaffected.
   - *With agents*: with `put_agent`, the existing `.claude/agents/` is kept and the settings file sits beside it.
   - *Negative*: (a) a `put_definition` that writes `.claude/settings.json` is refused with the fixed text, with no stub call and the directory removed. (b) The same happens for a `.claude/settings.json` that is a directory or a dangling symbolic link (skip the link case where links cannot be made). (c) A `.claude` that is a regular file is refused. (d) A `.claude` that is a symbolic link to another directory is refused, nothing is written in the link's target, and the target's contents are unchanged (skip where links cannot be made). (e) An empty `sys.executable` still raises `RuntimeError` before the first turn.
   - *Branch*: a definition that leaves `.claude` absent gets it created, and one that made it keeps its contents.
   - Run the module's existing tests unchanged apart from the listing updates. All of `pytest`, `ruff check .` and `ruff format --check .` pass, and the coverage gate (line ≥ 80 %, function ≥ 80 % for `hilclaw/`) holds.
6. Size within the D4 cap (≤ 300 non-test LOC, ≤ 5 files). The diff touches only `touchesFiles`, plus this task file's `Result`.

## Out of Scope

- Any edit of `hilclaw/turn_definition.py`, `hilclaw/turn_permissions.py`, `hilclaw/turn_start.py`, `orchestration/`, any ADR or `ARCHITECTURE/` document, `.claude/` of this repository, or any settings file of this repository.
- `hilclaw/start_instance.py` and the files of open PR #186.
- Static settings under `orchestration/` and how they would combine with the written file (ADR-0146 Boundaries). The `--settings` fallback (ADR-0146 Alternatives) is not taken.
- Moving the ADR-0141 decision 4 environment variables into the file.
- Hooks of any other session (checkpoint session, coder container, self-check).
- Starting a real `claude` or checking any of ADR-0146 items (lvi) to (lx). Those are runtime acceptance items already recorded as HQ-0061.
- Editing the "Less exact, not edited" records that ADR-0146 lists.

## Follow-ups

- (planner) None planned from this slice. After it lands, ADR-0146's two code slices are done. The rest of PLAN P2-4 (budget and gate checks, PostToolUse journaling, Stop commit; OD-18 and OD-19 remainder) is for later planning.

## Result

- PR #236 (branch `claude/T-0404-turn-loop-writes-hook-settings`), squash-merged; review rounds: see the merge commit and the PR comments (round 1 Approve with two nits, both fixed in the PR, then re-reviewed).
- Language: Python, the language of the module being extended (`hilclaw/turn_loop.py`).
- Timeout: `HOOK_TIMEOUT_S = 30` seconds, as the planner proposed. One interpreter start and one read of the session's agent files take well under a second or two even on a slow Windows machine, so 30 s leaves a wide margin. With `onFailure: "block"`, a hook that hangs blocks the call within 30 s instead of the 600 s default. It is also the default Claude Code itself uses for the shorter-lived hook events.
- Field placement: checked against https://code.claude.com/docs/en/hooks (read with `curl`; no `claude` was run). `timeout` is a "Common field" of a hook handler, and `onFailure` is a "Command hook field". Both sit inside the command hook object, as criterion 1 has them; the page's own `onFailure` example uses the same shape. The page's "Matcher patterns" table confirms that a matcher with a character outside letters, digits, `_`, `-`, spaces, `,` and `|` is read as an unanchored JavaScript regular expression, so `^mcp__hilclaw__` is both regular and anchored.
- Junction check: a `.claude` is refused when it is a link, no directory, or when its real path differs from `<real session>/.claude`; the last catches a Windows junction (tested on Windows with `_winapi.CreateJunction`).
- Local: full `pytest` 26273 passed, 564 skipped, with a marker-free `--basetemp` (this machine's system temp holds a stray `claude.md`, see T-0338). The two symlink tests skip here (no link privilege) and run on Linux CI. `ruff check` and `ruff format --check` are clean. Coverage: `turn_loop.py` 100 %, `caller_check.py` 100 %, `hilclaw/` 99 %.
- Runtime acceptance: ADR-0146 items (lvi)-(lx) stay open as HQ-0061; nothing new.
- Follow-ups: none from this slice. Reviewer note (info only): a definition-brought `.claude/settings.local.json` is not refused. It is out of this slice's scope, because the real `put_definition` copies only `LAYOUT`, and the turn uses `--setting-sources project`. Later P2-4 planning may consider it.
