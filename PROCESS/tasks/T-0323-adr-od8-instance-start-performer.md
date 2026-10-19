---
id: T-0323
title: Record an ADR on what performs the start of a first-case instance - whether one deterministic layer-2 function of the tool package builds the `run_id` and writes `instance.json` (first part of OD-8 sub-question 17, for the instances of ADR-0076 decision 1)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-13, NFR-1, OD-8, OD-23, "#5 A-12"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P1-8 (runtime STATE/instance/events schemas, "OD-8 종결 필요(§9)") is still open. Four accepted records fix what the start of a first-case instance (ADR-0076 decision 1) does:
- ADR-0076: the members it requires before the write, and its refusal;
- ADR-0025: the write procedure of `instance.json`;
- ADR-0109: the stop when the final name is taken;
- ADR-0111: the start takes no `run_id`, builds its own by ADR-0027, and gives it back.

The deterministic pieces already exist in `hilclaw/`: `instance_start.prepare`, `instance_file.write` and `run_id.new`. But no record says what performs the start. ADR-0004 gives `instance.json` to the role "The start of the instance, once". ADR-0076, ADR-0109 and ADR-0111 each say they name no component (OD-23). ADR-0109 and ADR-0111 each name a code slice and say it "waits on a start component (⑰'s first part, OD-23)". OD-8 sub-question ⑰ still lists "`instance.json`을 무엇이 쓰는지" as open. So the code that joins those pieces cannot be written yet.

This task records an ADR that answers that open part for the scope of ADR-0076 decision 1, and only at the level of the layer model of #5 A-12. The question: is the role performed by a deterministic function of the layer-2 package, by a layer-1 agent that writes the file with its own file tools, or by something else? The answer would unblock the code slices named by ADR-0109 and ADR-0111.

This is a design-level OD part. Under DRIVER §9 the executor writes the ADR, a reviewer's approval accepts it, and the driver posts the 7-day owner notice. It is no #5 A/B item and not C-6, OD-25 or OD-3. OD-23 is `논의중`, but it is not owner-only. Search #4 (body and comments) and the #5 comments that are not the driver's for any owner sentence on who writes `instance.json`, what creates a run's workspace, or whether the start is an agent's step. Search terms: instance start, instance.json, workspace, 작업공간, 시작, Round-Manager, bring-up. If an owner sentence decides the point, or reads two ways about it, stop with BLOCKED `requirement-unclear` and quote it in Result. UC-1 step 2 ("시스템이 instance용 작업공간 … 을 만들고") is a requirement sentence. Cite it, but it does not name a component.

