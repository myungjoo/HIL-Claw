---
id: T-0035
title: Add the C gate (clang build of every tracked C source) to the CI workflow
phase: P0.5
status: IN_PROGRESS
commitMode: code
coversReq: ["#9", "CLAUDE.md language policy", "C-7", "#5 A-12"]
dependsOn: [T-0003, T-0010, T-0033]
touchesFiles: [.github/workflows/ci.yml]
estimatedSize: {loc: 25, files: 1}
hq: []   # clang is the C gate tool named by #9 and by the CLAUDE.md language policy and is already used by the Python gate's real-clang tests on the runner, so it is no new external dependency; no action, no package and no install step is added
---
## Why
CLAUDE.md's tool-layer language policy (#5 A-12) admits {Python, POSIX sh, C} and requires one CI gate per language, **built up front** (#9): Python = pytest + ruff, sh = shellcheck, C = clang build + harness pass. The Python gate (T-0003) and the sh gate (T-0010) are on `main`. PLAN P0.5-1 is still open for its C half. Since T-0033 (`470585a`) the tool layer holds its first C source, `hilclaw/harness/timing_driver.c`, so there is something to build.

**What #9 asks, and what this task takes of it.** #9 ("Scope update (A-12)") words the C gate as "`clang` build of the stand-in kernels + harness pass (correctness against the f64 reference)". Two parts of that sentence have nothing to act on today:
- No stand-in kernel is tracked in the repository. Kernels are the coder's output (third layer); the only C kernels so far are strings inside test files.
- The correctness half of the harness does not exist. PLAN P1-3 is marked "오너 확정 필요" for its f64 reference (#5 A-7) and its tolerance (#5 B-7).

This task is therefore the **clang-build slice of the C gate only**: one CI job that compiles every tracked C source of the repository with clang, warnings as errors. The "harness pass" half is **not** built and not redefined here.

**What the job adds beyond the Python gate** (the question left by T-0033 Follow-up (b) and T-0034 Follow-ups). The Python gate already builds and runs `timing_driver.c` with the runner's clang in the real-clang tests. It does so only for C files that some test happens to build, with flags that each test chooses, and its log does not show the compiler version. The new job:
1. compiles **every tracked `*.c` file**, whether or not a test builds it, from the first PR that adds it (as the sh gate does for `*.sh`);
2. is a check of its own, `C gate (clang)`, next to the other gates, so that a C diagnostic is not hidden inside a pytest failure;
3. prints `clang --version`, so that the toolchain of a run is in the log (T-0013 Result, Follow-up (a)).

Planner's judgement (DRIVER §6 and §9; the reviewer is asked to re-check it): what the job compiles and with which flags is fixed by no document. None of it is an owner-only item (#5 A / B items, C-6, OD-25, OD-3) or a registered OD; T-0010 treated the same kind of choice for shellcheck (dialect, severity, file selection) as provisional conventions of the task. The flags below are lint settings of the repository's **own tool-layer C sources**. They decide nothing about how a coder's kernel is built (ADR-0009 Boundaries "Build settings", OD-6 sub-question ②).

Why this item now (planner, 2026-10-07 UTC): P0.5-3 is BLOCKED on HQ-0003 (T-0014, unanswered on #5); the rest of P0.5-4 is the owner's hook registration, and the forbidden-command guard needs the owner's word on its tests (T-0007 Follow-ups). In P1, P1-3 and P1-4 wait for the owner (#5 A-7, B-7), P1-1 for OD-10 / OD-18 / OD-23, the rest of P1-8 for OD-17 / #8 M7. No open PR at planning time.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, test rules D12 — rule ⑤ in particular) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §9
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책" (last sentence: per-language CI gates), "브랜치·merge 절차" (CI workflows are code mode; BLOCKED reasons), "테스트 규칙" ⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks, in particular "can CI block bad code")
- PROCESS/PLAN.md — P0.5-1 (this task takes the clang-build slice of its C half), P1-3 (why the other half waits)
- Issue #9 (`gh issue view 9 --repo myungjoo/HIL-Claw --json body,comments`) — "Scope update (A-12)" (the C line) and "Revision (D10)"
- PROCESS/tasks/T-0010-ci-sh-gate-shellcheck.md — `## Acceptance Criteria` and `## Result` (the precedent this task imitates: job shape, `shell: bash` for `pipefail`, tracked-file selection, the one-time check in both directions, run evidence format)
- PROCESS/tasks/T-0033-timing-driver-c-source.md — `## Result`: "Flags the tests build with", "Optional syntax check", Follow-up (b)
- Existing files: `.github/workflows/ci.yml` (whole file, 86 lines), `hilclaw/harness/timing_driver.c` lines 1-45 (self-contained: its own `_POSIX_C_SOURCE`, C library and POSIX only), `.editorconfig` (2-space indent for `*.yml`), `.gitattributes` (LF)

## Acceptance Criteria
The choices below are **conventions chosen by this task, provisional**. State each with one line of reason in the commit body, the PR body and `## Result`. Do not present them as requirements.

### Workflow (`.github/workflows/ci.yml`; the only file this task changes on `main`)
- Add **one new job** next to the existing ones. Suggested id `c`, suggested name `C gate (clang)`. `runs-on: ubuntu-latest`, no matrix. The jobs `python`, `sh` and `test-presence`, the triggers, the top-level `permissions` and the `concurrency` block stay byte-for-byte unchanged.
- Steps:
  1. checkout — the same `actions/checkout` commit SHA, tag comment and `persist-credentials: false` as the other jobs (copy the lines; do not bump the action).
  2. one `run` step with `shell: bash` (so that the runner uses `-eo pipefail`, T-0010 Result) that prints `clang --version` and then compiles every **tracked** file matching `*.c`, anywhere in the tree, **each file alone, to an object file** (`-c`), with no link step.
- File selection: from git, NUL-separated, as the sh gate does (`git ls-files -z -- '*.c'`), so that untracked files are not compiled and odd file names are safe.
- Flags: `-std=c99 -Wall -Wextra -Wpedantic -Werror -O2`. Provisional reasons: these are the flags under which the tests of T-0033 already build `timing_driver.c` on the runner; `restrict` in the kernel prototype of ADR-0008 needs C99; `-O2` because some diagnostics need the optimiser's analysis. No `-D`, no `-I`, no `-fopenmp`, no `-march`.
- Compile, not `-fsyntax-only`: the gate is a "build" in #9's wording. No link, because a tool-layer C source need not be a whole program (`timing_driver.c` leaves `hilclaw_gemm` undefined by design).
- Nothing is written into the workspace: the object goes to `/dev/null` or to a directory under `$RUNNER_TEMP`.
- Empty file set: the step exits 0 when no tracked `*.c` file exists (GNU `xargs -r` runs nothing, or an explicit loop over an empty list).
- Failure: the step exits non-zero when clang reports an error or a warning in any tracked C source, and when `clang` is not on `PATH`. No `continue-on-error`, no `|| true`, no `-Wno-...`.
- Where clang comes from: the binary on the GitHub-hosted Ubuntu runner image, the one the real-clang tests of the Python gate already use (`ubuntu-latest`; T-0013, T-0033 and T-0034 ran there with no skip). Do **not** add an action, an `apt-get` step, an OpenMP runtime or anything in `pyproject.toml`. The version is the runner image's and is not pinned by the repository; record the version the first run printed in `## Result`.
- YAML follows `.editorconfig` (2-space indent, LF, final newline). No comments beyond the existing SHA-to-tag comment style.

### Tests
- No test file is added or changed. Tests that target a CI workflow are forbidden (CLAUDE.md test rule ⑤, DRIVER §5 rule ⑤, and the owner's global rule of the same content). No module in `hilclaw/` is touched, so rules ①-④ are vacuous.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and again before the merge, from the repository root: `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` all exit 0 (unchanged by this task; at `43491e3` on Windows: 3572 passed, 133 skipped; ruff 0.16.10, pytest 9.1.1). `git ls-files --eol .github/workflows/ci.yml` shows `i/lf`. The driver machine has no C compiler and none is to be installed; the PR's runs are the verification of the new job.
- The PR's first run (final workflow, `timing_driver.c` as the only tracked C source): `gh pr checks <PR> --watch` ends with **five** successful checks — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)` and the new job. Confirm from the new job's log that `clang --version` printed a version and that `hilclaw/harness/timing_driver.c` was compiled (quote the lines).
- If `timing_driver.c` itself draws a diagnostic in the new job, do **not** edit the C file and do not weaken the flags in this task: return BLOCKED ("requirement unclear") with the diagnostic, so that the planner decides between a fix of the source and other flags.
- One-time check that the gate works in both directions (dev-code-review: "can CI block bad code"), done **before** requesting the review, with temporary commits on the PR branch and never a force-push:
  1. Add a temporary tracked source (for example `tmp_t0035_check.c` at the repository root, LF) with a real diagnostic, for example a function with an unused parameter or an unused variable. Expect: the new job **fails** at the compile step and names that file; the other four checks stay green.
  2. Fix the source so that it is clean (keep the file). Expect: the new job **succeeds** — a second tracked file is found and a clean one passes.
  3. Delete the file. Expect: all five checks green. `git diff origin/main --stat` must then list only `.github/workflows/ci.yml`.
  The deliberate red run of step 1 does **not** count toward the "CI 3 consecutive failures" BLOCKED counter. The squash-merge keeps the temporary commits off `main`.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

### Process
- First the §3-5 landed check: `git log origin/main --grep='^Task: T-0035'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0035 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; an open PR touching `.github/workflows/ci.yml` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0035-ci-c-gate-clang-build` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0035`; executor commits end with the trailer `Task: T-0035`.
- Pushing a file under `.github/workflows/` needs the `workflow` scope on the `gh` / git token (present for T-0003, T-0010, T-0011). If the push is rejected for that reason, return BLOCKED and name the missing scope.
- After a failed CI run that is not the deliberate one, read the whole failed log (`gh run view <id> --log-failed`) before pushing again. Three consecutive failed runs: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; past the cap without a final Approve is BLOCKED). Ask the reviewer explicitly to (a) check that the job fails on a diagnostic, on a missing compiler and on a failing `git ls-files`, and passes on an empty file set; (b) re-check the planner's judgements in `## Why` — that the clang-build slice may be built before the harness half, that the flags are a convention of this task and no owner-only or OD matter, and that nothing here decides how a coder's kernel is built; (c) confirm that the other jobs are unchanged. If the reviewer reads (b) as a design choice needing an ADR or the owner, return BLOCKED with the exact question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0035`**. Delete the remote branch and the local branch in separate commands, only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: the provisional choices (job id and name, runner's clang, tracked `*.c` selection, one object per file and no link, the flags, empty-set behaviour) with one line of reason each; that the harness half is deferred and why; that no tool-layer language choice was needed (workflow YAML only).
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the CI runs with URLs (the three runs of the one-time check included), the clang version printed, the provisional choices, the local verification lines, and **your and the reviewer's reading on the PLAN P0.5-1 checkbox** (below).
- **PLAN checkbox.** The planner's reading: P0.5-1 **stays unchecked** when this task is DONE, because #9 words the other half of the C gate as correctness against the f64 reference, which waits for P1-3. The executor does not edit PLAN.md; say in `## Result` whether you and the reviewer agree, and the driver decides from that.
- Size: 1 file, about 15-25 added lines; far below 300 LOC / 5 files.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- The "harness pass" half of the C gate: correctness against a reference, the f64 oracle, tolerance (PLAN P1-3, P1-4; #5 A-7, B-7). Running `pytest` or any built program in the new job (the Python gate runs the real-clang tests).
- Tracking a stand-in kernel or any other new C file; any edit of `hilclaw/harness/timing_driver.c`, `hilclaw/`, `tests/` or `pyproject.toml`.
- Build settings of a coder's kernel (flags, language standard, `-march`, OpenMP runtime and thread count — ADR-0009 Boundaries, OD-6 sub-question ②); installing `libomp`; a real `-fopenmp` build.
- A macOS or WSL runner (C-7), pinning the clang version, a `.clang-format` / `clang-tidy` / sanitizer step, header files (`*.h`) as a selection of their own.
- Changing the other jobs, the triggers or the action SHAs; the coverage gate (P0.5-3); the merge guard registration (P0.5-4).
- Editing CLAUDE.md, the skills, the agents, README.md, DRIVER.md, PLAN.md, any ADR or the OD register.

## Follow-ups
- (P0.5-1 remainder) The "harness pass" half of the C gate, once the verification half of the harness (P1-3) exists; P0.5-1 is ticked then.
- (planner, next) Raise the owner questions of PLAN P1-3 as an HQ with a BLOCKED P1-3 task (precedent T-0014 / HQ-0003): the reference oracle of `cpu_standin` (#5 A-7 "still open"; NumPy float64 would also be a new external dependency) and the tolerance vocabulary (#5 B-7). After this task no P0.5 or P1 slice is left that needs neither the owner nor an OD closure.
- (planner, design-level, D6) OD-18 (exposure form of the FR-10 tools, before P1-1) and OD-17 with #8 M7 (before the runtime `STATE.json` of P1-8) are closable by an ADR task under DRIVER §9.
- (later, when the first tracked kernel or a deliberately non-conforming C fixture lands) Decide whether such files are compiled by this job with the same flags or selected apart.
- (owner, informational) The clang version follows the runner image and is not pinned, as shellcheck. From this merge on every PR and every push to `main` (driver state commits included) runs five jobs.
- (later, small) Use `timing_build.DRIVER_SOURCE` in `tests/harness/test_timing_driver.py` (T-0034 Follow-ups).

## Result
