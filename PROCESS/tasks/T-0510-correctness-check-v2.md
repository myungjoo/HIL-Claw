---
id: T-0510
title: Land ADR-0183 code slice 2 — correctness.check writes v2 results under correctness_check_sim_v2 / correctness_check_board_v2, step from point alone, fp32 gemm and the bf16 checks migrated, check-line readers on the new values
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, NFR-1, OD-8, OD-18, OD-31, HQ-0078, "PLAN P2-11", "PLAN P2-14"]
dependsOn: [T-0509]
touchesFiles:
  - hilclaw/check_identity.py
  - hilclaw/check_tool.py
  - hilclaw/check_admission.py
  - hilclaw/check_judging.py
  - hilclaw/check_answer.py
  - hilclaw/check_result.py
  - hilclaw/layout.py
  - hilclaw/check_standing.py
  - hilclaw/checks_tool.py
  - hilclaw/spec_feedback.py
  - tests/
estimatedSize: {loc: 450, files: 10}   # ADR-0183 decision 9 item 2: "About 450 lines, 10 to 12 files, mostly removals"; cut to 10 here (verdicts_tool.py moves to T-0511, hw_tool.py stays untouched); tests excluded from the cap
hq: []
---
## Why

**State.** ADR-0183 (T-0508, `main` `8b6c7318`) records the owner's answer to HQ-0078: one result format v2 for `correctness.check`, `sim.run` and `board.run`; the six `step` values of today retired. Its decision 9 **item 2** is this task: "**`correctness.check` v2** — `hilclaw/check_identity.py` (the two v2 values, the `step` from `point`; the four retired constants and `step_of_read` removed), `hilclaw/check_tool.py` (the `step` from `point`), `hilclaw/check_admission.py` (the rule of a `dtype` changed since ⓢ removed), `hilclaw/check_judging.py` and `hilclaw/check_answer.py` (every result through the v2 builder, fp32 `gemm` included), `hilclaw/check_result.py` (the builders of today removed), `hilclaw/layout.py` (the two check values in `BUILD_LOG_STEPS`, the four retired check values out), and the check-line readers `hilclaw/check_standing.py` (one value per point), `hilclaw/checks_tool.py`, `hilclaw/spec_feedback.py` and the check part of `hilclaw/verdicts_tool.py` (the values and their docstrings). About 450 lines, 10 to 12 files, mostly removals; `hilclaw/hw_tool.py` may also change if `read_stepped_tool_function` loses its last user. The readers land with the writer because the constants they read change with it. If the slice exceeds the cap, the removal of the builders of today (in `check_result.py`) and any clean-up of `hw_tool.py` may follow in a third task."

**Cut to the cap (DRIVER §5: ≤ 10 files).** The docstring edits of the check part of `hilclaw/verdicts_tool.py` move to T-0511 (which edits that file for the run part anyway; `verdicts_tool` reads the check values through `check_standing.STEPS_OF`, so its code keeps working). `hilclaw/hw_tool.py` is not touched: `read_stepped_tool_function` (and `journaled_tool.read_stepped_function` under it) lose their last caller here but stay, covered by their own tests; their removal is a refactoring set aside under D18 (a deferred line returned to the driver).

**Why P2-14 needs it (PLAN checklist).** ADR-0181's bf16 timing slices, which make the bf16 entries `timed` so the instance start admits them for P2-14, stack on the v2 code of both tools (owner order, HQ-0078). P2-11 / P2-14 are checklist items; D18 does not apply. T-0509 (item 1, the builder) is planned in the same batch and lands first; T-0511 (item 3) follows.

**RuntimeAcceptance.** No `실패` item as of `main` `ac8e143c`. ADR-0183 Consequences: none.

**D16.** Tests use the mock backend and the existing stubs (and `clang`-backed `cpu_standin` tests where the existing ones run them); no `claude`, no real Docker daemon, no board.

## Required Reading

