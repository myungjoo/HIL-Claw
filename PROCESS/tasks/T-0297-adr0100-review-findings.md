---
id: T-0297
title: Apply the three unapplied R7 findings of ADR-0100 (the `stepped_tool_function` observation, the OD-8 row link words, the empty cell of alternative (d)); no code
phase: P1
status: DONE
commitMode: doc
coversReq: [OD-8, "#5 D6"]
dependsOn: [T-0296]
touchesFiles: [ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 15, files: 3}
hq: []   # Corrections of a driver-accepted design record (DRIVER §9) within its objection window; no owner-only item (#5 A/B, C-6, OD-25, OD-3), no new decision. Independent of every open HQ (HQ-0013, HQ-0014, HQ-0016..HQ-0019 runtime-acceptance; HQ-0021..HQ-0029 concern OD-18 sub-questions 18/19, OD-30, instance-start members, profiler.collect, the build log, clang_build/local_run env checks, a shared JSON helper). No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

T-0296 landed ADR-0100 (OD-8 sub-question ㉟ (가)) as b836dbe with the reviewer's round-7 Approve, leaving three findings unapplied (T-0296 `## Result`):

1. **Minor** — ADR-0100 decision 1 (line 28) says `hilclaw/hw_tool.tool_function` "takes `step` when the function is built", but `correctness.check` is built by `hilclaw.hw_tool.stepped_tool_function` (`hilclaw/check_tool.py` line 144), which takes `steps` and `step_of`: the `step` of a call follows from the checked request (`point`), not from a value bound at build time. The observation is therefore inexact for the only HW tool function that exists today.
2. **Nit** — the OD-8 row of `ARCHITECTURE/Requirements.md` (line 99) reads `도구 \`result\` 정의 변경의 구분(새 \`step\` 값) [ADR-0100](…)`; the parenthetical restates the record's answer, which the register's **행 형식** (line 84) forbids.
3. **Nit** — in ADR-0100's Alternatives table, the "What a step … meets" cell of alternative (d) is `—`, unlike every other row.

This task applies those three corrections. It decides nothing new and writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72; executor procedure, resume rule, time limit), §5 (lines 86-115; task format, naming convention, `Task:` trailer, size limit), §9 (lines 141-149; driver-accepted records and the objection window).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `PROCESS/tasks/T-0296-adr-od8-tool-result-change.md` `## Result` (the three findings as recorded).
- `ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md` (whole, 92 lines; Status line 10, decision 1 lines 24-29, Alternatives lines 57-66, Consequences line 70, References line 92).
- `ARCHITECTURE/decisions/ADR-0097-od8-event-payload-change.md` decision 4 (grep `### 4.`; what alternative (d) is rejected by).
- `hilclaw/hw_tool.py` module docstring (lines 1-60), `tool_function` (line 164) and `stepped_tool_function` (lines 232-300); `hilclaw/check_tool.py` lines 1-20 and 100-150; `hilclaw/journaled_tool.py` module docstring, `tool_function` (line 139) and `stepped_function` (line 246) — read as files; run nothing.
- `ARCHITECTURE/Requirements.md` lines 80-86 (정본 규칙 and **행 형식** at line 84) and line 99 (OD-8 row).
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙) and lines 168-173 (§검사 결과: its first paragraph, line 170, is the recording rule; line 172 is the "최근 재검사" line).

## Acceptance Criteria

