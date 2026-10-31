---
id: T-0527
title: Build and run the model program of hilclaw.model_execute in ADR-0144 containers (ADR-0182 code slice 3, HQ-0080 group D)
phase: P2
status: DONE
commitMode: code
coversReq: [HQ-0080, OD-14, OD-31, NFR-4]
dependsOn: [T-0526]
touchesFiles:
  - hilclaw/model_container.py
  - hilclaw/model_gemm.py
  - hilclaw/model_execute.py
  - tests/test_model_container.py
  - tests/test_model_gemm.py
estimatedSize: {loc: 300, files: 5}
hq: []
---
## Why

The owner approved group D ("design hardening") of the PLAN hold section in HQ-0080. Its third line is the T-0506 follow-up: ADR-0182 code slice 3. The line is not judged again here, and P2-15 does not need the work, since P2-14 and P2-15 use the bf16 forward path, which already runs in containers.

ADR-0182 decision 2 requires every generation of a kernel an instance or a coder wrote to be built and run in containers, and decision 1 includes the model program of `hilclaw.model_execute`. That path has only its host form today. No caller hands it an instance kernel, so this closes a gap before one appears. The record already decides the design, so this task needs no new ADR.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (including D21 on pinned lists).
- `ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md`: decisions 1 to 9.
- `hilclaw/model_forward_container.py`: the whole file, which is the pattern.
- `hilclaw/model_execute.py` and `hilclaw/model_gemm.py`: the whole files.
- `hilclaw/model_run.py`: `encode_input`, `output_shapes`, `parse_report`, and `run_model_program` for the outcomes it gives.
- `hilclaw/model_build.py`: `PROGRAM_SOURCE`, `LIBRARY_FLAGS`, `PROGRAM_DTYPE_FLAGS`.
- `hilclaw/model_binding.py`: `KernelReference`.
- `tests/test_model_forward_container.py`: the stub client and how it compares with the host path.
- `tests/test_model_gemm.py`: `test_public_names_and_fields`, line 497.

## Acceptance Criteria

**New module `hilclaw/model_container.py`**

1. `execute(kernels, calls, *, dtype, build_timeout_s, run_timeout_s, program_flags=(), program_trailing_flags=(), environ=None, parent=None, keep_out=())` does what `model_execute.execute` does, with each build and the one process in a new container through `standin_container.run_in_container`. It adds and removes no container option (ADR-0182 decision 2). There is no host fallback, and it has no `compiler`, `env` or `prefix` parameter.
2. **Kernels.** Each entry needs `sources`, `flags` and `headers`, the attributes of `model_binding.KernelReference`. An entry without one is a `TypeError` naming its position.
3. **Copies** (decision 4). `model_build.PROGRAM_SOURCE` goes beside the sub-directories. Kernel `i`'s sources and headers go into `kernel-<i>`, which holds nothing else. Headers are never handed to a compiler. Two files of one basename are `CopyError` `ENTRY_EXISTS`, as in the forward path.
4. **Builds.** One container per kernel in index order, then one for the program. The program gets `program_flags`, then `PROGRAM_DTYPE_FLAGS[dtype]`, its copy, `program_trailing_flags` and `-o`. No dtype flag goes to a kernel build. A `program_flags` item naming `HILCLAW_MODEL_BF16` is refused as `model_execute.execute` refuses it.
5. **Run.** `input.bin` holds `model_run.encode_input(calls, dtype=dtype)`, written in the build directory on the host after the last build. One process container runs the program with the input and the libraries, each as its path inside the container.
6. **Outcomes** (decision 8), in one result `NamedTuple` with the fields `unavailable`, `build_failed`, `run` and `removed`:
   - **container unavailable**: the existing `model_forward_container.Unavailable` and its five reasons, not a second definition;
   - **build failed**: `model_execute.BuildFailed`, with `kernel` the index or `None` for the program;
   - **run failed**: `RunFailed.TIMEOUT`, `EXIT_STATUS` (125 to 127 included for the process container) or `REPORT_FORM` from `model_run.parse_report`;
   - **success**: the outputs in call order and the container result with `stdout` replaced by `b""`.
7. **Build directory.** It is made as `model_execute.execute` makes one, with a prefix of this module's. It is removed only where `standin_answer.build_dir_removable` holds for every container, otherwise it stays and `removed` is false.
8. **Limits** (decision 5). Both timeouts are required, with no default, and checked positive and finite before anything is made. A forced removal gets `standin_check.REMOVAL_TIMEOUT_S`. No memory bound is set and no figure is taken (decision 6).
9. **Reuse.** Import the forward path's helpers rather than copy them, as `model_forward_container` itself imports from `model_execute` (`_build`, `_container`, `_copy_kernel`, `_settle`, `_Stop`, or what they have become). If one needs a change to serve both paths, the behaviour of `model_forward_container.execute` stays the same and its tests pass unchanged. The module docstring cites ADR-0182 slice 3 and states what it does not do, in the manner of the forward path. Comments stay minimal.

