---
id: T-0061
title: Add the run side of a verification run (hilclaw/harness/verification.py) per ADR-0017 - start an already built verification executable, check the form of its report and the check values, and give the verdict with the per-draw counts
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-9, OD-16, OD-5, C-7, "#5 A-7", "#5 B-7", "#5 A-12"]
dependsOn: [T-0019, T-0036, T-0059, T-0060]
touchesFiles: [hilclaw/harness/verification.py, hilclaw/harness/__init__.py, tests/harness/test_verification.py]
estimatedSize: {loc: 250, files: 2}   # non-test: the new module and one docstring sentence; the test file is excluded from the cap (D4)
hq: []   # implements accepted decisions (ADR-0017 decisions 4-7, 9) on top of T-0059 / T-0060; closes no OD, writes no ADR, adds no dependency, names no data-plane field
---
## Why
**ADR-0017** (accepted 2026-10-08, with the owner's HQ-0004 answers) fixed the verification run of a C `gemm` kernel at `cpu_standin`. Two slices are on `main`:
- slice 1 (T-0059, `de54c66`): `hilclaw/harness/verification_program.c`, the C program that draws the inputs, reports a check value per draw and writes the kernel's output;
- slice 2 (T-0060, `c8a6f65`): `hilclaw/harness/verification_arrays.py`, the array side in NumPy (`draw_inputs`, `check_value`, `reference`, `check_tolerance`, `count_failures`) and the pin `numpy==2.4.6`.

**Nothing joins them yet**: no code starts the process, checks the report, compares the check values or says pass / fail / broken. PLAN P1-3 stays open for it, and P1-4 (three-state calibration), the "harness pass" half of the C gate (P0.5-1) and P2-3 / P2-5 wait behind it.

This task is **slice 3a: the run over an already built verification executable**, in one new module, as `hilclaw/harness/timing.py` (T-0032) is for a timing run.

**Planner's split of "slice 3"** (the notes of T-0059 / T-0060 named one slice for the build and the run): the run alone is about 250 non-test lines (`timing.py` is 262), and the build function with its docstring is about 80 more (`timing_build.py` is 82) - together over the cap of 300 (DRIVER §5, D4), and T-0032 reached the 7-round review limit at that size. So:
- **this task (3a)**: the run, its stand-in-program tests that run everywhere, and real-clang tests that build by calling `clang_build.build` directly (as `tests/harness/test_verification_program.py` does) and show that the two generators agree;
- **slice 3b (not this one)**: `hilclaw/harness/verification_build.py` - the one `clang_build.build` call of ADR-0017 decision 2, the mirror of `timing_build.py`. **It ticks PLAN P1-3.**

**This task ticks no PLAN checkbox.**

A-13 check (planner's reading - the reviewer is asked to re-check):
- No new dependency: `numpy` is already pinned; the module uses the standard library, `numpy`, `hilclaw.local_run` and `hilclaw.harness.verification_arrays`. `pyproject.toml` and `.github/` are unchanged.
- No data-plane file or field is read, written or named. The result type is an interface inside the harness (decision 7: "is not a file or a field of the data plane"). The module adds **no rule and no value** to ADR-0017.
- What the record leaves to the code and this task fixes as **provisional conventions of the source** (each stated with one line of reason in the commit body, the PR body and `## Result`): the module and its public names, the names and the order of the broken conditions, the spelling of the result type, and the cases under "unsaid" below.

Known risks, accepted: (1) the record's own choices of ADR-0017 are inside their objection window (until 2026-10-15). (2) The command line, report form and exit statuses of T-0059 and the names of T-0060 are provisional conventions; this module follows them as landed. (3) The driver machine is Windows without a C compiler: the real-clang tests run on CI only.

Note on the test rules: `hilclaw/harness/` is the verification harness of the product (FR-9, layer 2), not the test harness of this repository; tests of it are required.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md - the whole record**; decision 7 sentence by sentence (completed / broken, the verdict, what the Python side returns), decisions 4 (input check: a disagreement is broken, never a fail), 5 (the tolerance is refused before a process is started; it is not passed to the program), 6 (no defaults), 9 (parameters), 10 (limits; the Python-side work is bounded by nothing here); Boundaries
- **PROCESS/tasks/T-0059-verification-program-c-source.md - `## Result`**: "Conventions as landed" (command line, report of `draws * (4 + 4*m*n) + 4` bytes, end mark `end\n`, exit statuses), "Notes for slices 2 and 3", follow-ups (b) and (c)
- **PROCESS/tasks/T-0060-verification-arrays-numpy-pin.md - `## Result`**: "Public names and signatures as landed", "Cases the record leaves unsaid", follow-ups (a) and (b), "Local verification"
- `hilclaw/harness/verification_arrays.py` (whole file) and `hilclaw/harness/verification_program.c` (header comment, lines 1-55). **Not edited**
- `hilclaw/harness/timing.py` (whole file) - the model of this module: docstring sections, `Broken`, the result type, the `executable` prefix, the order of refusals, `_digits`. **Not edited**
- `hilclaw/local_run.py` - module docstring, `run`, `RunResult`. **Not edited**. `hilclaw/clang_build.py` - `build`, `BuildResult` (used by the tests only)
- `tests/harness/test_timing.py` - `STAND_IN`, the plan file, how a stand-in program is started as a command prefix on every platform, the signal cases; `tests/harness/test_verification_program.py` - the kernel template, `KERNELS`, the `clang` fixture (skip locally, `pytest.fail` on CI), the once-per-session build. **Neither is edited; nothing is imported from them**
- `hilclaw/harness/__init__.py`; `pyproject.toml`; `.github/workflows/ci.yml` (the six jobs)
- CLAUDE.md - 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- Issue #5: every comment after the ADR-0017 notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6053035869 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`; it was the last comment at planning time, 2026-10-08T07:18Z). If the owner has objected to ADR-0017 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0017 fixes the rules. Names, signatures and the cases under "unsaid" are **conventions chosen by this task, provisional**. Where a criterion below and the ADR disagree, **the ADR wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/harness/verification.py` (new; about 220-250 lines with its docstring, hard limit 280). Python because it is the Python side of the record, on top of `verification_arrays.py` and `local_run.py` - one line in the commit body and `## Result`.
- `hilclaw/harness/__init__.py` - only the docstring sentence that lists what the sub-package holds. No code, **no import of the new module** (the state of T-0060: `numpy` is imported only by modules that need it).
- `tests/harness/test_verification.py` (new).
- Nothing else.

### The module - each item is a requirement
The recommended names are provisional; the behaviour is not.

1. **Docstring**: what the module is (the Python side of a verification run of ADR-0017 over an executable that is already built); the command line of the verification program and the byte form of a complete report as landed in T-0059 (or by pointing at the header of `verification_program.c`); "Conventions of this module"; "What this module does not do". Otherwise comments only where the code cannot say it.
2. **`program_arguments(*, m, k, n, draws, seed)` -> tuple of five `str`**: `<m> <k> <n> <draws> <seed>` in decimal digits, exactly what the program accepts. `m`, `k`, `n` are `int` >= 1; `draws` an `int` with 1 <= `draws` <= 2**64 - 1; `seed` an `int` with 0 <= `seed` <= 2**64 - 1; a `bool` is not an `int` (`type(value) is int`, the rule of `timing.py` and `verification_arrays.py`). Anything else raises `verification_arrays.VerificationArgumentError` naming the argument (recommended: reuse that class, so a caller catches one class for the whole verification; say so). An `int` the interpreter cannot write in decimal digits is refused the same way (as `timing._digits`). **No tolerance is among the arguments** (decision 5).
3. **`run_verification(executable, *, m, k, n, draws, seed, rtol, atol, timeout_s, cwd=None, env=None)` -> a result** (item 7). **`draws`, `seed`, `rtol`, `atol` and `timeout_s` have no default** (decisions 6 and 9). `executable` is a `str` or `os.PathLike`, or a non-empty sequence used as the start of the command, exactly as in `timing.run_timing`. `timeout_s`, `cwd` and `env` are handed to `local_run.run` unchanged; the module sets no environment variable.
4. **Refused before a process is started**, in this order: the arguments of item 2; the tolerance, through `verification_arrays.check_tolerance` (decision 5: "refused before a process is started"); the `executable` (`TypeError` / `ValueError` as in `timing.py`); then whatever `local_run.run` raises for the command and the time limit, passed on.
5. **One process**, started once through `local_run.run((*prefix, *arguments), timeout_s=..., cwd=..., env=...)`. Standard error is never parsed. No retry.
6. **Completed or broken** (decision 7), tested in this order, the first failed condition being the one reported:
   - `TIMEOUT`: the run timed out;
   - `EXIT_STATUS`: the exit status is not 0 (a signal is not told apart; `returncode` shows it);
   - `REPORT_FORM`: the captured standard output is not **exactly** `draws * (4 + 4*m*n) + 4` bytes ending in the four bytes `end\n`. The length is computed with Python integers from `m`, `n` and `draws` alone; **no output byte is interpreted to find a boundary**, and nothing is allocated from the expected length;
   - `CHECK_VALUE`: for some draw, the four bytes at the start of its block, read as a `uint32_t` in the byte order of the host (`struct` format `=I`), differ from `verification_arrays.check_value` of the arrays `verification_arrays.draw_inputs(m, k, n, seed=seed, draw=d)` gives.
   Every other run is completed. A status of 0 alone is not enough (a kernel can call `exit(0)`): the form is always checked.
7. **Verdict and result** (decision 7). For a completed run: per draw `d`, in order, the output is the `4*m*n` bytes after the check value viewed as a `float32` array of shape `(m, n)` in the byte order of the host (`numpy.frombuffer`, no copy needed), the reference is `verification_arrays.reference(a, b)`, and the counts are `verification_arrays.count_failures(output, expected, rtol=rtol, atol=atol)`. The verdict is **pass** iff `failed` is 0 for every draw, otherwise **fail**; no partial verdict. Recommended form:
   - `class Broken(enum.Enum)`: `TIMEOUT`, `EXIT_STATUS`, `REPORT_FORM`, `CHECK_VALUE`;
   - `class Verdict(enum.Enum)`: `PASS`, `FAIL`;
   - `class VerificationResult(NamedTuple)`: `broken: Broken | None`, `verdict: Verdict | None`, `counts: tuple[Counts, ...] | None`, `run: local_run.RunResult`. Completed: `broken` is `None`, `verdict` is set, `counts` has exactly `draws` entries. Broken: `broken` is set, `verdict` and `counts` are `None` - **also when the draws it did report hold an element outside the tolerance or all pass** (decision 7: a broken run is neither pass nor fail).
8. **What the result holds of the runner's capture.** Decision 7: for a broken run the Python side returns "what the runner captured **apart from the report**", and "the harness itself puts no element of `a`, `b` or the reference into what it returns". Recommended (provisional): `run` is the `RunResult` of the runner **with `stdout` replaced by `b""`** (`run._replace(stdout=b"")`), so `returncode`, `timed_out`, `stderr`, `command` and `duration_s` are passed on unfiltered and the report bytes are not. The record names the runner's capture only for a broken run; carrying the same member for a completed run is this task's convention (the caller needs the status, the duration and standard error there no less, and the record already says they are "passed on unfiltered" and bind the caller). State both in the docstring and in `## Result`. The module keeps no array of a draw after its counts are taken.
9. **Memory and time**: one draw is regenerated and compared at a time; the arrays of a draw are not kept for the next. The Python-side work has no time limit of its own (decision 10) - say so in "What this module does not do"; add none.
10. **What the module does not hold**: no build, no path of the program, no tolerance value, no seed value or source of a seed, no number of draws, no dimension of an instance, no default for any of them, no index or deviation in what it returns, no retry, no storing of anything, no file.

### Cases the record leaves unsaid - choose, implement, test where a test is possible, and list each with one line of reason
- Whether the check values of all draws are compared before the first reference is computed, or draw by draw (either gives the same result; recommended: draw by draw, returning `CHECK_VALUE` at the first disagreement and discarding the counts taken so far).
- What NumPy raises on the Python side for arrays it cannot allocate (recommended: passed on, as in `verification_arrays.py`; say what a caller sees).
- A report that is of the exact length with a wrong end mark; a report longer than expected whose first bytes are a complete report (both `REPORT_FORM`).
- Output bytes whose offset in the report is not a multiple of 4 (NumPy reads an unaligned buffer; no copy is required, one is allowed).
- Anything else you meet. If you read one as a design choice that needs an ADR or the owner - in particular anything under ADR-0017 Boundaries or sub-questions 5 and 6 (where a seed comes from, whether a seed or the capture is recorded, the number of draws, the flags of the two builds), a tolerance value or default, a time-limit value, anything returned beyond the verdict, the counts and the runner's capture, or anything that reads as a request, result member or failure kind of `correctness.check` (ADR-0016) - do not choose: return BLOCKED with the exact question.

### Tests (`tests/harness/test_verification.py`; excluded from the size cap)
**Stand-in-program tests run everywhere** (no compiler; Windows too): a small Python script started as a command prefix (`(sys.executable, script)`), which records its arguments, working directory and one environment variable, writes planned bytes to standard output and standard error, and ends by a planned status, signal or sleep - the technique of `tests/harness/test_timing.py` (write this file's own copy; import nothing from that file). The reports the stand-in writes are built in the test from `verification_arrays.draw_inputs`, `check_value` and `reference` (they have their own tests against an independent implementation in T-0060; this file does not re-test them). Use small shapes with `m`, `k`, `n` all different.

- happy (stand-in):
  - a report whose outputs are the reference rounded to `float32`, for `draws` 1 and 3, under a tolerance the test chooses (`atol` > 0, decision 5): `broken` is `None`, `verdict` is `PASS`, `counts` has `draws` entries, each `(0, 0)`;
  - the stand-in received exactly the five arguments `m k n draws seed` as decimal digits and nothing else (no tolerance), for seeds `0` and `2**64 - 1`; `cwd` and `env` reached it; `executable` given as a path-like prefix and as a sequence;
  - `result.run`: `stdout` is `b""`, `stderr` is what the stand-in wrote (unparsed, also when it looks like a report), `command`, `returncode`, `timed_out`, `duration_s` are the runner's;
  - `program_arguments` returns the five strings for ordinary and extreme valid values (`draws` `2**64 - 1`, `seed` `2**64 - 1`).
- branch (stand-in):
  - one element outside the tolerance in the second of three draws: `FAIL`, counts `(0, 0), (1, 0), (0, 0)`; several draws failing; a NaN and an infinity in an output: counted in `failed` and `non_finite`; every element the NaN fill: `failed` = `non_finite` = `m*n` in every draw;
  - `rtol` = `atol` = 0 with an output that equals the reference exactly (a hand-chosen report) passes; integer tolerances;
  - a shape with a dimension of 1, and `1 1 1`.
- error / broken (stand-in), each asserting `broken`, `verdict is None`, `counts is None`:
  - `TIMEOUT`: the stand-in sleeps past a small `timeout_s`; also when it had already written a complete, passing report;
  - `EXIT_STATUS`: a non-zero status with a complete, passing report; a signal (POSIX only);
  - `REPORT_FORM` with status 0: empty output; the first draw complete and nothing more (the `exit(0)` case); one byte short; one byte long; a complete report followed by a second end mark; the exact length with another end mark; the end mark alone for `draws` >= 1;
  - `CHECK_VALUE`: a wrong check value in the first draw and in the last, with outputs that would pass and with outputs that would fail; a report that is right for another seed (the check value of a draw covers the words of `a` and `b` in one sequence, so it does not depend on where the cut between them lies: do not expect `CHECK_VALUE` from exchanged dimensions);
  - order: timed out with a non-form output is `TIMEOUT`; a non-zero status with a non-form output is `EXIT_STATUS`; a non-form output with a wrong check value is `REPORT_FORM`.
- negative (nothing is started - assert that the stand-in left no record):
  - `m`, `k`, `n`: `0`, `-1`, `1.0`, `"1"`, `True`, `None`, an `int` too long to write; `draws`: `0`, `-1`, `2**64`, `True`, `1.0`; `seed`: `-1`, `2**64`, `1.5`, `True` - `VerificationArgumentError` naming the argument (match the `<name>: ` prefix only), through `program_arguments` and through `run_verification`;
  - `rtol` and `atol`: negative, NaN, an infinity, `True`, `"0.1"`, `None` - `VerificationArgumentError` naming the parameter;
  - a call without `rtol`, without `atol`, without `seed`, without `draws` or without `timeout_s` raises `TypeError` (no default);
  - an empty `executable` sequence (`ValueError`), an `executable` that is neither a path nor iterable (`TypeError`), a program that does not exist (`local_run.ProgramNotFoundError`), a `timeout_s` of 0 or of a wrong type (what `local_run.run` raises).
- **real clang** (CI only: a fixture that skips when `os.name != "posix"` or clang is absent, and calls `pytest.fail` when `GITHUB_ACTIONS == "true"` and clang is absent). Kernels are short C strings in this file; each (kernel, flags) pair is built once per session with `clang_build.build((program, kernel), output, timeout_s=..., flags=...)`, the program path being `Path(hilclaw.harness.__file__).parent / "verification_program.c"`; the test asserts `result.ok` with `result.log` as the message. The executable itself is passed, no prefix.
  - **the two generators agree**: a plain triple-loop `gemm` kernel at a non-square shape, for seeds `0`, `1`, `2**63`, `2**64 - 1` and `draws` 1 and 3: the run is completed (so every check value of the C program equals the one of the Python generator) and the verdict is `PASS` under a tolerance the test chooses (`atol` > 0; a test value, not a tolerance of the harness); once more at a larger shape (for example 64 x 48 x 80) and with the program built with `-O2 -ffast-math`;
  - a kernel that computes something else (for example leaves out the last term of each sum, or copies `a`): `FAIL` with `failed` > 0 in every draw and `non_finite` 0;
  - a kernel that writes nothing: `FAIL`, `failed` = `non_finite` = `m*n` in every draw;
  - a kernel that never returns: `TIMEOUT`; one that `abort`s in its second call: `EXIT_STATUS`; one that calls `exit(0)` in its first call: `REPORT_FORM`; one that prints to standard output and to standard error: completed, the text in `result.run.stderr`.
  - The fixture kernels are test code: they are not the calibration kernels of ADR-0003 (PLAN P1-4) and get no tests of their own.
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① the coverage of `hilclaw/` stays >= 80% lines and functions (aim at every line of the new module **from the stand-in tests alone**, since the coverage job also has clang but local runs do not; the job `Coverage gate (hilclaw)` must stay green - record its two percentages); ② happy, error, branch and negative cases as above; ③ every public function of the new module is tested; ④ the new module has its test file at `tests/harness/test_verification.py` (the job `Test presence (hilclaw)` checks it); ⑤ no tests for test code (the stand-in program, the fixture kernels), the CI workflow or helper scripts.
- Keep the file's CI run time under about 30 s (one timeout test of a few seconds per kind; small shapes): the suite runs in three jobs.

### Verification (record summary lines and run URLs in `## Result`)
- Local Python environment: the suite needs the pinned `numpy` 2.4.6. **Do not change the user-level Python environment of the driver machine** (it holds numpy 2.5.2). Use a venv **outside the repository**: the one T-0060 left in place (`C:\Users\myung\AppData\Local\Temp\claude\C--Users-myung-HIL-Claw-driver\62adb481-ac07-4add-b2d0-508a61831447\scratchpad\venv-t0060`) if it still exists and holds numpy 2.4.6, pytest 9.1.1 and ruff 0.16.10; otherwise create one in the session scratchpad (`--group dev` and the pinned `numpy` with `--only-binary=:all:`). Record which was used and `numpy.__version__`. Nothing is installed into the tree; leave the venv in place (no recursive delete).
- Local, before the commit and before the merge: `python -m pytest` exits 0 (record pass and skip counts; the real-clang tests of the new file skip here), `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- `git ls-files --eol` shows `i/lf` for the changed files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only the files in `touchesFiles`.
- CI on the PR: `gh pr checks <PR> --watch` ends with **six** successful checks on the final head - `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`, `Coverage gate (hilclaw)`. **Open the log of both Python gates and of the coverage gate and confirm that the tests of `tests/harness/test_verification.py` ran and passed there with no skip** (record the pass / skip counts and the two coverage percentages). Merge only then.
- After the squash-merge, check the `push` run on `main` and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- First the §3-5 landed check: `git log origin/main --grep='^Task: T-0061'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0061 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching `hilclaw/harness/` is BLOCKED "open PR conflict"). The unmerged remote branches `claude/dazzling-wu-a91228` and `feature/uc-alignment` are not PRs of this task.
- Code mode: branch `claude/T-0061-verification-run-python-side` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0061`; executor commits end with the trailer `Task: T-0061`.
- **No local compiler.** Install nothing. A clang that already exists at hand (the WSL distribution of the driver machine had clang 14 in T-0059) may be used for an optional check with its output outside the repository; CI stays the verification of record. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic in it before pushing again. **Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures")** with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Ask it explicitly to (a) compare the module with ADR-0017 decision 7 sentence by sentence - the four conditions of a completed run and their order, the verdict, no partial verdict, a broken run neither pass nor fail, what is returned - and with decisions 4-6 and 9 (the tolerance refused before the start and never passed to the program, no default); (b) compare the report handling with the header of `verification_program.c` (length, end mark, the place and byte order of a check value, the layout of an output) and confirm that no output byte is interpreted to find a boundary; (c) re-check item 8 (the report bytes are not in the result; the same member for a completed run) against decision 7; (d) re-check the planner's judgements in `## Why` (the split into 3a / 3b, the A-13 reading, each provisional convention); (e) report anything the module decides that ADR-0017 lists under Boundaries or leaves open by name, or that reads as a part of the `correctness.check` contract. If the reviewer reads (c), (d) or (e) as a design choice needing an ADR or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED - do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the six checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0061`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** - the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the number of CI runs and failures, **the public names and signatures as landed** (slice 3b, P1-4 and the C gate are written against that text), the broken conditions and their order, what `run` holds, the unsaid cases, the verification outcomes, the language line, that no PLAN checkbox is ticked.
- Size: about 250 non-test lines in 2 files; the cap is 300 LOC / 5 files (tests excluded). If the module would exceed 280 lines, propose a split in `Follow-ups` and finish the current scope (DRIVER §5).
- If ADR-0017 is ambiguous or self-contradictory on a point the code must decide and that is not one of the provisional conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Slice 3b: `hilclaw/harness/verification_build.py` (the function that builds a verification executable by one `clang_build.build` call, a constant for the program's path). The tests of this task call `clang_build.build` directly.
- Any edit of `verification_arrays.py`, `verification_program.c`, `timing.py`, `timing_build.py`, `timing_driver.c`, `measurement.py`, `clang_build.py`, `local_run.py` and their tests; `pyproject.toml`, `.github/`, any dependency or pin.
- The calibration kernels of ADR-0003 and their tests (PLAN P1-4); the "harness pass" half of the C gate (P0.5-1).
- Everything ADR-0017 leaves open: other shapes (OD-16 sub-question 1), the relation to timing inputs (OD-13 sub-question 7), where a seed comes from, the number of draws and what is recorded of a run (OD-16 sub-question 5), the flags of the two builds (sub-question 6), non-finite or corner-case inputs, tolerance values, time-limit values, what is returned beyond the counts (indices, the largest deviation), a bound on the Python-side work, a sandbox (OD-14), what is kept of a broken run (OD-10).
- Fields of `eval.json` / `sim.json` / `board.json` / `instance.json` / events (P1-8); the contract of `correctness.check`, the harness / backend split, a tool registration (P1-1, OD-18).
- Any ADR, the OD register, README.md, CLAUDE.md, DRIVER.md, PLAN.md, the skills, the agents.

## Follow-ups
- (planner, next - code mode, slice 3b) `hilclaw/harness/verification_build.py`: `PROGRAM_SOURCE` and a function that builds a verification executable from the verification program and the sources of one kernel by exactly one `clang_build.build` call, no flag added (ADR-0017 decision 2; the mirror of `timing_build.py`, T-0034), with stand-in-compiler tests everywhere and a real-clang test that builds with it and runs `run_verification`. **Ticks PLAN P1-3.**
- (planner) Then P1-4 (three calibration kernels, `atol` > 0 in the tests) and the "harness pass" half of the C gate (ticks P0.5-1).
- (planner, independent) Slice 3 of ADR-0016: the path of a HW tool over a backend, checked through both fronts by a test-only tool with the mock, written against the call forms in T-0058 `## Result` (code mode, PLAN P1-1).
- (integrator or planner, document mode) Still open from T-0059 / T-0060: README "로컬 검사" names the install of the runtime dependency; the annotations of ADR-0010 / ADR-0015; the note on ADR-0017 decision 3 ("two draws of one run differ").

## Result
