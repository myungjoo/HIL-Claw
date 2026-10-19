---
id: T-0343
title: Write ADR-0125 — where the runtime self-check runs in the bring-up of a first-case run, what follows each of its results, and whether it runs again when the turn loop is started again on the same run (OD-18 sub-question 16 (ga), for the runs of ADR-0120 decision 1)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-1, FR-10, C-7, OD-18, OD-23, OD-19, OD-10, UC-1, UC-4, S0, S1, D16]
dependsOn: [T-0338, T-0341, T-0342]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0125-od18-self-check-in-round-zero.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-1 ("Round-Manager prompt and the round-0 (bring-up + baseline) procedure") is the first unchecked item in the P2 order (D18). This task is one slice of that item. The D18 rule for work outside the checklist does not apply to it. P2-5 (`cpu_standin` x GEMM, N=1, 5 rounds) needs it: PLAN P1-9 says the runtime self-check "runs in the instance bring-up ... P2-1 round 0 calls it". The owner's answer to HQ-0006 (quoted as O1 to O8 in ADR-0054) says the same. No record yet says which component runs the check for a first-case run, or when it runs relative to the instance start (ADR-0115) and the first round-0 turn (ADR-0118, ADR-0120). No record says what happens after five of its seven outcomes.

ADR-0054 decision 6 ("What follows an outcome") fixes two results, both from the owner: `not_logged_in` stops, and `front_refused` fails the bring-up. It then says: "What round 0 does after any of the other five — `passed` included — is PLAN P2-1's and is not decided here (sub-question ⑯ (가))". ADR-0057 Boundaries reads (가) as also covering exit status 20 (a fault of the check, which comes with no report). Sub-question ⑯ (가) of OD-18 also asks "whether the check runs again at a resume or at a round boundary". `hilclaw.turn_start` (T-0338) can be started again on a run that already has a `STATE.json` after the loop returned (ADR-0122), so the first-case runs meet this question too. ADR-0118 (Boundaries) and ADR-0119 (Boundaries) both list "the self-check in round 0 (OD-18 ⑯ (가))" as open.

This is a design-level choice under OD-18 (not on the owner-only list of DRIVER §9: it needs none of #5 A or B, C-6, OD-25 or OD-3). So the task writes the ADR (DRIVER §6, §9). Two neighbouring points stay owner-open and must not be decided: where the record of the check is stored (O7), and the credential form for unattended runs (O8). Open HQs checked: HQ-0016 and HQ-0019 are non-blocking runtime-acceptance notices on ADR-0054 and ADR-0057 and do not decide this point. No other open HQ (HQ-0013 to HQ-0038) touches it.

The record decides the design. It writes no code. The code slice (the component that calls `hilclaw.selfcheck.check` and the stub-`claude` tests) is a later task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, size cap), §8 (HQ, reason `runtime-acceptance`) and §9 (OD closing authority, owner notice).
- `CLAUDE.md`, "상시 규칙": "미결은 발명하지 않는다", "세션 진입 점검", "문서 커버리지 재검사", the three-layer model, "개발 드라이버와 런타임의 구분" (D16), and the document-mode branch/merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, the "Record format" section.
- `ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md`: Context (the owner sentences O1 to O8), decisions 1, 2, 6, 7, 8 and 10, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0057-od18-runtime-self-check-as-landed.md`: decision 1 (command, `check()`, time limits, exit statuses, report members), decision 4, the "For P2-1" bullet of Consequences, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: decisions 1 to 4 and 6, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`: decisions 1 to 4. `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`: decision 5. `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: decisions 1 to 6 and Boundaries (what the starter is told, and the outcomes of `turn_start`).
- `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`: decisions and Boundaries (the start function; its caller is open).
- `ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md`: decision 1 (the scope of runs that start from their own round 0) and Boundaries.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`: the whole file. It is the closest model for the shape of the new record. Do not copy its wording.
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8); § OD-18 (line 271 onward), especially the ADR-0054 sub-question ⑯ bullet and the ADR-0118 adopted line; § OD-10 and § OD-19 (only the parts on failure, retry and stopping).
- `ARCHITECTURE/Requirements.md`: the register's "행 형식" paragraph (line 84) and the rows OD-10, OD-18 and OD-19.
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과 (the 기록 규약, line 170), the "최근 재검사" line, and the S0 and S1 rows of the judgement table.
- `ARCHITECTURE/UsageCases.md`: UC-1 (the precondition ADR-0054 decision 8 stated there) and UC-4 (resume).
- Code, as observation only: `hilclaw/selfcheck.py` (module docstring, `check`, `main`), `hilclaw/selfcheck_report.py` (outcome names, exit statuses), `hilclaw/turn_start.py` (module docstring: one start, step 1, what the starter is told), `hilclaw/turn_loop.py` (module docstring), `hilclaw/further_turn.py` (states P1 to P4), `orchestration/round-manager.md`.
- Issue #5, the HQ-0006 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858 (the source of O1 to O8).

## Acceptance Criteria

### Before editing

