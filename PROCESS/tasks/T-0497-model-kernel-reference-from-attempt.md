---
id: T-0497
title: Read the kernel reference of the model executor from a named attempt of a run (ADR-0153 decision 3, ADR-0055, ADR-0029) and show a generation whose every kernel comes from attempt directories
phase: P2
status: DONE
commitMode: code
coversReq: [C-6, FR-6, FR-10, OD-31, "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/attempt_kernel.py
  - hilclaw/kernel_source.py
  - tests/test_attempt_kernel.py
estimatedSize: {loc: 180, files: 2}   # non-test: hilclaw/attempt_kernel.py ~170 (module docstring, one result type or error class, one public function, path and spec checks), hilclaw/kernel_source.py ~5 (the docstring sentence that lists who applies the reader). The module name `attempt_kernel` is a suggestion; the executor may choose another and adjust touchesFiles in the PR body. Tests are outside the cap (DRIVER §5, D4/D20).
hq: []
---
## Why

**State.** PLAN P2-14 (Llama 3.2 1B end to end, the D18 goal) needs "P2-11의 각 연산에 대해 instance가 커널을 내고, P2-13의 실행기가 그 커널로 토큰을 생성해 reference와 맞는다". P2-13 is checked (T-0495, PR #308, `main` `f0dbab88`). The executor (`hilclaw/model_forward_execute.execute`) takes a binding of `hilclaw.model_binding.KernelReference` values, and today only tests build those, from source files they write themselves (`tests/test_model_reference.py::real_binding`). Nothing reads a kernel reference from where an instance leaves a kernel: the attempt directories of a run (ADR-0004 decisions 1 and 3).

**The records already say what a kernel reference of an attempt is.**
- ADR-0153 decision 3: "A kernel reference is a kernel's source files with the `task.contract` of the spec it was written to (ADR-0002, ADR-0008 decision 8) and its build settings. The executor never chooses a kernel itself. How a binding is derived from a key's best is open … before then a binding is given by its caller."
- ADR-0055 decision 3 (R1 to R8): the kernel's source files are the **compiled set** of the attempt's `output/`, which `hilclaw.kernel_source.read_compiled_set` reads.
- ADR-0029 decisions 2 and 3 (with ADR-0051): the spec the kernel was written to is the attempt's `coder/…/spec.json`. `hilclaw.spec_file.parse` reads it, and the rule for a file at a path is `final_name(data_root, parse(content)) == path`.
- ADR-0116 decision 2: the build settings of a `cpu_standin` run are one fixed set in the package (`hilclaw.standin_settings`).

So this task builds a **caller-side reader**. Given a data root, a run id and one (round, candidate, attempt), it returns the `KernelReference` of that attempt. The caller still names the attempt, the call site and the shapes, as ADR-0153 decision 3 requires, and the reader chooses no kernel. **No ADR is written, and no OD is closed.** Deriving a binding from a key's best (OD-20, OD-7; ordering a best is the rest of OD-1, #5 A-4, owner-only) stays open. So do the exposure of the executor (OD-31 ⑩, OD-18, OD-23) and which attempt an instance's "result" is.

**Why now, and why this alone.** Every other next step toward P2-14 needs a new record:
- `correctness.check` for bf16 kinds (ADR-0177 slice 2) waits on HQ-0077.
- the bf16 timing run record (OD-13, OD-16 ⑥).
- a binding derived from a best (OD-20, OD-7).

A new record edits `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` and `ARCHITECTURE/StandardScenarios.md`, and open PR #309 (T-0496, BLOCKED on HQ-0077) holds all three. This task touches none of #309's files and depends on neither HQ-0076 nor HQ-0077. It is under half the size cap (DRIVER §6 "task 단위" ③). No adjacent P2-14 work exists that could join it without a record.

**PLAN order and D18.** P2-14 is a PLAN checklist item. This work is inside its completion criterion: the executor runs the kernels an instance left. The D18 rule does not apply. P2-10 is blocked on HQ-0076 (T-0493).

**No RuntimeAcceptance `실패` item is fixed by this task.** None exists as of `main` `11001364`.

**D16.** Everything is verified with attempt directories that the tests write under a temporary data root, and with fixture kernels built by clang. Nothing starts `claude` or uses Docker, a board, real Llama weights or a tokenizer.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming `claude/T-0497-<slug>`, `Task: T-0497` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`, D22), §9 (what the driver may close and how — this task closes nothing).
- `CLAUDE.md` (repo): "상시 규칙" — comments, "미결은 발명하지 않는다", branch/merge procedure, test rules, language policy, the D16 driver/runtime boundary.
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 (lines ~40-47: binding, kernel reference, fit, loading) and Boundaries.
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`: decision 3 (R1 to R8) and Limits L1 to L5.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decisions 1 to 3 (the tree, the attempt path formed by formatting alone, no walk of the tree).
- `ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md`: decisions 2 and 3; `ARCHITECTURE/decisions/ADR-0051-od6-spec-file-version-2.md`: decisions 1 to 3.
- `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md`: decisions 2 to 4.
- Code:
  - `hilclaw/model_binding.py` — `KernelReference`, `BindingEntry`, the module docstring's "Readings" and "What this module does not do".
  - `hilclaw/model_forward_execute.py` — docstring and `execute`.
  - `hilclaw/kernel_source.py` — whole, about 200 lines.
  - `hilclaw/spec_file.py` — docstring, `parse`, `final_name` and the error classes.
  - `hilclaw/layout.py` — `attempt_artefact`, `attempt_dir`, `InvalidPathValueError`, `check_run_id`.
  - `hilclaw/standin_settings.py` — docstring and `FLAGS`.
- Tests:
  - `tests/test_model_reference.py` lines ~530-790: `REAL_PRELUDE`, `REAL_SOURCES`, `clang`, `real_binding`, `executed`, `tolerance`, and the two end-to-end tests.
  - `tests/test_model_forward_execute.py` lines ~40-70: `CONTRACTS`, `binding_of`.
  - `tests/test_spec_file.py` lines ~50-110: `synthetic_hw`, `synthetic_op`, `minimal` (a valid version-2 document).
  - `tests/test_kernel_source.py`: how it builds `output/` fixtures and unreadable directories.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): before starting, check the open PRs, Issues #4/#5/#7/#8 and the unresolved `humanQuestions` of `PROCESS/STATE.json`. HQ-0076 (P2-10) and HQ-0077 (the bf16 check result form, PR #309) are not crossed by this task. Confirm that no file of `gh pr diff 309 --name-only` is touched.
2. **The reader** (suggested `hilclaw/attempt_kernel.py`; Python, the language of the modules it joins), one public function, for example `kernel_reference(data_root, run_id, round, candidate, attempt, *, flags)`:
   - It reads the spec at `layout.attempt_artefact(data_root, run_id, round, candidate, attempt, "spec.json")` with `spec_file.parse`. A spec whose `id` formats to another path (`spec_file.final_name(data_root, document)` differs from the path read) is refused.
   - It reads the compiled set of the same attempt's `output/` with `kernel_source.read_compiled_set`.
   - It returns `KernelReference(sources=<the compiled set, in R3's order, as a tuple>, contract=<the document's task.contract>, flags=<the caller's flags as a tuple>)`.
   - `flags` is required and has no default. The reader chooses no build setting; the docstring says the caller passes the settings the attempt was built with, for example `standin_settings.FLAGS` for a `cpu_standin` run (ADR-0116 decision 2).
   - The reader does not judge the attempt: no correctness or timing result, no `events.ndjson`, no `eval/`, no `best.json`. It checks no fit; `model_binding`'s checks do that when the executor runs. It writes nothing, reads no other file of the run, and walks no directory (ADR-0004 decision 3).
   - **Outcomes, each documented in the module docstring**:
     - a malformed argument: `TypeError` / `ValueError` with the attribute `parameter`, as `hilclaw/model_binding.py` and `hilclaw/model_build.py` do. A layout value error passes through, or is wrapped, consistently.
     - no spec file at the path.
     - a spec that `parse` refuses as invalid, and one of another version (ADR-0051 decision 3). These are told apart.
     - a spec whose `id` names another attempt.
     - no kernel source: each `missing` case of `kernel_source.NO_KERNEL_SOURCE_CASES`.
     - a reader failure: `KernelSourceReadError`, and an error reading the spec file other than its absence. Each is passed on or wrapped consistently.
     Choose one form — a result type with a reason drawn from a public tuple, or one error class with such a reason — and document it. If a choice beyond these mechanics turns out to be needed (for example which file holds an attempt's build settings, or a rule for choosing among attempts), stop and return BLOCKED (DRIVER §3, "Requirements OD 확정이 필요한 설계 선택"). Do not decide it.
3. **`hilclaw/kernel_source.py`**: correct the docstring sentence that lists who applies the reader, so that it names the new module. Change nothing else.
4. **Tests** (`tests/test_attempt_kernel.py`; D12: happy, error, branch and negative cases; every public function; package line and function coverage stay at or above 80 %):
   - **Happy**: an attempt directory written under `tmp_path` holds a valid version-2 `spec.json` whose `id` matches its path, with a `task.contract` from a contract module's `task_contract` (fp32 `gemm` and at least one bf16 contract). Its `output/` holds `.c` and `.h` files under admitted names. The reader returns the compiled set in R3's order, without the headers, plus that `task.contract` and the given flags.
   - **Branch**: two attempts of one run, and two candidates of one round, give their own references. An `output/` with several `.c` files keeps the byte order of names.
   - **Negative**:
     - no attempt directory; no `spec.json`; a `spec.json` that is not JSON or not a valid document; a version-1 file; a spec whose `id` names another round, candidate or attempt.
     - no `output/`; an `output/` holding no admitted `.c` file; an `output` that is a symbolic link (POSIX).
     - an unreadable `output/` (POSIX, skipped when running as root).
     - malformed `run_id`, `round`, `candidate`, `attempt`, `data_root` and `flags` (wrong types, `bool` for an integer, a negative number, a non-`str` flag).
     - Nothing is written below the data root in any case.
   - **End to end** (clang-backed; reuse the `clang` fixture's skip/fail rule):
     - For each of the six kinds of the forward program, write an attempt directory whose `output/` holds the real-operation fixture kernel of `tests/test_model_reference.py` (`REAL_PRELUDE` + `REAL_SOURCES[kind]`) and whose `spec.json` holds that kind's `task.contract` as `tests/test_model_forward_execute.py::CONTRACTS` gives it.
     - Read every kernel reference with the reader, build the binding with `binding_of`, and run `model_forward_execute.execute` in the greedy generation mode.
     - Show that the check is `ok`, and that the logits compared teacher-forced with `model_reference.reference_logits` on the selected tokens pass `compare` under the tolerance the existing test justifies.
     - Also show that the reader's references give the same report as `real_binding`'s for the same model.
     - Import the helpers from the existing test modules, as `tests/test_model_reference.py` already does. Do not copy them.
   - Existing tests pass unchanged. D21: an assertion that pins a module's public names or imports may be edited only as far as this change requires, and is listed in the PR body. None is foreseen: no existing module gains a public name or an import.
5. **Gates**: ruff check and format are clean. The full local suite passes on Linux/WSL with clang. CI is green.
6. **Procedure**:
   - Branch `claude/T-0497-<slug>`. Open a Draft PR whose title holds `T-0497` and whose body ends with `Task: T-0497`.
   - Review cycle (dev-code-review, at most 7 rounds), CI green, then squash-merge with that body (DRIVER §5).
   - No §9 owner notice: no record is written and no OD changes.
7. **Result** records:
   - the language choice and its reason in one line;
   - the chosen outcome form;
   - what remains for P2-14 (planner's candidates: ADR-0177's later slices after HQ-0077 and PR #309; the bf16 timing run record; a binding derived from a best, OD-20/OD-7);
   - any runtime acceptance item (expected none).

## Out of Scope

- Choosing an attempt for a call site: a best, a promotion, `best.json`, a correctness or timing gate (OD-20, OD-7, OD-1 / #5 A-4).
- Any tool, registry entry, command-line entry or orchestration text that exposes the executor (OD-31 ⑩, OD-18, OD-23).
- Reading `build.json` or any record of an attempt's build settings (OD-6 ②), CAS blobs, `events.ndjson` or `eval/`.
- Changing `hilclaw/model_binding.py`, `model_forward_execute.py` or any contract module. Changing `hilclaw/spec_file.py` or `hilclaw/layout.py` beyond reading them.
- Any file in PR #309: `ARCHITECTURE/` registers and ADRs, `hilclaw/contract_table.py`, `spec_tool.py`, `start_instance.py`, `check_definition.py`, `run_definition.py`, `instance_start.py`, `gemm_contract.py`, and their tests.
- Any deferred line of PLAN "보류".
- Starting `claude`, Docker, real weights, a tokenizer, a board or an API key (D16).

## Follow-ups

## Result
DONE. PR #310 squash-merged as `8647afd3` after 1 review round (Approve; its one Nit, a docstring sentence on when `no_attempt_directory` comes, was addressed under D20). CI green on the head commit (Python 3.11 and 3.14, coverage, test presence, C, sh). Local full suite on WSL Ubuntu with clang: 36202 passed, 50 skipped; package coverage 99 %.

- **Language**: Python. It is the language of `layout`, `spec_file`, `kernel_source` and `model_binding`, the modules this reader joins.
- **What was added**: `hilclaw/attempt_kernel.py` with `kernel_reference(data_root, run_id, round, candidate, attempt, *, flags)`. `hilclaw/kernel_source.py` has only its docstring sentence corrected. `tests/test_attempt_kernel.py` has 73 tests; one of them is the clang-backed greedy generation whose six kernels are all read from attempt directories.
- **Outcome form**:
  - A malformed argument raises `TypeError` or `ValueError` with `parameter`. `layout.InvalidPathValueError` passes through with `parameter` added.
  - Every other outcome raises one class, `AttemptKernelError`, whose `reason` is one of the public tuple `REASONS`, in this order:
    - the five spec outcomes: `no_spec_file`, `spec_unreadable`, `spec_invalid`, `spec_other_version`, `spec_other_attempt`;
    - then `kernel_source.NO_KERNEL_SOURCE_CASES`;
    - then `kernel_source.READER_FAILURES`.
  - The original error is the `__cause__`.
- **D21**: no existing assertion was edited.
- **No record or OD was changed**, and no §9 notice is needed.
- **What remains for P2-14**:
  - ADR-0177's later slices, after HQ-0077 and PR #309: `correctness.check` for bf16 kinds.
  - The bf16 timing run record (OD-13, OD-16 ⑥).
  - A binding derived from a key's best (OD-20, OD-7; OD-1 / #5 A-4 owner-only).
  - The exposure of the executor (OD-31 ⑩, OD-18, OD-23).
- **Runtime acceptance items**: none.
