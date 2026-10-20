---
id: T-0369
title: Add the registry tool round.end of ADR-0135 decision 2, which folds the stored spend view over the log's tail, compares the next round with round_budget and replaces STATE.json (ADR-0135 slice 1; PLAN P2-1)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-1, FR-3, NFR-1, OD-23, OD-8, OD-17, S0, S1]
dependsOn: [T-0368]
touchesFiles:
  - hilclaw/round_end_tool.py
  - hilclaw/tools.py
  - tests/test_round_end_tool.py
  - tests/test_tools.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
estimatedSize: {loc: 240, files: 2}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager and its round steps) is a checklist item and the first group in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply.

A first-case round cannot end today. The Round-Manager would have to fold the spend view itself and copy totals into `state.write`. ADR-0135 (landed on main as 0d5a3ba, T-0368) decides that this write is made only by a new registry tool, `round.end`. The tool folds the stored view over the log's tail, compares the next round with the run's `round_budget`, and replaces `STATE.json` itself, so the model supplies no number. Its Consequences name slice 1 as "Now": the tool in a module of `hilclaw/`, its test file, and its registration in `default_registry`. This task is that slice. Slice 2, the step in `orchestration/round-manager.md`, follows. Without the tool, P2-5's first run cannot end round 0.

The owner answered HQ-0041 this iteration (#5 A-8: one token axis that sums the orchestrator's and the coder's tokens). That answer does not change this slice. `round.end` folds whatever axes the log's end lines name and decides nothing about axes (ADR-0135 Boundaries: "axes not accounted through the log … HQ-0041 and #5 A-8 included"). The answer unblocks a later slice, ADR-0049 slice (d), not this one.

The tool reads `STATE.json`, `events.ndjson` and `instance.json` as files. A test writes them itself. It does not need the unlanded start function of PR #186 (T-0324, BLOCKED on HQ-0032), and it touches none of that PR's files.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §2 (code mode).
  - §3-5 (executor procedure, the resume rule, the 2 h 30 min time limit).
  - §5: naming (branch `claude/T-0369-<slug>`, a PR title containing `T-0369`, the trailer `Task: T-0369`, and `Task: T-0369` as the last line of the PR body used as the squash message); the size cap, which excludes tests; the language line in the Result; test rules ① to ⑤.
- `CLAUDE.md`: all rules. In particular:
  - the test rules (D12);
  - the language policy (Python here, with one line in the commit body saying why);
  - the A-13 code-mode procedure and its BLOCKED reasons (a data-plane schema change is one);
  - "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- **The record to implement**: `ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md`. Read the Decision with its Walk-through (lines 24-90), the Consequences (lines 112-131) and the Boundaries (lines 132-139). Decision 2's table is the contract: name, request, result, the six checks in order, and their kinds. Decisions 3 and 4 say what is folded and exactly what is written.
- Context for the contract:
  - `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md` decisions 6 and 7 (lines 79-102): *Replay*, *Bound*, *Disagreement*.
  - `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md` decisions 2 to 4 and 6 (lines 29-75 and 82-91). A total is of any size; position is an *integer*.
  - `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md` decisions 2 and 7 (lines 29-48 and 84-89).
  - `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decisions 2 to 4 (lines 39-82).
  - `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md` decisions 2 to 4 and 6 (lines 30-94), especially the table of decision 3.
  - `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` decision 4 (lines 69-99, the MCP name mapping).
  - `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md` decisions 2 to 4 (lines 39-72).
  - `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` decision 3 (lines 43-63).
  - `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md` decision 3 (lines 39-54).
- Code, in this order:
  - `hilclaw/case_tool.py` (whole). It is the closest model for the module shape, the description, the input schema, `_checked`, the `round_not_current` check and `_reported`.
  - `hilclaw/key_store_tool.py` (whole), the most recent tool of the same shape.
  - `hilclaw/run_file_tools.py`: the module docstring, `read` (from line 197), `_write` and `_reported` (lines 251-282), and `KIND_STATE_NOT_WRITTEN`.
  - `hilclaw/run_files.py` (`NOT_THERE`, `relative`, `data_root_is_there`, `read_failure`, `reading`).
  - `hilclaw/run_journal.py` (whole). `current` is the fold the ADR names. Note that it reads `STATE.json` itself and raises unmapped errors (AC 3 ④).
  - `hilclaw/events.py` `read` (from line 181), `CorruptEventsError`, `PositionBeyondLogError` and `UnsupportedVersionError`.
  - `hilclaw/journal.py` `SpendView`, `Report`, `JournalError` and `fold` (lines 52-176).
  - `hilclaw/checks_tool.py` lines 125-140 (`_LOG_KINDS`) and 260-300: an existing mapping of log-read errors to `run_file_*` kinds.
  - `hilclaw/run_state.py` `RunState`, `parse`, `to_stored` and `dump` (lines 60-190).
  - `hilclaw/run_state_file.py` (whole, `replace`).
  - `hilclaw/instance.py` `Instance`, `parse` and `round_budget_of` (line 1000).
  - `hilclaw/tools.py` (`ToolFailure`, the kind pattern, `RESERVED_KINDS`, `default_registry` from line 182, `call`).
  - `hilclaw/data_root_source.py`.
- Tests to model on and to extend:
  - `tests/test_case_tool.py`, `tests/test_key_store_tool.py`, `tests/test_run_file_tools.py` and `tests/test_run_journal.py`;
  - `tests/test_tools.py` (`DEFAULT_SET`) and `tests/test_default_registry_schemas.py` (`ACCEPTED`);
  - the tool-name lists in `tests/test_mcp_front.py`, `tests/test_blob_tools.py` (around lines 176-190 and 700) and `tests/test_check_definition.py` (around lines 120-135, 380-430 and 660).
- Before you start, run `gh pr list`. Open PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files outside this task, so it does not overlap. If another open PR touches a file of `touchesFiles`, stop and return BLOCKED (DRIVER §3-3). The unlanded branch `claude/T-0361-*` (ADR-0132, not a PR) also registers a tool in `hilclaw/tools.py`. Take nothing from it; whichever lands later rebases there.

## Acceptance Criteria

1. **New module `hilclaw/round_end_tool.py`.** (ADR-0135 leaves the module name to this slice. If you pick another name, keep the `_tool` suffix and update `touchesFiles` in the Result.)
   - It exposes `definition(source)`, which returns a `tools.ToolDefinition` for the name `round.end` (MCP `round_end`), as `case_tool.definition` does.
   - `source` is asked once per call, after the request is checked.
   - `definition` raises `TypeError` for a `source` that is not callable.
   - The module docstring states the contract below and cites ADR-0135. Each `KIND_*` constant carries a `#:` line.
   - The description tells the model the request, the result, and every failure kind in order. It also tells the model what to do: report a non-empty `reported_lines` in one line and go on, and on any failure report the kind in one line and end the session without another write (decision 5).
   - The input schema has `run_id` with the same pattern as the other tools, and `round` as an integer from 0 to 2^53 − 2. Both are required, with `additionalProperties: false`.
2. **Request and result** (ADR-0135 decision 2).
   - The request is exactly `run_id` and `round`.
   - Each of these gives `invalid_request`: any other member; a missing member; a `run_id` that `layout.check_run_id` refuses; a `round` that is not an `int` (a `bool` included); a `round` outside 0 to `keys.MAX_INTEGER − 1`.
   - The result is `{"round": k + 1, "over": bool, "reported_lines": [...]}`.
     - `over` is true exactly when `run_status` `"over"` was written.
     - `reported_lines` holds the file line numbers (from 1, ascending, possibly empty) of the `journal.Report`s of the fold. `Report.line` already counts from the file's first line; check this and say so in the docstring.
3. **The checks, in exactly this order.** The first failing check decides, and nothing is written before ⑥.
   1. The request (`invalid_request`).
   2. The data root, through `data_root_source.obtain` (`no_data_root`).
   3. `STATE.json`, read once by `run_file_tools.read(data_root, run_id, "STATE.json")`, which gives the four `run_file_*` kinds as `state.read` answers them. Then:
      - its `round` equal to the request's, else `round_not_current` (reuse `case_tool.KIND_ROUND_NOT_CURRENT`);
      - then its `others` empty, else the new kind `state_member_extra`. This holds for `run_status` of any value and for any other member. The message names the members found.
   4. The tail of `events.ndjson` after the position stored in the `STATE.json` of ③. It is read with `events.read` and folded with `journal.fold` from the view of ③. The view folded must be the one checked at ③, not a second read of `STATE.json`. So use `run_journal.current` only if you first widen it to take a given state; otherwise call `events.read` and `journal.fold` directly. Map the failures as ADR-0019 decision 3's table does, each message starting with `runs/<run_id>/events.ndjson`:
      - `run_file_invalid`: a damaged complete line (`CorruptEventsError`), a position beyond the log (`PositionBeyondLogError`), and a step line that breaks ADR-0011 (the `ValueError`/`JournalError` of `fold`'s line check, with its line number);
      - `run_file_unsupported`: a line of another version;
      - an `OSError`: as `run_files.read_failure` answers it.
   5. `instance.json`, read once by `run_file_tools.read(data_root, run_id, "instance.json")` (the four `run_file_*` kinds). Its `round_budget` is used, which is `None` when not stated.
   6. `run_state_file.replace(data_root, run_id, k + 1, view, others)`. `others` is `{"run_status": "over"}` when `round_budget` is stated and k + 1 ≥ `round_budget`, else `{}`. Any `OSError` gives `state_not_written` (reuse `run_file_tools.KIND_STATE_NOT_WRITTEN`), with the message `runs/<run_id>/STATE.json: was not written: …` as `state.write` gives it.

   A data root removed after ② gives `run_file_missing` at ③, ④ and ⑤ (ADR-0019 decision 4) and `state_not_written` at ⑥.
   - Check what `events.read` raises for a data root that is gone, with the position 0 and with a position above 0. Make ④ answer `run_file_missing` in both cases, not `run_file_invalid` and not a silent empty tail. If the position is 0 and a missing root gives an empty tail, ⑤ answers instead; state that in the docstring.
   - Every failure message starts with the path concerned, relative to the data root. A message for an `OSError` uses the class and the system text, without the absolute path, and says when the data root is gone.
4. **What is written** (ADR-0135 decisions 3 and 4).
   - Exactly `schema_version` 1, `round` k + 1, `budget_spent` the folded view, and `run_status` `"over"` only under the condition of AC 3 ⑥. Nothing else.
   - The `position` written is the stored position plus the number of complete lines after it. A torn tail is not counted, is not folded and is not removed: the log's bytes are unchanged after the call.
   - Open steps are written as the fold lists them, and the write is not refused for them.
   - A total above `keys.MAX_INTEGER` is written exactly and is read back equal by `run_state.parse`. This is the "conversion" ADR-0135 leaves to this slice: `run_state.dump` already writes such a total. Say so in the docstring.
5. **Kinds.**
   - Reused: `invalid_request`, `no_data_root`, the four `run_file_*` kinds, `round_not_current` and `state_not_written`.
   - New: `KIND_STATE_MEMBER_EXTRA = "state_member_extra"`.
   - Re-grep `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/` before the PR. `round.end`, `round_end`, `mcp__hilclaw__round_end` and `state_member_extra` must not already be in use as names with another meaning (ADR-0135 found only two longer test function names in `tests/test_run_commit.py`). Report the result in the Result.
6. **Not mapped, not invented.** An `InvalidStateError` from `run_state.dump` inside ⑥ has no kind in decision 2. That error is a total too long for the interpreter to write, or a position above `keys.MAX_INTEGER`. Do not map it. Let it pass out of the tool function so that `tools.call` answers it as it answers any other exception, and state which kind that is in the docstring. Cover it with one test through a seam.
7. **Not journaled, nothing else done** (ADR-0135 decision 2).
   - The tool appends no line to `events.ndjson`, selects no backend, and keeps nothing between calls.
   - It reads only `STATE.json`, `events.ndjson` and `instance.json`. Its only write is `run_state_file.replace`: no commit, no case and no removal of a torn tail.
   - It makes no fold from the first line and compares none.
8. **Registration.**
   - `default_registry` in `hilclaw/tools.py` registers `round_end_tool.definition(data_root_source)`, imported lazily like the others.
   - Its docstring names `round.end` (`hilclaw.round_end_tool.definition`, ADR-0135 decision 2), with which the Round-Manager makes the write that ends its round.
   - Building the registry still imports no NumPy.
   - Update the tool-name lists: `DEFAULT_SET` in `tests/test_tools.py`; `ACCEPTED` in `tests/test_default_registry_schemas.py`, with `{"run_id": "r1", "round": 0}`; and the lists in `tests/test_mcp_front.py`, `tests/test_blob_tools.py` and `tests/test_check_definition.py`.
   - Registry order is sorted by name, so `round.end` falls between `key.store` and `run.commit`. Adjust any slice index that shifts.
   - Leave the module docstring of `hilclaw/run_journal.py` unchanged (ADR-0135 lists it as an observation, not an edit of this slice).
9. **Tests: `tests/test_round_end_tool.py`, new**, following D12 and DRIVER §5. Each scenario below is a test.
   - **Happy paths** (the ADR-0135 Walk-through rows):
     - End of round 0 with `round_budget` 6: `round` 1, no `run_status`, `{"round": 1, "over": false, "reported_lines": []}`. The written totals and position equal those of a fold from the first line over the fixture's lines.
     - End of round 4 with `round_budget` 5: `run_status` `"over"`, `over` true.
     - No `round_budget` stated: no `run_status`, `over` false.
     - A stored view with a non-zero position: only the tail is folded. A damaged line *before* the position does not fail the call.
     - A log that ends in a torn tail: the write succeeds, the torn bytes are not counted, and the log is byte-identical afterwards.
     - An open step at the end: it is written in `open_steps`.
     - An end line with no start line, and a repeated start line: the write is made and `reported_lines` names both line numbers.
     - A total above `keys.MAX_INTEGER`: written exactly and parsed back equal.
     - A second call for the same round after one that wrote: `round_not_current`, nothing written.
     - The written file is valid for `run_state.parse` and `run_journal.read_state`.
     - One call through `tools.call` on `default_registry`, and one through the MCP front by its MCP name.
   - **Every kind, in order.** For each kind of AC 3, a fixture where every earlier check passes and only that one fails. Include:
     - each of the four `run_file_*` kinds for `STATE.json`, for the log (damaged line, step line breaking ADR-0011, position beyond the log, another version, unreadable through a seam) and for `instance.json`;
     - `round_not_current`;
     - `state_member_extra` for `run_status` `"over"` and for an unknown member;
     - `state_not_written` through a seam (for example `monkeypatch` of `os.replace` or `run_state_file.replace`), with `STATE.json` byte-identical afterwards;
     - a data root removed after ②, at each of ③, ④, ⑤ and ⑥ (seams);
     - `no_data_root`.
   - **Order**: at least four fixtures with two failures at once, showing that the earlier check decides. Use:
     - `invalid_request` before `no_data_root`;
     - `round_not_current` before `state_member_extra`;
     - `state_member_extra` before a damaged log line;
     - a damaged log line before an invalid `instance.json`.
   - **Negative requests**: an extra member, no member, each member missing, a bad `run_id`, a non-string `run_id`, `round` as a `bool`, a float, a negative number and 2^53 − 1, and a non-callable `source`.
   - **Nothing written on refusal**: after each refused call, `STATE.json`, `events.ndjson` and `instance.json` are byte-identical, and no temporary file is left in the run directory.
   - The unmapped error of AC 6.
   - Coverage of the new module, and of every public function of the touched modules, as CI requires (line ≥ 80% and function ≥ 80% for `hilclaw/`).
10. **No data-plane change.** No member, file, path, value, version or `events.ndjson` kind of any data-plane file is added or changed, and no validator changes (ADR-0135 Consequences, A-13 reading). `state_member_extra` is a tool failure kind only. If the implementation needs any of these changes, stop and return BLOCKED with the question.
11. **Procedure.**
    - Code mode: open a Draft PR, run the reviewer cycle (dev-code-review), and get CI green (pytest, ruff, the test-existence gate and the coverage gate).
    - Then squash-merge with `gh pr merge --squash --body`, whose last line is `Task: T-0369`, and delete the branch.
    - The commit body carries one line on the language choice: Python, because the registry and every reused module are Python.
    - Never start `claude`, and use no stub of it either: this tool needs none (D16).

## Out of Scope

- ADR-0135 slice 2: the `round.end` step in "The round steps" of `orchestration/round-manager.md` and its tool sentence in "Your run". This includes any change to ADR-0133 slice 2 (`case.write` step) and any agent definition or `.claude/` change.
- Any change to `state.write`, `run.commit`, `case.write` or `run_journal` behaviour. Widening `run_journal.current` to take a given state is allowed only if it keeps every existing caller and test unchanged; otherwise call `events.read` and `journal.fold` directly.
- What ends a round, the other ends of a run (ADR-0121 decision 4), a run without a round budget (OD-8 ㉙ (나)), axes not accounted through the log (HQ-0041, #5 A-8, ADR-0049 slice (d)), budget enforcement (OD-19), the lock and retry (rest of OD-17), open-step recovery (OD-10), HQ-0043.
- Any `ARCHITECTURE/` edit, any edit of an earlier ADR, and the "less exact" docstrings ADR-0135 Consequences lists, other than `default_registry`'s.
- Starting `claude`, or requiring a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- ADR-0135 slice 2: in `orchestration/round-manager.md`, the `round.end` step after `case.write` (round ≥ 1) or after round 0's last other step, then `run.commit`; the tool sentence in "Your run" names `mcp__hilclaw__round_end` as the only means of this write. This goes with P2-1.

## Result

- **Outcome**: DONE. PR #212 (`claude/T-0369-round-end-tool`), squash-merged; the merge commit is the one whose last line is `Task: T-0369`. The reviewer approved in round 1 and again in round 2 of 2. Round 1 had one non-blocking nit: `_reported` is a third copy of `run_file_tools._reported`. It was kept, because merging it into a public helper of `hilclaw/run_files.py` would touch a module outside this task. Round 1 also had two procedural notes: wait for CI, and record the re-grep here. CI was green: Python gate 3.11 and 3.14, Coverage gate, Test presence, sh gate and C gate.
- **Language**: Python, because the registry and every reused module are Python.
- **What landed**:
  - New module `hilclaw/round_end_tool.py` (`touchesFiles` unchanged), the tool `round.end` (MCP `round_end`), with the six checks of ADR-0135 decision 2 in order.
  - `run_journal.current` is not used and not widened. ③ reads `STATE.json` once by `run_file_tools.read`, and ④ calls `events.read` at the stored position and `journal.fold` from that same view.
  - Log errors map as ADR-0019 decision 3's table does, through `run_files.reading`: `CorruptEventsError`, `PositionBeyondLogError` and fold's line-check `ValueError`/`JournalError` give `run_file_invalid`, prefixed with `runs/<run_id>/events.ndjson`; `UnsupportedVersionError` gives `run_file_unsupported`; an `OSError` goes through `read_failure`.
  - `round_not_current` is `case_tool.KIND_ROUND_NOT_CURRENT`, `state_not_written` is `run_file_tools.KIND_STATE_NOT_WRITTEN`, and `state_member_extra` is new.
  - `default_registry` registers the tool and its docstring names it. The tool-name lists of the five test files gain `round.end`/`round_end`; the `[:5]`/`[5:]` slices of `test_blob_tools.py` needed no change.
- **Data root gone at ④**: `events.read` calls `_root` before anything else, so a gone data root raises `FileNotFoundError` both at position 0 and above 0. That answers `run_file_missing` at ④, never an empty tail; the docstring says so, and the tests cover positions 0 and 2.
- **Report lines**: `journal.fold` numbers lines from `view.position + 1`, so `Report.line` counts from the file's first line. The docstring says so, and a test with a stored position of 1 checks it.
- **Unmapped error (AC 6)**: an `InvalidStateError` of `run_state.dump` at ⑥ passes out, and `tools.call` answers it with `tool_crashed`. One test uses a `journal.fold` seam that returns a position above `keys.MAX_INTEGER`.
- **Re-grep (AC 5)**: before the PR, `round.end`, `round_end`, `mcp__hilclaw__round_end` and `state_member_extra` (fixed strings) were searched in `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/`. They occur only in ADR-0135 and its entries in `ARCHITECTURE/Requirements.md` and `ARCHITECTURE/OpenDecisionProposals.md`, which name this same tool. Elsewhere `round_end` appears only inside the two longer test function names of `tests/test_run_commit.py`, as ADR-0135 found. No name has another meaning.
- **Tests**: `tests/test_round_end_tool.py`, 87 tests: the Walk-through rows; every kind in order for `STATE.json`, the log and `instance.json`; `round_not_current`; `state_member_extra` for two `run_status` values and unknown members; `state_not_written` through `os.replace` and `run_state_file.replace` seams; a data root removed at ③, ④ (positions 0 and 2), ⑤ and ⑥; `no_data_root`; six order pairs; negative requests; the file tree byte-identical, with no temporary file, after every refusal; the unmapped error; one source call and only the three frame files read per call.
  - `hilclaw/round_end_tool.py` has 100 % line coverage. The full local suite passed (24707 passed, 725 skipped), and `hilclaw/` line coverage is 97 %.
- **Size**: about 260 non-test lines changed (module 255, `tools.py` 6), most of the module the docstring and the model-facing description.
- **Data plane**: no member, file, path, value, version, event kind or validator changed.
- **D16**: no `claude` was started and no stub of it was used. The runtime acceptance items of this slice are ADR-0135's (xxix) and (xxx) (HQ-0051); none is new.
- **Follow-ups**: ADR-0135 slice 2 (the `round.end` step and tool sentence in `orchestration/round-manager.md`) stands. No new follow-up.
