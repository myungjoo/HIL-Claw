---
id: T-0535
title: Add the graph program of ADR-0193 decision 5 (model_graph.c running an encoded plan), its host-side build and run, the byte-for-byte check against model_forward.c on synthetic weights, and a second model of another structure
phase: P3
status: TODO
commitMode: code
coversReq: [D27, OD-32, C-6, OD-31, "PLAN P3-4"]
dependsOn: [T-0534]
touchesFiles:
  - hilclaw/model_graph.c
  - hilclaw/model_graph.py
  - hilclaw/model_graph_execute.py
  - hilclaw/model_build.py
  - tests/test_model_graph.py
  - tests/test_model_graph_program.py
  - tests/test_model_graph_execute.py
  - tests/test_model_build.py
  - tests/model_graph_feed_forward.json
estimatedSize: {loc: 600, files: 4}
hq: []
---
## Why

**PLAN P3-4** ("모델 그래프 파일"), second of the two tasks ADR-0193 decision 8 sizes for it: "program, host, second model". T-0534 landed the format 1 reader, its checks, the resolution into a per-pass plan, the binding check and the Llama graph file. This task runs that plan. ADR-0193 decision 5, "Relation to the executor": `hilclaw/model_graph.py` encodes a resolved call plan, and `hilclaw/model_graph.c` runs it "through the same library loading, report and token selection rules (ADR-0166 decision 7, ADR-0176 decision 5)". "The checks of P3-4": with the synthetic weights of ADR-0166 decision 8, the Llama graph file gives reports equal **byte for byte** to `model_forward.c`'s. A second graph of another structure (a feed-forward stack with no attention, other dimensions) matches a Python re-computation in its test. Both use the six existing kinds.

**Before code, check T-0534 (DRIVER §6 "task 단위" ④).** T-0534 must be `DONE` with its `## Result`. Read that `Result`: the Llama file's path, the extensions of format 1, any `model_binding` function made public, the plan's public form, and any split T-0534 proposed in `## Follow-ups`. If T-0534 split off its binding check, do that part first, within this task's size. If T-0534 is not `DONE`, stop and report it.

**Order (DRIVER §6 D27 ①).** As for T-0534: no open `nightly-failure` issue, no open PR, no `실패` item in `PROCESS/RuntimeAcceptance.md`, no P2-15 preparation pending. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**P2-15 must not change (D27).** `model_forward.c`, `model_forward_run.py`, `model_forward_check.py`, `model_forward_execute.py`, `model_forward_container.py` and `model_check.py` are not edited. The new program runs beside them, and whether it replaces them later is a later record's (ADR-0193 decision 5).

**Open HQs not crossed (D27 ⑦).** HQ-0081, HQ-0088 to HQ-0091: none concerns this. No RoPE constant is chosen (HQ-0070). The tests give their own.

**D16.** Verification is on the development machine with clang and fixture kernels the test writes (host path, as `tests/test_model_forward.py` and `tests/test_model_forward_execute.py` do). No `claude`, no Docker, no model file. The same check on real Llama 3.2 1B weights is a runtime acceptance item (PLAN P3-4; ADR-0193 decision 5), which the executor writes in `## Result` for the driver to register (DRIVER §8, D22). After this task is `DONE`, the driver checks PLAN P3-4.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0535-<slug>`, the `Task: T-0535` trailer and the PR body's last line, the size cap, D12, D21), §3 "BLOCKED 사유", §6 D27 and "task 단위" ④, §8 (runtime acceptance items, D22).
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책" (one line per language used, C for the program and Python for the host side, with the reason, in the commit body and `## Result`), "코멘트 최소화" (the C file's boilerplate header comment may be long, as `model_forward.c`'s is), "개발 드라이버와 런타임의 구분".
- `PROCESS/tasks/T-0534-model-graph-reader-and-llama-file.md`, whole, `## Result` especially.
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`: decision 5 in full; decision 8, row P3-4; Consequences ("A-13 reading", "Runtime acceptance items").
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md` decisions 1 to 4, 7 and 8; `ADR-0176-od31-model-level-reference-and-comparison.md` decision 5; `ADR-0153-od31-model-executor.md` decisions 3 to 6; `ADR-0182-od14-model-executor-container.md` decision 7 (the host path is for kernels the caller wrote).
- Code: `hilclaw/model_graph.py` and `hilclaw/graphs/llama.json` (as landed by T-0534); `hilclaw/model_forward.c` (whole: command line, input and report form, checks, statuses, loading, selection); `hilclaw/model_forward_run.py` (whole); `hilclaw/model_forward_execute.py` (whole); `hilclaw/model_build.py` lines 1-60 and 140-175; `hilclaw/model_run.py` (`END_MARK`, `RunFailed`, `_path`, `_is_sequence`); `hilclaw/clang_build.py` (the `build` signature); `hilclaw/rope_table.py` lines 95-190.
- Tests: `tests/test_model_forward.py` (the fixture kernels, `make_model`, `generate`, `encode`, the clang fixture `built` and its CI rule), `tests/test_model_forward_execute.py` lines 1-180, `tests/test_model_build.py` lines 95-115 (the public-name assertion).