**`hilclaw/model_gemm.py`**

10. Add `run_in_containers(dimensions, binding, operands, *, prompt, generation_length, lm_head_rows, given=None, dtype, build_timeout_s, run_timeout_s, program_flags=(), program_trailing_flags=(), environ=None, parent=None, keep_out=())`. It makes the same binding check and operand checks as `run`, in the same order, through a shared private helper, then calls `model_container.execute`. It returns a `GemmRun` whose `execution` is that result. `run` behaves as before.
11. Update `tests/test_model_gemm.py::test_public_names_and_fields` by the new public name and import only (D21). That is the one pinned list foreseen. List every pinned assertion changed in the PR body.

**`hilclaw/model_execute.py` and `hilclaw/model_gemm.py` docstrings**

12. State decision 7 as `hilclaw/model_forward_execute.py` states it: `model_execute.execute` and `model_gemm.run` are host processes, only for kernels the caller wrote itself; an instance's or a coder's kernel goes through the container path; nothing checks who wrote a kernel. No behaviour of the host path changes.

**Tests (`tests/test_model_container.py`, and `tests/test_model_gemm.py` for `run_in_containers`)**

13. **Happy:** with a stub client, at `fp32` and `bf16`, the exact command lines, the k + 2 containers, the copies and the outputs. On CI with `clang`, a stub client that runs the program on the host gives outputs bit-for-bit equal to `model_execute.execute`, in the way the forward path's test does this. Tests start no real container runtime and no `claude` (D16).
14. **Error:** each of the five unavailable reasons, with nothing started after it and nothing on the host; a failing kernel build and a failing program build, and that nothing follows; each of the three run failures; a build with status 0 and no output; an `OSError` of the client passed on.
15. **Branch:** statuses 125 to 127 are unavailable for a build and run failed for the process; a directory kept when a forced removal does not show the container gone; `run_in_containers` when the check is not ok starts nothing, makes nothing and does not look at `operands`.
16. **Negative:** each refused argument (dtype, kernels, a kernel without `headers`, a call index too large, `keep_out`, `parent` inside a checkout, flags that are not `str` lists, the dtype macro in `program_flags`, a limit that is zero, negative, infinite or not a number, `environ` not a mapping) raises before anything is made. A source that is a symbolic link is refused by the copy.
17. **Gates.** `tests/test_model_forward_container.py`, `tests/test_model_execute.py` and the rest of `tests/test_model_gemm.py` pass unchanged. Every public function of the touched modules is tested. Line and function coverage stay at or above 80 %. Ruff is clean.

**Records**

18. No member, file, kind, value or version of the data plane changes, no dependency is added, and no image is adopted. `ARCHITECTURE/` does not change: ADR-0182 already holds the decision. Under `## Result`, write one runtime acceptance item for the driver to add to `PROCESS/RuntimeAcceptance.md` (D22), source T-0527 and ADR-0182: in the containers of decision 2 the image links `model_program.c` and the program loads the kernels' libraries, with `-ldl` where its C library needs it, narrowing ADR-0182 item (1) to this program. Do not edit that file.
19. **Code mode.** Draft PR, reviewer cycle, CI green, squash-merge with `Task: T-0527` on the last line of the PR body. `## Result` holds the language and the reason in one line (Python, as the sibling paths).

## Out of Scope

- Any caller of the new path, a tool, MCP name or command line (OD-31 ⑩, HQ-0084 ④).
- Time-limit source and values, a memory bound (ADR-0182 Boundaries).
- Removing or restricting by code the host path (ADR-0182 decision 7).
- A change to `ADR-0182`, including its "less exact" list, or to the docstrings of `model_build.py`, `model_run.py` and `standin_*.py`.
- fp16 (HQ-0083), real weights and tokenizer (HQ-0084).

## Follow-ups

## Result

- PR #345, squash-merged as 844c9ddc; branch deleted. 1 review round, Approve; the reviewer's one Nit (a `model_gemm` docstring sentence) fixed in f4e05a3d after Approve, no re-review (D20).
- CI green on the final commit (C, sh, test presence, coverage, Python 3.11 and 3.14). Touched modules at 100 % line coverage.
- Language: Python, as the sibling executor paths `model_execute` and `model_forward_container`.
- Pinned assertion changed (D21): `tests/test_model_gemm.py::test_public_names_and_fields` (`model_container` import, `run_in_containers` name).
- Beyond the criteria, stated in the PR body: `model_container.execute` refuses malformed kernel `sources`, `flags`, `headers` or a missing source before anything is made. Private helpers extracted from `model_forward_container` (outside `touchesFiles`, allowed by criterion 9) and `model_execute`, behaviour unchanged.
- Runtime acceptance item: RA added in `PROCESS/RuntimeAcceptance.md` (source T-0527, ADR-0182).
- Follow-ups: none.
