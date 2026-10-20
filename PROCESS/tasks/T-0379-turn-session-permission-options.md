---
id: T-0379
title: Start every first-case turn session with the permission options of ADR-0139 — dontAsk, --tools, --allowedTools derived from the Round-Manager's fixed list and the agent files, --setting-sources project (ADR-0139 slice 1; PLAN P2-1/P2-4)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, NFR-4, C-7, OD-18, OD-23, S0]
dependsOn: [T-0378]
touchesFiles:
  - hilclaw/turn_permissions.py
  - hilclaw/turn_loop.py
  - tests/test_turn_permissions.py
  - tests/test_turn_loop.py
  - tests/test_turn_start.py
estimatedSize: {loc: 200, files: 2}
hq: []
---
## Why

PLAN P2-1 (Round-Manager, round 0) and P2-4 (hooks; OD-18) are checklist items that come before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. Today `hilclaw/turn_loop.py` starts every turn as `claude -p <prompt> --mcp-config hilclaw-turn.mcp-config.json --strict-mcp-config` and nothing else. With no permission option, a `-p` turn session denies every tool call that needs approval, so the Round-Manager and the evaluator cannot call their `hilclaw` tools. P2-5's first run, the nightly run of P2-10 and P2-14 all wait on this.

ADR-0139 (landed on main as 930e7eb, T-0378) decides the means. Its Consequences name code slice 1: the command line of `hilclaw/turn_loop.py`, with the options of decisions 2, 4 and 7, the list of decision 3 built after `put_definition` from the session directory's `.claude/agents/` and a fixed Round-Manager list, the refusals of decision 3, and an optional new module for the frontmatter reading and the list. This task is that slice. Slice 2 (the coder-driver entry) waits on HQ-0040 and is not part of this task.

