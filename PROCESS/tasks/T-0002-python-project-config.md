---
id: T-0002
title: Add the Python project configuration and the first smoke test
phase: P0
status: DONE
commitMode: code
coversReq: ["CLAUDE.md language policy", "#9", "#5 D12"]
dependsOn: [T-0001]
touchesFiles: [pyproject.toml, .gitignore, tests/, hilclaw/.gitignore]
estimatedSize: {loc: 45, files: 2}
hq: []   # pytest and ruff are named by PLAN P0-2 and the CLAUDE.md language policy, so they are not a "new external dependency"
---
## Why
The CLAUDE.md language policy and Issue #9 fix the Python gate of the tool layer as `pytest` + `ruff`, "built up front". T-0001 created the empty package `hilclaw/` but nothing can run or lint it yet: there is no `pyproject.toml`, no test, and no declared minimum Python version. This task adds the smallest configuration that makes `pytest` and `ruff` runnable locally with one command each, so that P0-3 (CI skeleton) only has to call those commands and P1 tasks have a place to put tests. It also closes the two T-0001 follow-ups addressed to P0-2: a test for `hilclaw/__init__.py` (test rule 4) and keeping `__version__` consistent with `pyproject.toml`.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming, time limit) and §5 (task format, size limit, test rules D12)
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책", "테스트 규칙", "코멘트 최소화", "브랜치·merge 절차" (code mode); "현재 프로젝트 상태 주의사항: CI 미구축"
- .claude/skills/dev-item-address/SKILL.md (the procedure to follow)
- PROCESS/PLAN.md — P0-2, P0-3, P0.5-2, P0.5-3 (to see what is deliberately left to later items)
- PROCESS/tasks/T-0001-repo-skeleton.md — `## Result` follow-ups
- ARCHITECTURE/Requirements.md — C-7 (Constraints table: Linux/macOS/WSL, POSIX premise), FR-10 (single-package sentence)
- Issue #9 (`gh issue view 9 --repo myungjoo/HIL-Claw --comments`) — "Scope update" and "Revision" comments
- Existing files: `hilclaw/__init__.py`, `.editorconfig`, `.gitattributes`, `.claude/settings.json` (Edit allowlist)

## Acceptance Criteria
Nothing in the repository or the issues fixes the Python minimum version, the dependency declaration form, or the packaging layout. None of them is an owner-only decision (DRIVER §9) or a registered OD, and PLAN P0-2 assigns "minimum version" to this task. They are therefore **conventions chosen by this task, provisional**: choose by the criteria below, and state each choice and its reason in the commit body and in `## Result`. Do not present them as requirements.

`pyproject.toml` (new, repository root):
- `[project]` with `name = "hilclaw"`, a static `version` equal to `hilclaw.__version__` (currently `0.0.0`), and `requires-python`.
  - Minimum version criteria: the lowest CPython release that (a) is still security-supported upstream today, (b) is obtainable on all three C-7 platforms (Linux, macOS, WSL) and on GitHub-hosted Linux runners, and (c) provides every standard-library module this task uses (`tomllib` needs 3.11). Lower bound only, no upper cap. The planner's expectation is `>=3.11`; pick differently only with a stated reason.
- No `[build-system]` table, no build backend, no `src/` move, no console scripts. The package is used from the repository root; making it installable is not needed by any P0 item and is deferred (see Follow-ups). `hilclaw/__init__.py` keeps its hard-coded `__version__`; consistency is enforced by the test below rather than by a backend's dynamic-version feature.
- Development tools are declared as exactly `pytest` and `ruff`, in a form that does not require building the package (expected: `[dependency-groups]` `dev`, PEP 735). Lower bounds only; record the versions you verified with. No other dependency (no `pytest-cov`, no plugins, no type checker).
- `[tool.pytest.ini_options]`: `testpaths = ["tests"]` and whatever is needed so that both `python -m pytest` and bare `pytest` import `hilclaw` from the repository root without installation (expected: `pythonpath = ["."]`).
- `[tool.ruff]`: `target-version` consistent with `requires-python`; otherwise ruff defaults for lint rules, line length and formatter (compatible with `.editorconfig`). Do not enable extra rule sets in this task.

Smoke test (new, `tests/test_version.py`; the `tests/` location and the file name are provisional until P0.5-2 fixes the module-to-test mapping):
- happy: `import hilclaw` succeeds and `hilclaw.__version__` is a non-empty `str`.
- consistency (drift guard): `hilclaw.__version__` equals `project.version` read from `pyproject.toml` with `tomllib`, locating the file relative to the test file, not the current working directory.
- negative: `hilclaw/__init__.py` exposes no callable, so there is no invalid-input path to test (test rules 2 and 3 are vacuous beyond the two cases above). Instead, confirm once locally that the drift guard really fails when the two versions differ (temporary, uncommitted edit) and note that in `## Result`. Do not add a test for the test, for `pyproject.toml` parsing, or for the ruff/pytest configuration (test rule 5).

Ignore rules for tool caches:
- After running the verification commands, `git status --porcelain` must list no cache artifact (`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`).
- Preferred: a root `.gitignore` with those four patterns plus `.venv/`. Note that `.gitignore` is **not** in the Edit allowlist of `.claude/settings.json`. If the write is denied (non-interactive session), do not work around it through the shell: instead add `hilclaw/.gitignore` and `tests/.gitignore` containing `__pycache__/` (both paths are allowlisted; pytest and ruff already self-ignore their own cache directories) and record the missing allowlist entry in Follow-ups for the owner.

