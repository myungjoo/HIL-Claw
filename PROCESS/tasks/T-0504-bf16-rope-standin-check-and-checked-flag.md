---
id: T-0504
title: Build the cpu_standin operation of correctness.check for bf16 rope (rows on the container's standard input, ADR-0180 limits) and set the checked flag of the rope entry (ADR-0177 slice 3, second part)
phase: P2
status: DONE
commitMode: code
coversReq: [C-6, FR-9, FR-10, NFR-4, OD-14, OD-16, OD-18, OD-31, "PLAN P2-11", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/standin_container.py
  - hilclaw/standin_settings.py
  - hilclaw/standin_check.py
  - hilclaw/contract_table.py
  - tests/test_standin_container.py
  - tests/test_standin_settings.py
  - tests/test_standin_check.py
  - tests/test_contract_table.py
  - tests/test_check_tool.py
  - tests/test_check_definition.py
  - tests/test_check_admission.py
  - tests/test_backend_conformance.py
estimatedSize: {loc: 140, files: 4}   # non-test: standin_container ~35 (optional input, --interactive, check, docstring), standin_settings ~15 (rope in BF16_CHECK_KINDS, its dimensions and work), standin_check ~60 (rope arguments, rows from start_position, the input through run_container, docstrings), contract_table ~2. Tests are outside the cap (DRIVER §5, D4/D20).
hq: []
---
## Why

**State.** PLAN P2-14 (Llama 3.2 1B end-to-end, the D18 goal) needs every operation of P2-11 to come from an instance, and the instance start admits a contract only when its table entry is both `checked` and `timed` (ADR-0177 decision 2). On `main` `23bdd31a`, `correctness.check` serves bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and `sdpa_kv_cache` on the mock and `cpu_standin` (those five entries are `checked`), and T-0503 (PR #316, ADR-0180) built the tool side and the mock for `rope`. The `rope` entry is still not `checked`, because `cpu_standin` refuses a `rope` check.

**What this task is.** ADR-0180 Consequences names the next slice: "the `cpu_standin` operation for `rope` — `run_in_container` with the input and `--interactive` (decision 3), the limits of decision 2 in `standin_settings` (`rope` in `BF16_CHECK_KINDS`, E as above), the rows of `start_position` sent through the container — and the `checked` flag of the `rope` entry" (ADR-0177 decision 5 item 3, second part). Every design point is already decided by ADR-0180 (accepted, §9 notice posted); **no new ADR is written here** and no register changes.

**Size (D20 ③).** This slice is below half the cap. The adjacent work of the same PLAN item — the record of the bf16 timing run (ADR-0177 decision 5 item 4, task T-0505) — is not merged into it: that record is likely to stop at an owner question on the form of a run result (a data-plane schema change, as HQ-0077 was for the check), and merging would hold this code slice behind it.

**PLAN order and D18.** P2-11 and P2-14 are PLAN checklist items; D18 does not apply. P2-10 waits on HQ-0076 (T-0493). `PROCESS/RuntimeAcceptance.md` has no `실패` item as of `main` `23bdd31a`, so none is fixed here.

**D16.** Everything is verified with tests in this repository, with the stub container client the existing tests use; nothing starts `claude`, a real Docker daemon, needs a board, real Llama weights or an API key. Whether a real client passes the rows byte for byte, and whether the limits fit on each C-7 system, are already runtime acceptance items RA-0047 and RA-0048 (from T-0503); this task adds none unless the code reveals a new fact only a real container can establish.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0504-<slug>`, `Task: T-0504` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items, D22).
- `CLAUDE.md` (rules; A-13 BLOCKED reasons; test rules; language policy; comment minimisation).
- `PROCESS/tasks/T-0502-bf16-check-standin-operation-time-limits.md` and `PROCESS/tasks/T-0503-bf16-rope-check-start-position-tool-side.md` (their Results: how the bf16 `cpu_standin` operation and the `rope` tool side were built, and which assertions they edited).
- `ARCHITECTURE/decisions/ADR-0180-od16-bf16-rope-check-start-position.md` (all; decisions 1 to 3, A-13 reading, Consequences "Next slice").
- `ARCHITECTURE/decisions/ADR-0179-od14-bf16-standin-check-time-limits.md` decisions 1 to 8 (the rule, W = A + 10·E, the header copy, the answers at a limit).
- `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md` decisions 3, 4, 7 and 10 and Consequences (the rows on standard input, the command line, the report; `local_run.run`'s `stdin_data` and the broken pipe).
- `ARCHITECTURE/decisions/ADR-0168-od18-standin-container-situations.md` decisions 2, 3 and 5 (rows C8, C10, C16; build-dir removal); `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md` decisions 2 and 3.
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md` decisions 1, 2 and 5 (the flags, which place admits what).
- Code: `hilclaw/standin_container.py` (`run_in_container`, `_check`, `_check_arguments`), `hilclaw/standin_check.py` (`operation`, `_checked`, `_bf16_checked`, `_carry_out`, `run_container`), `hilclaw/standin_run.py` (the other caller of `run_container`, line ~175 — must keep its behaviour), `hilclaw/standin_settings.py` (`BF16_CHECK_KINDS`, `_BF16_DIMENSIONS`, `bf16_verification_process_time_limit_s`, `_bf16_work`), `hilclaw/contract_table.py` (`TABLE`, the `rope` entry), `hilclaw/local_run.py` (`run`, `stdin_data`, `_feed`), `hilclaw/harness/bf16_rope_verification.py` (`program_arguments`, `start_position`, `run_bf16_rope_verification` — the reference for how the rows are made and fed), `hilclaw/harness/bf16_rope_arrays.py` (`table_rows`), `hilclaw/harness/bf16_verification_build.py` (`PROGRAM_SOURCES`), `hilclaw/check_judging.py` (how the judge gets P for `rope`).
- Tests: the test files in `touchesFiles`; in particular `tests/test_standin_check.py` around line ~948 (the `rope` refusal row), `tests/test_check_tool.py` lines ~1300–1450 (`rope` cases, `test_the_default_registry_still_answers_rope_not_covered`), `tests/test_check_definition.py` lines ~860–900 (`CHECKED_BF16`, `ROPE`, `test_a_bf16_record_is_not_covered_by_the_check`), `tests/test_contract_table.py` (the flag pins, lines ~80–140).

## Acceptance Criteria

1. **Container input (ADR-0180 decision 3).** `hilclaw.standin_container.run_in_container` takes an optional keyword input of `bytes` (name of the executor's choice), `None` by default. Given, the client command gains `--interactive` among the options before the image (never `--tty`) and the bytes are passed to `hilclaw.local_run.run` as `stdin_data`; not given, the command and the call to `local_run.run` are exactly what they are today (no `stdin_data`, so the null device). An input that is not exactly `bytes` (for example `str`, `bytearray`, `memoryview`, `int`) is refused before the client starts, through the same path as the function's other argument checks so that `hilclaw.standin_answer` places it as ADR-0168 row C16; an empty `bytes` is the executor's choice, stated in the docstring and tested. No build container is ever given an input.
2. **Limits (ADR-0180 decision 2).** `hilclaw.standin_settings.BF16_CHECK_KINDS` holds `rope` (in the order of `contract_table.TABLE`), its dimensions are `("m", "h", "d")`, and `bf16_verification_process_time_limit_s("rope", (m, h, d), draws)` is `min(1500, 10 + draws * (1 + W / 2e8))` with A = 0 and E = 2·m·h·d + 2·m·d. Its values match ADR-0180's table (per-draw 1.433 s at (2048, 32, 64), 1.118 s at (2048, 8, 64), 1.027 s at (128, 32, 64), 1.000 s at (1, 32, 64), to the precision the table gives) and the cap. The build limit stays 60 s. The limits of the other five kinds and of fp32 `gemm` are unchanged.
3. **The operation (ADR-0180 decisions 1 to 3).** `hilclaw.standin_check.operation` accepts `Bf16CheckParameters` of kind `rope`: it copies `PROGRAM_SOURCES["rope"]` and the shared header as for the other bf16 kinds, builds it with ADR-0116's fixed set under the 60 s limit, computes P with `hilclaw.harness.bf16_rope_verification.start_position(dims, seed=seed)`, makes the rows with `hilclaw.harness.bf16_rope_arrays.table_rows(dims, start=P)` and runs the program with `bf16_rope_verification.program_arguments(dims, draws=draws, seed=seed)` and the rows' bytes as the process container's input, under the limit of criterion 2. The P the operation uses equals the P `check_judging` uses for the same check (same function, same dims and seed) — a test asserts it. What the operation returns (the report bytes or one of the four conditions) and every ADR-0168/ADR-0169 answer are as for the other bf16 kinds; the build container gets no input. NumPy is imported only where the existing bf16 path already imports it, so building the default registry still imports no NumPy (`tests/test_check_definition.py` `..._imports_no_numpy` stays green).
4. **Other callers unchanged.** `hilclaw/standin_run.py` (the timing run) and the fp32 `gemm` and five bf16 check paths start their containers exactly as today (no input, no `--interactive`); a test pins this for at least one fp32 process container and one non-`rope` bf16 process container.
5. **Flag.** `hilclaw.contract_table`: the `rope` entry is `checked=True`, `timed=False`. No other flag changes. So through the default registry a covered `rope` record is now admitted by `correctness.check`, and still refused by `sim.run`, `board.run` and the instance start (`run_covers`, `start_covers` false).
6. **Tests** (D12): happy — a `rope` check through the default registry on the mock judged pass (now admitted); a `rope` check through `cpu_standin` with the stub client (as the existing `cpu_standin` bf16 tests do) at a small covered shape with m = 1 (both parities of the seed, so both P = 127 and P = 2047) and one with m ≥ 2, asserting the command has `--interactive` and no `--tty`, the input bytes equal `table_rows(dims, start=P).tobytes()`, the program arguments and the limit; the settings values of criterion 2; branch — the container function with and without the input (command and `local_run.run` arguments), a `rope` process container that ends with a non-zero status (`exit_status`), one that passes its limit (`time_limit`), a build failure (`build_exit_status`, no input given to the build); negative — a non-`bytes` input refused before the client starts (C16), a `rope` `Bf16CheckParameters` with odd `d`, a zero, a `bool` or a missing dimension, wrong number of dimensions, `draws` or `seed` out of range, each refused before a container starts. Package line and function coverage stay at or above 80 %, ruff is clean, the full local suite passes on Linux/WSL with clang; CI is green.
7. **Existing tests.** D21 list pins foreseen: the public-name assertion of `tests/test_standin_settings.py` (if a name is added) and any assertion that pins the tuple `standin_settings.BF16_CHECK_KINDS`; the flag pins of `tests/test_contract_table.py` (`test_the_flags_of_this_slice`, `test_the_four_predicates_of_a_bf16_contract`, the `checked = contract is not rope_bf16_contract` lines ~86 and ~133, the `rope` branch line ~116). Besides those, this task's purpose changes the assertions that pin `rope` being refused by `cpu_standin` and by the default registry's check, and only those: the `bf16("rope", (1, 2, 4))` row of the refusal parametrisation in `tests/test_standin_check.py` (line ~948), `tests/test_check_tool.py::test_the_default_registry_still_answers_rope_not_covered` (becomes an admission test), `tests/test_check_definition.py::test_a_bf16_record_is_not_covered_by_the_check` with `ROPE` / `CHECKED_BF16` (rope joins the judged list), and any `rope` refusal under `check_covers` in `tests/test_check_admission.py` or `tests/test_backend_conformance.py` that the full suite finds. Other existing assertions stay unchanged. List every edited assertion in the PR body.
8. **Docstrings.** Update the docstrings of the touched modules where they say `rope` is refused or not served (for example `standin_check.py` line ~96, the `standin_settings` module docstring, `run_in_container`'s "no standard input" wording) — only in the touched modules; less exact sentences elsewhere are listed in Result, not edited.
9. **Result** names: the language choice and reason (Python), the PR, review rounds, edited assertions, any runtime acceptance item beyond RA-0047/RA-0048 worded for `PROCESS/RuntimeAcceptance.md` (D22) or "none", the less exact sentences found outside the touched files (for example ADR-0179 decision 1 "Not covered: `rope`", ADR-0180 Context on `run_in_container`), and the planner's next candidate (expected: T-0505, the record of the bf16 timing run).

## Out of Scope

- Any ADR or register edit (`ARCHITECTURE/` is not touched; ADR-0180 already decides this slice).
- The bf16 timing run, the `timed` flags, `sim.run` / `board.run` for bf16 (T-0505 and later); the instance start; the executor binding (OD-20, OD-7); catalog entries (OD-22).
- Handing the operation's rows to the judge to save one table build (ADR-0180 decision 2 leaves it optional; not done here).
- The number of draws, the tolerance, the seed source (owner, OD-16 ⑤, OD-3); OpenMP (HQ-0034, PLAN "보류").
- Any deferred line of PLAN "보류". Starting `claude`, a real Docker daemon, real weights, a board, an API key (D16).

## Follow-ups

## Result

**DONE**: PR #317 was squash-merged as `32a51138` after review Approve and green CI (run 40677055597 on `8cb896a6`: Python gate 3.11 and 3.14, C gate, sh gate, test presence and coverage gate all pass); the branch was deleted.

**Review**: 1 round (dev-reviewer, context-isolated; PR comment 6467308208): Approve, no Must-fix or Should-fix, three Nits (param id `rope-checked` → `rope-not-checked`; the test report no longer uses the private `mock_check._nearest_bf16`; a duplicate `pytest.approx` dropped). All three were fixed in `8cb896a6`; they are test-only and do not change meaning, so under D20 there was no re-review.

**Language**: Python, because every touched 2nd-layer module is Python.

**Code**:
- `standin_container.run_in_container(..., stdin_data=None)`: exactly `bytes` adds `--interactive` before the image (never `--tty`) and passes the bytes to `local_run.run` as `stdin_data` (empty `bytes` admitted); `None` leaves the command and the call unchanged; any other type, a `bytes` subclass included, is refused with `TypeError` and `parameter="stdin_data"` before the client starts (no `place_error` row, C16).
- `standin_settings`: `rope` is in `BF16_CHECK_KINDS` in table order, dims `(m, h, d)`, A = 0, E = 2mhd + 2md, matching ADR-0180's table; the build limit stays 60 s.
- `standin_check`: for `rope` it computes `program_arguments`, `P = start_position(dims, seed=seed)` and the bytes of `table_rows(dims, start=P)` before the image is read or a directory is made; the rows go only to the process container; `run_container` gains a keyword `stdin_data=None` passed on unchanged, so other kinds start their containers exactly as before.
- `contract_table`: `rope` is `checked=True, timed=False`.
- Non-test files: 4, about 105 lines.

**Edited existing assertions** (D21; also listed in the PR body): in `test_standin_settings`, `test_standin_check`, `test_contract_table`, `test_check_tool`, `test_check_definition` and `test_check_admission`, the kind lists and the `rope`-not-checked rows were updated to `rope` checked; no change in `test_backend_conformance.py`.

**Local tests**: full suite on WSL (Ubuntu, clang) at `8cb896a6`: 37259 passed, 50 skipped; ruff check and format clean.

**Runtime acceptance items**: none beyond RA-0047/RA-0048.

**Less exact sentences outside the touched files (not edited)**: ADR-0179 decision 1 and Boundaries ("Not covered: `rope`"); ADR-0180 Context and Consequences on `run_in_container` standard input and `rope` refusal; ADR-0164 Boundaries on registration; `hilclaw/harness/bf16_rope_verification.py` module docstring.

**Follow-ups**: none.
