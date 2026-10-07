---
id: T-0036
title: Write the ADR fixing the verification run of a C gemm kernel on cpu_standin (program and process, drawn inputs, the reference and the comparison as the owner answered HQ-0004, verdict) and reflect it in the ARCHITECTURE documents
phase: P1
status: BLOCKED
commitMode: doc
coversReq: [FR-9, OD-16, OD-5, OD-13, FR-10, C-7, "#5 A-7", "#5 B-7", "#5 A-6", "#5 A-12", "#5 D6"]
dependsOn: [T-0020, T-0028, T-0030, T-0031]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0010 at planning time)
estimatedSize: {loc: 220, files: 4}   # one new record of about 120-170 lines, the rest are in-place edits of a few lines each
hq: [HQ-0004]
---
## Why
PLAN P1-3 is the harness: random inputs from a seed that is not a file, an f64 reference, a tolerance comparison with the tolerance as an instance parameter, repeated timing. The timing half is on `main` (ADR-0007, ADR-0009; T-0029, T-0032, T-0033, T-0034). The **verification half** — the run that says whether a kernel computes its operation — does not exist, and nothing can be built on it: P1-4 (the three-state calibration of ADR-0003), the "harness pass" half of the C gate (rest of P0.5-1; #9 words it as "correctness against the f64 reference"), the evaluator of P2-3 and the first end-to-end run of P2-5.

PLAN marks P1-3 "오너 확정 필요". Two owner items (#5 A / B items, owner-only under DRIVER §9) stand in front of the verification half, and every record so far lists them under "Boundaries, owner-only" (ADR-0002, 0003, 0007, 0008, 0009):
- the **reference oracle of `cpu_standin`**: #5 A-7, "Still open (recommendation recorded, owner to confirm)" — "system-generated NumPy float64 reference, tolerance as an instance parameter (A-6). This is a stand-in-only answer to B-7, not the general one." FR-9 carries it as "`cpu_standin`의 오라클은 NumPy float64가 A-7 권고, 확정 대기";
- the **tolerance vocabulary** and default values: #5 B-7 (unanswered item of the issue body), the rest of OD-5 ("tolerance 어휘 ... 는 #5 B-7 답변 후 확정"); #5 A-6 fixed only that the tolerance is a user-set instance parameter and a hard floor.

The task is **BLOCKED on HQ-0004**. HQ-0004, verbatim:

> PLAN P1-3 (verification half of the harness) needs the two owner items it is marked with, for the first case only: `cpu_standin`, kind `gemm`, fp32, C kernel. (1) Reference oracle (open part of #5 A-7): (a) NumPy float64 as recommended there — `numpy` becomes the first runtime dependency of `hilclaw` (a new external dependency, A-13), exact pin; (b) a float64 reference written in C inside the harness and built with clang like the timing driver, no new dependency; (c) something else (name it)? (2) Tolerance vocabulary of the instance parameter for this case (#5 B-7): (a) per-element `rtol` and `atol`, pass iff |out - ref| <= atol + rtol * |ref| for every element, any non-finite output fails; (b) another form (name it)? (3) Defaults: (a) none — an instance must state its tolerance; (b) default values (name them)? Not asked here: vendor golden outputs, downstream-metric thresholds, datasets (B-8), other kinds, dtypes and backends.

Background of the three questions (facts, not answers):
- (1) `pyproject.toml` has no runtime dependency at all (`[project]` has no `dependencies`; the `dev` group pins `pytest==9.1.1` and `ruff==0.16.10`); the owner's HQ-0002 answer made pins deliberate. The first operations (#5 B-4) reach M = 512 with gate/up 2048→8192: one reference product is 512 × 2048 × 8192 ≈ 8.6e9 multiply-adds, which rules out a reference in pure Python. With (a) the kernel's output (up to 512 × 8192 fp32 values, 16 MB) has to reach the Python process; with (b) reference and comparison can stay inside the process that called the kernel. Layer-2 languages are {Python, POSIX sh, C}; the timing driver (ADR-0009) is C with the C library and POSIX only.
- (2) #5 A-6 names "per-dtype rtol/atol, downstream-metric thresholds, user-defined checks" as the vocabulary to be fixed after B-7. ADR-0002 version 1 has no spec field for a tolerance; ADR-0003 decision 7 requires only that a calibration test passes its tolerance explicitly.
- (3) StandardScenarios S0 step 2 starts an instance with "tolerance 기본값"; no document gives a value, and ADR-0003 places defaults with #5 B-7.

When the owner answers on #5 with `HQ-0004`, the driver sets this task back to `TODO` (DRIVER §3-2). The executor then reads the recorded `decision` in `PROCESS/STATE.json` and the owner's comment in full, and takes the answers as **fixed inputs** of the record. If the answer leaves one of the three points open, or goes beyond what this file covers, do not fill the gap: return BLOCKED ("requirement unclear") with the exact remaining question.

Why a record and not code (planner, DRIVER §6): beside the two owner items the verification run has design points that no document fixes and that the earlier records left to "the harness design (PLAN P1-3)" — how inputs are drawn, how many draws, shapes outside the `op_signature` (OD-16 sub-question ①), the relation of verification inputs to timing inputs (OD-13 sub-question ⑦), whether verification shares a program with timing (ADR-0009 Consequences "Verification half"), the verdict and its report. They are design-level (OD-16 and OD-13 are not owner-only), so the task that needs them carries the record that closes them (DRIVER §6, §9). The route used so far is two tasks, record then module (ADR-0007 → T-0029, ADR-0009 → T-0032..0034). **This task writes the record**; it ticks **no PLAN checkbox**.

Why this item now (planner, 2026-10-07 UTC, judged from the files): after T-0035 no P0.5 or P1 slice is left that needs neither the owner nor an OD closure. P0.5-3 is BLOCKED on HQ-0003 (T-0014, unanswered on #5); the rest of P0.5-1 and P1-4 wait for this half; the rest of P0.5-4 is the owner's hook registration. Raising the question now starts the owner's lead time on the item that the most later items hang on. No open PR at planning time; the latest #5 comment is the ADR-0009 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6026950959).

Planner's judgements — **the reviewer is asked to re-check them**:
- The register home of the design points is **OD-16** (its confirmed part is the harness; sub-question ① is registered there) with pointers in OD-13 (sub-question ⑦) and OD-5 (the vocabulary, as the owner answered). No new OD number.
- Reflecting the owner's HQ-0004 answers in the FR-9 row and the OD-5 row is a reflection of a recorded owner decision (with the comment URL), not a decision of the executor.
- A-13: document mode, no code, no schema file. If the answer to (1) is NumPy, the dependency is **approved by that answer but not added here** (the code task adds the pin).

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) — mandatory for every task (§6)
- PROCESS/DRIVER.md §0 last bullet, §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §8 (driver tail on #5 comments), **§9 (the whole section)**, §11 row D6
- PROCESS/STATE.json — `humanQuestions[]` entry `HQ-0004`: `question` and `decision`; then the owner's reply on #5 in full (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`, every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6026950959)
- CLAUDE.md — 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", **"세션 진입 점검"** (before the first edit: `gh pr list`, issues #4, #5, #7, #8), "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (document mode and the BLOCKED reasons)
- .claude/skills/dev-item-address/SKILL.md — the procedure (document mode: steps 2, 7, 9-12, 15); .claude/skills/dev-code-review/SKILL.md — what the reviewer checks (in particular "no invented decisions")
- ARCHITECTURE/Requirements.md — rows FR-1, **FR-9**, FR-10, NFR-3, NFR-4, C-7; the "Open Decisions" preamble (status vocabulary, update rule, one-line rule); register rows **OD-5**, OD-10, OD-11, **OD-13**, OD-14, **OD-16**, OD-18, OD-28
- ARCHITECTURE/OpenDecisionProposals.md — the header and sections **OD-5**, **OD-13** ("하위 질문" ⑦), OD-14, **OD-16** (threats A and B, "확정분", "하위 질문" ①-④)
- **ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md — the whole record** (the functional test and the contract, the three states, decision 7 "independence from the oracle and the tolerance", Consequences for P1-3 / P1-4)
- **ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md — the whole record** (prototype, operands, decision 6 guarantees — inputs are not promised finite —, decision 7, the sentence "how close the result must be is the tolerance", Boundaries)
- **ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md — the whole record** (decisions 2, 5, 6, 8, 10; Consequences "Verification half": what sharing a program would reopen)
- ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md — decision 2 (what a timed interval excludes: reference, comparison); ADR-0002 — Boundaries (no tolerance field in spec version 1); ADR-0001 — the closing **"Record format"** section; ADR-0004 — the path-table rows under `…/measure/…` and `…/eval/…` (to name no file there)
- Issue #5 comments (owner inputs; fixed): A-6 `gh api repos/myungjoo/HIL-Claw/issues/comments/5933950693 --jq .body`; **A-7** `.../comments/5944117402` ("Still open"); A-12 `.../comments/5946779596`; B-4 `.../comments/5944412285`; D6 `.../comments/5986348506`; the issue body items B-7, B-8
- Existing code the record must not contradict (not edited): `hilclaw/clang_build.py`, `hilclaw/local_run.py`, `hilclaw/harness/timing.py`, `hilclaw/harness/timing_build.py`, `hilclaw/harness/timing_driver.c` (module docstrings / file header and the public functions), `pyproject.toml`
- PROCESS/tasks/T-0031-adr-cpu-standin-timing-run.md — `## Acceptance Criteria` "Process" and `## Result` (how a record closing one part of an OD landed: register precedent, review findings, notice text); PROCESS/tasks/T-0020-adr-od16-harness-calibration.md — `## Result`; PROCESS/tasks/T-0032-timing-run-python-side.md and T-0033-timing-driver-c-source.md — `## Result` (provisional conventions a verification program may reuse); PROCESS/PLAN.md items P0.5-1, P1-3, P1-4

## Acceptance Criteria
What is **fixed** and must be taken as input, not re-decided:
- The owner's answers to HQ-0004 (1)-(3), exactly as far as they go.
- #5 A-6 / FR-9: correctness is a hard floor; the tolerance is a user-set instance parameter; verification uses inputs not exposed to the coder (shape / seed) in a harness the coder cannot modify; no input value is written to a file readable by the coder. #5 A-7 ② (C, clang, OpenMP / SIMD allowed), A-12 point 4 (the harness is one sub-module of the package), C-7 (POSIX).
- ADR-0003 (the functional test, the contract, the three states and what calibration requires of the harness), ADR-0008 (the call and the caller's guarantees), ADR-0007 decision 2, ADR-0009 as it is. The existing modules as they are.

What the ADR **decides**. Points marked **pending HQ-0004 (n)** take their content from the owner's answer and are written as *cited*; the rest is the executor's to work out and justify from the fixed inputs, with the alternatives considered and one or two lines of reason each, every value no source gives marked as the record's own; the reviewer's Approve confirms it.
1. **Scope and terms**: the verification run of one built attempt of a C kernel of ADR-0008 at `cpu_standin`, kind `gemm`, fp32. Not the timing run, not an FR-10 tool contract, not a simulator, board or remote mechanism, no other kind, dtype or language.
2. **Program and process**: who provides `main`; whether the verification program is the timing driver, a second driver source, or one source with two modes, and whether one executable or one run serves both — ADR-0009 Consequences names what sharing reopens (its decisions 5, 6, 8) and that no reference or comparison may lie inside a timed interval; say what is reopened, or that nothing is. The statement next to OD-14 that ADR-0009 decision 2 makes (a process is a mechanism; no sandbox or timeout policy adopted) is repeated for this run.
3. **Drawn inputs**: where the values of `a` and `b` come from (a seed that is a parameter of the run, never a file — FR-9), their range and why, the number of draws of one verification run (a constant or a parameter), and whether shapes other than the `op_signature`'s are drawn (OD-16 sub-question ①: decide it for this case with reasons, or leave it open by name). Relation to the inputs of a timing run of the same attempt (OD-13 sub-question ⑦): decide or leave open by name. Non-finite and corner-case inputs: say whether any is drawn; adopting a "strengthened oracle" of OD-16 is not in scope.
4. **The reference** — **pending HQ-0004 (1)**: what computes it, in which precision, from which values (the fp32 inputs widened to float64 — say so), and where it runs. Design consequences that follow from the answer are the record's own and must be argued: with a Python-side reference, how the kernel's output and the inputs reach it without a file the coder can read; with a C reference, where its source lives and that it is harness code, not kernel code. If the answer adds a dependency, the record says that the code task adds the pin and names no version.
5. **The comparison** — **pending HQ-0004 (2)**: the predicate, element by element or as answered; the treatment of NaN and infinity in the output (as answered, otherwise the record's own and marked so); that the tolerance is a parameter of the run, given by the caller from the instance (FR-9).
6. **Defaults** — **pending HQ-0004 (3)**: none, or the values the owner names. The record invents no value.
7. **The verdict and the report**: pass / fail of a run over all its draws; what a broken run is (status, timeout, malformed report) and that it is neither pass nor fail; what the program reports to the Python side and over which channel, fixed only as far as the code task needs, as an internal interface and **no data-plane field** (ADR-0009 decision 8 precedent). Whether the kernel's own output on descriptor 1 is handled as in ADR-0009.
8. **Calibration**: show that the run so defined can distinguish the three kernels of ADR-0003 (conforming, failing, functional-pass / contract-violating) and say what the "functional test on inputs fixed in advance" is in terms of this run, without requiring more than ADR-0003 does.
9. **Parameters and what stays the caller's** (dimensions, seed, tolerance, number of draws if a parameter, time limit, build flags, environment) — no flag, thread count or time-limit value is decided.
10. **Limits**: what the run does not show or protect against (a kernel that reads the reference or the report channel in a shared process, a kernel correct only for the drawn range), each with the place where it is decided (OD-16, OD-14).

What the ADR must **not** decide — name each as a boundary, with the place where it is decided:
- Anything of #5 B-7 beyond the answer: vendor golden outputs, downstream-metric thresholds, user-defined checks, tolerances of other dtypes; datasets (#5 B-8); the oracle of any backend other than `cpu_standin`.
- The measured quantity and its direction (OD-1 / #5 A-4); OD-3; OD-25; C-6.
- Any defence of OD-16 beyond the FR-9 minimum, any sandbox, isolation, resource limit or timeout hierarchy of OD-14, the isolation means of OD-8.
- Build settings; whether a kernel may link another library; the order of verification and timing inside a round and what follows a failed verification (FR-1, OD-10, OD-19).
- Fields and schemas of `eval`, `sim.json`, `board.json`, `instance.json`, any event kind or payload (PLAN P1-8); a tolerance field of the spec (ADR-0002); the FR-10 tool contract and exposure form (P1-1, OD-18).
- Any code, C file, test, CI change, or any change to `hilclaw/`, `tests/`, `.github/`, `pyproject.toml` or the `HIL-Claw-data` repository.

If a point of 1-10 cannot be written without an excluded item or without an owner fact the answer does not give, do not fill the gap: narrow the point and say so, or return BLOCKED with the exact question (DRIVER §3, §9).

The record (`ARCHITECTURE/decisions/ADR-NNNN-od16-cpu-standin-verification-run.md`, new; NNNN = the next free number on `origin/main` at execution time, ADR-0010 at planning time; the slug may be adjusted):
- Follow the "Record format" section of ADR-0001: Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References, in this order; English.
- **Status**: accepted under DRIVER §9 (D6) by reviewer approval, with the date; which parts are the **owner's decisions** (HQ-0004, with the comment URL — these are not subject to the 7-day window) and which are the record's own design choices (those are: the owner may object on #5 within 7 days of the notice, and a reverting task is then created); that it builds on ADR-0003, 0007, 0008 and 0009 and is revisited if one of them is reverted.
- Length about 120-170 lines; enough for the author of the verification program and of its Python side to write against it without reading the issues again.
- **Consequences** list what follows for later tasks without doing them: the code tasks of the rest of P1-3 (and the dependency pin, if any), P1-4 (the three C kernels and their tests), the "harness pass" half of the C gate (P0.5-1), P1-8 (what a result record must be able to hold, no field named), the spec (whether a tolerance is shown to the coder stays open — ADR-0002).
- **References** by stable handle: Requirements IDs, issue comment URLs, proposal sections, PLAN items, the ADRs, the modules.

Edits of existing documents (same commit as the record — register update rule):
- `ARCHITECTURE/Requirements.md`: the **FR-9** row — only the two clauses that say "확정 대기" / "어휘는 #5 B-7 답변 후 확정", rewritten to what the owner answered for this first case, with the rest of B-7 still shown as open; the **OD-5** row ("잔여"), the **OD-16** row (what the record fixed, the open rest kept visible) and, only if sub-question ⑦ is decided, the **OD-13** row. Do not renumber, add or remove any OD row; no other FR / NFR / C row; **no new OD number** — if one seems needed, return BLOCKED with the reason.
- `ARCHITECTURE/OpenDecisionProposals.md`: sections OD-5 ("잔여"), OD-16 (heading note, sub-question ① and any sub-question the record raises), OD-13 (sub-question ⑦, pointer or update). Keep the old sentences visible as T-0030 / T-0031 did; delete no proposal text.
- `ARCHITECTURE/StandardScenarios.md`: re-run the coverage check (CLAUDE.md "문서 커버리지 재검사") for every step that cites FR-9, OD-5 or OD-16 or rests on verifying a kernel (S0, S1, S7 at least), and update "검사 결과": heading date / note, one dated passage, the affected rows. State the outcome in the commit body even if no verdict changes.
- In-place edits keep the language of the text around them (Korean).
- No edit to ADR-0001..0009, `ARCHITECTURE/UsageCases.md` (a sentence that became false is a follow-up), `CLAUDE.md`, `README.md`, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills, the agents, the issue #5 body, or any file under `hilclaw/`, `tests/`, `.github/`.

Tests:
- None. Document mode: no code changes, so CLAUDE.md test rules ①-④ do not apply. The document checks below replace steps 4, 6 and 8 of dev-item-address.

Document checks (record the outcome of each in `## Result`; scripts used for them are **not committed**):
- Session-entry check before the first edit: `gh pr list --repo myungjoo/HIL-Claw --state open` and issues #4, #5, #7, #8 read for anything newer than this file about the oracle, the tolerance, OD-16 or the harness. An open PR editing the OD register or the OD-5 / OD-13 / OD-16 sections is BLOCKED ("open PR conflict"). An owner objection to ADR-0003 / 0007 / 0008 / 0009 that contradicts this task is BLOCKED ("requirement unclear"), quoting the comment.
- Every sentence marked as the owner's is traceable to a quoted line of the HQ-0004 answer; nothing the answer does not say is presented as the owner's.
- Decisions 2-8 are checked against ADR-0003 (decisions 2-7), ADR-0007 decision 2, ADR-0008 decisions 6-7 and ADR-0009 decisions 2, 5, 6, 8; list the pairs checked. Nothing contradicts the docstrings of the existing modules.
- Every relative link in the new record and in the edited lines resolves to an existing file or anchor.
- OD numbers: the count (29) and numbering of the register rows are unchanged; `git diff origin/main -- ARCHITECTURE/Requirements.md` touches only the rows named above.
- Nothing in the record states an excluded item as decided.
- `git ls-files --eol` shows `i/lf` for the changed files; `git diff origin/main --stat` lists only the new record and the three documents.
- CI is not a gate for document mode, but the push to `main` triggers the workflow: check the `push` run with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion; if it is not `success`, do not fix forward — record it and say so in the returned summary.

Process (document mode, CLAUDE.md A-13, dev-item-address steps 9-12 and 15):
- Before anything else, the §3-5 landed check: `git log origin/main --grep='^Task: T-0036'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0036 --state all`.
- Branch `claude/T-0036-adr-cpu-standin-verification-run` from `origin/main`. Commit and push the branch; **no PR**.
- Reviewer cycle: spawn a fresh-context `dev-reviewer` sub-agent, give it the branch name (review target = diff against `origin/main`) and this task file's path. Ask it explicitly to check (a) the planner's judgements at the end of `## Why` (OD-16 as the home, reflecting the owner's answers in FR-9 / OD-5, the A-13 reading); (b) that the owner's answers are rendered exactly and nothing beyond them is attributed to the owner; (c) that no excluded item is decided and no defence of OD-14 / OD-16 is adopted or rejected; (d) that decision 2 respects ADR-0009 and ADR-0007 decision 2, and decision 8 respects ADR-0003; (e) the register and coverage-check updates. Address findings and re-request review until Approve with nothing trivially fixable left; more than 7 rounds is BLOCKED. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Landing: `git fetch origin`, rebase the branch onto `origin/main`, then squash to **one** commit (`git reset --soft origin/main` + commit — only after the rebase). `git show --stat HEAD` must list only the new record and the three documents. If the rebase needed conflict resolution that changed content, go back to review.
- Commit message: English; subject starts with `T-0036:`; the body gives decisions 1-10 in one line each (owner's or the record's own), the boundaries, the register edits and the coverage re-check outcome; it ends with the trailers, in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0036`, then any attribution trailer your session requires.
- Push with `git push origin HEAD:main` (fast-forward). If rejected because `main` moved, fetch, rebase and retry (at most 3 times); never `git push --force*`, and never push the rewritten branch back to its remote branch. Delete the remote branch and the local branch in **separate** commands and only after the push to `main` is confirmed (T-0012 incident), then check out `main` at `origin/main`.
- **Owner notice (DRIVER §9)**: do not post it yourself unless the driver's spawn prompt tells you to. Put the ready-to-post English text in `## Result`: heading `### OD-16 / OD-5 — the verification run at cpu_standin fixed by ADR-NNNN under DRIVER §9 (T-0036)`, what was decided in six lines or fewer, the record's path and commit, which parts are the owner's HQ-0004 answers and which are the record's own, the readings to check, the boundaries left open, the A-13 reading, the date on which the 7-day window ends; last line `— posted by driver`.
- `## Result`: fill it in **after** the push, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The landed commit must not contain the task file. Record: commit hash, review rounds and findings, the decisions with their reasons, the boundaries, the document-check outcomes, the notice text, follow-ups.
- `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. This task ticks **no** PLAN checkbox; say so in `## Result`.
- Size: one new file of about 120-170 lines and three small edits; within 300 LOC / 5 files. If consistency needs a sixth file, finish and list it as a proposed follow-up (DRIVER §5).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Deciding any of HQ-0004 (1)-(3), or anything of #5 B-7 / B-8 the answer does not cover.
- Any code or C source: the verification program, a reference implementation, the Python side, calibration kernels, a CI job, a dependency pin, and their tests.
- Changing the timing run (ADR-0009) or the measurement policy (ADR-0007); if decision 2 would need that, state it as a consequence and a follow-up task, do not edit those records.
- A simulator, a board, the remote (LAN / SSH) path, any kind other than `gemm`, any dtype other than fp32, any kernel language other than C.
- Editing ADR-0001..0009, FR / NFR / C rows other than the two FR-9 clauses, issue bodies, or posting on GitHub issues without the driver's instruction.

## Follow-ups
- (driver, after the wrap-up push) Post the §9 owner notice on #5 from the text in `## Result`, with the driver tail.
- (planner, next — code mode, two or more slices) The verification run as recorded: the C side and the Python side under `hilclaw/harness/` (and the exact dependency pin if the answer to HQ-0004 (1) is NumPy); real-clang tests run on CI only (the driver machine has no compiler). Then P1-4: the three calibration kernels of ADR-0003 for `gemm` and their tests; then the "harness pass" half of the C gate (ticks P0.5-1). P1-3 is ticked when the verification code is on `main`.
- (integrator, document mode) Tick #5 B-7 in the issue body as far as answered and note the A-7 "Still open" line as closed; fix any UsageCases sentence the record made false.
- (planner, meanwhile, independent of HQ-0004) Design-level closures under DRIVER §9 that later items need: OD-18 (exposure form of the FR-10 tools, before P1-1) and OD-17 with #8 M7 (before the runtime `STATE.json` of P1-8).

## Result
