---
id: T-0054
title: Add the data-root source of ADR-0015 decision 3 (hilclaw/data_root_source.py - the source of the fronts over hilclaw.config.load_data_repo() and the function that asks a source at a call and raises no_data_root), let default_registry take the source its tools are bound to, and let the two fronts pass the configured source
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, FR-13, OD-18, NFR-6, C-3, "#5 A-1", "#5 A-12"]
dependsOn: [T-0012, T-0038, T-0039, T-0052, T-0053]
touchesFiles: [hilclaw/data_root_source.py, hilclaw/tools.py, hilclaw/__main__.py, hilclaw/mcp_front.py, tests/test_data_root_source.py, tests/test_tools.py, tests/test___main__.py, tests/test_mcp_front.py]
estimatedSize: {loc: 90, files: 4}   # non-test: about 60 lines in the new module, 15 in tools.py, 5 in each front; the four test files are excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0015 decision 3); closes no OD, writes no ADR, standard library only, registers no tool, names no member of a data-plane file
---
## Why
ADR-0015 (landed as `86ba32b`, T-0052) fixed the frame every FR-10 tool contract shares. Its Consequences name three code slices. Slice ① landed with T-0053 (`f3e22f1`). **This task is slice ②**: "the data-root source, with `no_data_root`".

Today:
- `tools.call(registry, name, request)` hands a tool function the request only, and nothing in `hilclaw/` calls `hilclaw.config.load_data_repo()`: no tool function has a way to the data root. ADR-0015 decision 3: "**A tool function that needs the data plane is bound, when the registry is built, to a data-root source**: a callable without arguments that returns the data root or fails. In the two fronts of the package the source is the existing loader, `hilclaw.config.load_data_repo()` … a test builds a registry bound to a source of its own."
- `hilclaw.tools.KIND_NO_DATA_ROOT` exists as a name (T-0053) and nothing raises it. ADR-0015 Consequences: "Today a data root that is no directory would reach a caller as `tool_crashed`." Decision 3: "**When the source fails, or what it names is not an existing directory, the call is a tool failure of the reserved kind `no_data_root`**, raised before anything is read or written."
- `hilclaw.tools.default_registry()` takes nothing, so the first tool that needs the data plane would have to change the registry builder and both fronts together with its own contract.

This task ticks **no PLAN checkbox**: P1-1 stays open (the journaled path, a tool, the mock backend and the conformance tests remain). `default_registry` keeps returning an empty registry.

