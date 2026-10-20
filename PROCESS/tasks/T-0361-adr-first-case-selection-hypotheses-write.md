---
id: T-0361
title: Record ADR-0132, the selection role of a first-case turn and what writes a round's decision/hypotheses.json (part of OD-23 and OD-30)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-11, FR-17, OD-23, OD-30, OD-18, OD-8]
dependsOn: [T-0352, T-0355, T-0357]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0132-od23-first-case-selection.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 260, files: 4}
hq: []
---
## Why

PLAN P2-6 (hypothesis records and verdicts) is a checklist item and comes before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. The evaluator side of P2-6 is done: ADR-0128 (evaluator, `verdicts.write`), ADR-0129 (`hypotheses.read`) and ADR-0131 (`checks.read`, the verdicts work) all have code (T-0353, T-0354, T-0356, T-0358 to T-0360). The comparison (ADR-0128 Consequences slice 3) waits on `sim.run`/`board.run` (T-0210, HQ-0021), and the coder call waits on HQ-0040/HQ-0041. The round steps of `orchestration/round-manager.md` are still "not yet defined".

The other half of P2-6 has no record yet: who writes a round's `decision/hypotheses.json`. ADR-0059 Boundaries leave open "Which agent writes the file, when it is written against the round's specs and other files (sub-question ⑩ of OD-8), and how its presence and its rules are enforced — '가설 없는 기법 선택을 허용하지 않는다' (OD-23, OD-18)". ADR-0129 Boundaries repeat it as "The selection side (rest of OD-23; P2-6)". OD-23 lists as open whether `technique-selector` is inlined into the main session or is a sub-agent. The layer-2 writer exists (`hilclaw.hypotheses_file.write`, once-only; `hilclaw.hypotheses.validate`; `hilclaw.hypotheses_cases.check_run` for the case rules of ADR-0073), but no tool or agent calls it. Without this record the selection step of the round steps (P2-1) and the first run's hypothesis record (P2-5, FR-17) cannot be written without inventing something.

