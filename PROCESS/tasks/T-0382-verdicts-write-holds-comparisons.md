---
id: T-0382
title: Make verdicts.write hold comparison entries by ADR-0140 decision 5 — remove comparison_not_given, add timing_result_invalid to the step pass, comparison_unfounded and comparison_unverified (ADR-0140 Consequences slice 2; PLAN P2-3)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-9, FR-17, OD-16, OD-23, OD-18, OD-30, S0, S1]
dependsOn: [T-0381]
touchesFiles:
  - hilclaw/verdicts_tool.py
  - hilclaw/timings_tool.py
  - tests/test_verdicts_tool.py
estimatedSize: {loc: 200, files: 2}
hq: []
---
## Why

ADR-0140 (T-0380, landed on `main` as 230e70b) decides how a first-case verdict gets the comparison of two attempts. ADR-0140 Consequences lists three code slices:

- Slice 1 is the registry tool `timings.compare`. T-0381 landed it (PR #219, squash-merged as f86bc53). Its shared function `hilclaw.timings_tool.compare(run_id, lines, metric, point, measured, against)` was written for this slice.
- Slice 2 is this task: decision 5 in `hilclaw/verdicts_tool.py`.
- Slice 3 is `orchestration/agents/evaluator.md` and its `tools` test. It is a later task.

Today `verdicts.write` refuses every record that holds a `comparison` entry (`comparison_not_given`). So no verdict can be `supported` or `refuted`, even with the comparison tool in place. Decision 5 replaces that refusal:

- every `comparison` entry is recomputed from the log by the same function as `timings.compare`;
- a counted comparison is refused unless both of its sides have the standing "verified" at `board`.

Priority (DRIVER §6, D18): this task is work on the checklist item PLAN P2-3 (evaluator). P2-3 comes before P2-5 in the P2 order, and ADR-0140 is the OD-16 / OD-23 record that P2-3 needs. Without this slice, the evaluator cannot write a single verdict that is anything but `inconclusive` in the first run (P2-5, the near goal). This task is not input hardening, a refactor or a wording cleanup.

Open HQs checked: none is crossed.

- `sim.run` and `board.run` stay unregistered. The tests use fixture log lines only (HQ-0021).
- The evaluator's definition is not touched (slice 3), and no model or budget is named (HQ-0041).
- `hilclaw/verdicts_file.py` and the JSON text helpers are not touched (HQ-0022, T-0225).
- The selection role and `hypotheses.write` are not touched (HQ-0048).
- The files do not overlap open draft PR #186 (T-0324, HQ-0032). That PR touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, D4 size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": the language policy, the test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0140-od16-first-case-attempt-comparison.md`. This is the specification. Read the whole file, and read closely:
  - **decision 5**: every bullet, and the order of checks in its first bullet;
  - decisions 3 and 4, to know what `compare` gives;
  - the Walk-through rows that name `verdicts.write`, `comparison_unfounded` or `comparison_unverified`;
  - Consequences slice 2.
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md` decisions 4 and 5: the `check` entry rule and the log check of `verdicts.write` as they stand.
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md` decisions 2 and 3: the standings.
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md` decisions 3 and 4: the `comparison` entry and the counted comparison.
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md` decision 6: the checks and kinds of `verdicts.write`. Its sentences on `comparison_not_given` are the ones ADR-0140 makes less exact.
- `hilclaw/verdicts_tool.py`, the whole file. This is the module you change.
- `hilclaw/timings_tool.py`: the module docstring, the kind constants, `METRIC`, `STEP_OF`, `_problem`, `_measurement` and `compare`.
- `hilclaw/checks_tool.py`: `STEP_OF`, `LOG`, `KIND_CHECK_RESULT_INVALID`, `log_lines`, `_outcome` and `checks_of`.
- `hilclaw/check_standing.py`: the module docstring, `Standing` and `standing`.
- `hilclaw/verdicts_hypotheses.py`: the docstring of `check`, and `_value`. They give the counted-comparison rule of ADR-0071 decision 4 as the code has it.
- `hilclaw/verdicts.py`, around lines 15-35 and 80-90 and 185-230: what the validator already holds of a `comparison` entry. `measured` is of the document's round, `against` is of a round not above it, and the two are not equal.
- `tests/test_verdicts_tool.py`, the whole file: the fixtures (`record`, `pair`, `check_entry`, `comparison`, `verdict`, `with_hypotheses`, `raw`, `damaged`, `refused`) and the tests that name `comparison_not_given`. `tests/test_timings_tool.py`: how converged, not converged and broken timing end lines are written as fixtures.

## Acceptance Criteria

1. **`comparison_not_given` is removed.** Remove `KIND_COMPARISON_NOT_GIVEN`, its comment, its loop branch and its sentence in the description. No code or test of the package names it afterwards. `orchestration/agents/evaluator.md` still names it; slice 3 changes that file, not this task.
2. **The order of checks** is that of ADR-0140 decision 5, first bullet:
   1. the request (`invalid_request`);
   2. the record's validity and `run_id` (`invalid_request`);
   3. the data root (`no_data_root`);
   4. the round's `hypotheses.json` (the four `hypotheses_*` kinds);
   5. `verdicts_hypotheses.check` (`verdicts_mismatch`);
   6. the read of the run's `events.ndjson` from its first line by `checks_tool.log_lines`, for every record (the four `run_file_*` kinds);
   7. the step lines, in line order (AC 3);
   8. every `check` entry founded (`check_unfounded`);
   9. every `comparison` entry founded (`comparison_unfounded`, AC 4);
   10. every counted comparison verified (`comparison_unverified`, AC 5);
   11. the write (`verdicts_exist`, `verdicts_not_written`).

   Within each of checks 8, 9 and 10, the first failing entry in record order decides. Every check before the write still creates nothing. The only files read are still `hypotheses.json` and the log.
3. **The step pass.** The step lines are looked at in line order, and the first that fails decides among three kinds:
   - a step line about any attempt that `journal.identity_of` refuses is `run_file_invalid`;
   - an end line of an attempt and point that a `check` entry names, whose `result` has no admitted check `outcome`, is `check_result_invalid` (as today);
   - an end line of an attempt that a `comparison` entry names as `measured` or `against`, at the `step` of that entry's `point`, whose `result` is not an admitted timing result, is `timing_result_invalid`.

   An admitted timing result is defined as in `timings_tool` (ADR-0140 decision 3, "An admitted timing result"). The kind's value is `timings_tool.KIND_TIMING_RESULT_INVALID`, re-exported by `verdicts_tool` as `KIND_TIMING_RESULT_INVALID`. Messages start with `runs/<run_id>/events.ndjson: line <n>`.

   **The two scopes are disjoint.** A check scope key has a `correctness_check_sim` or `correctness_check_board` step, and a timing scope key has `sim_run_timing` or `board_run_timing`. So no end line is held to both rules, even when one attempt is named by a `check` entry and by a `comparison` entry. A test shows that a check end line of a compared attempt is not held to the timing rule, and that a timing end line of a checked attempt is not held to the check rule.

   **The executor chooses how the single line-order pass is built.** For example, `timings_tool` may expose a public validation of one timing result, or a scoped pass. Any change to `timings_tool.py` must leave `timings.compare` and `compare` behaving exactly as before. Their existing tests must pass unchanged. A new public function there is tested in `tests/test_timings_tool.py`, and that file is then added to `touchesFiles` in `## Result`.

   **Behaviour that must hold.** When an in-scope invalid timing result comes before an in-scope invalid check result, the timing kind decides, and the reverse order gives the check kind. A step line refused by `identity_of` decides over either one when it comes first.
4. **`comparison_unfounded`** (ADR-0140 decision 5, second bullet). For every `comparison` entry of every verdict, counted or not, in record order, call `timings_tool.compare(run_id, lines, entry["metric"], entry["point"], entry["measured"], entry["against"])` over the lines read in check 6.
   - The entry is unfounded when `compare` raises a `ToolFailure` of `measurement_several`, `measurement_unknown`, `measurement_missing`, `shapes_differ` or `samples_out_of_domain`, or when it returns a `difference` other than the entry's.
   - The failure is `KIND_COMPARISON_UNFOUNDED = "comparison_unfounded"`. Its message names the place (`record.verdicts[i].evidence[j]`) and either the kind and message that `compare` gave, or the two `difference` values (the record's and the one the log gives).
   - `run_file_invalid` and `timing_result_invalid` can no longer come from `compare` at this point, because check 7 already ran. If one does, it must not be reported as `comparison_unfounded`; it propagates as it is.
   - `compare`'s `ValueError` cannot arise for a record that `verdicts_file.parse` admitted. Do not catch it.
5. **`comparison_unverified`** (ADR-0140 decision 5, third bullet). A comparison entry is counted when its `point` is `"board"` and the same verdict holds `check` entries at `board` with `outcome` `"pass"` for both its `measured` and its `against`. This is the rule of `verdicts_hypotheses._value`, without its metric filter, which in version 1 admits only `latency_minimisation`.
   - For every counted comparison, in record order, each of its two attempts must have `check_standing.standing(lines, checks_tool.STEP_OF["board"], round, candidate, attempt)` equal to `Standing.VERIFIED`.
   - Otherwise the failure is `KIND_COMPARISON_UNVERIFIED = "comparison_unverified"`. The message names the place, the side (`measured` or `against`), the attempt and its standing.
   - `measured` is checked before `against`.
   - A comparison that is not counted (a `sim` comparison, or a `board` comparison without both `"pass"` entries) is not held by this check and needs no `check` entry (ADR-0140 decision 5, fourth bullet).
   - `standing` raises `journal.JournalError` for a line that checks 7 and 8 already admitted only if the module rules differ. The executor confirms that this cannot happen for a record that has reached check 10, or else maps it to `run_file_invalid` with the line named, and states which in `## Result`.
6. **Docstrings and description.**
   - The module docstring of `hilclaw/verdicts_tool.py` states the new order of checks with their kinds. It drops "until a tool gives a comparison". It states the rule of AC 4 and the rule of AC 5, and that the two scopes of AC 3 are disjoint. It says that `verdicts_file.validate` is unchanged and that a file which breaks decision 5 is still valid by ADR-0071.
   - The docstring of `definition` lists the new kinds.
   - `_DESCRIPTION` drops "comparison_not_given … refused for now: write check entries only" and tells the model these things, in the manner of the existing text:
     - every comparison entry is recomputed from the log as `timings.compare` computes it;
     - `timing_result_invalid`, `comparison_unfounded` and `comparison_unverified` mean what they mean;
     - a comparison at board counts only with pass check entries at board for both sides, and then both attempts must be verified there;
     - a comparison that does not count is still written.
   - The three new kinds are tool-layer names, not added to `RESERVED_KINDS`. No other new kind is added.
7. **Tests** in `tests/test_verdicts_tool.py`:
   - The fixture log lines are written by `events.append` or as bytes in a temporary data root built by the test. The timing results are built as `tests/test_timings_tool.py` builds them.
   - Each verdict value written must satisfy `verdicts_hypotheses.check`. A `supported` verdict needs a counted comparison as expected, and so on.
   - No `claude` process is started, stub or real. The tests pass on Linux CI and on the local Windows machine.
   - Update the tests that named `comparison_not_given`. Replace `test_a_comparison_entry_is_comparison_not_given` and `test_a_comparison_wins_over_an_unfounded_entry`, and fix the parametrized `test_an_earlier_check_wins_over_a_damaged_log`. Their replacements test the new order.

   The tests cover at least the following.

   **Happy** (the ADR-0140 Walk-through rows):
   - One converged board end line on each side, the interval wholly below `1 / 1.02`, both attempts verified at board, two `"pass"` check entries at board, and the comparison `"lower"`. The record with `verdict` `supported` is written, and the file holds it byte for byte.
   - A `"not_converged"` `against` enters and counts.
   - A `sim` comparison with no `check` entry is written, uncounted, with `inconclusive`.
   - A `board` comparison without the two `"pass"` entries is written, uncounted, even when a side is not verified.
   - A `refuted` record is written.

   **Branch:**
   - Every compare kind becomes `comparison_unfounded`: several measurements, an open identity or a `failure` end line beside one measurement, a missing measurement (including a missing log), `shapes_differ`, and `samples_out_of_domain`.
   - A wrong `difference` (`"higher"` where the log gives `"lower"`) is `comparison_unfounded`.
   - A broken timing end line beside a converged one is founded.
   - With two failing comparison entries, the first in record order decides, across verdicts.
   - A `check_unfounded` entry decides over a later `comparison_unfounded`.
   - `comparison_unfounded` decides over `comparison_unverified`.
   - A counted comparison whose `measured` has a passed board check and an open one is `comparison_unverified`.
   - A counted comparison whose `against` has a passed board check and a class (ii) `failure` end line is `comparison_unverified`. A class (i) `failure` beside a pass stays verified and is written.
   - `measured` is reported before `against`.
   - The line-order rules of AC 3 hold, and the two scopes stay disjoint.
   - A `timing_result_invalid` end line of an attempt or point that no comparison entry names is no failure.
   - An invalid timing result decides over an earlier-checked kind only when its line comes first; it does not decide over a `hypotheses_*` or `verdicts_mismatch` failure.

   **Negative and error:**
   - For each `timing_result_invalid` rule, at least a bad `outcome`, short `intervals_ns` and a bad `shape`, on either named side.
   - A damaged log with a comparison record gives `run_file_invalid`.
   - After every refusal, nothing is created under the data root and the log is byte-identical.

   **Registry:** `verdicts.write` through `default_registry` and the MCP front writes a record with a counted comparison.
8. **D12 test rules**:
   - ① line and function coverage of `hilclaw/` stays at 80 % or more;
   - ② the tests include happy, error, branch and negative cases;
   - ③ every public function of each touched module that changes behaviour is tested;
   - ④ each new module has a test file (none is expected);
   - ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
9. **No data-plane change**: nothing is added to or changed in `verdicts.json`, `events.ndjson`, `hypotheses.json`, `STATE.json`, `instance.json` or `artifacts.json` — no member, file, kind of event, value or version. `verdicts_file`, `verdicts` (the validator) and `verdicts_hypotheses` are unchanged. The three new kinds are tool-layer names (ADR-0140 decision 5, fifth bullet). If the work turns out to need a data-plane change, stop and return BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
10. **Size**: the non-test change stays within the D4 cap (≤ 300 LOC, ≤ 5 files). If it would not, keep checks 9 and 10 together in this task and propose a split in `## Follow-ups`.
11. **Language**: Python. Record the choice and one reason in the commit body and in `## Result` (CLAUDE.md language policy).
12. **Code mode (A-13)**: open a Draft PR whose title contains `T-0382`. After the reviewer cycle ends in Approve and CI is green, squash-merge with the PR body ending in `Task: T-0382`, and delete the branch `claude/T-0382-verdicts-write-holds-comparisons`.
13. Start no `claude` process, and require nothing runtime-only (D16).

## Out of Scope

- **Slice 3**: `orchestration/agents/evaluator.md` (its `tools` list, "Verdicts", and its list of correctable kinds, which still names `comparison_not_given` after this task), and the tools tests in `tests/test_turn_definition.py` and `tests/test_turn_permissions.py`.
- **Any edit of `ARCHITECTURE/`**: no ADR, register row, proposal section or scenario note. The "Less exact, not edited" sentences listed in ADR-0140 Consequences are not edited. The one exception is the `hilclaw/verdicts_tool.py` docstring, comment and description named in slice 2.
- **Behaviour changes elsewhere**: no change to the behaviour of `timings.compare`, `checks.read`, `check_standing`, `verdicts_file`, `verdicts`, `verdicts_hypotheses`, `hilclaw/harness/measurement.py`, the MCP front or `hilclaw/tools.py`.
- **Comparison rules ADR-0140 leaves open**: which attempt `against` must be, whether a verdict must include every comparison, and the rest of OD-18 ⑳.
- **Run tools**: `sim.run` and `board.run` and their registration (HQ-0021, T-0210).
- **Open PR #186**: none of its files.

## Follow-ups

- Next for the planner: ADR-0140 Consequences slice 3. That is `orchestration/agents/evaluator.md` by decision 6: `mcp__hilclaw__timings_compare` added to `tools`, "Verdicts" rewritten, and the correctable kinds updated to `comparison_unfounded` and `comparison_unverified` in place of `comparison_not_given`. The test of the evaluator file's `tools` set changes with it.

## Result
