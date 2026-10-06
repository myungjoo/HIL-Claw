---
id: T-0012
title: Add hilclaw.config.json (data repository binding) and its loader with environment overrides
phase: P1
status: DONE
commitMode: code
coversReq: [FR-13, "#5 A-1", "#5 D7"]
dependsOn: [T-0002, T-0003]
touchesFiles: [hilclaw.config.json, hilclaw/config.py, tests/test_config.py]
estimatedSize: {loc: 100, files: 2}   # non-test: the JSON file and the loader module; the test file is excluded from the cap (D4)
hq: []   # standard library only; no OD is closed and no ADR is written (see Why)
---
## Why
Owner decision #5 A-1 (2026-07-22, detail 2) fixes how the source repository finds the data plane: "a `hilclaw.config.json` in the source repository — `data_repo.url` + `data_repo.local_path`, overridable by environment variables". FR-13 repeats it ("on the source side `hilclaw.config.json` specifies the physical binding"), and the README of `HIL-Claw-data` states the same rule. The data repository itself exists since 2026-10-05 (D7: private, empty `runs/` `db/` `blobs/` layout), and D7 narrowed PLAN P1-7 to "the config file only". This task is P1-7 in full: the file and the one function that reads it.

It is a leaf that later tasks need: `hilclaw/cas.py` (T-0008) takes the data repository root as an explicit argument and its Follow-ups name P1-7 as the supplier of that argument; the runtime STATE and `artifacts.json` (P1-8, P1-6 slice 3) will live under the same root.

