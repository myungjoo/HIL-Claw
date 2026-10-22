---
id: T-0407
title: Have the turn loop write the second PreToolUse entry of ADR-0147 (the round-budget check on the two spending tools, with the data-root argument) into the session's .claude/settings.json (ADR-0147 code slice 2; PLAN P2-4)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-3, FR-4, NFR-5, OD-19, OD-18, "PLAN P2-4"]
dependsOn: [T-0405, T-0406, T-0404]
touchesFiles: [hilclaw/turn_loop.py, tests/test_turn_loop.py, hilclaw/budget_check.py]
estimatedSize: {loc: 60, files: 2}   # non-test: hilclaw/turn_loop.py (~50 with docstring) and hilclaw/budget_check.py (docstring, ~4); the test file is excluded from the cap (D4)
hq: []
---
## Why

PLAN P2-4 (runtime hooks: PreToolUse budget and gate checks, PostToolUse journaling, Stop commit) is a checklist item. PLAN's P2 header puts it before P2-5, so the D18 priority rule (DRIVER §6) does not apply to it. ADR-0147 (landed as `afa64a2`, T-0405) closes the round-budget part of OD-19, and a part of OD-18, for the turn sessions of ADR-0120 decision 1. Its Consequences name two code slices:

- Slice 1, the hook program `hilclaw/budget_check.py`, landed as `4b7921d` (T-0406, PR #237).
- This task is **slice 2, the second settings entry**. Until it lands, no settings file names the budget program, so no spending call of a turn session is checked.

No open HQ holds this slice:
- HQ-0062 (items (lxi), (lxii)) and HQ-0061 (ADR-0146 items (lvi) to (lx)) are runtime acceptance items. They do not block code tested with a stub `claude`.
- HQ-0053 (coder start), HQ-0021 and HQ-0026 (`sim.run`, `board.run`) are not touched. The spending list is slice 1's constant, unchanged.

Open PR #186 touches only `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. There is no overlap.

Test rule: `hilclaw/turn_loop.py` and `hilclaw/budget_check.py` are modules of the layer-2 package, so rules ① to ④ of CLAUDE.md "테스트 규칙" apply (DRIVER §5, D12). This is the same reading as T-0403, T-0404 and T-0406, and their reviewers accepted it. The stub `claude` in `tests/test_turn_loop.py` stays a test fixture. Extending it is test code and gets no test of its own (rule ⑤).

D16: nothing here starts `claude`. Every test uses the stub `claude` that the tests write. The hooks that the stub runs are Python interpreters, not `claude`.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, the 2h30m limit, no force push) and §5 (lines 86-114). §5 covers:
  - the task format;
  - the naming convention: branch `claude/T-0407-<slug>`, PR title containing `T-0407`, trailer `Task: T-0407`, and `Task: T-0407` as the PR body's last line;
  - the D4 size cap;
  - code-task test rules ① to ⑤;
  - the language line in `Result`.
  Both sections are mandatory for every task (§6).
- `CLAUDE.md`, 상시 규칙: "코멘트 최소화", "세 층 모델", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ① to ⑤, "미결은 발명하지 않는다".
- `ARCHITECTURE/decisions/ADR-0147-od19-first-case-spend-path-check.md`. The binding parts:
  - decision 3 (lines 62-69);
  - decision 4 (lines 71-79), above all "The data root" and "Delivery";
  - Context row H11 (exact-match matcher list) and H12 (lines 30-36);
  - the Walk-through (lines 102-117);
  - Consequences slice 2 and the runtime acceptance items (lines 138-145).
  Skim Status (lines 3-15).
- `ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md` decision 4 (lines 61-68). ADR-0147 revises only "this one `PreToolUse` entry and nothing else". The rest of decision 4 holds: no `permissions`, no `env`, and a definition's own `settings.json` is refused.
- `hilclaw/turn_loop.py` (whole file, 425 lines). Read especially:
  - the docstring paragraphs "Decided by ADR-0146", "Choices of this module" (*The data root and the image…*, *The hook settings*), "What is raised" and "Runtime acceptance items";
  - `_data_root` (line 247), `_config_text` (line 254), `_settings_text` (line 268), `_write_settings` (line 285) and `run` (line 379).
- `hilclaw/budget_check.py` lines 1-70: the module docstring (its paragraph "This module is registered in no settings file here …"), `SPENDING_TOOLS`, `START`, `EXIT_PASS`, `EXIT_REFUSE` and `REFUSAL`. Skim the rest; it is not changed apart from that docstring paragraph.
- `hilclaw/caller_check.py` lines 1-63 (`START`, `TOOL_PREFIX`, `EVENT`).
- `tests/test_turn_loop.py`:
  - lines 1-135: the stub `claude`, which runs `["PreToolUse"][0]["hooks"][0]` only (lines 81-94), and `Stub.install`;
  - lines 180-235: the `data_root` and `parent` fixtures, `put` and `go`;
  - lines 974-1100: `NOT_PLAIN`, `EXACT_MATCH`, `expected_settings`, `settings_text`, `hook_input`, `test_settings_content`, `test_settings_written_in_every_turn`, and the two `test_hook_runs_as_written_*` tests.
