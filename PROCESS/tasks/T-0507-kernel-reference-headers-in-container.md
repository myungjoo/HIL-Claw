---
id: T-0507
title: Land ADR-0182 code slice 2 — the kernel reference carries the kernel's own headers, read by attempt_kernel and copied by the container path of the forward pass beside the sources
phase: P2
status: DONE
commitMode: code
coversReq: [C-6, NFR-4, OD-14, OD-31, "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/model_binding.py
  - hilclaw/attempt_kernel.py
  - hilclaw/model_forward_container.py
  - tests/test_model_binding.py
  - tests/test_attempt_kernel.py
  - tests/test_model_forward_container.py
estimatedSize: {loc: 120, files: 6}   # non-test ~120 lines over 3 modules (mostly docstrings); tests excluded from the cap
hq: []
---
## Why

**State.** ADR-0182 (T-0506, PR #318, `main` `a877d0ba`) puts every build and the generation process of the model executor's bf16 forward path into ADR-0144 containers; its code slice 1 is `hilclaw/model_forward_container.py`. Decision 4 of ADR-0182 says: "**A kernel's own headers are not copied**: a `KernelReference` names its compiled set 'without its headers' (cited: `hilclaw.attempt_kernel`, observation), so a kernel that includes a header of its own fails its build in the container where the host build found the header beside its source. Carrying the headers is slice 2 (decision 9)." Decision 9 item 2 is this task: "the kernel reference carries the headers the reader of ADR-0055 found beside its compiled set (`attempt_kernel` answers them), and slice 1 copies them into `kernel-<i>` beside the sources (ADR-0144 Q3's 'The kernel's own headers are found as before, beside the kernel sources', cited). Needed before an instance kernel that includes a header of its own is run."

**Why P2-14 needs it (D18).** PLAN P2-14 runs kernels written by instances through the executor. ADR-0055 R5 admits a kernel's own `.h` headers in `output/`, so a coder may write a kernel that includes one; without this slice the container build of such a kernel fails (`build failed`) although the kernel passed its checks, whose containers do copy the headers (`hilclaw/standin_copies.py`, ADR-0144 Q3). This is a functional gap on the P2-14 path, not input hardening or wording.

**Nothing here depends on an open HQ.** The change touches no tool, no `sim.run` / `board.run` / `correctness.check` result and no data-plane file: it does not depend on HQ-0078 (T-0505, bf16 timing run result shape) or HQ-0076 (T-0493, nightly values). `KernelReference` is an in-memory record of the 2nd layer, not a data-plane schema.

**Task unit (D20 ③).** This slice is under half the size cap. The adjacent work of the same ADR is slice 3 (the fp32 `hilclaw/model_execute.py` path in containers), which ADR-0182 decision 9 says "P2-14 does not run"; under D18 it is set aside (a deferred line returned to the driver), so it is not merged here. No ADR is written: ADR-0182 already decides this slice.

**RuntimeAcceptance.** `PROCESS/RuntimeAcceptance.md` has no `실패` item as of `main` `091c069a`. This task adds no runtime acceptance item unless the executor finds one; RA-0049 (ADR-0182 items) stays as it is.

**D16.** Tests use the stub client of `tests/test_model_forward_container.py` (and its clang-backed `real_client` where `clang` is available); no real Docker daemon, no `claude`, no real weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0507-<slug>`, `Task: T-0507` trailer in commits and as the last line of the PR body, size cap, test rules D12, D21 list-assertion rule), §8 (runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`, D22).
- `CLAUDE.md` (rules; A-13 code mode and BLOCKED reasons; test rules; language policy; comment minimisation).
- `ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md` — decision 4 (lines 43-50), decision 7 (lines 63-68), decision 8 (lines 69-76), decision 9 (lines 77-83), Consequences (lines 101-115).
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md` — Q3 (line 57).
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md` — R2, R3, R5 (around line 55).
- `hilclaw/kernel_source.py` lines 1-30 and 90-145 (`read_compiled_set`, the `headers` member and its order).
- `hilclaw/attempt_kernel.py` (whole file, 197 lines).
- `hilclaw/model_binding.py` lines 210-250 (`KernelReference`, `BindingEntry`) and 1132-1170 (`_entry`, the kernel checks).
- `hilclaw/model_forward_container.py` lines 1-100 (module docstring) and 385-430 (`_copy_kernel`, `_build`).
- `hilclaw/standin_copies.py` lines 95-175 (how the check path copies the compiled set and the headers into one kernel directory; `ENTRY_EXISTS`).
- `hilclaw/model_forward_execute.py` lines 230-260 — only `_distinct_kernels` (distinct kernels are told apart by `KernelReference` equality, which now includes `headers`) and `_library_table`, both imported by the container path.
- `tests/test_model_binding.py` lines 110-130; `tests/test_attempt_kernel.py` lines 160-240; `tests/test_model_forward_container.py` lines 250-380, 600-665, 755-870.

## Acceptance Criteria

1. **`KernelReference` gains `headers`.** `hilclaw.model_binding.KernelReference` gets a fourth field `headers`, last, with default `()`, so every existing three-argument construction keeps its meaning. Its docstring says what `headers` is: the kernel's own header files (ADR-0055 R5), copied beside the sources where a build copies them, never handed to the compiler.
2. **The binding check accepts and checks `headers`.** `model_binding`'s kernel check (`_entry`) refuses, with `TypeError` and a message naming the call site as for `sources`, a `headers` that is not exactly a `tuple`, or that holds an element that is not a `str` or `os.PathLike`. An empty `headers` is accepted. No other check of `_entry` changes.
3. **`attempt_kernel.kernel_reference` answers the headers.** Its answer's `headers` is `tuple(source.headers)` of `kernel_source.read_compiled_set` (R5, the reader's order). `sources`, `contract`, `flags` and every outcome and its order are unchanged. The module and function docstrings no longer say "without its headers"; they say the headers are in `headers`.
4. **The container path copies the headers.** `hilclaw.model_forward_container` copies each distinct kernel's `headers`, read and written as its sources are (`_read(..., harness=False)`, `_write_new`, no link followed), under their basenames into the same `kernel-<i>` sub-directory, after the sources. The build container's command line is unchanged: headers are not on it. A header whose basename equals a source's or another header's basename of the same kernel raises `standin_copies.CopyError` with `failure == standin_copies.ENTRY_EXISTS`, before any container starts, and leaves no build directory behind (as two sources of one name do today). A missing or non-regular header raises what reading a missing source raises today, with the same cleanup. The module docstring's step 3 names the headers and the sentence "it copies no header of a kernel, since a `KernelReference` names none (decision 9)" is replaced by what is now true.
5. **Host paths unchanged.** `hilclaw/model_forward_execute.py`, `hilclaw/model_execute.py` and `hilclaw/model_build.py` do not change behaviour; on the host a header is found beside its source as before. Do not edit them unless a docstring there becomes false (say which in Result).
6. **Tests** (D12: happy, error, branch and negative cases; every public function of the touched modules stays covered; coverage ≥ 80 % line and function):
   - `test_model_binding.py`: a `KernelReference` with non-empty `headers` binds; `headers` of a `list`, of a non-path element, or of a `tuple` subclass is refused with `TypeError`; the default is `()`.
   - `test_attempt_kernel.py`: an attempt with `k.h` beside `a.c`, `b.c` answers `headers == (output / "k.h",)` and `type(headers) is tuple`; several headers keep the reader's order; an attempt without headers answers `()`.
   - `test_model_forward_container.py` (stub client): headers lie in `kernel-<i>/` with their bytes (the stub's `seen` map) and are absent from the build command; a header clashing with a source name, and two headers of one name, raise `ENTRY_EXISTS` and start nothing; a missing header raises and leaves nothing; two kernels equal but for `headers` are built as two kernels.
   - Where `clang` is available (the existing `clang` fixture and `real_client`): one kernel whose source does `#include "<name>.h"` of its own header builds and the greedy generation completes through the stub client; skipped otherwise as the existing clang-backed test is.
7. **Existing tests.** No existing assertion changes except these, which pin a field list or the old "no headers" answer and are expected to change (D21; list each one you edit in the PR body): `tests/test_model_binding.py` `KernelReference._fields == ("sources", "contract", "flags")` (line ~125); `tests/test_attempt_kernel.py` `test_the_answer_is_what_the_reader_and_parse_give` (`answer == (compiled_set, contract, FLAGS)`, which gains the headers member). `test_model_forward_container.py::test_public_names_and_fields` should not need an edit (no public name is added); if it does, list it.
8. **No record edits.** No file under `ARCHITECTURE/` changes; no OD status changes; no #5 notice is needed (no OD is closed). Sentences of ADR-0182 (decision 4 "A kernel's own headers are not copied", Consequences/Boundaries "A kernel's own headers (slice 2)") and of other records that become less exact are listed in Result, not edited.
9. **Result** records the language (Python, the language of the touched modules) and the reason, the edited list assertions, and the less exact sentences.

## Out of Scope

- ADR-0182 slice 3 (the fp32 `model_execute` path in containers) — set aside under D18.
- Passing `-I` or any include flag; headers outside the kernel's sub-directory; headers of the forward program.
- Choosing an attempt for a call site, a binding from a key's best, `best.json` (OD-20, OD-7, OD-1 / #5 A-4).
- The bf16 timing run, `timed` flags, `sim.run` / `board.run` (HQ-0078, T-0505).
- Exposure of the executor as a tool (OD-31 ⑩, OD-18, OD-23); time-limit records or memory bounds (OD-14).
- Any change to `hilclaw/standin_copies.py` or the check path.

## Follow-ups

## Result

**DONE.** PR #319 squash-merged as `c1acfe33` (branch `claude/T-0507-kernel-headers-in-container` deleted). Review: 1 round, Approve (fresh-context `dev-reviewer`); afterwards one nit fixed without re-review (D20: rename `test_an_attempt_without_headers_answers_none` → `..._answers_no_header`); the other nit (helper `kernels_in` duplicating an inline dict of an existing test) was left alone because AC7 forbids editing that test. CI green on the final head: Python 3.11/3.14, Coverage gate, C gate, sh gate, Test presence. Local: full pytest 35468 passed / 1930 skipped (Windows; clang tests skip), ruff check + format clean; the three touched modules have 100 % line coverage.

- **Language**: Python, the language of the three touched layer-2 modules (`model_binding`, `attempt_kernel`, `model_forward_container`).
- **Edited list assertions (D21)**: `tests/test_model_binding.py::test_named_tuples` (`KernelReference._fields` gains `"headers"`); `tests/test_attempt_kernel.py::test_the_answer_is_what_the_reader_and_parse_give` (the expected tuple gains `source.headers`). `test_model_forward_container.py::test_public_names_and_fields` needed no edit.
- **Test helper change**: `tests/test_attempt_kernel.py::write_forward_attempts` gains an optional `header` (the prelude moved into a header that the source includes); the clang-backed `test_a_greedy_generation_from_attempts_through_a_stub_client` is parametrised with `header` in `[None, "fx.h"]` (it runs in CI on ubuntu).
- **Host-path docstrings**: none of `model_forward_execute.py`, `model_execute.py` or `model_build.py` became false; none was edited.
- **Records now less exact (not edited, AC8)**: ADR-0182 decision 4, "A kernel's own headers are not copied … Carrying the headers is slice 2"; ADR-0182 Consequences/Boundaries, "A kernel's own headers (slice 2)" listed as not yet done.
- **Runtime acceptance items**: none added.
- **Follow-ups**: none (ADR-0182 slice 3 was already deferred by the driver).
