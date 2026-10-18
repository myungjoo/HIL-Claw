---
id: T-0317
title: Record an ADR on whether the start of a first-case instance may take a `run_id` it did not build (OD-8 sub-question 24, for the instances of ADR-0076 decision 1)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-6, FR-13, NFR-1, OD-8]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0111-od8-run-under-given-id.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 180, files: 4}
hq: []
---
## Why

PLAN P1-8 (runtime STATE/instance/events schemas, "OD-8 종결 필요(§9)") is still open. ADR-0027 fixed the form of a `run_id` that the system builds. Its decision 1 left open whether a run may be started under an id the system did not build, meaning a name given by a person or by a caller. That question is OD-8 sub-question ㉔. ADR-0109 then fixed what the start of a first-case instance (ADR-0076 decision 1) does when its own id turns out to be in use. It put a caller-given id outside its scope and named ㉔ in its Boundaries. So the start of a first-case instance now has its required members (ADR-0076) and its answer to a taken name (ADR-0109), but nothing says whether its `run_id` must be one it built. No open HQ blocks this point.

This is a design-level OD part. Under DRIVER §9 the executor writes the ADR, a reviewer's approval accepts it, and the driver posts the 7-day owner notice. It is not owner-only: it is no #5 A/B item, not C-6, OD-25 or OD-3. Check that no sentence of #5 or #4 speaks to run names given by a user or caller. Search the comments of #5 that are not the driver's for `run_id`, run name, naming and label. If one does speak to it, stop with BLOCKED `requirement-unclear` and quote it in Result.

The scope is narrow on purpose. It covers only the start of an instance of ADR-0076 decision 1. Several things stay open, and the answer must hold whatever they turn out to be:
- which component performs the start, and how it gets its inputs from the user (⑰ first part, OD-23, UC-1);
- whether a branch or a continuation is a new run, and under which id it runs (①, OD-20, UC-4, S3);
- how readers treat a found `run_id`. ADR-0027 decision 1 says that a name matching ADR-0004 decision 8 is a valid `run_id` whether or not it is of the built form. That stays as it is.

## Required Reading

- `PROCESS/DRIVER.md`: §3 (lines 63-77, with executor steps 5-6, the naming rule and the time cap), §5 (lines 86-114), §8 (lines 135-139) and §9 (lines 141-148).
- `CLAUDE.md`: the rules "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검" and "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md`: decision 1 (lines 25-31; line 29 holds the ㉔ sentence), decisions 5 and 6 (lines 57-71), Limits (lines 72-80), Alternatives (lines 81-97) and Boundaries (lines 105-115; line 112 holds the text of ㉔).
- `ARCHITECTURE/decisions/ADR-0109-od8-instance-start-name-taken.md`: the whole file (102 lines), especially decision 1 (Scope, its "Outside" bullet), decisions 2 and 4, the Walk-through row for an id given by a caller, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md`: decisions 1 to 3 (lines 25-58) and Boundaries (lines 97-105).
- `ARCHITECTURE/decisions/ADR-0025-od8-instance-file-write.md`: decision 4 (lines 48-54) and Boundaries (lines 117-128).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decision 8 (lines 127-130, the `run_id` pattern) and decision 10 (lines 146-149).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: the "Record format" section (from line 146).
- Read only, to see what the code does today: `hilclaw/run_id.py` (module docstring), `hilclaw/layout.py` (`check_run_id`, line 60) and `hilclaw/instance_start.py` (module docstring).
- `ARCHITECTURE/UsageCases.md`: UC-1 (lines 69-78), the list in step 1 of what the user gives, and UC-4 (lines 106-115).
- `ARCHITECTURE/Requirements.md`: FR-6 (line 24), FR-13 (line 31), the "행 형식" paragraph (line 84) and the OD-8 row (line 99).
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8) and the OD-8 section (lines 87-161), especially the ①, ⑰, ㉓ and ㉔ bullets (lines 124, 130, 135, 136).
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과 (from line 168), S2 (from line 66, CI as the actor) and S3 (from line 76, continuation).

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0111-od8-run-under-given-id.md`, written in the record format of ADR-0001. Before writing, check with `git ls-tree` that ADR-0111 is free on `origin/main` and on every remote branch. The unlanded branches of T-0210, T-0231 and T-0264 hold ADR-0068, ADR-0074 and ADR-0088. If ADR-0111 is taken, use the next free number, rename the file and its touchesFiles entry, and say so in Result.
2. Status:
   - says the record was accepted under DRIVER §9 and has not been confirmed by the owner;
   - keeps cited sentences, quoted with their source, apart from the record's own choices;
   - states the result of the owner-sentence search described in Why;
   - names the records it builds on (at least ADR-0027, ADR-0076 and ADR-0109) and says the record is revisited if one of them is reverted.