Local verification (CI is not built — run all of these from the repository root before the commit and again before the merge, and paste the summary lines into `## Result`):
- `python -m pytest` — exits 0, collects at least 1 test, 0 failures.
- `python -m ruff check .` — exits 0.
- `python -m ruff format --check .` — exits 0 (existing `hilclaw/__init__.py` included).
- `git ls-files --eol` — no `i/crlf` for the new files.
- If `pytest` or `ruff` is missing for the interpreter in use, install only those two; if installation is denied or impossible, return BLOCKED rather than skipping a check.

Process:
- Code mode: branch `claude/T-0002-python-project-config`, Draft PR, reviewer cycle, squash-merge per CLAUDE.md A-13 with `Task: T-0002` as the last line of the PR body.
- The commit body states the provisional choices (minimum Python version, dependency declaration form, no build backend, `tests/` location) with one line of reason each, and that the language is Python because the gate being configured is the Python gate.
- Size stays within 300 LOC / 5 files excluding tests; expected 2 non-test files.

## Out of Scope
- CI workflow under `.github/` (P0-3). Exact tool-version pinning or a lock file (decide in P0-3 if CI reproducibility needs it).
- Coverage measurement and the 80% gate, `pytest-cov` (P0.5-3).
- The test-existence check and the final module-to-test naming rule (P0.5-2).
- README changes (P0-5). shellcheck / clang gates (P0.5-1).
- Build backend, installable distribution, entry points, `src/` layout, any runtime dependency.
- Any tool code in `hilclaw/` beyond what already exists; `hilclaw/__init__.py` is expected to stay unchanged.
- Editing `.claude/settings.json` (denied to sessions by D11).

## Follow-ups
- (P0-3) CI should call exactly the three verification commands above and install the dev tools from the declaration made here.
- (P0.5-2) Decide whether `__init__.py` needs a dedicated test file or is exempt, and whether `tests/test_version.py` satisfies the mapping.
- (later, first need) Packaging: build backend / installability / entry points, likely together with OD-18 (MCP server vs CLI exposure).

## Result
- PR #14 (code mode), squash-merged to main as 5860a7d ("T-0002: Add the Python project configuration and the first smoke test (#14)"); branch commit 3317d80. Change: 3 files, +39 lines (`pyproject.toml`, `.gitignore`, `tests/test_version.py`); 2 non-test files. `hilclaw/__init__.py` unchanged.
- Review: 1 round by a reviewer agent, verdict Approve (0 Critical/High/Medium, 2 Low, 4 Nit; https://github.com/myungjoo/HIL-Claw/pull/14#issuecomment-5999553366). No finding asked for a change in this PR, nothing was changed, so no re-review.
- Language: Python, because the gate being configured is the Python gate. No dependency beyond pytest and ruff.
- Provisional choices (conventions of this task, not requirements):
  - `requires-python = ">=3.11"`: lowest CPython that is upstream security-supported, obtainable on Linux/macOS/WSL and GitHub-hosted Linux runners, and ships `tomllib` (used by the drift guard). No upper cap.
  - Dev tools as `[dependency-groups] dev` (PEP 735): installable without building the package. Lower bounds are the verified versions, `pytest>=9.0.3` and `ruff>=0.15.14` (verified on CPython 3.14.4); no pin, no lock file.
  - No `[build-system]` / build backend / `src/` move: no P0 item needs an installable package; `pythonpath = ["."]` lets pytest import `hilclaw` from the root. `__version__` stays hard-coded; the test enforces consistency.
  - `tests/test_version.py` at the repository root: provisional until P0.5-2.
  - ruff: only `target-version = "py311"`; rules, line length and formatter at ruff defaults.
- `.gitignore`: the preferred root `.gitignore` (4 cache patterns + `.venv/`) was written with the Write tool without a denial, so the `hilclaw/.gitignore` / `tests/.gitignore` fallback was not used.
- Local verification (CI not built), run before the commit and again before the merge, same output both times:
  - `python -m pytest` -> `2 passed in 0.01s` (also passes when started from `tests/`, and through the `pytest.exe` entry point, which is not on PATH on this PC)
  - `python -m ruff check .` -> `All checks passed!`
  - `python -m ruff format --check .` -> `2 files already formatted`
  - `git ls-files --eol` -> `i/lf w/lf` for `.gitignore`, `pyproject.toml`, `tests/test_version.py`
  - `git status --porcelain` after the runs -> no cache artifact
- Drift-guard negative check (temporary, uncommitted edit, reverted): with `version = "0.0.1"` in `pyproject.toml`, `python -m pytest` -> `1 failed, 1 passed` (`FAILED tests/test_version.py::test_version_matches_pyproject - AssertionError`).
- Follow-ups:
  - (P0-3) Run CI on the lowest supported version (3.11) as well; the `>=3.11` floor was only verified on 3.14.4 (reviewer L1).
  - (P0-3) `[dependency-groups]` needs pip >= 25.1 (`pip install --group dev`) or uv; the pip bundled with 3.11 is too old, so the CI step must upgrade pip or use uv (reviewer L2).
  - (P0-3) When deciding pin/lock policy, consider relaxing the dev-tool lower bounds, which equal the newest verified versions (reviewer N1).
  - (P0.5-2) `tests/` has no `__init__.py`, so test file basenames must be unique across directories; settle together with the mapping rule (reviewer N2).
  - (owner, optional) `.gitignore` is not in the Edit allowlist of `.claude/settings.json`; the write succeeded in this session, but a stricter non-interactive session may be denied.
