---
id: T-0485
title: Record who chooses the technique ids of a round >= 1 spec and how they reach the coder-driver, and the coder-driver's round >= 1 delegation, as one new ADR (rest of OD-23, with OD-22/OD-6 where touched), and land its first code slice (the layer-1 definitions, or the registry tool the record needs first), with tests
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-5, FR-8, FR-17, OD-23, OD-22, OD-6, S0, S1, "PLAN P2-1"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - orchestration/round-manager.md
  - orchestration/agents/coder-driver.md
  - orchestration/agents/technique-selector.md
  - hilclaw/turn_definition.py
  - hilclaw/turn_permissions.py
  - tests/test_turn_definition.py
  - tests/test_turn_permissions.py
  - tests/test_caller_check.py
estimatedSize: {loc: 330, files: 9}   # tests excluded from the cap; the ADR's lines count (DRIVER §5, D4/D20). If the record needs a new registry tool first, the code slice changes (criterion 3 (B)) and `hilclaw/tools.py`, a new module and the registry-name test files join touchesFiles.
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and round procedure) is open, and in the P2 order (P2-1 to P2-4, P2-6, P2-7, then P2-5) it is the next item that can move. This is checklist work, so the D18 rule for work outside the checklist does not apply. P2-5 (the first end-to-end run, `cpu_standin` x GEMM, 5 rounds) needs it: today a turn of a round >= 1 stops right after it reads the round's hypothesis record (step 7 of "The round steps" in `orchestration/round-manager.md`, landed by T-0484). No round >= 1 reaches a spec write or a coder call, so no run can get past round 1.

What is on `main`:
- `spec.write` already composes a round >= 1 spec from a `techniques` request member (ADR-0151, code slices landed by T-0415/T-0416).
- `coder.run` accepts any round (`hilclaw/coder_call.py` `_checked`).
- The technique-selector writes the round's `decision/hypotheses.json` (ADR-0132, T-0484).
- The catalog `catalog/cpu_standin/` holds four entries with `## When` (selection criteria) and `## Guidance` (ADR-0150).

No record decides the following. The records leave all of it open by name:
- **who chooses which technique ids a round >= 1 spec carries, by what criteria and means, and how those ids reach the coder-driver and `spec.write`**. See ADR-0132 Boundaries, second bullet; ADR-0151 Boundaries, "The selection side"; ADR-0150 decision 2, last bullet, and decision 4, "Not decided here".
- **how the catalog's selection criteria (`## When`) reach the one that chooses** (FR-8 "선택 기준은 Orchestrator 세션에서 트리거에"; ADR-0150 decision 2; ADR-0132 Boundaries: "a `Skill`, a tool or `Read`").
- **the coder-driver's round >= 1 delegation and `coder.run` for round >= 1**. See ADR-0141 decision 6, "Left open and named: … any coder call in a round ≥ 1"; ADR-0151 Boundaries, second bullet; ADR-0132 Boundaries, "the coder-driver's round ≥ 1 delegation (P2-1)".

The Requirements OD-23 row lists them under `**잔여**` ("라운드 spec의 기법 id를 누가 정해 coder-driver에 넘기는지", "라운드 ≥ 1의 코더 호출"). These are design parts of OD-23 that the driver may close (DRIVER §9, D6). By D20 ① the record goes with its first code slice in one task: code mode, with the ADR file in the PR.

**Scope is deliberately the coder-call side only**, as ADR-0141 was for round 0. The steps that follow the coder call in a round >= 1 are a later record and a later task. Those steps are the evaluator's checks, the measurement, the comparison (ADR-0140), the verdicts (ADR-0128), `case.write` and the closing steps. Folding them in was weighed: they are a different question (ADR-0142 was a separate record from ADR-0141 for round 0). Together they would raise the risk of the 7-round review limit and of the 600-line cap. D20 ④ also forbids pre-creating the later task while its content depends on this record's numbering of the steps.

