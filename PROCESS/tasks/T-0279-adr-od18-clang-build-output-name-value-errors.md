---
id: T-0279
title: Write ADR-0092 on which row of `correctness.check` the new pre-start check of the output file name of `clang_build.build` (a `ValueError` or, on POSIX, a `UnicodeEncodeError` with `parameter` "output", raised after the output path tests) lets an operation place, and what is now left of U4 (more of OD-18 sub-question 18 part (ma)); no `local_run.run`, no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18, "#5 D6"]
dependsOn: [T-0277, T-0278]
touchesFiles: [ARCHITECTURE/decisions/ADR-0092-od18-correctness-check-output-name-value-errors.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 140, files: 4}
hq: []
---
## Why

ADR-0091 (T-0277, landed `d993253`) placed the pre-start `ValueError`s named `"sources"`, `"output"` and `"kernel_sources"` as no row. It left U4 open: a `ValueError` from after the checks up to and including the start, which holds what `build` passes on from `subprocess`. ADR-0091 decision 3 named the way out: a later record that reads what `subprocess` raises, or a code change that makes `build` refuse such a value in a named check before the start.

T-0278 (PR #176, squash-merged as `304a8fc`) made one such code change:

- `build` now runs `_check_argument(str(target), ...)` inside a second `_parameter("output")` step.
- That step runs **after** the output path tests (`is_dir` of the directory, `exists`, `is_dir` of the path) and **before** the compiler lookup.
- A NUL character in the output file name now raises `ValueError` with `parameter` `"output"`. On POSIX, a character `os.fsencode` cannot convert raises its `UnicodeEncodeError` with the same `parameter`. Before, such a name passed the path tests and reached `subprocess.Popen` through the temporary name, as an unnamed `ValueError` (part of U4).
- A defect in a parent directory still gives `FileNotFoundError` with `path_role` `"output"`.

No record has placed this new error yet. ADR-0091's observations (K1: "Inside `_parameter("output")` runs only the forming of the absolute path"; K4: what stays unnamed) are now less exact. This task writes the record. It is the follow-up in T-0278's `## Follow-ups`.

ADR-0088 is held by the unlanded branch `claude/T-0264-adr-od18-local-run-parameter`, and ADR-0089 to ADR-0091 are landed. So this record takes **ADR-0092**: on 2026-10-18 no branch holds that number.

This is a design-level part of OD-18, not an owner-only item (DRIVER §9). It closes by an ADR under D6, with the §9 notice. It needs no real `claude`, compiler or container (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming convention, the `Task: T-0279` trailer, size cap;
  - §8: the driver tail of #5 comments;
  - §9: who may close an OD; the 7-day notice.
- `CLAUDE.md`, the standing rules. In particular:
  - "문서 커버리지 재검사";
  - "미결은 발명하지 않는다";
  - "세션 진입 점검";
  - "브랜치·merge 절차" (document mode).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0091-od18-correctness-check-sources-output-kernel-sources-value-errors.md`, whole (115 lines). This record continues it.
  - Read in particular Context K1, K2 and K4, decisions 1, 2, 3, 5, 6 and 7, the walk-through, and Consequences.
  - Follow its structure, but do not copy its sentences.
- `ARCHITECTURE/decisions/ADR-0090-od18-correctness-check-clang-build-named-setting-value-errors.md`: decision 2 (the `"flags"`/`"compiler"` NUL and `os.fsencode` refusals placed as S4, because those values are settings of the backend's). This is the contrast for the output name, which is the operation's own.
- `ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`: decision 3 (`"cwd"`: no row, and its reading that a `ValueError` for an argument the operation forms is no row as well).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 3 (from line 46; which side holds each setting; the artefact path is the operation's own) and decision 4 (from line 69; the S3 and S4 rows, and "what `clang_build.build` passes on from `subprocess` … was not read").
- Read `ADR-0045-…` decisions 4 to 6, `ADR-0078-…` decision 2, `ADR-0083-…` decision 2 and `ADR-0086-…` decisions 3 and 4 only where you cite them.
- `hilclaw/clang_build.py` at `304a8fc`. Read these as files and do not run them:
  - the docstring of `build` (lines 207-297), especially "Raised before anything is started" and the sentence "Once the output path has passed its tests, its absolute path is checked the same way" (around line 235), and the `parameter` paragraph ("The check of `output` forms its absolute path and, after the tests of that path below, …", around line 262);
  - the check steps, the output path tests, the second `_parameter("output")` step, and the temporary name and command (lines 302-337);
  - `_parameter` (line 472) and `_check_argument` (line 539).
- `hilclaw/harness/verification_build.py`: `build_verification_executable`, its docstring and body (lines 41-90), only to confirm that the artefact path is the one the operation hands and that nothing there changed.
- `PROCESS/tasks/T-0278-clang-build-output-name-checks-before-start.md`: `## Why`, `## Result` and `## Follow-ups` only. Note its second follow-up: the example `"k\udcff.o"` converts on POSIX through `surrogateescape`; if the record shows an example, use a lone surrogate such as `"\ud800"`.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and register row OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's "기록 규칙" (line 8);
  - section `## OD-18` (from line 250), with its adopted-record lines (ending at line 302) and the status at the end of sub-question 18 (line 315).
- `ARCHITECTURE/StandardScenarios.md`:
  - `## 검사 규칙` (line 13);
  - `# 검사 결과` (from line 168), with its first paragraph (line 170) and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md), before any edit:
   - Run `gh pr list`, then read issues #4, #5, #7 and #8. If an open PR edits OD-18 sub-question 18 or any of the four files, stop and return BLOCKED (open-PR conflict risk).
   - Confirm that `ADR-0092` is free on `main` and on every remote branch. If it is taken, use the next free number and say so in `## Result`.
   - Look on #5 for an owner comment (one without the driver tail) on ADR-0091, T-0278 or (ma). If there is one, cite it and follow it.
   - Check whether HQ-0027 has been answered. If it has and the answer bears on this record, say how in `## Result`.
   - Do not land T-0264's branch.
2. **New file** `ARCHITECTURE/decisions/ADR-0092-od18-correctness-check-output-name-value-errors.md`, in the ADR-0001 record format.
   - Status: accepted under DRIVER §9 (D6). It says which sentences are the owner's, which are cited, and which are the record's own design.
   - Statements about code are observations at `304a8fc`. They bind no code, and nothing is established by running code.
3. **What the record weighs and answers** for `correctness.check` of the first case and of the mock. Each answer is the record's own design under §9 and states its reason and its cost. Leaving a case open with a reason is an acceptable answer.
   - **(a) The new named error.** A `ValueError` (NUL character) or, on POSIX, a `UnicodeEncodeError` (from `os.fsencode`) with `parameter` `"output"`, raised by the step after the output path tests.
     - Weigh whether ADR-0091 decision 2 ("a named `ValueError` of `"output"` is no row") already covers it, or whether its being raised **after** the path tests, for a path that passed them, changes the reading. ADR-0091 placed U3, raised while the absolute path is formed.
     - Weigh "no row" against S3 (the build directory cannot be made or written) and against S4 by analogy with ADR-0090 decision 2, where the same two refusals for flags and compiler parts are S4 because those are settings. Say why the artefact path, which is the operation's own (ADR-0060 decision 3), is not a setting.
     - State the cost: for example, a name the operation forms from a directory the platform let it make, or a POSIX file system encoding that cannot hold the name. Do not claim what a platform does unless the record has read it. Do not establish anything by running code.
   - **(b) What is now left of U4.** List from the code at `304a8fc` every pre-start `ValueError` of `build` that still carries no `parameter`: from forming the temporary name, the command, the clock, and `subprocess.Popen`.
     - Say what the new check removes from U4: a NUL or unencodable character in the output file name, which before reached the command through the temporary name.
     - Weigh whether the temporary name itself can now raise a `ValueError` before the start (it is built from `target.stem`, `target.suffix`, the pid and `secrets.token_hex`). Read only the code of `build` and the documentation you cite; if it is not read, say so.
     - What `subprocess.Popen` raises (for example for an `env` with no `items` method) stays unread unless the record reads it. A reading of `subprocess` is not required by this task. If the record does not read it, U4 stays open with the reason of ADR-0091 decision 3, now narrowed. A further code change may be named as a follow-up, not decided.
   - **(c) No log and the message.** For the no-row case there is no `settings_refused` message. Say only what follows from ADR-0078 decision 2 and ADR-0045 for the log and the message, and add no new rule. Note that the message of the new check does not show the path.
   - **(d) No data-plane change.** Add none of the following:
     - a value of `error.kind` or `condition`;
     - a member or a reserved kind;
     - a change to `schema_version` or the layout version (CLAUDE.md A-13).

     `parameter` is an attribute of an in-process exception. If only a new value would place a case, leave it open, say so in the record, and name in this task's `## Result` Follow-ups that it needs an owner HQ. Do not decide it.
   - **(e) How far (ma) is answered.** End the decisions with this.
     - List what this record answers, and which entries of ADR-0091 decisions 3 and 7 it narrows or answers.
     - List every entry of (ma) that stays open, read from ADR-0091 decision 7 as it stands on `main`.
     - Keep the `local_run.run` entries listed as open, because ADR-0088 is unlanded.
   - **Walk-through and Alternatives tables.** The walk-through has one line for each of: a NUL character in the output file name; on POSIX, an unencodable character in it; the same defect in a parent directory (which keeps `FileNotFoundError` with `path_role` `"output"`, ADR-0086); and at least one line for what (b) leaves open. Use the run names of ADR-0056 as ADR-0091 does. The Alternatives cover at least:
     - the chosen answers;
     - S3 for the new error;
     - S4 for the new error, by analogy with ADR-0090 decision 2;
     - treating the new error as still part of U4, because it is raised after the path tests;
     - a new kind, declined as a data-plane change.
4. **No sentence of an earlier ADR is edited.** Consequences lists the sentences that become less exact. Find them by reading ADR-0091 (and ADR-0090 and ADR-0089 where they speak of the output path or of U4), not by relying on this list alone. At least check:
   - ADR-0091 Context K1 ("Inside `_parameter("output")` runs only the forming of the absolute path", and "So U3 carries `"output"` where the path is formed"), K2, K4 (the list of U4), decision 2 ("U3, one raised while the absolute artefact path is formed"), decision 3 ("What is left is U4 alone" and "What would let it be placed", now partly done by T-0278), decision 7, the walk-through, Consequences and Boundaries.

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
   - Rewrite the open parts in place: the row's `**잔여**:` only if its text changes, and the status at the end of sub-question 18. In that status, the "남음" entry on the unnamed pre-start `ValueError` of `clang_build.build` must say what is now left, if the record narrows it.
   - Do not restate the record, and add no dated paragraph. OD-18 keeps its status word.
   - Re-check coverage by StandardScenarios' rules for every scenario row that cites OD-18. Update `# 검사 결과` as its first paragraph says.
6. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0279-<slug>`.
   - Run the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Rebase on `origin/main` and push directly to `main`, with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0279`.
   - Delete the branch.
   - After landing, post the §9 notice on issue #5 in English, ending with the driver tail of DRIVER §8, and record its URL in `## Result`. If the driver's spawn prompt says the driver posts it, write the notice text in `## Result` instead.
7. **Size**: one new file and three edited files, at most 300 changed lines in total.
8. **Result** records:
   - the landed commit, and the review rounds with their findings;
   - the §9 notice URL or its text;
   - the session entry check;
   - the overlap with the unlanded branches `claude/T-0264-*`, `claude/T-0210-*` and `claude/T-0231-*`. They edit the same register row, the sub-question 18 status and the "최근 재검사" line, and must rebase over this edit. When ADR-0088 lands, its text must keep the entries of ADR-0089 to this record;
   - the follow-ups.

   The executor starts no `claude` program, compiler or container (D16).

## Out of Scope

- `local_run.run` and every entry that waits for ADR-0088 and HQ-0027. The branch `claude/T-0264-*` is not touched or landed.
- `hilclaw/harness/timing_build.py` and the timing build of `sim.run` / `board.run` (sub-question 19; T-0210, HQ-0021).
- Any change to `hilclaw/`, `tests/`, CI, `.claude/` or any settings file, to ADR-0001 to ADR-0091, or to `ARCHITECTURE/UsageCases.md`.
- A reading of what `subprocess.Popen` raises, beyond what the record chooses to cite; it is not required here.
- The other open entries of (ma), except to restate them as open:
  - the unroled `OSError` of `build`;
  - the `CompilerRunError` with `timed_out` false and `returncode` `None`;
  - an unnamed `TypeError`;
  - the rest of what `build` passes on from `subprocess`.
- Parts (ga), (da), (ra) and the size bound of (na) of sub-question 18; sub-questions 17 and 19.
- Any new value of `error.kind` or `condition`, any data-plane member, and any owner-only item (DRIVER §9: #5 A/B items, OD-3, OD-25, C-6).

## Follow-ups

## Result
