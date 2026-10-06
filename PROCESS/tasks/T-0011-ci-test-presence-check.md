---
id: T-0011
title: Add the test-presence check for hilclaw/ modules to the CI workflow
phase: P0.5
status: IN_PROGRESS
commitMode: code
coversReq: ["#5 D12", "#9", "dev-code-review test completeness"]
dependsOn: [T-0003]
touchesFiles: [.github/workflows/ci.yml]
estimatedSize: {loc: 30, files: 1}
hq: []   # no new dependency: the check is an inline workflow step that uses only git and the runner's bash (see Acceptance Criteria)
---
## Why
Owner decision D12 (2026-10-05, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5996957869, item 1) adopted a **test-presence check**: "a new module under the tool package (`hilclaw/`) without a corresponding test file fails CI. Scope: the tool package only (not the whole repository)." It is test rule ④ of CLAUDE.md / DRIVER §5 made mechanical, and it is PLAN item P0.5-2. Until now only the reviewer enforces the rule (dev-code-review). CI has been on `main` since T-0003 (`17d3dee`), so the dependency is met.

Where the check lives is settled by the repository's own test rules, not by preference:
- A check script placed **inside** `hilclaw/` would be a new module of the tool package, so rule ④ (and this very check) would demand a test file for it, while rule ⑤ forbids tests that target CI workflows, check scripts and test tooling. The only named exceptions to rule ⑤ are the driver STATE validator and the merge guard hook. That placement cannot satisfy both rules.
- A script in a new top-level directory would add a repository layout convention that nothing has decided.
- Therefore the check is an **inline step of the existing workflow file**. It adds no module, no file, no directory and no dependency, and rule ⑤ applies to it plainly: no test is written for it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, test rules D12 — rules ④ and ⑤ in particular) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §11 row D12
- CLAUDE.md — 상시 규칙: "테스트 규칙" (①-⑤), "브랜치·merge 절차" (CI workflows are code mode; BLOCKED reasons incl. "새 외부 의존성"), "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; steps 4, 9, 10-12, 13, 14, 15. .claude/skills/dev-code-review/SKILL.md — what the reviewer checks (line 13: test rules; "can CI block bad code")
- PROCESS/PLAN.md — P0.5-2 (this task), P0.5-3 (left to a later task)
- D12 answer on #5: `gh api repos/myungjoo/HIL-Claw/issues/comments/5996957869 --jq .body` (item 1 is the whole requirement of this task)
- PROCESS/tasks/T-0010-ci-sh-gate-shellcheck.md — `## Acceptance Criteria` (workflow conventions: separate job, copied checkout line, tracked files taken from git NUL-separated, the red/green/clean one-time check with temporary commits) and `## Result` (why the step sets `shell: bash`; evidence format)
- Existing files: `.github/workflows/ci.yml` (whole file, 55 lines), `.editorconfig` (2-space indent for `*.yml`), `.gitattributes` (LF); `git ls-files hilclaw tests` (today: `hilclaw/__init__.py`, `cas.py`, `driver_state.py`, `merge_guard.py`; `tests/test_cas.py`, `test_driver_state.py`, `test_merge_guard.py`, `test_version.py`)

## Acceptance Criteria
D12 fixes only this: scope = `hilclaw/`, and a module without a corresponding test file fails CI. It does not fix what "corresponding" means for a nested module, whether `__init__.py` counts, how "new" is detected, or the job's name. None of these is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below and state each choice with one line of reason in the commit body, the PR body and `## Result`. Do not present them as requirements.

Workflow (`.github/workflows/ci.yml`; the only file this task changes on `main`):
- Add **one new job** next to `python` and `sh`. Suggested id `test-presence`, suggested name `Test presence (hilclaw)`. `runs-on: ubuntu-latest`, no matrix, no Python setup. The `python` and `sh` jobs, the triggers, the top-level `permissions` and the `concurrency` block stay byte-for-byte unchanged.
- Steps:
  1. checkout — the same `actions/checkout` commit SHA, tag comment and `persist-credentials: false` as the other jobs (copy the lines; do not bump the action).
  2. one `run` step with `shell: bash` that performs the check below, using only bash built-ins, coreutils and `git`. No third-party action, no Python package, no download, nothing in `pyproject.toml`.
