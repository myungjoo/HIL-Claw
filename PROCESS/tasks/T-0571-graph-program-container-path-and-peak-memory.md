---
id: T-0571
title: ADR-0206 slice 2 (PLAN P3-12) — add the graph program's container path (`hilclaw/model_graph_container.py`) and run its timed form R times under the ADR-0145 waiter for the peak-memory figure, leaving every existing container function and `model_check` unchanged
phase: P3
status: DONE
commitMode: code
coversReq: [D27, FR-19, OD-33, "PLAN P3-12", ADR-0206, ADR-0182]
dependsOn: [T-0570]
touchesFiles:
  - hilclaw/model_graph_container.py
  - tests/test_model_graph_container.py
  - hilclaw/model_forward_container.py
  - hilclaw/standin_container.py
estimatedSize: {loc: 350, files: 2}
hq: []
---
## Why

**PLAN P3-12**, **ADR-0206** (`ARCHITECTURE/decisions/ADR-0206-od33-llm-level-evaluation.md`) decision 7, **slice 2**: the graph program's container path (ADR-0182 — the only path allowed for a coder's kernel), with the timed form of slice 1 (T-0570) started by the waiter of ADR-0145 so that each timed run yields its peak-memory figure (ADR-0206 decision 4). It depends on T-0570 (the timed form, its encoder and report reader) and on nothing the owner still has to answer: slices 3 and 4 wait on HQ-0102 and HQ-0103, slice 2 does not (ADR-0206 decision 7).

**Order and brake**: as T-0570's Why (DRIVER §6 D27 ①, D31 ① and ②): a PLAN item, nothing ahead of it at `main` `4aeba6e6`. If an open `nightly-failure` issue or a `실패` item of `PROCESS/RuntimeAcceptance.md` has appeared when this task starts, report it in `## Result` and stop before writing.

**The PLAN "보류" line** "T-0535 follow-up — graph program의 ADR-0182 컨테이너 경로와 실제 가중치 확인(RA-0070)을 coder 커널로 돌리는 진입점(`hilclaw/model_graph_container.py`와 명령 진입점) …" is taken up by this task **for its container-path part only** (the module); the command entry point for RA-0070 is not part of ADR-0206 slice 2 and stays out of scope.

**The P2-15 path is not touched** (ADR-0193 decision 5, ADR-0206 decisions 2 and 7): if this task extends a shared module (`hilclaw/standin_container.py`, `hilclaw/model_forward_container.py`), every existing function keeps its behaviour, so `model_check`'s answer, statuses and verdict and their tests stay as they are. Prefer a new module that reuses the existing ones without editing them; edit a shared module only where reuse is impossible, and say why in the PR body.

## Required Reading

