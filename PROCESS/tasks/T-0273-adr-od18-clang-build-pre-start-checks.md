---
id: T-0273
title: Write ADR-0089 on which rows of `correctness.check` the pre-start checks that `clang_build.build` and `build_verification_executable` gained after ADR-0087 (T-0267, T-0268, T-0270, T-0271) let an operation place - `parameter` "env"/"cwd", the NUL and unencodable flag or compiler part, the too-long time limit, `parameter` "kernel_sources" (more of OD-18 sub-question 18 part (ma)); no `local_run.run`, no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18, "#5 D6"]
dependsOn: [T-0262, T-0267, T-0268, T-0270, T-0271]
touchesFiles: [ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 170, files: 4}
hq: []
---
## Why

ADR-0087 (T-0262, landed `31b0654`) placed the `TypeError` of `clang_build.build` that carries `parameter` for `correctness.check`: S4 `settings_refused` for `"timeout_s"`, `"flags"`, `"trailing_flags"`, `"compiler"`; no row for `"sources"`, `"output"`. It left open, among others (its decision 5 and decision 8), an unnamed `TypeError` from `subprocess.Popen` or later, such as an `env` that cannot be handed over, and the `TypeError` that `build_verification_executable` raises itself for `kernel_sources` (its T5).

Four code tasks have since changed what these functions state before anything is started. None of them placed anything in a row:

- **T-0267** (PR #168, `e932bf3`): `build` checks `env` and `cwd` after the compiler is found and before the start. A `TypeError` or `ValueError` from those checks carries `parameter` `"env"` or `"cwd"`. A missing `cwd` still fails the start as `CompilerNotStartedError`.
- **T-0268** (PR #169, `8aee9ba`): `build` refuses before the start a NUL character in a flag, a trailing flag or a compiler-prefix part after the first, with `ValueError`. On POSIX it also refuses a part that `os.fsencode` cannot convert, passing on its `UnicodeEncodeError`. Neither carries `parameter`. Before this change these were "whatever `clang_build.build` passes on from `subprocess`".
- **T-0270** (PR #171, `e2ae330`): the `TypeError` that `build_verification_executable` raises itself for `kernel_sources` carries `parameter` `"kernel_sources"`. Its `ValueError` for no kernel source carries none.
- **T-0271** (PR #172, `e6553a2`) and **T-0272** (PR #173, `57172c0`): `build` and `compiler_version` refuse before the start a `timeout_s` above (2**31 - 1) / 1000 s with `ValueError` (no `parameter`), instead of an `OverflowError` after the start. T-0272 changed only a message.

The follow-ups of those tasks deferred one record "after HQ-0027". That record would cover these changes together with the `local_run.run` ones. HQ-0027 is about the review-round limit of T-0264 (ADR-0088, on `local_run.run` only). The `clang_build` side does not depend on how HQ-0027 is answered, so this task takes only that side. `local_run.run` stays with ADR-0088 and HQ-0027. **ADR-0088 is held by the unlanded branch `claude/T-0264-adr-od18-local-run-parameter`, so this record takes ADR-0089** (precedent: T-0242 took 0078 while 0068 and 0074 were held).

This is a design-level part of OD-18, not an owner-only item (DRIVER §9). It closes by an ADR under D6, with the §9 notice. It needs no real `claude` (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, `Task:` trailer, size cap), §8 (the driver tail of #5 comments) and §9 (who may close an OD; the 7-day notice).
- `CLAUDE.md`: the standing rules. In particular "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", and the branch and merge procedure (document mode).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`, whole. It is the record this one continues. Its structure (Status, Context with observations, Decision 1-8, Walk-through, Alternatives, Consequences, Boundaries, References) is the form to follow. Do not copy its sentences.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 3 (lines 46-68, which side holds each setting, `env` and `cwd` included), decision 4 (lines 69-104, the rows S3 to S10 and "a `ValueError` or `TypeError` for a setting … → S4"), decision 5 (lines 105-109, messages) and Consequences.
- `ARCHITECTURE/decisions/ADR-0086-od18-correctness-check-path-role.md` decisions 6 and 8, and `ADR-0083-…` decision 2, for the open entries of (ma) this record must restate. Read `ADR-0078-…` decision 2 (no log before a start) and `ADR-0045-…` decisions 4 and 5 (`operation_answer_invalid`) only where you cite them.
- `hilclaw/clang_build.py` at `57172c0`: the docstring and checks of `build` (lines 196-322), `compiler_version` (around line 404), `_parameter`, `_check_env`, `_check_cwd`, `_check_timeout`, `_checked_flags`, `_check_argument`, `_checked_sources`, `_resolve` (lines 462-570). `hilclaw/harness/verification_build.py` `build_verification_executable` (lines 41-90). Read them as files and do not run them.
- `PROCESS/tasks/T-0267-*.md`, `T-0268-*.md`, `T-0270-*.md`, `T-0271-*.md`: `## Result` and Follow-ups only.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and register row OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8) and section `## OD-18` (from line 250). Read its adopted-record lines and the end of sub-question 18.
- `ARCHITECTURE/StandardScenarios.md`: the check rules near the top and `# 검사 결과` (from line 168), with its first paragraph (line 170) and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md), before any edit:
   - Run `gh pr list`, then read issues #4, #5, #7 and #8. If an open PR edits OD-18 sub-question 18 or any of the four files, stop and return BLOCKED (open-PR conflict risk).
   - Confirm that `ADR-0089` is the next free number on `main` and that no remote branch other than `claude/T-0264-*` holds ADR-0088 or ADR-0089. If 0089 is taken, use the next free number and say so in `## Result`.
   - Look on #5 for an owner comment (one without the driver tail) that speaks to ADR-0060 decision 4, ADR-0087, T-0267, T-0268, T-0270, T-0271 or (ma). If there is one, cite it and follow it. Also check whether HQ-0027 has been answered. If it has, and the answer bears on this record, say how in `## Result`. Do not land T-0264's branch.
2. **New file** `ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`, in the ADR-0001 record format.
   - Status: accepted under DRIVER §9 (D6). It says which sentences are the owner's, which are cited and which are the record's own design.
   - Statements about code are observations at `57172c0` and bind no code. Nothing is established by running code.
3. **What the record weighs and answers** for `correctness.check` of the first case and of the mock. The answers are the record's own design under §9; each choice states its reason and its cost. Leaving a case open with a reason is an acceptable answer.
   - **(a) `parameter` `"env"` and `"cwd"` of `build`.** Weigh S4 for `"env"` against ADR-0060 decision 3's side of `env`. Weigh no row for `"cwd"` (the operation's own, if decision 3 says so) against S4 and S3. Each applies to both a `TypeError` and a `ValueError` of those checks, one Python raises inside them included. State that a missing `cwd` is still `CompilerNotStartedError`, which ADR-0079/ADR-0080 already place. Do not re-place it.
   - **(b) The unnamed pre-start `ValueError` of `build`.** List from the code every pre-start `ValueError` that carries no `parameter`: no source, the two `timeout_s` refusals, the empty compiler prefix, a flag that sets the output, the NUL check of T-0268, and on POSIX the `UnicodeEncodeError` of T-0268. Say which of them is for a setting and which for an argument the operation forms. Then weigh whether ADR-0060 decision 4's "a `ValueError` … for a setting … → S4" already reaches the T-0268 and T-0271 cases. Also weigh whether an operation that sees only the class can tell them from the no-source `ValueError`. Check whether that one can arise at all through `build_verification_executable`, which adds the program source and refuses no kernel source itself. If the class alone cannot place them, leave them open with the reason. A code change (for example a `parameter` on these `ValueError`s) may be named as a follow-up, not decided.
   - **(c) `parameter` `"kernel_sources"` of `build_verification_executable`.** Weigh no row, as for `"sources"` in ADR-0087 decision 4. Say what stays unnamed: its `ValueError` for no kernel source.
   - **(d) The too-long time limit.** It is now a pre-start `ValueError` of `build` and of `compiler_version` (T-0271). Say whether an `OverflowError` after the start is still reachable from `build` for this cause. The errors of `compiler_version` stay a Boundary unless the record finds that an operation calls it.
   - **(e) No log and the message.** No compiler was started, so no log is handed to the keeper (ADR-0078 decision 2). Say what an S4 message may name under ADR-0060 decision 5, with no new rule.
   - **(f) No data-plane change.** Add no value of `error.kind` or `condition`, no member, no reserved kind, and no change to `schema_version` or the layout version (CLAUDE.md A-13). `parameter` is an attribute of an in-process exception, not a data-plane member. If only a new value would place a case, leave it open, say so in the record, and name in this task's `## Result` Follow-ups that placing it needs an owner HQ. Do not decide it.
   - **(g) How far (ma) is answered.** End the decisions with this. List what this record answers. List every entry of (ma) that stays open, read from ADR-0087 decision 8 and the records it cites as they stand on `main`. Say which entries of ADR-0087 decision 8 this record narrows. Keep the `local_run.run` entries listed as open; ADR-0088 is unlanded.
   - **Walk-through and Alternatives tables**: one walk-through line per new case of (a) to (d), and at least one line for a case left open. Alternatives must cover at least these:
     - the chosen answers;
     - leaving all of them open;
     - S4 for every pre-start `ValueError` of `build` by its class;
     - a new kind (declined as a data-plane change);
     - the operation's own type and value tests in place of `parameter`.
4. **No sentence of an earlier ADR is edited.** Consequences lists the sentences that become less exact. Find each by reading ADR-0060, ADR-0079 to ADR-0087, and do not rely on this list alone. At least check ADR-0087 T4, T5, decision 5 (the `env` example and `kernel_sources`), decision 8 and Boundaries, and ADR-0083 decision 2. Consequences also states three things: what a later code task of the `cpu_standin` operation applies; that the record binds no code; and "Runtime acceptance items: none" (no `claude`, compiler or container is started or required).
5. **Register, proposals and coverage edits** follow the recording rules written in those files, read as they stand. These are the Requirements register's "행 형식" (line 84), the OpenDecisionProposals header's "기록 규칙" (line 8), and the first paragraph of StandardScenarios `# 검사 결과` (line 170). Take neither the wording of earlier task files nor the shape of earlier edits as the model.
   - Add one link for ADR-0089 to the OD-18 row's `**확정분**:` and one adopted-record line in OpenDecisionProposals `## OD-18`.
   - Rewrite the open parts in place: the row's `**잔여**:` if its text changes, and the end of sub-question 18 ("→ 부분 답: … 남음: …"). Do not restate the record and add no dated paragraph. OD-18 keeps its status word.
   - Re-check coverage by StandardScenarios' rules for every scenario row that cites OD-18, and update `# 검사 결과` as its first paragraph says.
6. **Document mode** (CLAUDE.md A-13):
   - Branch `claude/T-0273-<slug>`.
   - Run the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Rebase on `origin/main` and push directly to `main`, with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0273`.
   - Delete the branch.
   - After landing, post the §9 notice on issue #5 in English, ending with the driver tail of DRIVER §8, and record its URL in `## Result`. If the driver's spawn prompt says the driver posts it, write the notice text in `## Result` instead.
7. **Size**: one new file and three edited files, at most 300 changed lines in total.
8. **Result** records:
   - the landed commit and the review rounds with their findings;
   - the §9 notice URL or its text;
   - the session entry check;
   - the overlap with the unlanded branches `claude/T-0264-*`, `claude/T-0210-*` and `claude/T-0231-*`, which touch the same register lines and must rebase over this edit;
   - the follow-ups.

   The executor starts no `claude` program, compiler or container (D16).

## Out of Scope

- `local_run.run` and every entry of T-0263 to T-0266 and T-0269: they wait for ADR-0088 and HQ-0027. The branch `claude/T-0264-*` is not touched or landed.
- `hilclaw/harness/timing_build.py` and the timing build of `sim.run` / `board.run` (sub-question 19; T-0210, HQ-0021).
- Any change to `hilclaw/`, `tests/`, CI, `.claude/` or any settings file; any change to ADR-0001 to ADR-0087 or to `ARCHITECTURE/UsageCases.md`.
- The other open entries of (ma) except to restate them as open. These are:
  - the unroled `OSError` of `build` (ADR-0086 decision 6);
  - the `CompilerRunError` with `timed_out` false and `returncode` `None`;
  - an unnamed `TypeError` from binding the call or from `Popen`;
  - what `build` still passes on from `subprocess`.
- Parts (ga), (da), (ra) and the size bound of (na) of sub-question 18; sub-questions 17 and 19.
- Any new value of `error.kind` or `condition`, any data-plane member, and any owner-only item (DRIVER §9: #5 A/B items, OD-3, OD-25, C-6).
- The round-7 wording minors of T-0248 unless this record edits the same lines anyway.

## Follow-ups

- (code, if the record names one) Give the pre-start `ValueError`s of `build` that cannot be told apart by class a `parameter`, as T-0267 did for `env`/`cwd`.
- (doc, after HQ-0027) The `local_run.run` side: `parameter` `"env"`/`"cwd"`, `path_role` `"cwd"`, the NUL and unencodable argument checks, and the timeout. Start from ADR-0088 as it lands.
- (possible HQ) If the record leaves a case open because only a new `error.kind` would place it, the driver records that question for the owner.

## Result