## Acceptance Criteria

1. **The program `hilclaw/model_graph.c`**, C with the C library and POSIX.1-2008 only (`<dlfcn.h>` included), built like `model_forward.c`. It reads one input file that holds the encoded plan, the scalars, the tables, the token ids and the weights, and takes the libraries on the command line. It runs the plan's passes in order, with the same rules as `model_forward.c`:
   - every buffer and state element is set to `0x7FC0` once at allocation;
   - libraries are opened with `dlopen(path, RTLD_NOW | RTLD_LOCAL)` before the input is read;
   - per-pass, per-site library indices; each entry point found by its kind's symbol before the first call;
   - descriptor 1 is kept apart from the report;
   - the report form, its end mark and the generation mode's selection rule are those of ADR-0176 decision 5;
   - the exit statuses 0 and 2 to 7 have the same meanings.
   Its header comment states the command line, the input form, the checks and the statuses, as `model_forward.c`'s does. It does no floating-point arithmetic beyond passing `eps` and the tables to kernels. Every size from the input is checked against `size_t` and the file length before any allocation, and every offset and count is checked against its array before the first call.
2. **The encoding** in `hilclaw/model_graph.py`: a public function turns a resolved plan (T-0534), a binding check result, scalar values, table arrays, a provider of the logical weights (a mapping from each logical name, and `{index}` entry, to a `numpy.uint16` array of its declared shape), the prompt, the given tokens or `None`, and `lm_head_rows` into the input file's bytes. The RoPE table is built with `rope_table.build` from caller-given constants, as `model_forward_run.encode_input` does, and `eps` is passed through `model_binding.rmsnorm_eps`. A weight of the wrong element type or shape, a missing or extra provider name, and a token id not below the declared vocabulary are refused before any byte is built. A public function parses the report into the token ids and logits rows; reusing `model_forward_run`'s report reader without editing that module is preferred.
3. **Build and run on the host.** `hilclaw/model_build.py` gains the program's source path and a `build_graph_program`, mirroring `FORWARD_PROGRAM_SOURCE` and `build_forward_program`. A new `hilclaw/model_graph_execute.py`, mirroring `model_forward_execute.execute`, reads or takes a graph, resolves it, checks the binding, builds each distinct kernel and the program in its own build directory, writes the input and runs the program once. Its outcomes are those of ADR-0153 decision 5: no kernel, kernel unfit, invalid input, build failed, run failed. Its docstring states, as `model_forward_execute` does, that it is only for kernels the caller wrote (ADR-0182 decision 7). The container path is not built here (see Follow-ups).
4. **Byte for byte with `model_forward.c`.** With clang present, tests build both programs and the fixture kernels of `tests/test_model_forward.py`, and use the same synthetic model (at least two layers, H a multiple of H_kv and larger than it, S ≥ 2, G ≥ 3). Under both `lm_head_rows` values and both modes (given sequence and generation), and with a one-library binding and a per-site, per-pass binding, the Llama graph program's report bytes equal `model_forward.c`'s. A per-pass binding that sends one site to a different library at a decode pass is among them.
5. **The second model.** A test-only graph file `tests/model_graph_feed_forward.json` (the executor may place it elsewhere under `tests/`, named in `## Result`): a feed-forward stack with no attention (no `rope`, no `sdpa_kv_cache`), dimensions other than the Llama test's, at least two repeated blocks, and an `output` of its own. With fixture kernels, its reported logits and token ids equal, bit for bit, a Python re-computation in the test, under both `lm_head_rows` values, in the given-sequence mode, and in the generation mode if the graph has a token output. It uses only the six existing kinds.
6. **Negative cases of the program and host**, each one change at a time:
   - an input shorter or longer than its header gives;
   - a library index out of range;
   - a library without its site's entry point at a decode pass;
   - a plan offset or count past its array;
   - a token id not below the vocabulary;
   - a NaN in the selection row (status 7);
   - a wrong argument count;
   - a kernel that aborts (no end mark);
   - on the host: each refusal of criterion 2;
   - each outcome of criterion 3.
