---
id: T-0192
title: Add a package function that classifies the value `objective_of` returns for a run tool call (not stated / not covered / covered) and gives, for a covered one, the sample form and the `bound` or that none is stated (ADR-0061 code slice (1))
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18, OD-13, "#5 D12"]
dependsOn: [T-0191]
touchesFiles: [hilclaw/run_objective.py, tests/test_run_objective.py, hilclaw/instance.py]   # module name is the planner's proposal; the executor may choose another name and must then keep touchesFiles honest in Result
estimatedSize: {loc: 140, files: 3}   # about 130 lines of module (mostly docstring) + a one-sentence docstring edit in instance.py; tests excluded from the cap (D4)
hq: []   # ADR-0061 (accepted 2026-10-15 under DRIVER §9) is the rule; no owner-only decision and no new design choice is needed
---
## Why
PLAN P1-1 (FR-10 tool contracts) is open, and `sim.run` / `board.run` now have the first record of their contract, ADR-0061 (landed as 8f971f1 by T-0191). Its Consequences name two code slices that are "possible now"; this task is slice (1):

> a function of the package that, given the value `objective_of` returns, says whether it is not stated, not covered or covered, and for a covered one gives the sample form and the `bound` or that none is stated

It is the run tools' analogue of `hilclaw/check_admission.py` for `correctness.check` (which renders `tolerance_not_stated` and friends ahead of the tool function). It does not register a tool, ticks no PLAN checkbox and changes no data-plane member: the two `error.kind` values it raises are already named by ADR-0061 decision 4 and are never written to `events.ndjson` (ADR-0061 Consequences, "A-13 reading").

Slice (2) (the judging half split out of `run_timing`) is a separate later task.

## Required Reading
- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time cap 2h30) and §5 (task format, naming: branch `claude/T-0192-<slug>`, PR title contains `T-0192`, commit trailer `Task: T-0192`, PR body last line `Task: T-0192`, size cap, D12 test rules).
- `CLAUDE.md` (repository rules: comment minimisation, language policy, code mode, test rule D12).
- `.claude/skills/dev-item-address/SKILL.md` (the procedure to follow).
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: decision 3 (lines 48-57: what the tool function takes and derives; "An operation is never handed the `bound` or the `objective`"), **decision 4** (lines 59-67: the sample form `interval` for exactly one objective of type `latency_minimisation`; the meaning of "covered"; `objective_not_stated`, `objective_not_covered`), **decision 6** (lines 75-83: the `bound` of the `memory_ceiling` entry; an empty `constraints` is "no ceiling stated", distinct from *not judged*; no other source stands in), decision 7 tool-failure bullet (line 94), Consequences (lines 147-153, code slice (1) and the list of now-less-exact docstrings incl. `objective_of`).
- `ARCHITECTURE/decisions/ADR-0053-od8-instance-record-objective.md` decisions 4 and 5 (lines 54-78: the only valid value today is `{"objectives": [{"type": "latency_minimisation"}], "constraints": []}`; `None` = a valid file without the member; nothing substitutes).
- `ARCHITECTURE/decisions/ADR-0050-od6-task-objective-members.md` decisions 4 and 5 (lines 65-81: a constraint entry has exactly `type` and `bound`; at most one entry per type; `memory_ceiling` defined but not admitted).
- `hilclaw/check_admission.py` (whole file, 188 lines) and `tests/test_check_admission.py` (skim): the pattern to follow - module docstring listing kinds and "choices that are this module's own", `KIND_*` constants, `_MESSAGES` (≤200 chars, start with the member name, show nothing of the content), a `typing.NamedTuple` answer, `tools.ToolFailure` raised.
- `hilclaw/instance.py` lines 1127-1150 (`objective_of` and its docstring).
- `hilclaw/tools.py` lines 65-80 (`ToolFailure`).
- `hilclaw/harness/timing.py` line 74 (`SAMPLE_FORMS = ("interval", "reciprocal")`).
- `hilclaw/harness/memory_ceiling.py` (top 30 lines: `BOUND_MAX`, and that `verdict` is computed elsewhere, not by this task).