1. **Finding 1 (decision 1 of ADR-0100).** Rewrite the `hilclaw/journaled_tool.py` bullet (line 28) in place so that it states what the files say at a named commit: which builder fixes `step` at build time (`journaled_tool.tool_function`, `hw_tool.tool_function`), which takes the contract's `steps` and a `step_of` callable so that the `step` of a call follows from the checked request (`journaled_tool.stepped_function`, `hw_tool.stepped_tool_function`), and that `correctness.check` is built by `hw_tool.stepped_tool_function` (`hilclaw/check_tool.py`). Verify by reading whether any tool function for `sim.run`/`board.run` is built in `hilclaw/` today and say so only as the files show it. Keep the point the bullet serves: `step` is the contract's (never a request member) and the four values are bound once in `check_identity.py` / `run_identity.py`. If the commit at which decision 1 is read changes, update the commit named in the Status "record, not code" bullet (line 10) consistently; otherwise leave it. If Consequences (line 70) or References (line 92) name `hw_tool.tool_function` in the same inexact way, correct them by the same rule; nothing else in the record changes.
2. **Finding 3 (alternative (d)).** Replace the `—` cell with a short statement of what a step ended under the earlier list and called again under the later one would meet under (d), taken from or consistent with ADR-0097 decision 4, without re-weighing (d); the "Why" cell stays as it is.
3. **No decision changes.** Decisions 2-5, the adopted alternative, the Boundaries, the registered sub-question ㊱ and every `step` value, closed list, data member, `schema_version` and kind stay as they are. If a correction would change what the record decides, stop and return BLOCKED (reason: 요구 불명확/미결 발명 의심) instead.
4. **Finding 2 (Requirements OD-8 row).** Edit by **행 형식** (line 84) only: in the `**확정분**:` part, the ADR-0100 link keeps a few words of topic with the parenthetical `(새 \`step\` 값)` removed. No other text of the row and no other row changes; the status cell keeps `확정`.
5. `ARCHITECTURE/OpenDecisionProposals.md` is not edited (its ADR-0100 adopted line at line 118 already follows the header's 기록 규칙).
6. `ARCHITECTURE/StandardScenarios.md`: because `Requirements.md` changes, coverage is re-checked under its 검사 규칙 for the scenarios that cite OD-8 (the edits change no decision, so no verdict is expected to change); the "최근 재검사" line (line 172) is rewritten in place as the first paragraph of §검사 결과 (line 170) prescribes — date, trigger (T-0297, corrections of ADR-0100), result. A history entry is added only if a verdict changes or a gap is found or closed.
7. Document mode (CLAUDE.md A-13): branch `claude/T-0297-adr0100-review-findings`, reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) to Approve, rebase on `origin/main`, squash the branch to one commit, push to main directly; the commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0297`. No `git push --force*`.
8. No #5 notice is required (no OD status changes and no decision is added); if the executor judges the decision-1 correction material to the owner's objection window, it may post one short English comment on #5 ending with `— posted by driver` and record its URL in `## Result`.
9. `## Result` records: the three corrections as applied, review rounds and any unapplied findings, and any #5 comment URL. No `claude` process is started (D16); no code, test, compiler or container is run.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `pyproject.toml` or settings files.
- Any change to what ADR-0100 decides; editing any other ADR; `ARCHITECTURE/OpenDecisionProposals.md`; `ARCHITECTURE/EventKinds.md`; `README.md`.
- OD-8 sub-questions ⑥, ⑦, ㉟ (나), ㊱; OD-11, OD-10, the rest of OD-17.
- Open PR #179 files and blocked tasks (T-0121, T-0149, T-0153, T-0155, T-0156, T-0169, T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- None expected. Record any new finding left unapplied in `## Result`.

## Result

- Landed on main as one squashed document-mode commit (`Reviewed-by: reviewer agent (2 rounds, Approve)`; `Task: T-0297`). Files: ADR-0100, Requirements.md (OD-8 row), StandardScenarios.md (recent re-check line).
- Finding 1 (decision 1): the bullet now names both builder pairs as read at `ab71b86` (no `hilclaw/` change up to the landing base): `journaled_tool.tool_function` / `hw_tool.tool_function` take one `step` at build time; `journaled_tool.stepped_function` / `hw_tool.stepped_tool_function` take `steps` and `step_of`, so a call's `step` follows from the checked request. `correctness.check` is built by `hw_tool.stepped_tool_function` (`hilclaw/check_tool.py`), its `step` following from `point`. No `sim.run`/`board.run` tool function is built in `hilclaw/`, and no module there imports `run_identity.py`. `hilclaw/check_tool.py` was added to the read-file lists in Status and References; the commit `ab71b86` stays. Consequences was already exact and is unchanged.
- Finding 3: the (d) "meets" cell now states, from ADR-0011 decision 3 and ADR-0097 decision 4, that a new end kind is not found as an end until the journal and its reader change; "Why" unchanged.
- Finding 2: the OD-8 row link reads `도구 \`result\` 정의 변경의 구분 [ADR-0100]`; nothing else changed.
- No decision changed; OpenDecisionProposals.md not edited. StandardScenarios re-checked S1, S2, S3, S5, S6, S8, S10, S11 (those citing OD-8): no verdict change, no gap, no history entry.
- Review: 2 rounds (R1 Approve with two Nits, both applied; R2 Approve, no findings). No unapplied findings. No #5 comment posted (not material to the objection window). No `claude` process, code, test, compiler or container was run.
