---
id: T-0313
title: Record an ADR on what the start of a first-case instance does when the write of `instance.json` finds its final name taken, and what a second start under a `run_id` in use means (OD-8 sub-question 23 part (ga), for the instances of ADR-0076 decision 1)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-6, FR-13, NFR-1, OD-8]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0109-od8-instance-start-name-taken.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P1-8 (runtime STATE/instance/events schemas, "OD-8 종결 필요(§9)") is open. The write of `runs/<run_id>/instance.json` is fixed: ADR-0025 gives the steps, and `hilclaw/instance_file.py` implements them. When the last step finds the final name taken, the write puts nothing under the name and raises `NameTakenError`. ADR-0025 decision 4 leaves open what the caller does next. That is part (가) of OD-8 sub-question ㉓, together with "what a second start with a `run_id` that is in use means". ADR-0027 decision 5 and ADR-0076 Boundaries leave the same point open. ADR-0076 already fixes what the start of a first-case instance checks before it writes. So the next step of that start, the answer to a taken name, is a design-level part of OD-8 that no open HQ blocks.

This is a design-level OD part. Under DRIVER §9 the executor writes the ADR, a reviewer's approval accepts it, and the driver posts the 7-day owner notice. Nothing here is owner-only: no sentence of #5 or #4 speaks to it (check this, and stop with BLOCKED `requirement-unclear` if one does). UC-1 step 2 says that the system creates the run workspace. The record may cite that sentence but must not read more into it.

The scope is narrow on purpose. It covers the start of an instance of ADR-0076 decision 1 that builds its id by ADR-0027. Which component performs the start (⑰ first part, OD-23) and its order against the first `STATE.json` (⑩) stay open, and the answer must hold whatever they turn out to be. Caller-given names (㉔), branches and continuations (①, FR-6, UC-4) stay open too.

## Required Reading

- `PROCESS/DRIVER.md` §3 (lines 63-77: executor steps 5-6, the naming rule, the time cap), §5 (lines 86-114), §8 (lines 135-139), §9 (lines 141-148).
- `CLAUDE.md`: the rules "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검" and "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0025-od8-instance-file-write.md`: decisions 3 to 6 (lines 36-68), Alternatives row 5 (line 100), Boundaries (lines 117-128, which hold the text of ㉓).
- `ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md`: decisions 1, 5 and 6 (lines 25-31, 57-71), Limits (lines 72-80), Boundaries (lines 105-115).
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md`: the whole file (110 lines). Its decision 3 says what a refusal of the start is (nothing written, every missing member reported). Its Boundaries line 103 names ㉓ (가).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decision 1 (from line 23, "a directory exists only when something was written into it"), decision 8 (lines 127-130), decision 10 (lines 146-149).
- `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md`: decision 1 and Boundaries. They cover what the replacement of `STATE.json` does when no file is there yet; ⑩ stays open.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: the "Record format" section, and decision 3, the "same key" rule that ADR-0025 decision 4 contrasts with.
- `hilclaw/instance_file.py` (module docstring, `NameTakenError`) and `hilclaw/instance_start.py` (module docstring). Read only. They show what the code does today.
- `ARCHITECTURE/UsageCases.md`: UC-1 (lines 69-78) and UC-4 (lines 106-115).
- `ARCHITECTURE/Requirements.md`: FR-6 (line 24), the "행 형식" paragraph (line 84), the OD-8 row (line 99).
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8), the OD-8 section (lines 87-160), and the ㉓, ㉔ and ⑩/⑰ bullets (lines 126-135).
- `ARCHITECTURE/StandardScenarios.md`: §검사 결과 (from line 168), and S3 (from line 76) for continuation.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0109-od8-instance-start-name-taken.md`, in the record format of ADR-0001. Before writing, make sure ADR-0109 is free on `origin/main` and on every remote branch (`git ls-tree`; the unlanded branches of T-0210, T-0231 and T-0264 hold ADR-0068, ADR-0074 and ADR-0088). If it is taken, use the next free number, rename the file, and say so in Result.
2. Status says the record was accepted under DRIVER §9 and is not owner-confirmed. It keeps cited sentences (quoted, with their source) apart from the record's own choices. It names the records it builds on (at least ADR-0025, ADR-0027 and ADR-0076) and says it is revisited if one of them is reverted.
3. Scope: the start of an instance of ADR-0076 decision 1, under a `run_id` that the start built by ADR-0027. The record says how its answer holds while ⑰'s first part (who performs the start) and ⑩ (the order against the first `STATE.json`) stay open. If no answer can hold without fixing one of those, record that as a finding, leave the part open, and do not invent the order.
4. The Decision answers ㉓ (가) for that scope. It weighs alternatives, at least those the question itself names:
   - read the file under the name and take its content, equal in some stated sense, as the start's own write;
   - stop;
   - build another `run_id` and try again.
   For each alternative, the record says what it does to the retried start whose writer died after the last step and before its report (the case ADR-0025 decision 4 names), and to NFR-1 and FR-6. If it adopts any notion of "equal content", it defines that notion; ADR-0025 decision 4 notes that no record defines a canonical form for this file. It states what the start reports and what it leaves on disk. That includes a run directory left with other files and no `instance.json`, whose meaning stays with ⑰'s third part.