OD-23 and OD-30 are design-level ODs, not owner-only (DRIVER §9: owner-only means #5 A/B items, C-6, OD-25 and OD-3). Under DRIVER §6 and §9 this task writes the ADR. It must not answer HQ-0031 (whether injected hypotheses must be tested; owner-only), the distribution of injected against system hypotheses (T-0318, blocked on HQ-0031), HQ-0040 (whether any agent has a shell) or HQ-0041 (models and tokens, #5 A-8).

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0361-<slug>`, trailer `Task: T-0361`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`: all rules. In particular "미결은 발명하지 않는다", 문서 커버리지 재검사, the A-13 branch/merge procedure (doc mode: reviewer cycle, rebase onto `origin/main`, **one squashed commit** with the `Reviewed-by` and `Task:` trailers, direct push to main), the BLOCKED reasons (a data-plane schema change is one), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` decision 1 (the *name* form) and §"Record format".
- The models, read whole: `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md` (152 lines; decisions 1 to 7 at lines 26-92 — the holder, its tools, what it is given and returns, the write tool `verdicts.write` and its refusals, the definition's place; Consequences and Boundaries at lines 112-145) and `ARCHITECTURE/decisions/ADR-0129-od23-round-hypotheses-read.md` (127 lines; the `hypotheses_*` kinds, runtime acceptance item (xxi), Boundaries "The selection side").
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md` decisions 1 to 5 (lines 24-87: place, name, once-only write, the file, hypotheses and candidates, round 0) and Boundaries (lines 140-155).
- `ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md` decisions 1 to 3 (lines 25-63: the lookup is input of every round ≥ 1's selection before it writes `hypotheses.json`; the `case` basis; identification of the cases read) and Boundaries (lines 112-125).
- `ARCHITECTURE/decisions/ADR-0075-od30-injection-at-instance-start.md` decision 4 and Boundaries (read so the record does not answer coverage or distribution).
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md` decisions 3 and 6 (the latest registry tool and the evaluator's work; runtime acceptance item (xxii), the last number in the turn-session series).
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` decisions 1 to 5 (lines 27-89), `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md` decisions 1 to 7 (lines 28-91), `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md` decisions 1, 2 and 5 (lines 48-113), `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md` decision 1 (the runs in scope), `ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md` decision 2 (the round-0 attempt a round-1 hypothesis may cite).
- `ARCHITECTURE/Requirements.md`: FR-11, FR-15, FR-17; the OD register preamble **"행 형식"** (line 84); rows OD-8, OD-18, OD-23, OD-30.
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's **"기록 규칙"** (line 8); sections OD-23 (from line 394) and OD-30 (from line 463); the OD-8 sub-question ⑩ text in section OD-8 (from line 87).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29) and §검사 결과 — **its first paragraph is the recording rule**; S0, S1, S8, S11.
- Code, read only as observations (this record binds no code): `hilclaw/hypotheses_file.py` (`parse`, `final_name`, `write` and what each raises), `hilclaw/hypotheses.py` (`validate`), `hilclaw/hypotheses_cases.py` (`check`, `check_run`), `hilclaw/case_lookup.py` (`find`, `lookup`), `hilclaw/hypotheses_tool.py` and `hilclaw/verdicts_tool.py` (kinds and their order), `hilclaw/tools.py` `default_registry`, `orchestration/round-manager.md`, `orchestration/agents/evaluator.md`.
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (CLAUDE.md 세션 진입 점검). Open PR #186 (T-0324) touches only `hilclaw/start_instance.py` and its test. The unlanded branches `claude/T-0318-*` and `claude/T-0231-*` also edit the OD-30 row and section: do not take their content, do not decide what they decide, and note the overlap in the Result. If an open PR touches the same tables or sections, stop and return BLOCKED.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0132-od23-first-case-selection.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Alternatives considered, Consequences, Boundaries, References. Before the push, confirm that ADR-0132 is still free on `origin/main` and every remote branch; if not, take the next free number and update every reference. Keep the record at about 210 lines or fewer.
2. Scope: the runs of ADR-0120 decision 1 (the first case), rounds ≥ 1 (ADR-0059 decision 5: round 0 has no hypothesis record). Each point below is weighed against at least one alternative, and every sentence of the record's own is marked as such (the "cited" versus "this record's own" convention of ADR-0128):
   - (a) **The holder of the selection role** in a turn: the Round-Manager itself (inline) or a `technique-selector` sub-agent issued by it. Weigh the OD-23 note (a sub-agent has a fresh context and reloads state and catalog each round) against the ADR-0128 / ADR-0126 precedent of sub-agents with a narrow tool set.
   - (b) **What writes `decision/hypotheses.json`**: a typed registry tool through the MCP front (for example `hypotheses.write`, taking `run_id`, `round` and the record, calling the layer-2 writer and the case rules of ADR-0073 through `hilclaw.hypotheses_cases`), or the holder's own Write tool, or another means. If a tool is chosen: its request members, its result, its refusals and their order, which of the `hypotheses_*` kinds of ADR-0129 / `verdicts.write` it reuses and with what meaning, any new kind (a *name* of ADR-0001; grep `hilclaw/`, `tests/` and `ARCHITECTURE/` on the day; report equality with existing kinds as on purpose), what it answers when the name is already taken (ADR-0059 decision 1's once-only write), and whether it journals. It admits exactly what the validators on `main` admit; it neither widens nor narrows `hypotheses.json` (an `injected` origin stays as the validator has it — T-0233 is blocked on HQ-0024).
   - (c) **When**, against the round's other writes: whether the record is written before the round's first coder call or spec copy (OD-8 sub-question ⑩ part; ADR-0059 Boundaries), and whether the round steps go on to a coder call without it. Answer it or say plainly that it stays open.
   - (d) **How the holder reaches the lookup output of ADR-0073 decision 1** (a read tool, the write tool's own check, or left to a named later record). Answer it or say plainly what record it waits on.
   - (e) **Presence**: what this record makes of "가설 없는 기법 선택을 허용하지 않는다" for these runs, without deciding hooks (P2-4, rest of OD-18).
   - (f) **The definition's place**: the round steps of `orchestration/round-manager.md` or a file under `orchestration/agents/`, and the tools list it would carry (names only; no model key — HQ-0041).
   - (g) A Walk-through table: round 1 at N = 1 citing the round-0 attempt (ADR-0119 decision 2); a record citing a case; a record that breaks ADR-0059's rules; a second write for the same round; a round-0 request.
3. **Not decided, said openly**: whether injected hypotheses must be tested (HQ-0031) and the order and share of injected against system hypotheses (T-0318); the models and token accounting of any agent (HQ-0041, #5 A-8); whether any agent has a shell (HQ-0040); the comparison and `eval.json` (OD-20); the catalog (OD-22); hooks and permissions (P2-4); a round that never reaches evaluate and a resumed turn (OD-17); runs outside ADR-0120 decision 1. Do not invent an owner decision.
4. **No data-plane schema change.** No member, file, path, kind of `events.ndjson`, value or version of `hypotheses.json` or any other data-plane file is added or changed; tool-failure kinds may be named, with the A-13 reading stated in Consequences as ADR-0128 and ADR-0129 did. If the design you judge right needs a data-plane change or a new external dependency, stop and return BLOCKED with the question.
5. No earlier record is edited. Consequences lists the earlier sentences that become less exact, at least ADR-0059 Boundaries ("Which agent writes the file"), ADR-0129 Boundaries ("The selection side"), ADR-0128 Boundaries where it names the selection, and, as observations, `orchestration/round-manager.md` "The round steps" and the `hilclaw/tools.py` `default_registry` docstring if a tool is added.
6. Consequences names the code slices this record makes possible (for example the tool module and its test file, registration in `default_registry`, and the definition change), each testable with a stub `claude` or none (D16), and names any new runtime acceptance item numbered in the turn-session series after (xxii) of ADR-0131.
7. **Register edits follow the recording rules written in those files, not earlier task files**:
   - `ARCHITECTURE/Requirements.md`: in rows OD-23 and OD-30 (and OD-18 or OD-8 only if the record answers part of them), follow the register's "행 형식": add one link to ADR-0132 with a few words of topic after `**확정분**:`, rewrite `**잔여**:` in place, no restatement of the record and no dated paragraph. Status words stay unchanged.
   - `ARCHITECTURE/OpenDecisionProposals.md`: in sections OD-23 and OD-30 (and others only as in the line above), follow the header's "기록 규칙": one `- **채택분** [ADR-0132](…) — …` line per section after the last adopted line, and rewrite in place the state at the end of each sub-question or open bullet this record answers in part or whole. No restatement, no dated note.
   - `ARCHITECTURE/StandardScenarios.md`: re-check S0, S1, S8 and S11 by §검사 규칙 and record the result exactly as the first paragraph of §검사 결과 says (a re-check with no verdict change leaves no dated line there).
8. Doc mode: reviewer cycle (dev-item-address steps 10 to 12), then rebase onto `origin/main` and push **one squashed commit** to `main` carrying `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0361`. Do not chain the rebase and the push in one command; check the rebase finished before pushing (T-0357 landed unsquashed after a failed chained rebase). Then post the DRIVER §9 owner notice on #5 with the `— posted by driver` footer and put its URL in the Result; give any runtime acceptance HQ text to the driver in the Result.

## Out of Scope

- Any code, test, CI, prompt, agent definition or settings change, including `orchestration/`, `hilclaw/` and `.claude/`.
- The round steps beyond the selection (bring-up, baseline, coder call, measurement, promotion — P2-1, P2-2), the comparison tool, `eval.json`.
- HQ-0031, HQ-0040, HQ-0041 and every owner-only point (#5 A/B items, C-6, OD-25, OD-3).
- Editing earlier ADRs, FR/NFR text, UsageCases, the README or the index documents.
- Starting `claude` or any program that needs a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- Expected next for the planner if the record chooses a tool: the code slice (tool module, test file, `default_registry`), then the definition slice (round steps or a selector definition, with its `tools` test).

## Result
