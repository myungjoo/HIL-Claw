---
id: T-0534
title: Add the model graph file of ADR-0193 decision 5 (format 1 reader, checks against the contract table and a binding, resolution into a per-pass call plan) and the Llama graph file
phase: P3
status: DONE
commitMode: code
coversReq: [D27, OD-32, C-6, OD-31, "PLAN P3-4"]
dependsOn: []
touchesFiles:
  - hilclaw/model_graph.py
  - hilclaw/graphs/llama.json
  - hilclaw/model_binding.py
  - tests/test_model_graph.py
  - tests/test_model_binding.py
estimatedSize: {loc: 560, files: 3}
hq: []
---
## Why

**PLAN P3-4** ("모델 그래프 파일"): read an internal file that states nodes and connections and run the model from it; write the Llama structure in this form and show on synthetic weights that it gives the same results as today, and check another structure on synthetic weights too. The real-weight check is a runtime acceptance item after P3-4 lands; external formats stay under OD-9. P3-1 (ADR-0193, `d213d9a6`) and P3-2 (T-0532) are checked. P3-3 stays unchecked on purpose (ADR-0193 decision 8: it waits on HQ-0090 and HQ-0091), and P3-4 does not depend on those answers (decision 8, row P3-4: "Must wait for: Nothing"), so under DRIVER §6 D27 ⑥ P3-4 goes on.

**Design.** ADR-0193 decision 5 is the binding text: the file's members, the node forms, "a connection is a buffer name", logical weight names mapped by a caller's provider, and the place outside the data plane. Decision 8 sizes P3-4 at about 1000 LOC with the C program as **two tasks**: (1) format, reader, Llama file — **this task**; (2) program, host, second model — T-0535, which depends on this one.

**Order (DRIVER §6 D27 ①).** On `main` `5d7650d7`: no open `nightly-failure` issue, no open PR, no `PROCESS/RuntimeAcceptance.md` item whose `상태` is `실패` (RA-0056 is `미확인`), no P2-15 preparation pending, and no `TODO` task. So the next P3 item that can go ahead is P3-4. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs not crossed (D27 ⑦).** HQ-0081 (S6 scale), HQ-0088 and HQ-0089 (candidate kinds and their record), HQ-0090 (unit list), HQ-0091 (oracle at `virtual_npu`, a new type): none concerns the graph file. This task chooses no dtype other than bf16, no RoPE constant (HQ-0070), no model, no external format (OD-9) and no data-plane member.

**P2-15 must not change (D27, ADR-0193 decision 5).** `model_forward.c`, `model_forward_run.py`, `model_forward_check.py`, `model_forward_execute.py`, `model_forward_container.py` and `model_check.py` are not edited. What the owner's P2-15 check runs stays byte-for-byte the same.

