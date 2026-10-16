---
id: T-0240
title: Write the ADR that answers the first half of OD-18 sub-question 5 - what checks that a tool's stated input schema and the check of its tool function agree - and reflect it in the ARCHITECTURE documents
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18, "#5 D6"]
dependsOn: [T-0214, T-0215]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0077 at planning time; ADR-0068 and ADR-0074 are held by the unlanded branches of T-0210 and T-0231, and BLOCKED T-0239 also names ADR-0077 but holds no branch)
estimatedSize: {loc: 170, files: 4}   # one new record of about 110-150 lines; the rest are in-place edits of one or two lines each
hq: []
---
## Why

PLAN P1-1 ("FR-10 도구 계약 ... 인터페이스 + mock 백엔드 + 백엔드 적합성 테스트") is open. ADR-0015 decision 2 made the input schema of a tool definition "a statement to the caller, not a check of the frame: no part of the package validates a request against it. The tool function checks its own request", and tied the two by a rule: "the stated schema admits every request the tool function accepts, and what the function refuses beyond what the schema says is told in the description". Nothing says what makes that rule hold. ADR-0015 registered this as **OD-18 sub-question 5**: "Whether anything checks that the stated schema of a tool and the check of its function agree, and what Claude Code does with an `inputSchema` (F14)". ADR-0039 decision 3 and ADR-0069 decision 4 each wrote a schema under that rule and left 5 open by name ("Sub-question ⑤ stays open: nothing here checks that the schema and the function agree", ADR-0069).

Three tools are registered today (`blob.fetch`, `blob.push`, `correctness.check`; `hilclaw/tools.py` `default_registry`), and `sim.run` / `board.run` will follow (ADR-0061 to ADR-0067; registration waits on T-0210). Each tool's tests check refusals of its own request, tool by tool; nothing is stated about how a tool registered later is held to the rule. This task writes the record that answers the **first half** of sub-question 5, so that a later code task can write the check.

This is a design-level part of OD-18 (not owner-only: DRIVER §9), so the record is written under §9 and the owner is notified on #5. It depends on no unanswered HQ: HQ-0021 (T-0210) concerns `sim.run` / `board.run` tool failures, HQ-0025 (T-0239) the offer of `profiler.collect`; neither is needed to say what checks the agreement of a schema and a function. This task ticks **no PLAN checkbox** (P1-1 stays open).

**The second half of sub-question 5 is not answered here and must stay open**: what Claude Code does with an `inputSchema` (whether it checks arguments before sending, which keywords it accepts; ADR-0015 F14 "not verified"). That is a fact only a live Claude Code session can establish, a runtime acceptance item under D16; the record names it as such and does not try to establish it.

