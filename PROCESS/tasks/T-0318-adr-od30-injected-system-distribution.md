---
id: T-0318
title: Record an ADR on the distribution of injected and system hypotheses across rounds and candidates (OD-30, "주입 가설과 시스템이 세운 가설의 배분")
phase: P1
status: BLOCKED
commitMode: doc
coversReq: [FR-15, FR-17, FR-11, OD-30, S11]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0112-od30-injected-system-distribution.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 190, files: 4}
hq: [HQ-0031]
---
## Why

PLAN P2-6 (hypothesis records and verdicts, "OD-30 종결 필요(§9)") is open. Its dependencies P2-1 and P2-3 need the selection role to know how it combines injected hypotheses with its own. Since ADR-0075 (injection at instance start), a run can hold injected inputs. ADR-0075 decision 4 and its Boundaries say that **no rule of share or order follows** from that record. They leave open: whether injected hypotheses are tested first, whether they are mixed into one round's N candidates, or whether this is left to the selection's judgement; whether every injected input must be tested, and by when; and whether every round must hold a system hypothesis. The OD-30 section of `ARCHITECTURE/OpenDecisionProposals.md` holds the same question as the bullet "주입 가설과 시스템이 세운 가설의 배분" (line 451). That bullet has no status tail yet. The planner of T-0317 named this as the next candidate.

This is a design-level part of OD-30. The executor writes an ADR, a reviewer's approval accepts it under DRIVER §9, and the driver posts the 7-day owner notice. The OD-30 section names only injection at a gate or during a run (② and ③), and their MVP inclusion, as owner questions (line 450). The distribution is not among them, and ADR-0075's Boundaries agree. One citation reads otherwise and must be checked, not followed blindly: ADR-0073 Boundaries (line 117) puts "the distribution of injected and system hypotheses" inside a parenthesis "(owner, HQ, per the OD-30 section; FR-15)". ADR-0075's Consequences list that parenthesis as less exact, reading it as covering ② and ③ only.

The owner's own words bind the answer. These are the decision of 2026-10-13 (point 4) and its addendum: "Injection must never mean that no new hypothesis is formed." and "Different cycles may test different hypotheses." FR-17 adds "주입된 가설이 있어도 시스템은 라운드마다 … 스스로 추가 가설을 세우는 일을 멈추지 않으며". The record reads these sentences; it does not widen or narrow them. Before writing, search the comments of #5 that are not the driver's (no "— posted by driver" footer), the body and comments of #4, and the S11 and FR-15/FR-17 text for sentences about order, share, priority, mixing, "first", "every round", and the Korean forms (순서, 비율, 배분, 먼저, 우선, 라운드마다). Two outcomes stop the task with BLOCKED `owner-only-decision`, with the sentence quoted in Result:
- an owner sentence reserves this choice to the owner;
- an owner sentence fixes the choice in a way that two readings could disagree on.

Unresolved HQs this task must not depend on: HQ-0023 (the S6 metric, T-0231) and HQ-0024 (the code slice of ADR-0075, T-0233). The answer must not need either of them.

## Required Reading

