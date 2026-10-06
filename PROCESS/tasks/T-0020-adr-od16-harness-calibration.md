---
id: T-0020
title: Write ADR-0003 closing the P1 minimum of OD-16 (three-state calibration as the acceptance criterion of the verification harness) and reflect it in the ARCHITECTURE documents
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-16, FR-9, NFR-4, "#5 D6", "#5 A-12", "#7 S-2 N8"]
dependsOn: [T-0015]
touchesFiles: [ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md, ARCHITECTURE/UsageCases.md]
estimatedSize: {loc: 170, files: 5}   # one new record of about 100-140 lines, the rest are in-place edits of a few lines each
hq: []   # OD-16 is a design-level OD (DRIVER §9: not among #5 A/B items, C-6, OD-25, OD-3; PLAN P1-4 marks it "OD-16 종결 필요(§9 ADR 경로)")
---
## Why
FR-9 requires a verification harness the coder cannot modify, which re-verifies on inputs the coder never saw. Nothing yet says **when that harness itself counts as done**. Survey item #7 S-2 N8 proposes the answer: the *three-state calibration* of Kernel Contracts — show a conforming implementation, a failing one, and one that "passes the functional test but violates the contract", and prove the harness tells them apart. The proposal was absorbed into OD-16 (OpenDecisionProposals OD-16, bullet "하네스 자체의 수용 기준") as "adoption under consideration". PLAN P1-4 (the calibration tests) is marked "**OD-16 종결 필요(§9 ADR 경로)**": the tests cannot be written before it is decided what the three states are in HIL-Claw terms and which violations the harness must be shown to catch.

Owner decision D6 (2026-10-05, DRIVER §9) lets the driver close **design-level** ODs by a decision record (ADR) + a context-isolated reviewer's Approve + an owner notice with a 7-day objection window. This task writes that record for the **P1 minimum of OD-16** — the harness acceptance criterion only — and keeps the ARCHITECTURE documents consistent with it. It is a prerequisite slice of PLAN P1-4 and ticks **no PLAN checkbox**. The calibration kernels and tests themselves are a later code task (after P1-3).

Why this item now (planner's judgement, DRIVER §6, 2026-10-07): phase P0.5 has no actionable item (P0.5-3 is BLOCKED on HQ-0003; the rest of P0.5-1 waits for P1-2 / P1-3; the rest of P0.5-4 is the owner's hook registration). In P1: P1-3 is marked "오너 확정 필요" (the f64 oracle) and is skipped; the rest of P1-2 (timing, adapter) needs the kernel calling convention, whose values no source gives; P1-5 slice 3 needs the same owner values; P1-1 needs request / result shapes hanging on OD-10 / 13 / 18 / 23; P1-8 (OD-8) depends on OD-3 (owner-only); the rest of P1-6 needs OD-8. The acceptance criterion of the harness can be decided without any of these.

