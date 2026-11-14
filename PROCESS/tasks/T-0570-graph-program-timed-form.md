---
id: T-0570
title: ADR-0206 slice 1 (PLAN P3-12) — add the timed form of the graph program (`model_graph.c`), its encoding and report reading in `hilclaw.model_graph`, and a host-path timed run of R repetitions in `hilclaw.model_graph_execute`, verified with the real clang
phase: P3
status: DONE
commitMode: code
coversReq: [D27, FR-19, OD-33, "PLAN P3-12", ADR-0206]
dependsOn: []
touchesFiles:
  - hilclaw/model_graph.c
  - hilclaw/model_graph.py
  - hilclaw/model_graph_execute.py
  - tests/test_model_graph.py
  - tests/test_model_graph_program.py
  - tests/test_model_graph_execute.py
estimatedSize: {loc: 300, files: 3}
hq: []
---
## Why

**PLAN P3-12** (LLM-level evaluation) is the first unchecked P3 item that can move. Its §9 record, **ADR-0206** (`ARCHITECTURE/decisions/ADR-0206-od33-llm-level-evaluation.md`, landed by T-0569 on `main`), lists four slices in decision 7. Slices 3 and 4 wait on the owner's answers to **HQ-0102** (HQ-A: the record form and the key of LLM-wide code) and **HQ-0103** (HQ-B: the lengths); **slices 1 and 2 need only the ADR** (decision 7, "Slices 1 and 2 need only this record"). This task is **slice 1**: the timed form of the graph program (decision 3) and its host side.

**Order** (DRIVER §6 D27 ①, D31 ①). At `main` `4aeba6e6`: no open PR; no open `nightly-failure` issue (T-0559 is BLOCKED on HQ-0100 and is not this task's concern); no item of `PROCESS/RuntimeAcceptance.md` has `상태` `실패` (RA-0056 is `미확인`); no P2-15 preparation is pending. P3-12 comes before P3-16 (D31 ①). If any of this has changed when the task starts, report it in `## Result` and stop before writing.

**The brake** (DRIVER §6 D31 ②) does not apply: this is a PLAN item (P3-12) and ADR-0206 decision 7 names this slice.

**The P2-15 path is not touched.** ADR-0193 decision 5 and ADR-0206 decision 2 keep `hilclaw/model_forward.c`, `hilclaw/model_forward_run.py` and `hilclaw/model_check.py` unchanged while the owner's P2-15 check (RA-0056) is open. The timed runs are runs of the **graph program**, and its **untimed form keeps its input file and its report byte for byte** (the P3-4 equality with `model_forward.c`'s report, RA-0070).