7. **Tests (D12).** Every public function of each touched or new module; happy, error, branch and negative cases. New test files: `tests/test_model_graph_program.py` (the C program, as `tests/test_model_forward.py` is for `model_forward.c`) and `tests/test_model_graph_execute.py`. Additions to `tests/test_model_graph.py` and `tests/test_model_build.py`. Clang tests follow the existing rule: skip without clang locally, fail on the CI runner. Package line and function coverage stay at or above 80 %. The full suite and `ruff` pass locally.
8. **Existing tests pass unchanged**, apart from assertions that pin a list of public names, imports, fields or binders (DRIVER §5, D21). Pinning assertions this task is expected to touch: `test_public_names` of `tests/test_model_build.py` (the new source path and build function); any public-name or import assertion of `tests/test_model_graph.py` from T-0534. Each edited assertion is listed in the PR body.
9. **No frame change.** As in T-0534 criterion 11: the graph file and the program's input stay outside the data plane, and no contract-table entry, `kind`, `dtype`, member or version is added. If the work shows otherwise, stop and return `BLOCKED` (A-13; DRIVER §8).
10. **Size.** If the change is seen to exceed 600 LOC or 10 files (tests excluded, DRIVER §5), land criteria 1 to 4 and 6, and propose the second model (criterion 5) as a split in `## Follow-ups`. In that case PLAN P3-4 is not checked until it lands.
11. **`## Result`** states:
   - the language lines;
   - the edited assertions;
   - the input form of the program in one paragraph;
   - the path of the second graph;
   - whether the container path and an entry for the owner's real-weight check are needed, with a sketch, as a follow-up (do not build them);
   - the runtime acceptance item for the driver to register (D22), in Korean, in the form of `PROCESS/RuntimeAcceptance.md`'s other items (source `P3-4`, basis task T-0535). Its content: with the real Llama 3.2 1B weights read by `hilclaw.model_files.read` (ADR-0191), the Llama graph file's report equals `model_forward.c`'s byte for byte, for the same binding and settings. State how it can be run with what has landed. If it cannot be run yet, state the condition under which it becomes checkable. Name RA-0056 and RA-0065 to RA-0067 as the items it is checked with.

## Out of Scope

- The container path of ADR-0182 for the graph program and any command-line or tool entry for it (a follow-up, judged by the planner under D27 ②).
- Any edit of `model_forward.c`, `model_forward_run.py`, `model_forward_check.py`, `model_forward_execute.py`, `model_forward_container.py`, `model_check.py` or `model_files.py`; replacing the forward program.
- External formats (OD-9), a dtype other than bf16, fusion (C-6), any model-level record (OD-31 ⑧).
- Any edit of `ARCHITECTURE/`, PLAN or RuntimeAcceptance (the driver records the RA item and checks P3-4).

## Follow-ups

- If needed for the owner's real-weight check: the graph program in the ADR-0182 container path and an entry for it, proposed in `## Result` with a sketch.

## Result