- `PROCESS/DRIVER.md` **§3-5 and §5**: branch `claude/T-0571-<slug>`, `Task: T-0571` trailer and PR-body last line, size (D30), file cap, storage (D29: `${TMPDIR:-/tmp}/hilclaw-driver/T-0571/`; any working image tagged with the task id and removed at the end), test rules (D12), list assertions (D21). §6 D29 (real clang on this machine), D16 and D22 (container facts only a C-7 machine shows are runtime acceptance items).
- `PROCESS/tasks/T-0570-graph-program-timed-form.md` `## Result` (the timed report layout and the public names it added).
- `ARCHITECTURE/decisions/ADR-0206-od33-llm-level-evaluation.md`: decisions 2, 3 (repetitions), **4** (peak memory: what it covers, `null`, failed runs), **5** (failures that end an evaluation), **7** (slice 2's row, "Tests", the slice-2 runtime acceptance item), A-13 reading.
- `ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md` (decisions 2–8: image, copies, builds, the process container, outcomes, decision 6 "no memory figure" — replaced for the timed runs only by ADR-0206 Status).
- `ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md` decision 3 (the waiter W0–W6, its line) and its runtime facts (liii), (liv); `ADR-0052-od13-memory-ceiling-measurement.md` decisions 3 and 4 (KiB × 1024 on Linux; non-positive value → `null`); `ADR-0144-od14-first-case-build-run-container.md` decision 6; `ADR-0186-od14-standin-toolchain-from-image.md`; `ADR-0168-od18-standin-container-situations.md` (runtime statuses 125–127).
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md` decisions 3 and 5.
- Code: `hilclaw/model_forward_container.py` (whole — the pattern to follow), `hilclaw/model_container.py` (header), `hilclaw/standin_container.py` (`run_in_container`), `hilclaw/standin_run.py` (how the waiter is placed, built with the target's `waiter_flags` and started; `WAITER_SOURCE`), `hilclaw/standin_waiter_line.py` (`read`), `hilclaw/standin_answer.py` (header), `hilclaw/harness/timing_waiter.c` (header), `hilclaw/targets.py` (`waiter_flags`), `hilclaw/model_graph_execute.py` and `hilclaw/model_graph.py` after T-0570.
- Tests: `tests/test_model_forward_container.py` (stub container client, real-clang builds), `tests/test_standin_container.py`, `tests/test_standin_waiter_line.py`.

## Acceptance Criteria

1. **`hilclaw/model_graph_container.py`** (new; mirrors `hilclaw/model_forward_container.py` for the graph program, ADR-0182 decisions 2–8): image from `hilclaw.standin_image` (none or refused → the same "container unavailable" outcomes), its own build directory (prefix constant, removed at the end), copies of the kernels and of `model_graph.c`, one build container per kernel and one for the program, then the process container(s) through `hilclaw.standin_container.run_in_container`. It offers:
   - an **untimed run** of the graph program in a container (the deferred T-0535 path), whose report is read by `hilclaw.model_graph.parse_report`;
   - a **timed execution of R runs** (R an odd `int` ≥ 1, refused otherwise before anything is made): the waiter (`timing_waiter.c`) is built in a container with the target's `waiter_flags`, and each timed run is a **new process container** in which the waiter is process 1 and starts the timed graph program as its one child (ADR-0145 decision 3); the timed report is read with T-0570's reader and the waiter's line with `hilclaw.standin_waiter_line.read`; each run gives its G intervals, `resolution` and a memory figure in bytes = KiB × 1024, or `null` when the waiter's value is not a positive integer (ADR-0052 decision 4, ADR-0206 decision 4).
   - The first timed run that fails — a failed build, the time limit, a status other than 0, a runtime status 125–127, a timed report or waiter line of the wrong form or missing, a non-increasing reading — **ends the execution with that failure and no figures** (ADR-0206 decision 5), carried as `model_forward_container`'s outcomes carry theirs (ADR-0182 decision 8).
   - No argument but flags, `environ`, `parent` and `keep_out` has a default (no default R, G, prompt, time limit, image or flag). It computes no summary (median, rates, maximum), makes no token tie, writes no record and starts no command — those are slices 3 and 4.
2. **Existing behaviour unchanged**: every existing function of `hilclaw/standin_container.py`, `hilclaw/model_forward_container.py`, `hilclaw/model_container.py`, `hilclaw/standin_run.py` and `hilclaw/model_graph_execute.py` behaves as before, and their existing tests pass unchanged except list assertions DRIVER §5 D21 allows (foreseen: none; if a pinned set of public names of a module you extend changes, name it in the PR body). `hilclaw/model_forward.c`, `hilclaw/model_forward_run.py`, `hilclaw/model_check.py` are not touched.
3. **Tests** (`tests/test_model_graph_container.py`, D12: happy, error, branch, negative; every public function of the new module): a **stub container client** in place of the runtime's (as `tests/test_model_forward_container.py` does) that runs the commands on the host, while **the timed program and the waiter are built by the real clang** on this machine (ADR-0206 decision 7 "Tests"); where the stub cannot make the waiter process 1 (W0 writes nothing), the test may run the waiter under a PID namespace if the machine allows it without privilege, or else drive the waiter-line branch with a stub-produced line and say so in the PR body — do not install anything. Cases: untimed Llama report equal to the host path's (`model_graph_execute.execute`) for the same input; R = 1 and R = 3 timed runs with R memory entries; a waiter value that is not positive → `null`; a missing waiter line, a runtime status 125–127, a timeout, a non-zero status, a failed kernel build, no image named and a refused image each give their outcome with no figures; R even/zero/non-`int` refused before anything is made; the build directory is removed in every case. Coverage of `hilclaw/` stays ≥ 80 % line and function.
4. **Runtime acceptance item** in `## Result` (ADR-0206 decision 7; DRIVER D22 — the driver adds it to `PROCESS/RuntimeAcceptance.md`): on a machine of C-7 with the container runtime, the timed graph program started by the waiter in a container of ADR-0144 gives a complete timed report followed by the waiter's line, and the report's tokens equal those of the untimed program for the same input (ADR-0145 (liii) and (liv) for this process). Write it in Korean in the file's item style, naming this task and its PR.
5. **Process**: code mode — dev-item-address steps, Draft PR (title contains `T-0571`, body's last line `Task: T-0571`), context-isolated review to Approve (≤ 14 rounds, D28), CI green, squash-merge with `--body`, branch deleted. `## Result` states the language (Python) with a one-line reason and the clang version used.

## Out of Scope

- The record of ADR-0206 decision 6, its writer and validator (slice 3 — HQ-0102); the command `hilclaw.llm_eval`, the summaries, the binding derivations and the token tie (slice 4 — HQ-0102, HQ-0103); PLAN P3-12's check.
- A command entry point for RA-0070 (the rest of the T-0535 deferred line); real weights; vendor targets; GPU or NPU memory.
- Any change to `model_forward.c`, `model_forward_run.py`, `model_check.py`; any data-plane file or schema; any ADR file.
- Starting `claude` in any form (D16); no test run (D25); no real Docker run is required (the stub client covers CI; real-container facts are the runtime acceptance item above).

## Follow-ups

## Result

PR #384 (squash-merged; branch deleted); 1 review round (Approve with two test-only nits, fixed afterwards under D20: a test renamed, a one-line comment on the `user` fixture's `tmp_path` dependency). Not BLOCKED.

Order check (D27 ①) at start (main a86d2bca): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`.

**Language.** Python for `hilclaw/model_graph_container.py`, like the executor's other host-side container modules; the program and the waiter stay the existing C sources. Clang used: Ubuntu clang 14.0.0-1ubuntu1.1 (WSL2).

**What landed.** New module only; no existing module edited (it imports `model_forward_container`'s outcome types and private helpers and `model_graph_execute._prepare`). `execute(...)` runs the untimed graph program in containers (report by `model_graph.parse_report`). `execute_timed(..., repetitions, waiter_flags, ...)` refuses R that is not an odd `int` >= 1 before the graph is read, builds the waiter in its own container with the caller's `waiter_flags` (the target's), and runs R new process containers `/build/waiter /build/model_graph /build/input.bin <libs>`. Each run gives a `TimedReport` and `memory_bytes` (KiB x 1024, or `None` for a non-positive value or the none line). The first failed run ends the execution with no figures: `TimedRunFailed.TIMEOUT`, `EXIT_STATUS` (any non-zero status, 125-127 included as ADR-0168 decision 4 reads a timing process), `WAITER_LINE` (status 0, no line), `REPORT_FORM`, `NOT_INCREASING`. Build-container 125-127, no image, a refused image and no client are `model_forward_container.Unavailable`. A failed waiter build is `BuildFailed(None, ...)` with the waiter's `output`. Size: about 540 lines in the new module (docstrings included), 1 code file plus 1 test file.

**Existing tests (D21).** None changed.

**Verification.** `tests/test_model_graph_container.py` has 83 tests. A stub client covers every outcome. With real clang, the untimed Llama report equals `model_graph_execute.execute`'s (given and generation modes). The timed R = 1 and R = 3 runs ran under the real waiter as PID 1 in an unprivileged PID namespace (`unshare --user --pid --fork --mount-proc --kill-child`, as `tests/harness/test_timing_waiter.py`): tokens equal the untimed generation's, `memory_bytes` > 0 and a multiple of 1024. When no namespace can be made, the test falls back to a stub-produced waiter line. A real waiter outside PID 1 gives status 3 and `EXIT_STATUS`. Full suite under `coverage run --branch` (Python 3.12.13, from a non-git copy of the tree): 42260 passed, 119 skipped, 1 failed — `test_remote_eval.py::test_snapshot_holds_the_package_and_no_git_directory`, which needs `git archive` of a checkout and fails only because the copy had no `.git`; package 99 %, new module 100 % line and branch. ruff check/format clean. No `claude`, Docker or model file used (D16); no test run (D25).

**Runtime acceptance item (D22)** — for `PROCESS/RuntimeAcceptance.md`:

> PLAN P3-12 / ADR-0206 결정 7 (slice 2). 컨테이너 런타임이 있는 C-7의 머신에서, ADR-0144의 컨테이너 안에서 waiter(ADR-0145)가 시작한 timed graph program(`hilclaw.model_graph_container.execute_timed`)이 완전한 timed 보고를 내고 그 뒤에 waiter의 줄이 오는가, 그리고 그 보고의 token이 같은 입력에 대한 untimed program(`hilclaw.model_graph_container.execute`)의 token과 같은가(이 프로세스에 대한 ADR-0145 (liii)·(liv)의 컨테이너 사실). 실패로 드러나면 ADR-0206 결정 4(waiter를 통한 peak memory)를 다시 본다. T-0571(PR #384) 착지 뒤 확인 가능.

**Follow-ups.** None.

**Storage.** `%TMP%/hilclaw-driver/T-0571/` and the WSL `/tmp/hilclaw-driver/T-0571/` (repo copy, pytest base, coverage data) removed with `rm -r`; no images, no installs.