The scope is narrow on purpose. The record answers only which **layer** and **kind of component** performs the start: one function, an agent, a hook, or another thing. These stay open, and the answer must hold whatever they turn out to be:
- who calls the start, and how the user's inputs reach it: a command-line front, a UI, the Round-Manager of PLAN P2-1, a CI (UC-1, OD-23);
- the form, moment and channel of its reports (ADR-0076 decision 3, ADR-0109 decision 3, ADR-0111 decision 3 leave these to "the code task's and the UI's");
- the order of the first files and whether the start writes `STATE.json` (⑩);
- where the start takes each value from (ADR-0076 decision 2, ⑰/⑱/⑳/㉛);
- the roster of agents (OD-23 remainder);
- the meaning of a run directory with other files but no `instance.json` (⑰'s last part).

## Required Reading

- `PROCESS/DRIVER.md`: §3 (lines 63-77, with executor steps 5-6, the naming rule and the time cap), §5 (lines 86-114), §8 (lines 135-139) and §9 (lines 141-148).
- `CLAUDE.md`: the rules "세 층 모델" (line 16), "개발 드라이버와 런타임의 구분", "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검" and "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0111-od8-run-under-given-id.md`: decisions 1-3 (lines 24-45), Consequences (lines 78-85, the code slice) and Boundaries (lines 86-97).
- `ARCHITECTURE/decisions/ADR-0109-od8-instance-start-name-taken.md`: decisions 1-5 (lines 23-56), Consequences (lines 80-86) and Boundaries (lines 87-96).
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md`: Context (lines 14-22, line 20 on OD-23), decisions 1-5 (lines 23-67), Consequences (lines 91-96) and Boundaries (lines 97-105).
- `ARCHITECTURE/decisions/ADR-0025-od8-instance-file-write.md`: decisions 1-5 (lines 21-59) and Boundaries (lines 117-128).
- `ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md`: decisions 1, 5 and 6 (lines 25-31, 57-71).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: the file table row for `runs/<run_id>/instance.json` (line 67).
- `ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md`: decision 1 (from line 23, line 30): a precedent for naming a role ("the promotion step") and leaving the agent to OD-23.
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: Context (lines 14-16) and the choice of two fronts over one registry (lines 62-66). These help the record say whether the start is a tool (ADR-0111 Consequences says it is not "by any record").
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: the "Record format" section (from line 146).
- Read only, to see what exists today: the module docstrings of `hilclaw/instance_start.py`, `hilclaw/instance_file.py` and `hilclaw/run_id.py`.
- `ARCHITECTURE/UsageCases.md`: UC-1 (lines 69-78), especially steps 1-3 and the actor "배포 엔지니어 / CI".
- `ARCHITECTURE/Requirements.md`: FR-13 (line 31), NFR-1, the "행 형식" paragraph (line 84), the OD-8 row (line 99) and the OD-23 row (line 114).
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8); in the OD-8 section, the `run_id` part of "제안으로 남는 부분" (line 124, "무엇이 언제 id를 만드는지(⑩·⑰ 첫 부분 …)") and the ⑰ bullet (line 131); the OD-23 section (lines 376-386).
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과 (from line 168), S0, S1 and S2 (CI as the actor).
- GitHub: Issue #4 (body §3a and §6, and the comments) and Issue #5 (the comments that are not the driver's), for the owner-sentence search in Why.

## Acceptance Criteria

1. Session entry check (CLAUDE.md "세션 진입 점검"): list the open PRs and read #4, #5, #7 and #8 for anything on the start of an instance or on who writes `instance.json`. If an open PR edits the OD-8 or OD-23 row, or the OD-8 or OD-23 section, stop and report it.
2. A new record `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md` in the record format of ADR-0001. ADR-0112 is on the kept branch of T-0318. ADR-0068, ADR-0074 and ADR-0088 are on the unlanded branches of T-0210, T-0231 and T-0264. Check with `git ls-tree` that ADR-0115 is free on `origin/main` and on every remote branch. If it is taken, use the next free number, rename the file and its touchesFiles entry, and say so in Result.
3. Status:
   - the record was accepted under DRIVER §9 and has not been confirmed by the owner;
   - cited sentences, quoted with their source, are kept apart from the record's own choices;
   - the result of the owner-sentence search of Why;
   - the records it builds on (at least ADR-0004, ADR-0025, ADR-0027, ADR-0076, ADR-0109 and ADR-0111), and that it is revisited if one of them is reverted.
4. Scope: the start of an instance of ADR-0076 decision 1. The record says how its answer holds while each item in the "stay open" list of Why stays open. If no answer can hold without fixing one of them, record that as a finding, leave the part open, and do not invent it.
5. The Decision answers what kind of component performs that start. Weigh at least these alternatives:
   - (a) one deterministic function of the layer-2 package. It takes the start's inputs, builds the id by ADR-0027, applies ADR-0076, ADR-0111 and ADR-0109, writes by ADR-0025 and gives the id back. Every way of starting calls it.
   - (b) a layer-1 agent (for example the Round-Manager of P2-1) composes and writes `instance.json` with its own file tools.
   - (c) a hook.
   - (d) leave it open.
   For each alternative, state what it does to the following:
   - the determinism and testability of the rules of ADR-0076, ADR-0109 and ADR-0111;
   - the A-12 split between layer 1 and layer 2;
   - a CI actor (UC-1, S2) that starts a run without an agent session;
   - NFR-1 (state survives the death of a process);
   - whether the start becomes an FR-10 tool. Say explicitly whether the record makes it one. If (a) is chosen, it is not a tool unless the record says why.
   The record may say where in `hilclaw/` such a function belongs, or leave the module and names to the code task. Either way, it does not decide its caller.
6. The record adds no member, file, kind of file, tool-failure kind or validity rule to the data plane. It changes no code, no `instance.json`, `STATE.json` or `events.ndjson`, and no agent definition or skill. Consequences carries an A-13 reading saying so. If the decision cannot be written without such a change, stop with BLOCKED (data-plane schema change).
7. Consequences:
   - name the code slice the record makes possible. Say how it joins the slices already named by ADR-0076, ADR-0109 and ADR-0111. Say what, if anything, it still waits on.
   - list, found by grep, the sentences of earlier records that become less exact (at least the "names no component" / "waits on a start component" sentences of ADR-0076, ADR-0109 and ADR-0111, where they do). Do not edit them.
   - name the runtime acceptance items, or say there are none.
   - a name check over `hilclaw/`, `tests/` and `ARCHITECTURE/`: no kind, member, `step` value, blob `type`, spend axis or reserved kind is added.
8. Boundaries list at least: the caller of the start and the input path from the user (UC-1, OD-23); the form and channel of the start's reports; ⑩; ⑰'s last part; ⑱, ⑳ and ㉛; instances outside ADR-0076 decision 1; the agent roster and per-agent allowlists (OD-23 remainder); the lock and a second writer (the rest of OD-17); OD-25. They also list any change to earlier records, `hilclaw/`, tests, CI, `.claude/`, settings files or `HIL-Claw-data`.
9. `ARCHITECTURE/Requirements.md`: follow the register's "행 형식" paragraph (line 84) as binding.
   - Edit the OD-8 row. If the record also answers part of OD-23, edit the OD-23 row too. Touch no other row.
   - In each edited row, add exactly one `**확정분**:` link to the new ADR, with a topic of a few words.
   - Rewrite in place the part of `**잔여**:` that the record answers. Do not restate the record and add no dated paragraph.
   - Change a status cell only as that paragraph allows.
10. `ARCHITECTURE/OpenDecisionProposals.md`: follow its header's "기록 규칙" (line 8).
    - Edit only the OD-8 section and, if criterion 9 touched the OD-23 row, the OD-23 section.
    - Add one adopted-record line per section touched.
    - Rewrite in place the ⑰ bullet's status tail and head status word, and the open-part sentence on line 124 ("무엇이 언제 id를 만드는지 …") if the record answers it.
    - Keep the question text, do not restate the record, and add no dated note.
11. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's own rules (CLAUDE.md "문서 커버리지 재검사"). Update §검사 결과 only as its first paragraph prescribes.
12. No other file changes. `git diff --stat origin/main` lists only the touchesFiles. `git diff --check` is clean. Every relative link added resolves. The OD register has the same number of rows before and after.
13. Document mode (CLAUDE.md A-13):
    - work on branch `claude/T-0323-<slug>`;
    - run a context-isolated reviewer cycle of at most 7 rounds;
    - rebase on `origin/main` and push directly to main;
    - end the commit message with one trailer block, with no blank line inside it, that holds `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0323`, and check with `git interpret-trailers --parse` that git parses both;
    - put the §9 owner notice text for #5 in Result, with the §8 footer. The driver posts it.
14. Start no compiler, kernel, container, test run or `claude` process (D16).

## Out of Scope

- Any code, test, CI, `.claude/` or settings change, including `hilclaw/instance_start.py`, `hilclaw/instance_file.py` and `hilclaw/run_id.py`.
- The caller of the start, its input path, the report form, ⑩, ⑱, ⑳, ㉛, the agent roster and allowlists (OD-23 remainder), the lock (OD-17), OD-20, and owner-only items (OD-25, OD-3, C-6, #5 A/B).
- Editing earlier ADRs, including the "less exact" sentences the new record lists. Also UsageCases, the README and the index documents.
- PR #179 (T-0284; it touches only `hilclaw/clang_build.py` and `tests/test_clang_build.py`). Also the unlanded branches of T-0210, T-0231, T-0264 and T-0318.

## Follow-ups

- If the record chooses (a), a code task: the start function that joins `instance_start.prepare`, `run_id.new` and `instance_file.write` under ADR-0076, ADR-0109 and ADR-0111, with tests, and with no caller bound.

## Result

- **Landed**: main `86abd39` (document mode, one squashed commit, pushed fast-forward from `716bbea`; task branch `claude/T-0323-adr-od8-instance-start-performer` deleted locally and on origin). Branch commits before the squash: `22b80dd`, `d272d51`, `87e644f`, `7b2588c`, `eadf156`, `8bd7174`, `7e1922f`. `git interpret-trailers --parse` gives `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0323` and the Co-Authored-By line.
- **Review**: 7 rounds of a context-isolated `dev-reviewer`. Rounds 1 to 3 asked for changes, one blocking finding each:
  - Round 1: the OD-8 remainder narrowed the open ⑩ order.
  - Round 2: decision 2 put a stored-record lookup (⑱) outside the function, which closed an open point.
  - Round 3: the less-exact list was incomplete against its own search terms.
  - Rounds 4 to 7 approved; the nits of rounds 4 to 6 were fixed.
  - Round 7 approved with one non-blocking finding and two nits. They were left unfixed, because a fix would need an eighth round (see Follow-ups).
- **Entry check (criterion 1)**: one open PR, #179 (T-0284; `hilclaw/clang_build.py`, `tests/test_clang_build.py`). No PR edits the OD-8 or OD-23 row or section. Landed check: before this run there was no `Task: T-0323` commit on `origin/main` and no PR for T-0323.
- **Owner sentences**: these were searched with the task's terms (instance start, instance.json, workspace, 작업공간, 시작, Round-Manager, bring-up, start of):
  - #4: body and its 6 comments;
  - #5: body and the 38 of its 181 comments without the driver marker;
  - #7 and #8: bodies and comments.

  No sentence decides who writes `instance.json`, what creates a run's workspace, or whether the start is an agent's step, and none reads two ways about it. The record quotes the closest ones for what they say:
  - #5 A-12 points 1 and 3;
  - the #4 §3a-revision agreement, conditions 2 to 4;
  - #4 §3/§3c;
  - HQ-0006 (b-2);
  - A-9, A-1 detail 3, and the 2026-10-13 decision on injection at start.
- **Record**: `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`. ADR-0115 was free on `origin/main` and on every remote branch.
  - Decision: for the instances of ADR-0076 decision 1, one deterministic function of the layer-2 package performs the start. It builds the id by ADR-0027, applies ADR-0076 and ADR-0111, writes by ADR-0025, stops by ADR-0109 and returns the id. Every way of starting calls it, and no agent writes the file with its own file tools.
  - It is no FR-10 tool (decision 3).
  - Left open: the caller, the input path, the report form, ⑩, the sources of values (⑱, ⑳, ㉛), the roster and ⑰'s last part.
  - Alternatives weighed: (a), (b) agent, (c) hook, (d) open, and (a') as a registry tool.
- **Register edits**:
  - Requirements: the OD-8 and OD-23 rows each gain one `**확정분**` link, and their `**잔여**` is rewritten in place. The OD-8 status date range is now `~19`; OD-23 stays `논의중`. The row count is unchanged at 30.
  - OpenDecisionProposals: the OD-8 and OD-23 sections each gain one adopted line. The ⑰ tail is rewritten; the head word stays "일부 답함" because ⑱ is open. On line 124, the `run_id` open-part sentence and the "쓰기와 작성자" clause are rewritten in place.
- **Coverage re-check**: S0, S1, S2 and S11 were re-checked. No verdict changed and no gap appeared. Only the "최근 재검사" line was rewritten.
- **Checks**: `git diff --stat origin/main` before landing listed only the four touchesFiles. `git diff --check` is clean. Every added relative link resolves. D16: no `claude`, compiler, container or test was started.
- **Owner notice text for #5 (DRIVER §9; the driver posts it)**:

OD-8 (P1 data-plane layout) gains an accepted part under DRIVER §9, which also settles one point of OD-23: ADR-0115 (https://github.com/myungjoo/HIL-Claw/blob/main/ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md, landed in 86abd39). The record covers the start of a first-case instance (`cpu_standin` or the mock, the instances of ADR-0076 decision 1). That start is performed by one deterministic function of the layer-2 package `hilclaw/`. The function builds the `run_id` (ADR-0027), checks the required members (ADR-0076), refuses a given id (ADR-0111), writes `instance.json` (ADR-0025), stops on a taken name (ADR-0109) and returns the id. Every way of starting such an instance calls that function. No agent composes and writes the file with its own file tools, and the function is not an FR-10 tool. The record leaves open who calls the start (a command line, a UI, the Round-Manager, a CI) and how the user's inputs reach it. It also leaves open the form of its reports, whether and when it writes the first `STATE.json`, where each value comes from, and the agent roster. Nothing in the data plane changes. You may object within 7 days of this notice; an objection creates a task that reverts the record.

— posted by driver

- **Follow-ups**:
  - Code task (the task's Follow-up): the start function. It joins `hilclaw.instance_start.prepare`, `hilclaw.run_id.new` and `hilclaw.instance_file.write` under ADR-0076, ADR-0109 and ADR-0111, binds `accelerators`/`covers`, builds the bytes and has its own tests. No caller is bound.
  - A small document task for the round-7 findings, unfixed because of the 7-round cap:
    1. Non-blocking: ADR-0115 decision 3 and the (a') row say that making the start a tool "would also choose an agent as one of its callers" / "makes an agent one of its callers". By ADR-0010 decision 3 a registry tool appears on both fronts, so making it a tool only opens a path for an agent. Suggested wording: "opens an agent's path to it, which decision 1 leaves open".
    2. Nit: in decision 2, "the stop of ADR-0109 comes at its last step" should read "at the last step of the write".
    3. Nit: the less-exact list could drop ADR-0111 Alternatives row 2 (c), a sentence about a rejected alternative.
