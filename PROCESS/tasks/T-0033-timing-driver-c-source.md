---
id: T-0033
title: Add the C driver program of a timing run (hilclaw/harness/timing_driver.c) per ADR-0009, and real-clang tests that run it through run_timing
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [OD-13, NFR-3, FR-9, FR-10, C-7, "#5 A-7", "#5 A-12"]
dependsOn: [T-0013, T-0019, T-0029, T-0030, T-0031, T-0032]
touchesFiles: [hilclaw/harness/timing_driver.c, hilclaw/harness/__init__.py, tests/harness/test_timing_driver.py]
estimatedSize: {loc: 230, files: 2}   # non-test: the C source and one docstring sentence of the package file; the test file is excluded from the cap (D4)
hq: []   # implements closed decisions (ADR-0009 decisions 2-8, ADR-0008 decision 4); closes no OD, writes no ADR, C library and POSIX only, names no data-plane field
---
## Why
**ADR-0009** fixed how the timing samples of one measurement are taken from a C kernel at `cpu_standin`: a *driver program* in C, built with one kernel into a *timing executable*, run as a process of its own. T-0032 (PR #32, `c65cc1d`) landed the Python side (`hilclaw/harness/timing.py`) and pinned, by tests, the two interfaces the C side must meet: the eight-argument command line and the report form. **The C source does not exist yet**; this task writes it.

The rest of ADR-0009's code task is split once more (planner, DRIVER §6), because T-0032 reached the cap of 7 review rounds by Low / Nit items alone and this half can be verified on CI only:
- **This task (slice 2a)**: the one C source file and its tests. The tests build a timing executable by calling `clang_build.build` **directly** and run it with `timing.run_timing`. No Python module is added or edited.
- **Next task (slice 2b, not this one)**: a small Python function that builds a timing executable from the driver source and one kernel (one `clang_build.build` call) and names the driver source path for callers. It ticks PLAN P1-2.

**This task ticks no PLAN checkbox** (P1-2 "타이밍 수집" stays open until slice 2b; P1-3 stays "오너 확정 필요").

Why this item now (planner, 2026-10-07 UTC): P0.5-3 is BLOCKED on HQ-0003 (T-0014, unanswered); the C gate of P0.5-1 has no C file to build until this lands; the rest of P0.5-4 is the owner's hook registration. In P1 everything else waits for an owner item or an open OD. No open PR at planning time; no comment on #5 after the ADR-0009 notice.

A-13 check (planner's reading — the reviewer is asked to re-check): the driver uses the C library and POSIX.1-2008 only (no `-lm`, no other library), `pyproject.toml` and `.github/` are unchanged, so no new dependency; no data-plane file or field is read, written or named. The file adds **no rule and no value** to ADR-0007 / ADR-0008 / ADR-0009. ADR-0009 hands three things to "the code task": the file name (decision 2), the generator (decision 5) and the exit status values (decision 8). They are fixed here as provisional conventions of the source.

Known risks, accepted: (1) ADR-0007 / 0008 / 0009 are inside their objection windows (until 2026-10-14). (2) **The driver clone's environment has no C compiler and is Windows**: every test that builds runs on CI only. "CI 3 consecutive failures" is a BLOCKED reason (CLAUDE.md A-13) — see Process.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md — the whole record**; decisions 2-8 and 10 are the specification of the C file
- ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md — decisions 4 (prototype, byte for byte), 6 (guarantees at a call), 7; ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md — decisions 1-4, 6, 8
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `hilclaw/harness/timing.py` — the module docstring (**the command line and the report form the C side is written against**), `driver_arguments`, `parse_report`, `run_timing`, `Broken`, `TimingResult`; `hilclaw/harness/measurement.py` — `stopping_state`, `_cv`, `N_MIN`, `CV_MAX` (the rule the C side must reproduce); `hilclaw/clang_build.py` — `build`, `BuildResult`; `hilclaw/local_run.py` — `run`, `RunResult`. **None of these is edited.**
- `tests/test_clang_build.py` lines 84-97 (the `clang` fixture: skip locally, `pytest.fail` when `GITHUB_ACTIONS == "true"` and clang is absent) and the real-clang tests at its end; `tests/harness/test_timing.py` (style); `.github/workflows/ci.yml`; `pyproject.toml`
- PROCESS/tasks/T-0032-timing-run-python-side.md — `## Result` ("Command line ... as landed", "Report as the parser accepts it", Follow-ups (a), (b), (d)); PROCESS/tasks/T-0031-adr-cpu-standin-timing-run.md — `## Result` Follow-ups
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6026950959. If the owner has objected to ADR-0007 / 0008 / 0009 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
The ADRs fix the rules. The file name, the generator, the exit status values and the cases listed under "unsaid" are **conventions chosen by this task, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and an ADR disagree, **the ADR wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/harness/timing_driver.c` (new; about 200-230 lines, hard limit 280). C because it is the language of the call and ADR-0009 decision 2 requires it — one line in the commit body and `## Result`. A boilerplate comment at the top (what the file is, ADR-0009, the command line, the exit statuses); otherwise comments only where the code cannot say it.
- `hilclaw/harness/__init__.py` — only the docstring sentence that lists what the sub-package holds is brought up to date. No code.
- `tests/harness/test_timing_driver.py` (new).
- Nothing else. `pyproject.toml` has no build backend, so "how it ships with the package" (ADR-0009 decision 2) needs no change now: say so in `## Result`. The CI job `Test presence (hilclaw)` looks at `*.py` only and is not changed.

### The C source — each item is a requirement
1. **Self-contained**: `#define _POSIX_C_SOURCE 200809L` before the first include; headers of the C library and POSIX only; **no call into the mathematics library** (no `sqrt`, `fabs`, ...), so that it links without `-lm`. It declares the kernel with the prototype of ADR-0008 decision 4, **byte for byte on one line**: `void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);`. It defines `main` and no other identifier with external linkage (every helper and object is `static`).
2. **Portable C99**: compiles without a diagnostic under `-std=c99 -Wall -Wextra -Wpedantic -Werror` with clang, at `-O0` and at `-O2`. No compiler extension, no `__attribute__`, no `#pragma`.
3. **Command line**: exactly the eight arguments of the `timing.py` docstring, `<m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>`. It reads no standard input, no file and no environment variable. Integers are accepted only as decimal digits (no sign, no space, not empty) that fit their type, with overflow detected rather than wrapped; `m`, `k`, `n` at least 1; `n_min` at least 2; `n_max` at least `n_min`; `seed` any value of `uint64_t` (0 and 2^64 - 1 included); `cv_max` read with `strtod`, wholly consumed, finite and positive; `sample_form` exactly `interval` or `reciprocal`. **The driver holds no value of the policy**: no `5`, `10` or `0.05` appears as a default.
4. **Operands** (decision 5): the byte sizes of m·k, k·n and m·n `float` elements are checked against `SIZE_MAX` before allocating; three separate `malloc` calls, once; `a` and `b` filled once from the seed by a deterministic generator written in the file — every element finite, magnitude in [0.5, 1), both signs occurring; `c` is not initialised by the driver; no input value is written anywhere. Recommended generator: splitmix64, 23 bits for the magnitude (`0.5f + u * 2^-24`), one bit for the sign.
5. **Report channel** (decision 8): before the first kernel call the driver takes a descriptor of its own for the standard output it was started with (`dup(1)`) and points descriptor 1 at standard error (`dup2(2, 1)`). Every report line is written to the kept descriptor, complete and at once when its value exists (`dprintf`, or `snprintf` plus a `write` loop), never through a buffered stream that could hold it back. The lines are byte-exact to the form `parse_report` accepts: `resolution_ns <i>` (from `clock_getres(CLOCK_MONOTONIC)`, written **before** the untimed call), one `interval_ns <i>` per repeat, last `stop converged` or `stop not_converged`; one space, LF only, `<i>` as plain decimal digits.
6. **Calls** (decisions 3, 4, 6): exactly one untimed call after the operands are prepared, then the timed repeats. Between the two `clock_gettime(CLOCK_MONOTONIC)` readings of a repeat lies exactly the one call `hilclaw_gemm(m, k, n, a, b, c)`. The call stays observable without the driver reading `c` (recommended: call through a `volatile` function pointer). The interval is the difference of the readings in whole nanoseconds, computed without overflow.
7. **Stopping rule** (decision 7), evaluated after each repeat and outside every timed interval, on all samples so far, where a sample is the interval length as `double` for `interval` and `1.0 / interval` for `reciprocal`. With n samples, mean `mu` and `q = sum(((x - mu) / mu)^2)`: from n = `n_min` on, the run stops with `stop converged` at the first n where `q < cv_max * cv_max * (n - 1)` (strict, as `stopping_state`); otherwise it stops with `stop not_converged` at n = `n_max`; no repeat is taken after either. An exit status of 0 follows a `stop` line and nothing else.
8. **Failures of the driver itself** end with a non-zero exit status and one line on standard error, and write no `stop` line. Recommended values: 2 for the command line, 3 for sizes or allocation, 4 for the clock, a descriptor or a write. They are listed in the boilerplate comment.

### Cases the record leaves unsaid — choose, implement, test where a test is possible, and list each with one line of reason
- An interval of 0 ns (decision 4 "ends the run as broken"). Recommended: write the `interval_ns 0` line (decision 7: every interval read is reported), take no further repeat, exit non-zero without a `stop` line.
- Integers with leading zeros on the command line (the Python side never writes them). Recommended: refuse, mirroring `timing.py`.
- An `n_max` whose sample array cannot be allocated. Recommended: status 3.
- Whether memory is freed and descriptors are closed before exit.
- Anything else you meet. If you read one as a design choice that needs an ADR or the owner, return BLOCKED with the exact question.

### Tests (`tests/harness/test_timing_driver.py`; excluded from the size cap)
Kernels are short C sources held as strings in the test file and written to a temporary directory; they are test fixtures and get no tests of their own (test rule ⑤). A kernel needing `nanosleep` or `abort` defines its own feature-test macro. Each (kernel, flags) pair is built **once** per test session with `clang_build.build((driver, kernel), output, timeout_s=..., flags=...)`, the driver path being `Path(hilclaw.harness.__file__).parent / "timing_driver.c"`, and the test asserts `result.ok` with `result.log` as the message. Runs go through `timing.run_timing(<path of the executable>, ...)` — **the executable itself, no prefix** (T-0032 follow-up (b)) — or, for malformed command lines, through `local_run.run`. Build-and-run tests use a fixture that skips when `os.name != "posix"` or clang is absent, and calls `pytest.fail` when `GITHUB_ACTIONS == "true"` and clang is absent.

Timing on a shared runner is noisy: **no test may depend on whether a plain kernel converges**. Where a state must be asserted, the kernel fixes it by sleeping (below).

- everywhere (no compiler; runs on Windows too): the driver source exists, is ASCII, and contains the ADR-0008 prototype line byte for byte.
- happy:
  - a plain correct kernel at a small shape (for example m = k = n = 64) builds under `-std=c99 -Wall -Wextra -Wpedantic -Werror` at `-O0` and at `-O2`; a run is completed (`broken is None`), `state` is `CONVERGED` or `NOT_CONVERGED`, `N_MIN <= len(intervals_ns) <= n_max`, `len == n_max` when `NOT_CONVERGED`, every interval is a positive `int`, `resolution_ns` is an `int`, exit status 0;
  - a kernel that writes one line to standard error per call: the number of lines is `len(intervals_ns) + 1` (one untimed call, one call per repeat, no more);
  - a kernel that prints to its standard output: the run is completed and the text is found in `run.stderr`;
  - a kernel that `abort`s unless its arguments are the given `m`, `k`, `n`, every element of `a` and `b` is finite with magnitude in [0.5, 1), and both signs occur: the run is completed;
  - a kernel that writes a checksum of the bits of `a` and `b` to standard error: equal for two runs with the same seed, different for another seed; seeds `0` and `2**64 - 1` run.
- branch:
  - a kernel that sleeps a fixed time per call (long against the jitter, for example 50 ms) → completed, `CONVERGED`, under `interval` and under `reciprocal`;
  - a kernel that alternates a short and a long sleep by a call counter → completed, `NOT_CONVERGED`, exactly `n_max` intervals (with a small `n_max`, and with `n_max == N_MIN`);
  - a non-square shape with m, k, n all different.
- error / negative:
  - a kernel that never returns from its first call, small `timeout_s` → `Broken.TIMEOUT`, and `run.stdout` is exactly one `resolution_ns` line (written before the untimed call);
  - a kernel that `abort`s in its third call → `Broken.EXIT_STATUS`, and `run.stdout` is the `resolution_ns` line plus exactly one `interval_ns` line, no `stop` line (each line is written when taken);
  - dimensions whose arrays cannot be held (for example m = k = n = 2**40, and a product that overflows `size_t`) → `Broken.EXIT_STATUS`, the documented status, empty `run.stdout`, a message on `run.stderr`;
  - malformed command lines run through `local_run.run`, each asserting the documented non-zero status, an empty standard output and a non-empty standard error: seven and nine arguments, no argument; `m` = `0`, empty, `-1`, `+1`, `1x`, ` 1`, a 30-digit number; `n_max` below `n_min`; `seed` = `18446744073709551616`; `cv_max` = `x`, `0`, `-0.05`, `nan`, `inf`, `0.05x`; a `sample_form` of another word;
  - a build error is not a test target here (it is `clang_build`'s).
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① and ③ concern Python modules — none is touched, so `hilclaw/` coverage is unchanged (say so); ② happy, error, branch and negative cases as above; ④ the C file has its test file by the same naming rule; ⑤ no tests for test code, CI workflows or helper scripts.
- Keep the file's CI run time under about 30 s: small shapes, few sleeping runs, one timeout test of a few seconds.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge: `python -m pytest` exits 0 (record pass and skip counts; the build-and-run tests of the new file skip here), `python -m ruff check .` and `python -m ruff format --check .` exit 0 (ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol` shows `i/lf` for the changed files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only the files in `touchesFiles`.
- CI on the PR: `gh pr checks <PR> --watch` ends with **four** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`. **Open the log of one Python gate and confirm that the tests of `tests/harness/test_timing_driver.py` ran and passed there and were not skipped** (record the pass / skip counts of that job). Merge only then.
- After the squash-merge, check the `push` run on `main` and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- First the §3-5 landed check: `git log origin/main --grep='^Task: T-0033'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0033 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching `hilclaw/harness/` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0033-timing-driver-c-source` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0033`; executor commits end with the trailer `Task: T-0033`.
- **No local compiler.** Install nothing. Before the first push, desk-check the C file line by line against items 1-8 (headers for every function used, `size_t` / `uint64_t` conversions under `-Wextra -Wpedantic`, format specifiers, unused parameters). If a clang already exists in an environment at hand (for example `wsl.exe -e sh -c 'command -v clang'`), it may be used for a syntax check with its output outside the repository; this is optional and CI stays the verification of record. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic in it before pushing again. **Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures")** with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Ask it explicitly to (a) compare the C file with ADR-0009 decisions 2-8 sentence by sentence and with items 1-8 above; (b) compare the stopping rule with `measurement.stopping_state` / `_cv` (strict `<`, divisor n - 1, all samples so far); (c) check every report line against `timing.parse_report` and every argument against `timing.driver_arguments`; (d) re-check the planner's judgements in `## Why` (the split, the A-13 reading, each provisional convention); (e) report anything the file decides that ADR-0009 lists under Boundaries (a quantity or direction, a flag, a thread or environment setting, a defence of OD-14 / OD-16, a field of any file). If the reviewer reads (d) as a design choice needing an ADR or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the four checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0033`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the number of CI runs and failures, the exit status values as landed, the generator, the provisional choices and unsaid cases, the flags the tests build with, the verification outcomes, the language line, that no PLAN checkbox is ticked.
- Size: about 230 non-test lines in 2 files; the cap is 300 LOC / 5 files (tests excluded). If the C file would exceed 280 lines, propose a split in `Follow-ups` and finish the current scope (DRIVER §5).
- If an ADR is ambiguous or self-contradictory on a point the code must decide and that is not one of the provisional conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any Python module under `hilclaw/`: a function that builds a timing executable, a constant for the driver path (slice 2b); any edit of `timing.py`, `measurement.py`, `clang_build.py`, `local_run.py`.
- `.github/` (the C gate of PLAN P0.5-1), `pyproject.toml`, packaging of non-Python files.
- Build settings: the tests choose flags for themselves and decide nothing for callers (no `-march`, no OpenMP, no thread count, no language standard for kernels).
- The verification half of the harness: verification inputs, the reference oracle, the tolerance, a correctness verdict, the calibration kernels (PLAN P1-3 "오너 확정 필요", P1-4). The plain kernel of the tests is a fixture; its output is not judged.
- The quantity, its unit and direction, a default sample form (OD-1); the seed policy (OD-13 ⑦); calls per repeat as a parameter (OD-13 ⑧); time-limit values, sandbox, resource limits (OD-14); any defence against forged timing (OD-16); what is kept of a broken run (OD-10).
- Fields of `sim.json` / `board.json` / `instance.json` / events (P1-8); an FR-10 tool contract (P1-1, OD-18).
- Any ADR, the OD register, README.md, CLAUDE.md, DRIVER.md, PLAN.md, the skills, the agents.

## Follow-ups
- (planner, next — code mode, slice 2b) A small Python function under `hilclaw/harness/` that builds a timing executable from `timing_driver.c` and the sources of one kernel with one `clang_build.build` call (flags, trailing flags, compiler, time limit, output path, `cwd`, `env` handed over unchanged; no flag added), with stub-compiler tests that run everywhere and one real-clang test. It ticks PLAN P1-2.
- (planner, after that) The C gate of PLAN P0.5-1: what "clang 빌드 + 하네스 통과" adds beyond the Python gate that already runs these tests.
- (planner) Still owner-only and not yet raised: the reference oracle of `cpu_standin` (#5 A-7 "still open"; NumPy float64 would also be a new external dependency) and the tolerance vocabulary (#5 B-7). Raise them as an HQ with a BLOCKED P1-3 task once the timing slices are done.

## Result