- The rule the step enforces:
  - Checked set: every **tracked** file under `hilclaw/` whose name ends in `.py`, at any depth, except files named `__init__.py`. Take the list from git (for example `git ls-files -z -- 'hilclaw/*.py'`; a git pathspec `*` also matches `/`), so that untracked files are ignored.
  - Corresponding test file: for `hilclaw/<name>.py` it is `tests/test_<name>.py`; for a nested `hilclaw/<dir>/<name>.py` it is `tests/<dir>/test_<name>.py`. The test file must itself be **tracked** (for example `git ls-files --error-unmatch -- <path>`); its content is not inspected.
  - Checking **all** tracked modules, not only those added by the PR, is deliberate: it needs no base-ref diff, behaves the same on `pull_request` and on `push` to `main`, and every new module is necessarily covered. Today all three modules pass (`cas`, `driver_state`, `merge_guard`).
  - `__init__.py` is exempt because the one that exists is a package marker holding the version, tested by `tests/test_version.py`; record this limit (logic placed in an `__init__.py` escapes the check) in `## Result`.
- Result of the step:
  - Every checked module has its test file, or the checked set is empty: exit 0.
  - Otherwise: exit non-zero **after** examining all modules, printing one line per missing pair that names both the module and the expected test path (a `::error file=<module>::` annotation is a good form). Do not stop at the first miss.
  - A failing `git ls-files` must fail the step, not pass as an empty set. Mind that `shell: bash` gives `-eo pipefail` but neither a `while` loop fed by a pipe (subshell: a counter set inside is lost) nor process substitution (the producer's exit status is dropped) reports this by itself; pick a form that does (for example read the list into an array with `mapfile -d ''` from a command whose status is checked first).
  - No `continue-on-error`, no allowlist of exempt modules, no path filter on the job.
- YAML follows `.editorconfig` (2-space indent, LF, final newline). No comments in the script beyond what the code cannot say (CLAUDE.md "코멘트 최소화"). Keep the step short: the expected addition is 20-30 lines.

Tests:
- No test file is added or changed on `main`. Tests that target a CI workflow or a check script are forbidden (CLAUDE.md test rule ⑤, DRIVER §5 rule ⑤, and the owner's global rule of the same content). No module in `hilclaw/` is touched, so rules ①-④ are vacuous for this change.

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` all exit 0 (unchanged by this task). `git ls-files --eol .github/workflows/ci.yml` shows `i/lf`. Running the step's script locally in Git Bash against the working tree is allowed as a quick sanity check; the PR's runs are the verification.
- The PR's first run (final workflow, tree otherwise unchanged): `gh pr checks <PR> --watch` ends with **four** successful checks — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)` and the new job.
- One-time check that the gate works in both directions (dev-code-review: "can CI block bad code"), done **before** requesting the review, with temporary commits on the PR branch and never a force-push:
  1. Negative: add two temporary tracked modules without tests, one flat and one nested (for example `hilclaw/tmp_t0011_a.py` and `hilclaw/tmp_t0011_pkg/__init__.py` + `hilclaw/tmp_t0011_pkg/b.py`; trivial content that passes ruff). Expect: the new job **fails** and its log names both missing pairs (`tests/test_tmp_t0011_a.py` and `tests/tmp_t0011_pkg/test_b.py`) — this shows the nested mapping, the `__init__.py` exemption and "report all, then fail". The other three checks stay green.
  2. Positive: add the two expected test files (one trivial passing test each; keep the modules). Expect: the new job **succeeds**. If pytest cannot collect the nested temporary test, that concerns only this temporary commit; note it in `## Result` as input for the nested-layout follow-up and do not change `pyproject.toml`.
  3. Delete every temporary file. Expect: all four checks green. `git diff origin/main --stat` must then list only `.github/workflows/ci.yml`.
  The deliberate red run of step 1 does **not** count toward the "CI 3 consecutive failures" BLOCKED counter. The squash-merge removes the temporary commits from `main`.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Code mode: branch `claude/T-0011-ci-test-presence-check`, Draft PR with the `DONOTMERGE` label, reviewer cycle, squash-merge per CLAUDE.md A-13 with `Task: T-0011` as the last line of the PR body (`gh pr merge --squash --body`). PR title contains `T-0011`.
- CI exists: dev-item-address step 13 is the real check result of the PR (`gh pr checks`, `gh api` for logs). Merge only when every check of the final head is successful.
- Commit body: the provisional choices (inline step instead of a script file and why — rules ④/⑤; job id and name; all tracked modules instead of a diff; the mapping incl. nested; the `__init__.py` exemption; tracked-ness of the test file; no content inspection) with one line of reason each. No tool-layer language choice arises: the step is workflow glue, not a 2nd-layer tool; say so in one line.
- Pushing a file under `.github/workflows/` needs the `workflow` scope on the `gh`/git token (present for T-0003 and T-0010). If the push is rejected for that reason, return BLOCKED and name the missing scope.
- If the check turns out to need more than an inline step (a script file, a new directory, a dependency), do **not** add it: return BLOCKED ("requirement unclear") with the exact question for the owner — where a CI check script may live given test rules ④ and ⑤.
- Size: 1 file, about 20-30 added lines; far below 300 LOC / 5 files.
- PLAN checkbox: **P0.5-2 is ticked** when this task is DONE.

## Out of Scope
- The coverage gate (P0.5-3) and any coverage tool; the C gate (rest of P0.5-1); registering the merge guard hook (rest of P0.5-4, an owner action).
- Non-Python files under `hilclaw/` (`*.sh`, `*.c`, `*.h`): what a "corresponding test file" is for them is not defined (#9 says sh logic is tested through the Python integration tests that call it). No such file exists today.
- Inspecting test content (that a test file imports its module, or contains a test); that is the reviewer's job and, for depth, the coverage gate's.
- Extracting the check into a script file or into `hilclaw/`; a `tests/` layout rule beyond the mapping above (`__init__.py` files in `tests/`, pytest import mode); changes to `pyproject.toml`, `hilclaw/` or `tests/` on `main`.
- Changing the `python` or `sh` job, the triggers or the action SHAs.
- Editing CLAUDE.md, the skills, README.md, DRIVER.md, PLAN.md or `.claude/settings.json`.

## Follow-ups
- (planner, next) P0.5-3 coverage gate: D12 fixes the thresholds (line ≥ 80%, function ≥ 80%) and names no tool. `coverage` / `pytest-cov` is a new external dependency (BLOCKED reason, CLAUDE.md A-13), and function coverage is not a stock report of that tool; a stdlib-only measurement would be a sizeable check script that test rule ⑤ leaves untested. Expect an HQ that asks the owner for the tool and for the definition of "function coverage".
- (later, when the first nested package lands in `hilclaw/`) Confirm or replace the provisional nested mapping `tests/<dir>/test_<name>.py`, together with the pytest layout it needs (duplicate test basenames across directories).
- (later, when the first sh or C file lands in `hilclaw/`) Decide whether and how the presence check covers non-Python modules.
- (informational) The `__init__.py` exemption means code placed in a package `__init__.py` is not seen by this check; the coverage gate (P0.5-3) is what would catch it untested.
- (integrator, document mode — unchanged from T-0003 / T-0010) Update the "CI 미구축" notes in CLAUDE.md, dev-item-address step 13, dev-code-review and README.md ("로컬 검사"); DRIVER §5 rule ④ and PLAN P0.5-2 may then point at this job as the mechanical check.

## Result
