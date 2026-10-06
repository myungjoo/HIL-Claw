---
id: T-0003
title: Add the CI skeleton with the Python gate (pytest + ruff)
phase: P0
status: IN_PROGRESS
commitMode: code
coversReq: ["#9", "#5 D10", "CLAUDE.md language policy"]
dependsOn: [T-0001, T-0002, T-0009]
touchesFiles: [.github/workflows/ci.yml]
estimatedSize: {loc: 45, files: 1}
hq: []   # HQ-0001 resolved 2026-10-06 (option a, D13); HQ-0002 resolved 2026-10-06 (option c): the fix lands first as T-0009, hence `dependsOn`. GitHub Actions on a Linux runner with pytest + ruff is named by #9, PLAN P0-3 and D10, so it is not a "new external dependency"; only first-party `actions/*` actions are allowed (see Acceptance Criteria)
---
## Why
The standard development process (dev-item-address steps 13-15, CLAUDE.md A-13) assumes CI: a code-mode PR is merged only when the reviewer approved **and** CI is green. Until now that step has been replaced by a local test rerun ("CI 미구축"). Issue #9 asks for one CI gate per tool-layer language, built up front, on a Linux runner; PLAN P0-3 takes the first slice: the Python gate (pytest + ruff) on pull requests and on pushes to `main`. T-0002 made both tools runnable with one command each, so this task only has to call them from a workflow. It also closes the T-0002 follow-ups addressed to P0-3: run on the lowest supported Python (3.11), and install the `[dependency-groups]` dev tools with a pip that understands PEP 735.

Owner decision D10 (2026-10-05) fixes that there is **no required status check / branch protection**: the gate is procedural (the executor reads the check result before merging) and will later be harness-enforced by the merge-guard hook (P0.5-4).

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming, resume rule, 2h30m limit) and §5 (task format, size limit, test rules D12 — rule 5 in particular); §3 "BLOCKED 사유" paragraph; §11 row D10
- CLAUDE.md — 상시 규칙: "브랜치·merge 절차" (code mode: CI workflows are code mode), "테스트 규칙" ⑤, "코멘트 최소화", "도구 계층 언어 정책" (last sentence: per-language CI gates); "현재 프로젝트 상태 주의사항: CI 미구축"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; steps 9, 13, 14, 15 (lines 31-45) for PR / CI handling
- .claude/skills/dev-code-review/SKILL.md — line 15 (the reviewer checks that CI can block bad code)
- PROCESS/PLAN.md — P0-3, and P0.5-1 / P0.5-2 / P0.5-3 / P0.5-4 (deliberately left to later items)
- PROCESS/tasks/T-0002-python-project-config.md — `## Acceptance Criteria` "Local verification" (the three commands) and `## Result` follow-ups marked (P0-3)
- Issue #9 (`gh issue view 9 --repo myungjoo/HIL-Claw --json body,comments`) — body, "Scope update (A-12)" and "Revision (D10)" comments
- Existing files: `pyproject.toml` (whole file, 17 lines), `tests/test_version.py`, `.gitattributes`, `.editorconfig` (2-space indent for `*.yml`), `.claude/settings.json` (allowlist)

## Acceptance Criteria
Nothing in the repository or the issues fixes the workflow file name, the action versions, the Python versions beyond the 3.11 floor, or the install command. None of these is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below and state each choice with one line of reason in the commit body and in `## Result`. Do not present them as requirements.