- `PROCESS/DRIVER.md`: §3 (lines 63-77; executor steps 5-6, the naming rule, the time cap), §5 (lines 86-114), §8 (lines 135-139) and §9 (lines 141-148).
- `CLAUDE.md`: the rules "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검" and "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0075-od30-injection-at-instance-start.md`: Status (lines 3-10), Context (lines 12-18), decisions 3 to 5 (lines 48-71), Consequences (lines 129-134) and Boundaries (lines 136-148, especially the bullet "The order and share of injected and system hypotheses", line 139).
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`: decisions 3 and 4 (lines 51-83; decision 4 holds the rule that every candidate tests at least one hypothesis and the recommendation on causal misattribution), decision 5 (lines 84-87) and Boundaries (lines 140-155, line 148 "The order and share").
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: decisions 4 and 5 (lines 68-81, shared candidates and causal misattribution) and Boundaries (lines 141-154).
- `ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md`: decision 1 (lines 25-38), decision 2 (the rule that a hypothesis resting on a case is `origin` `system`, lines 39-55) and Boundaries (lines 112-125, line 117).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: the "Record format" section (from line 146).
- `ARCHITECTURE/Requirements.md`: FR-1 (line 19, round loop and N), FR-11 (line 29), FR-15 (line 33), FR-17 (line 35), the "행 형식" paragraph (line 84) and the OD-30 row (line 121); also the OD-18, OD-23 and OD-29 rows for what enforces a rule and who selects.
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8) and the OD-30 section (lines 434-455, especially lines 450-453).
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과 (from line 168), S8 (from line 112, N candidates per round) and S11 (lines 122-136, step 3 names this question).
- `ARCHITECTURE/UsageCases.md`: UC-1 (lines 69-78) and UC-2 (lines 79-92), for the user's input and the gate.
- Owner decision 2026-10-13 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569 and its addendum https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136597638 (read with `gh issue view 5 --comments` or `gh api`).

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0112-od30-injected-system-distribution.md` in the record format of ADR-0001. Before writing, check with `git ls-tree` that ADR-0112 is free on `origin/main` and on every remote branch. The unlanded branches of T-0210, T-0231 and T-0264 hold ADR-0068, ADR-0074 and ADR-0088. If ADR-0112 is taken, use the next free number, rename the file and its touchesFiles entry, and say so in Result.
2. Status:
   - says the record was accepted under DRIVER §9 and has not been confirmed by the owner;
   - keeps cited sentences, each quoted with its source, apart from the record's own choices;
   - states the result of the owner-sentence search described in Why;
   - names the records it builds on (at least ADR-0059, ADR-0071, ADR-0073 and ADR-0075) and says the record is revisited if one of them is reverted;
   - says that OD-30 keeps its status word `제안됨`.
3. Scope: the rounds of one run whose `instance.json` holds `injections` (ADR-0075), for injection at instance start only. The record says how its answer holds while these stay open:
   - injection at a gate or during a run (②, ③, owner);
   - who derives a hypothesis from material;
   - the catalog boundary;
   - the verdict's comparison base;
   - Best-of-N beyond the MVP (OD-29).
   If no answer can hold without fixing one of them, record that as a finding, leave the part open, and do not invent it.
4. The Decision answers, for that scope, each of the open points listed in ADR-0075's Boundaries bullet (line 139):
   - (i) order: are injected hypotheses tested before system ones?
   - (ii) mixing: may one round's candidates test injected and system hypotheses together, and may one candidate test both?
   - (iii) coverage: must every injected input be tested, and by when? What happens to an input never tested because the budget ran out or the run ended early?
   - (iv) must every round from round 1 hold at least one system hypothesis?

   Weigh at least these alternatives:
   - (a) a fixed rule: injected inputs first, then system ones;
   - (b) a minimum rule only: for example, each round holds a system hypothesis, or each input is tested once before the run ends, with the rest left to the selection's judgement;
   - (c) no rule: the selection's judgement, recorded through `basis`/`origin`;
   - (d) leave it open.

   For each alternative, state what it does to:
   - the owner's addendum and FR-17's "멈추지 않으며";
   - FR-15's "탐색 우선순위 힌트" and "검증을 면제받지 않는다";
   - a run with N = 1 candidate per round (the MVP first run, PLAN P2-5) and a run with a small budget;
   - causal misattribution on a shared candidate (ADR-0059 decision 4, ADR-0071 decision 5);
   - FR-11, the decision log's identification of injected hypotheses (ADR-0075 decision 4).
5. Whatever is chosen binds the runtime's selection role (1층, PLAN P2-1 and P2-6) as a rule of conduct. It is not a rule of any file's validity. The record names what would enforce or check it (OD-18, OD-23), names no hook, module or prompt as binding, and does not decide that enforcement. If the answer can only be written as a new validity rule of `hypotheses.json`, `verdicts.json`, `instance.json` or a case file, stop with BLOCKED (data-plane schema change).
6. The record adds no member, value, file, kind of file, `basis` kind, `origin` value, event kind, `step` value or tool-failure kind to the data plane. It changes no code, `instance.json`, `hypotheses.json`, `verdicts.json`, `STATE.json` or `events.ndjson`. Consequences carries an A-13 reading saying so.
7. Consequences:
   - name the later slices the record makes possible, if any (for example, a sentence of the selection prompt of P2-1/P2-6, or a check a reader holding `instance.json` and the round files could make), with what each waits on, and name none as binding;
   - list, found by grep, the sentences of earlier records that become less exact, at least ADR-0075 decision 4's "No rule of share or order follows" and its Boundaries line 139, ADR-0059 Boundaries line 148 and ADR-0073 Boundaries line 117, if they do; do not edit them;
   - name the runtime acceptance items, or say there are none (whether a live selection follows the rule is something only a live run shows; say whether that is an acceptance item or simply a later check);
   - a name check over `hilclaw/`, `tests/` and `ARCHITECTURE/` showing that no name is added.
