---
id: T-0473
title: Add the decode passes to hilclaw/model_forward.c (cache kept across passes, given tokens) and the host side's input encoding, run and report parsing in hilclaw/model_forward_run.py (ADR-0166 code slices 3 and 4)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0471, T-0472]
touchesFiles: [hilclaw/model_forward.c, hilclaw/model_forward_run.py, tests/test_model_forward.py, tests/test_model_forward_run.py]
estimatedSize: {loc: 480, files: 2}
hq: []
---
## Why

**State.** ADR-0166 (T-0470, `d25a61e4`) designs the bf16 forward pass and generation of the model executor on `cpu_standin` (ADR-0153 code slice 2; PLAN P2-13, which P2-14 needs). Its Consequences (lines 167-173) list six code slices. When this task starts, T-0471 (slice 1, `hilclaw/model_forward_check.py`) and T-0472 (slice 2, `hilclaw/model_forward.c` with the prefill only) have landed. First check on `main` that both are `DONE` and read what they landed (dev-item-address step 1).

**This task is slices 3 and 4**, grouped under DRIVER §6 "task 단위" ③ (slice 3 alone is well under half the size cap and slice 4 is the adjacent work of the same PLAN item):
- **Slice 3**: "The program, decode passes: in `hilclaw/model_forward.c`, the G − 1 decode passes with the given tokens of decision 7, the cache kept across them, and the token ids in the report; with tests."
- **Slice 4**: "The host side's input and report: a new module `hilclaw/model_forward_run.py` — the input encoding (weights, the RoPE table built with `rope_table.build`, `eps` from `rmsnorm_eps`, token ids, the library table), one run of the program, the report's parsing; with tests that start a program built by the test."

**The binary form is T-0472's.** ADR-0166 leaves the binary form of the program's input, library table and report to the code slices. T-0472 chose it and stated it completely in the header comment of `hilclaw/model_forward.c`. **That header comment is the authority** for this task: the encoder and parser of slice 4 speak exactly that form. If slice 3 needs a change of the form (it should not: T-0472's input already carries G, the per-pass library table, S + G token ids and a table of S + G − 1 rows), make the smallest change, update the header comment and the slice-2 tests, and say why in the commit body.

**Batch (DRIVER §6 "task 단위" ④).** T-0471, T-0472 and T-0473 were created together; this task lists both earlier ones in `dependsOn`. Slices 5 (build-and-run path) and 6 (kind-faithful synthetic-model test) come in a later batch.

**PLAN order and D18.** P2-13 is a checklist item and P2-14 needs it; the D18 rule does not apply. The round-loop items and P2-5 are held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, OD-3).

**HQ-0071 (open, owner)** — token selection, model-level comparison, reference: only the given-sequence mode is built (ADR-0166 decision 7); no selection rule, reference or tolerance. **HQ-0070** — RoPE scale factor: every RoPE constant is the caller's required argument with no default; tests use their own constants. **HQ-0069** (runtime acceptance (lxvii)): not crossed; tests build and load on the local POSIX system.

**D16.** Built with the local `clang`, run as local processes with fixture kernels the test writes. Nothing starts `claude`, downloads a model file, or needs a board or an API key. Without clang or POSIX the clang tests skip locally and fail on CI; the pure-Python tests of the encoder and parser run everywhere.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (600 LOC, 10 files, tests excluded), the naming and the test rules.
  - §6 "task 단위" ④ (line 126): what to check when an earlier task of the batch closed without a result.
  - For this task: branch `claude/T-0473-<slug>`; commit trailer `Task: T-0473`; code mode, so a Draft PR whose body ends with `Task: T-0473`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`: decision 1 (lines 35-39, the order of a generation), decision 2 (lines 41-75), decision 3 (lines 77-102), decision 4 (lines 104-112: the cache and its lifetime, what the host side hands over and who makes it), decision 7 (lines 132-137: the given-sequence mode, the report), Consequences code slices (lines 167-173), Boundaries (lines 189-198).
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`: decision 4 (lines 52-59) and decision 15 (decode pass k has l = S + k).
- `hilclaw/model_forward.c`: the whole file as T-0472 landed it, header comment first.
- `tests/test_model_forward.py`: the whole file as T-0472 landed it (fixture kernels, the NumPy re-computation, the helpers).
- `hilclaw/model_run.py`: the whole file (340 lines) — the model for slice 4: `encode_input`, `output_shapes`, `parse_report`, `run_model_program`, `RunFailed`, `ModelProgramResult`, the conventions paragraph and the argument checks.
- `tests/test_model_run.py`: skim the structure (pure-Python cases, then cases that start a program built by the test).
- `hilclaw/model_binding.py`: the call-site tuples (lines 146-180), `ModelDimensions` (line 197), `rmsnorm_eps` (lines 897-922).
- `hilclaw/rope_table.py`: `build` (lines 132-160) and the "Inputs" paragraph of the module docstring.
- `hilclaw/model_forward_check.py` as T-0471 landed it: its weight and RoPE-constant types (reuse them as the arguments of the encoder; do not redefine them).

## Acceptance Criteria

**Slice 3 — decode passes in `hilclaw/model_forward.c`:**

