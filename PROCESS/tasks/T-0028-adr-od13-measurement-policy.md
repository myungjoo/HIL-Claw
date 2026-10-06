---
id: T-0028
title: Write ADR-0007 closing the P1 minimum of OD-13 (measurement and noise policy - samples, repeats, summary statistic, initial values) and reflect it in the ARCHITECTURE documents
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-13, NFR-3, FR-10, FR-9, NFR-2, C-4, "#5 B-4", "#5 D6"]
dependsOn: [T-0015, T-0020, T-0021]
touchesFiles: [ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md, ARCHITECTURE/UsageCases.md]
estimatedSize: {loc: 190, files: 5}   # one new record of about 110-150 lines, the rest are in-place edits of a few lines each
hq: []   # OD-13 is a design-level OD (DRIVER §9: not among #5 A/B items, C-6, OD-25, OD-3); status 제안됨, its register row names no owner input
---
## Why
NFR-3 asks that the variance of a performance measurement is taken into account "by repeated measurement / confidence intervals", and says of itself "구체 정책 = 미결 → OD-13". **OD-13** (status `제안됨`) lists five questions: how the number of repeats is decided, the statistic a judgement uses, when a difference counts as an improvement, whether raw samples are kept, and how warm-up / steady state is handled. The registered proposal (#7 §5 G2) answers each of them, and nothing has adopted or rejected it.

Things that already wait for it:
- PLAN P1-3 names "OD-13 초기값" in its `coversReq` and has "반복 타이밍" in its text; PLAN P1-2 has "타이밍 수집". Neither can say how often a kernel is run, what is kept of the runs, or which number stands for them.
- ADR-0004 gives every attempt `sim.json` and `board.json` and says "Content: OD-13"; ADR-0002 leaves the members of the `profile` section of a spec to "B4, OD-13"; ADR-0006 leaves the payload of a measurement event to OD-13. The authors of those schemas need to know what a measurement must carry.
- StandardScenarios S9 step 3 ("노이즈 범위 내 차이는 '개선 아님'으로 판정") rests on it.

Owner decision D6 (DRIVER §9) lets the driver close **design-level** ODs by a decision record (ADR) + a context-isolated reviewer's Approve + an owner notice with a 7-day objection window. This task writes that record for the **P1 minimum of OD-13: the policy for the timing measurement of one attempt, with initial values** — the "OD-13 초기값" PLAN P1-3 asks for — and keeps the ARCHITECTURE documents consistent with it. It is a prerequisite slice of PLAN P1-3 / P1-2 and ticks **no PLAN checkbox**. The code that computes the statistics is a later code task (Follow-ups).

Why this item now (planner's judgement, DRIVER §6, 2026-10-07 UTC):
- Phase P0.5 has no executable item: P0.5-3 is BLOCKED on HQ-0003 (T-0014, unanswered on #5); the C gate of P0.5-1 waits for P1-2 / P1-3; the rest of P0.5-4 is the owner's hook registration, and the forbidden-command guard needs the owner's word on its tests (T-0007 Follow-ups).
- In P1: P1-3 is marked "오너 확정 필요" (the reference oracle — #5 B-7, and A-7 "still open") and is skipped by DRIVER §6, and with it P1-4, the kernel-running rest of P1-2 and P1-5 slice 3. P1-1 needs request / result shapes that hang on OD-10 / OD-18 / OD-23 and #5 B-2. The rest of P1-8 (`STATE.json`, `instance.json`) hangs on OD-17 with the open contradiction #8 M7 and holds owner-only members (OD-3, OD-1 / #5 A-4, #5 B-7). P1-6 and P1-7 are done.
- The measurement policy is the one part of P1-3 that the owner item does not touch: it concerns timing, not the oracle, the tolerance or the calling convention of a kernel.
- No open PR at planning time. The latest comment on #5 is the ADR-0006 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6024069787); no objection to ADR-0001..0006.

Planner's judgement that this slice is design-level and hangs on no open owner item — the reviewer is asked to re-check it:
- DRIVER §9 lists the owner-only items (#5 A/B items, C-6, OD-25, OD-3). OD-13 is none of them, and its register row names no #5 input.
- The owner has spoken on one point, and that is a fixed input, not an open one: #5 B-4 "Initial run caps: ... measurement repeats adaptive per OD-13 with an initial upper bound of 10".
- Items next to it that **are** owner-only or blocked and must stay untouched: OD-1 / #5 A-4 (which quantity is the target, and the order "better than" for it), #5 B-7 (oracle, tolerance vocabulary), #5 B-2 / B-3 (board farm, simulator), OD-3. The record must therefore speak of "a sample of the measured quantity" without choosing the quantity or its direction. If the executor finds that a point below cannot be written without one of them, that is a narrowed point or BLOCKED, not a gap to fill.

A-13 check (planner's reading): document mode, no schema file, no code, no dependency; the record names **no field** of any data-plane file (it states what a later schema must be able to hold). "데이터 plane 스키마 변경(STATE/spec/eval/artifacts)" should not apply. Ask the reviewer explicitly; if the reviewer reads it differently, return BLOCKED with the question instead of arguing it out.

Known risk, accepted: ADR-0001 / 0002 (objection windows until 2026-10-13) and ADR-0003..0006 (until 2026-10-14) are inside their windows. This record refers to ADR-0003 (calibration covers the correctness verdict only) and ADR-0004 (the per-attempt result files); its Status must say that it is revisited if one of them is reverted.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) — mandatory for every task (§6)
- PROCESS/DRIVER.md §0 last bullet, §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §8 (the driver tail on #5 comments), **§9 (the whole section)**, §11 row D6
- CLAUDE.md — 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", **"세션 진입 점검"** (before the first edit: `gh pr list`, issues #4, #5, #7, #8), "세 층 모델", "브랜치·merge 절차" (document mode and the BLOCKED reasons)
- .claude/skills/dev-item-address/SKILL.md — the procedure (document mode: steps 2, 7, 9-12, 15); .claude/skills/dev-code-review/SKILL.md — what the reviewer checks (in particular "no invented decisions")
- ARCHITECTURE/Requirements.md — rows FR-1, FR-2, FR-3, **FR-9**, **FR-10**, **NFR-3**, NFR-2, NFR-4, NFR-7, C-4, C-6, C-7; the whole "Open Decisions" preamble (status vocabulary, update rule, one-line rule); register rows **OD-13**, OD-1, OD-2, OD-10, OD-11, OD-14, OD-15, OD-16, OD-20, OD-28, OD-29
- ARCHITECTURE/OpenDecisionProposals.md — the header and sections **OD-13**, OD-11 (the measurement-contract pin: a proposal, plus its "확정분"), OD-15, OD-16 (threat B ⑷ ⑸; "하위 질문" ③), OD-1, OD-2, OD-28
- Issue #7 body **§5 G2** — the six bullets of the proposal with their sources (`gh issue view 7 --repo myungjoo/HIL-Claw --json body --jq .body`); the mapping comment https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5139423949
- Issue #5 comments (owner inputs; fixed): **B-4** `gh api repos/myungjoo/HIL-Claw/issues/comments/5944412285 --jq .body` ("Initial run caps"; "tens of seconds per round on an 8-core laptop"); A-7 `.../comments/5944117402` (the stand-in is a compiled C kernel; OpenMP and SIMD allowed; local first, then LAN); D6 `.../comments/5986348506`; then every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6024069787 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). Also the issue body items A-4, B-2, B-3, B-7 (unanswered)
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — the closing **"Record format"** section (this record must follow it) and the Status section as a model
- ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md — decision 3 (the rows on threat B ⑷ ⑸: defences of the timing are not adopted), decision 7, Boundaries (the sub-question on calibrating the timing side)
- ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md — the path table rows of `sim.json`, `board.json`, `profile.json`, `eval.json` and the bullet "Whether a step may leave more than one record for one attempt"; ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md — the `profile` row; ARCHITECTURE/decisions/ADR-0006-od8-events-log.md — decision 7 and the Boundaries bullet on event kinds
- ARCHITECTURE/StandardScenarios.md — "계층", "검사 규칙", every step that cites NFR-3 or OD-13 or speaks of repeated measurement, noise or re-measurement (search for them; S9 step 3 at least), and "검사 결과" (heading, history paragraph, the affected rows); ARCHITECTURE/UsageCases.md — UC-2 and the row UC-E3
- `hilclaw/local_run.py` (module docstring: `duration_s` includes process start-up) and PROCESS/tasks/T-0019-local-process-runner.md `## Result` (limits left to OD-13 / OD-14) — existing code the record must not contradict. Not edited
- PROCESS/tasks/T-0020-adr-od16-harness-calibration.md — `## Result` (how a record that keeps its OD at `제안됨` landed: register precedent, review findings, notice text); PROCESS/PLAN.md items P1-2, P1-3, P1-4

## Acceptance Criteria
What is **fixed** and must be taken as input, not re-decided:
- NFR-3: score stability is obtained by repeated measurement and confidence intervals. S9 step 3: a difference inside the noise is "not an improvement".
- #5 B-4: for the initial runs, repeats are adaptive and have an initial upper bound of 10; one call of a first GEMM takes about 0.1 s and a round tens of seconds of hardware time.
- C-4: board time is expensive and shared, so a policy that multiplies measurements has a cost.
- #5 A-7 / C-7: the first backend is `cpu_standin`, a compiled C kernel on the local PC, OpenMP and SIMD allowed.
- FR-9 / #5 A-12: timing is done by the harness, which is one sub-module of the tool package; P1 pins the harness version by the source commit hash (the confirmed part of OD-11).
- ADR-0003: the calibration criterion covers the correctness verdict; no defence of the timing (threat B ⑷ ⑸) is adopted.
- #7 §5 G2 is a **proposal**. Its values (CV below 5 %, n in [5, 30], trimmed mean, δ = 2 %, 95 % interval) may be adopted, changed or left open — each with a reason. Where it and #5 B-4 differ (upper bound 30 versus 10), the owner's statement holds for the initial runs.

What the ADR **decides** (the P1 minimum of OD-13). The content of each decision is the executor's to work out and justify from the fixed inputs and the registered proposal; the reviewer's Approve is what confirms it. For every point give the choice, the alternatives considered and one or two lines of reason, and mark every value no source gives as this record's own initial value:
1. **Scope and terms**: what a measurement, a repeat and a sample are; that the policy is about one scalar sample per repeat of "the measured quantity" and chooses neither the quantity nor its direction (OD-1); to which execution points it applies now (`cpu_standin`) and what is only an initial value for sim and board (#5 B-2 / B-3 unanswered).
2. **What a sample covers**: what must be inside and outside the timed interval as a matter of policy (for example process start-up and input generation outside), without fixing the mechanism, the clock call or the calling convention of a kernel (PLAN P1-3).
3. **Raw samples are kept**: every sample of a measurement is kept in the order taken, so that a judgement can be redone later (#7 G2), including samples a later rule sets aside; a scalar alone is never the record. State it as a requirement on the result files of ADR-0004 and name **no field**.
4. **Number of repeats**: the stopping rule (which measure of spread, which threshold), the lower and the upper bound, and what a measurement is when the upper bound is reached before the rule is met (usable and marked, or not usable) — consistent with the owner's "adaptive, initial upper bound 10".
5. **Summary statistic**: the one number that stands for a measurement, how it behaves at the smallest allowed number of samples, and what is ruled out (the proposal rules out the minimum).
6. **Warm-up and steady state**: what P1 does with the first repeats — discard a fixed number, label, or nothing — given that the proposal rejects a fixed warm-up and that samples are never dropped silently (point 3).
7. **Judging a difference**: the form of the rule by which two measurements of the same quantity are called different (S9 step 3), and its initial values. Whether the paired, interleaved re-measurement of the incumbent is part of the P1 minimum: it costs hardware time (C-4) and needs the incumbent to be runnable again (OD-20, OD-28, OD-11). Decide only what can be said without those; otherwise fix the rule for two given sample sets and leave the pairing to the rest. "Better" is never defined here (OD-1).
8. **Parameters and identification**: which values are constants of this policy and which may be set per instance; that a result can be traced to the policy that produced it (in P1 through the source commit hash — refer to the confirmed part of OD-11, decide nothing more of OD-11).
9. **Reproducible judgement**: if a rule uses random resampling, how the same samples give the same judgement again (NFR-2). Keep this apart from the runtime seeds of verification inputs, which are never files (OD-16).
10. **Limits**: what the policy does not give — no protection against forged timing (rest of OD-16), no board health or fault handling (OD-10), no comparability across sessions, machines or harness versions (OD-11), and that the values are initial values to be revised with data.

What the ADR must **not** decide — name each as a boundary in the record, with the place where it is decided:
- The target quantity, its unit and direction, the order "better than", multi-objective handling (OD-1 / #5 A-4 — blocked); the hardware-quota budget axis (OD-2); the tolerance and the oracle (#5 B-7; PLAN P1-3 "오너 확정 필요").
- Board and simulator specifics: failure, retry and health (OD-10; #5 B-2), sim-to-board promotion and rank correlation (OD-15; #5 B-3), the number of promoted candidates (OD-29).
- Defences of the timing against a degenerate kernel, and whether the timing side gets a calibration (rest of OD-16).
- The measurement-contract pin per instance and the forced re-measurement of an incumbent (OD-11 proposal); which baseline (OD-28); what is archived of a candidate (OD-20).
- Fields and schemas of `sim.json`, `board.json`, `profile.json`, `eval.json`, `instance.json`; any event kind or payload (PLAN P1-8, P1-1; ADR-0006 Boundaries); profile content.
- The harness design, the kernel calling convention, the timer mechanism, session hygiene on a board (clock and power mode, temperature, firmware), and sandbox timeouts (PLAN P1-3; OD-14).
- Any code, test, schema file, CI change, or any change to the `HIL-Claw-data` repository.

If a point of 1-10 cannot be written without one of the excluded items, do not fill the gap: narrow the point and say so, or return BLOCKED ("design choice needing an owner-only decision" or "requirement unclear") with the exact question (DRIVER §3, §9).

The record (`ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md`, new; the slug may be adjusted, the number may not):
- Follow the "Record format" section of ADR-0001: sections Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References, in this order; one closure per record; written in English.
- **Status** says: accepted under DRIVER §9 (D6) by reviewer approval, the acceptance date, that it closes the P1 minimum of OD-13 and what stays open, which earlier records it refers to and that it is revisited if one of them is reverted, and that the owner may object on #5 within 7 days of the notice, in which case a reverting task is created. Do not write that the owner confirmed it.
- One table "parameter — initial value — source (cited / this record) — constant or per instance", and one short worked example with clearly synthetic sample values that shows the stopping rule, the summary statistic and the difference rule on a handful of numbers. Length about 110-150 lines; enough for the author of the following code task to write the functions without reading the issues again.
- **Consequences** list what follows for existing code and documents without changing them: `hilclaw/local_run.py` (`duration_s` is not a sample if point 2 says so), the result-file schemas, the following code task.
- **References** cite sources by stable handle: Requirements IDs, issue comment URLs, the proposal section, PLAN items, ADR-0001 / 0002 / 0003 / 0004 / 0006.

Edits of existing documents (same commit as the record — register update rule):
- `ARCHITECTURE/Requirements.md`: the **OD-13** row only. Two precedents exist: status `확정` with the open rest as "잔여" (OD-4, OD-6, OD-8), or the status kept and a "**확정분**" note added (OD-11, OD-16). Choose the one you can defend and say in the commit body which and why; the open rest must stay visible in the row. Keep the row to one line. Do not renumber, add or remove any OD row. Do not edit the body of NFR-3 or of any other FR / NFR / C row: NFR-3 says "구체 정책 = 미결 → OD-13" — name the proposed wording as a follow-up for the integrator.
- `ARCHITECTURE/OpenDecisionProposals.md`, section **OD-13**: a heading note and a "채택분(ADR-0007)" / "제안으로 남는 부분" pair in the style of the OD-16 and OD-8 sections; add any sub-question the record raises; delete no proposal text. In section OD-16 ("하위 질문" ③) and OD-11, at most one pointer each where a sentence saying "… with OD-13" is now partly answered; change nothing else.
- `ARCHITECTURE/StandardScenarios.md`: re-run the coverage check (CLAUDE.md "문서 커버리지 재검사") with the document's own rules for every step that cites NFR-3 or OD-13 or rests on repeated measurement, and update "검사 결과": heading date / note, one new dated passage in the history paragraph, and the affected rows. State the outcome in the commit body even if no verdict changes.
- `ARCHITECTURE/UsageCases.md`: only if a sentence that cites OD-13 has become false or now has a more precise pointer. If nothing needs to change, do not touch the file and say so in `## Result`.
- In-place edits of these documents keep the language of the text around them (Korean), as in T-0015 / T-0017 / T-0020 / T-0021 / T-0024 / T-0026.
- No edit to ADR-0001..0006, `CLAUDE.md`, `README.md`, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills, the agents, `hilclaw.config.json`, or any file under `hilclaw/`, `tests/`, `.github/`.

Tests:
- None. Document mode: no code changes, so CLAUDE.md test rules ①-④ do not apply. The document checks below replace steps 4, 6 and 8 of dev-item-address.

Document checks (record the outcome of each in `## Result`):
- Session-entry check done before the first edit: `gh pr list --repo myungjoo/HIL-Claw --state open` (the planner saw none on 2026-10-07) and issues #4, #5, #7, #8 read for anything newer than this task file about OD-13, NFR-3 or measurement (the planner found nothing: the latest #5 comment is the ADR-0006 notice 6024069787; HQ-0003 is unanswered and unrelated). If an open PR edits the OD register or the OD-13 section, stop and return BLOCKED ("open PR conflict"). If the owner has meanwhile answered A-4, B-2, B-3 or B-7, or objected to ADR-0003 or ADR-0004 in a way that changes what this record refers to, take the answer as a fixed input, or return BLOCKED ("requirement unclear") quoting the comment if it contradicts this task.
- Every relative link in the new record and in the edited lines resolves to an existing file or anchor (`ARCHITECTURE/decisions/` is one level below `ARCHITECTURE/`).
- OD numbers: `git diff origin/main -- ARCHITECTURE/Requirements.md` touches the OD-13 row only; the count (29) and numbering of register rows are unchanged.
- Nothing in the record states an excluded item as decided: no target quantity, unit or direction, no "better", no tolerance or oracle, no board or simulator rule, no timing defence, no field of any file, no event kind, no timer mechanism. Every value is marked with its source or as the record's own initial value.
- The record is consistent with #5 B-4 (adaptive; upper bound 10 for the initial runs), NFR-3, S9 step 3, ADR-0003 and ADR-0004.
- `git ls-files --eol` shows `i/lf` for the changed files; `git diff origin/main --stat` lists only files in `touchesFiles` (four or five).
- CI is not a gate for document mode, but the push to `main` triggers the workflow: check the `push` run with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion; if it is not `success`, do not fix forward — record it and say so in the returned summary.

Process (document mode, CLAUDE.md A-13, dev-item-address steps 9-12 and 15):
- Before anything else, the §3-5 landed check: `git log origin/main --grep='^Task: T-0028'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0028 --state all`.
- Branch `claude/T-0028-adr-od13-measurement-policy` from `origin/main`. Commit and push the branch; **no PR**.
- Reviewer cycle: spawn a fresh-context `dev-reviewer` sub-agent, give it the branch name (review target = diff against `origin/main`) and this task file's path, and receive the verdict and findings as its return value. Ask it explicitly to check (a) the planner's judgement in `## Why` that the record is design-level and hangs on no open owner item, and the A-13 reading; (b) that no excluded item is decided — in particular nothing of OD-1 (quantity, direction, "better"), no field, no board rule — and that the pairing question of point 7 is either argued without OD-20 / OD-28 / OD-11 or left open; (c) that each decision follows from a cited source or is argued as a design choice with alternatives, and that each value is marked as cited or as the record's own initial value; (d) the register and coverage-check updates. Address findings and re-request review until Approve with nothing trivially fixable left; more than 7 rounds is BLOCKED. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Landing: `git fetch origin`, rebase the branch onto `origin/main`, then squash to **one** commit (`git reset --soft origin/main` + commit — only after the rebase). `git show --stat HEAD` must list only files in `touchesFiles`. If the rebase needed conflict resolution that changed content, go back to review.
- Commit message: English; subject starts with `T-0028:`; the body gives the decisions 1-10 in one line each, the boundaries, which register precedent was followed and the coverage re-check outcome; it ends with the trailers, in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0028`, then any attribution trailer your session requires.
- Push with `git push origin HEAD:main` (fast-forward). If rejected because `main` moved, fetch, rebase and retry (at most 3 times); never `git push --force*`, and never push the rewritten branch back to its remote branch. Delete the remote branch and the local branch in **separate** commands and only after the push to `main` is confirmed (T-0012 incident), then check out `main` at `origin/main`.
- **Owner notice (DRIVER §9)**: do not post it yourself — the driver is the notifier (DRIVER §7, §8). Put the ready-to-post English text in `## Result`: what was decided in six lines or fewer with the parameter table, the record's path and commit, which values come from the owner (#5 B-4), which from the #7 proposal and which are the record's own, the boundaries left open, the A-13 reading, and the date on which the 7-day window ends. The driver posts it on #5 with its tail.
- `## Result`: fill it in **after** the push, on `main`, and leave that edit to this task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The landed commit must not contain the task file. Record: commit hash, review rounds and findings with how each was handled, the decisions with their reasons, the boundaries, the document-check outcomes, the notice text, follow-ups.
- `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. This task ticks **no** PLAN checkbox; say so in `## Result`.
- Size: one new file of about 110-150 lines and three or four small edits; within 300 LOC / 5 files. If consistency turns out to need a sixth file, do not exceed the cap: finish the five and list the sixth as a proposed follow-up (DRIVER §5).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Any code: the statistics functions, a timer, the harness, a result-file schema or validator, and their tests.
- Closing or changing any OD other than the P1 minimum of OD-13; anything of OD-1, OD-2, OD-10, OD-11, OD-15, OD-16, OD-20, OD-28, OD-29.
- Board and simulator measurement beyond marking the values as initial; session hygiene on a board.
- Editing the body of NFR-3 or any FR / NFR / C row, issue bodies, ADR-0001..0006, or posting on GitHub issues (the driver posts the owner notice).
- Answering #5 A-4, B-2, B-3, B-7 or any other owner item on the owner's behalf.

## Follow-ups
- (driver, after the wrap-up push) Post the §9 owner notice on #5 from the text in `## Result`, with the driver tail.
- (planner, next — code mode) A pure, standard-library module that implements ADR-0007 on given samples (stopping rule, summary statistic, difference rule), with tests. It runs no kernel and writes no file. Its place needs a judgement first: FR-9 / #5 A-12 put timing in the one harness sub-module (`harness/`), which does not exist yet.
- (owner or integrator) Proposed wording for NFR-3 once the record has landed (the task forbids editing it).
- (planner) PLAN P1-3 is still marked "오너 확정 필요": the reference oracle of `cpu_standin` (#5 B-7; A-7 "still open" — NumPy float64 would also be a new external dependency), and with it the memory layout, operand order and C prototype of the first GEMM and the `hw_source` of `cpu_standin` (T-0021 Follow-ups). It holds back P1-4, the rest of P1-2, the C gate of P0.5-1 and P1-5 slice 3. Once no design-level slice is left, raise these as an HQ with a BLOCKED P1-3 task, as T-0014 did for P0.5-3.
- (planner) The rest of P1-8 (`STATE.json`, `instance.json`) needs OD-17 / #8 M7 closed by an ADR and holds owner-only members (OD-3, OD-1, #5 B-7).

## Result