8. Boundaries list at least: injection at a gate or during a run and their MVP inclusion (owner, HQ); who derives a hypothesis from material and when; the catalog boundary (UC-5, OD-7, OD-24); the reference input at start that is not an injection; the verdict's comparison base and magnitude; rounds that never reach evaluate; the S6 metric (HQ-0023); the selection rule for many cases (ADR-0073); Best-of-N (OD-29); enforcement (OD-18) and the roster (OD-23); and the owner-only items (OD-25, OD-3, C-6, #5 A/B). They also list any change to earlier records, `hilclaw/`, tests, CI, prompts, settings files and `HIL-Claw-data`.
9. The edit to `ARCHITECTURE/Requirements.md` touches only the OD-30 row and follows that register's "행 형식" rule (line 84), which is binding:
   - add one `**확정분**:` link for the one new ADR, with a topic of a few words;
   - rewrite in place the part of `**잔여**:` that this record answers (the words "주입 가설의 배분"), keeping what stays open;
   - do not restate the record's content, add no dated paragraph, and leave the status cell unchanged.

   FR-15 and FR-17 stay unedited. Their "= OD-30" pointers stay true as pointers; if one becomes false, list it under Consequences and do not edit it.
10. The edit to `ARCHITECTURE/OpenDecisionProposals.md` touches only the OD-30 section and follows its "기록 규칙" (line 8):
    - add one adopted-record line for ADR-0112 after the ADR-0075 line, of the form that rule gives;
    - in the bullet "주입 가설과 시스템이 세운 가설의 배분" (line 451), add the head status word (일부 답함 or 답함) and the status tail (`→ 부분 답: [ADR-0112](…)…. 남음: …` or `→ 답함: [ADR-0112](…)`) that the rule prescribes;
    - if the "제안으로 남는 부분" bullet (line 443) names "배분" and it is now answered, rewrite that word in place;
    - keep the question text, do not restate the record, and add no dated note.
11. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's own rules (CLAUDE.md "문서 커버리지 재검사"), at least S0, S1, S8 and S11. Update §검사 결과 exactly as its first paragraph prescribes: rewrite the "최근 재검사" line in place, and add a "판정 변화 이력" entry only if a verdict changes or a gap is found or closed. Leave S11 step 3's pointer "주입 가설과 시스템 가설의 배분 = OD-30" unedited; if it becomes false, list it under Consequences.
12. No other file changes. `git diff --stat origin/main` lists only the touchesFiles. `git diff --check` is clean. Every relative link added resolves. The OD register has the same number of rows before and after.
13. Document mode (CLAUDE.md A-13): work on branch `claude/T-0318-<slug>`, run a context-isolated reviewer cycle of at most 7 rounds, rebase on `origin/main`, and push directly to main. The commit message ends with one trailer block, with no blank line inside it, holding `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0318`. Check with `git interpret-trailers --parse` that git parses both. The §9 owner notice on #5 follows, with the §8 footer.
14. Start no compiler, kernel, container or `claude` process (D16).

## Out of Scope

- Any code, test, CI, prompt or settings change, including `hilclaw/hypotheses.py`, `hilclaw/hypotheses_cases.py` and `hilclaw/instance.py`. The code slice of ADR-0075 is T-0233, blocked on HQ-0024.
- Injection at a gate or during a run, and their MVP inclusion (owner). Who derives a hypothesis from material. The catalog boundary. The S6 metric (T-0231, HQ-0023). The verdict's comparison base. OD-29, OD-23 and OD-18 beyond naming them. Owner-only items (OD-25, OD-3, C-6, #5 A/B).
- Editing earlier ADRs, including the "less exact" sentences of ADR-0059, ADR-0071, ADR-0073 and ADR-0075. Also FR-15, FR-17, UsageCases, the README and the index documents (`EventKinds.md`, `StepValues.md`, `BlobTypes.md`, `SpendAxes.md`).
- The unlanded branches of T-0210, T-0225, T-0231, T-0233 and T-0264. The branch of T-0231 also edits the OD-30 row and section; this task does not resolve that, and Result notes it for T-0231's later rebase. PR #179 (T-0284) touches only `hilclaw/clang_build.py` and `tests/test_clang_build.py`.