Workflow file (new, `.github/workflows/ci.yml`; the only file this task adds or changes):
- Triggers: `pull_request` (all branches) and `push` to `main` only. No `schedule`, no `workflow_dispatch`, no path filters (D10: "CI runs on every PR and on pushes to main").
- One job (the "Python gate"), `runs-on` a GitHub-hosted Ubuntu runner (`ubuntu-latest`, or a fixed `ubuntu-NN.04` label if you give a reason).
- Matrix over two Python versions with `fail-fast: false`: `"3.11"` (the `requires-python` floor) and the newest stable CPython available to `actions/setup-python` at execution time (planner's expectation: `"3.14"`, the version T-0002 was verified on). Quote the versions as strings.
- Steps, in this order, each a separate step so that the failing gate is visible by name:
  1. checkout
  2. set up Python (matrix version)
  3. install the dev tools from the declaration in `pyproject.toml`, not from a duplicated list: upgrade pip to a version that supports dependency groups (>= 25.1), then `python -m pip install --group dev`. Do not install the project itself (there is no build backend).
  4. `python -m ruff check .`
  5. `python -m ruff format --check .`
  6. `python -m pytest`
- Least privilege: top-level `permissions: contents: read`. No secrets, no `pull_request_target`, no caching, no artifact upload.
- A `concurrency` group that cancels superseded runs of the same PR is allowed (optional); it must not cancel runs on `main`.
- Actions policy (this is how the task stays clear of the "new external dependency" BLOCKED reason):
  - Only GitHub's own first-party actions are used: `actions/checkout` and `actions/setup-python`. They are part of the GitHub Actions platform that #9 and PLAN P0-3 already sanction.
  - Reference each by **full commit SHA** with the release tag in a trailing comment (e.g. `uses: actions/checkout@<40-hex> # v7.0.1`). Resolve the latest release and its commit at execution time with `gh api repos/actions/<name>/releases/latest` and `gh api repos/actions/<name>/git/ref/tags/<tag>` (dereference an annotated tag if needed). At planning time (2026-10-06) the latest releases were `actions/checkout` v7.0.1 and `actions/setup-python` v7.0.0.
  - If the workflow cannot be written without an action outside `actions/*` (for example `astral-sh/setup-uv`) or without a new tool beyond pytest and ruff, do **not** add it: return BLOCKED with reason "new external dependency" and the exact question for the owner.
- YAML follows `.editorconfig` (2-space indent, LF, final newline). Comments only where the code cannot say it (CLAUDE.md "코멘트 최소화"); the SHA-to-tag comments are the expected exception.

Tests:
- No test file is added or changed. Tests that target a CI workflow are forbidden (CLAUDE.md test rule ⑤, DRIVER §5 rule 5), and this task touches no module in `hilclaw/` (rules ①-④ are vacuous).

Verification (record the summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root — the same commands the workflow runs: `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .` all exit 0. `git ls-files --eol .github/workflows/ci.yml` shows `i/lf`.
- The PR's own run is the first real execution of the workflow: after pushing the branch and opening the Draft PR, `gh pr checks <PR> --watch` must end with **every matrix entry successful** (2 checks). This replaces the "local rerun" substitute of dev-item-address step 13 from this PR on. Confirm from the job log (`gh api repos/myungjoo/HIL-Claw/actions/runs/<id>/jobs`, then the job's `/logs`) that pytest collected the tests in `tests/` (currently 2) and that the 3.11 entry really ran on 3.11.
- Negative check — "can CI block bad code" (dev-code-review line 15), done **once**: push one temporary commit to the PR branch that makes `tests/test_version.py` fail (or introduces a ruff error), confirm with `gh pr checks` that the checks go red at the expected step, then push a second commit that restores the file byte-for-byte (`git diff origin/main -- tests/` must be empty afterwards). Never force-push; the squash-merge removes both commits from `main`. This deliberate red run does **not** count toward the "CI 3 consecutive failures" BLOCKED counter. Do it before requesting the review so the reviewer sees the final diff (one file).
- After the squash-merge, the `push` trigger fires on `main` for the first time: check that run with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary so that the next iteration plans a fix task.

Process:
- Code mode: branch `claude/T-0003-ci-skeleton`, Draft PR with the `DONOTMERGE` label, reviewer cycle, squash-merge per CLAUDE.md A-13 with `Task: T-0003` as the last line of the PR body (`gh pr merge --squash --body`). PR title contains `T-0003`.
- Commit body: the provisional choices (file name, runner label, the two Python versions, pip `--group` install path, SHA pinning of first-party actions) with one line of reason each; that no tool-layer language choice was needed (workflow YAML only).
- Allowlist notes (`.claude/settings.json`; do not edit it): `Edit(.github/**)` covers the workflow file. `gh run *` is **not** allowlisted — use `gh pr checks` (covered by `gh pr *`) and `gh api` instead. `git revert` is not allowlisted — restore the temporarily broken file with a normal edit + commit. `python -m pip ...` is covered by `python *`. If any needed call is denied in a non-interactive session, return BLOCKED rather than working around it through another shell command.
- Pushing a file under `.github/workflows/` requires the `workflow` scope on the `gh`/git token (present on the planning machine, 2026-10-06). If the push is rejected for that reason, return BLOCKED and name the missing scope.
- Size stays within 300 LOC / 5 files; expected 1 file, about 45 lines.

## Out of Scope
- Required status checks, branch protection, rulesets (D10: none). The `gh pr merge` guard hook (P0.5-4).
- shellcheck and clang gates (P0.5-1). Test-existence check (P0.5-2). Coverage measurement / `pytest-cov` / the 80% gate (P0.5-3).
- A CI-side line-ending (LF) check: `.gitattributes` already enforces LF and PLAN P0-3 lists only the Python gate.
- Changing `pyproject.toml` (dev-tool lower bounds, pins, a lock file, a build backend), `tests/`, or `hilclaw/`.
- Third-party actions, uv, dependency caching, artifact upload, badges, README changes (P0-5).
- Editing CLAUDE.md or the skills to remove the "CI 미구축" notes (document mode, a separate change — see Follow-ups). Editing `.claude/settings.json` (denied by D11).

## Follow-ups
- (integrator / doc mode, right after this lands) CLAUDE.md "현재 프로젝트 상태 주의사항: CI 미구축", dev-item-address step 13 note (line 40-41) and dev-code-review line 15 still describe CI as not built; update them once this workflow is on `main`.
- (owner, optional) `.claude/settings.json` has no `Bash(gh run *)` entry; `gh pr checks` + `gh api` suffice, but `gh run view --log-failed` would make CI failure analysis (dev-item-address step 13) simpler.
- (owner, informational) The repository is private, so Actions minutes are metered. Every driver iteration pushes at least two state commits to `main` (DRIVER §4) and each triggers a 2-entry run; if consumption becomes a concern, a `paths-ignore` for `PROCESS/**` on the `push` trigger would deviate from D10's "every push" wording and needs an owner decision.
- (P0.5-1 / P0.5-2 / P0.5-3) Add the further gates as additional steps or jobs of this same workflow file.
- (P0.5-4) The merge-guard hook should treat "no checks reported" as not-successful, now that every PR has checks.
- (later) Decide the dev-tool pin / lock policy (T-0002 reviewer N1) once CI reproducibility becomes an observed problem; `actions/*` SHA pins need periodic refresh (no Dependabot configured).

## Result
- 2026-10-05T18:22Z AKIHA:f2cf66cc — BLOCKED (`permission-denied`, HQ-0001). No implementation was started: no branch, no PR, no workflow file.
- The driver session (scheduled routine, auto permission mode) was denied when spawning the executor sub-agent; the classifier's reason was `[Self-Approval]` — the executor's brief covers implementing, getting its own reviewer sub-agent's Approve and squash-merging without a human. Per DRIVER §1-5 a denied call is treated as BLOCKED and is not worked around.
- The task specification above is unchanged and still valid; once HQ-0001 is answered the task returns to TODO.
- 2026-10-06T04:21Z AKIHA:15cc61e7 — resumed after HQ-0001 was answered (option a, D13); the executor spawn was not denied. BLOCKED again (HQ-0002: the first CI run is red because of code already on `main`, and every fix lies outside this task's single allowed file). Not merged.
- PR: #16 https://github.com/myungjoo/HIL-Claw/pull/16 — open, Draft, label `DONOTMERGE`, one file (`.github/workflows/ci.yml`, 39 lines), branch `claude/T-0003-ci-skeleton` at `bab9305` (remote branch kept for resume). No squash commit.
- Review rounds: 0 (the reviewer cycle was not started; the PR never reached a green CI). Negative check: not performed.
- Local verification before the commit (ruff 0.15.14, pytest 9.0.3, Python 3.14.4): `python -m pytest` -> `97 passed in 0.17s`; `python -m ruff check .` -> `All checks passed!`; `python -m ruff format --check .` -> `4 files already formatted`; `git ls-files --eol .github/workflows/ci.yml` -> `i/lf w/lf attr/text=auto eol=lf`.
- First workflow run (pull_request, `bab9305`): https://github.com/myungjoo/HIL-Claw/actions/runs/37413101512 — conclusion `failure`, both matrix entries (`Python gate (3.11)`, `Python gate (3.14)`).
  - Steps: Check out / Set up Python / Install dev tools = success; `ruff check` = failure; `ruff format --check` and `pytest` = skipped.
  - Cause: `pip install --group dev` resolved `ruff>=0.15.14` to ruff 0.16.10 (and pytest 9.1.1). ruff 0.16.10 reports `SIM905 Consider using a list literal instead of str.split` at `hilclaw/driver_state.py:26:5` (landed on `main` with T-0004); ruff 0.15.14 does not. `Found 1 error.`
  - Reproduced by the executor with ruff 0.16.10 in a throwaway venv outside the repository: `ruff check` -> the same 1 error; `ruff format --check` -> passes. pytest on the runner has not run yet, so its result there is unknown; the check that the 3.11 entry really ran on 3.11 and collected the tests is still open.
  - The workflow itself behaved as specified. This is 1 CI failure, not 3 consecutive ones; it is BLOCKED because `pyproject.toml` and `hilclaw/` are Out of Scope here, and pinning ruff inside the workflow would duplicate the dev-tool list, which the Acceptance Criteria forbid.
- Provisional choices made in the workflow (unchanged if the task resumes):
  - File name `.github/workflows/ci.yml`, workflow name `CI`: one workflow that P0.5-1..3 can extend with further steps or jobs.
  - Runner `ubuntu-latest`: #9 only asks for a Linux runner; nothing in the gate depends on a specific Ubuntu release.
  - Python `"3.11"` and `"3.14"`, `fail-fast: false`: 3.11 is the `requires-python` floor; 3.14 is the newest stable CPython available to `actions/setup-python` and the version T-0002 was verified on.
  - Install: `python -m pip install --upgrade "pip>=25.1"` then `python -m pip install --group dev`: tools come from `[dependency-groups]`, no duplicated list; the project itself is not installed.
  - `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1) and `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97` (v7.0.0): first-party only, pinned by full commit SHA.
  - `permissions: contents: read`; no secrets, cache or artifacts. `concurrency`: cancel-in-progress for `pull_request` only; `push` runs are never cancelled.
- No tool-layer language choice was needed (workflow YAML only). No test added (test rule 5).
- Follow-ups: the local dev tools (ruff 0.15.14, pytest 9.0.3) are older than what CI resolves and should be upgraded so that "local green" predicts "CI green". On resume: continue PR #16 (resume rule), then the green-run log checks, the one-time negative check, the reviewer cycle, the merge and the first `main` push run check — none of these has been done.
- 2026-10-06T07:39Z — HQ-0002 answered by the owner, option (c) (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6011684226): the `driver_state.py:26` fix and exact dev-tool pins (`ruff==0.16.10`, `pytest==9.1.1`) land first as **T-0009** (a small code task), this task stays limited to the workflow file, local tools are upgraded to the same versions, and pin bumps are deliberate tasks from now on. Status set back to `TODO` with `dependsOn: [.., T-0009]` by the owner (no lock held); `nextTask` is T-0009. **On resume — executor precondition (DRIVER §3-3 does not consult `dependsOn`)**: before touching PR #16, confirm that T-0009 is on `main` (`git log origin/main --grep='^Task: T-0009'` is non-empty and `origin/main:pyproject.toml` pins `ruff==0.16.10`); if not, return BLOCKED (reason `dependency-unmet`, reference HQ-0002 and T-0009) without pushing anything. **Then**: bring `claude/T-0003-ci-skeleton` up to date with `git merge origin/main` (never force), push, then continue with the green-run log checks, the one-time negative check, the reviewer cycle, the merge and the first `main` push run check.
