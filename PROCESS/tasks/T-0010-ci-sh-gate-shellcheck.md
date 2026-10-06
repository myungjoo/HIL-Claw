---
id: T-0010
title: Add the sh gate (shellcheck) to the CI workflow
phase: P0.5
status: IN_PROGRESS
commitMode: code
coversReq: ["#9", "CLAUDE.md language policy", "C-7"]
dependsOn: [T-0003]
touchesFiles: [.github/workflows/ci.yml]
estimatedSize: {loc: 20, files: 1}
hq: []   # shellcheck is the sh gate named by #9 ("Scope update (A-12)") and by the CLAUDE.md language policy, so it is not a "new external dependency"; the task uses the binary that ships on the GitHub-hosted Ubuntu runner and adds no action and no Python package (see Acceptance Criteria)
---
## Why
CLAUDE.md's tool-layer language policy (#5 A-12) admits {Python, POSIX sh, C} and requires one CI gate per language, **built up front** (#9): Python = pytest + ruff, sh = shellcheck, C = clang build + harness pass. The Python gate has been on `main` since T-0003 (`17d3dee`). PLAN P0.5-1 asks for the other two.

This task is the **first slice of P0.5-1: the sh gate only**. The C gate is not planned here because its dependencies are not met: #9 defines it as "clang build of the stand-in kernels + harness pass (correctness against the f64 reference)", and neither the stand-in kernels (P1-2) nor the harness (P1-3) exist. Choosing compile flags and a build layout for C code that does not exist would be inventing an undecided item.