Why this item now (planner's judgement, DRIVER §6): the phase is P0.5, but none of its three open items can become a task today. The rest of P0.5-1 (C gate) waits for P1-2 and P1-3; P0.5-3 (coverage gate) needs a tool that D12 does not name, which would be a new external dependency, and a definition of "function coverage" (an owner question, not a task); the rest of P0.5-4 is the owner's hook registration. §6 allows an item of a later phase whose dependencies are met. Among the P1 items this one is determined by a confirmed decision and carries neither an "owner confirmation needed" nor an "OD-n must be closed" mark in PLAN. The Requirements sentence "OD-4, OD-6, OD-8 are to be confirmed before the first commit" does not stop it: the file names the data repository, not anything inside it (no key schema, no coder spec, no directory layout). The file lives in the source repository, so it is not a data-plane schema (STATE/spec/eval/artifacts). If the executor or the reviewer finds that the implementation does need one of those ODs, that is the BLOCKED reason "design choice needing an OD" (DRIVER §3), not something to decide silently.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §9, §11 row D7
- PROCESS/PLAN.md — P1-7 (this task); P1-1, P1-6, P1-8 for what is deliberately not touched
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성" and "데이터 plane 스키마 변경"), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- ARCHITECTURE/Requirements.md — FR-13 (the whole row), NFR-7 ② (which artefacts carry `schema_version`), C-2, C-7 (POSIX and WSL), the OD register rows OD-8, OD-18 and OD-25 (read to know what is **not** decided here); ARCHITECTURE/UsageCases.md §0 "데이터 plane" definition
- Issue #5, comment "A-1 확정 (2026-07-22)": `gh api repos/myungjoo/HIL-Claw/issues/comments/5046307826 --jq .body` (detail 2 is the whole requirement of this task); comment "D7 done": `gh api repos/myungjoo/HIL-Claw/issues/comments/5996366069 --jq .body` (the repository URL)
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks
- PROCESS/tasks/T-0008-cas-blob-store.md — `## Acceptance Criteria` and `## Result`: conventions of the sibling module (stdlib only, explicit arguments, provisional choices listed with one line of reason, reachability check with the stdlib `trace` module, how the `## Result` text is handed to the driver)
- PROCESS/tasks/T-0011-ci-test-presence-check.md — `## Result`: the four CI jobs on every PR and the module-to-test mapping `hilclaw/<name>.py` → `tests/test_<name>.py` that CI enforces
- Existing files: `pyproject.toml`, `hilclaw/__init__.py`, `hilclaw/driver_state.py` (style reference: `REPO_ROOT`, docstrings, error class), `hilclaw/cas.py`, `tests/test_cas.py` (test style), `.editorconfig` (2-space indent for `*.json`), `.gitattributes`, `.github/workflows/ci.yml`

## Acceptance Criteria
A-1 fixes only this: the file is named `hilclaw.config.json`, it is in the source repository, it has `data_repo.url` and `data_repo.local_path`, and environment variables can override them. The committed values, the names of the environment variables, how a relative path is resolved, the module name, the public API and the error types are **not** fixed anywhere. None of them is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below, state each choice with one line of reason in the commit body, the PR body and `## Result`, and do not present them as requirements.

Constraints:
- **Standard library only** (`json`, `os`, `pathlib`, `typing` as needed). Adding any package is the BLOCKED reason "new external dependency". `pyproject.toml` stays unchanged.
- Code must run on CPython 3.11 and 3.14 (both are CI matrix entries).
- The loader only **reads** one file and the environment. It does not create, clone, fetch or inspect the data repository, does not check that `local_path` exists, never runs `git`, and writes nothing.
- No command line entry point, no `main`, no MCP server: how layer-2 tools are exposed to layer 1 is OD-18 (open).
- `hilclaw/cas.py` is not changed: it keeps taking the root as an explicit argument; a caller combines the two.

Config file (new, `hilclaw.config.json` at the repository root; tracked):
- Exactly this content, 2-space indent, LF, final newline:
  ```json
  {
    "data_repo": {
      "url": "https://github.com/myungjoo/HIL-Claw-data",
      "local_path": "../HIL-Claw-data"
    }
  }
  ```
- `url` is the repository created under D7. `local_path` is a provisional default: a checkout next to the source checkout. It cannot be an absolute path, because the file is shared by every checkout (the owner's tree, the driver's clone, CI); a machine that keeps the data repository elsewhere uses the environment override. Record it as provisional.
- No `schema_version` key: A-1 names two keys, and NFR-7 ② lists the persisted run artefacts (STATE/spec/eval/db records), not this binding file. Record this as a decision to revisit (Follow-ups), do not add the key.

Module (new, `hilclaw/config.py`; provisional name. Python because the package is Python and JSON and path handling are in the stdlib — one line in the commit body and `## Result`):
- Module docstring and short docstrings on the public names (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Public API (provisional names and shapes; the executor may rename or regroup them, but every public function must be tested):
  - `DataRepo` — a `typing.NamedTuple` with `url: str` and `local_path: pathlib.Path` (always absolute).
  - `load_data_repo(config_path=None, environ=None) -> DataRepo` — `config_path` defaults to `hilclaw.config.json` at the repository root (computed from `__file__`, as `hilclaw/driver_state.py` does with `REPO_ROOT`); `environ` defaults to `os.environ` and accepts any mapping, so that tests pass a plain `dict` instead of patching the process environment. `config_path` accepts `str` and `os.PathLike`.
  - `ConfigError` (a `ValueError` subclass) — every problem of the file or of the resulting values; the message names the file path and the offending key.
  - The two environment variable names as public constants: `HILCLAW_DATA_REPO_URL` and `HILCLAW_DATA_REPO_LOCAL_PATH` (the key path in upper case with the package prefix).
- Behaviour:
  - Each value is taken from its environment variable when that variable is set to a non-empty string, otherwise from the file. The two keys are overridden independently. A variable set to the empty string counts as not set (the usual shell convention; `VAR= cmd` must not blank a value).
  - The file must exist, be UTF-8, parse as JSON and be a JSON object. `data_repo`, when present, must be an object. A missing or unreadable file, invalid UTF-8, invalid JSON and a wrong top-level or `data_repo` type all raise `ConfigError` (chained with `from` to the underlying error).
  - A value from the file must be a non-empty JSON string; another type (number, `null`, list, object, boolean) or `""` raises `ConfigError`. A key that is absent from the file is acceptable **only** when its environment variable supplies the value; otherwise `ConfigError` names the missing key. A wrong-typed value in the file is an error even when the environment overrides it (the file is wrong either way) — or is ignored when overridden, if the executor finds that simpler; state the choice and test it.
  - Unknown keys, at the top level and inside `data_repo`, are ignored: later tasks add sections to this file (backends, limits) and an older loader must keep working (NFR-7 ①).
  - `url` is returned as given. No format check beyond "non-empty string": https, ssh and a local path are all valid git remotes.
  - `local_path`: `~` is expanded (`os.path.expanduser`). A relative path **from the file** is resolved against the directory that contains the config file (so the result does not depend on the caller's working directory); a relative path **from the environment** is resolved against the current working directory (what a shell user expects). The result is absolute and normalised (`..` segments removed) without requiring the path to exist and without resolving symbolic links.
  - The function is pure apart from reading: no caching, no module-level state filled at import time other than constants.

Tests (new, `tests/test_config.py`; excluded from the size cap). Config files are written under pytest's `tmp_path`; the environment is passed as a `dict`, except where the default `os.environ` path itself is under test (`monkeypatch.setenv` / `delenv`).
- happy:
  - a file with both keys and an empty environment → `DataRepo` with the URL as written and `local_path` absolute.
  - the **committed** `hilclaw.config.json` loads through the default `config_path` with `environ={}`: the URL is `https://github.com/myungjoo/HIL-Claw-data` and `local_path` equals `<repository root>/../HIL-Claw-data` normalised (the path need not exist).
  - `config_path` given as `str` and as `Path` give the same result.
- branch:
  - relative `local_path` in the file resolves against the config file's directory, also when the working directory is elsewhere (`monkeypatch.chdir`); an absolute `local_path` in the file is returned unchanged; `~` is expanded (patch `HOME` and `USERPROFILE`, or `os.path.expanduser`).
  - each environment variable alone overrides its key and leaves the other from the file; both together override both.
  - a relative `local_path` from the environment resolves against the working directory, not against the config file's directory.
  - an environment variable set to `""` does not override.
  - a key absent from the file is supplied by its environment variable; a file whose `data_repo` is absent works when both variables are set.
  - unknown keys at both levels are ignored.
  - `environ=None` reads the real process environment (`monkeypatch.setenv`).
- negative (each → `ConfigError`, and the message names the path or the key as specified):
  - the file does not exist; the path is a directory.
  - not valid JSON; not valid UTF-8; valid JSON whose top level is a list, a string or `null`.
  - `data_repo` is a list, a string, a number or `null`.
  - `url` or `local_path` missing with no override (each one separately; also an empty file object `{}`).
  - `url` or `local_path` of a wrong type (`123`, `null`, `[]`, `{}`, `true`) or `""`.
  - the chosen behaviour for "wrong-typed value in the file but overridden by the environment" (one test that pins the choice).
- Coverage is not measured by CI yet (P0.5-3 is open); the tests must still reach every branch above — say in `## Result` how you checked (e.g. the stdlib `python -m trace --count --missing --module pytest tests/test_config.py`, cover files written outside the repository).
- Do not add tests for other test files, `pyproject.toml` or any CI file (test rule ⑤).

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m pytest` exits 0 (all tests, including the existing ones), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0 (pinned tools: ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol hilclaw.config.json hilclaw/config.py tests/test_config.py` shows `i/lf` for all three; `python -c "import json; json.load(open('hilclaw.config.json', encoding='utf-8'))"` succeeds.
- `git status --short` after the test run shows no stray file.
- `git diff origin/main --stat` lists only the three files in `touchesFiles`; `pyproject.toml`, `hilclaw/__init__.py`, the other modules, `.gitignore`, `.claude/`, `.github/`, `README.md` and `ARCHITECTURE/` are unchanged.
- CI on the PR: `gh pr checks <PR> --watch` ends with **four** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`. Merge only then. The tests run on Linux in CI and on Windows locally, so path assertions must be built with `pathlib` / `os.path`, never with hard-coded separators or drive letters.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Code mode: branch `claude/T-0012-data-repo-config`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0012`; executor commits end with the trailer `Task: T-0012`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (≤ 7 rounds).
- Squash-merge per CLAUDE.md A-13 with `Task: T-0012` as the last line of the PR body, using `gh pr merge --squash` with that body (`--body-file` avoids quoting problems); delete the branch. The merge guard hook of T-0007 is not registered, so checking the four checks before the merge is the executor's own step.
- Commit body: the provisional choices (committed `url` and `local_path` values, no `schema_version`, module name, API and return type, environment variable names, empty variable = not set, relative-path bases for file and environment, `~` expansion, no existence check, unknown keys ignored, error type, the "wrong type but overridden" behaviour) with one line of reason each, and the language line.
- `## Result`: hand the text to the driver in your final report instead of committing this task file on the branch, so that the diff check above holds (as T-0007 and T-0008 did). `PROCESS/STATE.json`, `PROCESS/journal/` and the `PROCESS/PLAN.md` checkbox belong to the driver. **PLAN P1-7 is ticked** when this task is DONE.
- Size: 2 non-test files, about 100 lines; far below 300 LOC / 5 files.
- If the implementation turns out to need a decision that only the owner can make (for example where the owner's machines keep the data checkout, as a fact rather than as an overridable default), do not guess: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.

## Out of Scope
- Cloning, creating, fetching, committing to or validating the data repository; checking that `local_path` is a git checkout or has the `runs/` `db/` `blobs/` layout; any write to the real `HIL-Claw-data` repository.
- Any other configuration section (backends, budgets, model names, tolerances, the harness) and a general configuration framework; only `data_repo` is read.
- A `schema_version` for the config file, a JSON Schema file for it, and a validator command.
- A user-level or machine-level config file (`~/.config/...`, `hilclaw.config.local.json`), a search up the directory tree, an environment variable that points at another config file, and a `.gitignore` entry for a local override.
- Wiring the loader into `hilclaw/cas.py` or any other module; a command line, MCP exposure or hook integration (OD-18).
- The layout inside the data repository (OD-8, OD-4), `artifacts.json`, `instance.json`, the runtime STATE (P1-6 slices, P1-8); data governance and the template model (OD-25, owner-only).
- Recording the source commit hash in `instance.json` (A-1 detail 3; belongs to P1-8).
- Editing README.md, CLAUDE.md, DRIVER.md, PLAN.md, `ARCHITECTURE/` or the skills (document mode, separate changes); `.github/workflows/ci.yml`; `pyproject.toml`.

## Follow-ups
- (integrator, document mode) README.md "저장소 지도" may list `hilclaw.config.json` and the two environment variables once this lands.
- (P1-6 slices 2-3, P1-8) Callers obtain the data root with `load_data_repo().local_path` and pass it to `hilclaw.cas` and to the STATE / `artifacts.json` writers.
- (decision to revisit) Whether the config file gets a `schema_version` when a second section is added (NFR-7 ② names run artefacts only).
- (decision to revisit) The provisional default `local_path` (`../HIL-Claw-data`) and the environment variable names: the owner may prefer other values; changing them is a one-line change plus tests.
- (later, with the first run-time entry point) Whether a missing data checkout is reported by the loader's caller with a hint ("clone `url` to `local_path`"), and whether the system may clone it itself (A-3 forbids automatic push, says nothing about clone).
- (P0.5-3) First coverage measurement of `hilclaw/config.py` once the coverage gate exists.

## Result
- 2026-10-06 — fresh start (landed check: nothing with `Task: T-0012` on `main`, no PR, no branch). **DONE**: PR #22 https://github.com/myungjoo/HIL-Claw/pull/22 (code mode) squash-merged to main as `6448177` ("T-0012: Add hilclaw.config.json and its loader with environment overrides (#22)", last body line `Task: T-0012`); remote and local branch `claude/T-0012-data-repo-config` deleted. Branch commits: `d53a72b` (implementation), `e3e1964` (review round 1), `79b1489` (review round 2).
- Change: 3 files, +416 lines — `hilclaw.config.json` 6, `hilclaw/config.py` 89, `tests/test_config.py` 321; non-test 95 lines in 2 files (cap 300/5; the estimate was 100). `pyproject.toml`, `hilclaw/__init__.py`, `hilclaw/cas.py`, the other modules, `.gitignore`, `.claude/`, `.github/`, `README.md` and `ARCHITECTURE/` are unchanged. Standard library only (`json`, `os`, `pathlib`, `typing`). No OD closed, no ADR, no data-plane schema touched, no new dependency. PLAN P1-7 ticked.
- This `## Result` was not committed on the task branch (the task's own diff check); the executor handed the text to the driver.
- **Process incident (executor error, recovered, no force push)**: before the merge, a chained shell command stopped at a failing `git rev-parse --short` with three arguments, and the trailing `git push origin --delete claude/T-0012-data-repo-config` in the same command line still ran. The remote branch was deleted before the merge and GitHub closed PR #22 unmerged. Recovery: the unchanged local branch was pushed again as a new branch at the same commit `79b1489` (plain push), `gh pr reopen 22`, CI re-ran on that head (run 37450404380, four checks green), then the normal merge sequence followed. The reviewed head and the merged head are the same commit. No tool call was denied.
- Language: Python, because the package is Python and JSON and path handling are in the standard library.
- Review: 3 rounds by fresh-context `dev-reviewer` agents, all Approve, no `SECURITY` finding, no Blocking / Major / Minor in any round. The reviewers did not rerun tests (read-only role); CI and the executor's local runs are the gate.
  - Round 1, Approve on `d53a72b` (https://github.com/myungjoo/HIL-Claw/pull/22#issuecomment-6014287829): Nit, a `ValueError` from opening the path (NUL character) was reported as "not valid UTF-8 JSON" -> fixed in `e3e1964` (read and parse are separate steps with the messages "cannot read", "not valid UTF-8", "not valid JSON"; one test added); Info, a UTF-8 BOM is rejected -> kept, pinned by one test, listed as provisional; Nit, one test built an environment-relative expectation from `tmp_path` -> fixed (`os.getcwd()`); Info, `REPO_ROOT` duplicates `driver_state.REPO_ROOT` -> no change (sharing it would touch a module outside the task). Response: https://github.com/myungjoo/HIL-Claw/pull/22#issuecomment-6014307646
  - Round 2, Approve on `e3e1964` (https://github.com/myungjoo/HIL-Claw/pull/22#issuecomment-6014327020): Nit, PR body out of date (test count, BOM choice) -> body updated; Nit, `test_relative_config_path_gives_absolute_result` had the same `tmp_path` pattern -> fixed in `79b1489`; Info, `~` without a known home directory silently stays a relative segment -> no code change, recorded as provisional. Response: https://github.com/myungjoo/HIL-Claw/pull/22#issuecomment-6014337977
  - Round 3, Approve on `79b1489` (https://github.com/myungjoo/HIL-Claw/pull/22#issuecomment-6014367262): no Nit. Info, a pathologically deep JSON document raises `RecursionError`, which is not turned into `ConfigError`; Info, no test pins the "unexpandable `~`" behaviour. Neither asked for a change; the head did not change after this Approve.
- Provisional choices (conventions of this task, not requirements; A-1 fixes only the file name, its place, the two keys and "environment variables can override"):
  - Committed `url` = `https://github.com/myungjoo/HIL-Claw-data`: the repository created under D7.
  - Committed `local_path` = `../HIL-Claw-data`: a checkout next to the source checkout; it cannot be absolute because every checkout shares the file.
  - No `schema_version` key: A-1 names two keys and NFR-7 ② lists the persisted run artefacts, not this binding file.
  - Module name `hilclaw/config.py`: next to the other layer-2 modules, covered by pytest, ruff and the test-presence check.
  - API: `load_data_repo(config_path=None, environ=None) -> DataRepo`; `DataRepo` = `NamedTuple(url: str, local_path: Path)`, as `cas.BlobRef`; `config_path` accepts `str` and `os.PathLike`, `environ` any mapping so that tests pass a `dict`; `REPO_ROOT` and `DEFAULT_CONFIG_PATH` are public constants, as in `driver_state`.
  - Environment variables `HILCLAW_DATA_REPO_URL` and `HILCLAW_DATA_REPO_LOCAL_PATH`: the key path in upper case with the package prefix. **Naming differs from the task's wording**: the Python constants holding these names are `ENV_URL` and `ENV_LOCAL_PATH` (the task allows renaming).
  - An empty variable counts as not set: the shell convention, `VAR= cmd` must not blank a value.
  - Relative `local_path` from the file resolves against the config file's directory (independent of the working directory); from the environment against the working directory (what a shell user expects).
  - `~` is expanded with `os.path.expanduser` for both sources; a `~` that cannot be expanded is left as it is and treated as a relative path (what `expanduser` does; not pinned by a test).
  - The result is made absolute and normalised with `os.path.abspath`: no symbolic link resolved, the path need not exist; no existence check (the caller decides what a missing checkout means).
  - `url` is returned as given, checked only for "non-empty string": https, ssh and a local path are all valid remotes.
  - Unknown keys at both levels are ignored: later sections must not break an older loader (NFR-7 ①).
  - `ConfigError(ValueError)` for every problem, chained to the underlying error where there is one; the message starts with the file path and names the key (`data_repo.url`, `data_repo.local_path`); file-level problems are told apart as "cannot read", "not valid UTF-8", "not valid JSON".
  - Strict UTF-8: a file starting with a byte order mark is rejected ("not valid JSON: Unexpected UTF-8 BOM"), pinned by one test.
  - A value in the file that is not a non-empty string is an error **even when the environment overrides it**: the file is shared and wrong either way, and an override on one machine must not hide it. An absent key is acceptable when its variable supplies the value. Pinned by `test_malformed_file_value_is_an_error_even_when_overridden`.
- Known limits: `RecursionError` from a pathologically nested JSON document is not converted to `ConfigError`; a non-string value in a caller-supplied `environ` mapping is not checked.
- Local verification (CPython 3.14.4 on Windows, ruff 0.16.10, pytest 9.1.1):
  - Before the first commit: `python -m pytest` -> `539 passed`; `python -m ruff check .` -> `All checks passed!`; `python -m ruff format --check .` -> clean.
  - Before the merge (head `79b1489`, `origin/main` at `32605aa`): `541 passed` (73 in `tests/test_config.py`, 468 existing); `All checks passed!`; `39 files already formatted`; `git ls-files --eol` -> `i/lf w/lf` for all three files; the `json.load` one-liner succeeds; `git status --short` empty after the test run; `git diff origin/main --stat` -> only the three `touchesFiles`.
  - After the merge, on main `6448177`: `541 passed`; clean tree; `main` == `origin/main`.
- Reachability check: `python -m trace --count --missing --coverdir <dir outside the repository> --module pytest tests/test_config.py` marks **no** line of `hilclaw/config.py` as missing. Run on `d53a72b` and on the `e3e1964` code; `79b1489` changed only a test expectation.
- CI on the PR (`pull_request`), four checks each (`Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`), all success:
  - `d53a72b`: green on the reviewed head per the round 1 reviewer (run URL not recorded).
  - `e3e1964`: https://github.com/myungjoo/HIL-Claw/actions/runs/37449938641
  - `79b1489` (final head): https://github.com/myungjoo/HIL-Claw/actions/runs/37450151248, and again after the reopen: https://github.com/myungjoo/HIL-Claw/actions/runs/37450404380
- Merge: `DONOTMERGE` removed, PR marked ready, the four checks of `79b1489` confirmed successful, then `gh pr merge 22 --squash --body-file` with the PR body.
- `push` run on `main` after the merge (`6448177`): https://github.com/myungjoo/HIL-Claw/actions/runs/37450494664 — `completed` / `success` (the driver re-checked the conclusion before the wrap-up).
- Follow-ups: unchanged from `## Follow-ups`. Additions: (a) decision to revisit — accept a UTF-8 BOM (`utf-8-sig`) if Windows editors make the strict rule a nuisance; (b) decision to revisit — whether an unexpandable `~` should be an error instead of a relative segment; (c) minor — convert `RecursionError` to `ConfigError` if the file ever comes from an untrusted source; (d) `REPO_ROOT` is now defined in both `driver_state.py` and `config.py`; share it when a third module needs it; (e) executor procedure — keep branch deletion out of any command line that also contains the merge, so that a failed step cannot reach it.
