---
id: T-0065
title: Add the "harness pass" half of the C gate to the CI workflow - the job `C gate (clang)` runs the three-state calibration of the gemm verification harness itself, and fails when it is skipped
phase: P0.5
status: IN_PROGRESS
commitMode: code
coversReq: ["#9", "CLAUDE.md language policy", "#5 A-12", FR-9, OD-16]
dependsOn: [T-0035, T-0060, T-0061, T-0062, T-0063]
touchesFiles: [.github/workflows/ci.yml]
estimatedSize: {loc: 30, files: 1}   # workflow lines only; no file under hilclaw/ or tests/ changes on main (one calibration kernel is changed and restored on the PR branch for the one-time check)
hq: []   # no owner-only item and no OD: ADR-0003 decision 6 and ADR-0017 Consequences leave the design of this gate to the P0.5-1 task; no new dependency (python, pytest and numpy are the pins the other jobs already install), no new action
---
## Why
PLAN P0.5-1 reads "sh 게이트(shellcheck) · C 게이트(clang 빌드 + 하네스 통과) CI 추가" and is the first unchecked item of the current phase (P0.5). Its sh half (T-0010) and the clang-build half of the C gate (T-0035, job `C gate (clang)`) are on `main`. **This task is the remaining half, "harness pass", and ticks P0.5-1.**

What the sources say:
- #9, "Scope update (A-12)": "C: `clang` build of the stand-in kernels + harness pass (correctness against the f64 reference)"; "one gate per language, built up front".
- ADR-0003 (decision 6, line 80): "A skipped calibration test is no evidence. Calibration is a candidate content of the C gate of PLAN P0.5-1 ("clang build + harness pass"); the workflow is designed there."
- ADR-0017 Consequences: "**C gate** (PLAN P0.5-1): the "harness pass" half has a run to use; the gate is designed there."
- T-0035 deferred this half until the verification half of the harness existed. It exists since T-0059 to T-0062 (`hilclaw/harness/verification_program.c`, `verification_arrays.py`, `verification.py`, `verification_build.py`), and T-0063 added the three calibration kernels `tests/harness/calibration/gemm_{conforming,failing,violating}.c` with `tests/harness/test_calibration.py`.

The question the two previous planners left open (T-0064 `## Follow-ups`, journal 2026-10-08): since T-0063 the two `Python gate` jobs and the coverage job already build the calibration kernels with the runner's clang and run the harness against the float64 reference; neither #9 nor the PLAN says whether that already is the gate, or what "stand-in kernels" names while no kernel but the calibration fixtures is tracked.