1. Run the session entry check of CLAUDE.md: `gh pr list`, and issues #4, #5, #7 and #8. PR #186 (T-0324) touches only `hilclaw/start_instance.py` and its tests. If any open PR edits a file in `touchesFiles`, stop and return BLOCKED (open-PR conflict risk).
2. Search for owner sentences on the point: #4 body and comments, #5 comments without the "posted by driver" marker, #7, #8. Use terms such as self-check, selfcheck, 자체 점검, bring-up, 라운드 0, round 0, 재개, resume, 로그인, login, auth, front, 중단, stop. Record in Status what was searched and every sentence found that touches the point, each read for what it says and no further. **If an owner sentence decides a part of the point, cite it and do not decide against it. If a part turns out to need an owner-only decision (#5 A or B, C-6, OD-25, OD-3, or O7/O8 of ADR-0054), leave that part open in Boundaries. If the core of the point needs one, stop and return BLOCKED with the question (DRIVER §9).**

### The record `ARCHITECTURE/decisions/ADR-0125-od18-self-check-in-round-zero.md`

3. It follows the ADR-0001 "Record format". Status states that the record was accepted under DRIVER §9 (D6), separates cited sentences from the record's own, gives the owner-sentence search, names the records it builds on with "if reverted, revisited", and states the 7-day owner objection window.
4. Scope: the runs of ADR-0120 decision 1 (first case, started from their own round 0). Every other run stays outside and is named in Boundaries.
5. It decides **which component of the runtime runs the self-check** for these runs, and **at which point**: relative to the instance start of ADR-0115, to `hilclaw.turn_start` and its step 1, and to the first round-0 turn session. It gives reasons and lists at least two rejected alternatives in an Alternatives table. Examples: the start function; `turn_start` before the first turn while the run is fresh (P1); the Round-Manager of the round-0 turn; the starter by hand. Whatever it chooses must be a layer-2 or layer-1 component that already exists or is named for a later code task. It must not need any new data-plane member, file, kind, value or version (if it would, stop and return BLOCKED: data-plane schema change, CLAUDE.md A-13).
6. It decides **what follows each result** of the check for these runs, in one table. The table covers the seven outcomes of ADR-0054 decision 6, exit status 20 of ADR-0057 decision 1, and a check that ends with no readable status (120, killed, interrupted). Each row says whether a round-0 turn is started and what the starter is told. The two owner rows (`not_logged_in` stops; `front_refused` fails the bring-up) are cited, not changed. For `no_call` and `session_failed` (which ADR-0054 says say nothing against the front), the record states its reading and gives the reason. If it changes the set of outcomes of `turn_start` (ADR-0122 decision 5), it says so plainly as a requirement on the later code task. It must not edit ADR-0122.
7. It answers, or leaves open with a reason in Boundaries, each half of the rest of ⑯ (가): (i) whether the check runs again when `turn_start` is started again on a run of the scope that is not fresh (P4, a `STATE.json` exists), and (ii) whether it runs at a round boundary (between turns of one start). It must not decide recovery of open steps (OD-10, OD-17), the usage-limit pause (OD-19), or a login that expires during a run (⑯ (바)).
8. It states how the report of the check reaches the starter as process output only. It decides nothing about **where the record of the check is stored** (owner-open, O7) and defines no "instance's log" beyond what the record needs (⑯ (나) stays open unless the record answers it fully without a data-plane file). It decides nothing on ⑯ (다), (라), (마) or (바), or on O8.
9. It has a Walk-through table: P2-5 with a pass; `not_logged_in`; `front_refused`; one of the five other outcomes; status 20; a second start of `turn_start` on the same run. Each row cites the decision that gives it.
10. Consequences: the sentences of earlier records that become less exact are listed but not edited (for example ADR-0054 decision 6, ADR-0057 Consequences "For P2-1", ADR-0118 and ADR-0119 Boundaries, the `orchestration/round-manager.md` placeholder). The A-13 reading says document mode, no data-plane change. List any new **runtime acceptance items** (facts only a real logged-in `claude` on a runtime machine can confirm). The driver raises them under DRIVER §8, reason `runtime-acceptance`; this task raises no HQ itself. Boundaries lists every part left open, with its OD or sub-question.
11. No `claude` process, compiler, `hilclaw.selfcheck` or `hilclaw.turn_start` is started for this record (D16). State that in Status.

### The register, proposals and coverage edits

12. `ARCHITECTURE/Requirements.md`: follow the register's "행 형식" (line 84). In the OD-18 row, add one link to ADR-0125 with a few words of topic after `**확정분**:`, and rewrite `**잔여**:` in place so that it says what of ⑯ is left. Touch another row (OD-19, OD-10, OD-23) only if the record actually answers a part of it, in the same way. Do not restate the record, and do not add a dated paragraph.
13. `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's "기록 규칙" (line 8). In § OD-18 add one `- **채택분** [ADR-0125](…) — …` line. At the end of sub-question ⑯ set the state (`→ 부분 답: [ADR-0125]…. 남음: …`) and change the bullet's head state word in place. Keep the question's wording. Change the ADR-0118 adopted line's "⑯ (가)는 답하지 않음" only if it has become wrong. Do not copy register text.
14. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the rules of that file (CLAUDE.md "문서 커버리지 재검사") for at least S0 and S1. Follow the first paragraph of § 검사 결과: update the "최근 재검사" line in place. Add a "판정 변화 이력" entry only if a judgement changed or a gap was found or closed. In the judgement-table remarks, write only FRs and still-open ODs.
15. Size: within the DRIVER §5 cap (≤ 300 changed lines excluding tests, ≤ 5 files).

### Commit and landing

16. Document mode (CLAUDE.md A-13): work on branch `claude/T-0343-adr-self-check-in-round-zero`, pass the context-isolated reviewer cycle (dev-code-review), rebase on `origin/main`, and push to `main` directly with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0343`. Never use `git push --force*`. After landing, post the OD notice on issue #5 (DRIVER §9) and fill `## Result`.

