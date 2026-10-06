---
id: T-0019
title: Add the local process runner for built stand-in artefacts (hilclaw/local_run.py) with its tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, "#5 A-7", C-7, FR-1, NFR-2]
dependsOn: [T-0002, T-0003, T-0011, T-0013]
touchesFiles: [hilclaw/local_run.py, tests/test_local_run.py]
estimatedSize: {loc: 120, files: 1}   # non-test: the runner module; the test file is excluded from the cap (D4)
hq: []   # standard library only; no OD is closed and no ADR is written (see Why)
---
## Why
Owner decision #5 A-7 (2026-10-02) makes the CPU stand-in `cpu_standin` a **compiled-kernel** backend that runs "on the orchestrator machine first" (placement ③: local first, then LAN), so that the loop of FR-1 (`codegen → compile → run → correctness → profile → ...`) is exercised for real. PLAN P1-2 lists the parts of the adapter: "clang build wrapper, local execution, timing collection". T-0013 delivered the first part (`hilclaw/clang_build.py`: build, never run). This task is the **second slice of P1-2**: local execution only, as a leaf that starts one local process from an argument list, bounds it by a time limit and reports what happened.

It is deliberately ignorant of kernels. Earlier planner notes held the rest of P1-2 back because "the kernel calling convention hangs on P1-3 / P1-5": how a built kernel is called (its C prototype, whether it is an executable of its own or a shared library loaded by a harness driver), what is timed and how often, are all undecided (OD-13, OD-14, OD-16; P1-3 is marked "owner confirmation needed"). None of that is needed to start a process and wait for it: whatever those decisions turn out to be, something built by `clang_build.build` is started locally as a process, and the caller of this module decides what that is. Every policy question is left to the caller as an explicit argument (see Acceptance Criteria).