**Size.** ~300 LOC of non-test code in three files (D30 recommendation ≤ 600). Slice 2 (the container path with the waiter's memory figure, T-0571) is a separate task because the two together exceed the recommendation and the ADR draws the boundary between them.

## Required Reading

- `PROCESS/DRIVER.md` **§3-5 and §5**: branch `claude/T-0570-<slug>`, the `Task: T-0570` trailer and PR-body last line, size (D30), file cap, storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0570/`, removed at the end), the test rules (D12) and list assertions (D21). §6 D29 (real toolchain on this machine: host clang).
- `ARCHITECTURE/decisions/ADR-0206-od33-llm-level-evaluation.md`: Status, decision 2 ("Which program is timed"), **decision 3** (clock, readings, intervals, `"last"`, metrics, repetitions, lengths), decision 5 (what ends an evaluation — the failures a timed run can have), **decision 7** (slice 1's row and "Tests"), A-13 reading, Consequences ("Less exact, not edited": the `model_graph.c` header comment).
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md` decision 5 (the graph program, its input file and report, the rule on the P2-15 files).
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md` decision 4 (`resolution` reported as ns from `clock_getres`).
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md` decision 7 and `ADR-0176-od31-model-level-reference-and-comparison.md` decision 5 (the report and the greedy generation mode).
- `ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md` decision 7 (the host path is for kernels the caller wrote).
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md` decisions 2 and 3 (what stays outside an interval; keeping every sample in order) — for analogy only, as ADR-0206 decision 3 applies them.
- Code: `hilclaw/model_graph.c` (whole header comment and the generation loop), `hilclaw/model_graph.py` (`encode`, `_parts`, `parse_report`, `_report` use, `resolve` with `lm_head_rows`), `hilclaw/model_graph_execute.py` (whole), `hilclaw/model_build.py` (`build_graph_program`), `hilclaw/local_run.py` (`run`), `hilclaw/model_forward_run.py` (`ForwardProgramResult`, `ForwardReport` — read only).
- Tests: `tests/test_model_graph.py`, `tests/test_model_graph_program.py` (real-clang builds with fixture kernels, the byte-equal Llama check), `tests/test_model_graph_execute.py`.

## Acceptance Criteria

1. **Timed form of `model_graph.c`** (ADR-0206 decision 3), selected **by the input file** (for example a new value of the `mode` word for "timed generation"; the executor chooses the encoding and states it in the header comment). It exists only in the generation mode; the plan it runs is resolved with `lm_head_rows` `"last"` (the encoder refuses a timed request for another `lm_head_rows` or for the given-sequence mode, as an input error — status 5 in the program, `ValueError` in Python).
   - Clock `CLOCK_MONOTONIC` via `clock_gettime`; `clock_getres` of the same clock reported in ns as `resolution`. No new dependency beyond POSIX.1-2008.
   - Readings: `t_s` once, after the input file is read, the libraries are loaded and every buffer is allocated and initialised, immediately before the first step of pass 0; `t_p` after the token selection of pass p, p = 0 … G − 1.
   - The timed report holds **no logits rows**: the S prompt ids, the G selected ids, the G + 1 readings, `resolution`, then the end mark, **all written after `t_{G−1}`**. The layout (integer width, order) is this task's choice, stated in the header comment.
   - A failed `clock_gettime` or `clock_getres` ends the program with a status of its own (or an existing runtime status), documented in the header comment, with no report.
   - The header comment's "It reads no clock" sentence is corrected to describe the timed form; the rest of the header stays accurate.
2. **Untimed form unchanged byte for byte**: for every existing call, the input file `hilclaw.model_graph.encode` builds and the report `model_graph.c` writes are identical to before this task. The existing tests of `tests/test_model_graph.py`, `tests/test_model_graph_program.py` (including the Llama byte-equal check against `model_forward.c`) and `tests/test_model_graph_execute.py` pass unchanged, except list assertions D21 allows (foreseen: a pinned set of public names of `hilclaw.model_graph` or `hilclaw.model_graph_execute`, if one exists; name each one changed in the PR body).
3. **`hilclaw.model_graph`**: a public way to encode the timed form (a keyword of `encode` or a new function — executor's choice, documented) and a public reader of a complete timed report for a plan, returning the prompt ids, the G selected ids, the G + 1 readings (or the G intervals `d_0 … d_{G−1}` in ns) and `resolution`, or `None` for an incomplete or malformed report, as `parse_report` does. The reader reports a report whose readings do not increase strictly — an interval of 0 ns or less — as not usable (ADR-0206 decision 5: an interval of 0 ns is a failure of the run); the executor chooses how that is told (e.g. `None` with a reason, or a distinct result) and documents it.
4. **`hilclaw.model_graph_execute`** (host path, ADR-0182 decision 7 — for kernels the caller wrote): a timed execution that resolves, checks and builds as `execute` does, then runs the timed program **R times, each a new process with the same input file** (ADR-0206 decision 3), keeping every run's intervals in order, with no warm-up run. R is an `int`, odd and ≥ 1; anything else is refused before anything is built (`TypeError`/`ValueError` with `parameter`). The first run that times out, ends with a status other than 0, leaves no complete timed report or gives a non-increasing reading ends the execution as **run failed** with that run's result and no figures (ADR-0206 decision 5). It computes no summary and makes no token tie (slice 4's), and has no default for R, G, the prompt or any time limit. `execute`'s behaviour and result are unchanged.
5. **Tests** (D12: happy, error, branch, negative; every public function touched; real clang on this machine, skipped only where the existing graph-program tests skip):
   - the timed Llama form (fixture kernels, synthetic weights) gives the same S prompt ids and G selected ids as the untimed generation at `lm_head_rows` `"last"` for the same input; readings increase strictly; `resolution` ≥ 0; no logits bytes in the report;
   - the untimed input bytes and report are unchanged (an explicit byte comparison for at least one plan);
   - R = 1 and R = 3 give 1 and 3 runs of G intervals each; R = 0, R = 2, R = -1, `True` and a non-`int` are refused before any build;
   - a timed request in the given-sequence mode or at `"all"` is refused; a truncated or overlong timed report reads as `None`; a report with a non-increasing reading is not usable; a run that ends with a status other than 0 (e.g. a fixture kernel that exits) ends the timed execution as run failed.
   - Coverage of `hilclaw/` stays ≥ 80 % line and function.
6. **Not touched**: `hilclaw/model_forward.c`, `hilclaw/model_forward_run.py`, `hilclaw/model_check.py`, `hilclaw/model_forward_container.py`, `hilclaw/standin_container.py`, any data-plane file or schema, any ADR file. No record writer, no summary, no command.
7. **Process**: code mode — dev-item-address steps, Draft PR (title contains `T-0570`, body's last line `Task: T-0570`), context-isolated review to Approve (≤ 14 rounds, D28), CI green, squash-merge with `--body`, branch deleted. `## Result` states the languages (C for the program, Python for the host side) with one-line reasons, the clang version used, and the timed report layout chosen (one line, for T-0571).

## Out of Scope

- The container path, the waiter and the memory figure (slice 2, T-0571); the record, its writer and validator (slice 3, waits on HQ-0102); the command `hilclaw.llm_eval` and the token tie (slice 4, waits on HQ-0102 and HQ-0103).
- Any change to `model_forward.c` or `model_check` (ADR-0193 decision 5); any vendor target; GPU or NPU memory.
- Starting `claude` in any form (D16); no test run (D25).

## Follow-ups

## Result

PR #383 squash-merged as fb90552e (branch deleted); 2 review rounds (R1 Request changes: a missing test of execute_timed's timed invalid-input branch, plus three nits — fixed; R2 Approve with one comment-wrap nit, fixed afterwards as a comment-only change under D20). CI green on the final head 1645e780 (C gate, Python 3.11/3.14, coverage, test presence, shellcheck). Not BLOCKED.

Order check (D27 ①) at start (main d15a659a): no open PR, no open `nightly-failure` issue, no `실패` item in PROCESS/RuntimeAcceptance.md, no P2-15 preparation pending.

**Languages.** C for `hilclaw/model_graph.c`: the program is already C and `clock_gettime`/`clock_getres` of POSIX.1-2008 add no dependency. Python for the host side (`model_graph.py`, `model_graph_execute.py`), like the executor's other host modules.

**What landed.**
- `model_graph.c`: mode word 2 = timed generation (passes and greedy selection like mode 1, no logits rows). `clock_getres(CLOCK_MONOTONIC)`; `t_s` read immediately before the first step of pass 0 (after loading libraries, reading input, filling every buffer incl. the readings buffer); `t_p` after the token selection of pass p. A timed pass with other than one output row is status 5; a failed `clock_gettime`/`clock_getres`, or a time with negative `tv_sec` or too large for uint64 ns, is new status 8 with no report.
- `model_graph.py`: `encode(..., timed=False)` (TypeError for non-bool; ValueError for timed with `given` not None or a plan whose passes do not each report one row; `parameter` "timed"); `TimedReport` record (prompt, tokens, readings, intervals, resolution, increasing) and `parse_timed_report(report, plan)` (None for wrong length/end mark; `increasing` False for an interval ≤ 0).
- `model_graph_execute.py`: `execute_timed(...)` (host path; no `given`, no `lm_head_rows`, resolves at "last"); `repetitions` R odd int ≥ 1 checked before anything is read or built; R runs, each a new process with the same input file, no warm-up. The first run that times out, exits non-zero, leaves no complete timed report or gives non-increasing readings ends the execution: `runs` None, `failed` holds that `TimedRun` with `TimedRunFailed` (TIMEOUT, EXIT_STATUS, REPORT_FORM, NOT_INCREASING). No summary or token tie, no defaults. `execute` unchanged (build/run steps split into shared helpers).
- Not touched: `model_forward.c`, `model_forward_run.py`, `model_check.py`, `model_forward_container.py`, `standin_container.py`, any data-plane file, schema or ADR.

**Timed report layout (for T-0571).** uint64 host byte order: S prompt ids, G selected ids, G+1 readings `t_s, t_0 … t_(G-1)` (CLOCK_MONOTONIC ns), resolution (ns), then `end\n` — `8·(S+2G+2)+4` bytes, written as a whole after `t_(G-1)`; mode word (header word 5) = 2.

**Existing tests (D21).** No existing assertion changed; only the import line of `tests/test_model_graph_execute.py` gained the new names. `test_model_graph_program.py::test_header_refusals[5-2-out of range]` now hits the timed-pass rule (still status 5, "out of range"); passes unchanged; stated in the PR body.

**Untimed form unchanged.** SHA-256 of `encode`'s header/tables/steps/tokens part pinned from origin/main for all four lm_head_rows × mode combinations; the byte-equal Llama check against `model_forward.c` passes unchanged; the untimed report is unchanged under a failing clock (LD_PRELOAD shim).

**Verification.** Ubuntu clang 14.0.0-1ubuntu1.1 under WSL2. Full suite (Python 3.12.13) under `coverage run --branch`: 42178 passed, 118 skipped. `model_graph.py`, `model_graph_execute.py` 100 % line and branch; package 99 %. After fixes: graph and build test files 471 passed; ruff check/format clean. Real-clang timed Llama (fixture kernels, synthetic weights) equals the untimed generation for three bindings and (S,G) ∈ {(3,3),(5,4),(2,1)} with strictly increasing readings; clock shims give status 8; frozen clock gives `increasing` False; `execute_timed` R=1/R=3 equals the untimed tokens. Size about 330 non-test lines in 3 files. No `claude`, Docker or model file used (D16); no test run (D25).

**Follow-ups.** None. **Runtime acceptance items (D22).** None (slice 2/T-0571 and slice 4 carry theirs).

**Storage.** `%TMP%/hilclaw-driver/T-0570/` and the WSL coverage data were removed with `rm -r`; no images, no installs.
