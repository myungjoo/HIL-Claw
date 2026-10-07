---
id: T-0038
title: Add the tool registry, the tool-failure type and the command-line front of ADR-0010 (hilclaw/tools.py, hilclaw/__main__.py) with an empty fixed tool set, and their tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, NFR-6, C-3, C-7, "#5 A-12"]
dependsOn: [T-0037]
touchesFiles: [hilclaw/tools.py, hilclaw/__main__.py, tests/test_tools.py, tests/test___main__.py]
estimatedSize: {loc: 240, files: 2}   # non-test: two new modules; the two test files are excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0010 decisions 2, 3, 4, 7); closes no OD, writes no ADR, standard library only, names no data-plane field, registers no tool
---
## Why
**ADR-0010** (`acb0345`, T-0037) fixed how layer 1 calls a tool of the layer-2 package: a tool is defined once as a *tool function* (one JSON object in, one JSON object out, or a *tool failure*), all tool functions sit in one *registry*, and two *fronts* make the registry callable from outside the process — a stdio MCP server for agents and a command line for people, scripts and tests. Its Consequences split PLAN P1-1 into code slices: "① the registry, the tool failure type and the command-line front, with one tool that needs no undecided contract; ② the MCP front over the same registry; ③ the mock backend; ④ the conformance tests, run through both fronts; then one tool at a time".

**This task is slice ①.** Nothing of it exists: `hilclaw/` has library modules and two unrelated `python -m hilclaw.<module>` entries (`merge_guard`, `driver_state`), no registry and no `hilclaw/__main__.py`. It ticks **no PLAN checkbox** (P1-1 stays open until the contract, the mock backend and the conformance tests exist).

**Planner's reading on "one tool that needs no undecided contract" — the reviewer is asked to re-check it.** No such tool exists today, so this slice registers **none** and the fixed tool set of the package is empty:
- `sim.run`, `board.run`, `profiler.collect`, `correctness.check`: their arguments, result members and failure kinds are "each tool's" (ADR-0010 Boundaries; OD-10, OD-13, OD-23), and the verification half waits for HQ-0004.
- `blob.push`, `blob.fetch`: what a local push or fetch means on one machine is not decided (C-3 "MVP 로컬 구현, 백엔드는 #5 B-2 확정 후"; ADR-0004 and ADR-0005 Boundaries; T-0008 Out of Scope: "do not guess it here").
- A tool with a new name (a version or listing tool, for example) would decide "which tools exist beyond FR-10 and C-3", which ADR-0010 decision 4 leaves undecided.

The mechanism is therefore exercised by tool functions that the tests define and put into a registry of their own. If the executor or the reviewer finds a tool whose whole contract is fixed by a landed record, it is **not added here**: name it in `## Result` as a follow-up.

Why this item now (planner, 2026-10-07 UTC, judged from the files): P0.5-3 is BLOCKED on HQ-0003 (T-0014); the verification half of P1-3, P1-4 and the "harness pass" half of P0.5-1 wait for HQ-0004 (T-0036); the rest of P0.5-4 is the owner's hook registration; P1-5 slice 3 and the rest of P1-8 need owner values or OD-17. This slice needs neither owner answer nor an OD closure. No open PR at planning time. Last comment on #5: the ADR-0010 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6030526722).

