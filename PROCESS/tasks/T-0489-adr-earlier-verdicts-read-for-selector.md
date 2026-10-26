---
id: T-0489
title: Record how the technique-selector of a first-case run reads the verdicts and measurements of earlier rounds (FR-17 "앞선 판정을 입력으로") as one new ADR (part of OD-23 and OD-30), and land the read tool and the selector's use of it, with tests
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-11, FR-17, NFR-2, OD-23, OD-30, OD-18, S1, S8, "PLAN P2-6"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0174-od23-first-case-earlier-verdicts-read.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/verdicts_read_tool.py
  - hilclaw/tools.py
  - hilclaw/verdicts_file.py
  - orchestration/agents/technique-selector.md
  - hilclaw/turn_definition.py
  - tests/test_verdicts_read_tool.py
  - tests/test_turn_definition.py
  - tests/test_turn_permissions.py
  - tests/test_caller_check.py
  - tests/test_tools.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_mcp_front.py
  - tests/test___main__.py
  - tests/test_default_registry_schemas.py
estimatedSize: {loc: 400, files: 8}   # non-test: ADR ~160, tool module ~170, registry ~12, selector definition ~30, docstrings ~15, registers ~10. Tests are outside the cap; the ADR's lines count (DRIVER §5, D4/D20). The module name is a suggestion. `hilclaw/verdicts_file.py` is touched only if the record makes a public read of the file there (as `hilclaw/hypotheses_tool.py` `read` is for `hypotheses.json`).
hq: []
---
## Why

PLAN P2-6 (hypothesis records and verdicts) is open. Its first-case pieces exist:
- the selector writes the round's hypothesis record (`hypotheses.write`, ADR-0132);
- the evaluator writes the verdicts (`verdicts.write`, ADR-0128, ADR-0131, ADR-0140);
- the round >= 1 steps reach the verdicts delegation (ADR-0172);
- the selector reads the stored cases (`cases.lookup`, ADR-0173).

One piece is still missing. FR-17 ends with "다음 라운드 결정은 앞선 판정을 입력으로 삼는다", and it asks the system to learn from earlier verdicts when it forms new hypotheses. The technique-selector has no means to read an earlier round's `eval/verdicts.json`:
- Its `tools` hold `hypotheses_read` and `checks_read`, which give earlier hypothesis records and check standing, but no verdicts.
- It is given no place to `Read` from (ADR-0123 decision 2).
- ADR-0132 Consequences, "The cost, plainly", says: "Until a verdicts read exists the selector does not take earlier verdicts as input by a typed tool, so no means is set for FR-17's '앞선 판정을 입력으로'".
- ADR-0132 Boundaries leave open "the reads of earlier verdicts and measurements a selection needs: a verdicts read, a read of `sim.run` and `board.run` results once they are registered (ADR-0142 decision 7), profiles (ADR-0130); `eval.json` (OD-20)".
- The OD-23 register row lists under `**잔여**`: "첫 사례에서는 선택 쪽이 앞선 판정·측정에 닿는 도구".

T-0488's Result names this as the one input P2-6 still lacks on the selection side. P2-5 (5 rounds, coversReq FR-17) is the next item in the P2 order, and its later rounds are the first that have earlier verdicts to take as input. This is checklist work (P2-6), so the D18 rule for work outside the checklist does not apply.

These are design parts of OD-23 and OD-30 that the driver may close (DRIVER §9, D6). By D20 ① and ③, the record, the tool and the selector's use of it go in one task: code mode, with the ADR file in the PR. The selector's definition depends on the tool's name and result, which this record decides, so it is not split into a second task made in advance (D20 ④).

No owner-only part is known. `PROCESS/STATE.json` at `c3c89d1f` has no unresolved HQ, no PR is open, and no item of `PROCESS/RuntimeAcceptance.md` has the state `실패`.

