---
id: T-0277
title: Write ADR-0091 on which row of `correctness.check` a pre-start `ValueError` that now carries `parameter` "sources", "output" (of `clang_build.build`) or "kernel_sources" (of `build_verification_executable`) lets an operation place, and whether the unnamed rest (U4, U5) can now be placed (more of OD-18 sub-question 18 part (ma)); no `local_run.run`, no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18, "#5 D6"]
dependsOn: [T-0275, T-0276]
touchesFiles: [ARCHITECTURE/decisions/ADR-0091-od18-correctness-check-sources-output-kernel-sources-value-errors.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: []
---
## Why

ADR-0090 (T-0275, landed `61504e8`) left every pre-start `ValueError` with no `parameter` open. Its Context N3 lists them as U1 to U6:

- U1: no source.
- U2: one raised inside the check of `sources`.
- U3: one raised while the output path is formed or tested.
- U4: one from after the checks, up to and including the start (what `build` passes on from `subprocess`).
- U5: the no-kernel-source error of `build_verification_executable`.
- U6: one raised while `build_verification_executable` makes a tuple of `kernel_sources`.

ADR-0090 decision 3 kept them open because no step of the operation's own tells U2, U3 and U6 (an argument the operation forms) from U4 (which may hold a setting that `subprocess` refuses). It named the way out: give U1-U3 and U6 a `parameter`, after which "what stays unnamed would be U5 and U4".

T-0276 (PR #175, squash-merged as `1d61696`) made that code change:

- `build` now tags every `TypeError` or `ValueError` from the checks of `sources` and `output` with `parameter` `"sources"` / `"output"`. This includes the no-source error and one Python or a handed object's code raises inside the check, such as a path object whose `__fspath__` fails.
- The output path tests stay outside the `output` step. Their `OSError` keeps `path_role` and no `parameter`.
- `build_verification_executable` tags a `TypeError` or `ValueError` raised while iterating `kernel_sources` with `"kernel_sources"`. Its own no-kernel-source `ValueError` (U5) carries none.

No record has placed these newly named errors. This task writes that record. It is the follow-up named in T-0276's `## Follow-ups`, and it also takes up the two non-blocking Nits in T-0275's `## Follow-ups`.

`local_run.run` is out of scope. ADR-0088, on `local_run.run` only, is held by the unlanded branch `claude/T-0264-adr-od18-local-run-parameter` and waits on HQ-0027. ADR-0090 is landed, so this record takes **ADR-0091**.

This is a design-level part of OD-18, not an owner-only item (DRIVER §9). It closes by an ADR under D6, with the §9 notice. It needs no real `claude`, compiler or container (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming convention, the `Task: T-0277` trailer, size cap;
  - §8 (the driver tail of #5 comments);
  - §9 (who may close an OD; the 7-day notice).
- `CLAUDE.md`, the standing rules. In particular:
  - "문서 커버리지 재검사";
  - "미결은 발명하지 않는다";
  - "세션 진입 점검";
  - "브랜치·merge 절차" (document mode).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0090-od18-correctness-check-clang-build-named-setting-value-errors.md`, whole (115 lines). This record continues it.
  - Read in particular Context N3 and N4, decisions 1, 3 and 7, and Consequences.
  - Follow its structure, but do not copy its sentences.
- `ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`: decision 3 (`"cwd"`: no row, and its reading that a `ValueError` for an argument the operation forms is no row as well), decision 4 (`"kernel_sources"`: no row), decision 5 and decision 9.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`: decisions 1, 2 and 4 (a named `"sources"`/`"output"` `TypeError` is no row; not S5, not S3).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`:
  - decision 3 (from line 46): which side holds each setting;
  - decision 4 (from line 69): the S4 row, "a `TypeError` for an argument that is no setting … is no row", the no-kernel-source sentence, and "what `clang_build.build` passes on from `subprocess` … was not read";
  - decision 5 (from line 105): messages;
  - decision 7 (from line 122): its sentence "except for an error that one call raises in one class for two rows" (T-0275 Nit 2);
  - Consequences (from line 154).
- Read `ADR-0045-…` decisions 4 and 5, `ADR-0056-…` decisions 3 and 4, `ADR-0078-…` decision 2 and `ADR-0083-…` decision 2 only where you cite them.
- `hilclaw/clang_build.py` at `1d61696`. Read these as files and do not run them:
  - the docstring of `build`, from "Raised before anything is started" (line 221), especially the `parameter` paragraph (lines 250-262);
  - the check steps (lines 298-324);
  - `_parameter` (line 466) and `_checked_sources` (line 540);
  - `compiler_version` (line 407), only to confirm it still tags nothing.
- `hilclaw/harness/verification_build.py`: `build_verification_executable`, its docstring and body (lines 41-90).
- `PROCESS/tasks/T-0276-clang-build-sources-output-value-errors-parameter.md`: "The change, stated", `## Result` and `## Follow-ups` only.
- `PROCESS/tasks/T-0275-adr-od18-clang-build-named-setting-value-errors.md`: `## Follow-ups` only (the two Nits).
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and register row OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's "기록 규칙" (line 8);
  - section `## OD-18` (lines 250-318), with its adopted-record lines (ending at line 301) and sub-question 18 (line 314).
- `ARCHITECTURE/StandardScenarios.md`:
  - `## 검사 규칙` (line 13);
  - `# 검사 결과` (from line 168), with its first paragraph (line 170) and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md), before any edit:
   - Run `gh pr list`, then read issues #4, #5, #7 and #8. If an open PR edits OD-18 sub-question 18 or any of the four files, stop and return BLOCKED (open-PR conflict risk).
   - Confirm that `ADR-0091` is free on `main` and on every remote branch. If it is taken, use the next free number and say so in `## Result`.
   - Look on #5 for an owner comment (one without the driver tail) on ADR-0090, ADR-0089, ADR-0087, ADR-0060 decision 4, T-0276 or (ma). If there is one, cite it and follow it.
   - Check whether HQ-0027 has been answered. If it has and the answer bears on this record, say how in `## Result`.
   - Do not land T-0264's branch.
2. **New file** `ARCHITECTURE/decisions/ADR-0091-od18-correctness-check-sources-output-kernel-sources-value-errors.md`, in the ADR-0001 record format.
   - Status: accepted under DRIVER §9 (D6). It says which sentences are the owner's, which are cited, and which are the record's own design.
   - Statements about code are observations at `1d61696`. They bind no code, and nothing is established by running code.
3. **What the record weighs and answers** for `correctness.check` of the first case and of the mock. Each answer is the record's own design under §9 and states its reason and its cost. Leaving a case open with a reason is an acceptable answer.
   - **(a) A named `ValueError` with `parameter` `"sources"` or `"output"`** of `build`, and one with `"kernel_sources"` of `build_verification_executable`.
     - Weigh "no row" against ADR-0060 decisions 3 and 4, ADR-0087 decision 4 and ADR-0089 decisions 3 and 4. These placed the `TypeError` of the same names and the `"cwd"` `ValueError` as no row.
     - Say why it is not S5 and not S3.
     - Cover U1 (now `"sources"`, which cannot arise through `build_verification_executable`; ADR-0089 P4) and U2, U3 and U6 as T-0276 now tags them.
     - Cover a `ValueError` raised inside a handed object's code (for example a source's `__fspath__`). The program source that `build_verification_executable` adds is part of `"sources"`; say what that costs.
   - **(b) What stays unnamed.** List from the code at `1d61696` every pre-start `ValueError` of `build` and of `build_verification_executable` that still carries no `parameter`. Expect U4 and U5, but read the code to confirm.
     - The operation rules out U5 by its own step (ADR-0090 decision 3).
     - Weigh whether an unnamed `ValueError` that the operation meets through `build_verification_executable` can now be placed. After U5 is ruled out, only U4 is left: what `build` passes on from `subprocess`, which ADR-0060 decision 4 left "not read" and ADR-0083 decision 2 keeps open.
     - If it cannot be placed without reading U4 into a row, leave it open with the reason. A further code change may be named as a follow-up, not decided.
   - **(c) `compiler_version`.** Keep it a Boundary unless the record finds that an operation of a check now calls it.
   - **(d) No log and the message.** For the no-row cases there is no `settings_refused` message. Say only what follows from ADR-0078 decision 2 and ADR-0045 for the log and the message, and add no new rule.
   - **(e) No data-plane change.** Add none of the following:
     - a value of `error.kind` or `condition`;
     - a member or a reserved kind;
     - a change to `schema_version` or the layout version (CLAUDE.md A-13).

     `parameter` is an attribute of an in-process exception. If only a new value would place a case, leave it open, say so in the record, and name in this task's `## Result` Follow-ups that it needs an owner HQ. Do not decide it.
   - **(f) How far (ma) is answered.** End the decisions with this.
     - List what this record answers, and which entries of ADR-0090 decisions 3 and 7 and of ADR-0089 decision 9 it narrows or answers.
     - List every entry of (ma) that stays open, read from ADR-0090 decision 7 as it stands on `main`.
     - Keep the `local_run.run` entries listed as open, because ADR-0088 is unlanded.
   - **Walk-through and Alternatives tables.** The walk-through has one line per named case of (a) and at least one line for what (b) leaves open or places. The Alternatives cover at least:
     - the chosen answers;
     - S5 for `"sources"`/`"kernel_sources"` and S3 for `"output"`;
     - no row only for the `ValueError` the check itself raises, with one raised inside a handed object's code left open;
     - a new kind, declined as a data-plane change.
4. **No sentence of an earlier ADR is edited.** Consequences lists the sentences that become less exact. Find them by reading ADR-0060, ADR-0087, ADR-0089 and ADR-0090, not by relying on this list alone. At least check:
   - ADR-0090: Context N3 ("what stays unnamed"), decision 1 ("an unnamed `ValueError` is one of U1 to U6"), decision 3 (including "What would let it be placed", now done), decision 7 (the narrowed entry), the walk-through, Consequences ("A code task that tags … is a candidate follow-up") and Boundaries;
   - ADR-0089: decision 4's "What stays unnamed", decision 5 and decision 9;
   - ADR-0087: T-numbered observations and decision 2's sentences on a `ValueError` of the `sources`/`output` checks;
   - ADR-0060: decision 7's "except for an error that one call raises in one class for two rows" (T-0275 Nit 2).

   Consequences also states three things:
   - what a later code task of the `cpu_standin` operation applies;
   - that the record binds no code;
   - "Runtime acceptance items: none".
5. **Register, proposals and coverage edits** follow the recording rules written in those files, as they stand on `main`:
   - the Requirements register's "행 형식" (line 84);
   - the OpenDecisionProposals header's "기록 규칙" (line 8);
   - the first paragraph of StandardScenarios `# 검사 결과` (line 170).

   Do not take the wording of earlier task files or the shape of earlier edits as the model. Concretely:
   - Add one link for the new ADR to the OD-18 row's `**확정분**:`, and one adopted-record line in OpenDecisionProposals `## OD-18`.
   - Rewrite the open parts in place: the row's `**잔여**:` only if its text changes, and the status at the end of sub-question 18. In that status, the "남음" entry on the unnamed pre-start `ValueError` must say what is now left (T-0275 Nit 1 is superseded or taken up there).
   - Do not restate the record, and add no dated paragraph. OD-18 keeps its status word.
   - Re-check coverage by StandardScenarios' rules for every scenario row that cites OD-18. Update `# 검사 결과` as its first paragraph says.
6. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0277-<slug>`.
   - Run the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Rebase on `origin/main` and push directly to `main`, with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0277`.
   - Delete the branch.
   - After landing, post the §9 notice on issue #5 in English, ending with the driver tail of DRIVER §8, and record its URL in `## Result`. If the driver's spawn prompt says the driver posts it, write the notice text in `## Result` instead.
7. **Size**: one new file and three edited files, at most 300 changed lines in total.
8. **Result** records:
   - the landed commit, and the review rounds with their findings;
   - the §9 notice URL or its text;
   - the session entry check;
   - the overlap with the unlanded branches `claude/T-0264-*`, `claude/T-0210-*` and `claude/T-0231-*`. They edit the same register row, the sub-question 18 status and the "최근 재검사" line, and must rebase over this edit. When ADR-0088 lands, its text must keep the entries of ADR-0089, ADR-0090 and this record;
   - the follow-ups.

   The executor starts no `claude` program, compiler or container (D16).

## Out of Scope

- `local_run.run` and every entry that waits for ADR-0088 and HQ-0027. The branch `claude/T-0264-*` is not touched or landed.
- `hilclaw/harness/timing_build.py` and the timing build of `sim.run` / `board.run` (sub-question 19; T-0210, HQ-0021).
- Any change to `hilclaw/`, `tests/`, CI, `.claude/` or any settings file, to ADR-0001 to ADR-0090, or to `ARCHITECTURE/UsageCases.md`.
- The other open entries of (ma), except to restate them as open:
  - the unroled `OSError` of `build`;
  - the `CompilerRunError` with `timed_out` false and `returncode` `None`;
  - an unnamed `TypeError`;
  - the rest of what `build` passes on from `subprocess`.
- Parts (ga), (da), (ra) and the size bound of (na) of sub-question 18; sub-questions 17 and 19.
- Any new value of `error.kind` or `condition`, any data-plane member, and any owner-only item (DRIVER §9: #5 A/B items, OD-3, OD-25, C-6).

## Follow-ups

## Result
