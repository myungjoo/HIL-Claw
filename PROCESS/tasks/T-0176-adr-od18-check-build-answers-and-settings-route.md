---
id: T-0176
title: Write the ADR that answers OD-18 sub-question 17 (가) and (나) for `correctness.check` of the first case (`cpu_standin`, `gemm`, fp32, the C kernel of ADR-0008) and of a run at the mock - what a call answers in situations S3 to S10 of ADR-0056 decision 5 (the build and the start of the verification executable), with the class of S7 and S8 taken from the owner's answer to the HQ raised at planning, and through which side an operation has its flags, trailing flags, compiler, two time limits and environment - and reflect it in the ARCHITECTURE documents; no code
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-9, FR-10, FR-1, NFR-2, NFR-4, C-3, OD-18, OD-6, OD-14, OD-16, "#5 D6"]
dependsOn: [T-0156, T-0157, T-0158, T-0159]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0058 at planning time, after ADR-0057)
estimatedSize: {loc: 280, files: 4}   # one new record of about 170-210 lines; the rest are in-place edits of a few lines each
hq: [HQ-0020]   # raised at planning (reason `data-plane-schema-change`); execute only once it is answered
---
## Why

PLAN P1-1 is open. The contract of `correctness.check` has been written in slices (ADR-0021, ADR-0038, ADR-0040 to ADR-0048, ADR-0056), and its code up to the operation is on `main`. What stops the next code slices - the operation of `cpu_standin` for this tool, the last part of `hilclaw/check_tool.py`, the tool's registration and, with them, the conformance tests of P1-1 - is ADR-0056's own stop:

- ADR-0056 decision 5 lists ten situations in which an operation has no verification executable. S1 and S2 got answers (decision 6; the backend kinds `no_kernel_source` and `kernel_source_unreadable`, in code since T-0159). **S3 to S10 got none**: "S3 to S10 are given no answer here", left "so that the class of every answer of the build is decided in one place, by the record that also has the route of the settings".
- ADR-0056 decision 4, last table: flags, trailing flags, the compiler, the time limit of the build, the time limit of the process and the environment are **open** as to the side through which an operation has them. "An operation that builds needs a time limit and may need flags, so the operation of `cpu_standin` cannot be written to its end from this record."
- Both are registered as OD-18 sub-question ⑰, parts (가) and (나) (`ARCHITECTURE/OpenDecisionProposals.md` line 313). Part (다) (what records the bytes and settings a check was built from, keeping the executable, a failed removal of the build directory, a build directory left by a dead process) is not this task.

**This task writes the record that answers (가) and (나) together**, as ADR-0056 asked. It ticks **no PLAN checkbox** (P1-1 stays open: the code, the rest of the request, the run tools).

**Why an HQ was raised at planning (the planner's judgement; the reviewer is asked to re-check it).** For S7 (a compile or link failure) and S8 (a build past its time limit) ADR-0056 found that the reasoning of ADR-0021 decision 5 ("this attempt did not complete a verification under these parameters") points to a **result**, while a result needs a fifth value of `condition`, "a string with exactly four values" (ADR-0042 decision 3) in a closed list whose results are stored in `events.ndjson`. A new value of a stored result is a data-plane schema change, a BLOCKED reason of CLAUDE.md A-13 that only the owner clears; choosing a tool failure instead would be "the reading ADR-0021 decision 5 warned against, taken without that question having been put" (ADR-0056 decision 6). T-0175's Follow-ups named the same question. So the planner wrote this task and returned the question to the driver; **the task runs only after the owner has answered it**. Everything else in the record - S3 to S6, S9, S10 and part (나) - is design-level under DRIVER §9 (OD-18 is not on the owner-only list) and is decided by the record.

State of `main` at `c98ef1c` (planner, 2026-10-14): `hilclaw/check_failure.py` `BACKEND_KINDS` holds the two kinds of ADR-0056 decision 6; `hilclaw/check_operation.py` calls an operation with four things (ADR-0056 decision 3, T-0158); `hilclaw/kernel_source.py` is the reader of ADR-0055 (T-0157); `hilclaw/harness/verification_build.py` `build_verification_executable(kernel_sources, output, *, timeout_s, flags=(), trailing_flags=(), compiler=None, cwd=None, env=None)` chooses no setting and returns a `BuildResult` whose `ok` is false for a compile failure, a link failure or a timeout; `hilclaw/clang_build.py` raises `CompilerNotFoundError` when nothing was started; `hilclaw/local_run.py` raises `ProgramNotFoundError`; `hilclaw/check_result.py` knows the four values of `condition`. No backend table entry for `cpu_standin` holds an operation of this tool.

Planner's judgements (**the reviewer is asked to re-check each**):
- **Authority (DRIVER §9).** S3 to S6, S9, S10 and part (나) are design-level. The class of S7 and S8, and whether the compiler's log is returned or kept, are taken from the owner's answer. If the answer leaves a point open, the guarded exit applies. The record does not decide it.
- **Separable from the owner-only items and from the roster.** The record speaks of "the tool function" and "the operation of a backend" only, as ADR-0043 and ADR-0056 did. It names no agent, role holder or allowlist. It fixes no flag, compiler, language standard, thread count or time-limit **value**: part (나) asks *through which side*, and values stay with OD-6 sub-question ②, OD-14 and OD-16 sub-question ⑥.
- **Part (나) and the spec.** ADR-0002 decision 6 (b) puts the settings the orchestrator *prescribes* for a candidate into the spec's `task.build` ("version 1 names no member"; decision 6, line 100: a new member of `task.build` raises no `schema_version`). One defensible answer is "handed by the tool function from the attempt's `spec.json` `task.build`". That would need member names of `task.build`. Defining them in a stored spec is a data-plane schema change under A-13, and the owner's answer does not cover it. **That is a guarded exit, not a decision of this record.** The other defensible answers (each setting is the backend's own; or a split by setting) need no member.
- **Session entry check (planner, 2026-10-14)**: no open pull request. Open HQs: HQ-0013, HQ-0014, HQ-0016, HQ-0017, HQ-0018, HQ-0019, all `runtime-acceptance` and blocking nothing. No comment on #5 after `issuecomment-6160644223` was seen by T-0175.
- **D16.** The record is written from documents and from reading the source. Nothing is built or run; no `claude` process, compiler run, container runtime, board or API key is needed.

## Required Reading

Line numbers are those of `main` at `c98ef1c`; the text wins. Several lines of the ARCHITECTURE documents are tens of thousands of characters long. Read them with a script (`awk` with `substr`, or `sed -n '<line>p' | cut -c` / `fold`), never as a whole file. Read Python sources with `PYTHONIOENCODING=utf-8` on this machine.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, `T-NNNN` naming, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, size cap D4, commit trailers). These two are mandatory for every task (§6).
- PROCESS/DRIVER.md, more:
  - §0 (lines 12-18);
  - §1-5 (line 28: Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED);
  - §2 last bullets (lines 45-46);
  - the "BLOCKED 사유" paragraph (line 76);
  - §8 (lines 135-139);
  - **§9 whole (lines 141-148)**.
