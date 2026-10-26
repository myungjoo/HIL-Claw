---
id: T-0488
title: Record the case-lookup read tool the technique-selector uses (name, request, result, kinds, how the lookup's reports are carried, whether a selection goes on after one) as one new ADR (part of OD-30 and OD-23), and land the tool and the selector's use of it (ADR-0132 slice 4), with tests
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-11, FR-15, FR-17, FR-18, NFR-2, OD-30, OD-23, OD-18, S6, S11, "PLAN P2-7", "PLAN P2-6"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0173-od30-first-case-case-lookup-read-tool.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/cases_tool.py
  - hilclaw/tools.py
  - hilclaw/case_lookup.py
  - orchestration/agents/technique-selector.md
  - hilclaw/turn_definition.py
  - tests/test_cases_tool.py
  - tests/test_turn_definition.py
  - tests/test_turn_permissions.py
  - tests/test_caller_check.py
  - tests/test_tools.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_mcp_front.py
  - tests/test___main__.py
  - tests/test_default_registry_schemas.py
estimatedSize: {loc: 390, files: 8}   # non-test: ADR ~170, tool module ~160, registry ~12, selector definition ~25, docstrings ~10, registers ~10. Tests are outside the cap; the ADR's lines count (DRIVER §5, D4/D20). The new module's name is a suggestion; `hilclaw/case_lookup.py` is touched only for its docstring if the tool makes a sentence of it false.
hq: []
---
## Why

PLAN P2-7 (case storage and exact-match lookup, MVP minimum) is open. Two of its three parts exist:
- the case is stored at the end of a round (`case.write`, ADR-0133);
- the hypothesis injection at instance start exists (ADR-0075, ADR-0112).

The third part is still missing. P2-7 says the technique choice "reads the cases of that key and records the reference in the decision log". `hilclaw/case_lookup.py` implements the lookup of ADR-0073 decision 1, but no registry tool gives it to an agent. `orchestration/agents/technique-selector.md` says: "Write no `cases_read` and no basis entry of kind `case`: no lookup tool is in your list".

ADR-0132 decision 5 leaves that tool to "the case-lookup work of PLAN P2-7, which gives its name, result and kinds, how the lookup's reports are carried and whether a selection goes on after one". ADR-0132 Consequences slice 4 is this work: "the lookup read tool in the selector's list, and the selector recording `cases_read`". ADR-0073 Boundaries also leave open "how a report of a set-apart or invalid case is carried and whether a selection may go on after it" and "how a selection is made to take the lookup's output and record `cases_read`" (OD-18, OD-23).

P2-6 and P2-7 come before P2-5 in the P2 order, and P2-5 covers FR-18 and S1. This is checklist work, so the D18 rule for work outside the checklist does not apply. These are design parts of OD-30 and OD-23 that the driver may close (DRIVER §9, D6). By D20 ① and ③, the record, the tool and the selector's use of it go in one task: code mode, with the ADR file in the PR. The selector's definition depends on the tool's name and result, which this record decides, so it is not split into a second task made in advance (D20 ④).

The P2-1 round steps are all defined after T-0487 (ADR-0172). That task's Result names no further slice, so this task does not touch `orchestration/round-manager.md`.

No owner-only part is known. `PROCESS/STATE.json` at `73fc2d1c` has no unresolved HQ, no PR is open, and no item of `PROCESS/RuntimeAcceptance.md` has the state `실패`.

**Stop conditions. The executor checks these and does not assume them away:**
- If the only defensible design needs any of the following, return BLOCKED with a Korean question for the owner (DRIVER §8: the issue, options (a)/(b)/(c), what stays blocked and what does not):
  - **sharing of cases across forks or data repositories** (OD-25);
  - **a ranking, a "better than", or a choice among cases by quality** (#5 A-4, OD-1, OD-7);
  - **C-6 or OD-3**.
- **A bound on how many cases are returned, or a selection rule for many cases**, is open in OD-30 ("조회해 싣는 사례의 선택과 양"). ADR-0073 Boundaries say "any bound needs a derivation or a source". If the record can give neither, it returns what ADR-0073 decision 1 says (every valid case of the key except the reader's own run's) and leaves the bound open by name. It does not invent a number.
- If the design needs a new data-plane file, member, value or version, that is a data-plane schema change (CLAUDE.md A-13). Examples: a new member of `hypotheses.json`, `case-*.json` or `instance.json`; a file that caches the lookup. If no means that avoids it can be argued on the record's own ground, stop and return BLOCKED with the owner question. A new failure kind of the tool layer is not a data-plane change (as ADR-0132 decision 4 says of its kinds).
- If an open PR touches the same rows or sections of `ARCHITECTURE/`, or any file in `touchesFiles`, stop and return BLOCKED (CLAUDE.md 세션 진입 점검).

## Required Reading

Line numbers are those of `main` at `73fc2d1c`. Where the text and a line number disagree, the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

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
- **What the record answers**:
  - `ARCHITECTURE/decisions/ADR-0132-od23-first-case-selection.md`: decision 3 (its tools, lines 42-48), decision 4 (`hypotheses.write` and its check ④, lines 50-65), decision 5 (lines 67-71), decision 7 (lines 81-87), Consequences slice 4 (line 131) and Boundaries (lines 140-149).
  - `ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md`, the whole file (132 lines): decisions 1 to 3 and Boundaries (lines 112-124).
  - `ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md`: decisions 1 to 4 (the case file and the key directory).
- **The model for a read tool given to the selector, and for form**: `ARCHITECTURE/decisions/ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md`. Read decision 3 (`catalog.read`, lines 40-56), Consequences (109-121) and Boundaries (122-131). Format: ADR-0001 "Record format". Use the status marking, the Context rows, the Walk-through table, the "less exact, not edited" list and the runtime acceptance items as ADR-0171 and ADR-0172 do.
- Also read:
  - ADR-0129 decisions 2 to 4 (`hypotheses.read`, a typed read tool);
  - ADR-0010 decisions 3 and 4 (the MCP front; a name without `_`);
  - ADR-0015 decisions 2 to 4 (request members, `invalid_request`, no data root in a request);
  - ADR-0019 decisions 2 and 3 (the `run_file_*` kinds);
  - ADR-0139 decisions 3 and 4 and ADR-0146 decisions 2, 3 and 6 (the derived pre-approval and the caller check from an agent's `tools`).
- **Where the record is entered.** Follow each file's own rules, and do not copy the wording of earlier task files:
  - `ARCHITECTURE/Requirements.md`:
    - the "행 형식" paragraph (line 84);
    - the OD-30 row (line 121) and the OD-23 row (line 114);
    - the OD-18 row (line 109), only where the record answers part of it.
  - `ARCHITECTURE/OpenDecisionProposals.md`:
    - the "기록 규칙" in its header (line 8);
    - § OD-30 (from line 517; the "조회해 싣는 사례의 선택과 양" bullet and "제안으로 남는 부분");
    - § OD-23 (from line 431);
    - § OD-18 (from line 295), if touched.
  - `ARCHITECTURE/StandardScenarios.md`: its check rules (from line 13) and the first paragraph of § 검사 결과 (line 168). S1, S6 and S11 are the likely scenarios.
- **Code (observation, then the slice)**:
  - `hilclaw/case_lookup.py`, the whole file: `find`, `lookup`, `cases_read`, `Found`, `Report` and their kinds;
  - `hilclaw/hypotheses_cases.py`: `check_run`;
  - `hilclaw/hypotheses_write_tool.py`: the module docstring and `_cases` / `_reported`, which already map lookup failures to `cases_unreadable` and `cases_mismatch`;
  - `hilclaw/catalog_tool.py`, the whole file: the closest model of a read tool;
  - `hilclaw/tools.py` `default_registry` and its docstring (from line 180);
  - `hilclaw/turn_permissions.py`, lines 1-125;
  - `hilclaw/turn_definition.py`: the module docstring.
- **Definition**: `orchestration/agents/technique-selector.md`, the whole file (94 lines).
- **Tests**:
  - `tests/test_catalog_tool.py` (the model for the new test file);
  - `tests/test_turn_definition.py`: `TECHNIQUE_SELECTOR_TOOLS` (line 29) and the selector tests from line 819;
  - `tests/test_turn_permissions.py` `test_holder_lists_the_real_definition` (line 407);
  - `tests/test_caller_check.py` `test_the_real_technique_selector_holds_catalog_read` (line 313);
  - T-0485's `## Result` in `PROCESS/tasks/T-0485-adr-round-one-techniques-and-coder-delegation.md`, for the list of registry pinning assertions that the last new registry tool changed.

## Acceptance Criteria

1. **The ADR.** Write a new `ARCHITECTURE/decisions/ADR-0173-<slug>.md`. If 0173 is taken, use the next free number; check `ARCHITECTURE/decisions/` and the remote branches. The file name in `touchesFiles` is a suggestion. Scope: the runs of ADR-0120 decision 1, the selection of a round >= 1 (ADR-0132 decision 1).
   - It decides at least the points ADR-0132 decision 5 leaves to this work:
     - **(a) The tool**: its name, with no `_` (ADR-0010 decision 4); its request, exactly `run_id` unless the record argues another member (ADR-0015 decision 4); its result, in a form that lets the selector write `cases_read` and `case` basis entries that `hypotheses.write` check ④ admits (`hilclaw.hypotheses_cases.check_run`). Say whether the result carries the `cases_read` value of ADR-0073 decision 3 (`case_lookup.cases_read`) or leaves it to the selector.
     - **(b) Its checks and kinds, in order**: reuse existing kinds with their meanings where they fit (`invalid_request`, `no_data_root`, the four `run_file_*` kinds for `instance.json`, `cases_unreadable` of ADR-0132 decision 4). Name any new kind and search `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/` for it first, as ADR-0132 decision 4 did. Say whether the call is journaled and whether it costs a limited resource.
     - **(c) How the lookup's reports are carried** (`key_record`, `invalid`, `set_apart`, `unreadable` of `hilclaw/case_lookup.py`), and a miss of the key (no stored key record).
     - **(d) Whether a selection goes on after a report, a miss or a failure kind**, and what the selector writes then. The answer must keep ADR-0073 decision 3's meaning of an absent `cases_read`.
     - **(e) Who holds the tool**: the technique-selector's `tools` list, and whether any other agent or `ROUND_MANAGER_TOOLS` lists it, with the caller check's consequence (ADR-0146 decisions 2, 3 and 6).
     - **(f) The selector's use**: when in its work it calls the tool (before the record, since a record's `basis` of kind `case` and `cases_read` are written once, ADR-0059 decision 1), and the fixed rules that replace "Write no `cases_read` ...". The rest of its judgement stays its own.
   - Weigh the size of the result against what the record knows of the limit on an MCP tool result. If no source gives a bound, keep ADR-0073 decision 1's "every valid case" and name the open bound (OD-30) and the runtime fact (below).
   - Mark every sentence as owner, cited, or the record's own.
   - **Consequences**:
     - The A-13 reading, with no data-plane change.
     - The code slices in order. This task lands all of them unless the size cap forces a split (criterion 3).
     - The sentences of earlier records and docstrings that become less exact, without editing them. At least: ADR-0132 decision 5 "Until that tool exists", decision 3's exact list and the Consequences "The cost, plainly" sentence on the lookup tool; ADR-0073 Boundaries on reports and on how a selection takes the output; ADR-0171 Boundaries "The lookup read tool".
     - Runtime acceptance items for facts only a live session can show. Examples: the selector's sub-agent gets the new tool through its derived pre-approval and calls it without a prompt; the largest result a first-case key directory can give reaches the selector whole under Claude Code's MCP output limit. Number them after the last item in use: (lxxxvi) is ADR-0172's, so the next is (lxxxvii). Check the records and T-0487's Result for a higher roman numeral first. State that these items go to `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22).
   - **Boundaries** keep open what the record does not answer:
     - a selection rule or bound for many cases (OD-30);
     - similar-key lookup and ranking (OD-4, OD-7);
     - carrying cases to the coder or into a spec;
     - other versions and source commits (OD-11);
     - sharing (OD-25, owner-only);
     - the S6 metric (P2-8);
     - hooks beyond the caller check (P2-4);
     - round 0's use of cases;
     - the owner-only items.
2. **Register entries** follow the recording rules written in those files, not the wording of earlier task files:
   - Requirements.md: follow the "행 형식" paragraph (line 84) in the OD-30 and OD-23 rows, and in the OD-18 row only where the record answers part of it.
   - OpenDecisionProposals.md: follow the header's "기록 규칙" (line 8) in § OD-30 and § OD-23, and in § OD-18 if touched. Rewrite the status of each sub-question the record answers in place.
   - StandardScenarios.md: re-check coverage under its check rules (CLAUDE.md "문서 커버리지 재검사"), S1, S6 and S11 first. Update § 검사 결과 as its first paragraph says. Add a history entry only if a verdict changes.
3. **Code: the slices the record names**, in one PR unless the size cap forces a split:
   - **The tool**: a new module of `hilclaw/` (name per the record; `hilclaw/cases_tool.py` is a suggestion) built on `hilclaw.case_lookup`, not a second lookup. Add it to `default_registry` in `hilclaw/tools.py` in the source and in no other way (#5 A-12 point 3), and update its docstring. No new external dependency.
   - **The selector's use**, in `orchestration/agents/technique-selector.md`:
     - the new MCP name in `tools`;
     - a "What you are given" line for it;
     - the fixed rules of decision (f), replacing "Write no `cases_read` and no basis entry of kind `case` ...";
     - its report lines, if the record adds any.
     Each changed sentence cites the new ADR's decision. `ROUND_MANAGER_TOOLS` and the other agent files change only if decision (e) says so.
   - **Docstrings**: the `hilclaw/turn_definition.py` docstring and the `hilclaw/case_lookup.py` docstring, only where the slice makes a sentence false.
   - If the ADR and the slices exceed 600 lines or 10 files (tests excluded), land the ADR with the tool and name the selector slice in `## Follow-ups` (DRIVER §5). In that case update `touchesFiles` in the PR body and in `## Result`.

   Use no wording in a definition that the records do not support. No multi-line comments in code.
4. **Tests** (code mode; D12; test files are outside the size cap). Use fixture files under `tmp_path` and the real definitions copied there only. Never use a real `claude`, `docker` or `clang` (D16).
   - **The new test file** for the tool module, covering every public function:
     - happy: a hit with cases of other runs, returned in the order of ADR-0073 decision 1, the reader's own run's cases left out; a hit with no case;
     - branch: a miss (no stored key record); each lookup report kind carried as decision (c) says; an `instance.json` without an `op_signature`, if `case_lookup.lookup` allows one;
     - error and negative: a missing or extra request member and a bad `run_id` (`invalid_request`); no data root; each `run_file_*` kind for `instance.json`; a file-system failure of the lookup; every other kind the record names, in its order.
   - **The selector, in `tests/test_turn_definition.py`**:
     - `TECHNIQUE_SELECTOR_TOOLS` gains the new name;
     - the body states the new fixed rules with their citations;
     - negative: the body no longer says no lookup tool is in its list, and the selector still requests no check, measurement, spec or coder call.
   - **`tests/test_caller_check.py`**: the real definition passes the new tool for the selector and refuses it for the Round-Manager and for every other agent, as decision (e) says.
   - **`tests/test_turn_permissions.py`**: the selector's tuple in `test_holder_lists_the_real_definition` gains the name.
   - **Pinning assertions you may touch** (DRIVER §5 D21; list each in the PR body). Each is touched only by the new tool's name, and only if its list changes:
     - `TECHNIQUE_SELECTOR_TOOLS` in `tests/test_turn_definition.py`;
     - the selector's tuple in `tests/test_turn_permissions.py` `test_holder_lists_the_real_definition`, and `FIXED` there if the derived list is pinned;
     - `tests/test_tools.py` `DEFAULT_SET`;
     - `tests/test_blob_tools.py` `test_the_default_registry_holds_the_definitions` and `test_the_mcp_front_lists_the_blob_tools_among_the_fixed_set` (the unpacking of the first names and the slice after it);
     - `tests/test_check_definition.py`: the registry name lists, the MCP name list, the joined names string and any index of a listed tool that moves;
     - `tests/test_mcp_front.py` `FIXED_NAMES`, the `held` map and the listed-name lists;
     - `tests/test___main__.py` `FIXED_NAMES`;
     - `tests/test_default_registry_schemas.py` `ACCEPTED` (one accepted request of the new tool).
   - **An assertion that pins old prompt text** changes only where the slice replaces that text: `test_the_technique_selector_body` (`"Write no `cases_read` and no basis entry of kind `case`"`, line 856). State the change and its reason in the PR body. Every other existing assertion stays as it is.
   - Run `python -m pytest`, `ruff check .` and `ruff format --check .`. Coverage of `hilclaw/` stays at line >= 80% and function >= 80%, and the test-presence check holds. CI must be green before the squash-merge.
5. **Landing.**
   - The commit body names the language and the reason in one line.
   - The PR body ends with `Task: T-0488`.
   - After landing, post the owner notice of DRIVER §9 on issue #5 in English: what the ADR decides, the landed commit and the 7-day objection window. Its last line is `— posted by driver`. Record the URL in `## Result`.
6. **Result.** In `## Result`, write:
   - the ADR and what it decides, in a few lines;
   - the tool's name, request, result and kinds;
   - the selector sentences rewritten or added, quoted briefly, each with its decision;
   - the test assertions changed, the D21 pinning lists among them;
   - the record sentences made less exact but not edited;
   - the runtime acceptance items, for the driver to add to `PROCESS/RuntimeAcceptance.md` (not as an HQ);
   - whether, in the executor's reading, PLAN P2-6 and P2-7 still hold any work before P2-5, and what it is (for the planner).

## Out of Scope

- A selection rule or bound for many cases, similar-key lookup, ranking, `technique_stats.json`, carrying cases to the coder or into a spec.
- Any new data-plane file, member, value or version (a BLOCKED reason, CLAUDE.md A-13); any change to `hilclaw/cases_file.py`, `hilclaw/cases.py`, `hilclaw/hypotheses.py` or their validators.
- `orchestration/round-manager.md`, `orchestration/agents/coder-driver.md`, `orchestration/agents/evaluator.md` and `orchestration/agents/experiment-runner.md`, unless decision (e) gives the tool to one of them.
- The S6 metric and calculation tool (P2-8); hooks beyond the caller check (P2-4).
- Editing any earlier ADR, README, UsageCases, `catalog/`, `.claude/settings.json` or `.claude/settings.local.json`; any new external dependency.
- Starting `claude`, Docker or `clang` on this machine (D16). A run that reads real cases is P2-5's verification, through a stub `claude`, and not this task's.

## Follow-ups

- (planner) The selector slice, if the size cap split it off (criterion 3).

## Result