A-13 check (planner's reading — the reviewer is asked to re-check): standard library only, `pyproject.toml` and `.github/` unchanged, so no new dependency; no data-plane file or field is read, written or named; the request / result convention is an interface between layer 1 and layer 2, not a data-plane schema (ADR-0010 Consequences). The module adds **no rule** to ADR-0010; module names, public names, exit status values, the `kind` values of front-level failures and the cases listed under "unsaid" are provisional conventions of the source.

Known risks, accepted: (1) ADR-0010, ADR-0004 and ADR-0006 are inside their objection windows (until 2026-10-14). (2) The driver clone runs on Windows: the command-line front must write LF, not CRLF, there too, and the tests must show it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md — the whole record**; in particular decisions 1 (terms), 2, 3 (the bullet "What keeps the two identical"), **4** (Names; Command-line front; "Result or tool failure"), 5, 7 (no version member; no kept state), 8, Consequences and Boundaries. The MCP-front paragraph of decision 4 is read to keep the shared level usable by slice ②; it is not implemented here
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md line 34 (a *name* matches `[a-z][a-z0-9_]{0,31}`); `hilclaw/keys.py` lines 34 and 170-173 (how the package checks a name; `keys.py` is not edited and its private names are not imported)
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `hilclaw/driver_state.py` lines 1-12 and 209-236 and `hilclaw/merge_guard.py` (module docstring, `main`) — the two existing command-line entries, as style for `main(argv=None)` returning the exit status; **not edited, and not tools**. `hilclaw/config.py` (`load_data_repo`; read for decision 5, not called here). `hilclaw/__init__.py` (not edited)
- `.github/workflows/ci.yml` — job `Test presence (hilclaw)`: every `hilclaw/*.py` except `__init__.py` needs `tests/test_<file name>`, so `hilclaw/__main__.py` needs `tests/test___main__.py` (three underscores after `test`); five checks run on a PR. `pyproject.toml` (no runtime dependency, no console script, `requires-python >= 3.11`); `.gitattributes`
- `tests/test_driver_state.py` or `tests/test_merge_guard.py` — how an existing `main` is tested (in process and through `sys.executable -m`); style to imitate, **not edited**
- PROCESS/tasks/T-0037-adr-od18-tool-exposure-form.md — `## Result` "Follow-ups" (the inputs of slice ① and ②) and "Provisional readings"; PROCESS/tasks/T-0032-timing-run-python-side.md `## Result` process note (d) (review rounds spent on wording)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6030526722. If the owner has objected to ADR-0010 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0010 fixes the rules. Names, shapes, values and the unsaid cases are **conventions chosen by this task, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and the ADR disagree, **the ADR wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/tools.py` (new; about 100-140 lines) — the level below the fronts: the tool-failure type, the registry, the fixed tool set (empty) and the checks on a request and a result that both fronts must share.
- `hilclaw/__main__.py` (new; about 70-100 lines) — the command-line front, `python -m hilclaw <tool name>`.
- `tests/test_tools.py`, `tests/test___main__.py` (new).
- Python, because the package and both existing entries are Python — one line in the commit body and `## Result`. If you judge other module names or another spelling of the command better (ADR-0010: "the spelling before the name is the code task's"), say why; the Test presence job must pass **without an edit of `.github/`**.
- Nothing else. `hilclaw/__init__.py`, `pyproject.toml`, `README.md` and every existing module and test stay as they are.

### Constraints
- **Standard library only**; runs on CPython 3.11 and 3.14, on POSIX and on Windows.
- **A front holds no tool logic** (decision 3): everything that decides whether a value is a request or a result, and the conversion of what a tool function raises, lives in `hilclaw/tools.py` so that the MCP front of slice ② can use the same code. `__main__.py` only reads, decodes, looks up, calls and encodes.
- **No tool is registered** and **no way to add one from outside the source exists**: no environment variable, option, entry point, plugin directory or import-by-name that puts a function into the registry of the package (#5 A-12 point 3: the set is fixed; ADR-0010 decision 8: a front authenticates nobody). Tests reach the mechanism by passing their own registry to the functions.
- **No kept state** between calls beyond the registry itself (decision 7).
- The front in this slice **does not call `hilclaw.config.load_data_repo()`** and reads no configuration: no tool needs a data root yet. How the data root reaches a tool function (decision 5: "the front is that caller") is left to the first slice that registers a tool that needs one — do not choose it here; list it as a follow-up.
- No time limit, no size limit, no retry, no budget, gate, duplicate or concurrency check, no event append, no hook (decision 8 and Boundaries).
- A tool function never writes to standard output (decision 4); the modules of this task print nothing but what the front writes.

### Capabilities of `hilclaw/tools.py` (provisional names; each must exist and every public name must be tested)
1. **Tool failure**: an exception type, for example `ToolFailure(kind, message)`, with `kind` a *name* of ADR-0001 and `message` a `str`; constructing one with anything else raises `TypeError` / `ValueError` (say which). A function gives the error object of decision 4: `{"error": {"kind": ..., "message": ...}}`, exactly these members.
2. **Registry**: a table from tool name to tool function, for example a class `Registry` with `register(name, function)`, `get(name)` and `names()`. A name is checked when it is registered (recommended: `str` of lowercase words joined by single `.`, no `_`, since decision 4 says a name containing `_` reopens the MCP mapping — say what you chose and why); a function must be callable; registering a name twice raises. Looking up an unknown name raises a lookup error of its own type (for example `UnknownToolError(LookupError)`) — **not** a `ToolFailure`: decision 4 lets each front answer an unknown name in its own way.
3. **The fixed tool set**: one function, for example `default_registry()`, returns the registry of the package. It is **empty** in this slice; its docstring says that tools are added in the source only.
4. **One call**: for example `call(registry, name, request) -> dict`. It looks the name up, checks that `request` is a request, calls the tool function with it, and checks that what comes back is a result. A **request** and a **result** are each one JSON object in the strict sense of decision 2: a `dict` with `str` member names whose values are, recursively, `dict`, `list`, `str`, `int`, finite `float`, `bool` or `None`. A request that is not one is refused before the tool function is called (an error type of the shared level that a front turns into its own answer). What the tool function raises: a `ToolFailure` passes through unchanged; see "unsaid" for anything else and for a return value that is not a result.
5. A public way to check or encode a value as strict JSON that both fronts can share is welcome if it keeps `__main__.py` free of logic; do not build more than this slice uses.

### Capabilities of `hilclaw/__main__.py`
6. `main(argv=None, *, registry=None, stdin=None, stdout=None, stderr=None) -> int` (shape provisional): the exit status is returned, not raised; `registry=None` means `tools.default_registry()`; the stream arguments exist so that tests run in process, and default to the **binary** standard streams. `if __name__ == "__main__": raise SystemExit(main())`.
7. **Request** (decision 4): the tool name is the only argument; standard input is read to its end as bytes, decoded as UTF-8 and parsed as exactly one JSON object. `NaN`, `Infinity` and `-Infinity` are refused (strict JSON).
8. **Result**: exit status 0 and standard output holds exactly one JSON object and one LF (`b"\n"`, never `b"\r\n"`, also on Windows — write bytes).
9. **Tool failure**: a non-zero exit status and standard output holds the error object of capability 1 and one LF. The same form reports what never reached a tool function: an unknown tool name, a standard input that is not one JSON object, a wrong number of arguments. Standard output is never empty and never holds anything else when `main` returns.
10. **Standard error**: free text for a reader (recommended: one line saying what failed); nothing parses it and the tests assert at most that it is non-empty on a failure.

### Cases the record leaves unsaid — choose, implement, test and list each with one line of reason
- The non-zero exit status values (recommended: one value for a `ToolFailure` raised by a tool function and another for what the front answered by itself; avoid colliding by accident with the interpreter's own 1 for an uncaught exception if you can say why it matters, or say why it does not).
- The `kind` values the front and the shared level use for: unknown tool, input not a request (not UTF-8, not JSON, not an object, a non-finite number), wrong argument count, a tool function that raised something other than `ToolFailure`, a tool function that returned something that is not a result. These are kinds of the front, not a list for tools (decision 4 fixes "no list of kinds").
- **A tool function that raises something other than `ToolFailure`**, or returns a non-result: the call established no outcome, and decision 4 allows an empty standard output only when the front could not report at all — so it is reported as a tool failure (recommended: converted in `tools.call`, the original exception chained and its text in `message`; `KeyboardInterrupt` and `SystemExit` are not caught).
- No argument, more than one argument, an argument that looks like an option (`-h`, `--help`): there is no help output on standard output with status 0, because status 0 means a result (recommended: no `argparse`, or `argparse` only if it can be kept from writing to standard output and from exiting).
- An empty standard input; a UTF-8 byte order mark; duplicate member names in the request (recommended: refuse duplicates, since "one JSON object" with two values for one name has no single meaning — or accept the last and say so); trailing whitespace or a second JSON value after the object; a very deeply nested input (`RecursionError`).
- The form of the output line: compact or indented (one line recommended), member order, `ensure_ascii` or raw UTF-8.
- Whether `tools.call` copies the request before handing it over, and whether a tool function may return the request object itself.
- A `bool` / `int` subclass, a `tuple`, or a non-`str` member name in a result (recommended: exact types as `json.loads` returns them, as `hilclaw/artifacts.py` states for its file).
- Writing to a closed standard output (`BrokenPipeError`).
- Anything else you meet. If you read one as a design choice that needs an ADR or the owner — in particular anything that would fix a rule for **tools** rather than for this front — return BLOCKED with the exact question.

### Tests (excluded from the size cap)
Tool functions used by the tests are defined in the test files and registered in a registry the test builds; they are test helpers and get no tests of their own (test rule ⑤). All tests must pass on Windows and on POSIX.
- `tests/test_tools.py`
  - happy: register and look up; `names()`; `call` hands the request to the function and returns its result; nested objects, arrays, `null`, booleans, integers, finite floats and non-ASCII strings pass in both directions; `default_registry()` is a registry with no name, and two calls of it do not share additions made to one of them (or say why they do).
  - branch: `ToolFailure` passes through `call` with its `kind` and `message`; the error object has exactly the two members; an empty request `{}` and an empty result `{}` are valid.
  - error / negative: unknown name → the lookup error, the function of another name not called; duplicate registration; a name that breaks the chosen rule (empty, upper case, containing `_`, a space, a leading or trailing `.`, not a `str`); a function that is not callable; a request that is a list, a string, `None`, holds `float("nan")` / `float("inf")`, a non-`str` member name, a `bytes`, a `set` or an object of another class at depth → refused and **the tool function not called**; a result with each of the same defects → the chosen tool failure; a function that raises `ValueError`, `OSError` and a custom exception → the chosen tool failure, the original chained; `ToolFailure` built with a `kind` that is not a name (`""`, `"Bad"`, `"a.b"`, 33 characters, not a `str`) or a `message` that is not a `str`.
- `tests/test___main__.py`
  - happy (in process, streams injected as `io.BytesIO`): a registered echo-like tool → status 0, standard output is exactly `json` of the result plus `b"\n"`, parses back to the expected object, standard error empty or free; a non-ASCII request round-trips.
  - branch: a tool that raises `ToolFailure` → the chosen status and the error object with that `kind` and `message`; `registry=None` uses the fixed set (every FR-10 / C-3 name — `sim.run`, `board.run`, `profiler.collect`, `correctness.check`, `blob.push`, `blob.fetch` — is unknown today and reported as such; write this test so that it states the reading, since it must change when the first tool lands).
  - error / negative (each: non-zero status, standard output is exactly one error object and one LF, nothing else): unknown tool; no argument; two arguments; `--help`; empty input; input that is not UTF-8; not JSON; a JSON array, string, number and `null`; `NaN` and `Infinity`; the duplicate-member and trailing-data cases as chosen; a tool that raises a non-`ToolFailure`; a tool that returns a non-result; a tool that returns `float("nan")`.
  - through a real process (`subprocess.run([sys.executable, "-m", "hilclaw", ...], input=...)` from the repository root): an unknown tool and a malformed input give the error object, a non-zero status and bytes on standard output that end in `b"\n"` and contain no `b"\r"`; and one happy path — the test writes a small script into `tmp_path` that builds a registry with one tool and calls `hilclaw.__main__.main(registry=...)`, runs it with `sys.executable`, and checks status 0 and the exact bytes (this is the only way to see the default binary streams and the LF on Windows; the script is a test helper).
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003), so check that the in-process tests reach every line of the two new modules except the `if __name__ == "__main__"` line, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/test_tools.py tests/test___main__.py`, and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public name of both modules is tested; ④ each new module has its test file; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge: `python -m pytest` exits 0 (record pass and skip counts), `python -m ruff check .` and `python -m ruff format --check .` exit 0 (ruff 0.16.10, pytest 9.1.1). By hand once, from the repository root: `echo {} | python -m hilclaw sim.run` prints one error-object line and exits non-zero; record the line and the status.
- `git ls-files --eol` shows `i/lf` for the changed files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only the files in `touchesFiles`.
- CI on the PR: `gh pr checks <PR> --watch` ends with **five** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, check the `push` run on `main` and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- First the §3-5 landed check: `git log origin/main --grep='^Task: T-0038'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0038 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching `hilclaw/tools.py`, `hilclaw/__main__.py` or their test files is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0038-tool-registry-command-line-front` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0038`; executor commits end with the trailer `Task: T-0038`.
- Install nothing. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Keep docstrings exact and short so that rounds are not spent on wording (T-0032 process note (d)). Ask the reviewer explicitly to (a) compare the two modules with ADR-0010 decisions 2, 3, 4 and 7 sentence by sentence — one JSON object each way, exit status 0 only with a result, the error object and its two members, nothing else on standard output, no tool logic in the front; (b) re-check the planner's judgements in `## Why` — **that no tool can be registered yet**, the A-13 reading, each provisional convention; (c) report anything the code decides that ADR-0010 lists under Boundaries or Limits (a tool's arguments or kinds, a time or size limit, a check, a hook, registration of a server, the data root's way to a tool); (d) confirm that nothing outside the source can add a tool to the registry of the package. If the reviewer reads a point as a design choice needing an ADR or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0038`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the public API as landed, the exit status values and front-level kinds, the provisional choices and unsaid cases, the verification outcomes, the language line, the reading on "no tool yet", and that this task ticks **no** PLAN checkbox.
- Size: about 240 non-test lines in 2 files; the cap is 300 LOC / 5 files (tests excluded). If the two modules cannot stay within it, finish the shared level and the front without optional helpers and propose the split in `## Follow-ups` (DRIVER §5).
- If the ADR is ambiguous or self-contradictory on a point the code must decide and that is not one of the provisional conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any tool function, any tool's arguments, result members or failure kinds; the mock backend; the conformance tests through both fronts (P1-1 slices ③, ④ and later).
- The MCP front: the stdio server, JSON-RPC, the MCP names (`mcp__hilclaw__…`), `.mcp.json`, `--mcp-config`, `mcpServers`, any registration (slice ②; partly an owner action).
- How the data root reaches a tool function; any call of `hilclaw.config`; any read or write of the data plane; any event append (ADR-0006 decision 7).
- Time and size limits of a call, progress, retry, budget, gates, locking, access control (OD-18 sub-questions ② and ③; OD-3, OD-10, OD-14, OD-17, OD-19, OD-23).
- A console script, a build system or any other edit of `pyproject.toml`; `.github/`; `README.md`; `hilclaw/__init__.py`; turning `merge_guard` or `driver_state` into tools or routing them through `python -m hilclaw`.
- Any ADR, the OD register, FR-10's wording, CLAUDE.md, DRIVER.md, PLAN.md, the skills, the agents, anything under `.claude/`.
- Answering HQ-0003 or HQ-0004 on the owner's behalf.

## Follow-ups
- (planner, next — code mode, P1-1 slice ②) The stdio MCP front over `hilclaw/tools.py` with the standard library only (LF line ends, bytes on the standard streams); it settles OD-18 sub-question ① as far as a test can. A live check needs the server registered, which is partly an owner action — judge then whether that is an HQ.
- (planner, independent of HQ-0003 / HQ-0004) The §9 record for OD-17 with #8 M7 before the runtime `STATE.json` of PLAN P1-8; its gate, target and tolerance members are owner-only and stay out.
- (planner) The first tool: which one can be given a contract without an owner item — candidates to judge are a `sim.run` timing-only path at `cpu_standin` over `timing_build` and `timing.run_timing` (touches OD-10, OD-13 and the result form of P1-8) and the meaning of a local `blob.push` / `blob.fetch` (#5 B-2). With it: how the data root reaches a tool function.
- (integrator, document mode, after 2026-10-14) FR-10's closing sentence and #5 A-12 point 1 (T-0037 Follow-ups).

## Result