## Follow-ups

- If the record fixes a rule of conduct for the selection role, its sentence goes into the selection prompt in the P2-1/P2-6 task that writes that prompt.
- An integrator tidy-up of the less exact sentences listed under Consequences, if the reviewer asks for one.

## Result

**Outcome: BLOCKED (`owner-only-decision`)** — HQ-0031. Nothing landed on `main`. Two reviewer rounds (context-isolated `dev-reviewer`), both Request changes.

- **Branch** `claude/T-0318-od30-injected-system-distribution` is pushed to origin and kept for resume; head f550244 (on 1d713e2, 4ac270d). All commits carry `Task: T-0318`.
- **Files changed** are exactly the touchesFiles: new `ARCHITECTURE/decisions/ADR-0112-od30-injected-system-distribution.md` (ADR-0112 was free on `origin/main` and every remote branch); `ARCHITECTURE/Requirements.md` OD-30 row only (one `**확정분**` link; `**잔여**` rewritten as "주입 가설의 배분(시작 뒤 주입)"; status cell unchanged); `ARCHITECTURE/OpenDecisionProposals.md` OD-30 section only (adopted-record line after ADR-0075; the bullet "주입 가설과 시스템이 세운 가설의 배분" marked "(일부 답함)" with a partial-answer tail; "배분" → "배분(시작 뒤 주입)"); `ARCHITECTURE/StandardScenarios.md` "최근 재검사" line only (S0, S1, S8, S11 re-checked; no verdict change, no gap).
- **Checks**: `git diff --check` clean; all 28 added relative links resolve; OD register has 30 rows before and after.
- **Owner-sentence search**: 38 non-driver #5 comments (of 178), #5 body, #4 body and its 6 comments. No sentence reserves this choice to the owner; the addendum says the sharing (order, ratio) is open in OD-30.
- **Why blocked**: point 4 of https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569 ("An injected hypothesis goes through the same experiment, verification and verdict as the runtime's own") and FR-15 fix point (iii), coverage, under one reading (a duty to test every injected hypothesis) and leave it open under another (a rule of sameness only). The task's second BLOCKED condition says to stop in that case. Round 1 rejected a pace rule as widening the sources (FR-15's "참고사항(탐색 우선순위 힌트)으로만" allows putting an input off); round 2 rejected the sameness reading as a choice between readings (ADR-0075 decision 4 leaves coverage open). No single rule meets both readings.
- **Kept on the branch for resume**: decision 2 (iv) — every round from round 1 tests at least one `system` hypothesis (a selection-role behaviour rule, not a file-validity rule; cost: at N = 1 an injected test shares the one candidate with a system hypothesis); decision 4 (i)(ii) — no fixed order, mixing allowed within a round and on one candidate; decision 5 — no fixed ratio, FR-11 identification as in ADR-0075 decision 4; decision 6 — decision 2 checkable from one `hypotheses.json`, enforcement with OD-18, roster with OD-23. Decision 3 (iii) is drafted as "no coverage rule" and must be rewritten to the owner's answer (with Alternatives rows (b2)/(b3) and the Status readings if (b) or (c)).
- Review findings addressed: round 1 (Major on widening the sources, two Minors on costs, one Nit on the register residue); round 2 Minors 2–4 and the Nit.
- No data-plane, code, test, CI, prompt or settings change. No compiler, container or `claude` process was started (D16).
- **On resume**: rewrite decision 3 and its Status reading per HQ-0031; re-review with a fresh reviewer from round 3 of 7; rebase onto `origin/main`, squash with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0318`, push to `main`; post the §9 notice on #5. The unlanded T-0231 branch also edits the OD-30 row and section — resolve on T-0231's later rebase.