- CLAUDE.md, the whole file. In particular: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer), "바이너리 금지".
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15). .claude/skills/dev-code-review/SKILL.md (the document-mode return path; the "no invented decisions" check).
- **The owner's answer to the HQ this task carries in `hq`.** Find it on issue #5 by its `HQ-NNNN`: the newest comment that holds the id and lacks `— posted by driver`. Also read `PROCESS/STATE.json` `humanQuestions` for that id (`decision`). The answer is a fixed input.
- **ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md**, the model of form and the direct predecessor (213 lines). Read the whole record. Above all:
  - decision 4 (lines 73-94: build at each call, the build directory, the settings table);
  - **decision 5 (lines 95-114: S1 to S10)**;
  - **decision 6 (lines 115-131: the answers to S1 and S2, the two stops, "Until ⑰ is answered")**;
  - decision 7 (lines 132-143: the order of a call);
  - Consequences (185-192) and Boundaries (193-206).
- **ADR-0021-od18-correctness-check-split.md** decision 2 (lines 33-52) and **decision 5 (lines 76-85: results against tool failures, and why a broken run is a result)**.
- **ADR-0042-od18-correctness-check-result-members.md**:
  - **decision 3 (lines 46-61: `condition`, four values, the order)**;
  - decision 6 (what a result never holds);
  - **decision 7 (lines 105-131: the member list is closed; "Only a record adds a member, and a record that does so amends this table")**;
  - its A-13 reading.
- ADR-0047-od18-correctness-check-operation-tool-failure.md:
  - decisions 3 and 4 (what the log holds; the answer and `operation_failure_invalid`);
  - **decision 5 (lines 89-96: how a kind becomes a backend kind)**;
  - Limits.
- ADR-0045 decision 6 and ADR-0048 decision 6: what a message may carry. ADR-0048 decision 10: the order of a call.
- ADR-0017-od16-cpu-standin-verification-run.md:
  - decision 2 (one build call; "an attempt is built twice");
  - decision 7 (the verdict and the four conditions);
  - **decision 9 (lines 86-100: the parameter table)**;
  - decision 10.
- ADR-0009 decision 2: the timing build. Read only, to say whether the answer reaches the run tools. It does not decide them.
- ADR-0002-od6-codegen-spec.md:
  - decision 2, the `task.build` row (line 62);
  - **decision 6 (b) (line 95)**;
  - the versioning rule (line 100).
- ADR-0016 decision 2 ((a) to (d)). ADR-0010 decision 4 ("a tool failure says that no outcome was established").
- ADR-0055 decision 3 (R1 to R8). ADR-0004 decision 3 (`build.json`; "No source says which agent or tool runs that build").
- ARCHITECTURE/Requirements.md:
  - FR-1, FR-5, FR-6, FR-9, FR-10, NFR-2, NFR-4, C-3, C-7;
  - the "Open Decisions" preamble (status vocabulary, the one-line rule);
  - the register row **OD-18** (line 107; very long). Read its head and its last 3,000 characters: the clause for ADR-0056 and the "잔여" list with the ⑰ item;
  - the rows OD-6 (95), OD-14 (103), OD-16 (105).
- ARCHITECTURE/OpenDecisionProposals.md:
  - section OD-18 (lines 273-315). The "채택분(ADR-0056, ...)" bullet (line 301) is the form to follow. Read **sub-question ⑰ (line 313)** and sub-question ⑩ (line 306, with its dated notes);
  - section OD-6 sub-question ② (line 69);
  - section OD-14 (lines 225-232);
  - section OD-16 sub-question ⑥ (line 259).
- ARCHITECTURE/StandardScenarios.md:
  - "검사 규칙" and "검사 결과". The dated paragraphs of 2026-10-13 "9차" (line 188) and 2026-10-14 "1차"/"2차" (lines 190-192) are the form to follow;
  - S0 steps 5 to 7, S1 steps 4 to 6, S8, and the steps the "9차" paragraph names.
