---
id: T-0495
title: Build the greedy generation mode of the model executor (ADR-0176 code slices 2 and 3) — selection between passes in the forward program, the host side in place of the generation-mode refusal, and a generated run compared teacher-forced with the float64 reference
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/model_forward.c
  - hilclaw/model_forward_check.py
  - hilclaw/model_forward_run.py
  - hilclaw/model_forward_execute.py
  - hilclaw/model_reference.py
  - tests/test_model_forward.py
  - tests/test_model_forward_check.py
  - tests/test_model_forward_run.py
  - tests/test_model_forward_execute.py
  - tests/test_model_reference.py
estimatedSize: {loc: 330, files: 5}   # non-test: model_forward.c ~150 (mode word, value ordering of bf16 patterns, selection, NaN stop, report form, header comment), model_forward_run.py ~70 (encode the mode, parse the selected tokens), model_forward_check.py ~25, model_forward_execute.py ~40, model_reference.py docstring ~5. Tests are outside the cap (DRIVER §5, D4/D20). Slices 2 and 3 are joined under D20 ③ (each alone is under half the cap). If the joined work is seen to exceed the cap, land slice 2 (the program and its tests) and propose slice 3 as a follow-up (DRIVER §5).
hq: []
---
## Why

**State.** PLAN P2-13 (model executor) still has work that P2-14 needs: "토큰을 생성하며 모델 수준에서 reference와 대조한다". T-0494 (PR #307, `main` `c736ffec`) landed ADR-0176 and its code slice 1 (`hilclaw/model_reference.py`: `reference_logits`, `compare`, `LogitComparison`). ADR-0176 Consequences lists the remaining slices in landing order:

- **slice 2** — "in `hilclaw/model_forward.c`, a mode word in the input, the selection between passes, the NaN stop and the selected tokens in the report; with tests by hand-written fixtures and inputs written by the test";
- **slice 3** — "`hilclaw/model_forward_check.py` accepts no given tokens with a generation length in place of the refusal, `hilclaw/model_forward_run.py` encodes the mode and parses the selected tokens, `hilclaw/model_forward_execute.py` passes it through; with a test that generates through `execute` with the real-operation fixture kernels and compares the run, teacher-forced on its selected tokens, with slice 1's reference".

T-0494's Result names slice 2 then slice 3 as the planner's candidate. Each slice alone is under half the size cap, so they are one task (DRIVER §6 "task 단위" ③, D20). The design is already decided and accepted: ADR-0176 decision 5 (owner rule O1 (1): argmax of the last bf16 logits row of a pass, smallest token id on ties; applied in the forward program between passes; values compared as values, −0 equal to +0, infinities ordered as values; a NaN in the row stops the generation as a run failure naming the pass; the caller gives the prompt, no given tokens and G; G passes select G tokens, the last from the last pass's row; the given-sequence mode stays; the report holds the prompt and the G selected tokens and the logits rows as ADR-0166 decision 7 orders them). ADR-0176 Boundaries leaves "the binary form of slice 2's mode word and report, and the exit status of the NaN stop" to the code slice — this task chooses them and documents them in the program's header comment. **No new ADR is written**; if the work shows that decision 5 cannot be built as written, or needs a choice beyond the binary form, the exit status and the Python signature named below, stop and return BLOCKED (DRIVER §3-5, BLOCKED reason "Requirements OD 확정이 필요한 설계 선택").

**PLAN order and D18.** P2-13 is a PLAN checklist item in the P2 order (P2-11 … P2-14); the D18 rule does not apply. P2-10 is blocked on HQ-0076 (T-0493).

**No RuntimeAcceptance `실패` item is fixed by this task** (none exists as of `main` `912a6a92`).

**D16.** Everything is verified with synthetic weights, token ids and fixture kernels built with clang; nothing loads real Llama weights or a tokenizer, installs or imports Hugging Face transformers (ADR-0176 O1 (3): a runtime-machine optional dependency only), or starts `claude`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming convention `claude/T-0495-<slug>`, `Task: T-0495` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`, D22).
- `CLAUDE.md` (repo) — "상시 규칙" (comments, "미결은 발명하지 않는다", branch/merge procedure, test rules, language policy, D16 driver/runtime boundary).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0176-od31-model-level-reference-and-comparison.md` — whole; decision 5 is the rule of this task, decisions 3 and 4 the comparison used by its test, Consequences "Code slices" items 2 and 3 and "Less exact, not edited", Boundaries.
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md` — decisions 2, 4, 6 and 7 (buffers, inputs, the check's refusals including the generation mode, the given-sequence mode and the report order) and Boundaries.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md` — decisions 1, 4 and 5 (one process per generation, the outcome "run failed").
- `hilclaw/model_forward.c` — whole (header comment: input file, report, exit statuses, "does no floating-point arithmetic"; `run_pass`, `main`, `emit`, `read_inputs`).
- `hilclaw/model_forward_check.py` — docstring, `check`, `_GENERATION_MODE`.
- `hilclaw/model_forward_run.py` — docstring, `ForwardReport`, `encode_input`, `parse_report`, `run_forward_program`, `_rows`, `_report`.
- `hilclaw/model_forward_execute.py` — docstring, `execute`, `_library_table`, `_build_and_run`.
- `hilclaw/model_reference.py` — docstring, `reference_logits` (it refuses `given` `None`; a generated run is compared by passing the report's selected tokens as `given`), `compare`.
- `hilclaw/model_binding.py` — `check` (its `given=None` generation mode and `generation_length`), `generation_calls`, `ModelDimensions`.
- `tests/test_model_forward.py` — the helpers `widen`, `narrow`, `make_model`, `header_words`, `encode`, `generate`, `report`, `start`, `assert_failed`, and the given-sequence tests.
- `tests/test_model_forward_check.py` lines ~200-235, `tests/test_model_forward_run.py` lines ~150-170, `tests/test_model_forward_execute.py` lines ~380-430 and ~630-753 (the generation-mode refusal tests, `test_public_names_and_fields`, the clang-backed tests), `tests/test_model_reference.py` lines ~515-772 (the real-operation fixture kernels and `test_the_executor_with_real_kernels_matches_the_reference`).

## Acceptance Criteria

1. **The forward program (slice 2)** — `hilclaw/model_forward.c`:
   - The input carries a **mode** (given-sequence or generation) in a form this task chooses and documents in the header comment. In the generation mode the input holds the S prompt ids and no given tokens (or another form the header states), and the file-length rule follows the mode.
   - After the `lm_head` call of each pass p (0 … G − 1), in the generation mode, the program selects from that pass's **last** logits row (row T − 1 of the logits buffer for `"all"`, the one row for `"last"`) the token whose bf16 value is greatest, the smallest id among equal values, comparing −0 equal to +0 and infinities as values; the selected id is the token fed to pass p + 1 (it can be stored at position S + p of the token array, which `run_pass` already reads as the decode pass's token). The last pass's row selects the G-th token.
   - **NaN stop**: a NaN pattern anywhere in a pass's selection row ends the process with a status other than 0, one line on standard error that names the pass, and no end mark (ADR-0153 decision 5's run failed). The exit status is chosen here and added to the header's status list; it must differ from the existing statuses 2 to 6.
   - The header's statement that the program "does no floating-point arithmetic" stays true (e.g. order bf16 patterns by an integer key derived from sign and magnitude) or is amended to say exactly what is computed; the "holds no … token selection rule" sentence is corrected.
   - **Report**: the S + G token ids — in the generation mode the prompt and the G selected ids — and the logits rows in ADR-0166 decision 7's order, ending with the end mark. Since the selected ids are known only after the passes, the byte layout of the generation-mode report is this task's choice, documented in the header. **The given-sequence mode's input and report bytes stay as they are**, unless the executor finds a single layout for both modes clearly simpler; then the reason goes in the commit body and the test helpers that write inputs or read reports by hand may be updated to the new form (no behavioural assertion weakened; listed in the PR body).
2. **The host side (slice 3)**:
   - `hilclaw/model_forward_check.check` accepts `given` `None` with a `generation_length` (the check of `hilclaw/model_binding.check` already covers the generation mode); the `_GENERATION_MODE` refusal is removed and the docstring's order of this module's own outcomes is updated.
   - `hilclaw/model_forward_run.encode_input` encodes the generation mode and `parse_report` / `run_forward_program` read its report into the same `ForwardReport` form (`tokens`: S + G ids, the prompt then the selected tokens; `logits` as before). The rows count for `"all"` and `"last"` is unchanged.
   - `hilclaw/model_forward_execute.execute` runs a generation-mode generation: it needs G when `given` is `None`. Choose the signature form (for example a keyword `generation_length` that must equal `len(given)` in the given-sequence mode, or one taken only when `given` is `None`), keep the module convention that no model parameter has a default, refuse an inconsistent combination as the check reports it, and document it. If a new required keyword is added, existing calls of `execute` / `encode_input` in tests may be updated to pass it — a mechanical change of call arguments, listed in the PR body, no assertion weakened.
   - `hilclaw/model_reference.py` code is unchanged (it stays teacher-forced; the caller passes the report's selected tokens as `given`); only its docstring sentence "it has no token selection rule and no generation mode (ADR-0176 decision 5, a later code slice)" is corrected to say the generation mode lives in the executor and a generated run is compared by passing its selected tokens.
   - The docstrings of `model_forward_check`, `model_forward_run` and `model_forward_execute` that say they have "no generation mode or token selection rule (ADR-0176 decision 5, a later code slice)" or give the refusal to "OD-31 sub-question 6" are corrected. ADR-0176 and other ADRs are **not** edited.
3. **Tests** (D12: happy, error, branch and negative cases; every touched public function; coverage gates hold; clang-backed tests are skipped where clang/POSIX is missing locally and run on CI):
   - **Program** (`tests/test_model_forward.py`, hand-written fixture kernels and inputs written by the test): a generation-mode run under both `lm_head_rows` values equals a test-side re-computation bit for bit, where the re-computation selects by the owner's rule and feeds the selected token (extend `generate` or add a helper); each decode pass is shown to take the token selected by the previous pass (e.g. a fixture whose logits make the selection change between passes); **ties** pick the smallest id (including a tie between −0 and +0, and between equal values at non-adjacent ids); negative values, +∞ and −∞ in the row order as values; a NaN in the selection row at the prefill, at a decode pass and at the last pass each stops with the chosen status, a line naming that pass and no end mark; a NaN outside the selection row (a non-last row of `"all"`) does not stop; the input refusals of the new mode (mode word out of range, file length not matching the mode).
   - **Host side**: `check` returns `ok` for `given` `None` with a valid `generation_length` and still reports invalid lengths; `encode_input` produces the generation-mode bytes the header specifies; `parse_report` reads a generation-mode report and refuses a short or malformed one; `execute`'s new argument form and its refusals (missing G in the generation mode, G inconsistent with `given`, wrong types).
   - **End to end** (`tests/test_model_reference.py` or `tests/test_model_forward_execute.py`): a generation through `execute` with the real-operation fixture kernels of `tests/test_model_reference.py` (two layers, H > H_kv, S ≥ 2, G ≥ 3, both `lm_head_rows` values) whose selected tokens equal the greedy choice over the reported rows, and whose logits, compared with `reference_logits(..., given=<selected tokens>)` by `compare`, pass the tolerance the existing test justifies from bf16 rounding.
   - The tests that asserted the generation-mode refusal (`tests/test_model_forward_check.py` ~212-224, `tests/test_model_forward_run.py` ~163, `tests/test_model_forward_execute.py` ~391 and ~417) are replaced by tests of the new behaviour — this is the behaviour change of the task, not a weakening. `tests/test_model_reference.py::test_generation_mode_is_refused` stays (the reference still refuses `given` `None`).
   - Existing tests otherwise keep passing. Under D21, assertions that pin a list of public names, imports, fields or binders may be edited only as far as this change requires and are listed in the PR body. Foreseen: `tests/test_model_forward_execute.py::test_public_names_and_fields` (and any public-name test of `tests/test_model_forward_run.py`) if a public name or field is added; none otherwise. The bit-for-bit given-sequence tests are not weakened.
4. **No real `claude`, no model files** (D16): nothing requires a logged-in `claude`, Docker, a token, Llama weights, a tokenizer, a board or network access; no Hugging Face package is installed or imported.
5. **Procedure**: branch `claude/T-0495-<slug>`, Draft PR whose title holds `T-0495` and whose body ends with `Task: T-0495`, review cycle (dev-code-review, ≤ 7 rounds), CI green, squash-merge with that body (DRIVER §5). No §9 owner notice is needed (no new record; ADR-0176's notice is posted). Result records: the language choice in one line (C for the program, as ADR-0166; Python for the host side); the chosen mode word, report layout and NaN-stop status in one line each; whether PLAN P2-13's text ("토큰을 생성하며 모델 수준에서 reference와 대조한다") is now met in the executor's reading, and what P2-13/P2-14 work remains (e.g. deriving a binding from the instance's kernels, OD-20/OD-7; registering the six bf16 kinds with `correctness.check`/`spec.write`, OD-18/OD-6); any runtime acceptance item (expected: none).

## Out of Scope

- The P2-15 comparison against Hugging Face transformers, the first-N token check on real weights, real weights, a tokenizer, model file conversion (OD-31 sub-questions 5, 7, 8; runtime only, D16).
- Sampling or any selection rule other than the owner's greedy rule; skipping NaN elements.
- Changing `reference_logits` or `compare` behaviour; joining the comparison into `execute` (ADR-0176 decision 4 rejected it).
- Registering the six bf16 kinds with `correctness.check`, `spec.write` or the instance start; deriving a binding from a key's best (OD-18, OD-6, OD-20, OD-7) — later P2-14 work.
- fp16, other targets than `cpu_standin`, isolation and limits of the executor (OD-14, NFR-4), any data-plane record of a model run.
- Editing ADR-0166, ADR-0176 or other ADRs' "less exact" sentences (PLAN "보류" holds the ADR-0166 list as a T-0470 follow-up).

## Follow-ups

## Result
