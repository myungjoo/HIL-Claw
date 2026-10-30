---
id: T-0500
title: Write the ADR on how checks.read, verdicts.write and the round >= 1 spec feedback find the lines of a bf16 correctness.check, and build it (ADR-0177 slice 2, readers)
phase: P2
status: DONE
commitMode: code
coversReq: [C-6, FR-9, FR-17, OD-18, OD-23, OD-6, OD-31, "PLAN P2-11", "PLAN P2-14"]
dependsOn: [T-0498, T-0499]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0178-od23-bf16-check-lines-read.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/checks_tool.py
  - hilclaw/verdicts_tool.py
  - hilclaw/spec_feedback.py
  - hilclaw/check_standing.py
  - tests/test_checks_tool.py
  - tests/test_verdicts_tool.py
  - tests/test_spec_feedback.py
  - tests/test_check_standing.py
estimatedSize: {loc: 360, files: 8}   # non-test: ADR ~170 lines, checks_tool ~50, verdicts_tool ~40, spec_feedback ~40, check_standing ~10, registers ~10. The ADR file name and number are a suggestion (next free number). Tests are outside the cap (DRIVER §5, D4/D20).
hq: []
---
## Why

**State.** PLAN P2-14 (Llama 3.2 1B end-to-end, the D18 goal) needs every P2-11 operation's kernel to come from an instance. ADR-0177 (T-0496, `main` `31ebd97f`) decision 5 item 2 makes `correctness.check` serve the bf16 kinds, and names among its parts "the readers of a check result (`checks.read`, `hilclaw.spec_feedback`) accepting it". T-0498 and T-0499 build the check of bf16 `gemm`, `rmsnorm`, `elementwise_add` and `swiglu` and put its lines in `events.ndjson` under the two new values `correctness_check_bf16_sim` / `correctness_check_bf16_board` (ADR-0177 decision 3). The `checked` flags stay off until a later task adds the `cpu_standin` operation; this task makes the readers ready before that.

**Why an ADR.** The three readers find a check's lines by mapping the request's `point` to one `step` value and read only `events.ndjson`: `checks.read` (`hilclaw/checks_tool.py`, ADR-0131 decision 3; `STEP_OF`), `verdicts.write` (`hilclaw/verdicts_tool.py`, which looks up the board check through `checks_tool.STEP_OF` for ADR-0131 decision 5 and the ADR-0140 comparison) and `hilclaw/spec_feedback.py` (ADR-0151 decision 3, which asks `check_standing.standing` under `STEP_SIM` / `STEP_BOARD`). ADR-0177 says how the *tool* chooses a value (from the read of ⓢ) but no record says how a *reader* finds the lines of a bf16 check. That is a design-level choice (OD-23 / OD-18 / OD-6 parts, driver-closable under DRIVER §9), written with its code in one task (DRIVER §6 "task 단위" ①, D20).

**PLAN order and D18.** P2-11 and P2-14 are PLAN checklist items; D18 does not apply. No RuntimeAcceptance `실패` item exists as of `main` `1b6dc8ee`.