The judgement T-0053 `## Follow-ups` asked for (planner, 2026-10-08 UTC):
- **A code task, with no record and no owner question first.** ADR-0015 decision 3 states: "How the binding is written and which module builds the bound registry are the code task's." Both are therefore choices of this task, provisional, to be stated with one line of reason each. No OD is closed and no owner-only item (DRIVER §9) is touched.
- **Which module builds the bound registry** (planner's cut; the reviewer is asked to re-check it): `hilclaw.tools.default_registry` stays the one place where the fixed tool set is built and takes the source as its parameter; **each front passes the configured source** when it builds the default registry. Reasons: (a) `hilclaw/tools.py` keeps the docstring sentence "Nothing here … reads configuration" and imports neither `hilclaw.config` nor the new module, so no import cycle arises (`hilclaw/journaled_step.py` and every later tool module import `tools`); (b) it is the literal form of "In the two fronts of the package the source is the existing loader"; (c) a front hands over a callable and does not run it, so it holds no check and no way to fail of its own (ADR-0015 decision 3 "How this reads ADR-0010"; ADR-0010 decision 3).
- **Whether a test-only tool is enough**: yes. ADR-0015 decision 6 lists "that a failing data-root source is `no_data_root`" among what the frame alone lets a test check, and Consequences name "a test-only tool" for slice ③ in the same way. No tool of the package is defined, so no contract is invented. The test-only tools live in the test files.

How the slice is cut (DRIVER §5 and §6):
- A new module `hilclaw/data_root_source.py` (the name avoids the parameter name `data_root` that most modules use). `hilclaw/tools.py` is touched for `default_registry` and docstring sentences only; each front for the one line that builds the default registry and one docstring sentence.
- Slice ③ (the path of a journaled tool over `hilclaw/journaled_step.py`, the common request members `run_id` / `round` / `candidate` / `attempt` / `execution` as code) is **not** in this task.

Why this item now (judged from the files):
- P0.5-3 is BLOCKED on HQ-0003 (T-0014). The verification half of P1-3 (T-0036), P1-4 and the "harness pass" half of P0.5-1 wait for HQ-0004. Both are unanswered on #5. The rest of P0.5-4 is the owner's hook registration. P1-5 slice 3 needs owner values; the rest of P1-8 hangs on OD-3 (owner-only), OD-20, OD-23, OD-29.
- T-0053 `## Follow-ups` and the journal of 2026-10-08 name this slice as the next one. No open PR and no TODO / INTERRUPTED task file at planning time. The latest comment on #5 is the ADR-0015 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6040392389); no objection to ADR-0001..0015.

A-13 check (planner's reading — the reviewer is asked to re-check it):
- "데이터 plane 스키마 변경(STATE/spec/eval/artifacts)": none. The source is part of the interface between layer 1 and layer 2 (ADR-0015 Consequences "A-13 reading"); no data-plane file is read, written or named. `hilclaw.config.json` and its loader are unchanged.
- No new external dependency: standard library only; `pyproject.toml` unchanged.
- No tool, backend, hook, gate, roster or isolation means is decided (ADR-0015 Boundaries).

Known risk, accepted: ADR-0015 and ADR-0010 are inside their objection windows (until 2026-10-14). Code slices were carried out inside such windows before (T-0038, T-0047, T-0050, T-0051, T-0053). An objection creates a reverting task and this change is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (the driver's `PROCESS/STATE.json` — never touch it), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md** — Status (lines 5-10), Context "The data root" (16), decision 1 (33-37), decision 2 the refused request and the table of reserved kinds (45-53), **decision 3 (58-65), every sentence**, decision 5 first bullet (85; slice ③, read only to keep out of it), the Walk-through rows "The request is checked" and "The data root" (100-101), decision 6 (108-110), decision 7 "Two environments" and "A tool that does not use the frame" (118-119), Alternatives rows of point 3 (130-134), Consequences (144-145, 148), Boundaries (150-159)
- ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md — decision 2 (a tool function takes one request), decision 3 (a front holds no tool logic, text, check or default), decision 4 (result or tool failure; the answers of each front), decision 5 (the data root and the loader; the two variables), decision 7 (no state kept between calls)
- **`hilclaw/config.py` — the whole file (89 lines)**: `REPO_ROOT`, `DEFAULT_CONFIG_PATH`, `ENV_URL`, `ENV_LOCAL_PATH`, `DataRepo`, `ConfigError`, `load_data_repo` (what it raises, that `local_path` is an absolute `Path`, that it does not check that the checkout exists)
- **`hilclaw/tools.py` — the whole file (273 lines)**: the module docstring (lines 16-18), `KIND_NO_DATA_ROOT` (29), `ToolFailure`, `Registry`, `default_registry` (165-171), `call` (247-273)
- `hilclaw/__main__.py` (100 lines: `_outcome`, the docstring and line 80 of `main`); `hilclaw/mcp_front.py` (`_list`, `_call`, the docstring and line 215 of `main`)
- `hilclaw/cas.py` lines 96-100, `hilclaw/artifacts.py` lines 259-263 (how the modules below check a `data_root` their caller gives — unchanged by this task)
- **`tests/test_tools.py`** (the helpers at the top, `test_default_registry_is_empty_and_not_shared` at 461-466); **`tests/test___main__.py`** (`HELPER_SCRIPT` at 25-45, `registry_with`, `run`, `error_of`, the child-process helpers at 400-445 and the `test_process_*` cases); **`tests/test_mcp_front.py`** (`HELPER_SCRIPT` at 37-51, `registry_with`, the session helpers, line 454, the child-process helper near 944 and the `test_process_*` cases); `tests/test_config.py` lines 40-60 (how the committed file and the variables are tested)
- PROCESS/tasks/T-0053-tool-definition-reserved-kinds.md `## Result` (the public API as landed — this task is written against it) and `## Follow-ups`; PROCESS/tasks/T-0052-adr-od18-tool-contract-frame.md `## Result`
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` — five checks run on a PR; the job `Test presence (hilclaw)` requires `tests/test_data_root_source.py` for `hilclaw/data_root_source.py`
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6040392389 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0015 or ADR-0010 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0015 decision 3 fixes what a data-root source is, which source the fronts use, when it is asked, that its answer is not kept, and when a call is `no_data_root`. The names of the new public objects, how the binding is written, and the cases the record does not mention are **this task's choices, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and a record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/data_root_source.py` (new): the source of the fronts and the function that asks a source. About 60 lines with its docstrings.
- `hilclaw/tools.py` (edited): `default_registry` and docstring sentences. About 15 changed lines.
- `hilclaw/__main__.py`, `hilclaw/mcp_front.py` (edited): the line of `main` that builds the default registry, one import and one docstring sentence each. About 5 changed lines each. **No other change of behaviour of a front.**
- `tests/test_data_root_source.py` (new), `tests/test_tools.py`, `tests/test___main__.py`, `tests/test_mcp_front.py` (edited).
- Python, because the modules it joins are Python — one line in the commit body and `## Result`.
- Nothing else. `hilclaw/config.py`, `hilclaw/journaled_step.py`, every other module, `hilclaw.config.json`, `pyproject.toml`, `.github/`, every ADR stay as they are.

### The source of the fronts (`hilclaw/data_root_source.py`)
- A callable without arguments that returns the data root as the existing loader gives it: `hilclaw.config.load_data_repo().local_path`, with the default configuration file and `os.environ` — "with the configuration file and the two variables as they are". Recommended name: `configured`.
- It reads the configuration **at each call** and keeps nothing: no module-level value, no cache, no memoising decorator.
- It adds nothing to the loader: no default path, no further variable, no fallback when the loader fails (what the loader raises leaves it unchanged), no check that the directory exists (that is the next function's).

### Asking a source (`hilclaw/data_root_source.py`)
- One public function that a tool function calls when it needs the data root. Recommended: `obtain(source)`, returning a `pathlib.Path`.
- It calls `source` exactly once per call of itself and keeps nothing between calls.
- It returns the data root when the source returned a path that names an existing directory.
- It raises `hilclaw.tools.ToolFailure` of kind `hilclaw.tools.KIND_NO_DATA_ROOT` when **the source fails** or when **what it names is not an existing directory**: a missing path, a file. The message says which of the two happened and carries the reason or the path; the failure is chained to its cause where there is one. Nothing is created, read or written: the function touches the file system only to ask whether the path is a directory.
- It decides nothing else of the data plane: no `runs/`, no `blobs/`, no check that the directory is a git checkout or the data repository.

### The bound registry (`hilclaw/tools.py`, the two fronts)
- `default_registry` takes the data-root source to which every tool of the fixed set that needs the data plane is bound when the registry is built. Recommended signature: `default_registry(data_root_source)`, one required parameter with **no default** (a default would name the loader in `hilclaw/tools.py`); a value that is not callable raises `TypeError`.
- The set stays empty. **Building the registry never calls the source**, and neither does `names()`, `get()`, `definition()` or a call of an unknown name: "a tool that needs none never asks, and listing the tools or answering an unknown name never asks either".
- `hilclaw/tools.py` imports neither `hilclaw.config` nor `hilclaw.data_root_source`; "Nothing here keeps state between calls, reads configuration or the data plane" stays true.
- Each front builds its default registry with the source of the fronts: `tools.default_registry(data_root_source.configured)` where `tools.default_registry()` stands today (`hilclaw/__main__.py` line 80, `hilclaw/mcp_front.py` line 215). A `registry` handed to `main` is used as it is, as today.
- **A front does not call the source and does not catch `no_data_root` in a way of its own**: a `no_data_root` reaches the caller as every tool failure of a call does (exit status 3 with the error object on the command line; a text block with `isError` true from the MCP front). No new kind, exit status or JSON-RPC code is added to a front.
- How the binding is written is this task's choice. Recommended, and what the tests show: no wrapper around a tool function — a tool function is built with the source in reach (a closure or a `functools.partial`) and calls the function above itself, **after** it has checked its request. A wrapper that asked the source before the tool function ran would break "A tool function refuses before it asks for the data root" (decision 2) and is not acceptable.

### Docstrings (replace sentences; do not add paragraphs; no multi-line comments — CLAUDE.md "코멘트 최소화")
- `hilclaw/data_root_source.py`: a module docstring naming ADR-0015 decision 3 and saying, in few sentences, what a data-root source is, that it is asked at each call that needs the data root and its answer is not kept, and that the data root is never a member of a request. Public functions get a docstring with what they return and raise.
- `hilclaw/tools.py`: the docstring of `default_registry` says what the parameter is and that building does not call it; the sentence "The set is empty. A tool is added here, in the source, and in no other way …" stays true and stays.
- `hilclaw/__main__.py` and `hilclaw/mcp_front.py`: the sentence of `main` "``registry`` defaults to :func:`hilclaw.tools.default_registry`" is made true (the default registry is bound to the configured data root).

### Cases the record leaves to this task — choose, implement, test and list each with one line of reason
- The names of the module's public objects; whether the source of the fronts is a function or another callable.
- Which exceptions of a source count as "the source fails". Recommended: every `Exception` (`hilclaw.config.ConfigError` is one; a source of a test may raise anything), while a `BaseException` that is no `Exception` (`KeyboardInterrupt`, `SystemExit`) passes through. Whether a `ToolFailure` raised by a source passes through or becomes `no_data_root` (recommended: `no_data_root` — the record gives a failing source one kind).
- What a source may return. Recommended: a `str` or an `os.PathLike` naming a path; anything else (`None`, `bytes`, a number, a `DataRepo`) is `no_data_root`. **An empty `str` must not be read as the current directory** (`Path("")` is `.`): recommended `no_data_root`.
- A relative path returned by a source of a test (the loader returns an absolute one). Recommended: used as it is, not resolved.
- A symbolic link to a directory (recommended: an existing directory, as `Path.is_dir` answers) and a path the platform cannot ask about (an embedded NUL; recommended: `no_data_root`).
- A `source` that is not callable handed to the asking function (recommended: `TypeError`, a defect of the caller, not `no_data_root`).
- Whether the message of `no_data_root` repeats the text of a `ConfigError` (recommended: yes — it names the file and the key, which is what the caller must correct).
- Anything else you meet. If you read one as a rule of a tool's contract, of the journaled path, of a backend or of a hook that no record states, do not decide it: keep today's behaviour, or return BLOCKED with the exact question.

### Tests (excluded from the size cap)
Helpers and test-only tools live in the test files and get no tests of their own (test rule ⑤). Synthetic values only, temporary directories of pytest (`tmp_path`), placeholder tool names as the existing tests use them (`test.root` and the like); **no member of a real tool is invented**. The tests pass on Linux (CI) and on Windows (the driver's clone): a case that needs a symbolic link is skipped where one cannot be made. **No test reads or writes the real data repository**: a case that goes through the loader sets `HILCLAW_DATA_REPO_LOCAL_PATH` (and, for a failing configuration, replaces `hilclaw.config.DEFAULT_CONFIG_PATH` with `monkeypatch`, or sets the variable to a missing path).

A test-only tool of the form the criteria recommend is the vehicle: built with a source, it refuses a request that carries a marker member with `invalid_request` **before** it asks, otherwise asks for the data root and returns something read from it (for example the sorted names of its entries).

`tests/test_data_root_source.py` (new):
- happy: the asking function returns the directory a source names, for a `str` and for a `Path`; the source of the fronts returns exactly `load_data_repo().local_path` under a set `HILCLAW_DATA_REPO_LOCAL_PATH`, and the committed configuration file is read through the default path; a tool bound to a source returns the same result through `tools.call`, through `hilclaw.__main__.main` and through `hilclaw.mcp_front.main` (in-memory streams, a registry of the test).
- branch: the source is called once per call that needs it and never when the registry is built, when the tools are listed (`tools/list`), when an unknown name is called through either front, or when the tool refuses its request (`invalid_request`, counter still 0); **the answer is not kept** — a source that names another directory at its second call makes the second call answer from the other tree, in one MCP session (two `tools/call` lines) and through `tools.call`; the source of the fronts follows a change of `HILCLAW_DATA_REPO_LOCAL_PATH` between two calls in one process; a tool that needs no data root works with a source that always fails.
- error / negative (assert the kind `no_data_root`, a part of the message, and that nothing was created under the temporary directory): a source that raises (`ConfigError`, `OSError`, `RuntimeError`, and a `ToolFailure` as you chose); a path that does not exist; a path that is a file; an empty `str`; a returned value of another type (`None`, `bytes`, an `int`); the configured source with a missing configuration file, with a file that is not JSON and with `HILCLAW_DATA_REPO_LOCAL_PATH` naming a missing directory; a `KeyboardInterrupt` out of a source passes through; a `source` that is not callable as you chose. Through the fronts: the same failing source gives exit status 3 and `{"error": {"kind": "no_data_root", …}}` on the command line and a text block with the same error object and `isError` true from the MCP front (negative for "the failure arrives as `tool_crashed`" and for "a front answers it in its own way").
- child process (as `tests/test___main__.py` and `tests/test_mcp_front.py` do it, with a helper script that registers the test-only tool bound to the source of the fronts): with `HILCLAW_DATA_REPO_LOCAL_PATH` naming a temporary directory the call answers from it through **both** fronts and the two outcomes are equal; with the variable naming a missing directory both answer `no_data_root`.

Existing tests:
- `tests/test_tools.py`: `test_default_registry_is_empty_and_not_shared` passes a source; new cases for a source that is not callable and for "building does not call the source". `tests/test_mcp_front.py` line 454 passes a source.
- `tests/test___main__.py` and `tests/test_mcp_front.py`: one new case each showing that `main` **without** a `registry` (the default one) still answers an unknown tool, and lists no tool, while the configuration cannot be read (`DEFAULT_CONFIG_PATH` replaced by a missing file) — the front asked no source. The existing `test_process_*` cases that run `python -m hilclaw` and `python -m hilclaw.mcp_front` stay as they are and keep passing.
- Any other existing test whose expectation changes is named with the reason in the PR body; no assertion is weakened.

Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003; **install nothing**), so check that the tests reach every line of the new module and every changed line of the three others, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/test_data_root_source.py tests/test_tools.py tests/test___main__.py tests/test_mcp_front.py`, and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public function of the touched modules keeps its tests and every new public name gets one; ④ the new module has its test file `tests/test_data_root_source.py`; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (record pass and skip counts before and after; 5175 passed and 146 skipped on `84ea4b1`), `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- `git grep -n -E "load_data_repo|hilclaw.config|import config" -- hilclaw/` shows the loader used in `hilclaw/data_root_source.py` only (beside `hilclaw/config.py` itself); `git grep -n "default_registry()" -- hilclaw/ tests/` has no match; `git ls-files --eol` shows `i/lf` for the new and changed files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only files of `touchesFiles`. Record the line counts of the four modules after the change.
- CI on the PR: `gh pr checks <PR> --watch` ends with **five** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0054'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0054 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching a file of `touchesFiles` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0054-data-root-source` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0054`; executor commits end with the trailer `Task: T-0054`.
- Install nothing. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Ask the reviewer explicitly to (a) compare the code with ADR-0015 decision 3 sentence by sentence — the data root is no member of a request, the source is a callable without arguments, the fronts use the existing loader with the file and the two variables as they are, the source is asked at each call that needs it and its answer is not kept, a failing source or a path that is no existing directory is `no_data_root` before anything is read or written, listing and an unknown name never ask; (b) confirm that no front runs the loader, holds a check or answers `no_data_root` in a way of its own (ADR-0010 decision 3), that nothing keeps state between calls (decision 7), that the test-only tool refuses before it asks (ADR-0015 decision 2), and that every other answer of the two fronts is as before; (c) re-check the planner's readings in `## Why` — a code task without a record, `default_registry` as the builder with the fronts passing the source, a test-only tool as a sufficient vehicle, A-13 "data-plane schema change" and "new dependency" not applying; (d) re-check each choice under "Cases the record leaves to this task"; (e) report anything the code decides that ADR-0015 lists under Boundaries or that belongs to slice ③ (a journaled path, a caller of `hilclaw.journaled_step.run`, a member name of a request, a tool of the package, a backend, a hook). If the reviewer reads a point as a design choice needing a record or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0054`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: what changed in one paragraph, the provisional choices with one line of reason each, the existing tests whose expectation changed, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the public API as landed (names and signatures — slice ③ and the first tool are written against it), the provisional choices, the changed tests, the verification outcomes, the line counts, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 90 non-test lines in 4 files; the cap is 300 LOC / 5 files (tests excluded). If the change cannot be made without touching another `hilclaw/` file, do not widen the task: finish what fits, or return BLOCKED with the reason, and propose the split in `## Follow-ups` (DRIVER §5).
- If ADR-0015 turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the choices above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Slice ③: the path of a journaled tool, any caller of `hilclaw.journaled_step.run`, the common member names of a request (`run_id`, `round`, `candidate`, `attempt`, `execution`) as code, any change to `hilclaw/journaled_step.py`.
- Any tool of the package, its description or its schema; a non-empty `default_registry`; the mock backend; backends; conformance tests of a registered tool.
- Any change to `hilclaw/config.py`, to `hilclaw.config.json`, to the two variables or a third one; a check that the data root is a git checkout or holds a given layout; creating the directory; a cache of the data root; the data root as a member of a request or as a second argument of a tool function or of `tools.call`.
- Enforcement that a tool function refuses before it asks, or that it asks at all (ADR-0015 decision 7: not detected by the frame); a check of a request against a schema.
- A new kind, exit status or JSON-RPC code of a front; a way for the command line to show a description or a schema; the `RecursionError` of `tools/list` on a deeply nested schema (T-0053 Follow-ups).
- Hooks, gates (OD-3, owner-only), budget checks (OD-19), the roster (OD-23), the isolation means, registration of the MCP server (`.mcp.json`), the live check of the MCP front (OD-18 sub-question ①).
- Any edit of an ADR (the sentences ADR-0015 lists as "now less exact" are the integrator's, after the objection window), the OD register, OpenDecisionProposals, StandardScenarios, CLAUDE.md, DRIVER.md, PLAN.md, `pyproject.toml`, `.github/`, `.claude/`, `README.md`; any change to the `HIL-Claw-data` repository.
- Answering HQ-0003 or HQ-0004 on the owner's behalf.

## Follow-ups
- (planner, next — code mode, P1-1 slice ③) The path of a journaled tool over `hilclaw/journaled_step.py` (ADR-0015 decisions 4 and 5): the request checked for `run_id`, `execution` and the three numbers, the data root asked through this task's function, the identity formed with the `step` of the tool's contract, the three states and the three death points checked through both fronts by a test-only tool; with it the sentence "It is not a tool and not a hook: nothing registers or calls it" and OD-18 sub-question ④. To judge then: whether it is written as one part applied at registration or in each tool function, and whether sub-question ④ needs a record first.
- (planner, then — §9 record with the first tool) What a backend is, how a tool selects one and what the mock backend injects.
- (open, small) Whether the command-line front gets a way to show the description and the schema of a tool; whether the MCP front should answer a `tools/list` that fails on a deeply nested schema (T-0053 Follow-ups).
- (unchanged) The rest of P1-8; the integrator items after 2026-10-14 (T-0040, T-0042, T-0046, T-0049 and T-0052 Follow-ups); OD-18 sub-questions ①, ③ and ⑤; the T-0047, T-0048, T-0050 and T-0051 follow-ups.

## Result
**DONE.** PR https://github.com/myungjoo/HIL-Claw/pull/47, squash commit `6d4e873` on `main` (branch `claude/T-0054-data-root-source`, final head `59459d5`, deleted remotely and locally after `MERGED`). This task ticks **no** PLAN checkbox; `default_registry` still returns an empty registry.

§3-5 check before starting: no commit with `Task: T-0054` on `origin/main`, no PR for T-0054, no open PR. No comment on #5 after the ADR-0015 notice (issuecomment-6040392389).

### Public API as landed
- `hilclaw/data_root_source.py` (new, 74 lines)
  - `configured()` -> `pathlib.Path`: `hilclaw.config.load_data_repo().local_path`, read from the default configuration file and `os.environ` at each call. Raises `hilclaw.config.ConfigError` as the loader does; no check that the directory exists; keeps nothing.
  - `obtain(source)` -> `pathlib.Path`: calls `source` once and returns the data root it names. Raises `hilclaw.tools.ToolFailure` of kind `hilclaw.tools.KIND_NO_DATA_ROOT` when the source raises an `Exception`, returns no path or an empty `str`, or names what is no existing directory. Raises `TypeError` when `source` is not callable. It touches the file system only through `os.path.isdir`.
  - Messages: `the data-root source failed: <Type>: <text>` (the type alone when the text cannot be formed), `the data-root source named no path: got <Type>`, `the data root is not an existing directory: <path>`.
- `hilclaw.tools.default_registry(data_root_source)`: one required parameter, no default; `TypeError` when it is not callable; building never calls it. `hilclaw/tools.py` imports neither `hilclaw.config` nor `hilclaw.data_root_source`.
- `hilclaw/__main__.py` and `hilclaw/mcp_front.py`: `main` without a `registry` builds `tools.default_registry(data_root_source.configured)`. A front never calls the source. No kind, exit status or JSON-RPC code was added; `no_data_root` arrives as every tool failure of a call does (exit status 3 / text block with `isError` true).
- How a tool is bound (shown by the test-only tool): the tool function is built with the source in reach (closure) and calls `obtain(source)` itself, after it has checked its request. There is no wrapper.

### Provisional choices (ADR-0015 decision 3 leaves them to the code task)
- `default_registry` stays the one builder and the fronts pass the source: `tools.py` keeps reading no configuration and no import cycle arises.
- No wrapper around a tool function: a refusal (`invalid_request`) still comes before the data root is asked (decision 2).
- Names `configured` and `obtain`; the source of the fronts is a plain function: nothing to hold between calls.
- Every `Exception` of a source is `no_data_root`, a `ToolFailure` raised by a source included: the record gives a failing source one kind. A `BaseException` that is no `Exception` passes through, as in `tools.call`.
- Chaining: the failure is chained to the error of the source. When the text of that error cannot be formed, it is chained to the error of forming the text, whose `__context__` is the error of the source.
- A source may return a `str` or an `os.PathLike` giving a `str`. Anything else (`None`, `bytes`, a number, a `DataRepo`, a path object that gives `bytes` or raises) and an empty `str` are `no_data_root`: an empty `str` must not be read as the current directory. The message names the type of the value only (no `repr`).
- A relative path is used as given, not resolved: the loader already returns an absolute one.
- A symbolic link to a directory counts as an existing directory and an embedded NUL does not, both as `os.path.isdir` answers.
- A `source` that is not callable is a `TypeError` from `obtain`: a defect of the tool's author.
- The message repeats the text of a `ConfigError`: it names the file and the key the caller must correct.
- No criterion disagreed with a record.

### Review (context-isolated `dev-reviewer`, 3 rounds)
- Round 1, head `cabf2b3`: **Approve** — https://github.com/myungjoo/HIL-Claw/pull/47#issuecomment-6051060690
  - Low 1: a returned path object whose `__fspath__` raises, or a value whose `repr` raises, arrived as `tool_crashed`. Fixed in `3010845`.
  - Low 2: no test failed when a front passed another source. One case per front added in `3010845`.
  - Info: absolute paths appear in the message. Kept, as stated in the PR body.
  - Response: https://github.com/myungjoo/HIL-Claw/pull/47#issuecomment-6051082686
- Round 2, head `3010845`: **Approve** — https://github.com/myungjoo/HIL-Claw/pull/47#issuecomment-6051125115
  - Low 1: a source error whose `__str__` raises arrived as `tool_crashed`. Fixed in `59459d5`.
  - Nit 1: a test call wrote to the real standard error. Fixed in `59459d5`.
  - Response: https://github.com/myungjoo/HIL-Claw/pull/47#issuecomment-6051147952
- Round 3, head `59459d5`: **Approve**, no finding and no nit — https://github.com/myungjoo/HIL-Claw/pull/47#issuecomment-6051185143
  - Info, no change asked: a source that returns a `str` subclass whose `__bool__` or `__format__` raises still arrives as `tool_crashed`.
- The reviewer agreed in every round with the planner's readings: a code task without a record, `default_registry` as the builder, a test-only tool as a sufficient vehicle, A-13 "data-plane schema change" and "new dependency" not applying. It found nothing of Boundaries or of slice 3 decided, and no security concern.

### Tests
- New `tests/test_data_root_source.py`: 64 cases plus 1 symbolic-link case that is skipped on Windows. It covers happy, branch, error and negative cases through `obtain`, `configured`, `tools.call`, both fronts in memory and child processes of both fronts.
- Existing tests whose expectation changed: `test_default_registry_is_empty_and_not_shared` (`tests/test_tools.py`) and `test_the_fixed_tool_set_is_empty_today` (`tests/test_mcp_front.py`) pass a source to `default_registry`. No assertion was weakened.
- New cases in existing files:
  - `tests/test_tools.py`: building and reading never call the source; a source that is not callable; the parameter has no default.
  - `tests/test___main__.py` and `tests/test_mcp_front.py`: the default registry is built with `data_root_source.configured`; it answers an unknown tool and lists no tool while the configuration cannot be read.
- Coverage: `python -m trace --count --missing --coverdir <outside the repository> --module pytest tests/test_data_root_source.py` shows no missing line in `hilclaw/data_root_source.py`. The changed lines of the three other modules were not measured; the new cases in their test files call them. Nothing was installed.

### Verification
- Local on the final head: `python -m pytest` 5251 passed, 147 skipped (before, on `84ea4b1`: 5175 passed, 146 skipped; the new skip is the symbolic-link case on Windows). `python -m ruff check .` and `python -m ruff format --check .` clean.
- `git grep -n -E "load_data_repo|hilclaw.config|import config" -- hilclaw/`: `hilclaw/data_root_source.py` only, beside `hilclaw/config.py`.
- `git grep -n "default_registry()" -- hilclaw/ tests/`: no match.
- `git ls-files --eol`: `i/lf` for the 8 files. `git status --short` after the tests: empty. The diff against `origin/main` lists only the 8 files of `touchesFiles`.
- Line counts after the change: `hilclaw/data_root_source.py` 74, `hilclaw/tools.py` 280, `hilclaw/__main__.py` 102, `hilclaw/mcp_front.py` 246. The four non-test files stay inside the cap.
- CI on the PR, final head `59459d5`: five successful checks — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)` — https://github.com/myungjoo/HIL-Claw/actions/runs/37719677212. No failed CI run on the PR.
- `push` run on `main` for `6d4e873`: `success` — https://github.com/myungjoo/HIL-Claw/actions/runs/37720002020.

Language: Python, because the modules it joins are Python.

### Follow-ups left
- (reviewer, with the first tool that needs the data plane) A child-process case through the **default** registry, showing that `python -m hilclaw` and `python -m hilclaw.mcp_front` answer from the configured directory and answer `no_data_root`. It cannot be written while the fixed set is empty.
- (info, no action asked) A source returning a `str` subclass whose `__bool__` or `__format__` raises is `tool_crashed`; only a source built on purpose can do it.
- (next, unchanged) Slice ③: the path of a journaled tool over `hilclaw/journaled_step.py`, asking the data root through `data_root_source.obtain`.