Planner's notes (2026-10-17 UTC, `main` at `25221c9`, from the files; the reviewer is asked to re-check each):
- **What the record must answer** (the executor chooses, weighs alternatives and writes the reasons; nothing below is decided by this file): (1) whether the agreement is checked at all, and where - in the package's tests only, at registration (`Registry.register` today checks nothing of a schema but its type, `tests/test_tools.py::test_register_checks_nothing_of_a_schema_but_its_type`), or elsewhere; (2) which direction(s) of the ADR-0015 rule are checked - "a request the schema refuses is refused by the function as `invalid_request`" is mechanically derivable from a schema; "a request the function accepts is admitted by the schema" needs accepted examples; "what the function refuses beyond the schema is told in the description" may not be mechanically checkable at all; (3) whether a check covers every tool of `default_registry` without per-tool test code, so that a tool registered later is covered when it is added; (4) whether the keywords a schema of the package may use are limited to a named set (today's schemas use `type`, `properties`, `required`, `additionalProperties`, `pattern`, `enum`, `minimum`, `maximum`), and what happens to a schema that uses another.
- **Constraint from ADR-0015 decision 2 that the record must respect or explicitly reopen**: its Why rejects a schema validator in the package - a full one is a new external dependency (the owner's, CLAUDE.md A-13), a self-written subset is "a schema dialect of its own to maintain". A check that lives only in the tests is a different thing from a validator in the request path, but the record must say why the objection does or does not apply to it. A new external dependency is a BLOCKED reason (`new-external-dependency`), not something this record may choose.
- **Existing facts the record may cite as observations** (no code is bound by the record): `hilclaw/tools.py` module docstring and `default_registry`; `hilclaw/blob_tools.py` `_input_schema`; `hilclaw/check_definition.py` `input_schema`; the per-tool refusal tests `tests/test_check_definition.py::test_a_request_the_record_refuses_is_invalid_request`, `tests/test_blob_tools.py::test_a_refused_request_asks_no_source_and_looks_at_nothing`; ADR-0015 decision 6 (what a conformance test "can check of any registered tool" with the frame alone, a consequence, not a decision); the reduction rule of ADR-0039 decision 3, taken over by ADR-0069 decision 4.
- **Home in the register**: OD-18 (sub-question 5 is registered there, in the bullet "하위 질문(ADR-0015가 넘긴 것, ...)"). No new OD number. Any new sub-question the record raises is registered under OD-18 with the next free circled number.
- **A-13 reading**: document mode; no code, no test, no dependency, no schema file. The code slice that writes the check is the next task (Follow-ups), not this one.
- **Overlap**: the unlanded branch of T-0210 edits other bullets of the OD-18 section of `ARCHITECTURE/OpenDecisionProposals.md` (an adopted-record bullet and sub-question 19), the OD-18 row and the StandardScenarios re-check line; this task edits sub-question 5's bullet, an adopted-record bullet, the OD-18 row and the same re-check line. No open PR touches these files (`gh pr list` empty at planning). Report the overlap in the Result so the integrator knows a rebase of T-0210 meets it.

## Required Reading

- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, time limit) and §5 (task format, size cap D4, commit trailers) - mandatory for every task (§6).
- PROCESS/DRIVER.md §1-5 (forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §8 (driver tail on #5 comments), **§9 (the whole section)**.
- CLAUDE.md - 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", **"세션 진입 점검"** (before the first edit: `gh pr list`, issues #4, #5, #7, #8), "개발 드라이버와 런타임의 구분" (D16), "브랜치·merge 절차" (document mode; BLOCKED reasons).
- .claude/skills/dev-item-address/SKILL.md (document mode) and .claude/skills/dev-code-review/SKILL.md ("no invented decisions" in particular).
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md - section "Record format" only.
- ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md - the facts table (F8, F11, F14; around lines 20-30), decision 2 (from line 39), decision 6 (line 108), and the sub-question bullet (line 158).
- ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md - decisions 2 to 4 (request, front holds no check, tool failure).
- ARCHITECTURE/decisions/ADR-0039-od18-blob-push-fetch-local.md - decision 3 (line 36-42; the reduction rule).
- ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md - decisions 2 to 5 (lines 33-90) and Limits (from line 106).
- ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md - decision 5 (line 69) only.
- ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md - the Status section only, as the current model of the Status bullets (owner / record / observation kinds, §9 window). Follow its manner; do not copy its wording.
- hilclaw/tools.py - module docstring (lines 1-20), `Registry.register` (from line 114), `default_registry` (line 182). hilclaw/blob_tools.py `_input_schema` (line 77). hilclaw/check_definition.py `input_schema` (line 82). Read as observations only.
- tests/test_tools.py `test_register_checks_nothing_of_a_schema_but_its_type` (line 293); tests/test_check_definition.py `test_a_request_the_record_refuses_is_invalid_request` (line 464); tests/test_blob_tools.py lines 329-360.
- ARCHITECTURE/Requirements.md - row **FR-10** (line 28); the Open Decisions preamble with the **"행 형식"** paragraph (line 84); register row **OD-18** (line 109).
- ARCHITECTURE/OpenDecisionProposals.md - the header's **"기록 규칙"** (line 8); section **OD-18** (from line 250): its adopted-record bullets, and the bullet "하위 질문(ADR-0015가 넘긴 것, 2026-10-07 등재, 일부 답함)" (line 290) holding ④ and ⑤.
- ARCHITECTURE/StandardScenarios.md - the check rules (지원/미결/갭) at the top, the first paragraph of **§검사 결과** (line 168, "기록 규약") and the "최근 재검사" line; the S0 row (line 186), which cites OD-18 잔여.

## Acceptance Criteria

1. **Session entry check done and stated** in the Result: `gh pr list`, issues #4, #5, #7, #8 read before the first edit; any open PR touching the OD-18 section, row FR-10 or row OD-18 reported (CLAUDE.md "세션 진입 점검").
2. **One new record** `ARCHITECTURE/decisions/ADR-NNNN-od18-<slug>.md`, NNNN the next free number at execution time that is neither 0068 nor 0074, in the record format of ADR-0001, with Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References. Status says it was accepted under DRIVER §9 by the reviewer's approval, not confirmed by the owner, with the 7-day objection window after the #5 notice, and separates owner sentences (if any are cited), the record's decisions and observations of code.
3. The record **answers the first half of OD-18 sub-question 5**: it says whether and where the agreement of a stated schema and the check of its tool function is checked, which directions of the ADR-0015 decision 2 rule that check covers and which it does not, whether it covers every tool of `default_registry` (including tools registered later) without per-tool code, and what a schema that the check cannot read leads to. Each choice gives its reason; at least two alternatives are weighed in "Alternatives considered", among them "nothing checks it beyond each tool's own tests" (today's state).
4. The record **states its relation to ADR-0015 decision 2's Why** (no validator in the package): either the answer keeps it and says why a check of the chosen kind is not what that Why rejected, or it reopens that part by name. It adds **no new external dependency**; if the executor finds the question cannot be answered without one, return BLOCKED with reason `new-external-dependency` and the exact question instead of writing the record.
5. The record **changes no tool's request, result, schema, description or failure kind**, no `schema_version`, and no file of the data plane; it binds no module or function name (a code slice is described for the planner only, in Consequences). If the answer needs such a change, return BLOCKED with the A-13 reason that applies.
6. **The second half of sub-question 5 stays open**: the record names what Claude Code does with `inputSchema` (ADR-0015 F14) as not established, as a fact only a live Claude Code session can show (a runtime acceptance item under D16), and does not try to establish it. No step of this task starts `claude` in any form.
7. **Register edits follow the recording rules written in those files**, not the wording of earlier tasks:
   - `ARCHITECTURE/Requirements.md` row OD-18: per the "행 형식" paragraph - one link to the new ADR added in the row's 확정분 list; the 잔여 part rewritten in place so it no longer lists the first half of ⑤; the status cell unchanged unless the rule says otherwise; no restatement of the record and no dated paragraph. Row FR-10 changes only if the record makes its text untrue.
   - `ARCHITECTURE/OpenDecisionProposals.md` OD-18 section: per the header's "기록 규칙" - one adopted-record bullet linking the new ADR; the sub-question bullet holding ⑤ rewritten in place so ⑤ shows the answered part as a link and the open second half by name; no restatement of the record's content.
8. **Coverage re-check** per CLAUDE.md "문서 커버리지 재검사" and the first paragraph of StandardScenarios §검사 결과: the "최근 재검사" line updated in place (date, trigger, result); a "판정 변화 이력" entry only if a verdict changed or a gap was found or closed; any S-row note citing OD-18 잔여 adjusted only if it now says something untrue.
9. Document mode per CLAUDE.md A-13: branch `claude/T-0240-<slug>`, reviewer cycle (dev-item-address steps 10-12) to Approve within the 7-round cap, rebase on `origin/main`, direct push to `main` with the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0240`.
10. **§9 notice** on #5 after landing: the record's number and title, the OD-18 part it answers, the landing commit link, the 7-day window, with the driver tail of DRIVER §8.
11. Size within DRIVER §5 caps (≤ 300 changed lines, ≤ 5 files).

## Out of Scope

- Any code or test: the check itself, changes to `Registry.register`, any tool's schema or description (Follow-ups).
- The second half of OD-18 sub-question 5 (Claude Code's handling of `inputSchema`), and any runtime acceptance notice for it (Follow-ups; the driver decides).
- `sim.run` / `board.run` registration and ADR-0068 (T-0210, HQ-0021); `profiler.collect` (T-0239, HQ-0025).
- Other OD-18 sub-questions; OD-23; the hooks of PLAN P2-4.
- Correcting earlier ADRs beyond what this record must cite; if one is found untrue, note it in Follow-ups.

## Follow-ups

- (code, next-task candidate) The check the record describes, in the package's tests (and in `hilclaw/` only if the record puts it there), covering every tool of `default_registry`.
- (driver) Whether the second half of sub-question 5 (ADR-0015 F14) is notified as a runtime acceptance item through DRIVER §8 (reason `runtime-acceptance`), or folded into the observations of the runtime self-check (ADR-0054 / ADR-0057; HQ-0016, HQ-0019) - the planner does not decide this.

## Result
