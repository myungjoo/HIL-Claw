---
id: T-0311
title: Record ADR-0108, whether the compiler's log of the timing build of `sim.run` / `board.run` is kept and, if so, in which file of the attempt, by which side and with what answer when it cannot be written (OD-18 sub-question 19 part (da), for the runs the existing contracts cover)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, FR-6, OD-18]
dependsOn: [T-0310]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0108-od18-run-tools-timing-build-compiler-log.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` have contract records ADR-0061 to ADR-0067, ADR-0106 and ADR-0107. Sub-question ⑲ of OD-18 has four parts. (가) is answered (ADR-0067). The sameness part of (라) is answered (ADR-0107). The source and values of (라) wait on OD-14. (나) is on the unlanded branch of T-0210 (HQ-0021). **Part (다) is open and is not blocked**: "타이밍 빌드의 컴파일러 로그를 보존하는지와 시도의 어느 파일에 보존하는지(⑱ (나)·`build.json`과 함께)".

ADR-0065 decision 9 and Boundaries list "the compiler's log (⑲ (다))" among what still stops the `cpu_standin` operation of the run tools. ADR-0061 decision 7 says the log "is not returned under this record" and that the owner's keeping answer (HQ-0020 point 2) "was given for the verification build". ADR-0078 answered the counterpart for `correctness.check` (⑱ (나)). Its Boundaries call that answer "only a candidate" for the timing build.

This is a design-level OD part. Under DRIVER §9 the executor writes the ADR, and a reviewer's approval accepts it, with the 7-day owner notice. Nothing here is owner-only. The owner's O2 (HQ-0020 point 2) speaks of the verification build only. The record may cite it, but must not present an answer for the timing build as the owner's.

## Required Reading

- `PROCESS/DRIVER.md` §3 (lines 63-77, executor steps 5-6, naming and time cap), §5 (lines 86-114), §9 (lines 141-148).
- `CLAUDE.md` rules "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: the whole file (150 lines). It is the counterpart record: which builds' logs are kept, path and name, form, what the log may hold, the log keeper as a fifth thing, the order of the write, `build_log_unwritable`, and the size bound left open.
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: decision 7 (lines 86-97, the build that ended not ok is a broken result, and the log is not returned); Boundaries (lines 157-170, the text of ⑲).
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md`: decision 2 (lines 33-54, the "four things"); decision 4 (lines 64-76); decision 5 (lines 77-90, what crosses the cut); decision 7 (lines 98-110); decision 9 (lines 117-124); Boundaries (lines 179-190).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md`: decision 3 (lines 53-65, `step` values and `execution`); decision 6 (lines 80-98, the order of a call).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: decision 3 (lines 45-65, `condition`); decision 8 (lines 107-112, what a result never holds).
- `ARCHITECTURE/decisions/ADR-0066-od18-run-tools-mock-script.md`: decisions 2 and 6 (lines 33-43, 80-96, what the mock's script is asked with).
- `ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md`: decisions 1-3 (lines 26-59). Both builds compile the kernel sources with one compiler, one set of flags and one environment, so the two logs differ only by the harness program and what the compiler does with it.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: Context (lines 16-27, O1/O2/O4 as quoted there); decision 5 (lines 105-109).
- `ARCHITECTURE/decisions/ADR-0101-od8-failure-kind-change-and-step-values.md`: decision 3 (lines 39-46). A failure kind's name is never reused within one tool's contract, and its meaning is fixed.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decisions 3, 4 and 9 (lines 86-105, 131-145).
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and the OD-18 row (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8), the OD-18 section (from line 262), the ⑲ bullet (line 334).
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과 (from line 168).
- Open branch, read only: `origin/claude/T-0210-od18-run-tools-operation-tool-failure` holds ADR-0068 (⑲ (나), unlanded, HQ-0021). Read its decision 9 table and Boundaries so that this record does not contradict it. Do not cite ADR-0068 as accepted, and do not depend on it.

## Acceptance Criteria

1. A new file `ARCHITECTURE/decisions/ADR-0108-od18-run-tools-timing-build-compiler-log.md` in the record format of ADR-0001 ("Record format"). Before writing, confirm with `git ls-tree` on `origin/main` and with `git branch -r` / `git ls-tree` on every remote branch that ADR-0108 is unused. If it is used, take the next free number and rename the file. List the rename in Result.
2. Status says that the record was accepted under DRIVER §9 and does not claim owner confirmation. It marks owner sentences (quoted word for word with their source), cited sentences and the record's own design apart, as ADR-0078 and ADR-0107 do. It names the records it builds on and whose objection windows are still running (at least ADR-0078 and ADR-0107), and says that it falls with them if they are reverted.
3. Scope: the timing build of a call of `sim.run` or `board.run` about a run of ADR-0061 decision 1 (the first case at `cpu_standin`, and the mock). Other backends, `profiler.collect`, ⑫ and the isolated environment are out.
4. The Decision answers ⑲ (다) for that scope, with alternatives weighed and the choice stated. At least these points:
   - (a) **Whether the log is kept, and of which builds.** Weigh at least: keep as ADR-0078 does for every build whose compiler ended; keep only for builds that ended not ok; do not keep, on the ground that ADR-0107 makes the verification build's log of the same attempt cover the kernel. For the last alternative, say what it would miss: an attempt timed and never checked, a different harness program, a change of the settings source between calls (ADR-0107 Limit 3). Base the answer on FR-6 and on the reading of #5 A-2 that ADR-0078 decision 2 made. Do not claim that O2 covers the timing build.
   - (b) If kept: **the path and name** of the file in the attempt tree, distinct from the check's file of ADR-0078 decision 3 and one per call identity of these tools (`step` value and `execution`, ADR-0062 decision 3), with the reasoning of ADR-0004 decisions 3, 4 and 9. Also **the form** and **what the log may hold**: take over ADR-0078 decisions 4 and 5 by citation where they fit, and do not restate them.
   - (c) If kept: **the writing side and the route.** If the answer is a log keeper handed to the operation, say that it amends ADR-0065 decision 2 ("four things") and the table of decision 5, and the things the mock's script is asked with (ADR-0066 decision 6), without editing those records, as ADR-0078 decision 6 amended ADR-0056. Give the new rows of the table.
   - (d) If kept: **the place of the write in the order of a call** (ADR-0062 decision 6), and **what the call answers when the write fails.** Name the failure kind and give the sentence a caller may rely on. The kind must satisfy ADR-0101 decision 3: a *name* of ADR-0001, not used before by these tools' contracts, no reserved kind. State whether the name equals the check's `build_log_unwritable` and why. Before choosing a name, grep `hilclaw/`, `tests/` and `ARCHITECTURE/` for it.
   - (e) **The size bound**: answer it or leave it open, and say which.
   - (f) **The mock**: what its default script hands over (by the reasoning of ADR-0078 decision 6 and ADR-0066).
5. The record adds no member to a result, a request, `build.json`, `STATE.json`, `instance.json`, a spec or a line of `events.ndjson`, and changes no value of `condition`. If it adds a kind of file in the attempt tree or a value of `error.kind`, it says so in an A-13 reading in Consequences, in the manner of ADR-0078's.
6. Consequences:
   - name the code slice the record makes possible, if any, and what it waits on: the run tools' tool functions are not yet written; ADR-0078's own code slice T-0243 is BLOCKED on HQ-0026. Name no module or function as binding.
   - list the sentences of earlier records that become less exact (found by grep), as ADR-0107 Consequences does; do not edit them.
   - state that there are no runtime acceptance items, or name them.
7. Boundaries (not decided here) include at least: ⑲ (나) (T-0210 / HQ-0021); the source and values of ⑲ (라) and OD-14; the container and the log's route out of it (OD-14 ①, ⑱ (다)); `build.json` members (OD-6 ②); the record of a build's command and settings (⑰ (다)); ⑳; the result files (PLAN P1-8); and any change to earlier records, `hilclaw/`, tests, CI, settings files or `HIL-Claw-data`.
8. `ARCHITECTURE/Requirements.md`, OD-18 row only, following the register's "행 형식" (line 84): add **one** link to ADR-0108 with a few words of topic after `**확정분**:`, and rewrite the ⑲ entry of `**잔여**:` in place so that it reads ⑲ ((나), (라)의 출처와 값) or whatever remains. Do not restate the record's content, add no dated paragraph and leave the status cell as it is.
9. `ARCHITECTURE/OpenDecisionProposals.md`, OD-18 section only, following its "기록 규칙" (line 8): add one `- **채택분** [ADR-0108](…) — … (부분 답: 하위 질문 ⑲ (다))` line beside the other adopted lines. Rewrite in place the status tail of the ⑲ bullet (`→ 부분 답: … 남음: …`) and, if needed, its head status word. Keep the question text, do not restate the record and add no dated note.
10. `ARCHITECTURE/StandardScenarios.md`: re-check coverage with the document's rules (CLAUDE.md "문서 커버리지 재검사") and update §검사 결과 as its first paragraph prescribes. Record history only where a verdict changes; otherwise touch only the line that paragraph says to update.
11. No other file changes. `git diff --stat origin/main` lists only the touchesFiles. `git diff --check` is clean. Every relative link added resolves. The count of OD register rows is unchanged.
12. Document mode (CLAUDE.md A-13): branch `claude/T-0311-<slug>`, context-isolated reviewer cycle (at most 7 rounds), rebase on `origin/main`, direct push to main. The commit carries `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0311` in the last paragraph of the message (no blank line between trailers). The driver then posts the §9 owner notice on #5, with the footer of §8.
13. No compiler, kernel, container or `claude` process is started (D16).

## Out of Scope

- Any code, tests, CI or settings change; the code slice of ADR-0078 (T-0243) or of this record.
- ⑲ (나) and the rest of (라); ⑱ (가)/(다)/(라)/(마); OD-14; ⑳; `profiler.collect` (HQ-0025).
- Editing earlier ADRs (including the "less exact" sentences listed by ADR-0106 and ADR-0107), UsageCases, `EventKinds.md`, `StepValues.md`, `BlobTypes.md`, `SpendAxes.md` or the README.
- The unlanded ADR-0068 and its branch.

## Follow-ups

- If the record makes a code slice possible, a later code task. It must wait for the run tools' tool functions and for HQ-0026 (T-0243).

## Result

- DONE. Commit `5b5e6dc` (document mode, pushed straight to `main` with no PR) adds `ARCHITECTURE/decisions/ADR-0108-od18-run-tools-timing-build-compiler-log.md` and edits only the touchesFiles: the OD-18 row in Requirements.md, the OD-18 section of OpenDecisionProposals.md, and the "최근 재검사" line of StandardScenarios.md.
- Decision: for the first case and the mock, the log of every timing build whose compiler ended is kept in `build-log-<step>-<EE>.txt` below the attempt's `measure/`, in ADR-0078's form, written by the tool function from a log the operation hands to a fifth argument, the log keeper. This amends ADR-0065 decisions 2 and 5 and ADR-0066 decisions 2 and 6 by restatement (those records are not edited). A failed write ends the step with `build_log_unwritable`, which binds part (na) of sub-question 19 in that one case.
- Left open: the size bound (rest of part (da)), part (na), and the source and values of part (ra). StandardScenarios re-check: no verdict change, no gap.
- Review: 7 rounds, round 7 Approve. Two round-7 nits left: decision 7's name check does not list the frame's kinds (no clash); the OpenDecisionProposals line lacks the "그 계약의 아홉째 기록" tail.
- OD notice on #5: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6252659013. Task branch deleted. No compiler, container or `claude` process was started (D16).
- Follow-up: code slice (log path, keeper, write, kind, mock); waits for the run tools' tool functions and for T-0243 (HQ-0026).
