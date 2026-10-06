---
id: T-0009
title: Pin the dev tools exactly (ruff 0.16.10, pytest 9.1.1) and make main lint-clean under them
phase: P0
status: DONE
commitMode: code
coversReq: ["#5 HQ-0002 answer", "#9", "#5 D12"]
dependsOn: [T-0002, T-0004, T-0007]
touchesFiles: [pyproject.toml, hilclaw/driver_state.py, hilclaw/merge_guard.py, tests/test_merge_guard.py]
estimatedSize: {loc: 12, files: 3}   # non-test: the pin lines and three one-line lint fixes; the test file is excluded from the cap (D4)
hq: []   # HQ-0002 answered by the owner on 2026-10-06 (option c): this task is the "small code task that lands before T-0003 resumes"
---
## Why
T-0003 (CI skeleton, PR #16) was BLOCKED on HQ-0002 (it is set back to TODO, depending on this task, in the same owner edit that created this file): the workflow installs the dev tools with `pip install --group dev`, which resolves the unpinned bounds in `pyproject.toml` (`ruff>=0.15.14`, `pytest>=9.0.3`) to the newest releases, and the newer ruff reports findings that the locally installed ruff 0.15.14 does not. The first CI run was therefore red on code already on `main`, and T-0003 may only touch `.github/workflows/ci.yml`.

The owner answered HQ-0002 on 2026-10-06 with option (c) (https://github.com/myungjoo/HIL-Claw/issues/5, comment body starting `HQ-0002: (c)`): fix the reported line **and** pin the dev tools exactly in `pyproject.toml` (`ruff==0.16.10`, `pytest==9.1.1`), as a small code task that lands **before** T-0003 resumes, keeping T-0003 to the workflow file; the local tools are to be upgraded to the same versions; **pin bumps are deliberate tasks from now on**. This task is that preceding task. It answers the pin half of the T-0002 reviewer's open point N1 (pin / lock policy): exact pins, bumped only by a dedicated task; a lock file was not asked for and is not added.

The answer named one finding (`SIM905` at `hilclaw/driver_state.py:26`), the only one that existed when HQ-0002 was raised. T-0007 (`hilclaw/merge_guard.py`, `tests/test_merge_guard.py`) landed afterwards and was verified with ruff 0.15.14 only. With ruff 0.16.10 the repository at `9eef605` reports **four** findings (reproduced in a throwaway venv on 2026-10-06; `ruff format --check` passes and pytest 9.1.1 passes with 468 tests):

| Rule | Location | Nature |
|---|---|---|
| `SIM905` | `hilclaw/driver_state.py:26` | `set("...".split())` → list literal (the line the owner named) |
| `BLE001` | `hilclaw/merge_guard.py:199` | `except Exception` — intentional fail-closed catch-all of the guard (T-0007 `## Result`, "Fail closed (exit 2)" bullet: any other exception ends in a refusal) |
| `BLE001` | `hilclaw/merge_guard.py:253` | same, in `main` |
| `PLW1510` | `tests/test_merge_guard.py:465` | `subprocess.run` without an explicit `check` argument |

All four must be cleared for the pin to give a green `main` and a green PR #16; fixing only the named line would leave T-0003 red for a second time. The three additional fixes are one-line and do not change behaviour; the two `BLE001` catch-alls are deliberate and are to be kept, not narrowed (see Acceptance Criteria).

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode, the forbidden actions held by discipline, "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph
- CLAUDE.md — 상시 규칙: "브랜치·merge 절차" (code mode), "테스트 규칙" ①-⑤ (⑤: no tests for test code — the `PLW1510` fix edits a test file but adds no test), "코멘트 최소화", "미결은 발명하지 않는다"; "현재 프로젝트 상태 주의사항: CI 미구축"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow (steps 8, 9, 10-12, 13 note, 15); .claude/skills/dev-code-review/SKILL.md — what the reviewer checks
- Issue #5 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`): the HQ-0002 mirror (`### HQ-0002 — T-0003: ...`, posted by driver) and the owner's answer (`HQ-0002: (c) — ...`, 2026-10-06T07:39Z)
- PROCESS/tasks/T-0003-ci-skeleton.md — `## Result` (the red run, its cause, the workflow's install step `python -m pip install --upgrade "pip>=25.1"` then `python -m pip install --group dev`) and front matter (`dependsOn` now includes this task)
- PROCESS/tasks/T-0007-merge-guard-hook.md — `## Result`, "Fail closed (exit 2)" bullet and the "Provisional choices" list: why the two `except Exception` exist
- PROCESS/tasks/T-0002-python-project-config.md — `## Result` (reviewer N1: pin / lock policy deferred)
- Existing files: `pyproject.toml` (whole file, 17 lines), `hilclaw/driver_state.py` lines 24-28, `hilclaw/merge_guard.py` lines 190-201 and 245-256, `tests/test_merge_guard.py` lines 460-472, `.claude/settings.json` (allowlist: `python *` covers pip)

## Acceptance Criteria
Everything below is fixed by the owner's HQ-0002 answer or is a one-line mechanical fix. The one choice this task makes — how the two intentional `BLE001` catch-alls are treated — is a **provisional choice of this task** (as T-0007's provisional choices), not an owner decision and not an OD: state it with one line of reason in the commit body, in the PR body and in `## Result`, together with the three findings that the owner's answer did not name, so that the owner sees them before the merge.

`pyproject.toml`:
- `[dependency-groups] dev` becomes exactly `pytest==9.1.1` and `ruff==0.16.10` (the versions CI resolved on 2026-10-06, run 37413101512). Nothing else in the file changes: no lock file, no build backend, no `[tool.ruff.lint]` section (see below), no new group.

Lint fixes, each the minimal change that keeps behaviour identical:
- `hilclaw/driver_state.py:25-27`: replace `set("...".split())` by a literal containing the same ten keyword names (`type properties required additionalProperties items enum const pattern format minimum`); `_KEYWORDS` keeps the same membership. A `frozenset` literal or a set literal is fine (the module's sibling constants are `frozenset`).
- `hilclaw/merge_guard.py:199` and `:253`: the two `except Exception` are the guard's fail-closed contract and **stay as they are**. Provisional choice (reason in the commit body): suppress the finding per line with `# noqa: BLE001` on the `except` line — minimal, local and reversible; a per-line marker, not a multi-line comment, at the one place where the code cannot say the intent. Do **not** narrow the exception class, do not add a global `ignore` for `BLE001` in `pyproject.toml` (that would silence the rule for future modules where a blind `except` is a bug), and do not change the returned messages.
- `tests/test_merge_guard.py:465`: add `check=False` to the `subprocess.run(...)` call. No other change to the tests; no test is added (the module's behaviour is unchanged, and test rule ⑤ forbids tests that target test code).
- If ruff 0.16.10 reports anything beyond these four on the final diff (for example because `ruff format` rewrites a line), fix it in the same minimal way and list it in `## Result`. If a fix would need more than a line or would change behaviour, return BLOCKED (`requirement-unclear`) with the finding rather than deciding.

Tests:
- No test file is added. Test rules ①-④ are vacuous: no public function changes and no module is added. The existing `tests/test_driver_state.py` test for an unsupported keyword (`SchemaError`) already covers `_KEYWORDS`.

Verification (record the summary lines in `## Result`):
- **Edit the `[dependency-groups]` pins first, then install the pinned tools** in the Python environment the executor uses: `python -m pip install --upgrade "pip>=25.1"` then `python -m pip install --group dev` from the repository root (the same two commands the workflow runs). Installing before the edit would resolve the old `>=` bounds to whatever is newest at that moment, which may no longer be 0.16.10 / 9.1.1. Confirm `python -m ruff --version` prints `ruff 0.16.10` and `python -m pytest --version` prints `pytest 9.1.1`. This is the owner's instruction "local tools are to be upgraded to the same versions"; it changes the machine's environment, which the owner has asked for. If `pip install` is denied or fails, return BLOCKED and do not substitute a venv-only run as the verification of record.
- Before the commit and again before the merge, from the repository root: `python -m ruff check .` → `All checks passed!`; `python -m ruff format --check .` → all files already formatted; `python -m pytest` → all tests pass (468 at `9eef605`). `git ls-files --eol` shows `i/lf` for the four files.
- `git diff origin/main --stat` lists only the four `touchesFiles`.
- Reachability: nothing new to reach; say so.

Process:
- Code mode: branch `claude/T-0009-pin-dev-tools-ruff-fixes`, Draft PR with the `DONOTMERGE` label, reviewer cycle, squash-merge per CLAUDE.md A-13 with `Task: T-0009` as the last line of the PR body (`gh pr merge --squash --body`). PR title contains `T-0009`.
- CI is not yet on `main` (T-0003 is the next task), so this PR has no checks: dev-item-address step 13 is the local rerun, as for T-0004..T-0008. The merge guard hook is not registered yet, so it does not refuse the merge. Do not touch PR #16 or its branch.
- Commit body: that the pins implement the owner's HQ-0002 answer (c) and the "pin bumps are deliberate tasks" rule; the three additional findings and why they are in scope; the `BLE001` treatment with one line of reason; language line: Python (existing modules), no language choice for `pyproject.toml`.
- Size: 4 files (3 non-test), about 12 changed lines; far below 300 LOC / 5 files.
- No PLAN checkbox: this task is not a PLAN item (it is the HQ-0002 fix in front of P0-3). P0-3 stays unchecked until T-0003 lands; the driver's wrap-up ticks nothing for this task.

## Out of Scope
- `.github/workflows/ci.yml` and PR #16 (T-0003 resumes after this task lands; its branch picks up `main` through the pull-request merge ref or a `git merge origin/main` on resume — see T-0003 `## Result`).
- A lock file, `uv`, Dependabot or any automated pin refresh; a `[tool.ruff.lint]` `select`/`ignore` configuration; enabling or disabling rule families. Rule configuration is a later, deliberate change (Follow-ups).
- Upgrading `requires-python`, the `actions/*` SHAs, or pip itself beyond what the install step needs.
- Any behaviour change in `hilclaw/driver_state.py` or `hilclaw/merge_guard.py`; any change to `hilclaw/cas.py` or `hilclaw/__init__.py` (clean under ruff 0.16.10).
- Editing CLAUDE.md, the skills, DRIVER.md, PLAN.md or `.claude/settings.json`.

## Follow-ups
- (driver, wrap-up of this task) Set `nextTask` to `T-0003`: it is `TODO` with every dependency met once this task is `DONE`, and leaving `nextTask` at `T-0009` would make the next iteration re-select this task and close it as an empty `DONE` through the resume rule.
- (DRIVER.md, document mode, separate change) §3-3 does not consult `dependsOn` when it takes `nextTask` or a `TODO` file; only the planner (§6) does. Add to §3-3 ⓐ: a task whose `dependsOn` contains a task that is not `DONE` is not selected, and name `dependency-unmet` in the §3 BLOCKED list. Until then the executor-side precondition written into T-0003 `## Result` is the guard.
- (T-0003, on resume) Bring `claude/T-0003-ci-skeleton` up to date with `main` without force (`git merge origin/main`), push, and continue from the green-run checks. The first green run is the evidence that this task worked end to end.
- (owner, informational) Future ruff/pytest bumps are deliberate tasks (HQ-0002 answer). A bump task should run the three gates with the new version first and carry the resulting fixes in the same PR, as this task does.
- (later, deliberate) Whether to configure ruff rule families explicitly (`[tool.ruff.lint] select`) instead of relying on the defaults of the pinned version; not needed while the defaults and the pin are stable.
- (P0.5-2 / P0.5-3) Unchanged: the test-existence check and the coverage gate still start once T-0003 is on `main`.

## Result
- **Outcome**: landed. PR #19 (https://github.com/myungjoo/HIL-Claw/pull/19), squash commit `22115c6` on `main`; branch commit `15c79e5`. The task branch is deleted locally and on the remote.
- **Review**: 1 round, Approve (context-isolated `dev-reviewer`; comment https://github.com/myungjoo/HIL-Claw/pull/19#issuecomment-6012304368). No finding required a change. The reviewer reproduced the four findings on `origin/main` with ruff 0.16.10, reran the three gates on the PR head, and confirmed with `RUF100` that both `noqa` markers are in use.
- **Changes** (4 files, +18/-6):
  - `pyproject.toml`: `pytest==9.1.1`, `ruff==0.16.10`; nothing else.
  - `hilclaw/driver_state.py`: `SIM905` — `_KEYWORDS` is `_ANNOTATIONS | frozenset({...})` with the same ten names. It compares equal to the previous expression (14 members) and is a `frozenset` as before.
  - `hilclaw/merge_guard.py`: `BLE001` twice — `# noqa: BLE001` on the two `except Exception` lines; exception class and messages unchanged.
  - `tests/test_merge_guard.py`: `PLW1510` — `check=False` in `run_module`.
- **Findings beyond the owner's answer**: the HQ-0002 answer named only `SIM905`. The two `BLE001` and the `PLW1510` came from T-0007, which landed afterwards; they are fixed here because the pin alone would leave `main` and PR #16 red. ruff 0.16.10 reported nothing beyond these four on the final diff.
- **Provisional choice** (this task's, not an owner decision and not an OD): the two intentional fail-closed catch-alls are suppressed per line with `# noqa: BLE001` rather than by a global ignore, because a global ignore would also silence the rule in future modules where a blind `except` is a bug. Reversible by deleting the two markers.
- **Size against the estimate**: the estimate was about 12 lines; the diff is +18/-6 because `ruff format` puts the ten-name literal one name per line. Far below the 300 LOC / 5 files cap.
- **Local tools** (installed after the pin edit, with the workflow's two commands): `python -m pip install --upgrade "pip>=25.1"` moved pip 26.0.1 → 26.2.1; `python -m pip install --group dev` replaced pytest 9.0.3 and ruff 0.15.14. `python -m ruff --version` → `ruff 0.16.10`; `python -m pytest --version` → `pytest 9.1.1`. This is the user-level Python 3.14 environment of the driver machine, as the owner asked.
- **Verification** (before the commit, before the merge on a local test merge with `origin/main` at `1676652`, and on `main` at `22115c6` after the merge — same results each time):
  - `python -m ruff check .` → `All checks passed!`
  - `python -m ruff format --check .` → `34 files already formatted`
  - `python -m pytest` → `468 passed`
  - `git ls-files --eol` → `i/lf` for the four files
  - `git diff origin/main --stat` (before the merge) → only the four `touchesFiles`
  - CI: none on `main` yet, so PR #19 had no checks; step 13 was the local rerun.
- **Reachability**: nothing new to reach; no public function or module was added or changed.
- **Language**: Python (existing modules); `pyproject.toml` involves no language choice.
- **Tests**: none added (rules ①-④ vacuous, rule ⑤ for the test-file edit).
- **Note for the driver**: `main` moved during the task by one document commit that is not the driver's (`1676652`, "DRIVER: record the owner's confirmation of D15"); it touches `PROCESS/DRIVER.md`, `PROCESS/PLAN.md` and the D15 proposal only, and did not overlap this PR.
- **Follow-ups**: none new. The list under `## Follow-ups` stands unchanged; in particular the driver should set `nextTask` to `T-0003`, and T-0003's first green run on PR #16 is the end-to-end evidence for this task.
