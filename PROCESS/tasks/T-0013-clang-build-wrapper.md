---
id: T-0013
title: Add the clang build wrapper for stand-in kernels (hilclaw/clang_build.py) with its tests
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, "#5 A-7", C-7, FR-1]
dependsOn: [T-0002, T-0003, T-0011]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 130, files: 1}   # non-test: the wrapper module; the test file is excluded from the cap (D4)
hq: []   # standard library only; no OD is closed and no ADR is written (see Why)
---
## Why
Owner decision #5 A-7 (2026-10-02) fixes the toolchain of the first backend: the CPU stand-in `cpu_standin` is a **compiled-kernel** backend, "C, compiled with clang as the single toolchain", OpenMP and SIMD intrinsics allowed, so that the compile and repair path of FR-5 is real. FR-1 puts `compile` between code generation and `sim`, and a compile failure goes back to the coder with the failure report. PLAN P1-2 lists the parts of the adapter: "clang build wrapper, local execution, timing collection". This task is the **first slice of P1-2**: the build wrapper only, a leaf that turns C sources into one artefact with clang and reports what the compiler said.

It is a leaf that later tasks need: the rest of the `cpu_standin` adapter (running and timing a built kernel), the harness (P1-3) and the C gate of CI (rest of P0.5-1, "clang build of the stand-in kernels") all start from a build step.

