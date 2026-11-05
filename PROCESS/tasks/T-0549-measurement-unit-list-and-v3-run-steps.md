---
id: T-0549
title: Apply HQ-0090 (a)·(가) for PLAN P3-3 — write the §9 ADR for the open `unit` list of `sim.run`/`board.run` results (`ns`, `cycles`), the new `step` values `sim_run_timing_v3`/`board_run_timing_v3` and the readers of v2 and v3, update the registers, and land the ADR's first code slice (the readers)
phase: P3
status: DONE
commitMode: code
coversReq: [D27, OD-32, OD-33, OD-18, OD-8, FR-10, NFR-6, "PLAN P3-3", HQ-0090]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0196-od32-measurement-unit-list-and-run-result-v3.md
  - ARCHITECTURE/StepValues.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/run_identity.py
  - hilclaw/layout.py
  - hilclaw/timings_tool.py
  - hilclaw/verdicts_tool.py
  - hilclaw/harness/timing_finding.py
  - tests/test_run_identity.py
  - tests/test_layout.py
  - tests/test_timings_tool.py
  - tests/test_verdicts_tool.py
  - tests/harness/test_timing_finding.py
estimatedSize: {loc: 450, files: 10}
hq: []
---
## Why

**PLAN P3-3** (virtual NPU) asks for a backend whose compiler options, memory limit, data types **and measurement unit** differ from the CPU on purpose. T-0533 (PR #350, `0de635d9`) landed everything of P3-3 but the unit and the oracle. ADR-0193 decision 4 kept `virtual_npu` at `ns` "until O3 is answered", and decision 8 sizes the follow-up as "1 small one on answer O3 (~150 LOC + reader changes)". O3 was asked as **HQ-0090**. The owner answered it on 2026-11-05 (commit `c59beca5`):

> (a)·(가) — `unit` of the `sim.run`/`board.run` result (`events.ndjson`, `step_ended` line, `result`) becomes an approved open list of DRIVER §3, first values `ns` and `cycles`; new `step` values `sim_run_timing_v3`/`board_run_timing_v3` (ADR-0100) are used for all targets, and readers read both v2 and v3; `cpu_standin` stays `ns`; values are added by a §9 ADR that names this list in its A-13 reading. (가): the list reaches `intervals` and `resolution` only, not `memory_bytes`. `virtual_npu`'s `cycles` is its own ns times a fixed factor, a check value and no evidence about any real NPU; comparison, and ADR-0103's coarse-clock check, happen only within one unit of one run.

The integrator's note in the HQ's `decision` (not the owner's words) names the follow-up as "ADR-0193 decision 8's small task (unit list, `cycles` factor, readers, StepValues)", and leaves to that task's §9 ADR **whether the unit belongs to the target or to the measuring means of a point** (ADR-0194 decision 5: two points of one target may use different means). DRIVER §3 "승인된 열린 목록" already holds the list's entry (same commit). The frame change itself is the owner's; this task fills in the record and code.

**Why two tasks, and only the first now (DRIVER §5 file cap; §6 D20 ① and ④).** The whole change touches the ADR, four register documents and about nine package modules (the writers `run_identity.step_of`, `run_result`, `run_tool`, `targets`, and the readers `timings_tool`, `verdicts_tool`, `spec_feedback`, `model_run_binding`, `layout`, `harness/timing_finding`), more than the 10-file cap. So this task lands the ADR, the registers and the **first code slice**: the readers accept v3 lines (and their unit rule) before any writer writes them. The second slice (the writers switch to v3, `virtual_npu` reports `cycles`, and the remaining readers) depends on decisions this ADR makes (where the unit is held, the factor), so it is not created ahead (D20 ④); the ADR lists it, and the planner creates it after this task lands.

**PLAN P3-3 stays unchecked after this task** and after the second slice: ADR-0193 decision 8 also needs **HQ-0091** (oracle at `virtual_npu`, data type), which is unanswered. Do not anticipate HQ-0091.

**Order (DRIVER §6 D27 ①).** On `main` `c59beca5`: no `nightly-failure` issue is open, no PR is open, `PROCESS/RuntimeAcceptance.md` has no `실패` item (RA-0056 is `미확인`, so D27 ④ asks nothing yet), no P2-15 preparation is pending, and P3-3 is the first unchecked P3 item that is not "오너 확정 필요" (P3-6, P3-11, P3-12 are). If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥/⑦).** Do not ask again or anticipate: HQ-0091 (oracle and data type at `virtual_npu`), HQ-0095 (which execution is which point), HQ-0097 (device-unavailable kind), HQ-0088/0089 (candidate kinds), HQ-0083 (fp16) and HQ-0085 (gates). A GPU or NPU memory figure is not reported: (가) leaves `memory_bytes` as it is, and ADR-0194 decision 4 keeps it unreported until the owner states a form. If the work shows a further owner-only part none of these covers, write the question in `## Result` in the DRIVER §8 structure (Korean), land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0549-<slug>`, the `Task: T-0549` trailer and the PR body's last line, size (D30, ≤ 10 files excluding tests), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0549/`, removed at the end).
  - §3 "BLOCKED 사유" and **"승인된 열린 목록"** (the "측정 단위" entry and the paragraph after the list: what is and is not a frame change; `step` values and ADR-0100).
  - §6 D27 (⑥, ⑦) and §9 (the ADR path: executor ADR + reviewer Approve + owner notice on #5).
- `PROCESS/STATE.json`: `humanQuestions` **HQ-0090** (question and `decision`, verbatim source of the owner's answer), HQ-0078 (⑤ deferred the unit list), HQ-0091 and HQ-0095 (not to be anticipated).
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`: decision 3 (the `Target.unit` field, "Which placement needs no frame change"), **decision 4** (the virtual NPU table, the "Measurement unit" bullet), **decision 8** (the P3-3 row), decision 9 (O3, and the coverage table row ③).
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md`: decision 2 (step values), **decision 4** (the v2 run result; "Which measured values `unit` applies to", "One `unit` for both"), decision 7 (build-log names), **decision 8** (the readers table; "`unit` exactly `"ns"`"; "No other reader was found" and the search method), **decision 9** (slice form and the "one definition per value at every commit" rule), "A-13 reading" (the model for this ADR's).
- `ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md` decisions 3 to 5; `ARCHITECTURE/decisions/ADR-0101-od8-failure-kind-change-and-step-values.md` decisions 7 and 8; `ARCHITECTURE/StepValues.md` (whole, its adding rule and states).
- `ARCHITECTURE/decisions/ADR-0178-od23-bf16-check-lines-read.md` decisions 1 to 4: the existing precedent for a point read under two `step` values (`hilclaw.check_standing.STEPS_OF`), including "when one attempt holds lines of both values".
- `ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md` decision 3 (coarse clock: resolution vs smallest interval, a ratio).
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md` decisions 4 and 5 (clock and `resolution` in `ns` at vendor targets; one point's adapters per operation).
- `ARCHITECTURE/decisions/ADR-0140-od16-first-case-attempt-comparison.md` decisions 3 to 5 (`timings.compare` kinds are tool-layer names, not journaled).
- Code: `hilclaw/run_identity.py`, `hilclaw/run_result.py` (`UNITS`), `hilclaw/run_tool.py` (`_UNIT`, `target.unit`, `_result`), `hilclaw/targets.py` (`Target.unit`, `_virtual_npu`), `hilclaw/timings_tool.py` (`STEP_OF`, `_UNIT`, `timing_problem`, `timing_lines`, `difference_of`, `compare`), `hilclaw/verdicts_tool.py` (comparison entries, line ~300-375), `hilclaw/spec_feedback.py` (~line 250-270), `hilclaw/model_run_binding.py` (`_timed_attempt_without_spec`), `hilclaw/s6_metric.py` (`_best_of`, uses of `timings_tool`), `hilclaw/harness/timing_finding.py` (`run_identity.STEPS`), `hilclaw/layout.py` (`BUILD_LOG_STEPS`, `build_log_file`), `hilclaw/check_standing.py` (`STEPS_OF`, the two-value pattern).
- Recording rules — follow these, do not copy earlier task files' wording:
  - `ARCHITECTURE/Requirements.md` "**행 형식**" (the paragraph before the OD register).
  - `ARCHITECTURE/OpenDecisionProposals.md` header "**기록 규칙**".
  - `ARCHITECTURE/StandardScenarios.md` § 검사 결과, its first paragraph (기록 규약).

## Acceptance Criteria

1. **The ADR** `ARCHITECTURE/decisions/ADR-0196-<slug>.md` (next free number; rename the file in `touchesFiles` terms if the slug differs) records, under §9, the record's part of HQ-0090 (a)·(가), citing the owner's answer as the owner's and marking the integrator's readings as such. It decides at least:
   1. **Where the unit is held** — on the `Target` (today's `Target.unit`) or on the measuring means of a point (ADR-0194 decision 5) — with the reason, and what that means for a target whose two points use different means.
   2. **The v3 result definition** of `sim.run`/`board.run`: the v2 member list of ADR-0183 decision 4 with `unit` one of the approved open list (first values `ns`, `cycles`), applying to `intervals` and `resolution` only; `memory_bytes`, its name and meaning unchanged ((가)). State that v2 keeps `unit` exactly `"ns"` and that no line under a v2 value ever holds another unit.
   3. **`virtual_npu`'s `cycles`**: the fixed integer factor (a check value, no fact about any real NPU — say so in those words' sense), how `intervals` and `resolution` are converted (both by the same factor, integers, `resolution` 0 stays 0), and that ADR-0103 decision 3's coarse-clock test is a ratio and so unchanged within one unit.
   4. **The readers**: each reader of ADR-0183 decision 8's table (and any other found by the same search method, repeated now over `hilclaw/`, `orchestration/`, `catalog/`, `.claude/agents/`) reads a point's lines under **both** its v2 and v3 values (as ADR-0178 does for two check values), what it does when one attempt holds lines of both, and how a comparison handles two results of different units — only within one unit of one run (owner); the record decides whether that is a new tool-layer kind of `timings.compare` or an existing one, with the reason (ADR-0140: its kinds are not journaled). Include `s6_metric`'s best and its use of `timings_tool`.
   5. **StepValues states**: the two v3 rows `defined`; the state of the two v2 rows once writers move to v3, by StepValues' own rules (the states are the record's and do not change with slices, as in ADR-0183 decision 9).
   6. **Code slices in landing order** (the ADR-0183 decision 9 form): slice 1 = this task's code (criterion 3); slice 2 = the writers move to v3 for every target, `cpu_standin` with `ns` and `virtual_npu` with `cycles`, plus any reader not in slice 1. Each commit keeps every tool answering under one definition per value: no writer writes v3 before its readers read it, and no v2 line holds a unit other than `ns`. Give rough sizes against the cap.
   7. **A-13 reading**: names the approved open list "측정 단위" of DRIVER §3, states that `ns` and `cycles` are the owner's first values and the v3 `step` values the owner's, and lists what the record adds as detail; states that no member of `STATE.json`, `instance.json`, a spec or `artifacts.json`, no event kind and no layout version changes; that `memory_bytes` is untouched; and that no BLOCKED reason remains.
   8. **Consequences**: list the sentences of earlier records made less exact and not edited (at least ADR-0193 decision 4's "Unit `ns` until O3 is answered" and decision 8's P3-3 row, ADR-0183 decision 4's "`unit` string `"ns"`" and decision 8's "No reader keeps accepting the retired values"/"`unit` exactly `"ns"`" scope, the `targets.py` module docstring's "until the owner answers"). Do not edit those records.
   9. **Boundaries**: the memory-figure form at vendor targets (not decided, (가)), which execution is which point (HQ-0095), the oracle at `virtual_npu` (HQ-0091), units other than `ns`/`cycles`, and P3-3's check waiting on HQ-0091.
2. **Registers**, by their recording rules (Required Reading), with no restatement of the record and no dated paragraphs:
   - `ARCHITECTURE/StepValues.md`: the two v3 rows (after checking the strings are unused in `hilclaw/`, `tests/`, `ARCHITECTURE/`), and the v2 rows' state as the ADR sets it.
   - `ARCHITECTURE/Requirements.md`: one link to the new ADR in the `**확정분**:` of each OD row it answers part of (at least OD-32; OD-33 ⑥'s unit part; OD-18 if the ADR answers part of ⑩ or the result format), and the `**잔여**:` of those rows rewritten in place.
   - `ARCHITECTURE/OpenDecisionProposals.md`: in § OD-32 and § OD-33 (and § OD-18 if touched), one adopted-ADR line each and the affected sub-questions' end state and bullet status word rewritten in place (OD-32 ② and ③ unit parts; OD-33 ⑥'s unit-list part, which HQ-0090 says is now settled).
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by its rules and update the "최근 재검사" line in place; add to "판정 변화 이력" only if a verdict changes or a gap appears or closes.
3. **Code slice 1 — the readers accept v3, no writer changes** (adjust if the ADR's slicing differs, but stay within the cap):
   - `hilclaw/run_identity.py`: the two v3 constants; a per-tool or per-point mapping of the values a reader accepts (v2 and v3); `STEPS` (or a new name) covering the four values for readers such as `harness/timing_finding`; `step_of` **still returns the v2 values** in this slice.
   - `hilclaw/layout.py`: `BUILD_LOG_STEPS` gains the two v3 values (so a v3 writer's build-log name is valid when slice 2 lands); the v2 values stay.
   - `hilclaw/timings_tool.py`: a point's timing lines are read under both values; a v2 result is admitted only with `unit` exactly `"ns"`; a v3 result with `unit` one of the list the ADR names; two results of different units are not compared, answered as the ADR decides; `STEP_OF`'s callers keep working.
   - `hilclaw/verdicts_tool.py`: comparison entries find a point's lines under both values.
   - `hilclaw/harness/timing_finding.py`: reads the run lines of both values, if its `STEPS` use needs a change.
   - Every existing behaviour on v2 lines is unchanged: all existing tests pass, apart from D21 list assertions.
4. **Tests** (D12: happy, error, branch and negative; every public function of a touched module). At least: a v3 line with `ns` and one with `cycles` read and compared by `timings.compare` and `verdicts.write`; a v2 line with `unit` `"cycles"` refused as `timing_result_invalid` (negative); a v3 line with a unit outside the list refused; two results of different units refused as the ADR decides; an attempt holding a v2 and a v3 line handled as the ADR decides; `timing_finding` finds a coarse clock on a v3 `cycles` line; `layout.build_log_file` accepts the v3 values and still refuses an unknown step; `step_of` still returns the v2 values. Coverage of `hilclaw/` stays ≥ 80 % line and function. Tests use constructed `events.ndjson` lines; no Docker, no `claude`.
5. **List assertions (D21)** expected to change, only as far as the change requires, each listed in the PR body: the `BUILD_LOG_STEPS` tuple in `tests/test_layout.py`; the `STEPS` (and constant) assertions in `tests/test_run_identity.py`; any `STEP_OF` equality in `tests/test_timings_tool.py`; any public-name set of `run_identity` or `timings_tool`. No other existing assertion changes.
6. **Size**: about 450 changed non-test lines including the ADR, ≤ 10 non-test files (the 5 documents + at most 5 modules). If slice 1 needs another module (for example `hilclaw/s6_metric.py` for a new kind), move the least necessary reader to slice 2 rather than exceed the cap, and say so in the ADR and `## Result`.
7. **Language**: Python, as the existing modules (one line in the commit body, CLAUDE.md language policy).
8. **§9 notice**: after landing, post the owner notice on #5 as §9 requires (the ADR, the OD parts it answers, the 7-day objection period), and record the comment link in `## Result`.
9. `## Result` lists: PR and merge commit, review rounds, the ADR's decisions in one line each, the second slice as a follow-up with its files and rough size (for the planner), any reader found beyond ADR-0183's table, and any new owner-only question in the §8 form.

## Out of Scope

- The writers: `run_identity.step_of` returning v3, `run_result.UNITS`/the v3 builder, `run_tool`, `targets.py` (`virtual_npu` `cycles` and the factor), `spec_feedback.py`, `model_run_binding.py` — slice 2, planned after this task lands.
- Checking PLAN P3-3 (needs HQ-0091 too). `correctness.check` or instance start at `virtual_npu` (HQ-0091).
- Any memory-figure change, any new member, event kind or layout version; units other than `ns` and `cycles`.
- Editing earlier ADRs (list them in Consequences instead), and the PLAN "보류" wording lines (ADR-0193 follow-up and others).
- Any `claude` process, Docker run or vendor tool.

## Follow-ups

- Slice 2 of the new ADR (writers to v3, `virtual_npu` `cycles`, remaining readers): the planner creates it after this task is `DONE`.

## Result

- **Outcome**: DONE. PR #365 (squash-merged as `41dbf4bf`), branch `claude/T-0549-measurement-unit-list-v3` deleted. Review rounds: 4 (R1 Request changes — S6 `_best_of` could choose a best across units; R2 Approve; R3 Request changes after merging `origin/main` (HQ-0089/0091/0092/0094 register edits) — OD-18 ⑩'s end state lacked ADR-0196; R4 Approve; two docstring Nits after Approve fixed without re-review, D20). CI green on the PR head (run 41950324371); local full suite 38832 passed / 2213 skipped, `hilclaw/` coverage 98.7 % lines, 99.2 % functions.
- **Order check (D27 ①)** held at `main` `4d3e3ece`. During the task HQ-0091 was answered (`c1d2f567`); ADR-0196 records that and depends on nothing of it.
- **ADR-0196** (`ARCHITECTURE/decisions/ADR-0196-od32-measurement-unit-list-and-run-result-v3.md`), decisions one line each:
  1. Scope: every `sim.run`/`board.run` call at every target; one format for all targets (owner).
  2. v3 result under `sim_run_timing_v3`/`board_run_timing_v3` (owner's spellings): ADR-0183 decision 4's members, `unit` a value of the approved open list "측정 단위" (`ns`, `cycles`), applying to `intervals`/`resolution` only, `memory_bytes` unchanged; the definition refers to the list, so a later value needs no new `step`; v2 keeps `unit` exactly `ns`.
  3. The unit is held on the `Target` (not per point's means); a later target whose points differ moves it in package source.
  4. Readers read a point's v2 and v3 lines together (ADR-0178 form); each line held to its own value's unit rule; an attempt with both is one point (`measurement_several` etc.); two units → new tool-layer kind `units_differ` (after `shapes_differ`); S6 admits `ns` only (read failure otherwise).
  5. `virtual_npu` reports `cycles` = its ns × 3 (check value, no fact of any real NPU), converted after the ns judgement, `resolution` and `intervals` both, 0 stays 0; ADR-0103's test unchanged.
  6. Slices: 1 = readers (this task); 2 = writers and remaining readers.
  7. StepValues: v3 rows `defined`; v2 rows `not used`.
  A-13 reading names the list "측정 단위"; no frame change beyond the owner's; no BLOCKED reason.
- **Registers**: StepValues (2 v3 rows, v2 rows `not used`); Requirements OD-8/OD-18/OD-32/OD-33 rows; OpenDecisionProposals §OD-8, §OD-18 (adopted line and ⑩ end state), §OD-32 (②·③), §OD-33 (⑥); StandardScenarios "최근 재검사" (no verdict change, no gap).
- **Code slice 1** (non-test: 5 modules, ~220 changed lines incl. docstrings; with the ADR and registers ~400 changed lines, 10 files): `run_identity` (v3 constants, `STEPS` = four values, `UNITS_OF`; `step_of` still v2), `layout.BUILD_LOG_STEPS`, `timings_tool` (`STEPS_OF` replaces `STEP_OF`, unit rule, `KIND_UNITS_DIFFER`, `timing_problem(result, step=None)`, `TimingLines.steps`), `verdicts_tool`, `s6_metric`. `harness/timing_finding.py` needed no change (reads `run_identity.STEPS`), so it moved out of the slice to keep `s6_metric` within the 10-file cap. Language: Python.
- **D21 list assertions changed**: `tests/test_run_identity.py` (`STEPS` tuple and length, `set(STEPS)` → `set(STEPS[:2])`, public-name set, import list), `tests/test_layout.py` (`BUILD_LOG_STEPS` tuple), `tests/test_timings_tool.py` (`STEP_OF` → `STEPS_OF` equality).
- **Readers found beyond ADR-0183's table**: `hilclaw/s6_metric.py` (slice 1), `hilclaw/spec_feedback.py` `_board_median` (`feedback.base`, ADR-0184) and `hilclaw/model_run_binding.py` `_timed_attempt_without_spec` (ADR-0189) (slice 2).
- **Follow-up for the planner — ADR-0196 slice 2** (writers to v3 and remaining readers): `hilclaw/run_identity.py` (`step_of` → v3), `hilclaw/run_result.py` (`UNITS` from `UNITS_OF` of v3), `hilclaw/run_tool.py` (conversion by the target factor after the ns judgement; mock `ns`), `hilclaw/targets.py` (factor on `Target`, `virtual_npu` `cycles` × 3 as `VIRTUAL_NPU_CYCLES_PER_NS`, `cpu_standin` `ns` × 1, docstring), `hilclaw/spec_feedback.py` (both board values, `timing_problem` with the line's step, medians within one unit else no `base`), `hilclaw/model_run_binding.py` (either board value), `hilclaw/harness/timing_finding.py` docstrings. About 250 changed code lines, 7 files.
- **Runtime acceptance items**: none.
- **New owner-only question**: none.
- **§9 notice**: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6647513986
- **Storage**: task directory `${TMPDIR}/hilclaw-driver/T-0549/` removed with `rm -r`; no image, no install.