- `tests/test_budget_check.py` lines 1-135: how fixture runs are built with `hilclaw.instance_file.write` and `hilclaw.run_state_file.replace` (`stated`, `instance_bytes`), and `payload`.
- The Claude Code hooks page https://code.claude.com/docs/en/hooks, sections "Matcher patterns" and "Hook handler fields". You may read it with `curl`. Running `claude` is not allowed.

## Acceptance Criteria

### `hilclaw/turn_loop.py` (ADR-0147 decision 4, "Delivery" and "The data root")
1. **The written file.** `.claude/settings.json` stays one JSON object with the one member `hooks`, and holds no `permissions` and no `env`. `hooks.PreToolUse` becomes a list of exactly two entries, in this order:
   - **Entry 1**: the caller-check entry of ADR-0146, byte-for-byte unchanged.
   - **Entry 2**: `{"matcher": M2, "hooks": [{"type": "command", "command": C, "args": A2, "timeout": T2, "onFailure": "block"}]}`, where:
     - `M2` is `"|".join(budget_check.SPENDING_TOOLS)`. That is an exact-match list by H11: test that every character is in the `EXACT_MATCH` set of the tests, and that the text holds no `^`.
     - `C` is the same `os.path.abspath(sys.executable)` as entry 1.
     - `A2` is `["-I", "-c", budget_check.START, checkout_boundary.PACKAGE_DIRECTORY, R]`. `R` is the **same real absolute data-root path** that `_config_text` writes into the server entry's `env` under `config.ENV_LOCAL_PATH`, which is the value `_data_root` returns.
     - `T2` is a timeout in seconds, well below 600. The suggestion is to reuse `HOOK_TIMEOUT_S` (30): one interpreter start and two small file reads take well under that. Record the value and the reason in `Result`.
   - The text is still built once per loop in `run`, after `_data_root` (so `_settings_text` takes the root), and written unchanged in every turn.
2. **No other change of behaviour.** These stay exactly as they are: the server entry, its `env`, the order of the checks in `_turn`, `_write_settings`, the refusal of a definition's own `settings.json` and of a `.claude` that is no plain directory, the command line, and the environment of the session.
3. **A data root the args cannot carry.** T-0405's reviewer raised a data root whose path holds a hook placeholder such as `${CLAUDE_PLUGIN_ROOT}`; it is Info only and undecided. Check the hooks page for whether placeholders or variables are substituted in exec-form `args`.
   - If the page says they are substituted, refuse such a root before the first turn with a `ValueError` and a fixed text, and add it to "What is raised".
   - If the page does not say, add no refusal and record the reading in `Result`.
   - Either way, do not refuse anything beyond what the page gives grounds for (CLAUDE.md "미결은 발명하지 않는다").
4. **Docstrings** of `hilclaw/turn_loop.py`. Change no other sentence unless it becomes false.
   - In the "Decided by ADR-0146" paragraph, "It holds one ``PreToolUse`` entry" becomes the first of the two entries.
   - A new "**Decided by ADR-0147** and only applied here" paragraph states decision 4 as applied:
     - the second entry, its exact-list matcher built from `hilclaw.budget_check.SPENDING_TOOLS`, and `hilclaw.budget_check.START`;
     - the data root as the last `args` element, the same real absolute path as the server entry's `env`;
     - no `env` in the settings.
   - "Choices of this module", *The hook settings*: name the second matcher's form and the timeout choice.
   - "Runtime acceptance items": add (ADR-0147 Consequences) (lxi) and (lxii), with a pointer to `hilclaw.budget_check`, which lists them. Also say that ADR-0146 (lvi) and (lviii) to (lx) apply to the second entry, and (lix) to its data-root argument.
5. **`hilclaw/budget_check.py`**: change only the module docstring paragraph "This module is registered in no settings file here: …". It becomes a short sentence saying that `hilclaw.turn_loop` writes the second `PreToolUse` entry that names this program, with the matcher built from `SPENDING_TOOLS` and the data root as its last argument. Nothing else in the file changes.

### Tests in `tests/test_turn_loop.py` (stub `claude` only, never a real one, D16)
6. **Stub.** Extend the stub so that, for each fixture hook input, it runs **every** `PreToolUse` entry whose matcher matches `tool_name`, and records each entry's index, exit status, stdout and stderr. Match the way the hooks page describes:
   - a matcher made only of the exact-match characters is a list of exact names separated by `|` or `,`;
   - any other matcher is an unanchored regular expression, read with `re.search`.
   Each handler is run as `[command, *args]` with no shell, `CLAUDE_PROJECT_DIR` set to the session directory and the hook input on stdin. Update the existing `test_hook_runs_as_written_*` tests to the new record shape. Their caller-check expectations stay the same: entry 1 only, since `state_write` and `verdicts_write` are not spending tools.
7. **Happy.**
   - `expected_settings` grows to the two-entry object of criterion 1. `test_settings_content` checks it with `R` equal to `os.path.realpath(data_root)`, and also equal to the server entry's `env` value in the same recorded call.
   - The file is the same in both turns of a two-turn loop.
   - Hook run: build a fixture run under `data_root` with `round_budget` 5 and `round` 0, using the package writers as `tests/test_budget_check.py` does. A main-session `mcp__hilclaw__correctness_check` input naming that run then matches both entries, and both exit `0` with empty stdout.
