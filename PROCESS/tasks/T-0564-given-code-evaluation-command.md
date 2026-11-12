---
id: T-0564
title: Land ADR-0200 slice 4 for PLAN P3-11 — the command `python -m hilclaw.given_eval` that starts a given-code run with a round budget of 1 and carries round 0 through to `run.commit`, verified with the real clang at `cpu_standin`; and decide under §9 whether round ≥ 1 feedback shows the given attempt `(0, 1, 1)`
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, FR-19, FR-15, FR-17, FR-1, OD-33, OD-28, "PLAN P3-11", HQ-0092, HQ-0097, ADR-0200, ADR-0201]
dependsOn: [T-0563]
touchesFiles:
  - hilclaw/given_eval.py
  - hilclaw/spec_feedback.py
  - ARCHITECTURE/decisions/ADR-0202-od33-given-code-command-and-feedback.md
  - tests/test_given_eval.py
  - tests/test_spec_feedback.py
estimatedSize: {loc: 450, files: 3}
hq: []
---
## Why

**PLAN P3-11** ends with **ADR-0200 slice 4** (decision 8: "The command `hilclaw.given_eval`, verified with the real clang at `cpu_standin` (D29; clang is on the machine and in CI); PLAN P3-11 is checked after it", ~350 LOC, 2–3 files). Slices 1 (T-0560), 2 (T-0561), 3a (T-0562) and 3b (T-0563, with ADR-0201) have landed: a given-code run can be started (`start_instance.start(..., code_file=...)`), its run-level readers and the three evaluation tools read `instance.json` version 3, and `given.place` (`hilclaw/given_attempt.place`) writes `(0, 1, 1)`'s `output/given.c` from the verified blob. This task gives a person the out-of-loop independent evaluation of ADR-0200 decision 4 (b) and decision 5 — a run with a round budget of 1, carried through by a deterministic command with no `claude`. Slice 5 (given code with `compile_settings`) is not needed for P3-11 (ADR-0200 decision 8) and is not planned here.

**Merged in (D20 ③)**: T-0562's and T-0563's `## Result` both left one observation to the planner, recorded in ADR-0201 Boundaries: `spec_feedback` ignores an attempt directory without `spec.json`, so the given attempt `(0, 1, 1)` of a given-code **loop** run never appears in the `feedback.attempts` of a round ≥ 1 spec and can never be `feedback.base` (the incumbent of ADR-0184). P3-11's other use is the round-0 baseline of a loop run (ADR-0200 decision 4 (a), "ADR-0119's baseline rule applies to the given attempt"), and a round-1 coder that cannot see or start from the given code gets nothing from it. Judged under D27 ② as needed by the current PLAN item (P3-11's loop use); if that judgement is wrong it is a small, separable part (D18: "판단이 서지 않으면 task로 만들고 Why에 적는다"). It is not data-plane frame, check or error-path refinement (D31 ②). It is under half the size recommendation and of the same PLAN item, so it is merged with slice 4 rather than made a task of its own.

**Order and brake**: D27 ① — no open PR; nightly failure issue #373 is with T-0559 (BLOCKED on HQ-0100), so no nightly task comes first; `PROCESS/RuntimeAcceptance.md` has no `실패` item. D31 ①: P3-11 precedes P3-15–P3-17. D31 ②: PLAN-item work is the exception to the E4 brake. If the order has changed when the task runs (a new `nightly-failure` issue, a `실패` item, an open PR touching these files), report it in `## Result` and stop before writing code.

**Size**: ~450 LOC (slice 4 ~350, the feedback part ~100, the ADR counted), 3 non-test files; under the recommendation and the file cap.