**Stop conditions. The executor checks these and does not assume them away:**
- If the only defensible design needs any of the following, return BLOCKED with a Korean question for the owner (DRIVER §8: the issue, options (a)/(b)/(c), what stays blocked and what does not):
  - **the models of the orchestration's agents or how their tokens are counted** (#5 A-8);
  - **a ranking, a "best", or a "better than" among attempts beyond what ADR-0140 already gives** (#5 A-4, OD-1, OD-7);
  - **C-6, OD-25 or OD-3**.
- **Profiles**: `profiler.collect` is not provided on `cpu_standin` (ADR-0130, owner decision 2026-10-20). The record does not invent a profile read. It names profiles as open.
- **`eval.json`** is OD-20. The record does not define it or read it.
- If the design needs a new data-plane file, member, value or version, that is a data-plane schema change (CLAUDE.md A-13). Examples: a new member of `verdicts.json`, `hypotheses.json` or `STATE.json`; a file that summarizes earlier rounds. If no means that avoids it can be argued on the record's own ground, stop and return BLOCKED with the owner question. A new failure kind of the tool layer is not a data-plane change (ADR-0132 decision 4 says the same of its kinds).
- If an open PR touches the same rows or sections of `ARCHITECTURE/`, or any file in `touchesFiles`, stop and return BLOCKED (CLAUDE.md 세션 진입 점검).

## Required Reading

Line numbers are those of `main` at `c3c89d1f`. Where the text and a line number disagree, the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md**:
  - **§3-5** (line 73): the executor procedure, the resume rule and the time limit;
  - **§5** (lines 87-116): the task format, naming, trailers, the size cap (D4/D20), the test rules (D12) and the pinning-list rule (D21);
  - **§8** (lines 144-151): the HQ form; runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`, not to an HQ;
  - **§9** (lines 153-160): which ODs the driver may close, the owner notice on #5 and the 7-day window.
- CLAUDE.md, the whole file. These sections matter most:
  - "미결은 발명하지 않는다";
  - "문서 커버리지 재검사";
  - "세션 진입 점검";
  - "개발 드라이버와 런타임의 구분";
  - "도구 계층 언어 정책";
  - "테스트 규칙";
  - "브랜치·merge 절차";
  - "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- Before you edit `ARCHITECTURE/`, run `gh pr list`, read issues #4, #5, #7 and #8, and read the unresolved `humanQuestions` in `PROCESS/STATE.json` (CLAUDE.md 세션 진입 점검).
- **The requirement**: `ARCHITECTURE/Requirements.md` FR-17 (line 35) and FR-11 (line 29).
- **What the record answers**:
  - `ARCHITECTURE/decisions/ADR-0132-od23-first-case-selection.md`: decision 3 (its tools), decision 7, Consequences "The cost, plainly" (line 138) and Boundaries (from line 140, the fourth bullet).
  - `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: decisions 1 to 4 and 6 (lines 25-85), the file, its frame, one verdict and round 0.
  - `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: decisions 3 and 6 (lines 43-75), the evaluator's tools and what writes the evaluation files.
  - `ARCHITECTURE/decisions/ADR-0140-od16-first-case-attempt-comparison.md`: decisions 2 to 6 (lines 30-78), the `comparison` entries and `timings.compare`, which stays the evaluator's.
  - `ARCHITECTURE/decisions/ADR-0142-od23-first-case-round-zero-after-coder-call.md` decision 7, and `ARCHITECTURE/decisions/ADR-0130-od18-cpu-standin-profiler-collect.md` (profiles).
- **The model for a read tool given to the selector, and for form**: `ARCHITECTURE/decisions/ADR-0173-od30-first-case-case-lookup-read-tool.md`, the whole file (it is the most recent record of the same shape), and `ARCHITECTURE/decisions/ADR-0129-od23-round-hypotheses-read.md` decisions 2 to 5 (lines 33-66; a typed per-round read tool). Format: ADR-0001 "Record format". Use the status marking, the Context rows, the Walk-through table, the "less exact, not edited" list and the runtime acceptance items as ADR-0173 does.
- Also read:
  - ADR-0010 decisions 3 and 4 (the MCP front; a name without `_`);
  - ADR-0015 decisions 2 to 4 (request members, `invalid_request`, no data root in a request);
  - ADR-0019 decisions 2 and 3 (the `run_file_*` kinds);
  - ADR-0123 decision 2 (no place given to a turn's agents);
  - ADR-0139 decisions 3 and 4 and ADR-0146 decisions 2, 3 and 6 (the derived pre-approval and the caller check from an agent's `tools`).
- **Where the record is entered.** Follow each file's own rules, and do not copy the wording of earlier task files:
  - `ARCHITECTURE/Requirements.md`:
    - the "행 형식" paragraph (line 84);
    - the OD-23 row (line 114) and the OD-30 row (line 121);
    - the OD-18 row (line 109), only where the record answers part of it (its `**잔여**` names how a turn session reaches run files other than `hypotheses.json` and the check lines, "OD-23과 함께").
  - `ARCHITECTURE/OpenDecisionProposals.md`:
    - the "기록 규칙" in its header (line 8);
    - § OD-23 (from line 431);
    - § OD-30 (from line 518);
    - § OD-18 (from line 295), if touched.
  - `ARCHITECTURE/StandardScenarios.md`: its check rules (from line 13) and the first paragraph of § 검사 결과 (line 168). S1 and S8 are the likely scenarios.
- **Code (observation, then the slice)**:
  - `hilclaw/hypotheses_tool.py`, the whole file (201 lines): the closest model, a per-round read with its own `read` that `verdicts.write` reuses;
  - `hilclaw/verdicts_file.py`, the whole file: `parse`, `final_name` and the file's place;
  - `hilclaw/verdicts_tool.py`: the module docstring and `_reported`, for the kinds `verdicts.write` already names for this file (for example `verdicts_exist`);
  - `hilclaw/cases_tool.py`, the whole file: the most recent registry read tool;
  - `hilclaw/tools.py` `default_registry` and its docstring (from line 182);
  - `hilclaw/turn_permissions.py`, lines 1-125;
  - `hilclaw/turn_definition.py`: the module docstring.
- **Definition**: `orchestration/agents/technique-selector.md`, the whole file (117 lines).
- **Tests**:
  - `tests/test_hypotheses_tool.py` and `tests/test_cases_tool.py` (models for the new test file);
  - `tests/test_turn_definition.py`: `TECHNIQUE_SELECTOR_TOOLS` (line 29) and `test_the_technique_selector_body` (line 846) with the selector tests around it;
  - `tests/test_turn_permissions.py` `test_holder_lists_the_real_definition` (line 407);
  - `tests/test_caller_check.py`: the selector tests from line 313 and from line 533;
  - T-0488's `## Result` in `PROCESS/tasks/T-0488-adr-case-lookup-read-tool-and-selector.md`, for the registry pinning assertions that the last new registry tool changed.

## Acceptance Criteria

1. **The ADR.** Write a new `ARCHITECTURE/decisions/ADR-0174-<slug>.md`. If 0174 is taken, use the next free number; check `ARCHITECTURE/decisions/` and the remote branches. The file name in `touchesFiles` is a suggestion. Scope: the runs of ADR-0120 decision 1, the selection of a round >= 1 (ADR-0132 decision 1).
   - It decides at least:
     - **(a) The verdicts read**: its name, with no `_` (ADR-0010 decision 4); its request (`run_id` and a round, or `run_id` alone for all earlier rounds; argue the choice; ADR-0015 decision 4); its result, the stored document as it is or a stated subset; which rounds it admits, given round 0 (ADR-0071 decision 6) and the round being selected.
     - **(b) Its checks and kinds, in order**: reuse existing kinds with their meanings where they fit (`invalid_request`, `no_data_root`, the `run_file_*` kinds, and the kinds `verdicts.write` already names for this file). Name any new kind and search `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/` for it first, as ADR-0132 decision 4 did. Say whether a missing file is a kind or an empty result, given ADR-0071's rule that an absence is no value (ADR-0072 Alternatives row 3 cites it). Say whether the call is journaled and whether it costs a limited resource.
     - **(c) Measurements**: whether the selector needs a read of `sim.run` and `board.run` results beyond what the verdicts' `comparison` entries (ADR-0140 decision 5) and `checks.read` already give it. If it does, decide the means (a new read, or an existing tool given to it, with ADR-0140 decision 6's reason why `timings.compare` is the evaluator's weighed). If it does not, say why and leave it named. Profiles stay open (ADR-0130).
     - **(d) Who holds the tool(s)**: the technique-selector's `tools` list, and whether any other agent or `ROUND_MANAGER_TOOLS` lists them, with the caller check's consequence (ADR-0146 decisions 2, 3 and 6).
     - **(e) The selector's use**: when in its work it reads earlier verdicts (before the record, since the record is written once, ADR-0059 decision 1), what it does on a failure kind (whether a selection goes on), and the fixed rules the definition gains. Keep the rest as the selector's judgement, and keep FR-15/FR-18's "hint, not target" reading for anything an earlier verdict reports.
   - Mark every sentence as owner, cited, or the record's own.
   - **Consequences**:
     - The A-13 reading, with no data-plane change.
     - The code slices in order. This task lands all of them unless the size cap forces a split (criterion 3).
     - The sentences of earlier records and docstrings that become less exact, without editing them. At least: ADR-0132 decision 3's exact list, Consequences "The cost, plainly" ("Until a verdicts read exists ...") and the Boundaries bullet on reads of earlier verdicts and measurements; ADR-0173 decision 5 / Consequences where they list the selector's tools.
     - Runtime acceptance items for facts only a live session can show. Examples: the selector's sub-agent gets the new tool through its derived pre-approval and calls it without a prompt; the largest result a first-case run can give reaches the selector whole under Claude Code's MCP output limit. Number them after the last item in use: (lxxxviii) is ADR-0173's, so the next is (lxxxix). Check the records and `PROCESS/RuntimeAcceptance.md` for a higher roman numeral first. State that these items go to `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22).
   - **Boundaries** keep open what the record does not answer:
     - profiles (ADR-0130) and `eval.json` (OD-20);
     - `decision/decision.md` and its writer;
     - reads for runs outside ADR-0120 decision 1, and for N > 1;
     - a ranking or "best" across rounds (#5 A-4, OD-7) and `best.json`;
     - hooks beyond the caller check (P2-4);
     - the owner-only items.
2. **Register entries** follow the recording rules written in those files, not the wording of earlier task files:
   - Requirements.md: follow the "행 형식" paragraph (line 84) in the OD-23 row, in the OD-30 row only if the record answers a part of OD-30, and in the OD-18 row only where the record answers part of it. One link per new ADR after `**확정분**:`, the `**잔여**:` rewritten in place.
   - OpenDecisionProposals.md: follow the header's "기록 규칙" (line 8) in § OD-23, and in § OD-30 and § OD-18 if touched. Rewrite the status of each sub-question the record answers in place.
   - StandardScenarios.md: re-check coverage under its check rules (CLAUDE.md "문서 커버리지 재검사"), S1 and S8 first. Update § 검사 결과 as its first paragraph says. Add a history entry only if a verdict changes.
3. **Code: the slices the record names**, in one PR unless the size cap forces a split:
   - **The tool(s)**: a new module of `hilclaw/` (name per the record; `hilclaw/verdicts_read_tool.py` is a suggestion) built on `hilclaw.verdicts_file`, not a second parser. If the record puts a public read of the file in `hilclaw/verdicts_file.py` so that `verdicts.write` and the new tool name the same failures alike (as `hypotheses_tool.read` does), do that without changing `verdicts.write`'s behaviour. Add the tool to `default_registry` in `hilclaw/tools.py` in the source and in no other way (#5 A-12 point 3), and update its docstring. No new external dependency.
   - **The selector's use**, in `orchestration/agents/technique-selector.md`:
     - the new MCP name(s) in `tools`;
     - a "What you are given" line for each;
     - the fixed rules of decision (e);
     - the weighing in "The choice of techniques" and any report line, only where the record changes them.
     Each changed sentence cites the new ADR's decision. `ROUND_MANAGER_TOOLS` and the other agent files change only if decision (d) says so.
   - **Docstrings**: the `hilclaw/turn_definition.py` docstring and the `hilclaw/verdicts_file.py` / `hilclaw/verdicts_tool.py` docstrings, only where the slice makes a sentence false.
   - If the ADR and the slices exceed 600 lines or 10 files (tests excluded), land the ADR with the verdicts read and name the rest in `## Follow-ups` (DRIVER §5). In that case update `touchesFiles` in the PR body and in `## Result`.

   Use no wording in a definition that the records do not support. No multi-line comments in code.
4. **Tests** (code mode; D12; test files are outside the size cap). Use fixture files under `tmp_path` and the real definitions copied there only. Never use a real `claude`, `docker` or `clang` (D16).
   - **The new test file** for each new tool module, covering every public function:
     - happy: a stored verdicts file of an earlier round returned as the record says; for a request over several rounds, the rounds in the order the record says;
     - branch: a round with no verdicts file, as decision (b) says; round 0 and the round being selected, as decision (a) says; a document with unknown top-level members, if the result returns the document as stored;
     - error and negative: a missing or extra request member, a bad `run_id`, a bad round (`invalid_request`); no data root; a place that is no regular file, an unreadable file, bytes the parser refuses, another `schema_version`, a document whose `run_id` or `round` does not match the request; every other kind the record names, in its order.
   - If `hilclaw/verdicts_file.py` gains a public read, it gets tests in `tests/test_verdicts_file.py`, and `tests/test_verdicts_tool.py` still passes unchanged except for D21 lists.
   - **The selector, in `tests/test_turn_definition.py`**:
     - `TECHNIQUE_SELECTOR_TOOLS` gains the new name(s);
     - the body states the new fixed rules with their citations;
     - negative: the selector still requests no check, measurement, spec or coder call, and does not call `verdicts_write` or `timings_compare` unless decision (c)/(d) gives it one.
   - **`tests/test_caller_check.py`**: the real definition passes the new tool(s) for the selector and refuses them for the Round-Manager and for every other agent that decision (d) does not name.
   - **`tests/test_turn_permissions.py`**: the selector's tuple in `test_holder_lists_the_real_definition` gains the name(s).
   - **Pinning assertions you may touch** (DRIVER §5 D21; list each in the PR body). Each is touched only by the new tool's name, and only if its list changes:
     - `TECHNIQUE_SELECTOR_TOOLS` in `tests/test_turn_definition.py`;
     - the selector's tuple in `tests/test_turn_permissions.py` `test_holder_lists_the_real_definition`, and `FIXED` there if the derived list is pinned;
     - `tests/test_tools.py` `DEFAULT_SET`;
     - `tests/test_blob_tools.py` `test_the_default_registry_holds_the_definitions` and `test_the_mcp_front_lists_the_blob_tools_among_the_fixed_set` (the unpacking of the first names and the slice after it);
     - `tests/test_check_definition.py`: the registry name lists, the MCP name list, the joined names string and any index of a listed tool that moves;
     - `tests/test_mcp_front.py` `FIXED_NAMES`, the `held` map and the listed-name lists;
     - `tests/test___main__.py` `FIXED_NAMES`;
     - `tests/test_default_registry_schemas.py` `ACCEPTED` (one accepted request of each new tool);
     - the selector's parametrized lists in `tests/test_caller_check.py` (`test_the_real_technique_selector_holds_its_reads`, `test_the_real_technique_selector_is_refused_what_it_does_not_hold`).
   - **An assertion that pins old prompt text** changes only where the slice replaces that text. State each change and its reason in the PR body. Every other existing assertion stays as it is.
   - Run `python -m pytest`, `ruff check .` and `ruff format --check .`. Coverage of `hilclaw/` stays at line >= 80% and function >= 80%, and the test-presence check holds. CI must be green before the squash-merge.
5. **Landing.**
   - The commit body names the language and the reason in one line.
   - The PR body ends with `Task: T-0489`.
   - After landing, post the owner notice of DRIVER §9 on issue #5 in English: what the ADR decides, the landed commit and the 7-day objection window. Its last line is `— posted by driver`. Record the URL in `## Result`.
6. **Result.** In `## Result`, write:
   - the ADR and what it decides, in a few lines;
   - each tool's name, request, result and kinds;
   - the selector sentences rewritten or added, quoted briefly, each with its decision;
   - the test assertions changed, the D21 pinning lists among them;
   - the record sentences made less exact but not edited;
   - the runtime acceptance items, for the driver to add to `PROCESS/RuntimeAcceptance.md` (not as an HQ);
   - in the executor's reading, whether P2-1, P2-2, P2-3, P2-4, P2-6 and P2-7 still hold any work before P2-5, and what it is (for the planner).

## Out of Scope

- Profiles and a `profiler.collect` for `cpu_standin` (ADR-0130); `eval.json` (OD-20); `decision/decision.md`; `best.json`; `technique_stats.json`; any ranking across rounds.
- Any new data-plane file, member, value or version (a BLOCKED reason, CLAUDE.md A-13); any change to the validators of `verdicts.json`, `hypotheses.json` or `STATE.json`; any change to `verdicts.write`'s behaviour.
- `orchestration/round-manager.md`, `orchestration/agents/coder-driver.md`, `orchestration/agents/evaluator.md` and `orchestration/agents/experiment-runner.md`, unless decision (d) gives a tool to one of them.
- The S6 metric and calculation tool (P2-8); hooks beyond the caller check (P2-4); the first end-to-end run (P2-5).
- Editing any earlier ADR, README, UsageCases, `catalog/`, `.claude/settings.json` or `.claude/settings.local.json`; any new external dependency.
- Starting `claude`, Docker or `clang` on this machine (D16).

## Follow-ups

- (planner) A measurement read or other slice, if the size cap split it off (criterion 3).

## Result