**D16.** Pure Python and a JSON file; no process is started, no `claude`, no Docker, no model file.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0534-<slug>`, the `Task: T-0534` trailer and the PR body's last line, the size cap, the test rules D12, the list-assertion rule D21), §3 "BLOCKED 사유", §6 D27.
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책" (state the language and the reason in one line of the commit body and `## Result`), "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`: Status; decision 1 (the row "Six kinds, fifteen call sites and one call order are fixed"); **decision 5 in full** (the binding text); decision 8, row P3-4; Alternatives, rows of point 5; Consequences, "A-13 reading".
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`: decisions 1 to 4 (order, buffers, operands, copies, cache, host-side inputs) and 6 (the whole-generation check and its join).
- `ARCHITECTURE/decisions/ADR-0176-od31-model-level-reference-and-comparison.md` decision 5 (`lm_head_rows`, the generation mode); `ADR-0153-od31-model-executor.md` decisions 3 to 5 (binding entries, loading, outcomes); `ADR-0155-od23-first-case-instance-start-command-line.md` decision 3 (JSON input rules, left to the code) and `hilclaw/new_run.py` (how that code applied them).
- Code: `hilclaw/model_forward.c` lines 1-148 (the header comment: call sites, order, buffers) and 511-549 (`run_pass`, the one structure the Llama file must reproduce); `hilclaw/model_binding.py` lines 1-260 and the `*_shape` functions, `check` and `_bind`, `_unfit`, `_entry` (lines 284-460, 1028-1182); `hilclaw/model_forward_check.py` lines 1-135; `hilclaw/model_forward_run.py` lines 75-88; `hilclaw/contract_table.py` (whole); one bf16 contract module, for example `hilclaw/rmsnorm_bf16_contract.py` (its `PROTOTYPE`, `op_signature_record`, `task_contract`); `hilclaw/json_text.py` (whole); `hilclaw/model_files.py` lines 1-140 (the provider the Llama file will be read with in a later run).
- Tests: `tests/test_model_binding.py` (helpers and any public-name assertion), `tests/test_model_forward_execute.py` lines 1-180 (how bindings and synthetic models are built).

## Acceptance Criteria

1. **New module `hilclaw/model_graph.py`** with a module docstring that states format 1 in full (every member and node form of ADR-0193 decision 5, plus any extension of criterion 3) and what the module does not do. Every public function and class has a docstring; argument errors raise `TypeError` or `ValueError` with the attribute `parameter`, as `model_binding` does.
2. **Reading.** A public function reads a graph from a path (and one from text or bytes, for tests) and returns an immutable graph value. Decoding follows the rules `hilclaw.new_run` applies for ADR-0155 decision 3 through `hilclaw.json_text`: UTF-8, one JSON object, no repeated member name, no `NaN`/`Infinity`, no `-0`. Every failure is one exception class of this module (for example `GraphFileError`) with a `reason` from a public tuple of reason names and a message naming the JSON path; at least: unreadable, malformed JSON, not an object, missing member, unknown member, wrong type, `graph_format` not `1`, a bad expression (an operator other than `+`, `-`, `*`, parentheses; a name that is not a declared dimension, an always-available name or an extension name; an empty or overlong text), a name declared twice (across `dimensions`, `weights`, `tables`, `scalars`, `state`, `buffers`), a reference to an undeclared name, an unknown `op`, a `site` used twice, a `{index}` outside a `repeat` or a `per` entry referenced without it, a `repeat` whose `count` is not a dimension, an unknown table `source`, and an `output.buffer` that is not a buffer. Reading is pure: it starts no process, writes nothing and reads no file but the one named.
3. **Format 1 as written, extended only where the Llama file needs it.** The members and nodes are exactly those of ADR-0193 decision 5. Decision 5 allows P3-4 to extend format 1 before its first landing where writing the Llama file shows a need ("Completeness"). An expected case: the per-layer cache of ADR-0166 decision 4 has C = S + G - 1 rows, and `T`, `P` and `R` alone cannot express C, so an always-available name for it is needed. Each extension is the least that serves `run_pass`, is stated in the docstring beside the decision-5 table, and is listed in `## Result`. No member is added for another reason.
4. **Checks against the contract table.** A `kernel` node's `kind` must be the `kind` of a bf16 entry of `contract_table.TABLE` (format 1 is bf16 only, ADR-0193 decision 5). Its `shape` members, its `operands` names and its `scalars` arguments must be exactly those of that contract, read from the contract module (for example from `op_signature_record`'s parameters and `task_contract`'s operands), not from a list copied into `model_graph.py`. A mismatch is a `GraphFileError` with its own reason. No contract module is edited.
5. **Resolution.** A public function resolves a graph for given dimension values (a mapping from each name of `dimensions` to a positive `int`), a prompt length S, a generation length G and `lm_head_rows` (`"all"` or `"last"`) into a plan: per pass (pass 0 the prefill with T = S, P = 0; decode pass k with T = 1, P = S + k - 1, as `model_forward.c`), the ordered steps with every expression evaluated. A kernel step holds its `site`, `kind`, shape tuple in the contract's member order, and for each operand the array it names (buffer, weight entry, table, state entry) with its element offset. Embed and copy steps hold their counts, strides and offsets. Arrays carry their element counts: buffers evaluated once at the largest T of the generation, as ADR-0153 decision 4 allocates, and state and tables at their evaluated shapes. A shape member or element count that is not a positive integer, an offset range that runs past its array, and two operands of one kernel step that overlap (ADR-0166 decision 3, "Distinct arrays at every call") are refused with their own reasons, before any plan is returned. Missing or unknown dimension values and wrong argument types are argument errors.
6. **Binding check.** A public function checks a binding — a mapping from each `site` of the graph to a sequence of `model_binding.BindingEntry`, the form `model_forward_check.check` takes — against a resolved plan. Outcomes are `model_binding`'s `"no_kernel"` and `"kernel_unfit"` with the same meaning (ADR-0153 decision 5). For every kernel step the result names the kernel bound to its site at its shape. To avoid a second copy of the fitting rules, the executor may make one generic function of `model_binding` public (for example one that binds a site's entries to a list of shapes of a given contract), keeping every existing function's behaviour; it is named in `## Result`. A binding key that is not a site of the graph makes the binding malformed, as in `model_binding`.
7. **The Llama graph file `hilclaw/graphs/llama.json`** (the executor may choose another path inside `hilclaw/`, named in `## Result`): `dimensions` `D`, `F`, `V`, `N`, `H`, `H_kv`, `d`; weights with the logical names of the fields of `model_forward_check.Weights` (per-layer ones `per` `N`); the RoPE table from `hilclaw.rope_table`; `eps`; the per-layer `cache_k`, `cache_v`; the fifteen sites with the names of `model_forward_run.CALL_SITES`; nodes in the order of `run_pass`, including the three range copies, `freqs_cis` `{"of": "rope", "start": "P*d"}` and `lm_head` with `m` `R` on `{"of": "normed", "start": "(T-R)*D"}`. A module-level name gives its path (as `model_build.FORWARD_PROGRAM_SOURCE` does).
8. **The Llama file is `run_pass`.** Tests resolve the Llama file at several small dimension sets (at least two layers, H a multiple of H_kv and larger than it, S ≥ 2, G ≥ 3) under both `lm_head_rows` values, and show for every pass:
   - the sequence of `(site, kind, shape)` equals that of `run_pass` in `model_forward.c`, with each shape equal to what `model_binding`'s `gemm_shape`, `rmsnorm_shape`, `elementwise_add_shape`, `swiglu_shape`, `rope_shape` and `sdpa_shape` give for that pass;
   - each operand's array and offset equal those `run_pass` passes (written in the test from the C source's expressions);
   - the embed and copy steps equal `run_pass`'s copies;
   - buffer, state and table element counts equal those of `allocate_activations` and `read_inputs`.
   For the same binding over the fifteen sites, the binding check of criterion 6 is ok exactly when `model_forward_check.check` (with valid weights and settings) is ok, and binds the same kernel to every call. The no-kernel and unfit cases are compared too.