- PROCESS/tasks/T-0156-adr-od18-check-verification-executable.md `## Result`: "The nine points as landed" and the note for the next planner. PROCESS/tasks/T-0175-docstrings-spec-check-tool-check-seed.md `## Follow-ups`, first bullet.
- Existing code the record must describe truthfully (none of it is edited):
  - `hilclaw/harness/verification_build.py` (docstring and signature);
  - `hilclaw/clang_build.py` (`build`, `BuildResult`, `CompilerNotFoundError`, the refused arguments);
  - `hilclaw/local_run.py` (`run`, `RunResult`, `ProgramNotFoundError`);
  - `hilclaw/harness/verification.py` (`run_verification`);
  - `hilclaw/check_failure.py` (`BACKEND_KINDS`);
  - `hilclaw/check_result.py` (the values of `condition`);
  - `hilclaw/check_operation.py`, `hilclaw/mock_check.py`, `hilclaw/kernel_source.py`.

## Acceptance Criteria

### Fixed inputs (not re-decided)
- **Owner**:
  - the answer to the HQ in `hq` (quote it word for word where the record relies on it);
  - FR-9 (one harness, the same verification at both points);
  - HQ-0005 (3) and (4) (two checks per attempt; a run at the mock is answered by this contract);
  - HQ-0004 (the oracle and the tolerance);
  - #5 A-2 / C-3 (no binary in git).
- **Earlier records**, cited under the §9 route:
  - ADR-0056 decisions 3 to 7 (four things cross the cut; built at each call into a build directory outside both checkouts that is removed; S1 to S10; the answers to S1 and S2);
  - ADR-0047 decisions 3 to 5;
  - ADR-0042 decisions 3 and 7, including whatever the owner's answer adds to them;
  - ADR-0021 decision 5;
  - ADR-0017 decisions 2, 7 and 9;
  - ADR-0002 decision 6 (b).

### The record (one new file `ARCHITECTURE/decisions/ADR-NNNN-od18-correctness-check-build-answers-and-settings.md`, next free number on `origin/main` at execution time)

Write it in English. Use the "Record format" of ADR-0001 as ADR-0056 uses it: Status with its limits, Context, Decision, a short Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References. Aim for about 170 to 210 lines. Fence any example as `text` or `json`, never as C, Python or shell.

Say at the head of the Decision section that the content is of three kinds:
- the owner's sentences: quoted, marked **owner**, linked, and not subject to the objection window;
- what an earlier record or a requirement says: **cited**, with its decision number;
- the record's own design, not confirmed by the owner.

For every point give the choice, the alternatives weighed and one or two lines of reason.

The Decision section answers these points and only these:

1. **Scope and terms.** A call of `correctness.check` about one attempt of a run that ADR-0021 and ADR-0038 decision 6 cover, at the moments ADR-0056 decision 5 lists for S3 to S10. Say what the record is not:
   - not the roster;
   - not the run tools. Their timing build is theirs; say in one line whether the owner's answer reaches it, and decide nothing for them;
   - not any setting **value**;
   - not part (다);
   - not what anybody does after an answer.
2. **Limits**, each written before the statement it limits:
   - nothing was built or run;
   - the settings' values are open, so the record cannot say which flags make a build fail;
   - a backend that holds or reads settings otherwise is not detected;
   - the kernel's process stays as unprotected as ADR-0017 decision 10 says.
3. **Part (나): through which side an operation has each setting.** The settings are flags, trailing flags, compiler, the time limit of the build, the time limit of the process and the environment, each a row of ADR-0017 decision 9.
   - Weigh at least these alternatives:
     - (a) each is the backend's own, held by the operation of `cpu_standin` from a source this record does not fix;
     - (b) each is handed by the tool function, from a named file or member;
     - (c) a split by setting. Example: the time limits are the backend's own while flags a candidate is prescribed come from `task.build`.
   - Say for each setting which side it is and whether the mock's operation and a script are given it.
   - Restate the settings table of ADR-0056 decision 4 as amended (ADR-0056 itself is not edited).
   - Say what the answer means for OD-16 sub-question ⑥: whether the two builds of an attempt, or the verification build and the timing build, can be told to use the same settings. Say it as a consequence, not a decision.
   - **An answer that hands anything from the spec's `task.build` needs a member name of `task.build`: that is guarded exit (ii) below.** An answer that hands anything from `instance.json` needs a new member there: the same exit.