No owner-only part is known (#5 A/B items, C-6, OD-25 and OD-3 are not touched). No unresolved HQ exists in `PROCESS/STATE.json` at `5e6a08fc`. HQ-0048 (answered) and HQ-0053 (answered: the coder's credential) are settled. HQ-0034 (OpenMP) is deferred in PLAN and stays out.

**Stop conditions. The executor checks these and does not assume them away:**
- Suppose the only defensible way to carry the chosen ids needs any of these:
  - a new data-plane file, member, value or version;
  - a content or form for `decision/decision.md` (ADR-0132 decision 2: "no record gives its content or form");
  - a member of `hypotheses.json` that names a technique (ADR-0059 decision 3: a hypothesis names no technique).
  That is a data-plane schema change (CLAUDE.md A-13). If no means that avoids it can be argued on the record's own ground, stop. Return BLOCKED with a Korean question for the owner (DRIVER §8: the issue, options (a)/(b)/(c), what stays blocked and what does not). Note that the spec itself already records the ids a call got (`guidance.techniques`, ADR-0151 decision 2 (b)).
- If writing the record shows an owner-only decision, stop and return BLOCKED with the question. Examples:
  - a reading of FR-8's "Skill" that the record cannot make as its own design subject to the owner's objection;
  - anything about the models of the orchestration's agents (#5 A-8).
- If an open PR touches the same rows or sections of `ARCHITECTURE/`, stop and return BLOCKED (CLAUDE.md 세션 진입 점검).

## Required Reading

Line numbers are those of `main` at `5e6a08fc`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 73: executor procedure, landed check, resume rule, time limit), **§5** (lines 87-116: task format, naming, size cap D4/D20, trailers, the test rules D12, the pinning-list rule D21), **§8** (lines 144-151: HQ form, runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`, the `— posted by driver` footer) and **§9** (lines 153-160: which ODs the driver may close, the owner notice on #5 and the 7-day objection window).
- CLAUDE.md, the whole file. These sections matter most:
  - "미결은 발명하지 않는다";
  - "문서 커버리지 재검사";
  - "세션 진입 점검";
  - "개발 드라이버와 런타임의 구분": no `claude`, container or board is started on this machine; tests use fixture files and stubs only;
  - "테스트 규칙";
  - "브랜치·merge 절차": code mode and the BLOCKED reasons;
  - "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- Before you edit `ARCHITECTURE/`, run `gh pr list`, read issues #4, #5, #7 and #8, and read the unresolved `humanQuestions` in `PROCESS/STATE.json` (CLAUDE.md 세션 진입 점검).
- **The model records** for form and the direct predecessors:
  - `ARCHITECTURE/decisions/ADR-0132-od23-first-case-selection.md`, the whole file (157 lines). Read decisions 2, 3, 6 and 7 most closely, and the Boundaries (lines 140-149).
  - `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`: decision 1 (line 41), decision 5 (line 74: the coder-driver definition and its interim `spec_exists` rule), decision 6 (line 86: the round-0 delegation step and what it leaves open), Walk-through, Consequences and Boundaries.
  - The format follows ADR-0001's "Record format" section. Status marking, the K-rows of Context, the Walk-through table and the Consequences with the "less exact, not edited" list follow ADR-0132.
- **What is open and why** (read the parts named):
  - ADR-0151 (`ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md`): decision 2 (from line 37), above all (b) and (c); decision 3 (lines 63-77: the `techniques` request member, checks ⑦ and the kinds); Consequences (110-123); Boundaries (125-133).
  - ADR-0150 (`…/ADR-0150-od22-first-case-technique-catalog.md`): decision 2 (lines 53-67, the FR-8 split in its last bullet), decision 4 (78-82), decision 5 (84-), Boundaries (150-).
  - ADR-0138 decision 2 (b) (round 0 carries no technique) and decision 3 (line 62: `spec.write` and `spec_exists`).
  - ADR-0126 decisions 2, 4 and 6 (lines 37, 60, 70: the coder-driver judges nothing and composes nothing; the delegation names the tuple and no place).
  - ADR-0123 decision 2 (line 41: a delegation names the run id and no place).
  - ADR-0059 decision 3 (line 51: a hypothesis names no technique) and decision 1.
  - ADR-0112 decisions 1 to 3 (rules of conduct of the selection).
  - ADR-0139 decisions 3 to 5 (lines 59-80: pre-approved list derived from the agents' `tools`; the built-in set; sub-agent permissions) and decision 9 (line 100).
  - ADR-0146 decisions 2, 3 and 6 (the caller check takes up agent files with no code change).
  - ADR-0118 decision 5 (`LAYOUT`: what is copied into the session directory; `catalog/` is not).
  - ADR-0142 decisions 2 and 6 (how round 0 treats the coder-driver's report; the stop).
  - ADR-0143 decisions 2 and 7 (the stop's `run.commit`).
- **Where the record is entered.** Read each file's own rules; do not copy the wording of earlier task files:
  - `ARCHITECTURE/Requirements.md`:
    - the "행 형식" paragraph (line 84);
    - the OD-23 row (line 114);
    - the OD-22 row (line 113), only if the record answers how the selection criteria reach a selection;
    - the OD-6 row (line 97), only if the record answers part of OD-6;
    - FR-8 (line 26), read only.
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" in its header (line 8); § OD-23 (from line 429; its 채택분 lines and "제안으로 남는 부분" at line 459); § OD-22 (line 420) and § OD-6 (line 59) if touched.
  - `ARCHITECTURE/StandardScenarios.md`: its check rules (from line 13) and the first paragraph of § 검사 결과 (line 168).
- **Definitions (whole)**: `orchestration/round-manager.md`; `orchestration/agents/coder-driver.md`; `orchestration/agents/technique-selector.md`; `orchestration/agents/evaluator.md`; `orchestration/agents/experiment-runner.md`.
- **Code**:
  - `hilclaw/spec_tool.py`: the module docstring and the `techniques` checks;
  - `hilclaw/catalog.py`: the module docstring, `check`, `technique`;
  - `hilclaw/coder_tool.py` and `hilclaw/coder_call.py` `_checked`;
  - `hilclaw/turn_permissions.py`: the module docstring, `ROUND_MANAGER_TOOLS`, `options`;
  - `hilclaw/turn_definition.py`: the module docstring, `LAYOUT`, `SOURCE`;
  - `hilclaw/caller_check.py`: the module docstring, read only;
  - `hilclaw/tools.py` `default_registry`.
- **Tests (whole)**: `tests/test_turn_definition.py` (above all the coder-driver tests from line 500, the prompt tests from line 577 and the technique-selector tests from line 795), `tests/test_turn_permissions.py`, `tests/test_caller_check.py`.

## Acceptance Criteria

1. **The ADR.** Write a new `ARCHITECTURE/decisions/ADR-0171-<slug>.md`. If 0171 is taken, use the next free number; check `ARCHITECTURE/decisions/` and the remote branches. The slug is your choice. Its scope is the runs of ADR-0120 decision 1 with one candidate per round, as in ADR-0151.
   - It decides at least the following:
     - **The holder of the choice of a round >= 1's technique ids**, and the criteria it uses. Weigh at least these holders:
       - the technique-selector, as part of the selection work of ADR-0132;
       - the coder-driver, which today "judges nothing and composes nothing" (ADR-0126 decision 2; ADR-0141 decision 5);
       - the Round-Manager;
       - a deterministic rule of a tool.
       Weigh each against K2 of ADR-0132 (judgement in a sub-agent; reading the record rather than a report). Say how the choice relates to the round's hypotheses (ADR-0059 decision 3 stays: a hypothesis names no technique). Say whether an empty `techniques` list is allowed and when.
     - **How the selection criteria (`## When`) reach the holder** (FR-8; ADR-0150 decision 2). Weigh a `Skill` (the session has none, ADR-0139 decision 4), a registry read tool, and `Read` of `catalog/`. For `Read`, state how the holder finds `catalog/` when a delegation names no place (ADR-0123 decision 2) and `catalog/` is not in `LAYOUT` (ADR-0118 decision 5). Give the FR-8 reading the choice rests on, marked as the record's own design.
     - **How the chosen ids reach the coder-driver and `spec.write`'s `techniques`**: for example the delegation message, a file, or a tool result. Account for K2 condition 3 (a report is not a record). The data-plane stop condition of Why applies.
     - **The coder-driver's round >= 1 delegation**:
       - the tuple (`round` r, `candidate` 1, `attempt` 1, per ADR-0151 decision 3);
       - what the message names beyond ADR-0126 decision 6;
       - whether the coder-driver's `tools` change;
       - what it does on `spec_exists` and on each other kind, in round >= 1. Keep ADR-0141 decision 5's interim rule unless the record argues a change, and do not answer OD-8 ㉖ (가) / OD-23 ① (가).
     - **The Round-Manager's round >= 1 steps from the read of the record to the coder-driver's report**:
       - the new step(s) after step 7;
       - which reports go on and which come to the stop;
       - that the steps after the coder call stay undefined, so the turn comes to the stop after the report, as ADR-0141 decision 6 did for round 0 before ADR-0142.
   - Mark every sentence as owner, cited, or the record's own.
   - **Consequences**:
     - The A-13 reading, with no data-plane change.
     - The code slices for the planner, in order. This task's slice is the first.
     - The sentences of earlier records and the docstrings that become less exact, without editing them. At least these become less exact: ADR-0132 Boundaries, ADR-0151 Boundaries, ADR-0150 decision 4 "Not decided here", ADR-0141 decision 6 "Left open and named", the `hilclaw/catalog.py` docstring ("which ids a spec carries is the selection side's (HQ-0048)"), and the Requirements/OpenDecisionProposals sentences you rewrite.
     - Runtime acceptance items for facts only a live session can show. Number them after the last item in use: (lxxxii) is ADR-0170's, so the next is (lxxxiii). Check the records for a higher roman numeral first. The ADR states that these items go to `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22).
   - **Boundaries** keep open what this record does not answer:
     - the steps after the coder call in a round >= 1;
     - the lookup read tool (ADR-0132 decision 5, P2-7);
     - reads of earlier verdicts and measurements for a selection;
     - N > 1 (OD-29), repairs (OD-19), and a second call for one tuple (OD-23 ① (가));
     - hooks on the order (rest of OD-18);
     - the catalog of other keys (OD-22).
2. **Register entries** follow the recording rules written in those files, not the wording of earlier task files:
   - Requirements.md: the OD-23 row (line 114). Also the OD-22 row (line 113) and the OD-6 row (line 97), only where the record answers part of them. Follow the "행 형식" paragraph (line 84):
     - add one ADR link per touched row after `**확정분**:`;
     - rewrite `**잔여**:` in place where it changes (today it names "라운드 spec의 기법 id를 누가 정해 coder-driver에 넘기는지" and "라운드 ≥ 1의 코더 호출");
     - do not restate the ADR, and add no dated paragraph.
   - OpenDecisionProposals.md: § OD-23, and § OD-22 / § OD-6 if touched. Follow its header's "기록 규칙" (line 8):
     - add one `- **채택분** [ADR-NNNN](…) — …` line per touched section;
     - rewrite the open parts in place ("제안으로 남는 부분", and a sub-question's status "→ 부분 답: … 남음: …" where one is touched);
     - append no dated paragraph.
   - StandardScenarios.md: re-check coverage under its check rules (CLAUDE.md "문서 커버리지 재검사"). Update § 검사 결과 as its first paragraph says. Add a history entry only if a verdict changes.
3. **Code: the first slice the ADR names.** Exactly one of (A) or (B) applies, whichever the record makes first:
   - **(A) If the record's means needs no new or changed registry tool**, the slice is the layer-1 definitions:
     - `orchestration/round-manager.md`:
       - Add the round >= 1 step(s) after step 7. Step 7's "If it returns the round's record, come to the stop as well: the steps after it are not yet defined" becomes the go-on to the new step(s).
       - The stop paragraph for rounds >= 1 now follows the coder-driver's report: report in one line that the following steps of round `<round>` are not yet defined.
       - "Your run" widens the `Agent` bullet to the round >= 1 coder-driver delegation.
       - Check "The closing steps of a round" first sentence and the list of ends in "The end of a session"; change them only where the new steps make them wrong.
       - Each changed sentence cites the new ADR's decision.
     - `orchestration/agents/coder-driver.md`: its description and body cover the round >= 1 delegation as the record says. That includes the `techniques` it passes to `spec_write` and where it takes them from, and any change of its `tools`.
     - `orchestration/agents/technique-selector.md`, only if the record gives it the choice or a new read.
     - `ROUND_MANAGER_TOOLS` in `hilclaw/turn_permissions.py` changes only if the record gives the Round-Manager a new tool.
     - The `hilclaw/turn_definition.py` docstring: the *prompt* bullet and "Not done here" now describe the round >= 1 coder delegation. Docstring only; no code change.
     - If a test shows the permission derivation or the caller check does not take up a changed agent file unchanged, stop and return BLOCKED with the reason.
   - **(B) If the record's means needs a new registry tool, or a change of `spec.write` or `coder.run`, before any definition can use it**, the slice is that tool or change:
     - its module, its registration in `default_registry` with its docstring sentence, and its tests;
     - the definitions become the next slice, named in Consequences.
     - Update `touchesFiles` in the PR body and in `## Result`. If the ADR and that slice together would exceed 600 lines or 10 files (tests excluded), land the ADR with the smallest slice that fits. Name the rest in `## Follow-ups` (DRIVER §5).

   Use no wording in a definition that the records do not support. No multi-line comments in code (CLAUDE.md).
4. **Tests** (code mode; D12 applies; test files are outside the size cap). Use fixture files under `tmp_path` and the existing fixtures only. Never use a real `claude`, `docker` or `clang` (D16).
   - **For (A)**, in `tests/test_turn_definition.py`:
     - the coder-driver frontmatter: key set, exact `tools` set, every `mcp__hilclaw__` name served by `default_registry`, no forbidden tool, no `\r`;
     - its body names the round >= 1 rule (the `techniques` it passes and their source);
     - the prompt delegates to `coder-driver` in a round >= 1 only after a read that returned the record;
     - the prompt comes to the stop after that delegation's report, and still says the later steps of a round >= 1 are not yet defined;
     - a failed read still comes to the stop before any coder delegation;
     - negative: no round >= 1 reaches `case.write`, `round.end`, an evaluator or an experiment-runner delegation;
     - if the technique-selector changed: its frontmatter and body.
   - **In `tests/test_caller_check.py`**, if any agent's `tools` changed: the real definition lets each new tool through for its holder and refuses it from the main session and from the other agents.
   - **For (B)**: a new test file for the new module, with happy, every kind in its order, branch and negative cases, every public name exercised, and `definition` with a non-callable source raising `TypeError` as the other tools do.
   - **Pinning assertions you may touch** (DRIVER §5 D21 allows these edits as far as they reflect the change; list each in the PR body):
     - `tests/test_turn_permissions.py`: `FIXED` (line 22) if `ROUND_MANAGER_TOOLS` changes; `test_the_real_definition` and `test_holder_lists_the_real_definition` (the coder-driver's or selector's tool tuple) if an agent's `tools` change;
     - `tests/test_turn_definition.py`: `test_the_coder_driver_frontmatter` (line 500) if the coder-driver's `tools` change; `test_the_technique_selector_frontmatter` (line 795) if the selector's `tools` change;
     - for (B), the registry name lists: `tests/test_tools.py` (near line 490), `tests/test_blob_tools.py` (lines 176 and 707), `tests/test_check_definition.py`, `tests/test_mcp_front.py`, `tests/test___main__.py`, and `ACCEPTED` in `tests/test_default_registry_schemas.py`.
   - **Assertions that pin the old prompt text** change only because the slice replaces the text they pin. State each change and its reason in the PR body:
     - `test_the_stop_follows_the_read_in_later_rounds` (line 865);
     - `test_no_later_round_reaches_a_spec_write_or_a_coder_delegation` (line 889). It becomes a test that the delegation follows only a successful read; keep its negative intent for the steps after the call;
     - `test_the_prompt_keeps_the_stop_in_later_rounds` (line 593);
     - `test_the_prompt_delegates_to_the_coder_driver` (line 577);
     - `test_the_coder_driver_names_the_kind_and_the_result` (line 518);
     - `test_the_prompt_reaches_the_closing_steps_from_round_0_only` (line 659), where they read the replaced text.

     Every other existing assertion stays as it is.
   - Run the full local suite (`python -m pytest`), `ruff check .` and `ruff format --check .`. Coverage of `hilclaw/` stays at line >= 80% and function >= 80%, and the test-presence check holds. CI must be green before the squash-merge.
5. **Landing.**
   - The commit body names the language and the reason in one line: Markdown for the definitions; Python for any tool or docstring.
   - The PR body ends with `Task: T-0485`.
   - After landing, post the owner notice of DRIVER §9 on issue #5 in English. It states what the new ADR decides, the landed commit and the objection window (7 days from the notice), and its last line is `— posted by driver` (DRIVER §8). Record the comment URL in `## Result`.
6. **Result.** In `## Result`, write:
   - the ADR file and what it decides, in a few lines;
   - which of (A) or (B) landed and why;
   - every prompt sentence rewritten or added, quoted briefly, with the decision it follows;
   - the test assertions changed (as in the PR body);
   - the record sentences made less exact but not edited;
   - the runtime acceptance items the ADR names, for the driver to add to `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22; not as an HQ);
   - the next slices for the planner.

## Out of Scope

- The round >= 1 steps after the coder call: evaluator checks at `sim`/`board`, measurement, `timings.compare`, `verdicts.write`, `case.write` and the closing steps of a round >= 1. These need a later record and a later task.
- ADR-0132 slice 4: the lookup read tool and `cases_read` (ADR-0132 decision 5; PLAN P2-7).
- `decision/decision.md` and any writer of it; any data-plane change (no member, file, path, value, version or validator changes). Such a change is a BLOCKED reason (CLAUDE.md A-13).
- Adding, removing or editing `catalog/` entries; the catalog of other accelerators or keys (OD-22).
- Hooks on the order of steps or on a request's `run_id` (rest of OD-18; P2-4).
- Editing any earlier ADR, `README.md`, `UsageCases.md`, `.claude/settings.json` or `.claude/settings.local.json`; any new external dependency.
- Starting `claude`, Docker or `clang` on this machine (D16). An end-to-end round 1 through a stub `claude` is P2-5's verification, not this task's.

## Follow-ups

- (planner) The remaining slices the new ADR names, if any (for example the definitions after a tool slice (B)).
- (planner) The record of the round >= 1 steps after the coder call: the checks, the measurement, the comparison, the verdicts, `case.write` and the closing steps (ADR-0140, ADR-0128, ADR-0133, ADR-0135; PLAN P2-1). Then its code slice.

## Result

**Outcome**: (B) landed: the ADR with its first code slice, the registry tool `catalog.read`. Branch `claude/T-0485-round-one-techniques-and-coder-delegation`; the PR number, review rounds, squash commit and the owner notice are recorded at the end of this section.

**The ADR**: `ARCHITECTURE/decisions/ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md` (part of OD-23, OD-22 and OD-6; runs of ADR-0120 decision 1 with `candidates_per_round` 1, rounds >= 1). It decides:
- the **technique-selector** chooses a round >= 1 spec's technique ids once the round's hypothesis record exists, weighing the round's hypotheses first, then the entries' `## When`, then earlier attempts and records; hypotheses still name no technique (ADR-0059 decision 3); an empty list is allowed (on `catalog_unusable`, e.g. a mock run; on an empty result; or by the selector's judgement);
- the criteria reach it through a **new registry read tool `catalog.read`** (request exactly `run_id`; result `{"entries": [{"id", "when"}]}` in id order; checks `invalid_request`, `no_data_root`, the four `run_file_*` kinds for `instance.json`, `catalog_unusable`; no new kind; not journaled), added to the selector's `tools` in slice 2. `Read` of `catalog/`, `catalog/` in `LAYOUT` and a `Skill` were weighed and not adopted. The FR-8 reading is marked as the record's own, and the Skill form stays open;
- the ids travel as **one fixed report line** `techniques: <id>, ...` / `techniques: none` -> the Round-Manager's coder-driver delegation message -> the `techniques` of `spec.write`; the spec's `guidance.techniques` is the record (no data-plane change);
- the **coder-driver's round >= 1 delegation**: tuple (`r`, 1, 1); the message adds the ids; `tools` unchanged; `techniques` passed for round >= 1 only; ADR-0141 decision 5's interim `spec_exists` rule kept;
- the **Round-Manager's step 8** (round >= 1, after a read that returned the record): delegate to the coder-driver only when the selector's report holds exactly one `techniques:` line, otherwise stop; after the coder-driver's report, the stop ("the following steps of round `<round>` are not yet defined").

**Why (B)**: the turn session holds a copy of `orchestration/` only (ADR-0118 decision 5) and a delegation names no place (ADR-0123 decision 2), so the selector cannot `Read` `catalog/`. The record's means needs a new registry tool before any definition can use it. The definitions are slice 2 (Follow-ups below).

**Code (slice 1)**: Python (the package, its catalog reader and its registry are Python).
- `hilclaw/catalog.py`: new public `criteria(accelerator, *, source=None)` returning `{id: when}` in id order; `_entry` now returns `(when, text)`; docstring brought up to date (it no longer says "which ids a spec carries is the selection side's (HQ-0048)").
- `hilclaw/catalog_tool.py` (new): `catalog.read` of ADR-0171 decision 3; `KIND_CATALOG_UNUSABLE` re-exported from `spec_tool`.
- `hilclaw/tools.py`: registered in `default_registry`, docstring sentence added.
- touchesFiles beyond the task's list: `hilclaw/catalog.py`, `hilclaw/catalog_tool.py`, `hilclaw/tools.py`, `tests/test_catalog.py`, `tests/test_catalog_tool.py` and the registry-name test files below. Not touched (slice 2): `orchestration/*`, `hilclaw/turn_definition.py`, `hilclaw/turn_permissions.py`, `tests/test_turn_definition.py`, `tests/test_turn_permissions.py`, `tests/test_caller_check.py`.
- Size: 349 changed lines in 7 non-test files, plus this task file.

**Prompt sentences rewritten or added**: none in this task. Slice 2 carries them; the ADR fixes their content in decisions 4 to 6.

**Tests**:
- New `tests/test_catalog_tool.py`: definition and schema, non-callable source `TypeError`, result order and `when` text, empty directory, the committed `cpu_standin` catalog, the instance's accelerator choosing the directory, every kind in order (`invalid_request` variants, `no_data_root`, `run_file_missing`/`_invalid`/`_unsupported`/`_unreadable`, `catalog_unusable` for a missing directory, a mock run, a refused catalog, an empty `## When`, an unreadable directory), order checks, nothing created, `default_registry` and the MCP front.
- `tests/test_catalog.py`: `criteria` (sorted, line-feed stripping only, empty directory, new dict, committed catalog, refusals as `check`); `test_public_names` imports `criteria` and checks its docstring.
- Pinning-list assertions changed (DRIVER §5 D21), each only by `catalog.read` / `catalog_read`: `tests/test_tools.py` `DEFAULT_SET`; `tests/test_blob_tools.py` `test_the_default_registry_holds_the_definitions` and `test_the_mcp_front_lists_the_blob_tools_among_the_fixed_set` (unpacking of the first 8 names, slice `[8:]`); `tests/test_check_definition.py` two registry name lists, the MCP name list, the joined names string, and the index of `correctness_check` in the listed tools (`listed[6]` -> `listed[7]`, description and schema); `tests/test_mcp_front.py` `FIXED_NAMES`, the `held` map and docstring of `test_the_fixed_tool_set_is_the_blob_tools_hw_tools_and_run_file_tools`, and three listed-name lists; `tests/test___main__.py` `FIXED_NAMES` and its test docstring; `tests/test_default_registry_schemas.py` `ACCEPTED` (one accepted request).
- No assertion pinning the old prompt text changed (no prompt changed).
- Local: `python -m pytest` 33972 passed, 1858 skipped; `ruff check .` and `ruff format --check .` clean.

**Register entries**: Requirements OD-23, OD-22 and OD-6 rows get one ADR-0171 link each after `**확정분**`. The OD-23 `**잔여**` is rewritten in place: the selection's tool for the catalog criteria and "라운드 spec의 기법 id를 누가 정해 coder-driver에 넘기는지" are removed, and "라운드 ≥ 1의 코더 호출" is narrowed to the steps after it and to other runs. The OD-6 `**잔여**` drops "라운드 ≥ 1 spec의 기법 id를 고르는 쪽(선택 쪽)". OpenDecisionProposals § OD-6, § OD-22 and § OD-23 get one `**채택분**` line each, and § OD-23 "제안으로 남는 부분" is rewritten in place. StandardScenarios: S0 and S1 re-checked, no verdict change; the "최근 재검사" line is updated.

**Record sentences made less exact, not edited**: ADR-0132 decision 1 "Outside" and Boundaries second bullet (and decision 3's exact list once slice 2 lands); ADR-0151 decision 2 (c) and Boundaries first and second bullets; ADR-0150 decision 2 last bullet and decision 4 "Not decided here"; ADR-0141 decision 6 "Left open and named" and its Walk-through row "A round ≥ 1"; ADR-0126 decision 6. Observations until slice 2: `orchestration/round-manager.md` (step 7, the stop), `orchestration/agents/coder-driver.md` (description), the `hilclaw/turn_definition.py` docstring.

**Runtime acceptance items** (for `PROCESS/RuntimeAcceptance.md`, DRIVER §8, D22; not HQs), from ADR-0171 Consequences, to be checked after slice 2 lands:
- (lxxxiii) In a `-p` turn session, the technique-selector's call of `mcp__hilclaw__catalog_read` reaches the tool and its result reaches the selector whole, and the caller check lets it through for the selector and refuses it for the main session.
- (lxxxiv) The selector's final message holds exactly one `techniques:` line, and the Round-Manager carries its ids, unchanged and in order, into the coder-driver's delegation message, from which the coder-driver puts them unchanged into the `techniques` of its `spec.write` request.

**Next slices for the planner**:
- ADR-0171 slice 2, the definitions (PLAN P2-1): `orchestration/agents/technique-selector.md` (`mcp__hilclaw__catalog_read` in `tools`; the choice of decision 2; the report line of decision 4); `orchestration/agents/coder-driver.md` (decision 5: round >= 1 `techniques` from the message; no list means no call); `orchestration/round-manager.md` (step 8 and the moved stop, decision 6; the "Your run" `Agent` bullet); the `hilclaw/turn_definition.py` docstring. Tests go in `tests/test_turn_definition.py` (including the old-prompt assertions this task file lists), `tests/test_turn_permissions.py` (the selector's tuple) and `tests/test_caller_check.py` (`catalog_read` for the selector only).
- The record of the round >= 1 steps after the coder call (unchanged from Follow-ups above).

**PR and review**: PR #299 (Draft, DONOTMERGE until merge). Two review rounds by the dev-reviewer agent: round 1 Request changes (one blocking: the Skill form of the selection criteria was not registered as open; five nits), all addressed; round 2 Approve with two wording nits, fixed without a further round (D20 nit exception).
