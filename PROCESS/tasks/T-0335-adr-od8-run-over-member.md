---
id: T-0335
title: Write ADR-0121 — the STATE.json member that says a first-case run is over, its writer and moment, and when a run that states a round budget is over on it (rest of OD-8, part of OD-19, OD-8 sub-question 29 (ga) for the runs of ADR-0120)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-1, FR-3, OD-8, OD-19, S0, S1, S2]
dependsOn: [T-0333, T-0334]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18). This task is one slice of it.

It is also needed for P2-5, the near goal. The P2-5 run is `cpu_standin` × GEMM, N=1, 5 rounds. That run can only end if something says that it is over, and today nothing does:
- ADR-0012 decision 3 says that `round` does not tell "whether a turn runs at all … that the run is over, stopped or waiting is said by members this record does not define".
- ADR-0118 decision 3 leaves step 1 of the turn loop undefined. Until a record answers, `hilclaw.turn_loop.run` takes a predicate from its caller (T-0330), and the loop has no command-line entry.
- ADR-0120 decision 4 answers only the fresh run directory. Its Boundaries and the Follow-ups of T-0332, T-0333 and T-0334 name "the member that says a run is over, stopped or waiting (rest of OD-8, OD-19)" as what the full step-1 predicate and the loop's entry wait on.
- ADR-0032 records `round_budget` in `instance.json`, but nothing compares anything with it. What counts against it (round 0? which number? at which moment, by what?) is OD-8 sub-question ㉙ (가), which goes with OD-19.

The D18 priority rule therefore does not set this aside. P1 has nothing plannable:
- P0.5-4 waits on the owner's hook registration.
- The rest of P1-1 waits on HQ-0021, HQ-0025, HQ-0026 and OD-14 ①.
- P1-8's D18 completion criterion is the driver's to tick.

The other P2-1 prerequisites are less ready:
- how the Round-Manager reaches `replace` (OD-23, OD-18);
- OD-8 ⑪ (the commit step);
- OD-18 ⑯ (가) (the self-check in round 0).

This end condition comes first because every run, P2-5's included, needs it before it can finish.