## Out of Scope

- Any code: the component that calls the check, changes to `hilclaw/turn_start.py`, `hilclaw/selfcheck*.py`, `orchestration/round-manager.md`, tests or CI. These belong to the follow-up code task.
- The round-0 steps of the Round-Manager beyond the check (coder call, baseline measurement, the first `STATE.json` contents), the commit step (OD-8 ⑪), and folding the spend view (OD-23).
- Where the check's record is stored and the credential form for unattended runs (owner-open, ADR-0054 O7/O8). ⑯ (나) to (바).
- Editing any earlier ADR, FR/NFR text, UsageCases, `.claude/`, CLAUDE.md or the `HIL-Claw-data` repository.
- Starting `claude` in any form (D16).

## Follow-ups

- The code slice of ADR-0125: wire `hilclaw.selfcheck.check` into the chosen component, with stub-`claude` tests only (D16).

## Result

- **Outcome**: DONE. Document mode; landed on `main` as one commit with the trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0343` (the hash is in the driver's state commit and journal).
- **Files**: `ARCHITECTURE/decisions/ADR-0125-od18-self-check-in-round-zero.md` (new), `ARCHITECTURE/Requirements.md` (OD-18 row: one link after `**확정분**:`, ⑯ rewritten in `**잔여**:`), `ARCHITECTURE/OpenDecisionProposals.md` (§ OD-18: one `채택분` line; ⑯ head state 미결 → 일부 답함 and `→ 부분 답 … 남음 …`), `ARCHITECTURE/StandardScenarios.md` ("최근 재검사" line). 4 files, about 148 changed lines.
- **Decision (ADR-0125, part of OD-18 ⑯ (가), runs of ADR-0120 decision 1)**: `hilclaw.turn_start` runs `hilclaw.selfcheck.check()` in its own process once per start, after the first step 1 finds a turn due (P1 or P4) and before the first turn session; no check on P2, P3 or an open state. `passed` and `no_call` let the turn start; `no_claude`, `not_logged_in` (owner), `login_unreadable`, `front_refused` (owner), `session_failed` and a fault of the check (ADR-0057 status 20) stop the start; an interrupted or killed start writes no line. A later start on the same run checks again; nothing checks between two turns of one start. The report reaches the starter as one member of the entry's one output line; O7 (where the record is stored), O8 and ⑯ (나)-(바) stay open. No data-plane change.
- **Before editing**: open PRs: only #186 (T-0324, `hilclaw/start_instance.py` and tests), no overlap. Owner-sentence search (#4 body and 6 comments; #5 body and the 38 of 198 comments without the driver marker; #7 2; #8 6; terms as in the AC): only the HQ-0006 answer (O1, O2, O3, O7, O8) speaks of the point; PLAN P1-9 ("P2-1 라운드 0이 호출") is cited and read in decision 2.
- **Review**: context-isolated `dev-reviewer`, 7 rounds. Round 1 Request changes (blocking: "the only place the report goes" read against O7's "and the instance's log"; fixed). Rounds 2-7 Approve with non-blocking/nit findings, each fixed in the branch (P1-9 reading, ADR-0054 L5 and ADR-0122 cost sentences listed as less exact, wait-time wording, status 120, `no_claude` naming, ADR-0123 and `turn_loop.py` in the less-exact list, references, the definition of "a start"). Round 7's one nit (capitalised first letter of a quoted docstring phrase) was marked "no fix needed" and left, to stay within the 7-round limit.
- **D16**: no `claude`, compiler, `hilclaw.selfcheck` or `hilclaw.turn_start` was started.
- **Runtime acceptance item for the driver (DRIVER §8, reason `runtime-acceptance`; this task raised no HQ)**: (xvi) in the self-check series: what `claude auth status` reports for a stored login that has expired and cannot be refreshed — exit status 1 (`not_logged_in`) or 0 with an `authMethod` (the session then ends `session_failed`).
- **Follow-ups**: the code slice of ADR-0125 decision 6 (code mode): in `hilclaw/turn_start.py`, call `check()` between the first step 1 and the first turn; add the outcome "stopped at the check" (exit status not 0) and the report member; tell the check's `no_claude` apart from the entry's error `no_claude`; correct the docstrings of `hilclaw/selfcheck.py`, `hilclaw/turn_start.py` and `hilclaw/turn_loop.py`; tests against a stub `claude` only.
