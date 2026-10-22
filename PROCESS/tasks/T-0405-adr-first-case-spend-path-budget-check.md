---
id: T-0405
title: Write ADR-0147 - whether a first-case turn session checks the run's round budget on the path of the next spend, which calls that path holds, where the check sits (a PreToolUse hook beside the caller check of ADR-0146, the tool layer, or nothing beyond today's turn loop and prompt), and what it does when it cannot tell (budget-check part of PLAN P2-4; part of OD-19)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-3, FR-4, NFR-5, OD-19, OD-18, "PLAN P2-4"]
dependsOn: [T-0402, T-0403, T-0404]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0147-od19-first-case-spend-path-check.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-4 covers the runtime hooks: PreToolUse budget and gate checks, PostToolUse journaling, and the Stop commit, with **OD-18 and OD-19 to be closed by ADR, DRIVER §9**. It is still unchecked. It is a PLAN checklist item in the group that PLAN's P2 header puts before P2-5, so the D18 priority rule (DRIVER §6) does not apply to it. ADR-0146 and its two code slices (T-0402, T-0403, T-0404; main `d9205a6`) are done, so the first hook of a first-case turn session exists. Every other route to P2-5 is held by an unanswered HQ: `board.run`/`sim.run` and the `cpu_standin` operations by HQ-0021 and HQ-0026, the coder's container by HQ-0053, and the selection role by HQ-0048. This part of P2-4 is held by none of them.

**Which part of P2-4, and why this one.** "PreToolUse 예산 검사" is the first part PLAN P2-4 names. OD-19's open proposal is "검사를 **다음 지출의 경로 위에** 둘 것" (§ OD-19). ADR-0121 and ADR-0122 both list "a check on the path of the next spend" under Boundaries. As of `main` `12808e5`, the round budget of a first-case run (ADR-0121) is held in three places:
- the turn loop's step 1 (`hilclaw/further_turn.py`), which starts no turn once `run_status` is `"over"` and no commit is owed;
- the tool `round.end`, which writes `"over"` (ADR-0135 decision 4);
- the Round-Manager's prompt, entry steps 4 to 6 of `orchestration/round-manager.md`.

Between turns, the turn loop is the hold. Inside a turn, nothing below the prompt stops a further spending call once the run is over, or a call made after the prompt's own comparison has been skipped. ADR-0146 treated a hold that is only in the prompt as a gap before the first run. This record asks the same question for the budget. Of the gate half of "예산·gate", a gate is owner-only (OD-3, #5 A-5) and stays out of scope.