OD-8 and OD-19 are design-level ODs and not on the owner-only list of DRIVER §9. This task writes the ADR that closes the first-case part of them by the §9 path. Gates and "waiting at a gate" (OD-3, #5 A-5) are owner-only and stay out.

The ADR is a document; the code that follows from it (the reader of the member and the loop's step-1 predicate) is a later task. ADR-0121 is the next free number on `origin/main`; ADR-0112 is held by the unlanded branch `claude/T-0318-od30-injected-system-distribution`.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0335` trailer, size cap;
  - §9 (lines 142-149): the ADR path and the owner notice on #5.
- `CLAUDE.md`, these rules: "미결은 발명하지 않는다", "세션 진입 점검", "문서 커버리지 재검사", "브랜치·merge 절차" (document mode and the BLOCKED reasons, among them the data-plane schema change), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `PROCESS/PLAN.md`: P2-1 and P2-5 (the "5라운드" of the first run).
- `ARCHITECTURE/Requirements.md`:
  - FR-1 (line 19) and FR-3 (line 21);
  - the "행 형식" paragraph (line 84);
  - register rows OD-8 (line 99), OD-17 (line 108), OD-18 (line 109), OD-19 (line 110), OD-23 (line 114).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header, in particular its "기록 규칙" bullet (line 8);
  - § OD-8 (lines 87-164), in particular sub-questions ⑩-⑬ (search "⑩ run의 첫"), ㉙ (line 144) and ㉚ (line 145);
  - § OD-19 (lines 349-357);
  - § OD-28 (lines 424-433).
- `ARCHITECTURE/StandardScenarios.md`:
  - §검사 규칙 (lines 13-26);
  - S0, S1 and S2 (lines 30-75);
  - the first paragraph of §검사 결과 and the "최근 재검사" line (lines 168-172);
  - the S0, S1 and S2 rows of the verdict table (lines 186-189; S1 step 7 and S2 steps 2 and 5 point at OD-19 and ㉙).
- `ARCHITECTURE/UsageCases.md`: UC-1 (line 69), UC-2 (line 79), UC-3 (line 93) and UC-4 (line 106), for how a run ends or stops for a user.
- Accepted records:
  - ADR-0001 "Record format" (from line 146), the format to follow;
  - ADR-0004: the path table and the writer of `STATE.json`;
  - ADR-0011 decision 5 (the `phase` marker, lines 72-78) and decision 9 (lines 109-118);
  - ADR-0012: decisions 2, 3 and 6 (lines 29-56, 82-91), the version rule for top-level members in decision 2, and Boundaries (lines 142-152);
  - ADR-0032: decisions 2, 4 and 5 (lines 33-41, 55-73) and Boundaries (lines 160-172);
  - ADR-0033 decision 5, only to keep the wall-clock budget out of scope;
  - ADR-0076 decision 1 (lines 25-30);
  - ADR-0118 decision 3 (lines 67-90), Walk-through (lines 124-135) and Boundaries (lines 186-201);
  - ADR-0119 decision 1 (lines 35-39) and Boundaries (lines 115-128);
  - ADR-0120 decisions 1-4 (lines 38-69), Consequences (lines 92-121) and Boundaries (lines 122-136).
- Code, read only (this task changes no code):
  - `hilclaw/run_state_file.py`, what it accepts at the top level;
  - `hilclaw/turn_loop.py`, how step 1 asks the caller's predicate;
  - `hilclaw/fresh_run.py`;
  - `hilclaw/instance.py`, how `round_budget` is read today.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md).
   - Run `gh pr list`. Read issues #4, #5, #7 and #8, looking for run end, round budget and run status.
   - Open Draft PR #186 (T-0324) touches only `hilclaw/` and `tests/`, none of this task's files.
   - Stop and report if an open PR edits any of these:
     - the OD-8 or OD-19 row;
     - § OD-8 or § OD-19;
     - the S0, S1 or S2 rows;
     - the "최근 재검사" line.
   - Check with `git ls-tree` that `ADR-0121` is free on `origin/main` and on every remote branch. If it is taken, take the next free number, rename the file and its touchesFiles entry, and say so in Result.

2. **Owner-sentence search, before writing any decision.**
   - What to search: #4 (body and comments), the comments of #5 without the "posted by driver" marker, #7 and #8.
   - Search terms, English and Korean: budget, round budget, rounds, end, over, stop, terminate, status, 라운드, 예산, 종료, 끝, 중단, 소진.
   - List in Status the sentences that touch the points. Quote each for what it says and no further. They include #5 B-4 "budget 5–10 rounds" (as ADR-0032 quotes it), FR-3 "소진 → 종료" and P2-5's "5라운드".
   - Say whether any of them says if round 0 counts against a round budget.
   - **Write no ADR and return BLOCKED (`requirement-unclear`) with the question** in these cases:
     - an owner sentence decides a point differently from every answer you would give;
     - an owner sentence reads two ways about whether round 0 counts, and no answer holds under both readings;
     - the choice needs an owner-only item: #5 A/B, C-6, OD-25 or OD-3 (gates and "waiting at a gate" are OD-3).

3. **New `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`**, in the ADR-0001 record format and in English.
   - Sections: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References.
   - Mark each sentence as cited (source named) or as this record's own.
   - Scope: **the runs of ADR-0120 decision 1** (first-case new runs of ADR-0076 decision 1, started by the function of ADR-0115 and run by the turn loop of ADR-0118). Runs outside it, and continued or branched runs (OD-8 ①), are named in Boundaries.
   - It decides these points, and names in Boundaries each part it does not decide.
     - **(a) The member that says the run is over.**
       - It is a top-level member of `runs/<run_id>/STATE.json`: its name, its form and the values this record defines.
       - It defines at least the value for "over". It defines no value for "stopped" or "waiting".
       - It says how a later record adds such values. The Alternatives name the cost of this form against a later "stopped", "waiting" or "paused" (UC-2 gate, user's word, OD-19's rate-limit pause proposal).
       - It must not reuse or collide with `phase` (ADR-0011 decision 5; OD-29, OD-23) or with names the draft of #4 left to open decisions (`gate_status`, `next_action`, `best_ref`, `lock`).
       - It says what a file without the member means for a run of this scope.
     - **(b) Its writer and moment.**
       - Who writes it and in which write: the write that ends a round (ADR-0012 decision 6), or a write of its own.
       - What `round` and `budget_spent` hold in that write.
       - Whether a run that is over can be written again, and by what.
       - The single writer of ADR-0004 (Round-Manager only, treated as an owner sentence by ADR-0120) holds unless the record says why not; Alternatives weigh the turn loop and the start function, as ADR-0120 did.
     - **(c) When a run of this scope that states `round_budget` is over on it** (㉙ (가), for this scope):
       - whether round 0 counts;
       - whether a round that is cut short or given up counts, or that stays open;
       - which number is compared with the budget (the `round` of `STATE.json` or another count), at which moment and by what.
       - Show with a worked example what a `round_budget` of 5 means in rounds run, set against P2-5's "5 rounds".
       - Every other end of a run stays open (Boundaries): wall-clock (㉚), tokens (#5 A-8), the target metric reached early (#5 A-4, OD-1), the user's word (UC-2), a no-progress breaker and non-convergence (OD-19, UC-7), and a round 0 with no attempt that can stand (ADR-0119 decision 5).
     - **(d) What the turn loop's step 1 concludes from the member** for a run of this scope: the run that is over gets no further turn. Combine this with ADR-0120 decision 4 (fresh directory: a further turn). Say exactly which directory and file states the predicate now answers. These stay open:
       - a failed turn (OD-10, OD-17, OD-19, OD-27);
       - a run whose file states no round budget (㉙ (나));
       - the lock of two loops;
       - ⑪ (the commit is still owed).
   - **Data plane: version 1 and its acceptance unchanged.**
     - The member may be absent, and `schema_version` stays `1` by ADR-0012 decision 2's rule.
     - No other file, kind, member or version of the data plane is added or changed.
     - If the decision needs a required member, a version raise, or a change to `instance.json` or `events.ndjson`, write no ADR and return BLOCKED (`data-plane schema change`).
   - Consequences:
     - Search `ARCHITECTURE/decisions/` for "over, stopped or waiting", "㉙" and "round_budget". List the accepted records whose sentences are now less exact as integrator follow-ups; do not edit them.
     - Name the code slice the decision enables (the reader of the member, the loop's step-1 predicate and the loop's command-line entry) and what that slice still waits on.
     - Say whether that slice changes what `hilclaw/run_state_file.py` accepts. If it does, that is a change of the STATE schema in the sense of ADR-0012 Consequences and CLAUDE.md A-13; say so, so that the driver can plan it with the owner.
     - List runtime acceptance items only if any exists (D16).
   - About 150-220 lines. No dated paragraphs.

4. **`ARCHITECTURE/Requirements.md`, the OD-8 and OD-19 rows only**, edited by that file's "행 형식" rule (line 84):
   - add one 확정분 link per row;
   - rewrite each row's 잔여 in place;
   - mark the OD-19 status cell as a partial answer by the §9 path with the 7-day objection period, as the OD-8 cell already does.
   - Edit no other row and no FR text.

5. **`ARCHITECTURE/OpenDecisionProposals.md`, § OD-8 and § OD-19 only**, edited by the "기록 규칙" bullet of that file's header (line 8):
   - one 채택분 line in each section;
   - ㉙ rewritten in place (its status word and its end state "→ 부분 답: … 남음: …");
   - in § OD-19, the "본 항목에 남는 것" sentence rewritten in place to drop what the ADR answers.
   - Touch ⑩, ⑪ or ㉚ only where the new ADR answers part of them, and say which in Result.

6. **`ARCHITECTURE/StandardScenarios.md`** (CLAUDE.md "문서 커버리지 재검사").
   - Re-check S0, S1 and S2 by §검사 규칙.
   - Record the result as the first paragraph of §검사 결과 prescribes.
   - In the S0, S1 and S2 rows, change only the OD pointers that the ADR narrows (for example S1 step 7 and S2 step 5).

7. **Scope.**
   - `git diff --stat origin/main` lists only touchesFiles, plus this task file's Result.
   - No edit to any of these: FR or NFR text, UsageCases, earlier ADRs, `orchestration/`, `hilclaw/`, tests, CI, `.claude/`, `CLAUDE.md`, README, other `PROCESS/` files.
   - No new dependency.

8. **D16.** Neither the executor nor the reviewer starts `claude` (no subcommand, no flag). Nothing here needs a board, an accelerator or an API key.

9. **Merge (document mode, CLAUDE.md A-13).**
   - Branch `claude/T-0335-adr-od8-run-over-member`.
   - Context-isolated reviewer cycle (dev-code-review), at most 7 rounds, until Approve.
   - Rebase on `origin/main`. Push to main with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0335`.
   - Then post the OD-8 and OD-19 notice on #5 (DRIVER §9; its last line is `— posted by driver`) and put its URL in Result.

## Out of Scope

- Code: the reader of the member, the loop's step-1 predicate and command-line entry, the round-0 text of `orchestration/round-manager.md`, and `hilclaw/start_instance.py` of Draft PR #186.
- Values for "stopped", "waiting" or "paused".
- Gates (OD-3, owner-only).
- The rest of OD-19: per-round and coder-call caps, the single ledger, the circuit breaker, the rate-limit pause.
- ㉙ (나) and (다), ㉚, OD-8 ⑪ and ⑫, OD-17's lock, OD-18 ⑯ (가), and HQ-0032's question.
- Edits to earlier ADRs that this record makes less exact.
- Anything in PLAN's 보류 section, and anything blocked by HQ-0021..HQ-0029, HQ-0031, HQ-0032 or HQ-0034.

## Follow-ups

- The code slice: read the member, put the loop's step-1 predicate together with `hilclaw.fresh_run.is_fresh`, and add the loop's command-line entry. It is tested only against a stub `claude` (D16). If it changes what `hilclaw/run_state_file.py` accepts, the driver weighs the A-13 schema-change rule first.
- The remaining P2-1 slices: OD-18 ⑯ (가), OD-8 ⑪, how the Round-Manager reaches `replace` (OD-23, OD-18), then the round-0 part of the Round-Manager prompt.

## Result

- **Outcome**: ADR-0121 written (`ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`); OD-8 and OD-19 register rows, § OD-8 (one 채택분 line, ㉙ end state) and § OD-19 (one 채택분 line, "본 항목에 남는 것") updated; StandardScenarios S0/S1/S2 re-checked (no verdict change, no gap; S1 step 7 and S2 step 5 pointers narrowed; "최근 재검사" line rewritten).
- **Session entry check**: `gh pr list` showed only Draft PR #186 (T-0324; `hilclaw/start_instance.py` and tests), which touches none of this task's files. `ADR-0121` was free on `origin/main` and on every remote branch (`git ls-tree`).
- **Owner-sentence search** (#4 body + 6 comments; #5 body + 38 of 191 comments without the driver marker; #7 2; #8 6): no owner sentence names the member, its writer, or whether round 0 counts. Touching sentences are listed in the ADR's Status (O1 #5 B-4 "budget 5–10 rounds" caps; O2 #5 A-3; O3 2026-10-15 items 2-3; O4 2026-10-01 item 4; #4 §1 draft; #5 A-5/A-8 open). O1 reads two ways about round 0; the adopted answer (round 0 counts; over when `round` >= `round_budget`) never runs more rounds than stated, so it holds under both readings — not BLOCKED.
- **Decisions**: (a) top-level `run_status`, string, one value `"over"`, may be absent, `schema_version` stays 1, validator unchanged; unknown/other values make readers stop (no turn) and report. (b) Round-Manager writes it in the write that ends the last round (`round` = budget, fold as usual); one own-write case (no member, `round` >= budget at turn start); an over run is not written again. (c) round 0 counts; compared number is `round`; cut-short rounds count once when they end. (d) step-1 table P1-P4; other states fall back to the caller's predicate.
- **Sub-questions touched**: only ㉙ (가) (partial). ⑩, ⑪, ⑫ and ㉚ not edited; ⑪ gains a noted consequence in the ADR (a run that is over whose commit is owed gets no further turn).
- **Data plane**: one optional member; no version raise, no change to what `hilclaw/run_state_file.py` accepts, so the follow-up code slice is not a STATE schema change.
- **Follow-ups** (integrator, not edited here): less-exact sentences in ADR-0011 (stays exact), ADR-0012, ADR-0032, ADR-0033, ADR-0117, ADR-0118, ADR-0119, ADR-0120 (listed in ADR-0121 Consequences); § OD-28 "round budget 계상 — ADR-0032·OD-8 ㉙" in its 남음 list; the `hilclaw/turn_loop.py` docstring. Code slice: reader of `run_status`, step-1 predicate P1-P4 with `fresh_run.is_fresh`, loop CLI entry (stub `claude` only).