The repository contains **no shell script today** (`git ls-files '*.sh'` is empty). The gate is still worth building now: the next sh file (hook entry points and glue scripts, per #9) is then linted from its first PR on, and the merge guard hook (`hilclaw/merge_guard.py`, T-0007) sees the check on every PR. The gate must therefore pass on an empty file set and fail as soon as a tracked script has a finding.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, test rules D12 — rule ⑤ in particular) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책" (the set {Python, POSIX sh, C}; last sentence: per-language CI gates), "브랜치·merge 절차" (code mode: CI workflows are code mode; BLOCKED reasons incl. "새 외부 의존성"), "테스트 규칙" ⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; steps 9, 10-12, 13, 14, 15. .claude/skills/dev-code-review/SKILL.md — what the reviewer checks (in particular "can CI block bad code")
- PROCESS/PLAN.md — P0.5-1 (this task takes the shellcheck half), P0.5-2 / P0.5-3 (left to later tasks)
- Issue #9 (`gh issue view 9 --repo myungjoo/HIL-Claw --json body,comments`) — "Scope update (A-12)" (the sh line: "`shellcheck` (hook entry points and glue scripts; logic is tested through the Python integration tests that call them)") and "Revision (D10)"
- PROCESS/tasks/T-0003-ci-skeleton.md — `## Acceptance Criteria` (the conventions of the workflow: first-party actions only, pinned by full commit SHA, least privilege, the one-time negative check) and `## Result` (provisional choices, run evidence format)
- Existing files: `.github/workflows/ci.yml` (whole file, 41 lines), `.editorconfig` (2-space indent for `*.yml`), `.gitattributes` (LF)

## Acceptance Criteria
Nothing in the repository or the issues fixes how shellcheck is obtained, which files it scans, which shell dialect it assumes or which severity fails the gate. None of these is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below and state each choice with one line of reason in the commit body, the PR body and `## Result`. Do not present them as requirements.

Workflow (`.github/workflows/ci.yml`; the only file this task changes on `main`):
- Add **one new job** next to the existing `python` job. Suggested id `sh`, suggested name `sh gate (shellcheck)`. `runs-on: ubuntu-latest`, no matrix. The `python` job, the triggers, the top-level `permissions` and the `concurrency` block stay byte-for-byte unchanged.
- Steps:
  1. checkout — the same `actions/checkout` commit SHA and the same `persist-credentials: false` as the `python` job (copy the existing `uses:` line and its tag comment; do not bump the action in this task).
  2. one `run` step that prints `shellcheck --version` (so that the version used is in the log) and then runs shellcheck over every **tracked** file matching `*.sh`, anywhere in the tree. Take the list from git, NUL-separated, so that untracked files are not scanned and odd file names are safe, for example `git ls-files -z -- '*.sh' | xargs -0 -r shellcheck --shell=sh`.
- Empty file set: the step must exit 0 when no tracked `*.sh` file exists (today's state). With GNU `xargs -r` nothing is run in that case. Printing one line such as `no tracked *.sh files` is allowed, not required.
- Failure: the step must exit non-zero when shellcheck reports a finding in any tracked script. Keep shellcheck's **default severity** (every finding fails, style included) and add no `--exclude`, no `.shellcheckrc` and no `continue-on-error`.
- Dialect: pass `--shell=sh`. Provisional reason: the language policy admits POSIX sh, not bash, so a bash-only construct is flagged regardless of the script's shebang.
- Where shellcheck comes from: the binary preinstalled on the GitHub-hosted Ubuntu runner image. Do **not** add a third-party action (for example `ludeeus/action-shellcheck`), a Python wrapper package (for example `shellcheck-py`), a download step or anything in `pyproject.toml`. If the first run shows that `shellcheck` is not on the runner's `PATH`, installing the same tool from the runner's Ubuntu archive in the job (`sudo apt-get install -y shellcheck`) is acceptable; record that in `## Result`. If neither works, return BLOCKED ("new external dependency") with the exact question for the owner.
- The shellcheck version is therefore the runner image's, not pinned by this repository — unlike ruff and pytest (HQ-0002: exact pins). Record the version the first run printed in `## Result` and keep the Follow-ups entry about it.
- YAML follows `.editorconfig` (2-space indent, LF, final newline). No comments beyond the existing SHA-to-tag comment style (CLAUDE.md "코멘트 최소화").

Tests:
- No test file is added or changed. Tests that target a CI workflow are forbidden (CLAUDE.md test rule ⑤, DRIVER §5 rule ⑤, and the owner's global rule of the same content). No module in `hilclaw/` is touched, so rules ①-④ are vacuous.

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` all exit 0 (unchanged by this task; 468 tests at `02b2d22`). `git ls-files --eol .github/workflows/ci.yml` shows `i/lf`. shellcheck is not installed on the driver machine and is **not** to be installed there; the PR's runs are the verification of the new job.
- The PR's first run (final workflow, no script in the tree): `gh pr checks <PR> --watch` ends with **three** successful checks — `Python gate (3.11)`, `Python gate (3.14)` and the new job. Confirm from the new job's log that `shellcheck --version` printed a version.
- One-time check that the gate works in both directions (dev-code-review: "can CI block bad code"), done **before** requesting the review, with temporary commits on the PR branch and never a force-push:
  1. Add a temporary tracked script (for example `tmp_t0010_check.sh` at the repository root, LF, `#!/bin/sh`) containing a real finding, e.g. an unquoted expansion `echo $1` (SC2086) or a bash-only `[[ ... ]]` (SC3010). Expect: the new job **fails** at the shellcheck step; both Python entries stay green.
  2. Fix the script so that it is clean (keep the file). Expect: the new job **succeeds** — this shows that tracked scripts are really found and that a clean one passes.
  3. Delete the script. Expect: all three checks green on the empty file set. `git diff origin/main --stat` must then list only `.github/workflows/ci.yml`.
  The deliberate red run of step 1 does **not** count toward the "CI 3 consecutive failures" BLOCKED counter. The squash-merge removes the temporary commits from `main`.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Code mode: branch `claude/T-0010-ci-sh-gate-shellcheck`, Draft PR with the `DONOTMERGE` label, reviewer cycle, squash-merge per CLAUDE.md A-13 with `Task: T-0010` as the last line of the PR body (`gh pr merge --squash --body`). PR title contains `T-0010`.
- CI exists now: dev-item-address step 13 is the real check result of the PR (`gh pr checks`, `gh api` for logs), not the local rerun. Merge only when every check of the final head is successful.
- Commit body: the provisional choices (job id and name, preinstalled binary, tracked `*.sh` selection, `--shell=sh`, default severity, empty-set behaviour) with one line of reason each; that the C gate is deferred and why; that no tool-layer language choice was needed (workflow YAML only).
- Pushing a file under `.github/workflows/` needs the `workflow` scope on the `gh`/git token (present for T-0003). If the push is rejected for that reason, return BLOCKED and name the missing scope.
- Size: 1 file, about 15-20 added lines; far below 300 LOC / 5 files.
- PLAN checkbox: **P0.5-1 stays unchecked** when this task is DONE — the C gate half remains. The driver's wrap-up ticks nothing for this task.

## Out of Scope
- The C gate (clang build + harness pass): waits for the stand-in kernels (P1-2) and the harness (P1-3). No `*.c` handling, no compile flags, no build layout in this task.
- Test-existence check (P0.5-2) and coverage gate (P0.5-3).
- Adding any real shell script, a `.shellcheckrc`, an `.editorconfig` section for `*.sh`, or a rule that sh files must carry a particular shebang or extension.
- Scanning extensionless scripts by shebang (see Follow-ups).
- Changing the `python` job, the triggers, the action SHAs, `pyproject.toml`, `hilclaw/` or `tests/`.
- Editing CLAUDE.md, the skills, README.md, DRIVER.md, PLAN.md or `.claude/settings.json` (the "CI 미구축" notes are a separate document-mode change, already listed in T-0003 Follow-ups).

## Follow-ups
- (P0.5-1 remainder) C gate, once P1-2 (`cpu_standin`, clang build wrapper) and P1-3 (harness) provide something to build and run; P0.5-1 is ticked then.
- (planner, next) P0.5-2 test-existence check: a stdlib-only check needs no new dependency. Open point for that task: where a CI check script lives — inside `hilclaw/` test rule ④ would demand a test file that rule ⑤ forbids, so a location outside the package (or an inline workflow step) is the likely choice.
- (planner, P0.5-3) The coverage gate needs a measurement tool. `coverage` / `pytest-cov` would be a new external dependency (BLOCKED reason, CLAUDE.md A-13) unless the owner sanctions it; D12 fixes the thresholds but names no tool. Expect an HQ or a stdlib-only design (`sys.monitoring` / `trace`) when that task is planned.
- (later, when the first sh file lands) Decide whether hook entry points may be extensionless; if so, extend the file selection (for example by shebang). Add an `.editorconfig` section for `*.sh`.
- (owner, informational) The shellcheck version follows the runner image and is not pinned, unlike ruff / pytest. If a runner image update turns the gate red on unchanged scripts, a pinning task (and the choice of how to pin without a third-party action) is due.
- (integrator, document mode — unchanged from T-0003) Update the "CI 미구축" notes in CLAUDE.md, dev-item-address step 13, dev-code-review and README.md line 60.

## Result
