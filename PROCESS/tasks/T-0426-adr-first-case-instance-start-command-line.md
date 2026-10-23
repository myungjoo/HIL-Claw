---
id: T-0426
title: Record ADR-0155, the caller of the start of a first-case instance - a command-line entry of the package that hands a person's or a script's instance document to hilclaw.start_instance.start and tells the starter the run id or the refusal (part of OD-23 role assignment and of OD-8 sub-question 17 first part; for PLAN P2-5)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-13, OD-23, OD-8, "UC-1", "PLAN P2-5"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/ADR-0155-od23-first-case-instance-start-command-line.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `8cf6994`):
- `hilclaw/start_instance.py` (T-0324, `5cd442a`) is the one deterministic start function of ADR-0115 decision 2. Its docstring says "it binds no caller (OD-23, UC-1)". ADR-0115 decision 1 and its Boundaries leave the caller open: "a command-line front, a UI, the Round-Manager of P2-1, a CI". No module calls `start`.
- `hilclaw/turn_start.py` is the command-line entry of the turn loop. It takes the run id of an instance that **already exists** (`python -m hilclaw.turn_start <run_id>`).
- So outside a test, nothing can create the `instance.json` of a run. A first run (PLAN P2-5) cannot be started by a person or a script, and neither can the nightly run (PLAN P2-10).
- OD-23's register row lists, among its remaining parts, "역할 배정(첫 사례 instance의 시작을 무엇이 부르는지 포함)". This task closes that point for the first case.

**PLAN order and D18.** PLAN P2 runs in list order. Every round-loop item has no part that can be taken now:
- P2-1: round 0's step 5, the board measurement, waits on `board.run` being registered (P1-1; T-0210/HQ-0021, ADR-0142 decision 7). The round >= 1 steps wait on HQ-0048.
- P2-2: both ADR-0137 code slices have landed (T-0424, T-0425). The round >= 1 coder call waits on HQ-0048.
- P2-3: the round-0 evaluator steps have landed.
- P2-4: the gate half is owner-only (OD-3).
- P2-6 and P2-7: they wait on HQ-0048 and HQ-0031.

The next item is therefore P2-5, and this record is work of P2-5: a run must be started before any of its rounds. Under DRIVER §6 (D18), this is not a follow-up, wording or hardening item. If the reading "P2-5 work" is wrong, it is at least needed for P2-5. The candidate after the round-loop items, the P2-13 joining task of ADR-0153 slice 1, comes later in PLAN order.

**§9 and owner-only items.** The caller of the start is part of OD-23, a design-level OD. Choosing it is not one of the owner-only items of DRIVER §9. The owner has spoken on the start's inputs in two places, and the record must read them and not overrule them:
- #5 A-9 sub-decision 2: N "chosen by the user at instance start; the initial UI offers 1 <= N <= 5 (policy may change later)", read by ADR-0028 as no rule of validity;
- #5 B-4: the initial run caps.

Criterion 4 says what to do if the reading cannot be made without the owner.