## Acceptance Criteria
1. A new module (proposed `hilclaw/run_objective.py`) with:
   - `KIND_OBJECTIVE_NOT_STATED = "objective_not_stated"` and `KIND_OBJECTIVE_NOT_COVERED = "objective_not_covered"`, and a `KINDS` tuple in that order (not stated is tested first).
   - A public function (name the executor's, e.g. `admit(objective)`) that takes exactly the value `hilclaw.instance.objective_of` returns (`None` or the `dict` of the member) and:
     - `None` -> raises `tools.ToolFailure(KIND_OBJECTIVE_NOT_STATED, ...)`;
     - a value that is not covered in the sense of ADR-0061 decision 4 -> raises `tools.ToolFailure(KIND_OBJECTIVE_NOT_COVERED, ...)`: covered means `objectives` holds exactly one entry, that entry is exactly `{"type": "latency_minimisation"}` (an extra member such as `weight` or `priority`, another type, zero or two entries are not covered), and `constraints` holds no entry whose `type` is other than `memory_ceiling`;
     - otherwise returns a `typing.NamedTuple` with the sample form (`"interval"`, which must be a member of `hilclaw.harness.timing.SAMPLE_FORMS`) and the `bound`: the `bound` of the `memory_ceiling` entry as stated, or `None` meaning "no ceiling stated" when `constraints` is empty. The docstring must say that `None` here is *no ceiling stated* and never *not judged* or *within* (ADR-0061 decision 6; ADR-0050 decision 5).
   - The function computes no verdict, reads no file, keeps nothing between calls, takes no default and no other source for the objective or the `bound` (ADR-0061 decision 6), and does not decide its place relative to the op_signature / `n_max` answers (that is OD-18 sub-question 19 (가); say so in the docstring).
   - Value handling the records do not fix (e.g. a non-`dict`, a `dict` missing `objectives`/`constraints`, non-list members - all impossible from `read`) is decided by the module, raised as `TypeError` (never taken as covered), and listed in the docstring under "choices that are this module's own", as `check_admission.py` does. Whether the `bound` is re-validated against `memory_ceiling.BOUND_MAX` is the executor's choice, recorded the same way; no new rule may be presented as a record's.
2. `hilclaw/instance.py`: the sentence of the `objective_of` docstring "what a call of a tool answers when no target is stated is not said (ADR-0053 decision 7)" is updated to cite ADR-0061 decision 4 for the run tools (one sentence; no behaviour change).
3. Tests in `tests/test_run_objective.py` (D12): happy (today's only valid value -> `interval`, `bound is None`; a hand-built value with one `memory_ceiling` entry -> that `bound`), error (`None` -> not stated; each not-covered shape: other objective type, two objectives, zero objectives, extra member in the objective entry, a constraint of another type, with and without a `memory_ceiling` entry beside it), branch (not stated wins over everything else; `KINDS` order; the returned sample form is in `timing.SAMPLE_FORMS`), negative (non-dict, missing members, non-list members -> `TypeError`; messages ≤200 chars and contain no content value), and an integration case through a real `instance.json` written in `tmp_path` and read by `objective_of` (valid file with the member; valid file without it). All public functions of the touched modules are exercised; coverage of `hilclaw/` stays ≥80% line and function.
4. `ruff` and the full `pytest` suite pass locally; CI green on the Draft PR before the squash-merge.
5. Result records the language choice (Python, and why) in one line, as DRIVER §5 requires.

## Out of Scope
- Slice (2) of ADR-0061 Consequences (splitting the judging half out of `run_timing`).
- Any tool function, operation, registration, request or result member of `sim.run` / `board.run`; the seed (OD-13 sub-question 7); the call identity; OD-18 sub-question 19.
- Computing the memory verdict, admitting `memory_ceiling`, or touching `hilclaw/spec.py` / `hilclaw/instance.py` validation (ADR-0052 decision 7 (c) stays unmet).
- Any `ARCHITECTURE/` edit, including the two R7 Nits of T-0191 (a separate doc-mode task).
- Starting any compiler, kernel, container or `claude` process (D16).

## Follow-ups
- (planner, document mode, small) The two R7 Nits of T-0191 in ADR-0061 decision 5 and the OD-13 sub-question 10 note in OpenDecisionProposals (T-0191 Follow-ups).
- (planner, code mode) ADR-0061 code slice (2): the judging half of a timing run split out of `hilclaw.harness.timing.run_timing`.
- (planner, document mode, P1-1) The second slice of the run tools' contract (call identity), then OD-18 sub-question 19 (가)/(나), the result members, the timing seed.

## Result
- **DONE.** PR #133 (https://github.com/myungjoo/HIL-Claw/pull/133) squash-merged as `139ac1a`; branch `claude/T-0192-run-objective-admission` deleted.
- **Files** (touchesFiles kept): new `hilclaw/run_objective.py` (`KIND_OBJECTIVE_NOT_STATED`, `KIND_OBJECTIVE_NOT_COVERED`, `KINDS`, `Admitted(sample_form, bound)`, `admit(objective)`), new `tests/test_run_objective.py`, one docstring sentence of `objective_of` in `hilclaw/instance.py` (now cites ADR-0061 decision 4 for the run tools and keeps ADR-0053 decision 7 for other tools; no behaviour change).
- **Module's own choices** (listed in its docstring): not stated tested first; values `read` cannot return (non-dict, members other than exactly `objectives`/`constraints`, non-list members, non-dict entries, an entry of either list without a `str` `type`) are `TypeError` before coverage; of a covered value, a `memory_ceiling` entry not exactly `type`+`bound` or two of them is `TypeError`, a non-`int` `bound` is `TypeError` and one outside `0..memory_ceiling.BOUND_MAX` is `ValueError` (the bound is re-validated).
- **Language**: Python, because the module is a pure function over the dict the Python instance reader returns and raises the Python `ToolFailure` of `hilclaw.tools`.
- **Review**: 2 rounds, dev-reviewer (fresh context). R1 Approve with 4 Nits (objective/constraint entry handling made symmetric, not-covered message uses the ADR's phrase, docstring sentence reworded, public-name/import test relaxed), all addressed in `1d54688`; R2 Approve with 1 Nit (squash message must reflect the R1 change and keep the language line), addressed in the PR body used as the squash body.
- **Tests**: local `python -m pytest` 19449 passed / 354 skipped (before R1; new file 49 tests after R1, `tests/test_instance.py` re-run green); `ruff check` and `ruff format --check` clean; `hilclaw/run_objective.py` 100% line and branch. CI run 38700161559 on head `1d54688`: all six jobs green (Python 3.11/3.14, Coverage, Test presence, C, sh).
- **Follow-ups**: none new; the task file's existing Follow-ups (T-0191 R7 Nits, ADR-0061 code slice (2), next run-tools contract slice) stand.