Planner's judgements (2026-10-08 UTC; the reviewer is asked to re-check each):
- **This is no owner-only item and no OD** (DRIVER §9: #5 A / B items, C-6, OD-25, OD-3). Both records hand the design of the gate to this PLAN item ("the workflow is designed there", "the gate is designed there"). T-0010, T-0011 and T-0035 treated the same kind of choice (what a gate job selects and runs) as provisional conventions of the task.
- **The C gate job runs the harness itself.** #9 words the C gate as two parts of one gate, and the PLAN item as "C 게이트(clang 빌드 + 하네스 통과)". With this task the gate is met under both readings of the open question: under "the Python gates already meet it" nothing is lost but about a minute of runner time; under "the C gate must do it" it is now done. A change of C sources then has one check, by name, that says both "builds without a diagnostic" and "the harness gives the right verdicts", which is what the merge guard and a reader of the checks see.
- **Content of the harness pass: the three-state calibration** (`tests/harness/test_calibration.py`, six cases). It is what ADR-0003 names as the candidate content, and it is stronger than "a conforming kernel passes": it also shows that the harness fails a wrong kernel and a kernel that is right on known inputs only.
- **"Stand-in kernels"** is read as: the C sources the repository tracks. Kernels of a run are the coder's output (layer 3) and live in the data plane, never in this repository; the only tracked gemm kernels are the three calibration fixtures. The build half already compiles every tracked `*.c`.
- **A skip must fail the gate.** "A skipped calibration test is no evidence" (ADR-0003). `test_calibration.py` already fails instead of skipping when clang is missing on a CI runner; the new step must also fail when any selected case is reported as skipped or when no case is selected.
- **No ARCHITECTURE file, no OD row and no ADR is edited.** The workflow is the only file.

If the reviewer reads one of these as needing a record or the owner, do not decide it: return BLOCKED ("requirement unclear") with the exact question (suggested wording: "Is the "harness pass" half of the C gate of #9 met by the Python gates that run the calibration since T-0063, or must the job `C gate (clang)` run it; and which sources does "stand-in kernels" name?").

Why this item now: no lock, no unresolved HQ, no TODO / INTERRUPTED task file and no open PR at planning time (2026-10-08T09:18Z, `main` at `a8386a0`). The other open item of P0.5 is the owner's hook registration (P0.5-4), which the driver may not do (DRIVER §1-5).

A-13 check (planner's reading): code mode (CI workflow). No new external dependency: `actions/setup-python` at the pinned SHA, `pytest==9.1.1` and `numpy==2.4.6` are already used by the `python` and `coverage` jobs. No data-plane schema. No security-relevant change: `permissions: contents: read` and `persist-credentials: false` stay.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (never touch `PROCESS/STATE.json`), §3 "BLOCKED 사유" paragraph
- `.github/workflows/ci.yml` (185 lines, all of it): the job `c` (lines 61-73) and, as the model to copy, the steps `Set up Python`, `Install dev tools` and `Install runtime dependencies` of the job `coverage` (lines 114-125)
- `tests/harness/test_calibration.py` (all of it; the `executables` fixture: the POSIX skip, the clang skip that is a failure under `GITHUB_ACTIONS`) and `tests/harness/calibration/gemm_conforming.c`
- `pyproject.toml` (pins; `[tool.pytest.ini_options]`: `testpaths`, `pythonpath`)
- ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md - decision 6 (the lines around "A skipped calibration test is no evidence"); ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md - Consequences (the "C gate" sentence)
- Issue #9 (`gh issue view 9 --repo myungjoo/HIL-Claw --json body,comments`): the "Scope update (A-12)" and the "Revision (D10)" comments
- PROCESS/tasks/T-0035-ci-c-gate-clang-build.md - `## Acceptance Criteria` (the conventions of the workflow: first-party actions pinned by full commit SHA, explicit `shell: bash`, the one-time red / green check with temporary commits and no force push) and `## Result` (the evidence format); PROCESS/tasks/T-0063-gemm-three-state-calibration.md `## Result` (what the six cases show; run time)
- CLAUDE.md - 상시 규칙: "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ⑤ (no tests for CI workflows), "코멘트 최소화"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks, "can CI block bad code")
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6053035869 (the last one at planning time). If the owner has said something about the C gate, #9 or P0.5-1 there, follow it and say so in `## Result`; if it contradicts this task, return BLOCKED quoting the comment

## Acceptance Criteria
Names of steps, the Python version of the job and the means of the skip check are **this task's choices, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`.

### The change (`.github/workflows/ci.yml`, job `c` only)
- The job keeps its id `c`, its name **`C gate (clang)`** (the merge guard and earlier task files know the check by that name), `runs-on: ubuntu-latest`, its checkout step and its `clang build` step unchanged and first.
- After `clang build`, added steps:
  1. Python set up with the same `actions/setup-python` commit SHA and tag comment as the other jobs (copied, not bumped); one version (recommended `"3.14"`, as the `coverage` job).
  2. `Install dev tools` and `Install runtime dependencies`, copied from the `coverage` job without change (the pins of `pyproject.toml`; `--only-binary=:all:`). Nothing else is installed; no `apt`, no further action.
  3. A step (suggested name `harness pass`, `shell: bash`) that runs `python -m pytest tests/harness/test_calibration.py` from the repository root and **fails** when: a case fails or errors; any selected case is skipped; no case is collected or the file is missing (pytest's own exit status covers the last two - confirm it). The skip check is inline shell or an inline `python -c` / heredoc over what pytest reports (for example `-rs` with the summary line, or a `--junitxml` file under `$RUNNER_TEMP`); no script file is added to the tree and no pytest plugin is installed. The log shows the pytest summary line.
- The step writes nothing into the checkout that a later step reads, and the job needs no new permission.
- The other four jobs (`python`, `sh`, `test-presence`, `coverage`), the triggers, `permissions` and `concurrency` are byte-for-byte unchanged. The Python gates keep running the whole suite, the calibration included: no test is removed from them, deselected or marked.
- LF line endings; YAML valid (GitHub accepts the workflow: the PR run starts and shows six checks).
- No comment lines beyond what the file's style already has (CLAUDE.md "코멘트 최소화"); the reasons go to the commit body.

### Cases (covered by the one-time check below and by reading, not by tests - test rule ⑤)
- happy: on the real tree the job is green and its log shows six passed, none skipped.
- error: a conforming kernel that computes a wrong product makes the job red at the new step.
- branch / negative, by reading and stated in the PR body: a skipped case fails the step; a missing test file or zero collected cases fails the step; a missing clang fails already at `clang build`; a failed install fails the job before the harness runs.

### One-time check that the gate works in both directions (before requesting the review; temporary commits on the PR branch, never a force push; each its own CI run)
1. Temporary commit: change `tests/harness/calibration/gemm_conforming.c` so that it still compiles without a diagnostic under the flags of the `clang build` step but returns a wrong product (for example one element of `c` off by 1.0f). Expect: `C gate (clang)` **fails at the new step**, with `clang build` successful; the two `Python gate` jobs and `Coverage gate (hilclaw)` fail too, because they run the same test - that is expected and deliberate. Record the run URL and the failing lines.
2. A second commit restores the file exactly (`git diff origin/main -- tests/` is empty afterwards). Expect: all six checks green.
- The deliberate red run of step 1 does **not** count toward the "CI 3 consecutive failures" BLOCKED counter. The squash-merge keeps the temporary commits off `main`.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit: `python -m ruff check .` and `python -m ruff format --check .` exit 0; `python -m pytest` unchanged in pass and skip counts (6195 passed, 266 skipped on the driver's Windows clone at `ec29b82`, where the real-clang tests skip). Install nothing.
- `git diff origin/main --stat` before the merge lists **only** `.github/workflows/ci.yml`; `git ls-files --eol -- .github/workflows/ci.yml` shows `i/lf`.
- CI on the final head: `gh pr checks <PR> --watch` ends with **all six checks successful** - `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`, `Coverage gate (hilclaw)`. Record the run URL, the pytest summary line of the new step and the duration of the `C gate (clang)` job before (about the T-0064 run https://github.com/myungjoo/HIL-Claw/actions/runs/37753770000) and after.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0065'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0065 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; an open PR that touches `.github/workflows/ci.yml` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0065-ci-c-gate-harness-pass` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0065`; executor commits end with the trailer `Task: T-0065`.
- No test is added (CLAUDE.md test rule ⑤: CI workflows are not a test target). No file under `hilclaw/` changes, so rules ① to ④ have nothing to act on; no tool-layer language choice is needed (workflow YAML with inline bash) - say so in `## Result`.
- After a failed CI run that is not the deliberate one, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed runs: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; past the cap without a final Approve, return BLOCKED). Ask the reviewer explicitly to (a) confirm from the run of step 1 that the job blocks a wrong kernel at the new step, and by reading that a skip, zero collected cases and a missing file fail it; (b) re-check each planner's judgement in `## Why` - no owner-only item or OD, the C gate job runs the harness itself, the calibration as its content, the reading of "stand-in kernels" - and say whether **PLAN P0.5-1 is complete with this task**; (c) confirm that the other jobs, triggers, `permissions`, `concurrency` and the action pins are unchanged and that nothing new is installed; (d) re-check the A-13 reading. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED - do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm that every check of the final head is successful, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0065`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: what changed in one paragraph; the provisional choices with one line of reason each (step names, Python version, the means of the skip check, the calibration as the content); the reading of #9 taken; that no test was added and why.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** - the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. **Do not put a fenced code block into `## Result`** (a Python block there turned `main` red after T-0063: `ruff format --check .` reads Markdown); use inline code. Record: PR and commit, branch commits, review rounds and findings, the run URLs of the deliberate red run and of the final green run with the lines that show them, the provisional choices, the job duration before and after, the push run on `main`, and **whether executor and reviewer read P0.5-1 as complete** (the driver ticks the checkbox on that).
- Size: about 30 workflow lines in 1 file; the cap is 300 LOC / 5 files.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any change under `hilclaw/` or `tests/` that reaches `main`; a new calibration kernel, shape, dtype or tolerance; a stand-in kernel tracked in this repository; a helper script or a new top-level directory.
- Removing, deselecting or moving tests of the Python gates or of the coverage job; a pytest marker or plugin; a change of the flags or of the selection of the `clang build` step (T-0035 follow-up: whether deliberately non-conforming C fixtures are selected apart).
- A timing run, a profile or any performance threshold in CI; sanitizers; other compilers; other runners or operating systems.
- Excluding `PROCESS/` Markdown from `ruff format --check .` (T-0064 follow-up; a task of its own).
- Any edit of an ADR, the OD register, StandardScenarios, issue #9, CLAUDE.md (its "CI 미구축" notes), DRIVER.md, PLAN.md, `.claude/`, `README.md`, `pyproject.toml`.
- The merge guard hook registration (P0.5-4, the owner's) and the D15 migration.

## Follow-ups
- (driver, at wrap-up) Tick PLAN P0.5-1 if executor and reviewer read it as complete. P0.5 then holds only the owner's hook registration of P0.5-4: judge the phase transition to P1 under DRIVER §6 (that item carried over).
- (planner, next) The first HW tool contract of P1-1 hangs on OD-18 sub-question ⑦ (which HW tools `cpu_standin` offers - a §9 record, or an HQ if it needs the owner's reading of #5 A-7) and on sub-question ⑥ (where a run states its hw_profile - a §9 record next to `instance.json`, PLAN P1-8, so that `hw_tool.tool_function` gets a real reader).
- (a small code task) Whether `PROCESS/` Markdown leaves the set of `ruff format --check .`; public names for `journaled_tool._built` and `backends._hw_tool` (T-0064 `## Result`).
- (integrator, document mode) The "CI 미구축" notes of CLAUDE.md and the skills, once the gates of #9 are all on `main`.

## Result