**D16.** The command-line entry decided here starts no `claude`. Nothing in this task starts a process, and nothing is required of this machine.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (format, naming, size cap), §8 (the driver footer of a #5 comment) and §9 (OD closing by ADR, owner notice, 7-day objection period).
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`, whole (155 lines). In particular decision 1 (lines 46-57), decision 2 "What the function takes, and what stays on the caller's side" (line 73), decision 3 (lines 81-89), the Walk-through rows on lines 94-95, and Boundaries line 139.
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` decision 3 (lines 49-68: the command-line front is "for people, scripts and tests") and decision 5 (lines 100-103: configuration and data root).
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md` decisions 1 to 3 (lines 23-58).
- `ARCHITECTURE/decisions/ADR-0028-od8-instance-record-candidates-per-round.md` lines 13-55 (the owner's sentence on the initial UI, and why the 1-to-5 range is no rule of validity).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md` decision 5 (lines 77-89: what the starter of the turn loop is told). This is a precedent for a report form, not a rule for this entry.
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md` lines 45-50 and 100-104: `instance.json` enters the data repository's history with the commit that ends round 0. This entry makes no commit.
- `hilclaw/start_instance.py`, whole (130 lines): the signature `start(document, *, data_root)`, the reports `GivenRunIdError`, `MissingMembersError`, `RunIdInUseError`, `OSError` and the `ValueError` of `json.dumps`.
- `hilclaw/turn_start.py` lines 1-120 (module docstring: command line, data root, the one-line JSON report and its exit statuses).
- `hilclaw/data_root_source.py`, whole (`configured`, `obtain`).
- `ARCHITECTURE/UsageCases.md` UC-1 (lines 69-78).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-28), S0, S1 and S2 (lines 30-75), and §검사 결과 from line 168. Its first paragraph holds the recording rule.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84), and the register rows OD-8 (line 99) and OD-23 (line 114).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's "기록 규칙" (line 8);
  - § OD-8, lines 89-160, in particular line 126 (the ADR-0115 entry) and line 141 (sub-question ⑰);
  - § OD-23, from line 412 to the end of that section.
- GitHub issues #4, #5, #7 and #8, for the owner-sentence search of criterion 3 (`gh issue view N --comments`).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md "세션 진입 점검").
   - Run `gh pr list`. Read issues #4, #5, #7 and #8, and the unresolved `humanQuestions` of `PROCESS/STATE.json`.
   - If an open PR edits the OD-8 or OD-23 rows or sections, or `ARCHITECTURE/decisions/ADR-0155*` exists on `main` or on an open branch, stop and return BLOCKED with the reason. Do not pick another number on your own.
   - The record's Status names the open HQs it checked and states that none of them is touched. HQ-0021, HQ-0048 and HQ-0031 are the ones closest to this record.

2. **The record** `ARCHITECTURE/decisions/ADR-0155-od23-first-case-instance-start-command-line.md`. It follows the section layout of ADR-0115 (Status, Context, Decision with a Walk-through, Alternatives considered, Consequences, Boundaries, References), in English. It is scoped to the instances of ADR-0076 decision 1. It decides, each point with its reason:
   - **(a) The caller.** A person or a script starts a first-case instance through a command-line entry of the package of the form `python -m hilclaw.<module>`. This entry is not a tool of the registry's command-line front `python -m hilclaw <tool name>`, as ADR-0115 decision 3 and its Walk-through line 94 require. The record names the module, or states that the code task names it. It also states whether the entry lives in `hilclaw/start_instance.py` or in a new module.
   - **(b) The input.** How the document reaches the entry: for example, the path of one file holding the JSON document, or standard input. Choose one and give the reason.
     - Which arguments and options exist. Prefer none beyond the input.
     - That the entry passes the parsed document to `start` unchanged. It adds no member, fills in no default and asks nobody, so the gathering of values stays with the person or the script (ADR-0115 decision 2).
     - What the entry does with input that is not one JSON object: unreadable, not UTF-8, not JSON, or JSON but not an object. The decoding rules are left to the code task within that answer.
   - **(c) The data root.** Where the entry takes it from, for example `hilclaw.data_root_source.configured` as `hilclaw.turn_start` does (ADR-0010 decision 5). Also what it reports when no data root can be had.
   - **(d) The report to the starter.**
     - The form: for example one line of JSON on standard output with an `outcome` member and distinct exit statuses, as `hilclaw.turn_start` tells its starter (ADR-0122 decision 5, a precedent only).
     - On success the report gives the run id. Each refusal or stop of `start` must be told apart from the others: given id, missing members, out of scope or invalid, id in use, file-system failure, and the NaN/infinity `ValueError`. So must the input and data-root failures of (b) and (c).
     - Whether the exact values, the member names and the statuses are fixed by the record or left to the code task. Values the record leaves open are named as the code task's.
   - **(e) What the entry does not do.** It starts no turn and no `claude`. It writes no `STATE.json` and no line of `events.ndjson`, and makes no commit; `instance.json` enters history with round 0's end, ADR-0127. It is no tool and gets no MCP name. It keeps nothing between calls.
     - **How the starter goes on.** The record states it: the starter then runs `python -m hilclaw.turn_start <run_id>` with the reported id. Alternatively, if the record joins the two, it says how and why, weighed against ADR-0122 and the "no option" rule of `turn_start`.
   - **Alternatives considered.** At least these:
     - the Round-Manager or another agent as caller through a new registry tool (ADR-0115 (a'));
     - a joined start-and-loop command;
     - an interactive prompt or menu that asks for the values;
     - leaving the caller to each test or script that imports `start`.
     Each row gives the reason it was taken or not.
3. **Owner sentences.**
   - Status records the owner-sentence search of #4, #5, #7 and #8 that the record relied on. Give the search terms, and for each sentence used its comment URL and the quoted words.
   - At least these are quoted and read: #5 A-9 sub-decision 2 ("chosen by the user at instance start; the initial UI offers 1 ≤ N ≤ 5 (policy may change later)"), and the #5 B-4 initial run caps.
   - The record states explicitly how the entry stands to "the initial UI" of that sentence. Two readings are possible:
     - the entry is not that UI: the UI and its offering stay open with UC-1's menu, and the entry takes the document as given;
     - the entry applies the 1-to-5 offering.
     Weigh both. Choose one only if the chosen reading contradicts no owner sentence and needs no value the owner has not given.
   - The same goes for the B-4 caps: applied by the entry, or left with the UI.
   - UC-1 step 1 lists inputs such as the autonomy mode, the gate configuration and injected hypotheses. The entry does not take them beyond what the document of ADR-0076 holds. The record says that this decides nothing about them.

4. **Stop conditions.**
   - If the owner-sentence reading of criterion 3 cannot be made without choosing something only the owner may choose, stop. This covers a value or policy of the initial UI, the MVP scope (C-6) and data governance (OD-25). Write nothing on `main`. Return BLOCKED with the reason `owner-only-decision` and a question with lettered options that the driver can record as an HQ (DRIVER §8).
   - Likewise stop if any point (a) to (e) turns out to need a data-plane change. That means a new member, file, kind or version, and is a BLOCKED reason under A-13. This record should need none.

5. **Consequences of the record.**
   - **The code slice for the planner.** Code mode, within the D4 cap. Name the module, a test file, tests with fixtures and temporary data roots only, and no `claude`, container or board (D16).
   - **Runtime acceptance items.** None is expected, because the entry starts no `claude`. If the record finds one anyway, number it after the last item on `main`. Search `ARCHITECTURE/decisions/` for the highest numeral; ADR-0137 ends at (lxxiv). Also say that the driver raises its HQ.
   - **"Less exact, not edited" list.** It comes from a search of `ARCHITECTURE/decisions/`, `hilclaw/` docstrings and `README.md`. Search for "binds no caller", "Its caller is not decided", "Who performs the start", "start component" and "what writes `instance.json`", and say that the list is not claimed complete. It includes at least:
     - ADR-0115 decision 1 and Boundaries;
     - the `hilclaw/start_instance.py` docstring sentence "it binds no caller (OD-23, UC-1) … has no command-line or MCP entry".
     These are not edited here. The docstring is the code slice's to fix.
   - **The A-13 reading.** Document mode, no data-plane change, nothing required of the development machine.
   - **UsageCases and StandardScenarios.** State whether any sentence becomes false. UC-1 step 2's "시스템이" stays true of the entry calling the function.

6. **Register and proposals.** Apply the recording rules written in those files themselves. Do not copy wording from earlier task files.
   - `ARCHITECTURE/Requirements.md`: follow the "행 형식" paragraph (line 84). The OD-23 row gains one link to ADR-0155 under `**확정분**:`, with a topic of a few words. The open part this record answers, the "instance의 시작을 무엇이 부르는지" clause of `**잔여**:`, is rewritten in place: removed, or narrowed to what stays open, such as the caller outside the first case, a UI, or a CI through `claude -p`. The OD-8 row is edited in the same way only if the record answers part of sub-question ⑰'s first part that the row names. The status cell keeps `논의중` or `제안됨` as it is, because OD-23 and OD-8 are not closed. There is no dated paragraph and no restatement of the record.
   - `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's "기록 규칙" (line 8). § OD-23 gains one `**채택분**` line linking ADR-0155, and its remaining-open text is rewritten in place where this record answers it. Under § OD-8, the ⑰ sub-question line, or the ADR-0115 entry on line 126, gets the same treatment only where ⑰'s first part is answered for the first case. There is no restatement of the record and no dated paragraph.
   - `ARCHITECTURE/StandardScenarios.md`: re-check S0, S1 and S2 by §검사 규칙. Record the result as the first paragraph of §검사 결과 prescribes, which means a history entry only if a verdict changes.
   - `ARCHITECTURE/UsageCases.md` is edited only if a sentence becomes false. In that case it counts as the fifth file and is named in Result.

7. **Procedure.**
   - Follow dev-item-address in document mode. Work on branch `claude/T-0426-adr-first-case-instance-start-command-line`.
   - Run the isolated reviewer cycle (dev-code-review) to Approve, at most 7 rounds.
   - Rebase on `origin/main` and push to `main` directly, without a PR. The commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0426`.
   - After landing, post the DRIVER §9 owner notice on #5. It names ADR-0155, the OD-23 part it settles and the 7-day objection period, and ends with the driver footer of DRIVER §8. Put its URL in Result.

## Out of Scope

- **Any code.** That means `hilclaw/`, `tests/`, `orchestration/` and `.claude/`. The entry itself is the next code task.
- **The start's other open parts:**
  - where values come from, ⑱, ⑳ and ㉛ (owner and project, OD-25 adjacency);
  - the first `STATE.json`, which is the Round-Manager's per ADR-0120;
  - an event line for the start, OD-8 ⑧;
  - a given run id, beyond ADR-0111.
- **A UI, a menu, the autonomy mode, gates (OD-3), injected hypotheses at the start (HQ-0031), and a CI start through `claude -p` (S2).**
- **Making the start a registry tool or giving an agent the start.** ADR-0115 decision 3 leaves this to a later record. It is weighed here only as an alternative.
- **The less-exact sentences of criterion 5.** They are listed, not edited.

## Follow-ups

- (planner) If ADR-0155 lands, its code slice is the next task. It adds the command-line entry, its test file, and the docstring fix of `hilclaw/start_instance.py`. It is code mode, uses stubs and temporary data roots only, and comes under PLAN P2-5.
- (planner) After that, the P2-13 joining task of ADR-0153 slice 1 (T-0423 Follow-ups) stays the candidate, unless an HQ answer reopens a round-loop item first.

## Result
- **Outcome**: DONE. ADR-0155 landed on `main` in document mode (reviewer agent, 5 rounds, Approve; rounds 1-4 approved with non-blocking/nit findings, all fixed on the branch; round 5 approved with no finding).
- **Record**: `ARCHITECTURE/decisions/ADR-0155-od23-first-case-instance-start-command-line.md`. A person or a script starts a first-case instance with `python -m hilclaw.new_run <file>` (new module `hilclaw/new_run.py`, not a registry tool): one argument, the path of a file holding the JSON document, no option, nothing from standard input; the parsed object goes to `hilclaw.start_instance.start` unchanged; the data root comes from `data_root_source.obtain(configured)`; one compact JSON line with `outcome`, status 0 only for a started run, every refusal/stop/input/data-root failure told apart (words, member names other than those fixed, and status numbers are the code task's). The starter goes on with `python -m hilclaw.turn_start <run_id>`; the two are not joined, and the turn loop does not call the start. The entry is not the "initial UI" of #5 A-9 and applies neither the 1-5 range nor the B-4 caps (OD-8 ㉕ (가) unchanged).
- **Register/proposals**: Requirements OD-8 and OD-23 rows (one `확정분` link each, `잔여` narrowed to UI/agent/`claude -p` CI callers; OD-8 status date range to 2026-10-24, status words unchanged); OpenDecisionProposals OD-8 (채택분 line, ⑰ partial answer and remainder, "제안으로 남는 부분" clause) and OD-23 (채택분 line). StandardScenarios: S0, S1, S2 re-checked, no verdict change; only the "최근 재검사" line updated. UsageCases not edited (no sentence became false).
- **Runtime acceptance items**: none; no HQ needed.
- **Follow-ups (planner)**: the code slice of ADR-0155 Consequences — `hilclaw/new_run.py`, `tests/test_new_run.py` (fixtures and temporary data roots only, no `claude` or stub), and the docstring fix of `hilclaw/start_instance.py`; code mode, PLAN P2-5. Then the P2-13 joining task of ADR-0153 slice 1, as the task's Follow-ups say.