4. **The class of every situation S3 to S10, as a table.** For each situation give:
   - a **result** or a **tool failure**;
   - for a result: its `outcome` and `condition` as ADR-0042 (amended by the owner's answer, if it amends it) has them;
   - for a tool failure: its kind; whether it is a **backend kind** named "with the situation it means" (ADR-0047 decision 5); and whether it is answered **before the start line** or **from an end line with a `failure`** (ADR-0047 decision 3). Under ADR-0056 decision 5 all ten situations are found by the operation in ⑥, after the start line;
   - which side finds it.

   Specifically:
   - **S7 and S8 follow the owner's answer.** Restate the answer, then apply it.
     - If the owner chose a result with new `condition` value(s), give the value(s) exactly as the owner named them, or, if the owner named none, the record's spelling as a *name* of ADR-0001. Restate the table of ADR-0042 decision 3 as amended and say where in its order the new value stands and why. ADR-0042 is not edited.
     - If the owner chose a tool failure, name the backend kind(s) with their situation.
   - **S3 to S6, S9, S10 are the record's own.** S4, S6 and S10 depend on point 3; ADR-0056 decision 6 explains why. Weigh for each the reasoning of ADR-0021 decision 5: whether the situation is a property of the attempt or of the machine and the settings.
   - Split or merge kinds the way ADR-0019 decision 2 and ADR-0056 decision 6 did. Check every new kind or value name for a collision in `hilclaw/`, `tests/` and `ARCHITECTURE/`, in the manner of ADR-0056 decision 6, last bullets.
5. **The message** of every new kind, in the manner of ADR-0045 decision 6 and ADR-0056 decision 6. It shows no path, no entry name, no byte of a file and no text of an error. **The compiler's log**: follow the owner's answer. If the answer does not speak of it, say that this record neither returns nor keeps it, as ADR-0056 decision 4 has it, and leave it to part (다) / `build.json`.
6. **The order of a call.** Give the table of ADR-0056 decision 7 again. Mark in bold the rows this record changes or adds, and abridge every other row by citation. Then say what a repeated call finds for each new answer (ADR-0011 decision 3).
7. **How far OD-18 sub-question ⑰ is answered.** One line per part:
   - (가): answered for which situations, and the compiler's log;
   - (나): answered for which settings, and not their values;
   - (다): not answered.
   Add one line for the run tools: whether the owner's answer is to be applied to their timing build. Quote it; do not decide it.
8. **Consequences**, not decisions:
   - the code slices that can now be cut. These are the operation of `cpu_standin` for this tool, the last part of `hilclaw.check_tool`, the new kinds in `hilclaw.check_failure.BACKEND_KINDS`, and, if the owner chose a result, the new value(s) in `hilclaw/check_result.py` and its tests. Names and modules are the code task's; D12 rules apply. Say which settings values a code task still lacks, so that the operation still cannot be written to its end if any are open (OD-14), and say it plainly;
   - the sentences of earlier records and docstrings that become less exact (listed, none edited);
   - the A-13 reading, said precisely: what the owner's answer approved, and that nothing else of the data plane changes;
   - any **runtime acceptance item** in the form of ADR-0056's bullet, or say there is none.

**Boundaries**, at least:
- part (다);
- every setting value and the timeout hierarchy (OD-14);
- the members of `task.build` and `build.json` (OD-6 sub-question ②; ADR-0004 decision 3);
- whether the two builds use the same flags (OD-16 sub-question ⑥), beyond the consequence of point 3;
- the run tools (PLAN P1-1; OD-13 sub-question ⑩);
- the rest of the request, its input schema and description;
- the spend;
- what anybody does after an answer (FR-1, OD-10, OD-17, OD-19);
- other targets, languages and accelerators;
- the roster (OD-23);
- the owner-only items (#5 A and B, OD-3, OD-25, C-6);
- code and tests.

Register a question the record raises as **one new numbered sub-question under OD-18** in `OpenDecisionProposals.md`. Check that the next number (⑱ at planning time) is free before using it.

### Before writing: the inventory
Search `ARCHITECTURE/` and `hilclaw/` for sentences about S3 to S10 and the source of build settings. Search at least for: `⑰`, `sub-question 17`, `S7`, `S8`, `condition`, `exactly four values`, `compile failure`, `link failure`, `time limit of the build`, `flags`, `task.build`, `빌드가 ok가 아니게`, `플래그`.

Classify each hit as one of:
- **covered** by this record;
- **left open and registered** (say where);
- **now less exact** (listed under Consequences, not edited);
- **not affected**.

The list must cover at least ADR-0002, ADR-0017, ADR-0021, ADR-0042, ADR-0047, ADR-0056, the OD-18 section, and the docstrings of `hilclaw/check_result.py`, `hilclaw/check_failure.py` and `hilclaw/harness/verification_build.py`. Put the list into `## Result`.

### Edits of existing documents (same commit)
- `ARCHITECTURE/OpenDecisionProposals.md`, section **OD-18**:
  - one "채택분(ADR-NNNN, ...)" bullet in the form of line 301. It says what was decided, what is the owner's (the HQ answer, linked), what is the record's own (오너 미확정, 통지 후 7일 이의 기간) and what stays open;
  - **one dated note appended to sub-question ⑰** (line 313) saying which parts are now answered;
  - the new sub-question bullet, if the record raises one;
  - one dated sentence in the OD-6 ② or OD-16 ⑥ text, only where a sentence there would otherwise be false.

  Delete no proposal text.
- `ARCHITECTURE/Requirements.md`:
  - the **OD-18 row**: one "확정분" clause in the form the row uses for ADR-0056, as short as that form allows, and its "잔여" item for ⑰ brought up to date;
  - **keep the status word** (`제안됨`), unless the register's own vocabulary requires otherwise; say in `## Result` which rule you applied;
  - the OD-6, OD-14 and OD-16 rows only where a sentence would otherwise be false;
  - no FR, NFR or C is reworded, and no OD row is added, removed or renumbered.
- `ARCHITECTURE/StandardScenarios.md`: the coverage re-check of CLAUDE.md, by that file's own rules (지원 / 미결 / 갭), for every step in which an attempt is verified or built: S0-5 to 7, S1-4 to 6, S8, and the steps the "9차" paragraph names. Update "검사 결과": the heading note and one dated paragraph, numbered after the last paragraph of its UTC day. State the outcome in the commit body even if nothing changes.
- In-place edits keep the language of the surrounding text (Korean). No Korean clause says more than the English record.
- Not edited: ADR-0001 to ADR-0057, `README.md`, `ARCHITECTURE/UsageCases.md`, the #5 body, `CLAUDE.md`, anything under `PROCESS/` (but see `## Result` under Process), `hilclaw/`, `tests/`, `.github/`, `.claude/`.

### Do not invent
- No agent, roster, allowlist or hook; nothing about who calls the tool or when.
- No flag, compiler, language standard, thread count or time-limit **value**, and no default of any.
- No new path of the run tree. No `build.json` or member of it, no record kind of `artifacts.json`, no member of `STATE.json` or `instance.json`, **no member of `task.build` or of any other part of a spec**, no event kind, no raise of a layout or file version.
- No new member of a request. **No new member or value of a result beyond exactly what the owner's answer approves.**
- No rule for what anybody does after an answer.
- No statement about what a real compiler or machine does that was not read from a record or from the source.
- No new external dependency. No new reserved `kind` of the frame. A kind of this tool's own, or a backend kind named with its situation, is allowed.
- **Guarded exit.** Stop if a point cannot be said without something on this list. In particular:
  - (i) the owner's answer is not there, or leaves the class of S7 or S8 open, or is read by a reviewer as not covering what the record needs;
  - (ii) the defensible answer to point 3 needs a member of `task.build` or of `instance.json`;
  - (iii) a reviewer reads a point as the roster's or the owner's.

  Then **decide the smaller part that is separable** and register the rest as the sub-question, saying exactly which sentence stopped it. An example of a smaller part: S3, S5 and S9, which ADR-0056 says "do not depend on the settings". If nothing worth a record is left, land nothing and return BLOCKED with the exact question: "data-plane schema change" for (ii), "requirement unclear" otherwise. A narrowed record and a BLOCKED result are both acceptable outcomes.

### Size
The cap is 300 changed lines and 5 files (DRIVER §5, D4). If the record cannot stay within it, land points 3 and 4 with their table, and propose the split of the rest in `## Result` as a follow-up.

### Document checks (document mode replaces tests; record each outcome in `## Result`; do not commit the scripts you use)
- Each sentence marked owner equals its source word for word. Each citation was checked against its record in place, decision numbers included. Each statement about today's code was checked against the files named in Required Reading.
- **Negative sweep before the first review**:
  - no sentence states an item of "Do not invent" as decided;
  - every enumerating sentence ("exactly", "only", "every", "closed") was checked item by item;
  - S3 to S10 each have exactly one answer;
  - what `clang_build.build`, `build_verification_executable` and `local_run.run` can return or raise was mapped onto that list, so that nothing is without an answer or a registration;
  - every new name was checked for a collision.
- Every relative link of the new record and of the edited passages resolves. The ADR number and the sub-question number are free on `origin/main` at the push. The count and numbering of OD rows are unchanged.
- `git diff --stat origin/main` lists only the new record and the three documents. `git ls-files --eol` shows `i/lf` for the changed files. `git diff --check` is clean. `python -m ruff format --check .` exits 0.
- After landing, read the `push` run on `main` once (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion. A run that started no job is recorded as such. It is not a BLOCKED reason for a document-mode task.

### Process
- Work only in the driver's dedicated clone.
- First run the §3-5 landed check: `git log origin/main --grep='^Task: T-0176'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0176 --state all`.
- Then run the session entry check of CLAUDE.md: `gh pr list --repo myungjoo/HIL-Claw --state open`, and issues #4, #5, #7, #8.
  - An open PR that edits the OD-18, OD-6, OD-14 or OD-16 row or section, the "검사 결과" section, or a file of `touchesFiles` is BLOCKED ("open PR conflict").
  - **Without an owner answer to the HQ in `hq`, stop at once and return BLOCKED** ("requirement unclear", naming the HQ).
  - An owner comment on #5 that objects to ADR-0042, ADR-0047 or ADR-0056 is taken as a fixed input, or is BLOCKED quoting it.
  - An answer to HQ-0013, 0014 or 0016 to 0019 does not stop this task; name it in `## Result`.
- **D16, in practice**:
  - neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag;
  - no program is built or run for this task;
  - if the record lists runtime acceptance items, put them in `## Result` with a ready-to-post notice text in the form of the HQ-0018 mirror (first line `### HQ-NNNN — T-0176: ...`, last line `— posted by driver`). **Do not post it.**
- **Branch.** Document mode (CLAUDE.md A-13): branch `claude/T-0176-adr-od18-check-build-answers-and-settings` from `origin/main`; **no PR**.
- **Review cycle.** Use the reviewer cycle of dev-item-address steps 10 to 12, with a fresh-context `dev-reviewer` each round, given the branch name and this task file's path. At most 7 rounds.
  - Past the cap without a final Approve, return BLOCKED.
  - A result starting with `SECURITY` is BLOCKED.
  - If no reviewer can be spawned, return BLOCKED; do not review your own work.
  - Tell each reviewer to write no file and to start no `claude` process.
  - Ask the reviewer explicitly to:
    - (a) re-check the planner's judgements in `## Why`;
    - (b) check every owner sentence against the HQ answer and its other sources, and that the record applies the answer no wider than it reads;
    - (c) attack point 3: a setting whose side is unclear, a hidden member of a data-plane file, a value smuggled in as a default, and what the mock is given;
    - (d) attack point 4: a situation with no answer or two answers; a tool failure from which a caller reads a property of the attempt without the record saying so; a kind whose moment is unclear; whether a repeated call behaves as the record says;
    - (e) check that point 7 claims no more than was decided;
    - (f) look for anything on the "Do not invent" list;
    - (g) check each statement about today's code, each Korean summary, the inventory and the coverage re-check.
  - **If a reviewer reads a point as needing the owner, return BLOCKED with the question instead of arguing it out.**
- **Landing.**
  - `git fetch origin`, then rebase onto `origin/main`.
  - Make one commit: `git reset --soft origin/main` and commit, only after the rebase. A rebase that changed content goes back to review.
  - Push with `git push origin HEAD:main` (fast-forward). If rejected, fetch, rebase and retry, at most 3 times.
  - Commit message in English. The subject starts with `T-0176:`. The body says in a few lines what the record decides (owner's, cited, or the record's own), what it leaves open, the register edits, the coverage re-check outcome, and that nothing was built or run.
  - Trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0176`, then any attribution trailer your session requires.
- **Owner notice (DRIVER §9).** Put the ready-to-post English text in `## Result`, in the form of the ADR-0056 notice:
  - heading `### OD-18 - the answers of the build of a check of correctness.check and the side its settings come through (first case) fixed by ADR-NNNN under DRIVER §9 (T-0176)`;
  - what the record decides, in six lines or fewer;
  - what is the owner's and what is the record's own;
  - the provisional choices, most contestable first;
  - the limits;
  - the register status word;
  - the date the 7-day window ends;
  - last line `— posted by driver`.

  Do not post it yourself unless the driver's spawn prompt tells you to.
- **Prohibitions.**
  - Never use `git push --force*` or `-f`, never a recursive forced remove, never `gh repo delete`.
  - Do not edit `.claude/settings.json` or `.claude/settings.local.json`.
  - A denied or failed tool call is BLOCKED; do not work around it.
  - Delete the task branch only after the push to `main` is confirmed: remote and local in separate commands. Then check out `main` at `origin/main`.
- **`## Result`.** Fill it in after the push, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). Put no fenced code block in it. Record:
  - the commit, the review rounds and their findings;
  - the answer to each point as landed, with **the table of S3 to S10 with their classes, kinds and moments, and the settings table** (the code slices are written against them);
  - whether the record was narrowed by a guarded exit, and at which sentence;
  - the register status word before and after;
  - the inventory and the document checks;
  - the runtime acceptance items with their notice text, or "none";
  - the owner notice text;
  - the follow-ups, with a "Note for the next planner".

  `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Any code: the operation of `cpu_standin`, `hilclaw/check_tool.py`, `hilclaw/check_failure.py`, `hilclaw/check_result.py`, tests.
- Part (다) of sub-question ⑰; `build.json`; keeping the executable.
- Setting values, the timeout hierarchy, a sandbox (OD-14); the members of `task.build` (OD-6 sub-question ②).
- The run tools `sim.run`, `board.run`, `profiler.collect` and their timing build (PLAN P1-1; OD-13 sub-question ⑩), beyond quoting whether the owner's answer reaches them.
- The roster and every other part of OD-23; PLAN P2.
- Editing earlier records, `README.md`, UsageCases, PLAN, DRIVER.md, CLAUDE.md; anything HQ-0013, HQ-0014 or HQ-0016 to HQ-0019 ask.

## Follow-ups
- (driver) Raise the HQ at planning (reason `data-plane-schema-change`), with the question text from the planner's return, and record its id in `hq`.
- (planner, code mode, after this record) The new kinds and, if the owner chose a result, the new `condition` value(s) in `hilclaw/check_failure.py` / `hilclaw/check_result.py`. Then the operation of `cpu_standin` for `correctness.check`, once the setting values it needs are decided.
- (planner, document mode, §9) The run-tool contracts of PLAN P1-1 (OD-13 sub-question ⑩), taking the build answers from this record.
- (planner, code mode, small) `hilclaw/check_operation.py`, the sentence on decision 8 / sub-question ⑩, third clause: less exact since ADR-0047 (T-0175 Follow-ups).

## Result

**DONE** (executor, 2026-10-15). Landed on `main` as `4060d70` (document mode, one commit, fast-forward push; trailers `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0176`). Branch `claude/T-0176-adr-od18-check-build-answers-and-settings` deleted (remote, then local). Record: `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md` (182 lines). Diff: 4 files, +190/-4.

Resume check: no commit with `Task: T-0176`, no PR and no remote branch before execution. Session entry check: no open PR. On #5 after `issuecomment-6160644223` there are only the ADR-0058/0059 notices, the owner decisions of 2026-10-15 (`6182984913`) and the HQ-0020 answer (`6183004538`). No objection to ADR-0042, ADR-0047 or ADR-0056; no answer to HQ-0013/0014/0016-0019. #4, #7, #8: no new comment.

### Review rounds
- R1 Request changes. Major: the error-to-row mapping had double answers and gaps; run-level time limits and the hw_profile `toolchain` were not weighed. Minor: S9/S10 reasoning; wrong module named for the form (B) test (it is `check_answer.py`); decision 7 and Korean lines unqualified; the Walk-through implied a writer of the log.
- R2 Request changes. Major: flags sent to OD-6 sub-question ② although option (a) excludes that route; no "reads no setting" sentence. Minor: code defaults; incomplete order citation; signal reading; more two-row errors; decision 7 on sub-question ⑩.
- R3 Request changes. Major: the cost of coder-chosen settings under #5 A-7 ② (OpenMP and intrinsics allowed) was unstated; the OSError of S6/S9/temp-file removal could not be told apart. Minor: no writer of the log is possible under ADR-0056 decision 3; environment confused with the isolated environment; less-exact entries missing.
- R4 Approve with Minors: the request as a settings route; local_run ValueErrors; a dropped phrase of the order table restored; sub-question ⑩ qualifier.
- R5 Approve with Minors: TypeError symmetry; decision 7 exception for two-row errors, registered as ⑱ (마).
- R6 Approve with Minors: one canonical two-row list; S4 header marked as the record's reading; Korean "S7·S8 빌드의".
- R7 Approve. Four Nits were left as they are because any change would need an eighth round (see Follow-ups).

### The points as landed
- Guarded exit: not taken, and the record was not narrowed. Point 3 chose (a), which needs no member of `task.build` or `instance.json`.
- Point 1 scope. Point 2 limits: nothing built; no values; other backends undetected; process unprotected; host code only until OD-14 ①; cause not established.
- Point 3, settings table (ADR-0056 decision 4 as amended):
  - Path of the executable and working directory: the operation's own (ADR-0056).
  - Flags and trailing flags: the backend's own; the tool function hands none. Value open (⑱ (라); OD-16 ⑥; a prescribed one: ⑱ (가)).
  - Compiler: the backend's own; clang as the single toolchain (#5 A-7 ②). Installation and version open (OD-14 ①, container of O4).
  - Time limit of the build and of the process: the backend's own; open (OD-14).
  - Environment (thread settings): the backend's own; open (⑱ (라)).
  - The operation reads no setting from any file of the data plane, the hw_profile, the request or the check parameters. The mock and its scripts get no setting.
  - Provisional as to prescribed or coder-chosen settings, run-level time limits and the `toolchain` relation (⑱ (가)).
  - OD-16 ⑥ (a consequence only): the two checks of an attempt use the same settings only as far as the backend's source is constant.
- Point 4, table of S3 to S10. All are found by the operation in ⑥, after the start line. Tool failures are answered from the end line with a `failure`, results from the end line with a `result`.
  - S3, the build directory cannot be made or written: tool failure `build_directory_unusable`, before the build.
  - S4, a setting is refused (output flag, time limit not positive and finite, env that cannot be handed over, empty compiler prefix or wrong type, process time limit the platform cannot wait for): tool failure `settings_refused`, before the process the setting belongs to; in the last case after the process was started and killed.
  - S5, a compiled-set file is no longer regular, or the verification program is missing: tool failure `build_input_missing`, before the compiler starts.
  - S6, the compiler is not found or cannot start: tool failure `compiler_unavailable`, at the start of the build.
  - S7, the compiler ends with a non-zero status (a signal included; the record's reading): result, `outcome` broken, `condition` `build_exit_status` (owner).
  - S8, the build passes its time limit: result, broken, `condition` `build_time_limit` (owner).
  - S9, status 0 and no executable, or it cannot be moved: tool failure `build_output_missing`, after the build ended.
  - S10, the executable cannot be started: tool failure `executable_unstartable`, at the start of the process.
  - `condition` order: `build_time_limit`, `build_exit_status`, `time_limit`, `exit_status`, `report_form`, `check_value`; extending the order is the record's own. Form (B) becomes one of four strings. All six kinds are backend kinds that any backend may raise, the mock's scripts included.
  - Errors that one call raises in one class for two rows get no kind; the code task separates or registers them (⑱ (마)). They are: the OSError of S6/S9/temp-file removal; a missing cwd (S3 against S6 or S10); a TypeError for a setting against another argument; a local_run ValueError/TypeError for env against another argument; path errors (S3 against S5).
- Point 5: messages show no path, entry name, file byte, error text, setting value or log. The compiler log of the S7/S8 builds is kept in a file of the attempt and not returned (owner); its path, form and writer, and the logs of other builds, are ⑱ (나).
- Point 6: the order table with its ⑥ and ⑦ rows changed. A repeated call gets the stored result or the same tool failure and builds nothing.
- Point 7:
  - (가) answered for S3-S10, except two-row errors;
  - (나) answered for every setting, provisionally (⑱ (가)); no values;
  - (다) not answered;
  - run tools: O3 quoted only;
  - a note on sub-question ⑩.
- Point 8:
  - Code slices that can now be cut: the two `condition` values (`hilclaw/check_result.py`, `hilclaw/check_answer.py`; mind the positional pairing in `check_answer.py` and `check_judging.py`) and the six kinds in `BACKEND_KINDS`.
  - Not yet possible: the operation of `cpu_standin` (no setting values, no container design, no log file), and so the registration.
  - A-13: only the two owner-approved `condition` values enter the data plane; six `error.kind` values are named.
  - Runtime acceptance items: none beyond ADR-0056's.
- New sub-question ⑱ under OD-18, in five parts:
  - (가) settings placed in a file of the run or attempt, coder-chosen settings, request members, and the relation to `toolchain`;
  - (나) the log file;
  - (다) situations of the isolated environment;
  - (라) source and values of the backend's flags and environment;
  - (마) two-row errors.

### Register and coverage
- Status word of OD-18: `제안됨` before and after. Rule applied: the "상태 어휘" preamble. `확정` means the whole OD is decided, and OD-18 keeps a long 잔여 list, as it did after ADR-0056.
- OD-6, OD-14 and OD-16 rows and sections: no sentence became false, so none was edited. OD row count 30 before and after.
- OpenDecisionProposals OD-18: the ADR-0060 채택분 bullet; dated notes on ⑩ and ⑰; the new ⑱ bullet.
- Requirements OD-18 row: one 확정분 clause; the ⑩ and ⑰ 잔여 items updated; a ⑱ item added.
- StandardScenarios: heading note and the paragraph "2026-10-15 (2차)". Re-checked: S0-5/6/10, S1-3/4/6, S1-b-2/4, S2-2, S3-4, S6-3, S11-3, S8-3, and the storage and resume steps S0-6, S8-4, S2-3, S3-2. No verdict change, no gap.

### Inventory
Searched for ⑰, sub-question 17, S7, S8, condition, exactly four values, compile failure, link failure, time limit of the build, flags, task.build, 빌드가 ok가 아니게, 플래그.
- Covered by this record: ADR-0056 decisions 4-6 and 8 (the S3-S10 answers and the settings table); the text of OD-18 sub-question ⑰ (가)(나) in OpenDecisionProposals and Requirements.
- Left open and registered: ⑰ (다) of ADR-0056 (unchanged); the log file, prescribed or coder-chosen settings, situations of the container, the source of the flags, and two-row errors (all ⑱).
- Now less exact (listed in Consequences, not edited):
  - ADR-0042 decisions 3, 6, 7;
  - ADR-0021 decisions 2, 5;
  - ADR-0043 decisions 4, 7;
  - ADR-0044 decisions 2, 3, 5;
  - ADR-0045 decisions 1, 4 and Alternatives;
  - ADR-0047 decisions 5, 8;
  - ADR-0056 decisions 3, 4, 6, 8;
  - ADR-0017 decision 9;
  - the docstrings of `hilclaw/check_result.py`, `check_answer.py`, `check_operation.py`, `check_ending.py`, `check_judging.py`, `check_failure.py` and `harness/verification_build.py`.
- Not affected: ADR-0002 (line 13, "repair after a compile failure"; decision 6 (b) is cited only); the hits of S7 and S8 that name scenarios; `hilclaw/spec.py` and `gemm_contract.py` (`task.build`); `harness/timing_build.py`.

### Document checks
- Owner sentences O1-O5 checked word for word against comments 6183004538, 6182984913 and 6117798837, and the question 6164154089. The reviewer re-checked them in every round.
- Citations checked in place, decision numbers included. Statements about code checked against `clang_build.py`, `local_run.py`, `harness/verification_build.py`, `check_result.py`, `check_failure.py`, `check_answer.py` and `check_judging.py` at `97a0816`.
- Negative sweep:
  - no item of "Do not invent" is stated as decided;
  - S3-S10 have one answer each;
  - what the functions return or raise is mapped, and what cannot be placed is registered as ⑱ (마);
  - the eight names collide with nothing in `hilclaw/`, `tests/` or `ARCHITECTURE/`.
- Mechanical checks:
  - relative links resolve;
  - ADR-0060 and ⑱ were free at the push;
  - `git diff --stat origin/main` listed the record and the three documents only;
  - `i/lf`; `git diff --check` clean; `python -m ruff format --check .` exited 0.
- The push run on `main` for `4060d70` (workflow CI) was in_progress when this was written; that is not a BLOCKED reason.

### Runtime acceptance items
None beyond ADR-0056's.

### Owner notice (posted by the driver: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6184597227)
### OD-18 - the answers of the build of a check of correctness.check and the side its settings come through (first case) fixed by ADR-0060 under DRIVER §9 (T-0176)

ADR-0060 (commit 4060d70) answers parts (가) and (나) of OD-18 sub-question ⑰:
- S7 (compile or link failure) and S8 (build past its time limit) are broken results with `condition` `build_exit_status` / `build_time_limit` (your HQ-0020 answer). `condition` now has six values, the two build values first.
- The compiler's log of those builds is kept in a file of the attempt, never in the result or events.ndjson (your answer). Its path, form and writer are registered (sub-question ⑱ (나)).
- S3-S6, S9 and S10 are tool failures of six new backend kinds: build_directory_unusable, settings_refused, build_input_missing, compiler_unavailable, build_output_missing, executable_unstartable.
- Flags, trailing flags, compiler, both time limits and the environment are all the backend's own. The tool function hands none, and no value is decided.

Yours: the class of S7/S8, the two value names, keeping the log, the principle for the run tools' timing build, and the container (cited, not designed). Everything else is the record's own.

Provisional choices, most contestable first:
1. All settings are the backend's own. A setting later prescribed in `task.build`, chosen by the coder or stated for a run does not reach the build. So a kernel within its contract that needs a flag the backend does not give (OpenMP and intrinsics are allowed, #5 A-7) is stored as a broken `build_exit_status` result.
2. A compiler ended by a signal is read as S7.
3. S5, S9 and S10 are tool failures although they may follow from the attempt; a result would need a value you have not approved.

Limits: nothing was built or run; no setting has a value; the situations were read from host code, not from a container; the cause (machine, settings or kernel) is not established. The operation of `cpu_standin` for this tool still cannot be written to its end.

Register: OD-18 stays `제안됨`. New sub-question ⑱ under OD-18. The objection window ends 2026-10-22.

— posted by driver

### Follow-ups
- (planner, code mode) Add the two `condition` values to `hilclaw/check_result.py` and form (B) of `hilclaw/check_answer.py`, minding the positional pairing with `check_judging.py`. Add the six kinds to `BACKEND_KINDS` in `hilclaw/check_failure.py`. Tests per D12.
- (planner, document mode, small) The R7 Nits, not applied because the cap was reached:
  - in decision 4, narrow `NotADirectoryError` to the output path only;
  - give one line of reason why a wrongly typed setting is `settings_refused` while a wrongly typed argument the operation formed is `operation_answer_invalid`;
  - make the Status list "Single sentences rest on" match References (ADR-0006, 0010, 0026, 0040, 0044 and 0055 are missing), or mark it as not exhaustive;
  - optionally, mention the keeping of the log (⑱ (나)) in the ⑥ row of decision 6.
- (planner, document mode) Sub-questions ⑱ (나) (the log file, with `build.json`) and ⑱ (라) (the source of the backend's flags and environment) come before the `cpu_standin` operation. OD-14 ① (the container) gates it too.
- (planner, document mode, §9) The run-tool contracts of PLAN P1-1, taking the build answers from ADR-0060 and O3.
- (planner, code mode, small) The `hilclaw/check_operation.py` sentence on decision 8 / sub-question ⑩ (T-0175 Follow-ups) is still open.

Note for the next planner: ADR-0060 lets a code slice add only the two values and the six kinds. The operation of `cpu_standin` for `correctness.check` stays blocked on the setting values (OD-14, ⑱ (라)), the container design (OD-14 ①) and the log file (⑱ (나)). Do not plan it before those are answered.