1. Lift the G > 1 refusal. After the prefill, run G − 1 decode passes: decode pass k (k = 1 … G − 1) has T = 1, P = S + k − 1, and takes given token k − 1 (0-based) as its only token (ADR-0166 decisions 1 and 7). The last given token is fed to no pass.
2. Each decode pass uses the same buffers (their first row), the same per-layer cache buffers kept from the prefill and earlier decode passes (never cleared, never refilled), `freqs_cis` = the table advanced by P·d, `sdpa` with (m, l) = (1, P + 1), and the library the table names for that call site at pass k.
3. The report: the S + G token ids, then the logits rows pass by pass in pass order — for `"all"` the T rows of each pass (S + G − 1 rows in total), for `"last"` the last row of each pass (G rows) — then `end\n`. Update the header comment (the order of a generation, the report length) and remove the "prefill only" statements.
4. Tests in `tests/test_model_forward.py`: extend the NumPy re-computation to decode passes and show **bit-for-bit** equality for G ≥ 3 under both `lm_head_rows` values; show the cache is kept across passes (for example a run whose decode logits differ from those of a run where the test's re-computation clears the cache between passes, or an SDPA fixture whose output depends on all l cache rows); show the per-pass library table is followed (a different library bound at a decode pass than at the prefill for one call site); report length for G ≥ 2; G = 1 still works; replace the slice-2 test that expected G = 2 to be refused. Keep every other slice-2 test passing.

**Slice 4 — `hilclaw/model_forward_run.py`** (Python, the host side's language, ADR-0153 decision 2; one line in the commit body):

5. A module docstring in the form of `model_run.py`'s: the rule (ADR-0166 decisions 4 and 7), the command, the conventions, what it does not do (no binding check, no build, no selection rule, no reference, no tolerance, no RoPE constant default, no cast, nothing stored).
6. **The input encoding**, for example `encode_input(dimensions, *, eps, rope, weights, prompt, given, lm_head_rows, libraries)` returning `bytes` in exactly the form of `model_forward.c`'s header comment, where `libraries` maps each of the fifteen call sites to its per-pass library indices (or to a per-shape mapping the function expands — state which). It builds the RoPE table with `rope_table.build(head_dim=d, positions=S + G − 1, …)` from the caller's five constants and converts `eps` with `model_binding.rmsnorm_eps`. It requires `given` (the given-sequence mode only) and raises `TypeError`/`ValueError` before encoding for arguments outside what it states (wrong types, wrong weight shapes or element types, index outside the libraries, token ids outside the vocabulary), with a message naming the argument; reuse T-0471's checks where they apply rather than duplicating them, if that keeps the module simple.
7. **The report parsing**, for example `parse_report(report, dimensions, *, prompt_length, generation_length, lm_head_rows)` returning the token ids and the logits rows as a `numpy.uint16` array of shape (rows, V), with the length computed from the arguments and compared before any byte is read, and the end mark checked; a report of any other length or without the end mark is a run failure.
8. **One run of the program**, for example `run_forward_program(program, input_path, libraries, *, timeout_s, …)`, mirroring `model_run.run_model_program`: start the program once through `hilclaw.local_run.run` with the given time limit (no default), and return a result that is either the parsed report or the outcome **run failed** of ADR-0153 decision 5 (timeout, non-zero status, incomplete report), as `model_run` names it. The caller places the input file; the module chooses no path, no container and no environment. Reuse `model_run`'s `RunFailed` or define the same shape here (state which).
9. Tests in new `tests/test_model_forward_run.py` (D12): every public function; happy, error, branch and negative cases. Pure-Python cases (run everywhere): the encoding of a small model byte for byte against an independently written expectation in the test; each argument refusal; parsing of a well-formed report, of a short report, of trailing bytes and of a missing end mark. Cases that start a program built by the test (skip without POSIX/clang, fail on CI without clang): an end-to-end run of `model_forward.c` with the fixture kernels of `tests/test_model_forward.py` (import or share them — do not copy large blocks if a shared helper in `tests/` keeps it simpler) whose parsed logits equal the NumPy re-computation bit for bit, for G ≥ 3; a timeout; a non-zero exit; a kernel that aborts.

**Both:**

10. **Size**: at most 600 changed lines outside tests, at most 10 files; expected two (`model_forward.c`, `model_forward_run.py`). If it would go over, finish slice 3 and propose the rest of slice 4 in Follow-ups (DRIVER §5).
11. **No other behaviour change**: `model_program.c`, `model_build.py`, `model_run.py`, `model_execute.py`, `model_binding.py`, `rope_table.py`, `model_forward_check.py` unchanged (except a change the reviewer agrees is needed to reuse T-0471's checks); no dependency added; local `pytest` (80 % line and function coverage gates) and `ruff` green; `model_forward.c` passes the C gate command locally where `clang` is available.
12. **Process**: code mode (CLAUDE.md A-13). Draft PR titled with `T-0473`, body ending with `Task: T-0473`; reviewer cycle (dev-code-review), at most 7 rounds, until CI is green; then `gh pr merge --squash --body` with the PR body and delete the branch. The reviewer checks at least: P, l and the token fed at each decode pass; the cache kept and never refilled; the report order and length for both `lm_head_rows`; that the encoder writes exactly the form of the header comment (the library table order, the RoPE table rows S + G − 1, the weight order); that no selection rule, reference, tolerance or RoPE constant default appears.

## Out of Scope

- The build-and-run path (`model_build.py` learning the forward source, `model_forward_execute.py`; slice 5) and the kind-faithful synthetic-model test of ADR-0166 decision 8 (slice 6): the next batch.
- A generation mode, token selection, a model-level comparison or reference (HQ-0071); any Llama RoPE constant (HQ-0070); a cache capacity value or a longest sequence.
- Exposure of the executor as a tool (OD-18, OD-23), isolation (OD-14), a data-plane record of a model run.
- Editing any ADR or the "less exact" sentences ADR-0166 Consequences lists.

## Follow-ups

- Next (planner): ADR-0166 code slices 5 and 6 (build-and-run path and the synthetic-model test), after which ADR-0153's runtime acceptance item (lxviii) is to be asked (ADR-0166 Consequences, line 176).

## Result