3. Scope: the start of an instance of ADR-0076 decision 1. The record says how its answer holds while ⑰'s first part (who performs the start and how it gets its inputs) and ① (branches and continuations) stay open. If no answer can hold without fixing one of them, record that as a finding, leave the part open, and do not invent it.
4. The Decision answers ㉔ for that scope: may such a start run under a `run_id` it did not build, and if so, what is required of that id beyond ADR-0004 decision 8 and what checks it. Weigh at least these three alternatives:
   - (a) the start takes no `run_id` from its caller and always builds its own by ADR-0027;
   - (b) the start accepts a caller-given id that matches ADR-0004 decision 8, with stated extra requirements and a stated checker;
   - (c) leave it open.
   For each alternative, state what it does to the following:
   - ADR-0109's stop, and the four origins of a taken name that ADR-0109 decision 2 lists;
   - ADR-0027 decision 5 (uniqueness is improbable collision, not a check);
   - a CI actor (UC-1, S2) that wants to find its run again;
   - FR-6 and NFR-1.
   A wish for a human-readable label is not a reason to admit a given `run_id`. Any label member would be a data-plane change and is out of scope (criterion 6).
5. ADR-0027 decision 1 stays as it is: a found `run_id` that matches the pattern and is not of the built form is still a valid `run_id` for every reader, and nothing refuses such a run because of its id. The record says this explicitly and binds only what the start takes. It does not decide whether a branch or a continuation runs under the id it comes from (①, OD-20). If the answer turns out to need that decided, stop and leave that part open.
6. The record adds no member, file, kind of file, tool-failure kind or validity rule to the data plane. It changes no code, `instance.json`, `STATE.json` or `events.ndjson`. Consequences carries an A-13 reading saying so. If the decision cannot be written without such a change, stop with BLOCKED (data-plane schema change).
7. Consequences:
   - name the code slice the record makes possible, if any (for example, a start component that takes no `run_id` parameter and calls `hilclaw.run_id`), what it waits on (⑰'s first part, OD-23), and name no module or function as binding;
   - list, found by grep, the sentences of earlier records that become less exact (at least the ㉔ sentences of ADR-0027 and ADR-0109, if they do), and do not edit them;
   - name the runtime acceptance items, or say there are none;
   - a name check over `hilclaw/`, `tests/` and `ARCHITECTURE/` showing that no kind, member, `step` value or reserved kind is added.
8. Boundaries list at least: ⑰ (first and third parts), ⑩, ①, ㉓ (나) and ㉓ (가) outside ADR-0109's scope, instances outside ADR-0076 decision 1, a human-readable label for a run, the lock and a second writer (the rest of OD-17), OD-20, OD-23 and OD-25. They also list any change to earlier records, `hilclaw/`, tests, CI, settings files or `HIL-Claw-data`.
9. The edit to `ARCHITECTURE/Requirements.md` touches only the OD-8 row and follows that register's "행 형식" rule (line 84), which is binding. Add one `**확정분**:` link for the one new ADR, with a topic of a few words. Rewrite in place the part of the open item that this record answers, in the `**잔여**:` list where ㉔ or "하위 질문 ①~㊱ 가운데 미결분" stands. Do not restate the record's content, add no dated paragraph, and leave the status cell unchanged.
10. The edit to `ARCHITECTURE/OpenDecisionProposals.md` touches only the OD-8 section and follows its "기록 규칙" (line 8). Add one adopted-record line for ADR-0111, of the form that rule gives. Rewrite in place the status tail of the ㉔ bullet (`→ 부분 답: …. 남음: …` or `→ 답함: …`) and its head status word (미결 / 일부 답함 / 답함). Keep the question text, do not restate the record, and add no dated note.
11. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's own rules (CLAUDE.md "문서 커버리지 재검사"). Update §검사 결과 exactly as its first paragraph prescribes: rewrite the "최근 재검사" line in place, and add a "판정 변화 이력" entry only if a verdict changes or a gap is found or closed.
12. No other file changes. `git diff --stat origin/main` lists only the touchesFiles. `git diff --check` is clean. Every relative link added resolves. The OD register has the same number of rows before and after.
13. Document mode (CLAUDE.md A-13): work on branch `claude/T-0317-<slug>`, run a context-isolated reviewer cycle of at most 7 rounds, rebase on `origin/main`, and push directly to main. The commit message ends with one trailer block, with no blank line inside it, holding `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0317`. Check with `git interpret-trailers --parse` that git parses both. The §9 owner notice on #5 follows, with the §8 footer.
14. Start no compiler, kernel, container or `claude` process (D16).

## Out of Scope

- Any code, test, CI or settings change, including `hilclaw/run_id.py`, `hilclaw/layout.py`, `hilclaw/instance_start.py` and `hilclaw/instance_file.py`.
- ①, ⑩, ⑰, ㉓ (나), the isolation means, the lock (OD-17), OD-20 and OD-23. Also owner-only items (OD-25, OD-3, C-6, #5 A/B).
- Editing earlier ADRs, including the "less exact" sentences listed by ADR-0027, ADR-0106, ADR-0107 and ADR-0109. Also UsageCases, the README and the index documents (`EventKinds.md`, `StepValues.md`, `BlobTypes.md`, `SpendAxes.md`).
- The unlanded branches of T-0210, T-0231 and T-0264, and PR #179 (T-0284; it touches only `hilclaw/clang_build.py` and `tests/test_clang_build.py`).

## Follow-ups

- If the record makes a code slice possible, a later code task. It must wait for a start component (⑰'s first part, OD-23).

## Result