**D16.** Everything is verified with tests in this repository; nothing starts `claude`, needs a board, a container runtime or real Llama weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0500-<slug>`, `Task: T-0500` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items, D22), §9 (OD closing: ADR + reviewer Approve + owner notice on #5).
- `CLAUDE.md` (rules; "미결은 발명하지 않는다"; "세션 진입 점검"; A-13 BLOCKED reasons, in particular "데이터 plane 스키마 변경"; test rules; language policy).
- `PROCESS/tasks/T-0498-bf16-check-parameters-result-judging-mock.md` and `PROCESS/tasks/T-0499-bf16-check-step-values-and-admission.md` (their Results).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md` decision 3 ("The two values", "Which value a call takes", "What a result does not say") and 5.
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md` decisions 2, 3, 5 and 7; `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md` decisions 2, 3 and 5; `ARCHITECTURE/decisions/ADR-0140-od16-first-case-attempt-comparison.md` (where it names the board check); `ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md` decisions 2 (d) and 3; `ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md` decisions 3–5.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph of the OD register (line ~84) and the rows of the ODs the ADR answers part of (at least OD-23, OD-18, OD-6). `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line ~8) and those sections. `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과 and rows S0 and S1.
- Code: `hilclaw/checks_tool.py`, `hilclaw/verdicts_tool.py`, `hilclaw/spec_feedback.py`, `hilclaw/check_standing.py`, `hilclaw/check_identity.py` (after T-0499), `hilclaw/timings_tool.py` (its own `STEP_OF`; read only).
- Tests: the test files of the four touched modules.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): before editing `ARCHITECTURE/`, check open PRs, Issues #4/#5/#7/#8 and the unresolved `humanQuestions` of `PROCESS/STATE.json` (HQ-0076 concerns P2-10 and is not crossed). Name in the ADR's Status what was checked.
2. **ADR** at `ARCHITECTURE/decisions/ADR-0178-<slug>.md` (next free number), in the form of recent ADRs (Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References). It decides how `checks.read`, `verdicts.write` (its board-check lookup and the ADR-0140 comparison) and `spec_feedback.attempts` find, for a `point`, the lines of a check of an attempt whose checks are under the bf16 values. Weigh at least: (i) read the lines of both values of the point; (ii) read the `op_signature` of `instance.json`, as the tool does in ⓢ. State what each reader answers when lines of both values exist for one attempt (a file changed between two checks, ADR-0177 decision 3), what `check_standing.standing` is asked and how the ADR-0110 floor counts executions then, and whether the request or the result of `checks.read` changes (keep both unchanged unless the ADR shows why not). **A-13 reading**: if the choice changes the form or meaning of a member of a data-plane file, of a line of `events.ndjson`, or of a tool result an agent reads, say so plainly; if it is a "데이터 plane 스키마 변경", stop and return BLOCKED with the question for the owner. Do not decide anything owner-only (#5 A/B, C-6, OD-25, OD-3).
3. **Register edits** follow the recording rules written in those files — not earlier task files: `Requirements.md` rows of the ODs the ADR answers part of, per the register's "행 형식" (one link per new ADR in `**확정분**:`, `**잔여**:` rewritten in place, no restatement of the record, no dated paragraph); `OpenDecisionProposals.md` per its header's "기록 규칙" (one `채택분` line per section the ADR answers, sub-question status rewritten in place); `StandardScenarios.md` § 검사 결과 per its first paragraph (CLAUDE.md "문서 커버리지 재검사"), S0 and S1 at least.
4. **Readers built** as the ADR decides: for a run whose checks are under the bf16 values, `checks.read`, `verdicts.write` and `spec_feedback.attempts` return what they return today for an fp32 run's lines; for fp32 runs exactly what they return today. `check_standing.standing` accepts the bf16 values.
5. **Tests** (D12), using log lines written as T-0499's tool writes them (or by the tool with a test-bound predicate): happy — each reader on a bf16 run's lines at both points, `checks.read` with and without `attempt`, `verdicts.write` with a board check and a comparison under the bf16 value, `spec_feedback.attempts` with a bf16 attempt in round 0; branch — an fp32 run unchanged; lines of both values for one attempt as the ADR decides; an open identity under a bf16 value; negative — a damaged bf16 end line (`run_file_invalid`), a bf16 end line whose `result` has no valid `outcome` (`check_result_invalid`), a `point` of neither value. Package line and function coverage stay at or above 80 %, ruff is clean, the full local suite passes on Linux/WSL with clang; CI is green.
6. **D21 list pins** foreseen: `tests/test_check_standing.py::test_public_names`; any public-name or import assertion of `tests/test_checks_tool.py`, `tests/test_verdicts_tool.py` and `tests/test_spec_feedback.py` that pins `STEP_OF` or the imports. Other existing assertions stay unchanged. List each edited assertion in the PR body.
7. **Owner notice** (DRIVER §9): after merge, one comment on Issue #5 announcing the ADR and the OD rows it changes, ending with `— posted by driver`; record the URL in Result.
8. **Result** names: the language choice and reason (Python), the PR, review rounds, edited list pins, and any runtime acceptance item (expected none; if any, word it for `PROCESS/RuntimeAcceptance.md`, D22). Name the planner's next candidate: the `cpu_standin` operation for the four kinds with the record of its bf16 verification build/process time limits (OD-14; ADR-0117 fixes them for fp32 `gemm` only) and the `checked` flags of the four entries.

## Out of Scope

- The tool side of the check (T-0498, T-0499), the `cpu_standin` operation and its time limits, the `checked` flags of `hilclaw/contract_table.py`.
- `sdpa_kv_cache` (`cache_differs`) and `rope` checks; the bf16 timing run (`timings.read`, `hilclaw/timings_tool.py`); the instance start; the executor binding.
- The evaluator's prompt or agent definition (`.claude/agents/`, `orchestration/`), unless the ADR finds one that names a `step` value — then name it in Boundaries, do not edit it here.
- Any deferred line of PLAN "보류". Starting `claude`, real weights, a board, an API key (D16).

## Follow-ups

## Result

**DONE**: PR #313 squash-merged as `7fcc576e` (branch `claude/T-0500-bf16-check-lines-readers` deleted). Review: 1 round, Approve (dev-reviewer, PR comment 6460706704). The reviewer left three Nits, all docstring-only, and all were fixed after the Approve: a stale `check_standing.standing` mention in `checks_tool`, line wrapping in `checks_tool`/`spec_feedback`, and `checks_of` → `checks_in_order` in the `verdicts_tool` docstring. Under the D20 exception they needed no re-review. CI is green: C, Python 3.11/3.14, coverage, test presence and shellcheck all passed.

- **ADR**: `ARCHITECTURE/decisions/ADR-0178-od23-bf16-check-lines-read.md`, part of OD-23, OD-18 ⑭ (first part) and OD-6.
  - A point's lines are the lines of both its `step` values (the ADR-0040 value and the bf16 value), read together in log order. Only `events.ndjson` is read; `instance.json` is not.
  - The ADR-0110 standing and floor are taken over both values.
  - If one attempt holds lines of both values, every reader takes all of them, and nothing is refused.
  - The request and result of `checks.read` and the `verdicts.json` entries are unchanged.
  - A-13 reading: this is no data-plane schema change.
- **Owner notice** (DRIVER §9): https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6460854442
- **Registers**:
  - `Requirements.md`: one `확정분` link in each of the OD-6, OD-18 and OD-23 rows. OD-6's status date range now reads 10-07~28.
  - `OpenDecisionProposals.md`: one `채택분` line in each of the OD-6, OD-18 and OD-23 sections, and ADR-0178 added to ⑭'s partial answer.
  - `StandardScenarios.md`: the re-check line updated. S0 and S1 were re-checked with no change and no gap.
- **Code**:
  - `check_standing.STEPS_OF` and `point_standing`.
  - `checks_tool.checks_in_order`; `checks.read` now reads both values, and `checks_tool.STEP_OF` is removed.
  - `verdicts_tool`: a check entry is founded on both values, and a counted comparison is checked with `point_standing` at board.
  - `spec_feedback`: the standing, the deciding check and the compiler log are taken over both values, and the log is named by the deciding line's `step`.
- **Language**: Python. The four touched 2nd-layer modules are Python.
- **Edited D21 list pins** (also listed in the PR body):
  - `tests/test_check_standing.py::test_public_names` adds `STEPS_OF` and `point_standing`.
  - In `tests/test_checks_tool.py::test_the_shared_names_are_the_log_and_the_steps_of_the_points`, the assertion on `checks_tool.STEP_OF` becomes one on `check_standing.STEPS_OF`, plus a check that `checks_tool` no longer has `STEP_OF`.
- **Local tests** (WSL, clang): 36712 passed, 50 skipped. `hilclaw/` line coverage is 99% (13077 statements, 52 missed). The CI coverage gate (line and function) passed. `ruff check` and `ruff format` are clean.
- **Size**: about 300 non-test lines (ADR 92, code about 200, registers 13) across 8 non-test files.
- **Runtime acceptance items**: none.
- **Next candidate for the planner**: the `cpu_standin` operation for bf16 `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. It needs the record of its bf16 verification build/process time limits (OD-14; ADR-0117 fixes them for fp32 `gemm` only) and the `checked` flags of those four entries in `hilclaw/contract_table.py`.
