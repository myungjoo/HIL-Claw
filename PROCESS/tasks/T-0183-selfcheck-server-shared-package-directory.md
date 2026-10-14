---
id: T-0183
title: Let hilclaw/selfcheck_server.py take the package directory from hilclaw.checkout_boundary instead of its own copy, with no change of behaviour
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0182]
touchesFiles: [hilclaw/selfcheck_server.py, hilclaw/checkout_boundary.py]
estimatedSize: {loc: 10, files: 2}   # tests excluded (D4): one import and one name in selfcheck_server, at most one docstring sentence in each module; no test is expected to change
hq: []
---
## Why

T-0182 (PR #126, 3910a5f) moved the copies of the "directory that holds this package" into `hilclaw/checkout_boundary.py` as the public `PACKAGE_DIRECTORY` (line 17), for `scratch`, `selfcheck_session` and `bring_in`. Its `## Result` names one copy left: `hilclaw/selfcheck_server.py` line 99 still computes

```python
_PACKAGE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

and uses it once, as the last element of `args` in `server_entry` (line 199). The value is the same expression applied to a file in the same package directory, so it is the same string. T-0182 left it out of scope because it serves a different purpose: it is the start argument of the server process, not a checkout boundary. This task removes the copy and has `selfcheck_server` use `checkout_boundary.PACKAGE_DIRECTORY`. That leaves one definition of the package directory in `hilclaw/`.

Points the executor must keep:

- **The server process imports the module too.** `_START` (lines 115-118) puts the package directory first on `sys.path` under `-I` and imports `hilclaw.selfcheck_server`. With the change, that import also loads `hilclaw.checkout_boundary`, which imports only `itertools` and `os`. The process still needs nothing outside the package. `tests/test_selfcheck_server.py::test_a_package_under_a_path_with_a_space_and_a_non_ascii_character` (line 284) copies the whole `hilclaw/` directory, so it covers this.
- **Public names stay the same.** Import the module under a private alias, as the other three callers do (`from hilclaw import checkout_boundary as _checkout_boundary`). Then no new public name appears in `selfcheck_server`.
- **Docstrings.** The `selfcheck_server` module docstring (lines 26-30) says the server entry holds "the directory that holds this package (from the module's own location)". The `checkout_boundary` module docstring (lines 1-12) describes the module as the test "shared by the modules that place a directory". The executor updates each sentence only as far as it becomes inaccurate, in at most one sentence per module, and says what changed in the commit body. If neither sentence becomes inaccurate, leave both unchanged.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72): executor procedure, resume rule, the 2h30m limit.
- `PROCESS/DRIVER.md` §5 (lines 86-114): task format, naming `claude/T-0183-*`, the `Task: T-0183` trailer (also the last line of the PR body, which becomes the squash body), size cap D4, D12 test rules.
- `PROCESS/DRIVER.md` §1-5 (line 28): Bypass permissions and the forbidden actions. A denied or failed tool call is BLOCKED.
- `CLAUDE.md` "상시 규칙": comment minimisation, "개발 드라이버와 런타임의 구분" (no `claude` is started; the selfcheck tests use child Python processes only), "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙" (D12).
- `.claude/skills/dev-item-address/SKILL.md` (whole; code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/checkout_boundary.py` (whole, 56 lines).
- `hilclaw/selfcheck_server.py`: module docstring lines 1-77 (especially lines 26-40, "The server entry"), imports and constants at lines 79-118 (`_PACKAGE_DIRECTORY` at line 99, `_START` at lines 115-118), `server_entry` at lines 182-200.
- `tests/test_selfcheck_server.py`: line 34 (`REPO_ROOT`), lines 284-312 (the copied-package test) and lines 695-720 (the `server_entry` shape tests, including `Path(entry["args"][-1]).samefile(REPO_ROOT)` at line 704).
- `PROCESS/tasks/T-0182-shared-checkout-boundary-check.md` `## Result` (last bullet: the origin of this follow-up).

Read Python sources with `PYTHONIOENCODING=utf-8` on this machine. Line numbers are those of `main` at a7935a3. Where they differ, the text wins.

## Acceptance Criteria

1. `hilclaw/selfcheck_server.py` no longer defines `_PACKAGE_DIRECTORY`. `server_entry` puts `checkout_boundary.PACKAGE_DIRECTORY` as the last element of `args`, imported under a private alias. Nothing else in `server_entry`, `_START`, `main` or the registry changes.
2. **No behaviour change.** Every existing test in `tests/test_selfcheck_server.py`, `tests/test_checkout_boundary.py`, `tests/test_scratch.py`, `tests/test_selfcheck_session.py` and `tests/test_bring_in.py` passes without being edited. If a test refers to the removed `selfcheck_server._PACKAGE_DIRECTORY` (none did at a7935a3), the executor stops and reports it rather than weakening the test. No new test is required: the behaviour is already covered (lines 284-312 and 695-720 of `tests/test_selfcheck_server.py`, and the `PACKAGE_DIRECTORY` test of `tests/test_checkout_boundary.py`). If review finds a public function of either touched module without a test, add one (D12 ③).
3. After the change, `grep -rn "dirname(os.path.dirname(os.path.abspath(__file__)))" hilclaw/` finds exactly one line, the one in `hilclaw/checkout_boundary.py`. The executor records the output in `## Result`.
4. Docstrings are handled as in Why: at most one sentence per module changes, and only where it would otherwise be inaccurate.
5. `python -m pytest` and `ruff check` / `ruff format --check` pass locally. CI (six jobs) is green. `hilclaw/` line and function coverage stay at or above 80%, and the figures are recorded in `## Result`.
6. The commit body states the language in one line (Python, the language of the module it edits).

## Out of Scope

- Any change to the server entry's form (`-I -c`, the `env` members, the tokens, the wire copy), to `_START`, or to `checkout_boundary`'s functions.
- Other `os.path` uses in `hilclaw/` that are not the package directory expression.
- The build directory of `correctness.check` (ADR-0056). T-0176 is BLOCKED on HQ-0020 and is not touched.
- Any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`.
- Starting `claude`, or anything that needs a board or an API key (D16).

## Follow-ups

- (driver/planner) Little else is selectable until HQ-0020 is answered (T-0176, then the `cpu_standin` operation for `correctness.check`). The remaining PLAN items P0.5-4 (owner's hook registration), P1-1 and P1-8 wait on owner answers or on that HQ.

## Result
