---
id: T-0481
title: Record what becomes of the compiler's log of the waiter's build (OD-18 ⑲ (다), the piece ADR-0169 left open) and anything else the `cpu_standin` operation of `sim.run` and `board.run` needs that no record decides, as one new ADR, and add that operation (ADR-0144 slice (4), the run tools' part, with ADR-0145's waiter build and process), bound to no backend table, with tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, OD-14, "#5 D12"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/ADR-0170-od18-standin-run-operation.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md, hilclaw/standin_run.py, tests/test_standin_run.py, hilclaw/standin_copies.py, tests/test_standin_copies.py]
estimatedSize: {loc: 560, files: 6}   # tests excluded from the cap; the ADR's lines count (DRIVER §5, D4/D20). standin_copies.py only if the second harness copy needs it.
hq: []
---
## Why

PLAN P1-1 is open. Its completion criterion (D18) needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin` as well as on the mock. PLAN P2-5 (the first run, `cpu_standin` x GEMM) needs the same. This is checklist work, not a D18 deferral.

What has landed: `correctness.check` has its `cpu_standin` operation (`hilclaw/standin_check.py`, T-0480, ADR-0169). The building blocks for the run tools are on `main`. They are `hilclaw/standin_container.py`, `hilclaw/standin_copies.py`, `hilclaw/standin_image.py`, `hilclaw/standin_settings.py` (`BUILD_TIME_LIMIT_S`, `timing_process_time_limit_s`), `hilclaw/standin_answer.py` (`read_build`, `read_timing_process`, `place_error`, `build_dir_removable`) and `hilclaw/standin_waiter_line.py`. The harness side is `hilclaw/harness/timing_driver.c`, `hilclaw/harness/timing_waiter.c` and `hilclaw/harness/timing.py` (`driver_arguments`). `hilclaw/run_operation.py` gives `ask` and `Reported`. `hilclaw/build_log.py` gives the keeper. The tool function (`hilclaw/run_tool.py`) and the registration (ADR-0167) have landed over the mock.

ADR-0169 Consequences name the next slice: "the `cpu_standin` operations of `sim.run` and `board.run` with the waiter's build and process … **the record of the waiter's build's log (decision 4) is needed first, or with it**". ADR-0169 decision 4 and Boundaries leave that log open and give the reason:
- Keeping it as a second file of a timing identity would add a file name to the data plane.
- Keeping it inside the one file would put the logs of two compiler processes there, which ADR-0108 decision 1's "The log: everything the compiler process of that build wrote" does not obviously cover.
- Not keeping it is a reading of #5 A-2's "에러 로그" that ADR-0078 decision 2 did not make. Note that the waiter's build compiles no kernel file (ADR-0145 decision 3: "It is not the kernel's: no kernel file is compiled into it").

The operation must do one of these, so the choice cannot be left to the code (CLAUDE.md "미결은 발명하지 않는다"). By D20 ① the record goes with the operation in one task: code mode, with the ADR file part of the PR.

The `cpu_standin` entry of the default table is **not** in this task. It is T-0482, which depends on this one. Folding it in was weighed under D20 ③: the record, the operation and the table entry with its docstrings together come close to or over the 600-line cap, so the entry stays a separate task.

This is a design part of OD-18 (and possibly of OD-14 ①) that the driver may close (DRIVER §9, D6). No owner-only part is known: #5 A/B items, C-6, OD-3 and OD-25 are not touched, and HQ-0034 (OpenMP) stays out, as it is deferred in PLAN. HQ-0060 (ADR-0145 items (liii)-(lv)), HQ-0073 and HQ-0074 are unresolved runtime acceptance items. They block nothing here, because the tests use stubs.

**Stop conditions. The executor checks these and does not assume them away:**
- Suppose the only defensible way to keep the waiter's log needs a new data-plane file, file name or member, or a new value of `error.kind` or `condition`. Or suppose it needs a change to the bytes rule of ADR-0078 decision 4 / ADR-0108 decision 4 that the record cannot read as within it. That is a data-plane schema change (CLAUDE.md A-13; ADR-0101 Consequences). If not keeping the log, or keeping it within the one file, cannot be argued on the record's own ground, stop. Return BLOCKED with a Korean question for the owner (DRIVER §8: the issue, options (a)/(b)/(c), what stays blocked and what does not).
- If writing the record shows an owner-only decision, stop and return BLOCKED with the question. An example is a reading of #5 A-2 "에러 로그" that the record cannot make as ADR-0078 decision 2 and ADR-0108 decision 2 made theirs, as its own design subject to the owner's objection.
- If the operation meets a situation ADR-0168's table lacks, register it as ADR-0168 decision 2 says ("A code task that finds a situation this table lacks registers it"). Do not invent its answer.

## Required Reading

Line numbers are those of `main` at `f3c68add`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, time limit), **§5** (lines 86-115: task format, naming, size cap D4/D20, trailers, the test rules D12), **§8** (lines 142-149: HQ form, the `— posted by driver` footer) and **§9** (lines 150-158: which ODs the driver may close, the owner notice on #5 and the 7-day objection window).
- CLAUDE.md, the whole file. Above all read "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (no container runtime is required on this machine; tests use stubs, never a real `docker`, `clang` or `claude`), "테스트 규칙", "브랜치·merge 절차" (code mode and the BLOCKED reasons) and "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- Before you edit `ARCHITECTURE/`, run `gh pr list`, read issues #4, #5, #7 and #8, and read the unresolved `humanQuestions` in `PROCESS/STATE.json` (CLAUDE.md 세션 진입 점검). If an open PR touches the same rows or sections, stop and return BLOCKED.
- **The model record** for form and the direct predecessor: ARCHITECTURE/decisions/ADR-0169-od18-standin-build-log-and-removal.md, the whole file. Above all read decisions 2-5 (lines 30-79), decision 7 (85-88), Consequences (116-121) and Boundaries (123-131). For form also see ADR-0168 (Status marking, decision table, Walk-through, Consequences with the "less exact" list, runtime acceptance items and the A-13 reading). The format follows ADR-0001's "Record format" section.
- **What is open and why**:
  - ARCHITECTURE/decisions/ADR-0108-od18-run-tools-timing-build-compiler-log.md: decisions 1 (lines 29-33), 2 (35-44: the three answers weighed and A-2's reading), 3 (46-50), 4 (52-56), 5 (58-72) and 7 (77-89).
  - ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md: decisions 1 (lines 26-30), 2 (32-37) and 4 (48-53).
  - ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md: decision 3 (lines 48-61: W0-W6, "The waiter's build" with one B_t for both builds, "What the operation takes"), decision 6 (73-78), Walk-through (79-84) and Consequences (101-107).
  - ARCHITECTURE/decisions/ADR-0168-od18-standin-container-situations.md: decision 2 (lines 36-70, rows C1-C19, C19 above all), decision 3 (72-78), decision 4 (80-86: the waiter's line before the status), decision 5 (88-92), decision 6 (94-98) and Boundaries (143-154).
  - ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md: Q2-Q4 (lines 56-58), decision 3 (65-79) and Consequences (141-148).
  - ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md decisions 2 and 7 (lines 39-48, 86-97); ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md decisions 2 (33-54), 4 (64-76) and 7 (98-110); ARCHITECTURE/decisions/ADR-0068-od18-run-tools-operation-tool-failure.md decisions 2 (35-55) and 8 (105-110).
  - ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md decisions 2 (lines 28-35), 5 (50-58), 8 (74-93) and 9 (94-110): the driver, its arguments and its report.
  - ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md decision 3 (lines 41-59: same settings in both builds); ARCHITECTURE/decisions/ADR-0117-od14-cpu-standin-time-limits.md decisions 2-5 (31-69).
  - ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md decision 4 (lines 73-94) and ARCHITECTURE/decisions/ADR-0096-od18-check-build-directory-removal-failure.md decisions 2-3 (31-55): the build directory and its removal, which the run tools' operation follows as the check's does.
  - ARCHITECTURE/decisions/ADR-0101-od8-failure-kind-change-and-step-values.md, the paragraph near line 104 ("For a record that names or changes a failure kind").
- **Where the record is entered** (read their own rules; do not copy the wording of earlier task files):
  - ARCHITECTURE/Requirements.md: the "행 형식" paragraph (line 84); the OD-18 row (line 109) and the OD-14 row (line 105).
  - ARCHITECTURE/OpenDecisionProposals.md: the "기록 규칙" in its header (line 8); § OD-18 (from line 294; its 채택분 lines up to about 360, and sub-question ⑲ at line 388); § OD-14 (lines 232-246).
  - ARCHITECTURE/StandardScenarios.md: its check rules (from line 13) and the first paragraph of § 검사 결과 (line 168).
- **Code (whole)**: `hilclaw/standin_check.py` (the sibling operation: build directory, copies, container runs, keeper, answers, removal; follow its shape), `hilclaw/standin_answer.py`, `hilclaw/standin_container.py`, `hilclaw/standin_copies.py` (`place_copies` copies **one** harness program; the run tools need the timing driver and the waiter's source), `hilclaw/standin_image.py`, `hilclaw/standin_settings.py`, `hilclaw/standin_waiter_line.py`, `hilclaw/run_operation.py` (`ask`, `Reported`, `CONDITIONS`: how an operation is called with five positional things and what becomes of what it returns or raises), `hilclaw/run_parameters.py`, `hilclaw/run_failure.py`, `hilclaw/mock_run.py` (the shape of an operation of a run tool, per tool), `hilclaw/harness/timing.py` (`driver_arguments`), `hilclaw/harness/timing_build.py` (`DRIVER_SOURCE`) and `hilclaw/harness/timing_waiter.c` (its arguments and its last line). Tests: `tests/test_standin_check.py` (how the container step is stubbed, the numeric user on every platform, a real `LogKeeper`) and `tests/test_standin_answer.py`.

## Acceptance Criteria

1. **The ADR.** Write a new `ARCHITECTURE/decisions/ADR-0170-od18-standin-run-operation.md`. If 0170 is taken, use the next free number; check `ARCHITECTURE/decisions/` and the remote branches. The slug is your choice. Write it in the format of ADR-0169, for the calls of `sim.run` and `board.run` at a run of ADR-0144 decision 1. It decides at least the following.
   - **The compiler's log of the waiter's build** (ADR-0169 decision 4 and Boundaries; part of ⑲ (다)): whether it is kept, and if so how, within one keeper per call (ADR-0108 decision 5) and the landed bytes rule. Weigh at least the three alternatives ADR-0169 decision 4 names (a second file, the one file, not kept) and give the A-2 reading the choice rests on, marked as the record's own design. If the timing build's log is unaffected, say so. The stop conditions of Why apply.
   - **How the operation hands the keeper the timing build's log** when the waiter's build follows it: the order, and the case where the waiter's build fails or B_t is used up before it starts (ADR-0168 C19). The timing build's log follows ADR-0169 decisions 2-4 (cite them; do not restate them).
   - **Anything else the operation must choose that a record leaves open and does not give to the code.** Choices an earlier record gives to the code stay the code's and are named in the module docstring, not in the ADR. Examples: names of copies and executables; whether the operation's own work between the two builds counts against B_t (ADR-0145 decision 3 gives this to "the code slice"); the retry bound of the directory's removal.
   - **The stop conditions** of Why: no new kind, condition, file, name or member. The Consequences give the A-13 reading as ADR-0169 does.

   Mark every sentence as owner, cited, or the record's own. Consequences list the sentences of earlier records and the docstrings that become less exact, without editing them. At least ADR-0108 decisions 1 and 4, ADR-0145 decision 3 and Consequences slice (4), and ADR-0169 decision 4, Boundaries and Consequences become less exact. Consequences also name the next slice for the planner: the `cpu_standin` entry of the default table, ADR-0167 decision 3 and Boundaries, task T-0482. They name runtime acceptance items for facts only a real Docker can show, numbered after the last item in use; check the records for the highest roman numeral; (lxxx) is ADR-0169's. Boundaries keep open what ADR-0169 Boundaries keep open that this record does not answer.
2. **Register entries** follow the recording rules written in those files, not the wording of earlier task files:
   - Requirements.md OD-18 row (line 109), and the OD-14 row only if the record answers part of OD-14 ①. Follow the "행 형식" paragraph (line 84): add one ADR link after `**확정분**:`, rewrite `**잔여**:` in place where it changes (today it names "(다)의 … 대기자 빌드의 컴파일러 로그" under ⑲), do not restate the ADR, and add no dated paragraph.
   - OpenDecisionProposals.md § OD-18, and § OD-14 if touched. Follow its header's "기록 규칙" (line 8): add one `- **채택분** [ADR-NNNN](…) — …` line per section, and rewrite in place the status at the end of each touched sub-question ("→ 부분 답: … 남음: …") and its bullet's status word. Do not append them as a dated paragraph.
   - StandardScenarios.md: re-check coverage under its check rules (CLAUDE.md "문서 커버리지 재검사") and update § 검사 결과 as its first paragraph says. Add a history entry only if a verdict changes.
3. **Code: the operation.** Add one new module `hilclaw/standin_run.py`, or a name you give and justify in the commit body. It holds the `cpu_standin` operation of `sim.run` and `board.run`: a callable for each tool, or one factory taking the tool name as `mock_run.operation` does. Each is called with the five positional things of `run_operation.ask` (request, hw_profile, timing parameters, output path, keeper). It is **bound to no backend table yet**: `hilclaw/check_definition.py`, `hilclaw/run_definition.py` and `hilclaw/tools.py` are not changed. In the order of ADR-0168's Walk-through, ADR-0145 decision 3 and this ADR, it does the following.
   - It reads the image (`standin_image.read_image`) before anything is made or started (C1, C2).
   - It makes a new build directory for the call outside both checkouts and inside neither's `.git/`, as `standin_check` does. It answers a directory that cannot be made as `build_directory_unusable` (S3).
   - It copies the kernel files, the timing driver (`timing_build.DRIVER_SOURCE`) and the waiter's source (`hilclaw/harness/timing_waiter.c`) into the build directory, the harness copies outside the kernel's sub-directory (ADR-0144 Q3; ADR-0145 decision 3). If `standin_copies.place_copies` cannot place a second harness program, extend it compatibly in `hilclaw/standin_copies.py` with its tests, or justify another way in the commit body. Copy failures answer by C12, C13 and C15.
   - It runs the timing build in one container with `clang`, the flags and trailing flags of `standin_settings` (ADR-0116; the same as the verification build, ADR-0107 decision 3), and the driver source first with the kernel's compiled set in the reader's order. It writes the executable into the build directory. It reads the result with `standin_answer.read_build` and hands the keeper the log as ADR-0169 and this ADR decide. It answers a status-0 build that left no executable as `build_output_missing` (S9).
   - It runs the waiter's build in a second container with the same flags, within what is left of `BUILD_TIME_LIMIT_S` (B_t covers both builds, ADR-0145 decision 3). It answers by C19 and keeps its log as this ADR decides.
   - It runs the timing process in a third container that starts the waiter with the timing executable's in-container path and the eight arguments of `timing.driver_arguments`, within `standin_settings.timing_process_time_limit_s`. It reads the result with `standin_answer.read_timing_process` and returns `run_operation.Reported(report, memory_bytes)` from the `WaiterRead`. It returns a condition as its string. For the open stream (status 0 and no waiter's line, `None`) it lets the landed rule answer, as ADR-0168 decision 4 says.
   - Every forced removal of a container gets ADR-0169 decision 5's limit. Reuse `standin_check.REMOVAL_TIMEOUT_S` or move it to a shared place; do not copy the value.
   - It turns every `standin_answer.Failure` into `hilclaw.tools.ToolFailure(kind, message)`. It places what the steps raise with `standin_answer.place_error`, and lets pass what it does not place (C14, C16) and every request to end (C18).
   - It removes the build directory before it returns or raises, only where `standin_answer.build_dir_removable` allows after every container of the call, as `standin_check` does (ADR-0168 decision 5; ADR-0096). A failed removal changes no answer.

   It hands the compiler nothing derived from the seed (ADR-0108 decision 4). It imports no NumPy, because the judging is the tool function's (ADR-0061 decision 3). It reads no environment variable except through `standin_image`, and keeps nothing between calls. Its module docstring names the records and lists which choices are the module's own. Shared helpers may be factored out of `hilclaw/standin_check.py` only if that lowers the total change. Then list the file in the commit body and keep `tests/test_standin_check.py` passing unchanged in substance. Leave every docstring the ADR lists as less exact as it is.
4. **Tests** (D12) go in `tests/test_standin_run.py`. Replace `standin_container.run_in_container` (or `local_run.run`) with a stub that records the commands and plays the client's result. Use a real temporary output directory and a real `LogKeeper`. Never use a real `docker`, `clang` or `claude` (D16). The tests pass on every platform the CI and the development machine run; stub the numeric user where the platform has none, as `tests/test_standin_check.py` does. Cover:
   - **Happy**, for both `sim.run` and `board.run`: two ok builds and an ok waiter run return `Reported` with the report before the waiter's line and the figure (value x 1024). Assert:
     - the timing build's command holds `clang`, the ADR-0116 flags, the driver source first, the kernel's compiled set in order, the trailing flags and an output inside `CONTAINER_BUILD_DIR`;
     - the waiter's build compiles only the waiter's source;
     - the process starts the waiter with the executable's path and the eight driver arguments;
     - the keeper holds what the ADR prescribes;
     - the build directory is gone afterwards.
   - **Every row the operation can meet**: C1-C8 as they apply to a timing call (C5 with 125, 126 and 127 for each build), C9 (with line and status 0, a line with non-zero, no line with non-zero, no line with status 0 left to the landed rule), C10 for each build and for the process (removal ok, failed, raised), C11, C12, C13, C15, C17, C19 (the waiter's build failing, past its limit, B_t used up before it starts, status 0 with no waiter executable), and the build directory that cannot be made (S3).
   - **Branch**: the log handed over or not by each rule; the second build's limit computed from what the first left; the build directory left where `build_dir_removable` says so and removed otherwise.
   - **Negative**: a plain `OSError` of the container step (C14) and C16 errors pass as they are. A `KeyboardInterrupt` from each build, from the process and from the directory's removal passes and is not caught. A message holds no path, image reference, container name or stream byte (ADR-0168 decision 6). Nothing derived from the seed is in any build command.
   - Every public function and class of the new module is tested. If `standin_copies.place_copies` changed, its changed behaviour is tested in `tests/test_standin_copies.py`.
5. `python -m pytest`, `ruff check .` and `ruff format --check .` pass. The `hilclaw/` coverage gate (line and function >= 80%) and the test-presence check hold.
6. The commit body names the language (Python) and the reason in one line. The PR body ends with `Task: T-0481`. After landing, post the owner notice of DRIVER §9 on issue #5 in English: what the new ADR decides, the landed commit, and the objection window (7 days from the notice). Its last line is `— posted by driver` (DRIVER §8). Record the comment URL in `## Result`. List there the runtime acceptance items the ADR names, for the driver to record as an HQ (reason `runtime-acceptance`).

## Out of Scope

- The `cpu_standin` entry of the default table and any change of `default_table`, `default_registry`, `run_definition` or the tools' docstrings (T-0482).
- OpenMP (HQ-0034, deferred in PLAN), a target-specific flag, the size bound of ⑱ (나)/⑲ (다), the rest of ⑲ (나) (C14 and its kin, the sorting of kinds for ADR-0140), OD-14 ① (나)/(라)/(마)'s rest, leftovers of a dead operation, and `profiler.collect` (not offered on `cpu_standin`, ADR-0130).
- Editing earlier ADRs or the docstrings of other modules. They are listed as less exact, not edited.
- Starting a real container runtime, compiler or `claude` on the development machine (D16).

## Follow-ups

- T-0482 (already planned, depends on this task): the `cpu_standin` entry of the default table binding `standin_check.operation` and this task's operation. It needs the module and callable names this task lands, so write them in `## Result`.

## Result