**Open HQs not to be anticipated or asked**: HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0100. An owner-only part found during the work goes into `## Result` in the DRIVER §8 structure (in Korean), the rest lands, `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0564-<slug>`, the `Task: T-0564` trailer and the PR body's last line, size (D30), tests (D12), list assertions (D21), storage (D29: `${TMPDIR:-/tmp}/hilclaw-driver/T-0564/`, removed with `rm -r` at the end).
  - §3 "BLOCKED 사유" and "승인된 열린 목록"; §6 D27 (①, ②, ⑥), D29 (real toolchain; clang), D31 (② brake); §8; §9 (ADR path, #5 notice).
- `PROCESS/tasks/T-0561-given-code-instance-start.md`, `T-0562-given-code-run-readers.md`, `T-0563-given-code-round-zero-placement.md` (`## Result` of each — especially T-0561's "read-once form" request for this slice, T-0562's real-clang test setup, and T-0563's ADR-0201 finding).
- **`ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md`**: decisions 2, 4 (a) and (b), **5** (the command's steps and order, targets accepted now), 7 (reader table, column "4"), 8 and Boundaries.
- **`ARCHITECTURE/decisions/ADR-0201-od33-given-code-run-fresh-directory.md`** (decisions 1–2; Boundaries: the feedback question).
- Command form: `ADR-0155-od23-first-case-instance-start-command-line.md` (the `new_run` command, its outcomes and report), `ADR-0192-od31-model-check-command.md` decision 1; code `hilclaw/new_run.py`, `hilclaw/model_check.py` (`main(argv, *, source, stdout, stderr)` form), `hilclaw/data_root_source.py`.
- Round 0 as the command must reproduce it: `orchestration/round-manager.md` ("The entry of a turn" steps 0–7, "The round steps" 1–5, "The closing steps of a round"), `ADR-0142-od23-first-case-round-zero-after-coder-call.md`, `ADR-0185-od23-first-case-round-zero-ends-without-standing-attempt.md`, `ADR-0119-od28-first-case-baseline.md`, `ADR-0120-od8-first-state-file.md`, `ADR-0121-od8-run-over-member.md`.
- Code: `hilclaw/start_instance.py` (`start`, its errors), `hilclaw/given_attempt.py` (`place`), `hilclaw/tools.py` (`default_registry`), `hilclaw/fresh_run.py`, `hilclaw/run_file_tools.py` (`state.write`, `instance.read`), `hilclaw/key_store_tool.py`, `hilclaw/check_tool.py`, `hilclaw/run_tool.py`, `hilclaw/round_end_tool.py`, `hilclaw/run_commit.py`, `hilclaw/targets.py` (`instance_start_accelerators`).
- Feedback: `hilclaw/spec_feedback.py` (module docstring; `attempts`, `feedback`, the "attempt directory without `spec.json` is ignored" choice), `hilclaw/spec.py` (the `feedback.attempts` entry and `feedback.base` rules), `ADR-0151-od6-first-case-later-round-spec.md` decisions 2 (d) and 3, `ADR-0184-od20-first-case-incumbent-base.md`, `hilclaw/coder_call.py` (how `feedback.base` reaches the coder), `orchestration/agents/coder-driver.md`.
- Tests: `tests/test_check_tool.py::test_the_given_attempt_of_a_started_run_is_checked_with_the_real_clang` (stub docker with the host clang), `tests/first_run_stubs.py`, `tests/test_new_run.py`, `tests/test_spec_feedback.py`.
- Recording rules, if an ADR changes an OD's status: `ARCHITECTURE/Requirements.md` register "행 형식", `ARCHITECTURE/OpenDecisionProposals.md` header "기록 규칙", `ARCHITECTURE/StandardScenarios.md` §검사 결과 first paragraph.

## Acceptance Criteria

1. **The command** `python -m hilclaw.given_eval <request> <c-file>` (argument form the executor's, in the manner of `new_run`), a module with a `main(argv=None, *, source=..., stdout=None, stderr=None)` entry, registered as no tool, starting no `claude`. It performs ADR-0200 decision 5's steps in order and stops at the first failure: the request (ADR-0155's form); the data root (existing source); the start with the C file and `round_budget` 1 through `start_instance.start(..., code_file=...)`, keeping T-0561's read-once form (the blob, `instance.json` v3 and the `given_code` record are written by the start); the entry of round 0 as the Round-Manager's entry steps make it (first `STATE.json`, ADR-0120/ADR-0201); `key.store`; the placement (`given_attempt.place`); `correctness.check` at `sim`, then at `board`, then `board.run`, through their tool functions or the default registry so that each step is journaled exactly as a live round 0's is; `round.end` of round 0, which ends the run (`run_status` `"over"`); `run.commit`. A given attempt that does not stand at a point follows ADR-0185 (the later evaluation steps are skipped as round 0 skips them) and the run still reaches `round.end` and `run.commit`. A summary goes to standard output (run id, the verdict at each point, the board measurement's median and unit when present); every refusal and failure goes to standard error with a distinct exit status and, once a run exists, its run id. Targets accepted: `targets.instance_start_accelerators` only (today `cpu_standin`, `virtual_npu`); any other is refused before anything is written.
2. **The record**: the command's outcome is the run's own files (ADR-0200 decision 4 (b)); it writes no new data-plane file, member, `step` value or kind. Any choice ADR-0200 leaves to this slice (argument form, exit statuses, how the first `STATE.json` is written, the summary's content) is written in the module docstring and the PR body; if one needs a record, it goes into the ADR of criterion 4.
3. **Feedback of the given attempt** (§9): decide whether `spec_feedback` shows `(0, 1, 1)` of a given-code run in `feedback.attempts` (and so can make it `feedback.base`), and implement the decision if it is yes. Constraints: the existing spec form must admit it unchanged (for example an entry whose `techniques` is `[]`, as `hilclaw/spec.py` allows) — a new member, value or version of `spec.json` is a frame change (D23) and goes into `## Result` as an HQ in the DRIVER §8 structure, with nothing of that part landed; runs without `given_code` and attempts with a `spec.json` behave exactly as before; check how `feedback.base` reaches the coder (`coder_call`) and that a base whose `output/` holds `given.c` works there.
4. **ADR** (`ADR-0202`, name the executor's; next free number at run time) in the ADR-0001 record format, holding the decision of criterion 3 (and any record criterion 2 needs). It cites ADR-0200 and ADR-0201 and closes the ADR-0201 Boundaries question. If it answers part of an OD, the Requirements row and the OpenDecisionProposals section are rewritten in place by their recording rules (one link per new ADR, open parts rewritten in place, no restatement of the record, no dated paragraphs), and StandardScenarios §검사 결과 is re-checked by its first paragraph. Notify #5 under §9. If criterion 3 is answered "no" with no code change, the ADR still records it.
5. **Tests** (D12): the command's happy path at `cpu_standin` **with the real clang** (D29) — start, place, both checks, `board.run`, `round.end` ending the run, `run.commit` in a git data root — in the manner of T-0562's real-clang test (stub docker, host clang; skipped where clang is missing only as the existing clang tests are, failing on CI); a wrong given kernel that fails at `sim` reaching `round.end`/`run.commit` by ADR-0185; error, branch and **negative** cases: a missing or unreadable request, a missing, oversize or unreadable C file, a target outside `instance_start_accelerators`, a `compile_settings` request, `candidates_per_round` ≠ 1, a request already holding `given_code`, no data root, a failure in each later step (by injection where real failure is impractical) with its exit status and run id. The feedback part: a given-code run whose `(0, 1, 1)` verified and was measured appears as decided (entry and `base`), one that failed at `sim` appears with its `failure`, and a run without `given_code` is unchanged. Every public function of touched modules tested; `hilclaw/` line and function coverage ≥ 80%. Existing tests unchanged except list assertions under D21 (foreseen: public-name sets in `tests/test_spec_feedback.py`, and any test pinning the set of `hilclaw` command modules or `python -m` entries); list every such edit in the PR body.
6. **Unchanged**: `new_run`, live loop runs, rounds ≥ 1 of runs without `given_code`, nightly and model paths behave as before; the full test suite passes.
7. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0564`; the §9 notice on #5 for the ADR. Record the language choice (Python) in the commit body. Do not edit `PROCESS/PLAN.md` (the driver checks P3-11 at §3-6) or `PROCESS/RuntimeAcceptance.md`. If the live check of the feedback part by a real coder is worth an item, return it in `## Result` as a runtime acceptance item in the form of `PROCESS/RuntimeAcceptance.md` (D22, in Korean).

## Out of Scope

- ADR-0200 slice 5 (given code with `compile_settings`); round 0 with N > 1 in a given-code run (OD-28).
- Vendor targets, `device_unavailable` (HQ-0097 (a)), HQ-0095, HQ-0096; LLM-level evaluation (P3-12); bundles of several files or other languages (ADR-0200 decision 2).
- A tool comparing figures across runs (ADR-0200 decision 4 (b)); cases and the S6 metric of a given-code run.
- Editing ADR-0155, ADR-0200 decision 5's `cas.put_file` wording or other "less exact" sentences listed by T-0561–T-0563 (they are deferred lines).
- Starting `claude` in any form (D16). No test run (D25) is needed: the command is deterministic and starts no `claude`.

## Follow-ups

- After this task the driver checks PLAN P3-11 (ADR-0200 decision 8); the next planner call goes to P3-15 (D31 ①; P3-12, P3-16 and P3-17 wait on owner answers).

## Result

**Outcome**: DONE — PR #378 (code mode), squash-merged by the executor after the context-isolated reviewer (opus) approved in round 2 (round 1: 2 should-fix, 4 nits; round 2: Approve with 2 nits, both addressed after Approve under D20 — a docstring reflow and the PR body's test-result line). CI green on all gates.

**Order check (D27 ①)**: unchanged at run time — no open PR, #373 still with T-0559, no `실패` item in `PROCESS/RuntimeAcceptance.md`.

**What landed**:
- `hilclaw/given_eval.py` (new): `python -m hilclaw.given_eval <request> <c-file>`, `main(argv=None, *, source=..., stdout=None, stderr=None)`, no tool, no `claude`. Steps: request (new_run's decoding; `target_refused` outside `instance_start_accelerators`, `round_budget_refused` for any value but 1, absent → 1) → data root → `start_instance.start(..., code_file=...)` (read-once) → `run.fresh` + `state.write` (first `STATE.json`) → `key.store` (failure told, goes on, as round step 1) → `given_attempt.place` → `correctness.check` + `checks.read` at `sim`, then `board` → `board.run` → `round.end` → `run.commit`, all through `tools.default_registry`, so journaled as a live round 0. ADR-0185 paths reach `round.end`/`run.commit`. Summary JSON on stdout (`measured` 0 / `not_measured` 10; place, sim, board, timing with median and unit); refusals and failures as JSON lines on stderr with distinct statuses (11–37) and the run id once a run exists.
- `hilclaw/spec_feedback.py` (ADR-0202 decision 1): in a run whose `instance.json` states `given_code`, `(0, 1, 1)` without `spec.json` is found with `techniques` `[]` and is shown, failed and chosen as `feedback.base` by the existing rules; `instance.json` is read only when that directory holds no `spec.json`. `hilclaw/spec_tool.py`: docstring only.
- **ADR-0202** (§9, new): `ARCHITECTURE/decisions/ADR-0202-od33-given-attempt-in-feedback.md` — decision 1 (feedback) and decision 2 (the command's choices); closes the ADR-0201 Boundaries question; registers unchanged (no new OD part answered). §9 notice on #5 (link in the driver record / issue #5, "ADR-0202 accepted").

**Tests**: `tests/test_given_eval.py` (new; the real-clang happy path and wrong kernel at `cpu_standin` through the stub docker of `tests/first_run_stubs.py`, skipped where clang or `os.getuid` is missing and failing on CI via `openmp_clang.need()`; step order, survived failures, stops, all negative cases of criterion 5, streams, status table); added cases in `tests/test_spec_feedback.py`, `tests/test_spec_tool.py` (round 1 of a given-code run names the given attempt and its base, or its failure) and `tests/test_coder_call.py` (base `given.c` copied to the scratch). No existing assertion edited (no D21 list needed a change). Local: Windows ruff + touched tests; WSL Ubuntu (clang 14, libomp 14 extracted user-locally into the task directory) the touched and related files, 809 passed with the real clang; the full suite on the final head, 41960 passed, 71 skipped, 1 failed — `tests/test_standin_openmp.py::test_the_waiter_built_without_openmp_keeps_its_line_for_a_child_with_threads` (WSL reports a child RSS of 16637952 bytes, under the test's 16 MiB floor; a measurement of this machine, not touched by this change, green on CI). `hilclaw/given_eval.py` 98% and `hilclaw/spec_feedback.py` 99% line coverage; CI Coverage gate green.

**Deviation from `touchesFiles`**: `hilclaw/spec_tool.py` (docstring), `tests/test_spec_tool.py`, `tests/test_coder_call.py` (review round 1, criterion 3's coder check). Non-test files: 3 plus the ADR.

**Less exact, not edited**: ADR-0151 decision 3 ⑧ and decision 2 (d) (only attempts with a spec); listed in ADR-0202 Consequences.

**Runtime acceptance item** (for `PROCESS/RuntimeAcceptance.md`; the driver adds it):
- 출처: `T-0564`, ADR-0202 결정 1
- 항목: 실제 `claude`가 도는 given-code 루프 run(`instance.json` 버전 3에 `given_code`, `cpu_standin`, `candidates_per_round` 1, `round_budget` 2 이상)에서 라운드 0의 주어진 시도 `(0, 1, 1)`이 두 지점에서 검증되고 측정된 뒤, 라운드 1의 `spec.write`가 그 시도를 `feedback.attempts`(`techniques` `[]`)와 `feedback.base`로 적고, 실제 코더가 scratch의 `base/given.c`에서 출발해 커널을 쓰는가(코더의 보고나 산출물로 확인).
- 선택지: (a) 오너가 수동 확인 (b) 런타임 자체 점검 코드로 확인 (c) 보류. D16에 따라 드라이버 task로는 닫지 않는다.
- 막히는 것: 없음(T-0564 DONE). 실패로 드러나면 ADR-0202 결정 1(주어진 시도의 feedback 표시)을 다시 정한다.

**HQ**: none.

**Storage**: `%TMP%/hilclaw-driver/T-0564/` (commit and PR drafts, CI watch log) and WSL `/tmp/hilclaw-driver/T-0564/` (libomp 14 extract, two working copies of the tree, logs, coverage data) removed with `rm -r` at the end. No image made, nothing installed; the existing WSL venv `~/.venvs/hilclaw-driver` was used as it was. No `claude` process was started and no test run was made (D25).