- `PROCESS/DRIVER.md` §3-5, §5 (naming `claude/T-0510-<slug>`, `Task: T-0510` trailer in commits and as the last line of the PR body, size cap, D12, D21), §8 (D22).
- `CLAUDE.md` (rules; A-13 code mode, BLOCKED reasons; test rules; language policy; comment minimisation).
- `PROCESS/tasks/T-0509-v2-check-result-builder.md` `## Result` — the names and signatures of the v2 builder and of the per-operand mapping, and where the sdpa sum is formed.
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md` — decisions 2 (lines 44-57), 3 (59-80), 5 (107-119), 6 (121-125), 7 (127-130), 8 (132-150), 9 (152-161).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md` decision 3 (lines 62-80) — what is replaced (the bf16 values, the choice from the read of ⓢ, the dtype-mismatch rule).
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md` decision 3; `ADR-0041-od18-correctness-check-dimensions.md` decision 8 (order of the answers of ④); `ADR-0100-od8-tool-result-change.md` decisions 3-5; `ADR-0178-od23-bf16-check-lines-read.md` decisions 1-4 (the two-value reading being replaced).
- Code: `hilclaw/check_identity.py` (235 lines), `hilclaw/check_tool.py` (224), `hilclaw/check_admission.py` (300; `admit`, `admit_for_step`, `_admit` around 190-300), `hilclaw/check_judging.py` (278), `hilclaw/check_answer.py` (151), `hilclaw/check_result.py` (after T-0509), `hilclaw/layout.py` lines 50-62 and 170-200 (`BUILD_LOG_STEPS`, `build_log_file`), `hilclaw/check_standing.py` (201; `STEPS_OF` at ~90), `hilclaw/checks_tool.py` lines 1-40 and 290-346, `hilclaw/spec_feedback.py` lines 1-60 and 130-190; `hilclaw/hw_tool.py` lines 248-330 (`stepped_tool_function`, which `run_tool.py` already uses — read only); `hilclaw/check_operation.py` lines 180-195 (`_result`, read only).
- Tests to adapt: `tests/test_check_identity.py` (lines ~224, 493-510, ~565), `tests/test_check_result.py` (~586), `tests/test_check_judging.py` (~637), `tests/test_check_answer.py` (~439), `tests/test_check_admission.py`, `tests/test_check_tool.py`, `tests/test_layout.py` (~617), `tests/test_check_standing.py` (~436-470), `tests/test_checks_tool.py`, `tests/test_spec_feedback.py`, `tests/test_check_build_log_file.py`, `tests/test_check_operation.py`, `tests/test_mock_check.py`, `tests/test_backend_conformance.py`, `tests/test_first_run_end_to_end.py`, `tests/test_verdicts_tool.py`, `tests/test_spec_tool.py`, `tests/test_standin_answer.py` (search `tests/` for the four retired check values and `cache_differs`).

## Acceptance Criteria

1. **Step values** (ADR-0183 decision 2). `hilclaw.check_identity` binds exactly the two values `correctness_check_sim_v2` (point `sim`) and `correctness_check_board_v2` (point `board`); `STEPS` is those two; `step_of(request)` gives the value from `point` alone. The constants of the four retired values (`correctness_check_sim`, `correctness_check_board`, `correctness_check_bf16_sim`, `correctness_check_bf16_board`), `BF16_STEPS` and `step_of_read` are removed. No string of a retired check value remains in `hilclaw/` code (docstrings may name them only as retired, citing ADR-0183).
2. **The tool path** (decision 2, "How a call chooses its value"). `hilclaw.check_tool` builds the tool over `hw_tool.stepped_tool_function` (the `step` from the request), no longer over `read_stepped_tool_function`; the build-log file is named with the call's `step` (decision 7, e.g. `build-log-correctness_check_sim_v2-01.txt`). `hilclaw.check_admission` drops `admit_for_step` / the `bf16_step` rule: a record covered by `contract_table.check_covers` is admitted whatever its `dtype`, and the answers of ④ keep the order of ADR-0041 decision 8 (`op_signature_not_stated`, `op_signature_not_covered`, …), unchanged otherwise.
3. **Every result is v2** (decisions 3 and 6). `check_judging` and `check_answer` produce every result — fp32 `gemm` and the six bf16 kinds, completed and broken, from the `cpu_standin` report and from an answer of either backend — through T-0509's v2 builder, with `contract_key` of the covering entry; a broken result holds `contract_key`, `shape`, `draws`, `tolerance`, `condition` and no `counts`; tool failures are unchanged in kind and form and append the same lines as today. `check_operation.py` is changed only if the result path cannot be switched without it — if it must change, keep the 10-file cap by leaving the builders of today in `check_result.py` (criterion 4) and say so in Follow-ups.
4. **Today's builders removed.** `check_result.completed`, `broken`, `bf16_completed`, `bf16_broken` (and the existing `check_judging` / `check_answer` functions that only served them) are removed when nothing calls them; `PASS`, `FAIL`, `BROKEN`, `CONDITIONS` stay (other modules import them). Module docstrings describe v2 only.
5. **Build-log names** (decision 7). `hilclaw.layout.BUILD_LOG_STEPS` holds the two check v2 values and the two run values of today (`sim_run_timing`, `board_run_timing` — T-0511 replaces those), and none of the four retired check values; `build_log_file` refuses a retired check value as it refuses any value not in the list; its docstring names the values it admits.
6. **Check-line readers** (decision 8 rows `checks.read`, hard floor, `feedback.attempts`). `hilclaw.check_standing.STEPS_OF` maps each point to its one v2 value (the form — a one-item tuple or a single value — is this slice's; every reader follows it); `checks.read`, the hard floor and `spec_feedback` read the lines of the point's one v2 value only; a line under a retired value is neither read nor refused (decision 8 first bullet). Request, result and kinds of those readers are unchanged. The docstrings of `check_standing.py`, `checks_tool.py` and `spec_feedback.py` no longer describe two values per point (ADR-0178) but the one v2 value (ADR-0183 decision 8). `hilclaw/verdicts_tool.py` code keeps working through `STEPS_OF`; its docstrings are T-0511's.
7. **Untouched** (cap): `hilclaw/hw_tool.py`, `hilclaw/journaled_tool.py` (their read-stepped builders keep their own tests), `hilclaw/verdicts_tool.py`, every run-tool module, the operations of `cpu_standin` and the mock (the report and answer forms do not change), `orchestration/` (ADR-0183 decision 8: no prompt change).
8. **Tests** (D12: happy, error, branch, negative; every public function of the touched modules covered; coverage ≥ 80 % line and function):
   - end-to-end through the registered tool on the mock **and** `cpu_standin` (where the existing tests run it): an fp32 `gemm` check and at least one bf16 check (and an `sdpa_kv_cache` check with per-allocation `differs`) append `step_started` / `step_ended` lines under `correctness_check_sim_v2` / `correctness_check_board_v2` with a v2 `result`; a broken build gives a v2 broken result and the build log named after the v2 value;
   - an `op_signature` of a covered bf16 kind is admitted at either point without any read choosing the value; the identity of a call under the v2 value does not take an identity open under a retired value as open (ADR-0100 decision 5) — a log seeded with a retired-value line is passed over;
   - readers: `checks.read`, the hard floor and `feedback.attempts` on logs with v2 lines (pass, fail, broken; compile failure → `build-log-correctness_check_*_v2-<EE>.txt`), and on a log holding only retired-value lines (neither read nor refused);
   - negative: an unknown `point`, an `op_signature` not covered, `build_log_file` with a retired value.
9. **Existing tests.** Tests that assert a retired check value, `cache_differs`, today's check result members, or the two-value reading are rewritten to v2 — that is this task's change. Beyond that, list assertions touched by removed or changed names may be edited (D21); expected: `tests/test_check_identity.py` (`STEPS == …` ~224, public names ~493-510, `BF16_STEPS == …` ~565), `tests/test_check_result.py::test_public_names_of_the_module`, `tests/test_check_judging.py::test_public_names_of_the_module_and_no_default`, `tests/test_check_answer.py::test_public_names_of_the_module_and_no_default`, the public-name assertion of `tests/test_check_admission.py`, `tests/test_layout.py` (`BUILD_LOG_STEPS == …` ~617-618 and `test_public_name_lists_match_the_adr` if it pins the values), `tests/test_check_standing.py` (`test_public_names`, `STEPS_OF == …` ~468). No other existing assertion changes. List every edited assertion in the PR body.
10. **No record edits.** No file under `ARCHITECTURE/` changes (StepValues already says `not used` / `defined`). Sentences of records that become less exact beyond ADR-0183's Consequences list are named in Result.
11. **Result** records the language (Python) and reason, the files changed (≤ 10 non-test), whether `check_operation.py` changed and whether today's builders were removed, the edited list assertions, any runtime acceptance item (none expected), and the next candidate (T-0511).

## Out of Scope

- `sim.run` / `board.run`, `timings.compare`, `timing_finding` and `verdicts_tool.py` (T-0511).
- Removing `hw_tool.read_stepped_tool_function` / `journaled_tool.read_stepped_function` (deferred, D18).
- ADR-0181's bf16 timing slices; `timed` flags.
- Any edit of `ARCHITECTURE/`; any tolerance, seed, number of draws or other owner-only value.
- Starting `claude`, a real Docker daemon, a board, real weights or an API key (D16).

## Follow-ups

## Result
