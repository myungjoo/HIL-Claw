---
id: T-0397
title: Add the copies of Q3 into a cpu_standin build directory, refusing links, beside the reader of ADR-0055 (ADR-0144 code slice 2; bound to no tool)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [NFR-4, C-7, FR-10, OD-14]
dependsOn: [T-0396]
touchesFiles:
  - hilclaw/standin_copies.py
  - tests/test_standin_copies.py
  - hilclaw/kernel_source.py
  - tests/test_kernel_source.py
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P1-1 is open. Its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin`, and P2-5 (the first end-to-end run, `cpu_standin` x GEMM) needs the same. ADR-0144 (landed as `bba593f`, T-0395) decided that each first-case build and process runs in a new Docker container whose only host path is the build directory, and that what goes in crosses **by copy** (decision 2, Q3). Its Consequences list four code slices. T-0396 (PR #230, `265d570`) landed slice (1), `hilclaw/standin_container.run_in_container`. **This task is slice (2)**: "the copies of Q3 into the build directory, refusing links, beside the reader". Slice (4), the `cpu_standin` operations, needs it. This is checklist work (P1-1), so the D18 rule for work outside the checklist does not apply.

What Q3 asks of the copy, in short (read the full text in ADR-0144): before the build and on the host, copies with their own bytes (never a link) of the **kernel files** the reader of ADR-0055 found at that call (R2: the compiled set and the kernel's own headers, R3 and R5), and of the harness program of the build (the verification program or the timing driver). The kernel's copies go in a sub-directory of the build directory that holds nothing else. The harness program's copy and the executable go outside it, so that no admitted kernel file name can be the path of the harness copy or of anything the build makes. Nothing else of the attempt is copied (R6).

**A gap in the landed reader.** `hilclaw/kernel_source.read_compiled_set` returns only the compiled set (`.c` files). Q3 also needs the `.h` kernel files. They must come from the same listing as the compiled set, so that "the kernel files the reader found at that call" is one snapshot. This task therefore adds the headers to the reader's answer (Acceptance Criterion 1) and does not list `output/` a second time.

Planner's judgements (from `main` `46eb2af`; **the reviewer is asked to re-check each**):

- **No new external dependency** (standard library only). **No tool answer, kind or data-plane member.** The new function is bound to no tool and no backend operation. It writes only below the build directory it is given, adds no failure kind of `hilclaw.check_failure`, writes no data-plane file and changes no validator. Copy failures are plain Python facts: a module exception with a `failure` string, in the convention of `hilclaw/scratch.py` and `hilclaw/bring_in.py`. Those strings are **not tool kinds**, and their mapping to the rows of ADR-0056 decision 5 / ADR-0060 decision 4 (for example S5 `build_input_missing`) is slice (4)'s and is not made here (ADR-0144 decision 7: "A code slice that meets one registers it under those sub-questions rather than choosing an answer").
- **No value of an undecided item is fixed.** ADR-0144 Q3 leaves "the names of the sub-directory and of the other entries" to "the code slice". Here the kernel sub-directory name is a module constant and the harness copy keeps the basename of the harness program. The executable's name and where the build directory is made and removed (ADR-0056 decision 4, outside both checkouts) are slice (4)'s.
- **D16.** Nothing is started: no `docker`, `clang` or `claude`. Tests use `tmp_path` files only.
- **No open PR overlaps.** PR #186 (T-0324, draft, BLOCKED on HQ-0032) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None of them is touched here.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 (executor procedure, resume rule, the 2 h 30 min limit); §5 (task format; naming: branch `claude/T-0397-<slug>`, PR title with `T-0397`, trailer `Task: T-0397`, the PR body's last line `Task: T-0397`; D4 size cap; the code-task test rules ① to ⑤); §3 "BLOCKED 사유".
- `CLAUDE.md` (repository), "상시 규칙": "코멘트 최소화", "개발 드라이버와 런타임의 구분" (D16), "도구 계층 언어 정책" (record the language and one-line reason in the commit body), "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md`: Decision §2 Q1 to Q4 (lines 55-58; **Q3 is the rule this task implements**), §6 "Of the operation" (line 111), §7 (lines 113-116), Walk-through step 1 (line 119), Consequences "Slices for the planner" (line 143).
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`: decision 3, R1 to R8 (lines 47-66), decision 5 N1/N2 (section starting line 75).
- `hilclaw/kernel_source.py` (whole file) and `tests/test_kernel_source.py` (the `symlink` helper at lines 64-70 and the tests that compare whole `KernelSource` values).
- `hilclaw/scratch.py` lines 1-110 and 205-250, and `hilclaw/bring_in.py` lines 1-100 and 207-260: the module docstring style, the no-follow read (`lstat`, `open` with `O_NOFOLLOW`, `fstat` identity check), `_LINK_ERRNOS`, and the `O_CREAT | O_EXCL` write.
- `hilclaw/harness/verification_build.py` (`PROGRAM_SOURCE`) and `hilclaw/harness/timing_build.py` (`DRIVER_SOURCE`): the two harness programs the caller will pass.
- `hilclaw/standin_container.py` (module docstring and `BUILD_DIRECTORY`/in-container path constant): slice (1), for consistency of naming and of what "bound to no tool" means.

## Acceptance Criteria

1. **The reader also answers the headers.** In `hilclaw/kernel_source.py`, `KernelSource` gets one trailing field `headers: tuple[Path, ...]` with default `()`. It holds the kernel files (R2) whose name ends in `.h`, each the given path joined with the listed name, in ascending byte order of the names. `read_compiled_set` fills it **from the same two listings and the same `lstat` calls** it already makes: no extra listing, and nothing opened or read (R6, R7 unchanged). Rules for the field:
   - When the answer is "no kernel source" (`missing` not `None`), `headers` is `()`. This holds also for `NO_COMPILED_FILE`, where headers may lie in `output/` but are not reported, because a header is never built without a compiled file (R5).
   - Every other behaviour, outcome and exception is unchanged.
   - The module docstring and the `KernelSource` docstring are updated, and the sentence "Nothing calls this module yet" is corrected.
   - Existing tests in `tests/test_kernel_source.py` and `tests/test_bring_in.py` keep passing. Tests whose fixtures hold `.h` files and compare whole `KernelSource` values are adjusted, and new tests cover the field (with headers, without headers, a `.h` symlink not counted, a `.h` under a non-admitted name not counted, a `.h`-only `output/` giving `NO_COMPILED_FILE` with `headers == ()`).
2. **New module `hilclaw/standin_copies.py`** (Python; the executor may choose a clearer name and give the reason in the PR body) with one public function. Suggested signature: `place_copies(output_path, harness_program, build_dir)`. It applies `kernel_source.read_compiled_set(output_path)` **once**. Then:
   - **"No kernel source"** (`missing` not `None`): the function creates and writes nothing and returns an answer that carries that `missing` value unchanged.
   - **Otherwise**: below `build_dir` it makes one new sub-directory, whose name is a module constant (for example `kernel`), and copies into it every compiled-set file and every header under its listed name. It then copies `harness_program` into `build_dir` directly, under the basename of `harness_program`.
   - **The answer** is a `NamedTuple`. It holds the relative POSIX-form paths (relative to `build_dir`, `/` separators, for example `kernel/gemm.c`) of the compiled-set copies **in R3 order**, the relative paths of the header copies, the relative path of the harness copy, and `missing`. Slice (4) will prefix these paths with the in-container path of slice (1), and will put the harness copy first among the sources, as `verification_build` and `timing_build` do. The function does not do either itself.
   - **The module docstring** states:
     - what the module is (ADR-0144 slice (2), Q3);
     - that it is bound to no tool and no operation;
     - that it writes nothing outside `build_dir`, starts no program and reads no environment variable or configuration of its own;
     - what it does not decide: the failure kinds and rows of decision 7 / ADR-0060 decision 4, the making and removal of the build directory (ADR-0056 decision 4, Q4), and the name of the executable;
     - that the copies are not bounded in number or size (R7; ADR-0144 Q7).
3. **Copies, never links, own bytes.**
   - **Reading.** Each source is read whole by the no-follow pattern of `scratch._read_source` / `bring_in._read`: `os.lstat` must show a regular file; it is opened with `O_RDONLY | O_NOFOLLOW` (where the platform has it) `| O_NONBLOCK | O_BINARY`; `os.fstat` must show a regular file of the same `st_dev`/`st_ino`. A source that fails one of these checks is refused with its own `failure` value, and the module's other failure values are distinct from it. That includes a source that became a symbolic link or another kind of file between the reader's listing and the open, and an open that fails with a link errno (`_LINK_ERRNOS`).
   - **Writing.** Each copy is a new regular file made with `O_WRONLY | O_CREAT | O_EXCL` (plus `O_NOFOLLOW` and `O_BINARY` where present). No mode bits or times are carried over, and nothing uses `shutil.copy*`, `os.link`, `os.symlink` or a reflink.
   - **Sub-directory.** It is made with `os.mkdir`. If something already exists at that name it is an error, never reused.
   - **Bytes.** The written bytes equal the bytes read, unchanged.
   - **The harness program** follows the same read rule.
4. **Checks before anything is written**, each raising `TypeError` or `ValueError` with an attribute `parameter` naming the argument (the `local_run` / `standin_container` convention):
   - `harness_program` and `build_dir`: not `str`/`os.PathLike` of `str`, or containing NUL;
   - `build_dir`: not absolute;
   - `harness_program`: a basename equal to the kernel sub-directory constant, or empty.
   After those checks the function tests `build_dir` with `os.lstat`. If it is not a plain directory (missing, a file, a symbolic link) the function raises before the reader is applied. The exception class is the executor's and is documented.
   An invalid `output_path` is left to the reader: its `InvalidOutputPathError` is passed on unchanged, as is its `KernelSourceReadError`, and nothing is written in either case.
5. **Failure after writing began.** When a copy fails after the sub-directory was made, the function raises the module's copy exception, whose `failure` is one of a documented tuple of values, and the cause is chained. The function does **not** try to remove what it wrote. The docstring says that the caller removes the whole build directory, as ADR-0056 decision 4 and ADR-0144 Q4 say (slice (4)). An `OSError` of `os.mkdir` or of a write may be either wrapped or passed on; document which, and keep the texts of the module's own exceptions free of paths, as `scratch` and `bring_in` do.
6. **Tests** in `tests/test_standin_copies.py`, on `tmp_path` only. They run on Linux CI and on a Windows development machine; symlink cases use a skip-on-refusal helper like the one in `tests/test_kernel_source.py`. They cover:
   - **happy:** an `output/` with two `.c` files and one `.h`, and one with a single `.c`. Assert the layout under `build_dir`: the sub-directory holds exactly the kernel files and the harness copy lies beside it. Assert byte equality, that every copy is a regular file and not a link (`os.lstat`), the R3 order of the compiled-set paths, and the POSIX form of the returned paths. Copy both the real `verification_build.PROGRAM_SOURCE` and `timing_build.DRIVER_SOURCE`.
   - **branch:**
     - a kernel file named like the harness program (`verification_program.c` is an admitted name) gives two distinct files: the kernel's copy below the sub-directory and the harness copy beside it;
     - non-admitted names, a sub-directory and a non-`.c`/`.h` file below `output/` are not copied (R6);
     - each `NO_KERNEL_SOURCE_CASES` value is returned with nothing created under `build_dir`.
   - **error/negative:**
     - every refusal of criterion 4, with its `parameter` and with nothing written;
     - an existing entry at the sub-directory name;
     - an existing entry at the harness copy name;
     - a harness program that is a symbolic link or a directory;
     - a kernel file swapped for a symbolic link after the listing (monkeypatch `kernel_source.read_compiled_set` to return a crafted answer, or patch `os.open` / `os.fstat` to simulate a changed identity);
     - a read error and a write error, raised from a patched `os.read` / `os.write`;
     - `KernelSourceReadError` and `InvalidOutputPathError` passed on.
   - every public function and class of the new module, and the new `KernelSource` field (criterion 1).
7. `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` pass locally. CI is green on the PR, and the `hilclaw/` coverage gate (line ≥ 80 %, function ≥ 80 %) holds. `Result` records the language (Python) and its one-line reason, the PR, the review rounds and any follow-up.

## Out of Scope

- Slice (1) changes, slice (3) (the environment variable that names the image, with T-0395 round-7 nits (a) and (c)), and slice (4) (the `cpu_standin` operations of `correctness.check`, `sim.run` and `board.run`: making and removing the build directory, the executable's name, the mapping of failures to kinds, wiring with `run_in_container`).
- Wiring the function into `clang_build`, `verification_build`, `timing_build`, any `check_*`/`run_*` module, `backends.py` or `tools.py`.
- Any tool answer, failure kind, data-plane member, journal line or validator; any bound on the number or size of files.
- Any edit of an ADR, of the `ARCHITECTURE/` registers, or of the docstrings ADR-0144 lists as "less exact".
- Editing `hilclaw/bring_in.py` or `hilclaw/scratch.py`. Their private helpers may be imitated but not refactored into a shared helper here; that would be a no-behaviour-change refactoring, which is a D18 hold item.
- Starting `docker`, `clang` or `claude` (D16).

## Follow-ups

- After this lands: ADR-0144 slice (3), the image environment variable (its name, its reference check, refusing a value `docker run` would read as an option, and how it reaches a turn's MCP server process: T-0395 round-7 nits (a) and (c)). Then slice (4), which still waits on OD-18 ⑱/⑲ answers (HQ-0021, HQ-0026) and ① (마) for the memory figure.

## Result
