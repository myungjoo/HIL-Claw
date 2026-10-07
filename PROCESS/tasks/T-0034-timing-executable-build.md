---
id: T-0034
title: Add the build step of a timing run (hilclaw/harness/timing_build.py) - one clang_build.build call over timing_driver.c and the sources of one kernel per ADR-0009 decision 2 - and its tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [OD-13, FR-9, FR-10, C-7, "#5 A-7", "#5 A-12"]
dependsOn: [T-0013, T-0031, T-0032, T-0033]
touchesFiles: [hilclaw/harness/timing_build.py, hilclaw/harness/__init__.py, tests/harness/test_timing_build.py]
estimatedSize: {loc: 100, files: 2}   # non-test: the new module and one docstring sentence of the package file; the test file is excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0009 decisions 2 and 9); closes no OD, writes no ADR, standard library only, names no data-plane field
---
## Why
**ADR-0009** fixed how the timing samples of one measurement are taken from a C kernel at `cpu_standin`. Two of its three code parts are on `main`: the Python side that starts a run and reads its report (`hilclaw/harness/timing.py`, T-0032, `c65cc1d`) and the driver program (`hilclaw/harness/timing_driver.c`, T-0033, `470585a`). The part in between is missing: ADR-0009 decision 1 says the Python side "builds the executable", and decision 2 says how — "The driver source and all source files of **one** kernel are compiled and linked by **one call of `clang_build.build`** into one executable, with the caller's flags ... The harness adds no flag". Today only the tests of T-0033 do this, by spelling the driver path themselves. A caller of the package has no function for it and no name for the driver source.

