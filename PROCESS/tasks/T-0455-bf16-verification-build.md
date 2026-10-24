---
id: T-0455
title: Add hilclaw/harness/bf16_verification_build.py, which builds the bf16 verification program of one kind with one kernel into one executable (ADR-0163 code slice 4)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0454]
touchesFiles: [hilclaw/harness/bf16_verification_build.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_verification_build.py]
estimatedSize: {loc: 130, files: 2}
hq: []
---
## Why

**State on `main` `379745f`.** ADR-0163 (T-0451, `c004ccc`) records the verification run of one built bf16 kernel on `cpu_standin` for `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. Three code slices have landed:
- T-0452 (`cafb152`): the array side, `hilclaw/harness/bf16_verification_arrays.py`.
- T-0453 (`5e40098`): the shared header `hilclaw/harness/bf16_verification.h` and the `gemm` program `bf16_verification_gemm.c`.
- T-0454 (`d6a2a0f`): the `rmsnorm`, `elementwise_add` and `swiglu` programs.

**This task is the fourth slice: the build.** ADR-0163 decision 2 says each kernel is "built with its program by one call of `clang_build.build` with the caller's flags", and its Consequences list "its build, as `verification_build.py` builds the first case's" as one code slice. Today only the tests build the bf16 programs, by calling `clang_build.build` directly. This slice adds the package module that does it, so the next slice (the report reader and the verdict over an executable, ADR-0163 decision 8) has an executable to run that the package itself builds.

The module mirrors `hilclaw/harness/verification_build.py` (93 lines). The one difference is that the caller names the **kind**, and the module picks that kind's program source (one program per kind, ADR-0163 decision 2). Like the first case's module, it adds no flag. ADR-0163 decision 2 rejects a define chosen at build time because the harness would add a flag ("The harness adds no flag", `verification_build.py`, cited by ADR-0107 Context). So `-lm` for a SwiGLU kernel that calls `expf` stays among the caller's trailing flags (ADR-0163 decision 2, last bullet but two).

**Size.** About 100 lines for the module plus a few lines of the package docstring. That is 2 files, well under the cap of 300 lines in 5 files. The report reader and verdict (the counterpart of `verification.py`, 323 lines) would push the cap if added here, so they stay in the next slice.

**Later slices (not here):**
- the report reader and the verdict over an executable (the counterpart of `verification.py`, ADR-0163 decision 8);
- the twelve calibration kernels of ADR-0163 decision 9 and their tests.

**PLAN order and D18.** This is the "하네스 검증" of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items, and P2-14 needs them, so the D18 rule does not apply. Unresolved HQs still hold the round-loop items and P2-5: HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4. Work therefore continues on P2-11 to P2-14, as for T-0451 to T-0454.

**D16.** The module calls the local `clang` through `clang_build.build`. The tests build stub kernels that the tests write and run them as local processes. Nothing starts `claude` or needs a board, a model file or an API key. Where `clang` is absent, the clang tests skip locally and fail on CI, as `tests/harness/test_bf16_verification_programs.py` does.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit;
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules. Branch `claude/T-0455-<slug>`; commit trailer `Task: T-0455`; code mode, so a Draft PR whose body ends with `Task: T-0455`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화" (a module docstring may be long), "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure, code mode).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - decision 2 (lines 44-53): one program per kind, the rejected build-time define, one kernel per executable built "by one call of `clang_build.build` with the caller's flags", and the `-lm` bullet;
  - decision 10 (lines 145-155): flags, trailing flags, compiler, build time limit, path of the executable, environment and working directory are the caller's;
  - Consequences (line 186) and Boundaries (lines 195-207), in particular "Build settings and OpenMP" and "How a check or an instance reaches these runs".
- `hilclaw/harness/verification_build.py`: the whole file (93 lines). It is the model for the module: the docstring, the argument handling of `kernel_sources`, the `parameter` attribute and the single handover to `clang_build.build`.
- `tests/harness/test_verification_build.py`: the whole file (718 lines). It is the model for the tests: the stub compiler (`Stub`, `PRELUDE`), the `kernel`, `out` and `clang` fixtures, the handover tests with a monkeypatched `clang_build.build`, the refusals and their `parameter`, and the real-clang tests.
- `hilclaw/clang_build.py`: lines 1-20 and the `build` docstring (from line 196).
- `hilclaw/harness/bf16_verification_arrays.py`: `KINDS` (line 92). Read the module docstring's first paragraph (lines 1-11) only to see that this module imports NumPy.
- `hilclaw/harness/bf16_verification_gemm.c` and `hilclaw/harness/bf16_verification_swiglu.c`: the header comment of each (the command line, the exit statuses and the report), and line 42 of the latter: each program includes `"bf16_verification.h"` with quotes, which the compiler finds next to the program source, so no `-I` is needed.
- `tests/harness/test_bf16_verification_programs.py`: lines 1-80 and the session build fixture around line 304. They show the stub kernels per kind and the `-lm` in `trailing_flags`.
- `hilclaw/harness/__init__.py`: the package docstring (lines 1-23).
- `tests/test_instance_start.py` line 375: an example of checking in a fresh interpreter that an import does not load `numpy`.

## Acceptance Criteria

1. **New module `hilclaw/harness/bf16_verification_build.py`**, in Python (it wraps `clang_build.build` as `verification_build.py` does; say this in one line of the commit body). It holds:
   - **`PROGRAM_SOURCES`**: a read-only mapping (for example `types.MappingProxyType`) from each kind to the `Path` of its program, next to the module: `"gemm"` → `bf16_verification_gemm.c`, `"rmsnorm"` → `bf16_verification_rmsnorm.c`, `"elementwise_add"` → `bf16_verification_elementwise_add.c`, `"swiglu"` → `bf16_verification_swiglu.c`. Its keys appear in the order of `bf16_verification_arrays.KINDS`.
   - **`build_bf16_verification_executable(kind, kernel_sources, output, *, timeout_s, flags=(), trailing_flags=(), compiler=None, cwd=None, env=None)`**. It makes one call `clang_build.build((PROGRAM_SOURCES[kind], *kernel_sources), output, ...)` with every other argument handed over unchanged, and returns the `BuildResult` as it is. A compile failure, a link failure or a timeout is a result with `ok` false.
2. **`kind`** is tested first, before every other argument. It must be exactly a `str` that is a key of `PROGRAM_SOURCES`. Anything else raises `ValueError` before anything is started, with the attribute `parameter` set to `"kind"`. That covers an unknown name, a different case such as `"GEMM"`, a `str` subclass, `bytes` and `None`. The message names the accepted kinds.
3. **`kernel_sources`** is handled exactly as `verification_build.build_verification_executable` handles it:
   - one path (`str` or `os.PathLike`) or a non-empty iterable of paths;
   - `ValueError` for no kernel source, tested right after `kind`, with no `parameter`;
   - `TypeError` for a value that is neither a path nor iterable, with `parameter` `"kernel_sources"`, and the same attribute on any `TypeError` or `ValueError` raised while iterating it;
   - whatever `clang_build.build` raises is passed on unchanged with its own attributes, including `FileNotFoundError` for a program source missing from the installation.
4. **Command and flags.** The program source comes first among the sources. The module adds no flag, no `-I`, no define and no `-lm`. Flags, trailing flags, the compiler, the time limit, the output path, `cwd` and `env` are the caller's, with the defaults of `clang_build.build`.
5. **No NumPy.** The module does not import `numpy`, `bf16_verification_arrays` or `verification_arrays`, so `import hilclaw.harness.bf16_verification_build` in a fresh interpreter leaves `numpy` out of `sys.modules`. The `__init__.py` claim that exactly three modules of the harness import `numpy` stays true.
6. **Module docstring**, in the form of `verification_build.py`'s:
   - the rule (ADR-0163 decisions 2 and 10);
   - the command, with the kind's program source first;
   - that the harness adds no flag, so a kernel that needs the math library (a SwiGLU kernel calling `expf`, an RMSNorm kernel using `<math.h>`) needs the caller's `-lm` in `trailing_flags`;
   - that the header is found next to the program sources;
   - the conventions (the program first, sources not compared);
   - what the module does not do: it chooses no flag, compiler, time limit or output path; it runs nothing it built; it does not retry, repair or store a failed build; it reads no configuration or environment variable of its own; it relates this build to no timing build; and it registers no kind with `correctness.check`, `spec.write` or the instance start (ADR-0163 Boundaries).
7. **`hilclaw/harness/__init__.py`**: add the new module to the docstring, next to the bf16 C sources (for example "… and the build of a bf16 verification executable from one of them (`hilclaw.harness.bf16_verification_build`)"). Keep the sentence about the three modules that import `numpy` true. No other Python module changes behaviour.
8. **Size**: at most 300 changed lines outside tests, in at most 5 files. Expected: the new module and the `__init__.py` docstring.
9. **Tests**, in the new file `tests/harness/test_bf16_verification_build.py`. Follow `tests/harness/test_verification_build.py` and D12 (DRIVER §5): happy, error, branch and negative cases, and every public name of the new module. Parametrize over the four kinds where the behaviour is the same. At least:
   - **Program sources**: `PROGRAM_SOURCES` has exactly the keys of `bf16_verification_arrays.KINDS`, in that order. Each value is the existing `.c` file of that name in the directory of `hilclaw.harness`, and `bf16_verification.h` is in the same directory. The mapping cannot be assigned to.
   - **Handover**: with a monkeypatched `clang_build.build`, one call per build. Its sources are `(PROGRAM_SOURCES[kind], *kernel_sources)` with the kind's own program, and every other argument is handed over unchanged, by identity where the caller's object can be passed through. The defaults are those of `clang_build.build`. The returned object is the one `clang_build.build` returned.
   - **Stub compiler** (the `Stub` pattern of `test_verification_build.py`, no `clang` needed): the command line holds the flags, the kind's program source, the kernel sources in the order given and the trailing flags, and nothing that the module added. `cwd` and `env` reach the compiler. A failed build and a timeout are results with `ok` false.
   - **`kernel_sources` forms**: `str`, `Path`, list, tuple and generator.
   - **Refusals of `kind`**: an unknown name, `"GEMM"`, `""`, a `str` subclass instance, `b"gemm"`, `None` and `7`. Each raises `ValueError` with `parameter == "kind"` before anything is started, which a monkeypatched `clang_build.build` that fails the test shows. `kind` is tested before an empty `kernel_sources` and before a missing `timeout_s` value would matter.
   - **Refusals of `kernel_sources`**: no source (`()`, `[]`, an empty generator, `b""`) gives `ValueError` without `parameter`. Values that cannot be iterated give `TypeError` with `parameter == "kernel_sources"`. An error raised during iteration keeps or gets that attribute as in the model tests. A `bytes` path keeps the `parameter` of `clang_build.build`.
   - **Errors passed on**: a missing kernel source, a missing program source (monkeypatch one entry by replacing `PROGRAM_SOURCES` in the module), a flag that sets the output, and a `timeout_s` that is not a positive finite number. Each is the error of `clang_build.build`.
   - **No NumPy**: a fresh interpreter (`sys.executable -I` with the repository on the path, or the pattern of `tests/test_instance_start.py`) imports the module and finds no `numpy` in `sys.modules`.
   - **Real clang, per kind** (skip without a POSIX system or without `clang`, fail on CI without `clang`, as `test_bf16_verification_programs.py` does): build a small stub kernel of the kind's prototype that copies its first operand to the output. Use `-std=c99 -Wall -Wextra -Wpedantic -Werror` flags, and for `swiglu` a stub that calls `expf` with `-lm` in `trailing_flags`. Run the executable with `local_run.run` at a small shape and two draws. It exits 0 and its standard output has the complete report length of ADR-0163 decision 8, ending with `end\n`.
   - **Kernel for another kind**: building the `rmsnorm` program with the `gemm` stub kernel is a result with `ok` false, because the symbol is undefined at link time.
   - Keep the number of `clang` builds small; no test should take more than a few seconds on a CI runner.
10. **No other behaviour change**:
    - Leave unchanged `bf16_verification.h`, the four bf16 programs, `bf16_verification_arrays.py`, the first case's files (`verification_program.c`, `verification_build.py`, `verification.py`, `verification_arrays.py`), `clang_build.py`, the contract modules, the existing tests and the CI workflow.
    - Add no dependency.
    - The local `pytest` and `ruff` runs are green, and coverage of `hilclaw/` stays at or above 80% for lines and functions.
11. **Process**: code mode (CLAUDE.md A-13).
    - Open a Draft PR titled with `T-0455`, whose body ends with `Task: T-0455`.
    - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
    - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
    - The reviewer checks at least:
      - that the module adds no flag and hands every argument over unchanged in one call;
      - the kind-to-program mapping against ADR-0163 decision 2 and the file names;
      - the order of the refusals (`kind`, then no kernel source) and their `parameter` attributes;
      - that `numpy` is not imported;
      - that the bf16 programs, the header and the first case are unchanged.

## Out of Scope

- The report reader, the form check, the check-value comparison, the verdict and the run of a built executable (ADR-0163 decision 8; the counterpart of `verification.py`). That is the next slice.
- The calibration kernels of ADR-0163 decision 9, and any change to `test_calibration.py` or the CI calibration step.
- Any change to the bf16 programs, the header, `bf16_verification_arrays.py` or the first case's modules.
- RoPE and SDPA, the bf16 timing run and its build, and fp16.
- Registering a bf16 kind with `correctness.check`, `spec.write` or the instance start.
- Default flags, a default `-lm`, OpenMP or other build settings (ADR-0163 Boundaries; HQ-0033, HQ-0034).
- Any edit to `ARCHITECTURE/` or `PROCESS/`, except this task file's `## Result`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next slice: the Python side of ADR-0163 decision 8 over a built executable. It has the counterpart of `verification.py`: program arguments per kind, the report form check with length draws · (4 + 2·m·n) + 4, the check-value comparison through `bf16_verification_arrays`, the counts and the verdict, and the run through `local_run.run`. If it goes over the size cap, split `judge_report` from the run. After that come the calibration kernels of decision 9.

## Result