The code is tested only with the stub `claude` the tests already write. No real `claude` is started, and nothing is required of the development machine (D16). Whether the options take effect in a live session is covered by ADR-0139's runtime acceptance items (xxxiv)-(xl), already notified as HQ-0055. This task does not close them.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming convention, D4 size cap, test rules).
- `CLAUDE.md` sections "테스트 규칙", "도구 계층 언어 정책", "브랜치·merge 절차", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (what the reviewer checks).
- `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md`: Decision §1-§10 and the Walk-through (lines 42-123), and Consequences "Code slices for the planner" item 1 and the runtime acceptance items (xxxiv)-(xl) (lines 146-156).
- `hilclaw/turn_loop.py` (whole, 303 lines).
- `hilclaw/turn_definition.py` lines 1-80 (layout of the copy; `.claude/agents/` may hold nested directories).
- `hilclaw/selfcheck_session.py` lines 100-160 (the self-check's option constants `OPT_SETTING_SOURCES`, `OPT_TOOLS`, `OPT_PERMISSION_MODE`, `OPT_ALLOWED_TOOLS`, `ALLOWED_TOOLS_SEPARATOR`; follow their naming style, and reuse them only if that adds no import cycle).
- `hilclaw/mcp_front.py` lines 40-72 (`SERVER_NAME`, `mcp_name`).
- `orchestration/agents/evaluator.md` lines 1-5 (the only agent file today) and `orchestration/round-manager.md` (the tools the prompt names).
- `tests/test_turn_loop.py` (whole: the stub, `expected_argv`, `put`), `tests/test_turn_start.py` lines 100-160 (its stub tells the self-check from a turn by `"--allowedTools" in argv`) and lines 560-610, and `tests/test_turn_definition.py` lines 120-155 (the existing frontmatter test of the evaluator).

## Acceptance Criteria

1. **New module `hilclaw/turn_permissions.py`** (Python; it holds the fixed list and the derivation of ADR-0139 decisions 3, 4 and 6):
   - A public constant holding the Round-Manager's fixed list, exactly: `mcp__hilclaw__state_read`, `mcp__hilclaw__instance_read`, `mcp__hilclaw__run_fresh`, `mcp__hilclaw__state_write`, `mcp__hilclaw__run_commit`, `mcp__hilclaw__key_store`, `mcp__hilclaw__case_write`, `mcp__hilclaw__round_end` (ADR-0139 decision 3, Source 1).
   - Public option constants: `--permission-mode` / `dontAsk`, `--tools`, `--allowedTools`, `--setting-sources` / `project`, and the separator `,`.
   - One public function, called with a session directory, that returns the option arguments to append after `--strict-mcp-config`, as a tuple of `str`: `--setting-sources project --tools <built-in set> --permission-mode dontAsk --allowedTools <pre-approved list>`. The order of these options is the module's choice, and the docstring states it.
   - **Reading the agent files** (ADR-0139 decision 3, Source 2): it reads every regular file whose name ends in `.md` under `<session>/.claude/agents/`, at any depth, in a fixed (sorted) order. If that directory is absent there are no agents. Each file must start with a line `---` and have a later closing line `---`. Every line between them is `key: value`, with each key at most once. The module takes `name` and `tools`, and `tools` is split on commas with the entries stripped. Both `\n` and `\r\n` line ends are accepted. No YAML library or any other new external dependency is added.
   - **Refusals**, each a `ValueError` with a fixed text and raised before anything is returned:
     - a file that is not UTF-8;
     - a file with no frontmatter as defined above, or a line between the markers that is not `key: value`;
     - a missing or malformed `name` (the accepted form, e.g. lowercase letters, digits and `-` starting with a letter, is the module's and the docstring states it);
     - no `tools` key, or an empty `tools` value (an omitted list inherits every tool, ADR-0139 P8);
     - a `tools` entry that is neither an exact `mcp__hilclaw__<name>` (with `<name>` in a stated form, such as lowercase letters, digits and `_`) nor exactly one of `Read`, `Grep`, `Glob`. This covers wildcards, `mcp__hilclaw` alone, `mcp__hilclaw__*`, another server's name, `Bash`, `Write`, `Edit` and `Agent`;
     - a `permissionMode` key.
   - **The built-in set** (decision 4): `Agent` when at least one agent was read, plus every built-in name (`Read`, `Grep`, `Glob`) that the agents' `tools` lists hold. The names are sorted, without repeats, and joined by `,`. With no agent the value is the empty string `""`.
   - **The pre-approved list** (decisions 3 and 6) is the union of the fixed list, `Agent(<name>)` for each agent, and every entry of every agent's `tools` list. It is sorted, without repeats, and joined by `,` into one argument. It has no wildcard entry.
   - The module docstring states that it is runtime code tested only against fixture files, names ADR-0139 decisions 2-4, 6 and 7, and lists the runtime acceptance items it depends on: (xxxiv)-(xl) of ADR-0139. It also says that the coder-driver's entry (decision 9, HQ-0040) is not handled here: a `Bash` entry is refused.
2. **`hilclaw/turn_loop.py`**: in `_turn`, after `put_definition` has run and before the process starts, the command line becomes `PROGRAM`, `-p`, prompt, `--mcp-config`, `CONFIG_FILE`, `--strict-mcp-config`, followed by the arguments the new function returns for that session directory. A refusal raised there stops the turn before any process starts, and the directory is still removed (the existing `finally`). Update the module docstring:
   - rewrite "and nothing else" in **The command line**;
   - rewrite the sentence "No permission, model, turn-limit, setting-source or bypass option is passed: …" so that it names the options now passed, and says that no model, turn-limit or bypass option is passed (ADR-0139 decision 10);
   - remove "no permissions" from "Not done here";
   - add the new refusals under "What is raised".
   No other behaviour of the loop changes.
3. **No bypass**: no code path passes `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions`, `bypassPermissions`, `acceptEdits` or `auto`. A test asserts that none of these strings is in any argument of a started turn.
4. **Tests** (CLAUDE.md test rules ①-④; stub `claude` only):
   - New `tests/test_turn_permissions.py` covers every public function and constant:
     - happy path: no `.claude/agents/` gives `--tools ""` and exactly the fixed list; one agent with the evaluator's real frontmatter gives `Agent,Glob,Grep,Read` and the expected union;
     - two agents with overlapping tools give a deduplicated, sorted list;
     - a nested agent file is read; a non-`.md` file is ignored; `\r\n` line ends are accepted;
     - every refusal listed in criterion 1 is a negative case, each asserting its fixed text;
     - a check that every name of the fixed list is `mcp__hilclaw__` plus `mcp_front.mcp_name(n)` for a tool `n` registered in `hilclaw.tools.default_registry` (as `tests/test_turn_definition.py` does for the evaluator);
     - a test that runs the function on a session directory filled by `hilclaw.turn_definition.put` from the real `orchestration/`, and checks that it succeeds and that every tool of the evaluator's `tools` list is in the result.
   - `tests/test_turn_loop.py`: `expected_argv` and the affected tests expect the new options. Add a test where `put_definition` writes an agent file, and check that its `Agent(<name>)` and tools reach `--allowedTools` and its built-ins reach `--tools`. Add a test where `put_definition` writes a refused agent file: the `ValueError` propagates, no `claude` call is recorded, and the session directory is removed.
   - `tests/test_turn_start.py`: its stub must no longer classify a call as the self-check by `"--allowedTools" in argv`, because turn sessions now carry it too. Use an option only the self-check passes (for example `--no-session-persistence` or `--output-format`; check `hilclaw/selfcheck_session.py`). Its existing assertions keep passing, and one assertion checks that a turn call carries `--permission-mode dontAsk` and an `--allowedTools` that holds `Agent(evaluator)`.
   - `pytest`, `ruff check` and `ruff format --check` pass. `hilclaw/` line and function coverage stay ≥ 80%.
5. **Size**: non-test change within the D4 cap (≤ 300 LOC, ≤ 5 files). If the docstrings push it over, say why in the Result.
6. **D16 and boundaries**:
   - no real `claude` is started in any form;
   - nothing is required of the development machine;
   - `.claude/settings.json` and `.claude/settings.local.json` are not edited;
   - no file under `ARCHITECTURE/` or `orchestration/` changes;
   - no data-plane member, file, kind, value or version is added or changed;
   - no new external dependency.
7. The Result names the language and the reason in one line (CLAUDE.md language policy), the PR number, the review rounds, and any docstring elsewhere that this change made less exact. Such docstrings are listed in the Result, not edited.

## Out of Scope

- The coder-driver definition and its entry (ADR-0139 decision 9, ADR-0138 slice 2, HQ-0040), the coder's container session (HQ-0053, unlanded ADR-0137).
- Hooks of any kind (rest of PLAN P2-4), deny rules in a definition `settings.json`, gates (OD-3), budget checks (OD-19).
- The self-check's command line (`hilclaw/selfcheck_session.py`, ADR-0057): unchanged.
- `hilclaw/turn_start.py` and `hilclaw/turn_definition.py` code. Edit `turn_start.py` only if the fixed list cannot live in the new module, and say why in the Result.
- Any edit to `orchestration/round-manager.md` or `orchestration/agents/evaluator.md`, and to any ADR or `ARCHITECTURE/` file, including the "Less exact, not edited" sentences of ADR-0139.
- Checking agent `tools` entries against the registry at turn time. Only the form is checked.
- Anything from the unlanded branches `claude/T-0210-*`, `claude/T-0233-*`, `claude/T-0264-*`, `claude/T-0361-*`, `claude/T-0375-*`, and from draft PR #186.

## Follow-ups

- After HQ-0040 is answered: the coder-driver agent file, and under answer (B) the record and code that admit a `Bash(<entry command> *)` pattern (ADR-0139 decision 9).

## Result