**Scope, to keep one record reviewable.** It covers the turn sessions of the runs of ADR-0120 decision 1 (first case) only, and the round budget only (`round_budget`, ADR-0032; "over" by ADR-0121 decision 4):
(a) **Which calls of such a session spend.** Each `mcp__hilclaw__` tool the session can call (the Round-Manager's `ROUND_MANAGER_TOOLS`, `coder-driver`'s and `evaluator`'s `tools`) is weighed by what it consumes: plan usage, machine time, or only a read or a write. The record should say plainly what is true today. `coder.run` is not journaled (ADR-0126 decision 7). It is bound to `NoContainerRuntime` until ADR-0141 slice (d), which waits on HQ-0053, so today it starts no coder. `correctness.check` is journaled with an empty `spend` (ADR-0040 decision 6). The turn session's own model turns spend plan usage that no tool call carries. So the record must also say what a check on that path buys before and after slice (d).
(b) **Whether a call on that path is refused** when the run is over on its round budget, or at some other moment the record can ground in ADR-0121, ADR-0032 decision 5 or ADR-0135 decision 4 without a new rule of counting. If so, where the check sits. Weigh the alternatives: a `PreToolUse` hook (a second check in ADR-0146's program, or a second hook entry in the written `.claude/settings.json`); the tool layer (inside the tool functions of the spending tools); both; or nothing beyond the turn loop's step 1, `round.end` and the prompt.
(c) **If checked**: what the check reads and how it reaches it.
- How it reaches the data root. The server uses `hilclaw.data_root_source.configured`. ADR-0010 decision 5 and ADR-0015 decision 3 cover this.
- Which run it reads. The request's `run_id` is one candidate. Comparing that `run_id` with the session's run is a separate open check (ADR-0146 Boundaries), and this record does not decide it.
- Which member it compares.
- What it does when it cannot read the state, meets a state ADR-0121 decision 5 leaves open, or fails itself (refuse or let through). This is for this check only. The general default-FAIL contract of OD-18 stays open.
(d) The code slices this implies, the runtime acceptance items, and the earlier records' sentences that become less exact.

The record may conclude that no check is adopted, for example if what it would catch is already caught, or what it would cost is worse. It then says so, gives the cost plainly, and names what stays open.

Planner's judgements (from `main` `12808e5`; **the reviewer is asked to re-check each**):

- **Not owner-only.** OD-19 is a design-level OD. ADR-0121 and ADR-0122 closed parts of it under DRIVER §9. No budget value is chosen: neither P2-5's `round_budget` (ADR-0121 decision 4 leaves it to the run) nor any cap per round or per coder call. **The repair bound of FR-1 ⑴ and any coder-call cap have no recorded value, and this record does not invent one.** If a coherent answer needs a value, it leaves that open. No gate is set, listed or checked (OD-3, #5 A-5). If the executor finds that the check cannot be written without choosing a budget value, a gate, or the clock of `wall_clock_budget_s` (OD-8 ㉚ (가)), it stops and returns BLOCKED (`requirement-unclear`) with the question.
- **Other axes stay out.** Wall-clock (ADR-0033; its clock is ㉚ (가)), tokens (#5 A-8; the owner's HQ-0041 answer (2), one token axis summing orchestrator and coder tokens, has no record yet and no member), the target metric (#5 A-4), the usage-limit pause (ADR-0122 decision 6) and the no-progress breaker are named under Boundaries and not decided.
- **No open HQ is crossed.** HQ-0053: the record may say what a check would do for `coder.run`, not how the coder starts. HQ-0021, HQ-0026: `sim.run` and `board.run` are not in `default_registry` on `main`. They may be named as future spending calls, but they are not presumed registered. HQ-0048 / T-0361: the unlanded draft ADR-0132 on branch `claude/T-0361-*` is not a record. Do not cite it, and do not presume a `technique-selector` agent or a `hypotheses.write` tool. HQ-0061 (ADR-0146 items (lvi) to (lx)) and HQ-0055 are runtime acceptance items: cite them, but do not treat them as confirmed. Unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0318-*`, `claude/T-0361-*` and `claude/T-0375-*` are not sources, and their ADR numbers are not taken. ADR-0147 is free on `main` and on every remote branch.
- **No data-plane schema change and no new external dependency** (CLAUDE.md A-13).
  - The check only reads. It adds no `STATE.json` or `instance.json` member, no event kind or payload, no file and no `schema_version`.
  - A refusal by a `PreToolUse` hook is not a tool result, and it adds nothing to the data plane.
  - A new failure kind in the contract of a tool that is **not** journaled has precedent: the kinds ADR-0138 added in `hilclaw/spec_tool.py`. Such kinds were not treated as a data-plane change. The reviewer judges this reading.
  - A new kind in a **journaled** tool (`correctness.check`) would reach an `events.ndjson` end line (ADR-0011 decision 7; ADR-0100). Avoid it, leave it open, or return BLOCKED (data-plane schema change).
  - A hook program in the package's languages is not a new dependency.
- **Relation to ADR-0146.** ADR-0146 decision 4 has the turn loop write `.claude/settings.json` with one `hooks` member holding one `PreToolUse` entry. ADR-0146 decision 5 makes the caller check's whole body refuse on any fault. If the record extends that program or that file, it says which sentences of ADR-0146 it revises, and it keeps the caller check's own answers unchanged. If it adds a second hook, it says how the two hooks combine (the `hooks` page: what happens when several matching hooks disagree).
- **Test rule note for a later code slice.** T-0403 read CLAUDE.md test rule ⑤ ("hook 스크립트") as not covering a hook entry point that is a module of `hilclaw/`, so rules ① to ④ applied. The reviewer accepted that reading as Info. The record names the same question for its code slice and does not decide it.
- **No open PR overlaps.** PR #186 (T-0324, draft) touches `hilclaw/start_instance.py` and test files only.

All work is documents and documentation reading. No `claude` process is started on this machine (D16; DRIVER §1-5). Every fact about Claude Code hooks comes from the official documentation (https://code.claude.com/docs/en/hooks, https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/headless), read with a web fetch or `curl` and quoted with URL and date read, as ADR-0146 Context does. Such facts include several hooks on one event and how their decisions combine, the order of hooks from one settings file, the `tool_input` a `PreToolUse` hook receives, and timeouts. What the documentation cannot show becomes a runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, time cap) and §5 (lines 86-114: task format, naming convention, size cap). Also §9 (lines 144-151: OD closing authority, the owner notice on #5, and the 7-day objection period).
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode) and "세 층 모델".
- `ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md`, whole (173 lines). It is the model for form, scope, the Context fact table and its verification marks, the runtime acceptance numbering (last item (lx), line 141) and the "Less exact, not edited" list.
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`: decisions 2 to 5 (lines 39-86) and Boundaries (lines 123-135).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: decisions 1 and 6 (lines 38-44, 90-95) and Boundaries (lines 145-159).
- `ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md`: decisions 2 and 4 (lines 32-48, 58-65).
- `ARCHITECTURE/decisions/ADR-0032-od8-instance-record-round-budget.md`: decisions 5 and 6 (lines 65-82). `ARCHITECTURE/decisions/ADR-0033-od8-instance-record-wall-clock-budget.md`: decision 5 (lines 72-81).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: decisions 5 and 6 (lines 100-113). `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: decisions 3 and 5 (lines 58-66, 83-92) and Alternatives row 5 (line 139).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: decisions 6, 7 and 9 (lines 79-118).
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`: decision 7 (lines 76-80). `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`: decisions 2 and 3 (lines 46-59).
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md`: decision 6 (search for "### 6").
- `ARCHITECTURE/Requirements.md`: FR-3 (line 21), FR-4 (line 22), NFR-5 (line 48), **the "행 형식" rule (line 84)**, and the OD-18 and OD-19 rows (lines 109-110).
- `ARCHITECTURE/OpenDecisionProposals.md`: **the "기록 규칙" bullet of the header (line 8)**, § OD-19 (lines 371-380) and the first bullets of § OD-18 (lines 281-288).
- `ARCHITECTURE/StandardScenarios.md`: line 26 and **the first paragraph of §검사 결과 (lines 168-172, the 기록 규약 and the "최근 재검사" line)**. Also the S0, S1, S2 and S8 rows that cite budgets (search for "budget").
- `orchestration/round-manager.md`: "One round at most" and the entry steps 4 to 7 (lines 6-14, 92-111).
- `hilclaw/further_turn.py` lines 1-55 (docstring). `hilclaw/round_end_tool.py` lines 1-62 (docstring). `hilclaw/coder_tool.py` lines 1-27. `hilclaw/caller_check.py` (whole, 140 lines). `hilclaw/turn_loop.py` lines 1-60 (docstring, including the ADR-0146 paragraph). `hilclaw/turn_permissions.py` lines 90-110 (`ROUND_MANAGER_TOOLS`). `orchestration/agents/coder-driver.md` and `orchestration/agents/evaluator.md` frontmatter (lines 1-5). `hilclaw/data_root_source.py` lines 1-30.

## Acceptance Criteria

1. **New file** `ARCHITECTURE/decisions/ADR-0147-od19-first-case-spend-path-check.md`, in the form of ADR-0146: Status, Context, Decision with a Walk-through, Alternatives considered, Consequences, Boundaries, References. Status says:
   - accepted under DRIVER §9;
   - which part of OD-19 (and of OD-18, if a hook is adopted) it answers, for which runs;
   - the open HQs checked and not crossed, as listed in Why;
   - that it is not owner-only;
   - that nothing was started for it (D16);
   - the sentences of earlier records it replaces or revises, none of them edited.
2. **Context**:
   - cites the gap with exact quotes: ADR-0121 and ADR-0122 Boundaries, the § OD-19 proposal, and ADR-0146's precedent for a hold that is only in the prompt;
   - states what exists as code at a named `main` commit: step 1 of the turn loop, `round.end`, entry steps 4 to 6 of the prompt, `coder.run` bound to `NoContainerRuntime`, and the empty `spend` of `correctness.check`;
   - lists the documentation facts used in a table with *verified* / *not verified* marks, URL and date read.
3. **Decision** answers (a) to (d) of Why for the stated scope. In particular:
   - (a) lists every `mcp__hilclaw__` tool the session's holders can call, with what it spends, and is honest about what is spent today and after ADR-0141 slice (d);
   - (b) states adopt or not, and where, with the reason against each alternative;
   - (c), if adopted: what is read, how the run and the data root are found, which comparison is made, and refuse or let through for unreadable states, open states and faults of the check itself;
   - if adopted as a hook, it states how it combines with ADR-0146's hook and settings file and what of ADR-0146 decisions 4 and 5 it revises.
   No budget value, cap, gate, clock or token axis is decided. A Walk-through covers at least these cases:
   - a call when the run is not over;
   - a call after `round.end` wrote `"over"` in the same turn;
   - a call in a turn that met `"over"` at entry step 4 but did not stop;
   - a call whose request names a run that cannot be read;
   - a fault of the check itself.
4. **Consequences**:
   - code slices for the planner, each sized within the D4 cap, tested with fixtures and a stub `claude` only (D16), and with the test-rule question of Why named;
   - runtime acceptance items numbered from **(lxi)** on, each with how it can be closed (owner by hand, or the runtime's self-check);
   - a "Less exact, not edited" list, found by reading the records of Required Reading and by a search of `ARCHITECTURE/decisions/` for "next spend", "spend path", "budget check" and "until a hook";
   - the A-13 reading (document mode; no code, test, setting, dependency or data-plane change);
   - "The cost, plainly".
   If the record adopts no check, Consequences says what stays held only by the prompt.
5. **Boundaries** names at least these as not decided:
   - gates (OD-3, owner-only);
   - caps per round and per coder call, and the repair bound;
   - the single ledger;
   - the usage-limit pause;
   - the no-progress breaker and non-convergence (UC-7);
   - wall-clock (㉚) and tokens (#5 A-8; HQ-0041 (2) not yet recorded);
   - the check of a request's `run_id` against the session's run;
   - PostToolUse journaling and the Stop hook (rest of P2-4);
   - hooks of other sessions;
   - runs outside ADR-0120 decision 1.
6. **`ARCHITECTURE/Requirements.md`**: edit the OD-19 row, and the OD-18 row only if a hook is adopted, **following the "행 형식" rule at line 84 of that file**. Add one link per new ADR, with a topic of a few words, after `**확정분**:`. Rewrite the open part after `**잔여**:` in place (for example "다음 지출 경로 위의 검사" narrowed to what stays open). Do not restate the record's content and add no dated paragraph. The status cell keeps one status word with a short date and path.
7. **`ARCHITECTURE/OpenDecisionProposals.md`**: edit § OD-19 (and § OD-18 only if a hook is adopted) **following the header's "기록 규칙" (line 8)**. Add one `- **채택분** [ADR-0147](…) — …` line per section touched. Rewrite the open parts and the status of any sub-question in place. Add no dated note and nothing copied from the register row.
8. **`ARCHITECTURE/StandardScenarios.md`**: re-check coverage by the rules of that file (CLAUDE.md "문서 커버리지 재검사") for at least S0, S1, S2 and S8. Record the result **following the first paragraph of §검사 결과**: update the "최근 재검사" line in place. Add an entry to "판정 변화 이력" only if a verdict changed or a gap was found or closed.
9. **Review and landing** (document mode, CLAUDE.md A-13):
   - The context-isolated reviewer cycle passes (dev-code-review document-mode path).
   - The reviewer is asked to re-check each planner judgement in Why, and every quoted documentation fact against its page.
   - Rebase on `origin/main` and push to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0405`.
   - After landing, post the DRIVER §9 owner notice on #5 and record its URL in `Result`.
   - The numbered runtime acceptance items go in `Result`, so the driver can record them as an HQ (`runtime-acceptance`, DRIVER §8). The executor does not edit `PROCESS/STATE.json`.
10. The diff touches only `touchesFiles` plus this task file's `Result`. Size is within the D4 cap (≤ 300 changed lines, ≤ 5 files).

## Out of Scope

- Any code, test, CI, setting or prompt change: `hilclaw/`, `orchestration/`, `tests/`, `.claude/` of this repository. The code slices come later as separate tasks.
- Budget values, caps, the repair bound's value, gates, the wall-clock clock, a token axis or member, and the usage-limit pause.
- The `run_id`-against-session check, PostToolUse journaling, the Stop hook, `PreCompact`, the kill switch, default-FAIL in general, and the invariant list (rest of OD-18 / P2-4).
- Editing any earlier ADR, including the sentences listed as less exact. Editing `PROCESS/PLAN.md` or `PROCESS/STATE.json`.
- Starting `claude`, a container runtime, or anything that needs the runtime machine (D16).

## Follow-ups

- (planner) If the record adopts a check, its code slices follow as code-mode tasks. Otherwise the next part of P2-4 is the disposal of PostToolUse journaling and the Stop hook for first-case turn sessions. ADR-0015 decision 5 and line 146 already place the step lines in the tool layer, and ADR-0143 puts the turn-end commit in the Round-Manager and the turn loop's step 1.

## Result

- **Outcome**: ADR-0147 written (document mode). It adopts, for the turn sessions of ADR-0120 decision 1 and the round budget only, a second `PreToolUse` command hook on `mcp__hilclaw__coder_run` and `mcp__hilclaw__correctness_check` (exact-list matcher) that reads the request's `run_id`, the run's `STATE.json` (and `instance.json`) through `hilclaw.run_file_tools.read` below the data root the turn loop passes as a hook argument (the same real path it gives the server), and refuses (exit 2) when `run_status` is present, when `round` >= `round_budget`, or when it cannot tell (an unreadable or invalid `instance.json` included); a run whose valid `instance.json` states no `round_budget` is let through (OD-8 ㉙ (나) stays open); otherwise no decision. Revises ADR-0146 decision 4 (two `PreToolUse` entries); the caller check is unchanged. Model turns, `Agent` delegations and the command-line front stay held by the loop and the prompt. No budget value, cap, gate, clock or token axis chosen; no data-plane change.
- **Files**: `ARCHITECTURE/decisions/ADR-0147-od19-first-case-spend-path-check.md` (new); `ARCHITECTURE/Requirements.md` (OD-18, OD-19 rows); `ARCHITECTURE/OpenDecisionProposals.md` (§ OD-18, § OD-19); `ARCHITECTURE/StandardScenarios.md` ("최근 재검사" line; S0, S1, S2, S8 rechecked, no verdict change).
- **Follow-ups (planner)**: code slice 1, the budget hook program (new `hilclaw/` module + test file; the test-rule ⑤ question named in ADR-0147 Consequences); code slice 2, `hilclaw/turn_loop.py` writes the second `PreToolUse` entry with the data-root argument (stub `claude` only). When HQ-0021/HQ-0026 lead to a slice that registers `board.run` or `sim.run` for these sessions, that task's Why must cite ADR-0147 decision 2: the slice also adds the tool to the budget check's list. Slice 2 may weigh refusing a data root whose path holds a hook placeholder such as `${CLAUDE_PLUGIN_ROOT}` (exec form substitutes them in `args`; reviewer Info, not decided).
- **Runtime acceptance items (D16) for the driver to record as an HQ (reason `runtime-acceptance`)**: ADR-0147 items (lxi) and (lxii). Suggested question text (Korean):
  > ADR-0147(첫 사례 턴 세션의 지출 도구 앞 라운드 budget 검사 hook; OD-19·OD-18 일부; T-0405)의 런타임 인수 항목 (lxi)·(lxii)를 런타임 머신에서 확인해 주세요. (lxi) `mcp__hilclaw__coder_run`·`mcp__hilclaw__correctness_check` 호출의 `PreToolUse` 입력 `tool_input`이 서버가 받는 인자 객체(그 `run_id` 포함)와 같은지. (lxii) 한 `.claude/settings.json`의 두 `PreToolUse` 항목이 같은 호출에 모두 걸릴 때 — 두 hook의 `command`가 같고 `args`만 달라도 — 둘 다 실행되고, 하나가 exit 2·다른 하나가 exit 0(출력 없음)이면 호출이 막히는지. 선택지: (a) 오너가 수동으로 확인해 결과를 답한다 (b) 런타임 자체 점검 코드 task로 돌린다(예: hook 입력과 서버 요청을 기록해 비교, 시험 도구에 건 두 hook이 각각 흔적을 남기는지) (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 이 검사가 실제 세션에서 지출 호출을 막는다는 확신(실패 시 모든 지출 호출이 거절되거나 검사가 효력이 없음). 막히지 않는 것: ADR-0147의 두 코드 slice(픽스처·스텁 `claude`로만 검증)와 그 밖의 드라이버 task.