This task (slice 2b of the ADR-0009 code task; planner's split recorded in T-0033 `## Why`) adds that one small module. With it a caller can go from kernel sources to intervals with two calls: build (this module), then `timing.run_timing`.

**PLAN checkbox.** PLAN P1-2 names three parts: "clang 빌드 래퍼" (`hilclaw/clang_build.py`, T-0013), "로컬 실행" (`hilclaw/local_run.py`, T-0019), "타이밍 수집" (T-0032, T-0033, this task); "OpenMP/SIMD 허용" holds because every flag is the caller's. The planner's reading is that P1-2 is complete when this task lands (precedent: T-0025 for P1-6). **The executor does not edit PLAN.md**: state in `## Result` whether you and the reviewer agree that the three named parts exist, and what, if anything, of P1-2 remains; the driver ticks the box from that. An FR-10 backend (`sim.run` / `board.run` behind a tool contract) is P1-1, not P1-2.

Why this item now (planner, 2026-10-07 UTC): P0.5-3 is BLOCKED on HQ-0003 (T-0014, unanswered); the C gate of P0.5-1 is planned after this slice; the rest of P0.5-4 is the owner's hook registration. In P1 everything else waits for an owner item or an open OD. No open PR at planning time; no comment on #5 after the ADR-0009 notice.

A-13 check (planner's reading — the reviewer is asked to re-check): standard library only, `pyproject.toml` and `.github/` unchanged, so no new dependency; no data-plane file or field is read, written or named. The module adds **no rule and no value** to ADR-0009: it chooses no flag, no compiler, no time limit and no output path. The module name, the public names, the order of the sources on the compiler command line and the cases listed under "unsaid" are provisional conventions of the source.

Known risks, accepted: (1) ADR-0007 / 0008 / 0009 are inside their objection windows (until 2026-10-14). (2) The driver clone's environment is Windows without a C compiler: the real-clang test runs on CI only; the stub-compiler tests run everywhere.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED), §3 "BLOCKED 사유" paragraph, §9
- ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md — decisions 1 (terms), **2** (the whole of it), **9** (parameter table: "Flags, trailing flags, compiler, build time limit, path of the executable — the caller, handed to `clang_build.build`"; "Environment and working directory — ... unchanged"), Consequences, Boundaries ("Build settings")
- ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md — decisions 4 and 7 (a kernel defines `hilclaw_gemm` and no `main`)
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `hilclaw/clang_build.py` — the whole module (`build`, `BuildResult`, `CompilerNotFoundError`, `_checked_sources`: what it accepts as `sources` and what it raises); `hilclaw/harness/__init__.py`; `hilclaw/harness/timing.py` — the module docstring and `run_timing` (the consumer of the executable; "it builds nothing"). **`clang_build.py` and `timing.py` are not edited; `timing_driver.c` is not edited.**
- `tests/test_clang_build.py` lines 1-101 (the `Stub` compiler written as a Python script and run as `(sys.executable, script)`, its `started.json` record, the `clang` fixture) and the real-clang tests at its end; `tests/harness/test_timing_driver.py` lines 1-60 and 180-215 (`DRIVER`, `PROTOTYPE`, `STRICT`, the kernel text, the session fixture that skips off POSIX or without clang and calls `pytest.fail` on CI) — style to imitate, **not edited**
- `.github/workflows/ci.yml` (job `Test presence (hilclaw)` maps `hilclaw/harness/timing_build.py` to `tests/harness/test_timing_build.py`); `pyproject.toml`
- PROCESS/tasks/T-0033-timing-driver-c-source.md — `## Result` (Follow-ups (a), (d); "Flags the tests build with"); PROCESS/tasks/T-0032-timing-run-python-side.md — `## Result` (Follow-up (b): pass the executable itself, no prefix; process note (d) on review rounds)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6026950959. If the owner has objected to ADR-0007 / 0008 / 0009 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0009 fixes the rule. Names, shapes and the unsaid cases are **conventions chosen by this task, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and the ADR disagree, **the ADR wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/harness/timing_build.py` (new; about 60-100 lines, most of it docstring). Python because `clang_build` is Python — one line in the commit body and `## Result`. A separate module, not an addition to `timing.py`: that module states that it builds nothing and imports no `clang_build`, and it is at 262 lines. If you judge another name or place better, say why.
- `hilclaw/harness/__init__.py` — only the docstring sentence that lists what the sub-package holds is brought up to date. No code, no re-export.
- `tests/harness/test_timing_build.py` (new).
- Nothing else.

### Constraints
- **Standard library only**; `pyproject.toml` unchanged; runs on CPython 3.11 and 3.14. Imports `hilclaw.clang_build` and no other `hilclaw` module.
- **The harness adds no flag** (decision 2): the module never puts a flag, a library, a language standard, an optimisation level, `-march`, an OpenMP option or a define on the command line, and never inspects, filters or corrects the caller's flags. Whether the caller's flags produce an executable is the caller's matter ("the Python side does not correct it"); the module does not test the artefact.
- **Exactly one `clang_build.build` call** per call of the build function, one compiler process, no retry. It runs nothing that it built, reads no configuration and no environment variable of its own, and writes nothing but what `clang_build.build` writes.
- **No default for the build time limit or the output path**; no compiler chosen here (`None` means what it means in `clang_build`).
- No field, no file form, no `main`, no command-line entry point (OD-18 is open). A failed build is a result, never retried, repaired or stored (OD-10).

### Capabilities (provisional names; each must exist and every public name must be tested)
1. **The driver source has a name.** A public constant or function gives the path of `timing_driver.c` as the installed package holds it, for example `DRIVER_SOURCE = Path(__file__).with_name("timing_driver.c")`. It is the one place in `hilclaw/` that spells the file name.
2. **Build a timing executable**, for example `build_timing_executable(kernel_sources, output, *, timeout_s, flags=(), trailing_flags=(), compiler=None, cwd=None, env=None) -> clang_build.BuildResult`: one call `clang_build.build((<driver source>, *<kernel sources>), output, timeout_s=..., flags=..., trailing_flags=..., compiler=..., cwd=..., env=...)` with every argument handed over unchanged, and its `BuildResult` returned as it is. `kernel_sources` is one path or a non-empty sequence of paths, as `sources` in `clang_build.build`. The defaults of `flags`, `trailing_flags`, `compiler`, `cwd` and `env` are those of `clang_build.build` (an empty flag list is not a flag); if you read decision 9 ("the caller") as requiring `flags` without a default, do that and say so.
3. **Errors.** A compile failure or a timeout is the `BuildResult` (`ok` false). What `clang_build.build` raises (`FileNotFoundError`, `IsADirectoryError`, `NotADirectoryError`, `ValueError`, `TypeError`, `CompilerNotFoundError`, `OSError`) is passed on unchanged. **No kernel source** (an empty sequence) must raise before anything is started — `clang_build.build` alone would not notice, because the driver source is always there; say which exception type (recommended `ValueError`, as `clang_build` for no source).

### Cases the record leaves unsaid — choose, implement, test and list each with one line of reason
- The position of the driver source among the sources (recommended: first, as the tests of T-0033 build).
- A kernel source that is the driver source itself, or the same path twice (recommended: no check — the linker reports the duplicate definition and that is a failed build).
- A bare `str` / `os.PathLike` as `kernel_sources` (one path, as in `clang_build.build`) against other iterables; a `bytes` path.
- A driver source that is missing from the installation (recommended: the `FileNotFoundError` of `clang_build.build`, unchanged).
- Anything else you meet. If you read one as a design choice that needs an ADR or the owner, return BLOCKED with the exact question.

### Tests (`tests/harness/test_timing_build.py`; excluded from the size cap)
The stub compiler is a Python script the test writes into `tmp_path` and passes as `compiler=(sys.executable, script)`; it records its `argv`, working directory and one environment variable and writes the file after `-o`, as the `Stub` of `tests/test_clang_build.py` does. Write the helper in the new test file (do not import from another test module, do not edit other test files). It is a test helper and gets no tests of its own (test rule ⑤). All tests except the real-clang ones must pass on Windows without a C compiler.
- happy (stub): the build succeeds and the returned value is the `BuildResult` of the call (`ok`, `output`, `log`); the recorded `argv` is exactly `<flags...> <driver source> <kernel sources...> <trailing flags...> -o <temporary name>` with the driver source being the absolute path of capability 1 and **nothing added** when `flags` and `trailing_flags` are empty; the artefact is at `output`; `cwd` and `env` reach the compiler process; the driver source path exists, is a regular file named `timing_driver.c` and lies next to `hilclaw/harness/__init__.py`.
- branch (stub): one kernel source given as `str`, as `Path`, as a one-element list and as a tuple of two files; flags and trailing flags in the order given, around the sources; `compiler` as a prefix sequence.
- error / negative (stub): a compiler that exits non-zero → `ok` false, the log passed on, no file at `output`; a timeout → `timed_out`; no kernel source (`()` and `[]`) → the chosen exception and **no process started** (no record file); a kernel source that does not exist or is a directory → the exception of `clang_build.build`, no process started; a flag that sets the output → `ValueError`; a bare `str` as flags → `TypeError`; `timeout_s` omitted → `TypeError`; `timeout_s` of 0 → `ValueError`; a compiler that does not exist → `CompilerNotFoundError`; an output directory that does not exist → `FileNotFoundError`.
- real clang (fixture: skip when `os.name != "posix"` or clang is absent; `pytest.fail` when `GITHUB_ACTIONS == "true"` and clang is absent): (a) a plain correct `hilclaw_gemm` kernel (the prototype of ADR-0008 decision 4) at a small shape such as 64x64x64 is built by the new function with the tests' own flags (for example `-std=c99 -Wall -Wextra -Wpedantic -Werror -O2`), `result.ok` with `result.log` as the message, and `timing.run_timing(<the executable itself>, ...)` gives a completed run (`broken is None`) — **no assertion on whether it converges**; (b) negative: a kernel source without `hilclaw_gemm` (or with a second `main`) → `ok` false and a non-empty log. Keep it to these two builds; the behaviour of the driver program is T-0033's test file.
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003), so check that the stub tests reach every line of the new module, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/harness/test_timing_build.py`, and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public name of the new module is tested; ④ the new module has its test file; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge: `python -m pytest` exits 0 (record pass and skip counts), `python -m ruff check .` and `python -m ruff format --check .` exit 0 (ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol` shows `i/lf` for the changed files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only the files in `touchesFiles`.
- CI on the PR: `gh pr checks <PR> --watch` ends with **four** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`. Open the log of one Python gate and confirm that the real-clang tests of the new file ran and passed there and were not skipped. Merge only then.
- After the squash-merge, check the `push` run on `main` and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- First the §3-5 landed check: `git log origin/main --grep='^Task: T-0034'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0034 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching `hilclaw/harness/` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0034-timing-executable-build` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0034`; executor commits end with the trailer `Task: T-0034`.
- Install nothing (no compiler). After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). The module is small: keep docstrings exact and short, so that rounds are not spent on wording (T-0032 process note (d)). Ask the reviewer explicitly to (a) compare the module with ADR-0009 decision 2 and the build rows of decision 9 sentence by sentence — one `clang_build.build` call, the caller's flags unchanged, no flag added, nothing corrected; (b) re-check the planner's judgements in `## Why` (the A-13 reading, each provisional convention, **and whether PLAN P1-2 is complete with this task**); (c) report anything the module decides that ADR-0009 lists under Boundaries (a flag, a language standard, a thread or environment setting, a time-limit value, a field of any file). If the reviewer reads (b) as a design choice needing an ADR or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the four checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0034`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the public API as landed, the provisional choices and unsaid cases, the verification outcomes, the language line, and **the reading on the PLAN P1-2 checkbox**.
- Size: about 100 non-test lines in 2 files; the cap is 300 LOC / 5 files (tests excluded).
- If the ADR is ambiguous or self-contradictory on a point the code must decide and that is not one of the provisional conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any edit of `hilclaw/harness/timing.py`, `timing_driver.c`, `measurement.py`, `hilclaw/clang_build.py`, `hilclaw/local_run.py`, or of an existing test file (replacing the `DRIVER` path spelled in `tests/harness/test_timing_driver.py` by the new name is not done here).
- A function that builds **and** runs, a cache of built executables, a choice of output path or temporary directory, cleaning up artefacts.
- Build settings: flags, the language standard, `-march`, the OpenMP runtime and thread count, `task.build`, whether a kernel may link another library (ADR-0009 Boundaries; OD-6 sub-question ②). Open point (c) of T-0033 (`cv_max` checks under `-ffinite-math-only`).
- `.github/` (the C gate of PLAN P0.5-1), `pyproject.toml`, packaging of non-Python files.
- The verification half of the harness (PLAN P1-3 "오너 확정 필요", P1-4); the quantity and direction (OD-1); the seed policy (OD-13 ⑦); time-limit values, sandbox, resource limits (OD-14); defences against forged timing (OD-16); what is kept of a failed build or a broken run (OD-10).
- Fields of `sim.json` / `board.json` / `instance.json` / events (P1-8); an FR-10 tool contract or backend (P1-1, OD-18).
- Any ADR, the OD register, README.md, CLAUDE.md, DRIVER.md, PLAN.md, the skills, the agents.

## Follow-ups
- (planner, next) The C gate of PLAN P0.5-1 ("clang 빌드 + 하네스 통과"): judge first what it adds beyond the Python gate, which already builds and runs the driver program with clang on every push (T-0033 Follow-up (b)); if what the gate must check is not determined by #9 and the PLAN text, that is a question before a task.
- (planner, after that) Still owner-only and not yet raised: the reference oracle of `cpu_standin` (#5 A-7 "still open"; NumPy float64 would also be a new external dependency) and the tolerance vocabulary (#5 B-7). Raise them as an HQ with a BLOCKED P1-3 task; the timing slices are done with this task.
- (later, small) Use the new name of the driver source in `tests/harness/test_timing_driver.py`.

## Result