5. The Decision says what "a second start with a `run_id` that is in use" means within the scope. It does not decide whether a continuation or a branch is a new run (①, OD-20). It does not decide whether a run may have a caller-given name (㉔). If either one turns out to be needed for the answer, stop and leave that part open rather than decide it.
6. The record adds no member, file, kind of file, tool-failure kind or validity rule to the data plane. It changes no code, `instance.json`, `STATE.json` or `events.ndjson`. Consequences carries an A-13 reading saying so. If the decision cannot be written without such a change, stop with BLOCKED (data-plane schema change).
7. Consequences:
   - name the code slice the record makes possible, if any (for example, how a caller of `hilclaw.instance_file` answers `NameTakenError` once a start component exists), what it waits on (⑰'s first part, OD-23), and name no module or function as binding;
   - list, found by grep, the sentences of earlier records that become less exact, and do not edit them;
   - name the runtime acceptance items, or say there are none.
8. Boundaries list at least: ⑰ (first and third parts), ⑩, ①, ㉓ (나), ㉔, the lock and a second writer (rest of OD-17), OD-23, OD-25, and any change to earlier records, `hilclaw/`, tests, CI, settings files or `HIL-Claw-data`.
9. The edit to `ARCHITECTURE/Requirements.md` touches only the OD-8 row and is made under that register's "행 형식" rule (line 84), which is binding. That means one link for the one new ADR. Any part this record answers of an open item already named in the row is rewritten where it stands. The row does not repeat the record's content and gets no dated paragraph. The status cell is unchanged.
10. The edit to `ARCHITECTURE/OpenDecisionProposals.md` touches only the OD-8 section and follows its "기록 규칙" (line 8). That means one adopted-record line for ADR-0109. The status tail of the ㉓ bullet, and its head status word if it changes, are rewritten in place. The question text stays, the record is not restated, and no dated note is added.
11. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's rules (CLAUDE.md "문서 커버리지 재검사"). Update §검사 결과 exactly as its first paragraph prescribes. Change verdict history only if a verdict changes.
12. No other file changes. `git diff --stat origin/main` lists only the touchesFiles. `git diff --check` is clean. Every relative link added resolves. The OD register has the same number of rows before and after.
13. Document mode (CLAUDE.md A-13): branch `claude/T-0313-<slug>`, context-isolated reviewer cycle of at most 7 rounds, rebase on `origin/main`, direct push to main. The commit message ends with one trailer block, with no blank line inside it, holding `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0313`. Check with `git interpret-trailers --parse` that git parses both. The §9 owner notice on #5 follows, with the §8 footer.
14. Start no compiler, kernel, container or `claude` process (D16).

## Out of Scope

- Any code, test, CI or settings change, including any change to `hilclaw/instance_file.py` or `hilclaw/instance_start.py`.
- ㉓ (나), ㉔, ①, ⑩, ⑰, ⑱; the isolation means; the lock (OD-17); OD-23; owner-only items (OD-25, OD-3, C-6, #5 A/B).
- Editing earlier ADRs (including the "less exact" sentences listed by ADR-0027, ADR-0106 and ADR-0107), UsageCases, the README or the index documents (`EventKinds.md`, `StepValues.md`, `BlobTypes.md`, `SpendAxes.md`).
- The unlanded branches of T-0210, T-0231 and T-0264, and PR #179 (T-0284).

## Follow-ups

- If the record makes a code slice possible, a later code task. It must wait for a start component (⑰'s first part, OD-23).

## Result
- DONE. ADR-0109 (number free on origin/main and every remote branch) landed on main as 99ef08e (document mode, reviewer agent 7 rounds, Approve; trailers checked with `git interpret-trailers --parse`). Task branch deleted locally and on origin.
- Decision: within the scope (ADR-0076 decision 1 instance, `run_id` built by the start by ADR-0027), a taken `instance.json` name makes the start stop: it reads, compares and removes nothing, builds no other id, and reports the id in use apart from an ADR-0076 refusal and from a file-system failure. A second start under an id in use means no run. No "equal content" is defined. ① and ㉔ are not decided.
- Finding handed to ⑩: if ⑩'s order lets the start write the first `STATE.json` before `instance.json`, the stop protects `instance.json` only.
- Edits: OD-8 register row (one link; `㉓ (가)` → `㉓ (가)의 나머지`), OD-8 section (adopted line; ㉓ tail → 부분 답), StandardScenarios recent re-check (no verdict change, no gap). Register rows 30 → 30.
- §9 owner notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6253272646 (window until 2026-10-26).
- Left for the driver: the OD-8 status cell still reads "잔여의 여러 부분 2026-10-07~18". AC 9 kept it unchanged; reviewers suggested "~19" in a later doc task.
- Follow-up: a code task for the caller of `hilclaw.instance_file` that answers `NameTakenError`. It waits for a start component (⑰ first part, OD-23). Runtime acceptance items: none.