Planner's judgement that OD-16 is design-level and that this slice hangs on no owner item — the reviewer is asked to re-check it:
- DRIVER §9 lists the owner-only items exhaustively (#5 A/B items, C-6, OD-25, OD-3). OD-16 is none of them; its register row is `제안됨` with discussion in #7, not `차단됨`.
- The owner inputs OD-16 rests on are already given and are **inputs** here: OD-5 hard floor (#5 A-6), the harness as one sub-module outside the coder's scratch (#5 A-12), the principle "unforgeability, not concealment" and "no read restriction" (#4 comment 5139876430, owner judgement).
- Two owner items sit next to it and must stay untouched: the **oracle** of `cpu_standin` (NumPy float64 is a recommendation of #5 A-7 awaiting owner confirmation — the reason P1-3 is marked) and the **tolerance vocabulary** (#5 B-7, unanswered). The record must be written so that it is true for any oracle and any tolerance. If the executor finds that a criterion below cannot be written without choosing either, that is BLOCKED, not a gap to fill.
- Adopting an acceptance criterion for the harness adds no defence to the MVP beyond the FR-9 minimum; it only requires evidence that the minimum works. A record that would pull an extension defence (S7 / B1 / B8) into the MVP is outside this task.

A-13 check (planner's reading): no data-plane schema (STATE / spec / eval / artifacts) is defined or changed, no code, no dependency. If the reviewer reads it differently, return BLOCKED with the question.

Known risk, accepted: ADR-0001 and ADR-0002 are inside their 7-day objection windows (until 2026-10-13). This record depends on neither's content beyond the record format.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) — mandatory for every task (§6)
- PROCESS/DRIVER.md §0 last bullet, §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §8 (the driver tail on #5 comments), **§9 (the whole section)**, §11 rows D6 and D12
- CLAUDE.md — 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", **"세션 진입 점검"** (before the first edit: `gh pr list`, issues #4, #5, #7, #8), "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (document mode and the BLOCKED reasons), "테스트 규칙" (rule ⑤ in particular), "코멘트 최소화"
- .claude/skills/dev-item-address/SKILL.md — the procedure (document mode: steps 2, 7, 9-12, 15); .claude/skills/dev-code-review/SKILL.md — what the reviewer checks (in particular "no invented decisions")
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — the closing **"Record format"** section (this record must follow it) and the Status section as a model; ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md — Status, decision 2 bullet "No field carries verification inputs", `task.contract`, and the Boundaries bullets "OD-16 beyond the minimum of FR-9" and "The harness-side contract of a kind (PLAN P1-3)"
- PROCESS/tasks/T-0017-adr-od6-codegen-spec.md `## Result` (how the second ADR landed: register precedent, review findings, notice text) and PROCESS/tasks/T-0015-adr-od4-key-schema.md `## Result`
- PROCESS/PLAN.md — items P0.5-1, P1-3, P1-4, P2-3
- ARCHITECTURE/Requirements.md — rows FR-1 (correctness at two points, ⑴-⑶), FR-3 ④, **FR-9**, FR-10, NFR-3, NFR-4, NFR-6, NFR-7; the whole "Open Decisions" preamble (status vocabulary, update rule, register scope); register rows **OD-16**, OD-5, OD-11 (the two precedents: `확정` + "잔여" versus "**확정분**" note), OD-4, OD-6, OD-8, OD-12, OD-13, OD-14, OD-15, OD-18, OD-23; the "번호 이력" paragraph under the table
- ARCHITECTURE/OpenDecisionProposals.md — the header (lines 1-9) and sections **OD-16** (all bullets), OD-13, OD-14, OD-8 (candidates ① / ②), OD-11, OD-20 (`private_metrics`)
- ARCHITECTURE/UsageCases.md — glossary entry "검증 하네스", the actor row "(검증 하네스)", the UC-2 / UC-3 alternative flow "검증 실패", the row UC-E1
- ARCHITECTURE/StandardScenarios.md — "계층", "검사 규칙", S7 (all steps), S8 step 3, S0 / S1 correctness steps, and "검사 결과" (rows S7, S8; the heading and the history paragraph)
- ARCHITECTURE/reviews/2026-09-03-StandardScenarios-LiteratureReview.md — the note at line 7 and rows B1, B8
- Issue #7 (`gh issue view 7 --repo myungjoo/HIL-Claw --json body,comments`) — body §5 G1 and §7; the S-2 comment https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5566900982 (the "Kernel Contracts" row of the survey table, item **N8**, and "기각/보류한 아이디어": no concealment hardening); the S-1 supplement https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5139423949 (number mapping, item (2))
- Issue #4 comments https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 (the two owner premises: reads are not restricted; hard-coding is stopped in the measurement layer) and https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800 (evaluator row)
- Issue #5 comments (owner inputs; fixed): A-6 / OD-5 `gh api repos/myungjoo/HIL-Claw/issues/comments/5933950693 --jq .body`; A-7 `.../comments/5944117402` (its "Still open" part about the correctness reference); A-12 `.../comments/5946779596`; D6 `.../comments/5986348506`. Also the issue body item B-7 (unanswered)
- Issue #8 — only for the session-entry check (anything newer than this task file about OD-16, the harness or calibration)
- The Kernel Contracts paper (arXiv 2604.22032) is cited by #7 as the origin. Reading it is optional; do not state anything about it that #7 does not state unless you fetched and read the source, and say in References which of the two you relied on.

## Acceptance Criteria
What is **fixed** and must be taken as input, not re-decided:
- FR-9: correctness is a hard floor; the same verification runs at sim and at board; the minimum robustness clause — re-verification on inputs (shape / seed) not exposed to the coder, in an isolated harness the coder cannot modify; a result that fails verification enters neither best nor the statistics; FR-3 ④ early stop only after re-verification. Full hardening is an extension (S7) under OD-16.
- OD-16 confirmed part (#5 A-12): the harness (input generation, f64 reference, tolerance comparison, timing, profile, eval / event recording) is one sub-module of the tool package, outside the coder's scratch; its P1 version is the source commit hash.
- OD-16 principle (proposal text, 2026-07-31 revision, and the owner premises in #4 comment 5139876430): defences must hold even when everything is read; runtime seeds and input values do not exist as files; reads are not restricted.
- PLAN P1-3 / P1-4: P1-3 builds the harness with random inputs from a non-file seed; P1-4 names the three kernels "통과 커널 / 실패 커널 / 기능 통과·계약 위반 커널".
- CLAUDE.md: layer-2 languages {Python, POSIX sh, C}; layer 3 = C kernels produced by the coder; test rule ⑤.
- ADR-0002: a spec carries no seed, verification input or expected value.

What the ADR **decides** (the P1 minimum of OD-16). The content of each decision is the executor's to work out and justify from the fixed inputs and the registered proposal; the reviewer's Approve is what confirms it. For every point give the choice, the alternatives considered and one or two lines of reason:
1. **Adoption and unit**: whether three-state calibration is adopted as an acceptance criterion of the verification harness ("the harness is not done until …"), and for which unit it must be shown — the harness as a whole, each operation kind the harness can verify, or each rule it enforces.
2. **The three states in HIL-Claw terms**: what "conforming", "failing" and "passes the functional test but violates the contract" mean here. In particular define the two words the third state needs — which check is "the functional test" and which obligation is "the contract" — from FR-9 and S7 steps 1-2, not from a new requirement.
3. **Minimum violation classes for P1**: which kinds of contract-violating kernel the P1 calibration set must contain. Restrict the required set to violations that the FR-9 minimum clause and the confirmed parts of OD-16 already oblige the harness to catch. For each class of the OD-16 proposal (threat A items; threat B ⑴-⑹; the S7 / B1 / B8 extensions) say whether it is required in P1, and for those not required say why (the defence that would catch it is an unadopted extension) — without adopting that defence.
4. **What "caught" means**: the expected harness outcome for each state (for example a verdict of pass / fail), and whether calibration requires the harness to name the *cause* of a rejection. Failure-type tagging is S7 step 3 (extension): calibration may not make it an MVP requirement.
5. **Nature and place of the calibration kernels**: what they are (fixtures of the harness's tests, hand-written, in which language), that they are not coder output, not catalog entries and never part of a coder's scratch or spec; and how this reads against CLAUDE.md test rule ⑤ (the harness is layer-2 product code, so tests of it are ordinary product tests — state the reading; do not change the rule). Directory names are for the code task.
6. **When the criterion must hold**: on which events calibration is re-run (a change of the harness; a new operation kind; other), stated as a rule on the harness's tests. The CI job that runs it is P0.5-1 ("C gate: clang build + harness pass"): the record may say calibration is a candidate content of that gate; it does not design the workflow. The link to the measurement-contract pin is OD-11: refer, do not decide.
7. **Independence from the oracle and the tolerance**: state the criterion so that it holds for any reference oracle and any tolerance value, and say how the calibration tests obtain a tolerance (a parameter of the test, never a system default).
8. **Limits**: what passing calibration does not prove (it shows the listed violations are caught, not that no loophole exists), and its relation to the still-open items of OD-16 (hacker-fixer loop, adversarial re-verification strength).

What the ADR must **not** decide — name each as a boundary in the record, with the place where it is decided:
- Owner items: the reference oracle of `cpu_standin` (NumPy float64, #5 A-7 "still open"; also a possible new external dependency — A-13), the tolerance vocabulary and default values (#5 B-7, OD-5 rest), B-8 (datasets), OD-3 (gates, including any escalation gate of S7 step 5), OD-25, C-6, OD-12 (coder web search, B8).
- The harness's design: its API, the kernel calling convention and prototype (P1-3; ADR-0002 `task.contract` carries the values, it does not define them), how many inputs or which shapes a verification run draws, seed derivation, the first GEMM's layout and operand order.
- Rest of OD-16: static checks and forbidden patterns, precision-downgrade checks, roofline bound and its model, order-dependence test, per-trial reallocation / cache flush / timing-caching detection, profiler confirmation of execution, LLM verifier, hacker-fixer pre-hardening, strength of the adversarial re-verification before promotion, the `private_metrics` definition (with OD-20). Each stays a registered proposal unless decision 3 shows that the FR-9 minimum already obliges it — in that case cite the FR-9 words that do.
- OD-13 (measurement and noise; timing-related calibration), OD-14 / NFR-4 and OD-8 (process separation, write isolation, layout — threat A), OD-11 (measurement-contract pin and re-measurement), OD-15 (promotion), OD-18 (hooks), OD-23 and P2-3 (the evaluator agent and its contract; PLAN marks P2-3 with its own OD-16 closure).
- Any code, test, fixture, CI workflow change or schema file.

If a point of 1-8 cannot be written without one of the excluded items, do not fill the gap: return BLOCKED ("design choice needing an owner-only decision" or "requirement unclear") with the exact question (DRIVER §3, §9).

The record (`ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md`, new):
- Follow the "Record format" section of ADR-0001: sections Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References, in this order; one closure per record; written in English. Refer to ADR-0001 for the format in one line.
- **Status** says: accepted under DRIVER §9 (D6) by reviewer approval, the acceptance date, that it closes the P1 minimum of OD-16 (the harness acceptance criterion) and what stays open, and that the owner may object on #5 within 7 days of the notice, in which case a reverting task is created. Do not write that the owner confirmed it.
- Length: about 100-140 lines; enough for the author of the P1-4 code task to write the three kernels' tests without reading the issues again. A table for decision 3.
- **References** cite sources by stable handle: Requirements IDs, issue comment URLs, the proposal section, PLAN items, ADR-0001 / ADR-0002.

Edits of existing documents (same commit as the record — register update rule):
- `ARCHITECTURE/Requirements.md`, row **OD-16** only. Keep the row to one line. Two precedents exist: status `확정` with the open rest as "잔여" (OD-4, OD-5, OD-6 rows), or the current status kept and the "**확정분**" note extended (OD-11 row, and the OD-16 row itself today). The row's question is the adoption scope of defences beyond the FR-9 minimum, which this record does not decide in full and which PLAN P2-3 marks for a further closure — so the expected choice is to **keep `제안됨` and extend "확정분"** with the acceptance criterion and a pointer to the record by path. Choose `확정 (P1 최소분)` only if you can show the record decides everything the row names for P1. Say in the commit body which precedent you followed and why. Do not renumber, add or remove any OD row; do not edit the body of FR-9 or any other FR / NFR; do not touch the "첫 커밋 전에 확정해야 하는 항목" sentence (OD-16 is not one of them).
- `ARCHITECTURE/OpenDecisionProposals.md`, section **OD-16**: at the bullet "하네스 자체의 수용 기준" mark what the record adopted (link to it); in "잔여 미결" keep everything that stays open and add any sub-question the record raises. Do not delete proposal text.
- `ARCHITECTURE/StandardScenarios.md`: re-run the coverage check (CLAUDE.md "문서 커버리지 재검사") with the document's own rules for every step that cites OD-16 or is verified by the harness (S7 steps 1-3, S8 step 3, the correctness steps of S0 and S1, and any other the search finds), and update "검사 결과": heading date / note, one new dated passage in the history paragraph, and the affected rows. An extension step stays "확장 호환" unless the record makes it false. State the outcome of the re-check in the commit body even if no verdict changes.
- `ARCHITECTURE/UsageCases.md`: only if a sentence that cites OD-16 or describes the harness has become false or now has a more precise pointer (glossary "검증 하네스", row UC-E1). If nothing needs to change, do not touch the file and say so in `## Result`.
- In-place edits of these documents keep the language of the text around them (Korean), as in T-0015 / T-0017.
- No edit to ADR-0001, ADR-0002, `CLAUDE.md`, `README.md`, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills, the agents, or any file under `hilclaw/`, `tests/`, `.github/`.

Tests:
- None. Document mode: no code changes, so CLAUDE.md test rules ①-④ do not apply. The document checks below replace steps 4, 6 and 8 of dev-item-address.

Document checks (record the outcome of each in `## Result`):
- Session-entry check done before the first edit: `gh pr list --repo myungjoo/HIL-Claw --state open` (the planner saw none on 2026-10-07) and issues #4, #5, #7, #8 read for anything newer than this task file about OD-16, the harness, the oracle or calibration (the planner found nothing: the latest #5 comment is the ADR-0002 notice 6018744123; HQ-0003 is unanswered and unrelated). If an open PR edits the OD register or the OD-16 sections, stop and return BLOCKED ("open PR conflict"). If the owner has meanwhile answered A-7's open part or B-7, take the answer as a fixed input and say so in `## Result`.
- Every relative link in the new record and in the edited lines resolves to an existing file or anchor (`ARCHITECTURE/decisions/` is one level below `ARCHITECTURE/`).
- OD numbers: `git diff origin/main -- ARCHITECTURE/Requirements.md` touches the OD-16 row only; the count (29) and numbering of register rows are unchanged.
- Nothing in the record states an excluded item as decided; no oracle implementation and no tolerance value is named as chosen; no extension defence is made an MVP requirement; every claim about Kernel Contracts is one #7 makes or one read from the source.
- The record is consistent with FR-9 as written, with ADR-0002 (no verification input in a spec) and with PLAN P1-4's three kernels.
- `git ls-files --eol` shows `i/lf` for the changed files; `git diff origin/main --stat` lists only files in `touchesFiles` (four or five).
- CI is not a gate for document mode, but the push to `main` triggers the workflow: check the `push` run with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion; if it is not `success`, do not fix forward — record it and say so in the returned summary.

Process (document mode, CLAUDE.md A-13, dev-item-address steps 9-12 and 15):
- Before anything else, the §3-5 landed check: `git log origin/main --grep='^Task: T-0020'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0020 --state all`.
- Branch `claude/T-0020-adr-od16-harness-calibration` from `origin/main`. Commit and push the branch; **no PR**.
- Reviewer cycle: spawn a fresh-context `dev-reviewer` sub-agent, give it the branch name (review target = diff against `origin/main`) and this task file's path, and receive the verdict and findings as its return value. Ask it explicitly to check (a) the planner's judgement in `## Why` that this slice of OD-16 is design-level and hangs on no owner item, (b) that no owner-only or excluded item is decided and no extension defence is pulled into the MVP, (c) that each decision follows from a cited source or is argued as a design choice with alternatives, (d) the register and coverage-check updates. Address findings and re-request review until Approve with nothing trivially fixable left; more than 7 rounds is BLOCKED. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Landing: `git fetch origin`, rebase the branch onto `origin/main`, then squash to **one** commit (`git reset --soft origin/main` + commit — only after the rebase). `git show --stat HEAD` must list only files in `touchesFiles`. If the rebase needed conflict resolution that changed content, go back to review.
- Commit message: English; subject starts with `T-0020:`; the body gives the decisions 1-8 in one line each, the boundaries, which register precedent was followed and the coverage re-check outcome; it ends with the trailers, in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0020`, then any attribution trailer your session requires.
- Push with `git push origin HEAD:main` (fast-forward). If rejected because `main` moved, fetch, rebase and retry (at most 3 times); never `git push --force*`, and never push the rewritten branch back to its remote branch. Delete the remote branch and the local branch in **separate** commands and only after the push to `main` is confirmed (T-0012 incident), then check out `main` at `origin/main`.
- **Owner notice (DRIVER §9)**: do not post it yourself — the driver is the notifier (DRIVER §7, §8). Put the ready-to-post English text in `## Result`: what was decided in five lines or fewer, the record's path and commit, the boundaries left open (in particular that the oracle and the tolerance are untouched and that no extension defence was adopted), the A-13 reading, and the date on which the 7-day window ends. The driver posts it on #5 with its tail.
- `## Result`: fill it in **after** the push, on `main`, and leave that edit to this task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The landed commit must not contain the task file. Record: commit hash, review rounds and findings with how each was handled, the decisions with their reasons, the boundaries, the document-check outcomes, the notice text, follow-ups.
- `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. This task ticks **no** PLAN checkbox.
- Size: one new file of about 100-140 lines and three or four small edits; within 300 LOC / 5 files. If consistency turns out to need a sixth file, do not exceed the cap: finish the five and list the sixth as a proposed follow-up (DRIVER §5).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Closing or changing any OD other than OD-16, and any part of OD-16 beyond the harness acceptance criterion (see the boundary list).
- The harness (`hilclaw/harness/`, P1-3), its oracle, tolerance comparison, input generation and timing; the calibration kernels and their tests (P1-4, code mode); the C CI gate (rest of P0.5-1).
- The evaluator agent and its contract (P2-3, OD-23), hooks (P2-4), the data-plane layout (OD-8).
- Editing ADR-0001 / ADR-0002, FR-9's text, issue bodies, or posting on GitHub issues (the driver posts the owner notice).
- Answering #5 A-7's open part, B-7 or B-8 on the owner's behalf.

## Follow-ups
- (driver, after the wrap-up push) Post the §9 owner notice on #5 from the text in `## Result`, with the driver tail.
- (planner, next) PLAN P1-3 is marked "오너 확정 필요" and now gates P1-4, the rest of P1-2, the C gate of P0.5-1 and P1-5 slice 3. Raise it as an HQ with a BLOCKED P1-3 task: (1) confirm the reference oracle of `cpu_standin` (NumPy float64 per the #5 A-7 recommendation — also a new external dependency under A-13 — or a stdlib / C double-precision reference); (2) the values no source gives for the first GEMM: memory layout and operand storage order, the C prototype of the kernel; (3) the `hw_source` of a CPU stand-in.
- (planner, after P1-3) P1-4 code task: the three calibration kernels and their tests, implementing ADR-0003.
- (driver or integrator, document mode) Add the landed commit hash to the OD-16 register row.

## Result