Why this item now (planner's judgement, DRIVER §6): the phase is P0.5, but none of its three open items can become a task today. The rest of P0.5-1 (C gate) waits for P1-2 and P1-3; P0.5-3 (coverage gate) needs a tool that D12 does not name, which would be a new external dependency, and a definition of "function coverage" (an owner question, not a task); the rest of P0.5-4 is the owner's hook registration. §6 allows an item of a later phase whose dependencies are met. Among the open P1 items:
- P1-1 (FR-10 tool contract + mock backend) needs request and result shapes that no document defines and that touch OD-10, OD-13, OD-18 and OD-23; it needs ADR work first.
- P1-3 is marked "owner confirmation needed"; P1-4 depends on it.
- P1-5 and P1-8 are data-plane schemas behind OD-6 and OD-8.
- The rest of P1-6 waits for OD-8 (`artifacts.json`) and for a statement of what a "local" `blob.push` / `blob.fetch` does.
- This slice of P1-2 is determined by A-7 and needs none of those: every policy question is left to the caller as an explicit argument (see Acceptance Criteria).

The Requirements sentence "OD-4, OD-6, OD-8 are to be confirmed before the first commit" does not stop it: the wrapper uses no key schema (OD-4), no coder spec (OD-6) and no data-plane path (OD-8) — source and output paths are arguments. It does not implement the FR-10 tool contract, so P1-1 is not a prerequisite. If the executor or the reviewer finds that the implementation does need one of those ODs, that is the BLOCKED reason "design choice needing an OD" (DRIVER §3), not something to decide silently.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §9
- PROCESS/PLAN.md — P1-2 (this task is its first slice); P1-1, P1-3 and P0.5-1 for what is deliberately not touched
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성" and "데이터 plane 스키마 변경"), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- ARCHITECTURE/Requirements.md — FR-1 (the `compile` step and case ⑴ repair), FR-5, FR-10 (the whole row), NFR-2, NFR-4, C-7 (⑥ and the POSIX derivation); the OD register rows OD-4, OD-8, OD-13, OD-14, OD-18 (read to know what is **not** decided here)
- Issue #5, comment "A-7 confirmed (2026-10-02)": `gh api repos/myungjoo/HIL-Claw/issues/comments/5944117402 --jq .body` (the toolchain decision is the whole requirement of this task); comment "A-12 confirmed": `gh api repos/myungjoo/HIL-Claw/issues/comments/5946779596 --jq .body` (single package, language policy)
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks
- PROCESS/tasks/T-0008-cas-blob-store.md and PROCESS/tasks/T-0012-data-repo-config.md — `## Acceptance Criteria` and `## Result`: conventions of the sibling modules (stdlib only, explicit arguments, provisional choices listed with one line of reason, reachability check with the stdlib `trace` module, how the `## Result` text is handed to the driver); T-0012 `## Result` "Process incident" and its follow-up (e): never put a branch deletion in a command line that also contains another step
- PROCESS/tasks/T-0011-ci-test-presence-check.md — `## Result`: the four CI jobs on every PR and the module-to-test mapping `hilclaw/<name>.py` → `tests/test_<name>.py` that CI enforces
- Existing files: `pyproject.toml`, `hilclaw/__init__.py`, `hilclaw/cas.py` (style reference: docstrings, `NamedTuple` result, write to a temporary name and `os.replace`), `tests/test_cas.py` (test style), `.github/workflows/ci.yml`, `.editorconfig`, `.gitattributes`

## Acceptance Criteria
A-7 fixes only this: stand-in kernels are C, clang is the single toolchain, OpenMP and SIMD are allowed. The module name, the public API, the result shape, the error types and the write procedure are **not** fixed anywhere. None of them is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below, state each choice with one line of reason in the commit body, the PR body and `## Result`, and do not present them as requirements.

Constraints:
- **Standard library only** (`subprocess`, `shutil`, `os`, `pathlib`, `time`, `secrets`, `typing` as needed). Adding any package is the BLOCKED reason "new external dependency". `pyproject.toml` stays unchanged.
- Code must run on CPython 3.11 and 3.14 (both are CI matrix entries).
- **No policy in the wrapper.** It adds no compiler flag of its own: no optimisation level, no `-fopenmp`, no `-march`, no `-std`, no `-shared`. The caller passes every flag. The time limit is a required argument with no default. Which flags a stand-in kernel is built with, what kind of artefact it is (object, shared library, executable) and how long a build may take belong to the adapter, the hw_profile and OD-14, not to this task.
- The wrapper **builds, it never runs** the artefact. It reads no configuration file and no environment variable of its own, never runs `git`, never touches the data repository or `hilclaw.cas`, and writes nothing except the output artefact (and its temporary file) in the directory the caller named.
- The compiler is started without a shell (`subprocess` with an argument list, `shell=False`); no argument is ever interpolated into a command string.
- No command line entry point, no `main`, no MCP server: how layer-2 tools are exposed to layer 1 is OD-18 (open).
- **No binary file and no build output is committed**: C sources of the tests are written at run time under pytest's `tmp_path`.

Module (new, `hilclaw/clang_build.py`; provisional name and flat placement, next to the sibling modules — a `backends/` sub-package is a layout choice for the task that defines the FR-10 contract. Python because the package is Python and process handling is in the stdlib — one line in the commit body and `## Result`):
- Module docstring and short docstrings on the public names (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Public API (provisional names and shapes; the executor may rename or regroup them, but every public function must be tested):
  - `BuildResult` — a `typing.NamedTuple` with `ok: bool`, `returncode: int | None` (`None` when the build timed out), `timed_out: bool`, `output: pathlib.Path` (the artefact path as requested), `log: str` (everything the compiler wrote to stdout and stderr), `command: tuple[str, ...]` (the exact argument list that was run, for the audit trail of NFR-2) and `duration_s: float` (wall-clock time of the compiler process).
  - `build(sources, output, *, timeout_s, flags=(), compiler=None, cwd=None, env=None) -> BuildResult`.
  - `compiler_version(compiler=None, *, timeout_s) -> str` — the first line of `<compiler> --version` (for example `Ubuntu clang version 18.1.3 ...`), so that a caller can record which toolchain produced a result.
  - `CompilerNotFoundError` (a `LookupError` or `FileNotFoundError` subclass; the message names what was looked for).
- Behaviour of `build`:
  - `sources`: one path or a non-empty sequence of paths (`str` or `os.PathLike`). Every source must be an existing regular file; otherwise `FileNotFoundError` (or the matching `OSError` subclass for a directory) is raised **before** the compiler is started. An empty sequence raises `ValueError`.
  - `output`: `str` or `os.PathLike`. Its parent directory must exist and is never created (`FileNotFoundError` / `NotADirectoryError`), for the same reason `hilclaw.cas` does not create a missing root.
  - `flags`: a sequence of `str`, passed through in order. A non-`str` element or a bare `str` instead of a sequence raises `TypeError` (a string would be split into characters). A flag that sets the output (`-o`, or the form with the path attached) raises `ValueError`: the wrapper owns `-o`. State the exact rule you implement.
  - `compiler`: `None` means the `clang` found on `PATH` (`shutil.which`); a `str` / `os.PathLike` names another executable (looked up on `PATH` unless it contains a directory part); a sequence of `str` is a command prefix (for example `("ccache", "clang")`). If the executable cannot be found, `CompilerNotFoundError` is raised and nothing is started.
  - The command is `<compiler...> <flags...> <sources...> -o <temporary output>`; state the order you chose. `cwd` and `env` are handed to the process unchanged (`None` = inherit).
  - `timeout_s` must be a positive number (`bool` excluded); otherwise `ValueError` / `TypeError`. When the limit is reached the compiler process is killed and the result has `timed_out=True`, `ok=False`, `returncode=None`, with whatever output was captured. Only the direct child is killed; a process tree is a known limit to record (OD-14).
  - A **compile failure is a result, not an exception**: a non-zero exit gives `ok=False` with the return code and the log, because FR-1 ⑴ sends that log back to the coder. Exceptions are for caller errors and a missing compiler only.
  - `ok` is `True` only when the compiler exited with 0 **and** the artefact exists. Exit 0 without an artefact (for example `-fsyntax-only`) gives `ok=False`.
  - The artefact is written under a temporary name **in the output's directory** and moved into place with `os.replace` only on success, so that `ok=True` always means "the file at `output` was produced by this call". On failure or timeout the temporary file is removed and a file that was already at `output` is left untouched. No temporary file remains after any call. If the temporary name has to keep the output's suffix for a toolchain to behave, say so.
  - `log` is stdout and stderr together, decoded as UTF-8 with replacement of invalid bytes (a compiler message must never raise `UnicodeDecodeError`). It is not truncated or filtered; what part of it goes to the coder is OD-6.
- Behaviour of `compiler_version`: same compiler resolution as `build`; a non-zero exit, a timeout or empty output raises an error (provisional: `RuntimeError` or `OSError`; state the choice). It returns the line stripped of the line ending.

Tests (new, `tests/test_clang_build.py`; excluded from the size cap). All files under `tmp_path`.
- Two groups. **Stub-compiler tests** run everywhere: the compiler is a small Python script written by the test and passed as the command prefix `(sys.executable, <script>)`; the script reads its arguments and behaves as told (write the `-o` file and exit 0, print a diagnostic and exit 1, sleep past the limit, exit 0 without writing, print invalid UTF-8 bytes, dump its argument list and working directory to a file). **Real-clang tests** need `clang` on `PATH`: they are skipped when it is absent, **except under GitHub Actions** (`GITHUB_ACTIONS=true`), where a missing `clang` must fail the test instead of skipping — otherwise CI could go green without ever compiling.
- happy:
  - (real) a valid C file with `flags=("-c",)` → `ok`, `returncode == 0`, not timed out, the object file exists and is non-empty, `command` starts with the compiler and contains the source and `-o`.
  - (real) the same source as a shared library (`-shared`, `-fPIC`) on POSIX.
  - (real) `compiler_version()` returns one line that contains `clang`.
  - (stub) the argument order and that `cwd` and `env` reach the process; `duration_s >= 0`; a single path and a one-element list give the same command; `str` and `Path` arguments give the same result.
- branch:
  - (stub and real) a compile error → `ok=False`, non-zero `returncode`, the diagnostic is in `log`, no file at `output`, no temporary file left.
  - (stub) a file already at `output` survives a failed build unchanged and is replaced by a successful one.
  - (stub) exit 0 without an artefact → `ok=False`.
  - (stub) the limit is reached → `timed_out=True`, `returncode is None`, no file at `output`, no temporary file left, and the call returns within a few seconds.
  - (stub) invalid UTF-8 in the compiler output → `log` is a `str`, nothing raised.
  - (stub) two sources; stdout and stderr both appear in `log`.
  - (stub) `compiler_version` with a stub that prints two lines → the first line.
- negative:
  - a missing source, a directory as source, an empty source sequence → the errors above, and the stub's "I was started" marker file does not exist.
  - a missing output directory; an output whose parent is a regular file.
  - `flags` as a bare `str`, with a non-`str` element, with `-o` in both forms.
  - `timeout_s` of `0`, a negative number, `None`, `True`, a `str`.
  - a compiler that does not exist (an explicit name, and `compiler=None` with `shutil.which` patched to return `None`) → `CompilerNotFoundError`, for `build` and for `compiler_version`.
  - `compiler_version` with a stub that exits non-zero, one that prints nothing, and one that sleeps past the limit.
- Tests must not depend on the host's default target or on OpenMP being installed: no test links an executable and runs it, none uses `-fopenmp`.
- Coverage is not measured by CI yet (P0.5-3 is open); the tests must still reach every branch above — say in `## Result` how you checked (e.g. the stdlib `python -m trace --count --missing --coverdir <dir outside the repository> --module pytest tests/test_clang_build.py`).
- Do not add tests for other test files, `pyproject.toml` or any CI file (test rule ⑤).

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m pytest` exits 0 (all tests, including the existing ones), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0 (pinned tools: ruff 0.16.10, pytest 9.1.1). The driver's machine (Windows, CPython 3.14) has **no `clang` on `PATH`**, so the real-clang tests are skipped locally: record the skip count, and treat the CI run as the first real compilation. WSL on that machine has clang 14 but only CPython 3.10 (below the floor), so the suite cannot run there; an optional hand-run smoke there is not a substitute and must be labelled as such.
- `git ls-files --eol hilclaw/clang_build.py tests/test_clang_build.py` shows `i/lf` for both; `git status --short` after the test run shows no stray file.
- `git diff origin/main --stat` lists only the two files in `touchesFiles`; `pyproject.toml`, `hilclaw/__init__.py`, the other modules, `.gitignore`, `.claude/`, `.github/`, `README.md` and `ARCHITECTURE/` are unchanged.
- CI on the PR: `gh pr checks <PR> --watch` ends with **four** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`. Open the log of one Python gate job and confirm from the pytest summary line that **no test was skipped** there (the real-clang tests ran on the runner's clang); quote that line and the clang version if the log shows it. Merge only then.
- If the runner turns out to have no `clang`, the real-clang tests fail in CI by design. Do not weaken the tests and do not edit `.github/workflows/ci.yml` in this task: return BLOCKED ("CI runner has no clang") with the job log line, so that the C toolchain of the runner is settled together with the C gate (P0.5-1).
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Code mode: branch `claude/T-0013-clang-build-wrapper`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0013`; executor commits end with the trailer `Task: T-0013`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (≤ 7 rounds).
- Squash-merge per CLAUDE.md A-13 with `Task: T-0013` as the last line of the PR body, using `gh pr merge --squash` with that body (`--body-file` avoids quoting problems). The merge guard hook of T-0007 is not registered, so checking the four checks before the merge is the executor's own step. Delete the branch **after** the merge is confirmed, in a separate command (T-0012 incident).
- Commit body: the provisional choices (module name and flat placement, API and result fields, no flags added by the wrapper, required time limit, compile failure as a result, `ok` = exit 0 and artefact present, temporary name + `os.replace`, the `-o` rule, compiler resolution and the command-prefix form, command order, log decoding, error types) with one line of reason each, and the language line.
- `## Result`: hand the text to the driver in your final report instead of committing this task file on the branch, so that the diff check above holds (as T-0008 and T-0012 did). `PROCESS/STATE.json`, `PROCESS/journal/` and the `PROCESS/PLAN.md` checkbox belong to the driver. **PLAN P1-2 is not complete** after this task (running and timing remain); say so in `## Result`.
- Size: 1 non-test file, about 130 lines; far below 300 LOC / 5 files.
- If the implementation turns out to need a decision that is not yours to make (a default flag set, a time limit value, where build outputs live in the data repository), do not guess: keep it an argument, or return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.

## Out of Scope
- Running a built kernel, timing, repetition, warm-up and statistics (rest of P1-2; OD-13), and loading a shared library into the harness process or a separate one (P1-3; OD-14, OD-16).
- The FR-10 tool contract (`sim.run`, `board.run`, `profiler.collect`, `correctness.check`), the mock backend and conformance tests (P1-1); registering `cpu_standin` as a backend or hw_profile (OD-4, OD-26).
- A default or recommended flag set (`-O3`, `-march=native`, `-fopenmp`, sanitizers), a default time limit, and any environment variable or config key that selects the compiler.
- Sandboxing the compiler, resource limits, killing a process tree, cleaning the include path or the environment (NFR-4, OD-14).
- Storing the artefact in the CAS, writing `build.log`, `artifacts.json` or any event to the data repository (P1-6, P1-8; OD-8).
- Shaping or truncating the log for the coder, parsing diagnostics (OD-6).
- Compilers other than clang as a supported choice, cross-compilation, remote builds over SSH (A-7 ③ "then LAN"; #5 B-2), build caching, incremental builds, parallel builds.
- A CI job for the C gate, installing clang or OpenMP on the runner, any change to `.github/workflows/ci.yml` (rest of P0.5-1).
- A command line, MCP exposure or hook integration (OD-18).
- Editing README.md, CLAUDE.md, DRIVER.md, PLAN.md, `ARCHITECTURE/` or the skills (document mode, separate changes); `pyproject.toml`.

## Follow-ups
- (P1-2 slice 2) Run a built stand-in kernel locally and collect timings; needs the kernel calling convention, which the harness (P1-3) and the first spec example (P1-5, OD-6) define.
- (P1-1) When the FR-10 contract and the backend layout exist, decide whether this module moves under the `cpu_standin` backend package.
- (P0.5-1, C gate) The CI job "clang build + harness pass" can call `build`; it also has to pin or record the runner's clang version and decide whether OpenMP (`libomp`) is installed there.
- (decision to revisit, with OD-14) Killing the whole process tree on a timeout, resource limits for the compiler, and an environment scrubbed of host-specific variables.
- (decision to revisit) The flag policy of `cpu_standin` builds and where it is recorded (hw_profile, OD-4), including whether `-march=native` is acceptable for results that are compared across machines.
- (P0.5-3) First coverage measurement of `hilclaw/clang_build.py` once the coverage gate exists.

## Result
- 2026-10-06 — fresh start (landed check: nothing with `Task: T-0013` on `main`, no PR, no branch). **DONE**: PR #23 https://github.com/myungjoo/HIL-Claw/pull/23 (code mode) squash-merged to main as `6a850fc` ("T-0013: Add the clang build wrapper for stand-in kernels (#23)", last body line `Task: T-0013`); remote and local branch `claude/T-0013-clang-build-wrapper` deleted. Branch commits: `c4d59a7` (implementation), `4502302` (review round 1), `e8cdabe` (review round 2).
- Change: 2 files, +759 lines — `hilclaw/clang_build.py` 231, `tests/test_clang_build.py` 528; non-test 231 lines in 1 file (cap 300/5; the estimate was 130, the difference is mostly docstrings of the public API). `pyproject.toml`, `hilclaw/__init__.py`, the other modules, `.gitignore`, `.claude/`, `.github/`, `README.md` and `ARCHITECTURE/` are unchanged. Standard library only (`math`, `os`, `secrets`, `shutil`, `subprocess`, `time`, `pathlib`, `typing`). No OD closed, no ADR, no data-plane schema touched, no new dependency, no binary committed.
- **PLAN P1-2 is not complete** after this task: this is its first slice (the build step); running and timing a built kernel remain. P1-2 is not ticked.
- This `## Result` was not committed on the task branch (the task's own diff check); the executor handed the text to the driver.
- Language: Python, because the package is Python and process handling is in the standard library.
- Review: 3 rounds by fresh-context `dev-reviewer` agents, all Approve, no `SECURITY` finding, no Blocking / Major in any round. The reviewers did not rerun tests (read-only role); CI and the executor's local runs are the gate.
  - Round 1, Approve on `c4d59a7` (https://github.com/myungjoo/HIL-Claw/pull/23#issuecomment-6014609966), four Minor: (1) the consequences of "only the direct child is killed" on a timeout were not stated -> module docstring extended in `4502302`, no behaviour change (OD-14); (2) `test_timeout_kills_the_compiler` depended on the stub starting within 1 s -> limit raised to 5 s; (3) the `-o` rule is a prefix match and wider than its name -> stated in the `build()` docstring; (4) compiler lookup on Windows (`shutil.which` also searches the current directory; a `.bat`/`.cmd` match goes through `cmd.exe`) -> no code change, target platforms are POSIX (C-7), recorded below as a known limit. Response: https://github.com/myungjoo/HIL-Claw/pull/23#issuecomment-6014626582
  - Round 2, Approve on `4502302` (https://github.com/myungjoo/HIL-Claw/pull/23#issuecomment-6014643802): one cosmetic Minor, a 112-column docstring line left by the round 1 edit -> re-wrapped in `e8cdabe` (docstring only). Response: https://github.com/myungjoo/HIL-Claw/pull/23#issuecomment-6014654884
  - Round 3, Approve on `e8cdabe` (https://github.com/myungjoo/HIL-Claw/pull/23#issuecomment-6014691590): no finding. Note only: the branch commits end with `Co-Authored-By:` after the `Task: T-0013` trailer (as the driver instructed); the squash commit's last line is `Task: T-0013`. The head did not change after this Approve.
- Provisional choices (conventions of this task, not requirements; A-7 fixes only "C, clang as the single toolchain, OpenMP and SIMD allowed"):
  - Module `hilclaw/clang_build.py`, flat next to the sibling modules: a `backends/` sub-package is a layout choice for the task that defines the FR-10 contract.
  - API: `build(sources, output, *, timeout_s, flags=(), trailing_flags=(), compiler=None, cwd=None, env=None) -> BuildResult`; `compiler_version(compiler=None, *, timeout_s) -> str`; `CompilerNotFoundError(LookupError)`; public constant `DEFAULT_COMPILER = "clang"`. `BuildResult` is a `NamedTuple` (`ok`, `returncode`, `timed_out`, `output`, `log`, `command`, `duration_s`), as `cas.BlobRef`.
  - **`trailing_flags` is an addition to the API the task suggested**: with flags placed before the sources, a library such as `-lm` would precede the objects and be dropped by linkers that default to `--as-needed`; the caller needs a place after the sources.
  - No flag is added by the wrapper: flag policy belongs to the adapter and the hw_profile (OD-4, OD-14).
  - `timeout_s` is required, has no default, and must be a positive finite `int` or `float` (`bool` excluded; `TypeError` for a wrong type, `ValueError` for zero, negative, NaN or infinity): how long a build may take is policy.
  - A compile failure or a timeout is a result, not an exception: FR-1 ⑴ sends the log back to the coder. Exceptions are for caller errors and a missing compiler, all raised before anything is started.
  - `ok` = exit status 0 and the artefact exists: exit 0 without an artefact (`-fsyntax-only`) is not a build.
  - The artefact is written as `<stem>.tmp-<pid>-<random><suffix>` in the output's directory and moved with `os.replace` on success only; the temporary file is removed in every other case. The temporary name keeps the output's suffix because some linkers derive behaviour from the extension of the output.
  - The `-o` rule: any flag that starts with `-o` or `--output` raises `ValueError`, in `flags` and in `trailing_flags`. This also rejects the few unrelated clang options with that prefix (`-objcmt-*`, `--output-asm-variant`), which a C kernel does not need. It is a guard against mistakes, not a security boundary: `-Wl,-o,x` and `@response` files are not inspected.
  - Compiler resolution: `None` = `clang` on `PATH`; a `str` or `os.PathLike` names another executable; a sequence of `str` is a command prefix whose first element is resolved the same way (an empty prefix is `ValueError`, a non-`str` element `TypeError`). Resolution is `shutil.which` on the `PATH` of the calling process (not of `env`), and the result is made absolute so that `cwd` cannot change which executable starts.
  - Command order: `<compiler...> <flags...> <sources...> <trailing_flags...> -o <temporary output>`.
  - Sources and the output are passed to the compiler as absolute paths (`os.path.abspath`), so the checks made by the wrapper and the compiler agree whatever `cwd` is. `BuildResult.output` stays as the caller gave it. Consequence: absolute paths appear in diagnostics and in debug information unless the caller passes a prefix-map flag.
  - The compiler gets no standard input (`DEVNULL`): a compiler waiting for input would only end at the time limit.
  - `log` = stdout and stderr merged in one pipe, decoded as UTF-8 with `errors="replace"`, not truncated, no newline translation.
  - Error types: `FileNotFoundError` / `IsADirectoryError` for a source, `FileNotFoundError` / `NotADirectoryError` / `IsADirectoryError` (output is an existing directory) for the output, `ValueError` for no source, `TypeError` for wrong argument types including a bare `str` as flags. `compiler_version` raises `RuntimeError` for a non-zero exit, a timeout or no version line, reads the version from stdout only and returns the first line stripped. An `OSError` from starting the process or from `os.replace` is passed on.
- Known limits: (a) on a timeout only the direct child is killed (process tree: OD-14) — a surviving child (the compiler behind a `ccache` prefix, a linker) can still write the temporary file after the call has returned, and where it keeps the output pipe open the call can last longer than the limit (on Windows `subprocess.run` waits for the pipe after the kill); (b) the compiler is not sandboxed and the environment is not scrubbed (NFR-4); (c) on Windows `shutil.which` also searches the current directory and a `.bat`/`.cmd` match runs through `cmd.exe` — target platforms are POSIX (C-7); (d) a non-regular source (FIFO, device) is reported as `FileNotFoundError`.
- Local verification (CPython 3.14.4 on Windows, ruff 0.16.10, pytest 9.1.1; **no clang on `PATH`**, so the 5 real-clang tests are skipped locally):
  - Before the first commit: `python -m pytest` -> `618 passed, 5 skipped`; `python -m ruff check .` -> `All checks passed!`; `python -m ruff format --check .` -> clean.
  - Before the merge (head `e8cdabe`, `origin/main` at `0cdfdb6`): `618 passed, 5 skipped` (77 passed + 5 skipped in `tests/test_clang_build.py`, 541 existing); `All checks passed!`; `42 files already formatted`; `git ls-files --eol` -> `i/lf w/lf` for both files; `git status --short` empty after the test run; `git diff origin/main --stat` -> only the two `touchesFiles`.
  - After the merge, on main `6a850fc`: `618 passed, 5 skipped`; clean tree; `main` == `origin/main`.
  - Optional hand-run smoke, **not a substitute for CI** (WSL, Ubuntu clang 14.0.0-1ubuntu1.1, CPython 3.10.12 — below the supported floor, so the suite was not run there): `compiler_version()` returned `Ubuntu clang version 14.0.0-1ubuntu1.1`; `build()` produced an object file (`-c`) and a shared library (`-shared -fPIC`, trailing `-lm`), reported a compile error as `ok=False`, `returncode=1` with the diagnostic in `log`, gave `ok=False` / `returncode=0` for `-fsyntax-only`, and left no temporary file.
- Reachability check: `python -m trace --count --missing --coverdir <dir outside the repository> --module pytest tests/test_clang_build.py` marks **no** line of `hilclaw/clang_build.py` as missing (run on the `c4d59a7` code on Windows without clang; the later commits changed docstrings and one test limit only).
- CI on the PR (`pull_request`), four checks each (`Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`), all success:
  - `c4d59a7`: https://github.com/myungjoo/HIL-Claw/actions/runs/37451888033
  - `4502302`: https://github.com/myungjoo/HIL-Claw/actions/runs/37452188435
  - `e8cdabe` (final head): https://github.com/myungjoo/HIL-Claw/actions/runs/37452395865
- **The real-clang tests ran in CI**: on the final head the pytest summary lines are `623 passed in 8.60s` (Python gate 3.11) and `623 passed in 12.02s` (Python gate 3.14) — no test skipped, so the 5 real-clang tests compiled with the runner's clang (`ubuntu-latest`). The job log does not show the clang version (the tests do not print it).
- Merge: `DONOTMERGE` removed, PR marked ready, the four checks of `e8cdabe` confirmed successful, then `gh pr merge 23 --squash --body-file` with the PR body. The remote branch was deleted in a separate command only after `gh pr view 23 --json state` reported `MERGED` (T-0012 lesson); the local branch after its tree was checked identical to merged `main`. No tool call was denied; no force push.
- `push` run on `main` after the merge (`6a850fc`): https://github.com/myungjoo/HIL-Claw/actions/runs/37452766680 — `completed` / `success` (the driver re-checked the conclusion before the wrap-up).
- Follow-ups: unchanged from `## Follow-ups`. Additions: (a) (P0.5-1, C gate) the CI log does not record the runner's clang version; the C gate job can print `compiler_version()`; (b) decision to revisit with the adapter — whether sources should reach the compiler as absolute paths (current choice) or the caller should get a prefix-map flag by default, since absolute paths end up in debug information; (c) decision to revisit — narrow the `-o` rule from a prefix match to the exact output options if a kernel ever needs an option that starts with `-o`; (d) (with OD-14) process-tree kill would also close known limit (a); (e) decision to revisit — whether the compiler lookup should use the `PATH` of `env` when the caller passes one.