Why this item now (planner's judgement, DRIVER §6, 2026-10-07): phase P0.5 has no actionable item (P0.5-3 is BLOCKED on HQ-0003; the rest of P0.5-1 waits for P1-2 / P1-3; the rest of P0.5-4 is the owner's hook registration, and the forbidden-command guard needs the owner's word on tests). §6 allows an item of a later phase whose dependencies are met. In P1: P1-3 is marked "owner confirmation needed" and P1-4 depends on it; P1-5 slice 3 (the real GEMM example) needs owner values; P1-1 needs request / result shapes that no document defines; P1-8 (OD-8) takes the result of OD-3 (owner-only) as input; the rest of P1-6 needs OD-8. This slice needs nothing undecided.

It does not implement the FR-10 tool contract, uses no key schema (OD-4), no codegen spec (OD-6) and no data-plane path (OD-8), and closes none of OD-13, OD-14, OD-16 or OD-18. If the executor or the reviewer finds that the implementation does need one of those decisions, that is the BLOCKED reason "design choice needing an OD" (DRIVER §3), not something to decide silently.

Known risk, accepted: the later adapter or harness design may wrap, move or replace this module (for example if process-tree kill and resource limits of OD-14 need a different start-up). The module is small and policy-free so that such a change is cheap.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §9
- PROCESS/PLAN.md — P1-2 (this task is its second slice); P1-1, P1-3 and P0.5-1 for what is deliberately not touched
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성" and "데이터 plane 스키마 변경"), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- ARCHITECTURE/Requirements.md — rows FR-1, FR-9, FR-10, NFR-2, NFR-3, NFR-4, C-7; register rows OD-13, OD-14, OD-16, OD-18 (read to know what is **not** decided here); ARCHITECTURE/OpenDecisionProposals.md sections OD-13 and OD-14 (proposals, not decisions)
- Issue #5, comment "A-7 confirmed (2026-10-02)": `gh api repos/myungjoo/HIL-Claw/issues/comments/5944117402 --jq .body`
- `hilclaw/clang_build.py` — the sibling to follow closely: module docstring, `NamedTuple` result, `_check_timeout`, `_resolve` (executable lookup with `shutil.which`, result made absolute), no shell, `stdin=DEVNULL`, a timeout as a result; and `tests/test_clang_build.py` (test style: child processes are small Python scripts started with `sys.executable`)
- PROCESS/tasks/T-0013-clang-build-wrapper.md — `## Acceptance Criteria` (sections "Verification" and "Process") and `## Result` (provisional choices with one line of reason, known limits, reachability check, the four CI checks, branch deletion in a separate command)
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks
- Existing files: `pyproject.toml`, `hilclaw/__init__.py`, `.github/workflows/ci.yml`, `.editorconfig`, `.gitattributes`

## Acceptance Criteria
A-7 and PLAN P1-2 fix only this: built stand-in kernels are executed locally on the orchestrator machine. The module name, the public API, the result shape and the error types are **not** fixed anywhere. None of them is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below, state each choice with one line of reason in the commit body, the PR body and `## Result`, and do not present them as requirements.

Constraints:
- **Standard library only.** Adding any package is the BLOCKED reason "new external dependency". `pyproject.toml` stays unchanged.
- Runs on CPython 3.11 and 3.14 (both are CI matrix entries).
- **No policy in the runner.** The time limit is a required argument with no default. The runner sets no environment variable (no `OMP_NUM_THREADS`), pins no CPU, sets no priority and no resource limit, repeats nothing, discards no warm-up, computes no statistic and interprets neither the output nor the exit status. How often a kernel is run, what is timed and what a run "passes" belong to the harness and the adapter (OD-13, OD-16; P1-3).
- It knows nothing about kernels: no C prototype, no operand, no shape, no `hw_profile`. It does not import `hilclaw.clang_build`, `hilclaw.cas`, `hilclaw.config`, `hilclaw.keys` or `hilclaw.spec`.
- It reads no configuration file and no environment variable of its own, never runs `git`, never touches the data repository and writes no file.
- The process is started without a shell (`subprocess` with an argument list, `shell=False`); no argument is ever interpolated into a command string.
- No command line entry point, no `main`, no MCP server: how layer-2 tools are exposed to layer 1 is OD-18 (open).
- `hilclaw/clang_build.py` is not edited and none of its private names (leading underscore) is imported; the few lines of timeout check and executable lookup are restated (sharing them is a follow-up).

Module (new, `hilclaw/local_run.py`; provisional name and flat placement next to the sibling modules. Python because the package is Python and process handling is in the stdlib — one line in the commit body and `## Result`):
- Module docstring that says what the runner does and what it leaves to the caller, and names the known limits below; short docstrings on the public names (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Public API (provisional names and shapes; the executor may rename or regroup them, but every public function must be tested):
  - `RunResult` — a `typing.NamedTuple` with `returncode: int | None` (`None` when the run timed out; negative when the process was ended by a signal on POSIX, as `subprocess` reports it), `timed_out: bool`, `stdout: bytes`, `stderr: bytes` (kept apart and **not decoded**: what the output means and its encoding are the caller's), `command: tuple[str, ...]` (the exact argument list that was run, for the audit trail of NFR-2) and `duration_s: float` (wall-clock time of the process as seen by the caller, `time.monotonic`). There is no `ok` field: whether a non-zero exit is a failure is the caller's judgement.
  - `run(command, *, timeout_s, cwd=None, env=None) -> RunResult`.
  - `ProgramNotFoundError` (a `LookupError` subclass, as `clang_build.CompilerNotFoundError`; the message names what was looked for).
- Behaviour of `run`:
  - `command`: a non-empty sequence whose first element is the program (`str` or `os.PathLike`) and whose other elements are `str` arguments passed through in order. A bare `str` or `bytes` raises `TypeError` (a string would be split into characters); a non-`str` argument raises `TypeError`; an empty sequence raises `ValueError`.
  - The program is resolved as `clang_build` resolves its compiler: `shutil.which` on the `PATH` of the calling process, the result made absolute so that `cwd` cannot change which executable starts. If it cannot be found, `ProgramNotFoundError` is raised and nothing is started. Consequence to state: a relative program path is resolved against the working directory of the calling process, not against `cwd`.
  - `timeout_s` must be a positive finite `int` or `float` (`bool` excluded): `TypeError` for a wrong type, `ValueError` for zero, a negative number, NaN or infinity — the same rule as `clang_build`.
  - `cwd` and `env` are handed to the process unchanged (`None` = inherit). The process gets no standard input (`DEVNULL`).
  - When the limit is reached the process is killed and the result has `timed_out=True`, `returncode=None`, with whatever output was captured until then. Only the direct child is killed.
  - **A non-zero exit, a signal or a timeout is a result, not an exception**: FR-1 sends a failure report back to the coder, so the caller needs the output. Exceptions are for caller errors and a missing program, all raised before anything is started. An `OSError` from starting the process (for example a file that is not executable) is passed on.
  - The output is not truncated, filtered or decoded.
- Known limits to record in the module docstring and `## Result` (all belong to OD-14, none is decided here): only the direct child is killed on a timeout, so a surviving grandchild that keeps a pipe open can make the call last longer than the limit; the output is held in memory without a size limit; the process is not sandboxed and the environment is not scrubbed; on Windows `shutil.which` also searches the current directory (target platforms are POSIX, C-7).

Tests (new, `tests/test_local_run.py`; excluded from the size cap). Every child process is a small Python script written by the test under `tmp_path` and started as `(sys.executable, <script>, ...)`; no test needs `clang`, a compiled binary or the network, and no binary file is committed.
- happy: a child that exits 0 → `returncode == 0`, not timed out, `duration_s >= 0`, `command` starts with the absolute path of the program and carries the arguments in order; stdout and stderr are captured apart, as `bytes`; arguments, `cwd` and `env` reach the child (the child reports them); a `str` program and a `Path` program give the same command; a `list` and a `tuple` command give the same result; the child sees end-of-file on standard input.
- branch: a child that exits with a non-zero status → that status, output kept, nothing raised; a child that writes bytes that are not valid UTF-8 → returned unchanged; a child that writes nothing → empty `bytes`; a child that sleeps past the limit → `timed_out=True`, `returncode is None`, the output written (and flushed) before the sleep is in the result, and the call returns within a few seconds; (POSIX only, skipped on Windows) a child that ends itself with a signal → negative `returncode`, not timed out.
- negative: an empty command; a bare `str` and a `bytes` command; a non-`str` argument; a program that is neither `str` nor `os.PathLike`; a program that does not exist (a plain name and a path with a directory part) → `ProgramNotFoundError`; `timeout_s` of `0`, a negative number, NaN, infinity, `None`, `True`, a `str`; an existing file that cannot be executed (POSIX: a regular file without the execute bit, given by path) → the documented error. For every caller error assert that nothing was started (the child's "I was started" marker file does not exist).
- Test rules of CLAUDE.md / DRIVER §5 (D12) apply in full: ① `hilclaw/` keeps line coverage ≥ 80 % and function coverage ≥ 80 %; ② happy, error, branch **and negative** cases; ③ every public function of the touched module is tested; ④ the new module has its test file (CI job `Test presence (hilclaw)` enforces `hilclaw/local_run.py` → `tests/test_local_run.py`); ⑤ no tests for test code, CI workflows, hook scripts or driver helper scripts. Coverage is not measured by CI yet (P0.5-3 is BLOCKED on HQ-0003), so the tests must reach every line and branch of the new module: say in `## Result` how you checked (for example `python -m trace --count --missing --coverdir <dir outside the repository> --module pytest tests/test_local_run.py`), with throw-away scripts kept outside the repository.

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m pytest` exits 0 (the 5 real-clang tests of `tests/test_clang_build.py` skip on the driver's Windows machine — record the skip count, and any POSIX-only test of this task that skips there), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0 (pinned tools: ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol hilclaw/local_run.py tests/test_local_run.py` shows `i/lf` for both; `git status --short` after the test run shows no stray file.
- `git diff origin/main --stat` lists only the two files in `touchesFiles`; `pyproject.toml`, `hilclaw/__init__.py`, the other modules, `.claude/`, `.github/`, `README.md`, `ARCHITECTURE/` and `PROCESS/` are unchanged.
- CI on the PR: `gh pr checks <PR> --watch` ends with **four** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`. Open the log of one Python gate job and confirm from the pytest summary line that **no test was skipped** there (the POSIX-only tests ran on the Linux runner); quote that line. Merge only then.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Before anything else, the §3-5 landed check: `git log origin/main --grep='^Task: T-0019'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0019 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none on 2026-10-07 at planning time).
- Code mode: branch `claude/T-0019-local-process-runner` from `origin/main`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0019`; executor commits end with the trailer `Task: T-0019`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds). Ask it explicitly to report any policy the module decides that belongs to OD-13, OD-14 or OD-16. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the four checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0019`**. The merge guard hook is not registered, so checking the four checks before the merge is the executor's own step. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED` (T-0012 incident).
- Commit body: the provisional choices (module name and placement, API and result fields, raw `bytes` output kept apart, no `ok` field, required time limit, failure / signal / timeout as a result, program resolution, no standard input, error types) with one line of reason each, the known limits, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit to this task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The task branch and the PR must not contain the task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. **PLAN P1-2 is not complete** after this task (timing collection and the adapter itself remain); say so in `## Result`.
- Size: 1 non-test file, about 120 lines; the cap is 300 LOC / 5 files (tests excluded).
- If the implementation turns out to need a decision that is not yours to make (a default time limit, an environment policy, a kill policy for process trees, an output size limit, anything about the kernel interface), do not guess: keep it an argument or a recorded known limit, or return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Timing collection in the sense of NFR-3: repetition, warm-up, statistics, timers inside the measured process, raw sample storage (rest of P1-2 and P1-3; OD-13). `duration_s` is the wall-clock time of one process and is not presented as a kernel measurement.
- The kernel calling convention, a harness driver, loading a shared library, input generation, reference and tolerance comparison (P1-3, P1-4; OD-16), and the `cpu_standin` adapter that combines build and run.
- The FR-10 tool contract (`sim.run`, `board.run`, `profiler.collect`, `correctness.check`), the mock backend and conformance tests (P1-1); remote execution over SSH (A-7 ③ "then LAN"; #5 B-2).
- Sandboxing, resource limits, process groups and process-tree kill, an output size limit, a scrubbed environment, thread or CPU pinning (NFR-4, OD-14).
- Feeding standard input, streaming output while the process runs, running several processes at once.
- Storing output in the CAS or writing any log, event or `eval` record to the data repository (P1-6, P1-8; OD-8).
- A command line, MCP exposure or hook integration (OD-18).
- A CI job for the C gate, any change to `.github/workflows/ci.yml` (rest of P0.5-1).
- Editing `hilclaw/clang_build.py`, `pyproject.toml`, README.md, CLAUDE.md, DRIVER.md, PLAN.md, `ARCHITECTURE/`, the skills or the agents.

## Follow-ups
- (rest of P1-2) The `cpu_standin` adapter and timing collection; they need the kernel calling convention and the measurement policy (P1-3 "owner confirmation needed", P1-5 slice 3 owner values, OD-13).
- (with OD-14) Process-tree kill, resource and output limits, environment policy; this module and `clang_build` share the "only the direct child is killed" limit.
- (when a third module needs them) Share the timeout check and the executable lookup of `clang_build` and this module through one public helper.
- (decision to revisit) Whether a relative program path should be resolved against `cwd`; whether standard input is needed.
- (P1-1) When the FR-10 contract and the backend layout exist, decide whether this module moves under the `cpu_standin` backend package.
- (P0.5-3) First coverage measurement of `hilclaw/local_run.py` once the coverage gate exists.

## Result
