---
id: T-0354
title: Add the evaluator sub-agent definition orchestration/agents/evaluator.md of ADR-0128 decision 7, with a test that LAYOUT copies it (ADR-0128 Consequences slice 2; PLAN P2-3)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-9, FR-17, OD-23, OD-16, S0, S1]
dependsOn: [T-0352, T-0353]
touchesFiles:
  - orchestration/agents/evaluator.md
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
estimatedSize: {loc: 120, files: 3}
hq: []
---
## Why

PLAN P2-3 (the evaluator) is a checklist item, so the D18 rule for non-checklist work does not apply. It comes before P2-5 in the P2 order. ADR-0128 (T-0352) decided that the evaluation work of a turn of a run of ADR-0120 decision 1 is held by one sub-agent, `evaluator`. Its definition is `orchestration/agents/evaluator.md`, which `hilclaw.turn_definition.LAYOUT` copies into the session directory as `.claude/agents/evaluator.md`. ADR-0128 Consequences lists this definition as slice 2, "Now", to be written "with the tools that exist at that time". Slice 1, the tool `verdicts.write`, landed in T-0353 (PR #202), so every tool of decision 3 now exists. Without the definition a turn session has no evaluator to delegate to.

Nothing here needs an owner answer. ADR-0128 says the definition names no model, so #5 A-8 and HQ-0041 (the model) are not crossed. The evaluator has no shell, so HQ-0040 (the coder-driver's Bash) is not crossed either. The delegation steps in `orchestration/round-manager.md` are slice 4 and wait on HQ-0040 and HQ-0041, so they are out of scope here. PR #186 (T-0324, HQ-0032) touches `hilclaw/start_instance.py` and three other test files, none of which are in `touchesFiles`. HQ-0045 lists the runtime acceptance items (xviii) to (xx) of this definition. It does not block this task, and this task does not close it.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: Status (the "Answers" bullet), **Decision 1 to 7 in full**, the Walk-through, Consequences slices 2 to 4 and runtime acceptance items (xviii) to (xx), and Boundaries.
- `ARCHITECTURE/decisions/ADR-0118-*.md` decision 5 (where the definition lives, the naming rule) and decision 6 (the server and the open question of how sub-agents reach tools).
- `ARCHITECTURE/decisions/ADR-0010-*.md` decision 4 (MCP tool names) and F3 (per-agent allowlists).
- `ARCHITECTURE/decisions/ADR-0123-*.md` decisions 2 and 4 (the run id, no place), and `ARCHITECTURE/decisions/ADR-0015-*.md` decision 4 (the `run_id` and `execution` members).
- `orchestration/round-manager.md`, the whole file. It shows the style of the runtime's definition: citations in parentheses, one-line reports, and a section that says what is not yet defined.
- `hilclaw/turn_definition.py`, the whole file, and `tests/test_turn_definition.py`, lines 1 to 110 and the fixtures.
- `hilclaw/check_definition.py` `input_schema` (members of a `correctness.check` request), `hilclaw/verdicts_tool.py` (module docstring and `_DESCRIPTION`), `hilclaw/run_file_tools.py` (the descriptions of `state.read`, `instance.read` and `run.fresh`), `hilclaw/mcp_front.py` (`SERVER_NAME`, `mcp_name`) and `hilclaw/tools.py` `default_registry`.
- `.claude/agents/dev-reviewer.md`, lines 1 to 6, only as an example of a Claude Code sub-agent frontmatter (`name`, `description`, `tools`). Unlike that file, the evaluator has no `model` key.

## Acceptance Criteria

1. **New file `orchestration/agents/evaluator.md`**, a Claude Code sub-agent definition in English, as ADR-0128 decisions 2 to 7 state it:
   - Frontmatter holds `name: evaluator`, a `description` that says the Round-Manager delegates the evaluation work of a turn to it (checks of an attempt at a point, and the verdicts of a round), and `tools`. `tools` lists exactly `Read`, `Grep`, `Glob`, `mcp__hilclaw__correctness_check`, `mcp__hilclaw__state_read`, `mcp__hilclaw__instance_read`, `mcp__hilclaw__run_fresh` and `mcp__hilclaw__verdicts_write` (decision 3, with the decision-6 tool that now exists). There is no `model` key (decision 7, Boundaries) and no other key that grants tools or permissions. In particular the list has no `Write`, `Edit`, `NotebookEdit`, `Bash` or agent-delegating tool, and none of `sim_run`, `board_run`, `state_write`, `run_commit`, `blob_push` or `blob_fetch`.
   - The body carries the fixed rules of decision 7: every tool request carries the run id given in the delegation, and only that one. A check is requested only for the tuple (`run_id`, `round`, `candidate`, `attempt`) and point (`sim` or `board`) it was given, with `execution` 1 unless the delegation names another value. Nothing is written by any means but `mcp__hilclaw__verdicts_write`. No measurement is requested. The report follows decision 5: one final text message, with one line per tool request naming the tool, the tuple or round, and the result value or failure kind, plus, for a verdicts delegation, one line per hypothesis `id` with its `verdict`.
   - It states what it is given (decision 4): the run id and the work, no place, no paths and no hashes. It also says that its record rests on what typed tools return, not on another agent's account, and that it copies no computation into its own text (decision 2).
   - A standing is not reported while no standing tool exists (Walk-through, "once the standing tool exists"; Consequences slice 3). The definition must not ask the evaluator to work out a standing from the log by itself.
   - The verdicts work: for a round ≥ 1, the evaluator composes the whole record and calls `verdicts.write`. The record has `check` entries only, every verdict is `inconclusive`, and no `comparison` entry appears (decision 6). A refused record is corrected and sent again, and `verdicts_exist` replaces nothing. The record must rest on typed tools (decision 4), but the tool that reads a round's `hypotheses.json` is slice 3 and does not exist yet. The executor writes this part so that it asks the evaluator for nothing no listed tool gives. The expected reading follows the precedent of "The round steps" in `orchestration/round-manager.md`: the part names what is not yet given, and on a verdicts delegation the evaluator reports that in one line and writes nothing. If the executor or the reviewer finds that the definition cannot be written without a choice ADR-0128 leaves open, the executor stops and returns BLOCKED (requirement unclear, CLAUDE.md A-13). It must not invent the choice.
   - Each rule cites its source in parentheses, in the manner of `round-manager.md`. Nothing is added beyond ADR-0128 and the records it cites, except the wording of the description and of the reports.
   - The file name and every name below `orchestration/` keep the naming rule of ADR-0118 decision 5 (no `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md` or `.claude`).
2. **`hilclaw/turn_definition.py`, docstring only**: the "Not done here" sentence ("no roster and no agent definitions (OD-23)") now says that `orchestration/agents/` holds the evaluator's definition (ADR-0128 decision 7) and that the rest of the roster stays open (OD-23). The runtime acceptance item list may name ADR-0128 item (xviii). `LAYOUT`, `put` and every other behaviour stay unchanged.
3. **Tests in `tests/test_turn_definition.py`**. No `claude` is started, stub or real. The tests pass on Linux CI and on the local Windows machine.
   - Update `test_the_repository_definition_by_default`: `put(session)` with the default source now gives `CLAUDE.md` and `.claude/agents/evaluator.md`, each byte-equal to its source. This is the test that `LAYOUT` copies the definition (slice 2).
   - Replace `test_the_repository_definition_holds_only_the_prompt` with a test that `SOURCE` holds exactly `round-manager.md` and `agents/`, and that `agents/` holds exactly `evaluator.md`.
   - Add a test that reads the frontmatter of `SOURCE / "agents" / "evaluator.md"`, with no new dependency (parse the `---` block by hand). It checks that `name` is `evaluator`, that there is no `model` key, and that the `tools` set equals the list of criterion 1. It also checks that every `mcp__hilclaw__` entry is `mcp__<mcp_front.SERVER_NAME>__<mcp_front.mcp_name(n)>` for some `n` registered by `tools.default_registry()`, so a renamed tool fails the test.
   - Negative: the frontmatter test fails cleanly (assertion, not a crash) if the file has no frontmatter. Use `pytest.raises` on the test's own small parsing helper with a bad text, or an equivalent check. Existing negative tests of `put` stay as they are.
4. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more; ② the tests include happy, branch and negative cases; ③ `put` is the one public function of the touched module and is still tested; ④ no new module is added to `hilclaw/`; ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
5. **No data-plane change**, and no change to any tool, registry entry, kind or validator. If the work turns out to need one, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
6. **Language**: the definition is Markdown (layer 1), and the test changes are Python. Record this and one reason in the commit body and in `## Result`.
7. Code mode (A-13): a Draft PR whose title contains `T-0354`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0354`, and the branch `claude/T-0354-evaluator-agent-definition` deleted.
8. No `claude` process is started, and nothing runtime-only is required (D16). Runtime acceptance items (xviii) to (xx) of ADR-0128 (HQ-0045) are not closed by this task.

## Out of Scope

- Any change to `orchestration/round-manager.md`, including the delegation steps of slice 4, which wait on HQ-0040 and HQ-0041.
- The read, standing and comparison tools of slice 3, and lifting `comparison_not_given`.
- Settings, hooks or permissions of a turn session (`orchestration/settings.json`; PLAN P2-4), and the other agents of the roster.
- Any edit of `ARCHITECTURE/` documents, including the "Less exact, not edited" list of ADR-0128 (D18 hold class).
- `hilclaw/start_instance.py` and the other files of PR #186.

## Follow-ups

- Next slice for the planner (ADR-0128 Consequences slice 3): each of the read of a round's `hypotheses.json`, the read of an attempt's journaled results, the standing tool and the comparison tool needs its own record before code. Planning the first of these records belongs to P2-3 and P2-6.

## Result

- Outcome: DONE. PR #203 (https://github.com/myungjoo/HIL-Claw/pull/203), squash-merged as 71a57d5ef273943821cab145714363c38f1da7ac; branch claude/T-0354-evaluator-agent-definition deleted.
- Changes: new orchestration/agents/evaluator.md. Its frontmatter has name `evaluator`, a description of the delegation, and `tools` exactly Read, Grep, Glob, mcp__hilclaw__correctness_check, state_read, instance_read, run_fresh and verdicts_write. It has no `model` key. The body states the fixed rules of ADR-0128 decision 7, what the evaluator is given (decision 4), that it copies no computation (decision 2), that it reports no standing while no standing tool exists, and the report form of decision 5. Every rule cites its source.
- Verdicts: no tool reads a round's hypotheses.json or an attempt's journaled results yet (slice 3). On a verdicts delegation the evaluator therefore reports in one line that the round's verdicts cannot yet be written, does not call verdicts_write, and writes nothing. This follows the precedent of "The round steps" in round-manager.md. The record rules of decision 6 are written down for when that work is given. Nothing ADR-0128 leaves open was decided.
- hilclaw/turn_definition.py: docstring only (roster sentence; runtime acceptance item (xviii) named). LAYOUT and put are unchanged.
- tests/test_turn_definition.py: put() copies CLAUDE.md and .claude/agents/evaluator.md byte for byte; SOURCE holds exactly round-manager.md and agents/evaluator.md; frontmatter test checks name, no model key, the exact tool set, and that every mcp__hilclaw__ entry matches a default_registry tool.
- Language: Markdown for the definition (layer 1, read by Claude Code); Python for the tests (the package's test language).
- Tests: local ruff check, ruff format --check and full pytest (24103 passed, 724 skipped); CI green (Python 3.11/3.14, coverage, C, shellcheck, test presence).
- Review: 3 rounds (round 1 Request changes; rounds 2 and 3 Approve, the round-2 nit addressed).
- No data-plane, tool or registry change. No claude process started. ADR-0128 runtime acceptance items (xviii) to (xx) (HQ-0045) are not closed.
- Follow-ups: when slice 3 enables the verdicts work, narrow "can be corrected and sent again" to the refusals caused by the record itself (invalid_request, verdicts_mismatch, comparison_not_given) (reviewer note). The slice-3 records (hypotheses read, journaled-results read, standing tool, comparison tool) are as listed in the task's Follow-ups.