9. **Tests (D12)** in the new `tests/test_model_graph.py`: every public function and class; happy, error, branch and **negative** cases, one per refusal reason of criteria 2 to 6, each built from the Llama file text with one change; the expression evaluator's precedence and parentheses; a `repeat` with `{index}`. If `model_binding` gains a public function, `tests/test_model_binding.py` covers it. Package line and function coverage stay at or above 80 %. The full suite and `ruff` pass locally.
10. **Existing tests pass unchanged**, apart from assertions that pin a list of public names, imports, fields or binders (DRIVER §5, D21). Pinning assertion this task may touch: a public-name assertion of `tests/test_model_binding.py` if one exists and `model_binding` gains a public function. Each edited assertion is listed in the PR body.
11. **No frame change.** The graph file is outside the data plane (ADR-0193 decision 5): no tool writes it to `runs/`, `db/` or the CAS, no data-plane member names it, and `graph_format` is no data-plane version. No contract-table entry, `kind` or `dtype` value is added. If the work shows otherwise, stop and return `BLOCKED` with the reason (A-13; DRIVER §8).
12. **Size.** If the change is seen to exceed 600 LOC or 10 files (tests excluded, DRIVER §5; the JSON file counts), land criteria 1 to 5, 7 and 8's first three bullets, and propose the binding check (criterion 6 and the last part of 8) as a split in `## Follow-ups`. T-0535 then takes it first.
13. **`## Result`** states: the language line; the path of the Llama file; every extension of format 1 (criterion 3) with the need that caused it; any `model_binding` function made public; the edited assertions; and the plan's public form (names, members), which T-0535 encodes for the C program.

## Out of Scope

- The C program that runs a plan, the binary encoding of the plan for it, the host-side run and its report, and the second graph of another structure (T-0535).
- Any edit of `model_forward.c`, `model_forward_run.py`, `model_forward_check.py`, `model_forward_execute.py`, `model_forward_container.py`, `model_check.py` or `model_files.py`, and replacing the forward program by the graph (ADR-0193 decision 5: a later record's).
- External model formats and `model_ref` (OD-9, #5 B-5); a dtype other than bf16; fusion (C-6).
- Any edit of `ARCHITECTURE/`, PLAN or RuntimeAcceptance.

## Follow-ups

- T-0535: the graph program `hilclaw/model_graph.c`, the plan encoding and host run, the byte-for-byte check against `model_forward.c`, and the second model.

## Result

PR #351 squash-merged as 14ad0c2d; 2 review rounds (R2 Approve). Per acceptance criterion 12 the binding check (end of criteria 6 and 8) moves to T-0535. No new RA item.