8. **Error, branch and negative cases.**
   - Run over: the same run with `run_status` `"over"`. Entry 1 exits `0` (a main-session call is admitted by the caller check), entry 2 exits `budget_check.EXIT_REFUSE`, and entry 2's stderr is exactly the `REFUSAL` line for that tool. The call counts as refused.
   - At budget: `round` 5 and `round_budget` 5 with no `run_status`. Entry 2 refuses.
   - Unreadable: a `run_id` with no `STATE.json` under `data_root`. Entry 2 refuses.
   - A sub-agent (with `put_agent`) calling `mcp__hilclaw__coder_run`, which is in its `tools`, on a run over budget: entry 1 passes and entry 2 refuses.
   - A non-spending tool (`mcp__hilclaw__state_read`) matches entry 1 only. Entry 2 is not run.
   - `coder_run` with no `run_id`: entry 2 refuses.
   - A `data_root` given as a relative path or through a symbolic link: `R` is still the real absolute path. Skip the link case where links cannot be made.
   - If criterion 3 adds a refusal, test it: the `ValueError` with its fixed text before any stub call.
   - The existing refusals still hold: a definition's own `settings.json`, a `.claude` that is no plain directory, and an empty `sys.executable` (`RuntimeError`).
9. Package coverage stays at least 80 % lines and 80 % functions (rule ①). Record both figures of the final head from the `Coverage gate (hilclaw)` job. The touched modules keep tests for every public name (rule ③). Rule ⑤: add no test of the stub, of a test helper, of a CI workflow or of a script.
10. Python, standard library only. Add no new dependency (A-13). Record the language line in `Result` (DRIVER §5). Tests pass on Linux (CI) and on Windows (the driver's clone). Path comparisons must not assume POSIX separators or case.

### Process checks
11. Before each commit and before the merge, run `python -m pytest`, `python -m ruff check .` and `python -m ruff format --check .` from the repository root, and make sure each exits 0. Record the pytest pass and skip counts on `origin/main` and on the final head. Install nothing.
12. Check the diff against `origin/main`:
    - `git diff origin/main --stat` lists only files from `touchesFiles`, plus this task file's `Result`;
    - `git diff origin/main -- .claude .github orchestration ARCHITECTURE` is empty;
    - `git ls-files --eol` shows `i/lf` for the touched files.
    Record the non-test diff line count (cap: 300 LOC, 5 files). If it is exceeded, propose a split in `Follow-ups` and finish only the current scope (DRIVER §5).
13. Open a Draft PR and run the reviewer cycle with a fresh-context `dev-reviewer` running dev-code-review, for at most 7 rounds. Ask the reviewer explicitly to:
    - (a) confirm the data-root argument is the same real absolute path as the server entry's `env`, and cannot differ in any branch of `run`;
    - (b) confirm entry 1 is unchanged and the file holds no `permissions` and no `env`;
    - (c) confirm the second matcher is an exact list by H11 and names exactly `SPENDING_TOOLS`;
    - (d) check the stub's matcher emulation against the hooks page;
    - (e) re-check the criterion 3 reading and the timeout choice.
    A finding that starts with `SECURITY` is BLOCKED.
    After the review, get CI green on the final head with `gh pr checks <PR> --watch`, and record the check names and the run URL. Then squash-merge with `gh pr merge --squash --body`, using the PR body whose last line is `Task: T-0407`, and delete the branch.

## Out of Scope

- Any change to the behaviour of `hilclaw/budget_check.py` or `hilclaw/caller_check.py`, and any edit of `hilclaw/turn_definition.py`, `hilclaw/turn_permissions.py`, `hilclaw/turn_start.py`, `hilclaw/further_turn.py`, `orchestration/`, `.claude/`, `.github/`, `ARCHITECTURE/` or `pyproject.toml`.
- The files of open PR #186.
- `sim.run` or `board.run` in the spending list (HQ-0021, HQ-0026); the check of a request's `run_id` against the session's run; other budget axes, gates and caps; PostToolUse journaling; the Stop hook (ADR-0147 Boundaries).
- Refusing a definition-brought `.claude/settings.local.json`. This is the T-0404 follow-up already in PLAN 보류.
- Editing the "Less exact, not edited" records that ADR-0147 lists, and the ADR-0147 decision 4 citation nit in PLAN 보류. Both are document-mode work.
- The `caller_check` `NaN`/`Infinity` input finding (T-0406 reviewer Info). The planner weighs it separately.
- Starting `claude`, and checking ADR-0147 items (lxi) and (lxii) (HQ-0062) or ADR-0146 items (lvi) to (lx) (HQ-0061).

## Follow-ups

- (planner) After this lands, both code slices of ADR-0147 are done. The rest of PLAN P2-4 (gate checks, PostToolUse journaling, the Stop hook; the remainder of OD-18 and OD-19) is for later planning.

## Result
