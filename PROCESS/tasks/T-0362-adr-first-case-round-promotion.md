---
id: T-0362
title: Record ADR-0133, the promotion step of a first-case round - what writes the round's case file into the key directory, and when against the write that ends the round (part of OD-23 and OD-30; PLAN P2-7)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-11, FR-17, FR-18, NFR-1, OD-23, OD-30, OD-29, OD-17, S0, S1, S6]
dependsOn: [T-0348, T-0352]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 240, files: 4}
hq: []
---
## Why

PLAN P2-7 (store a round's hypothesis-outcome case at the round's end, rejected and failed included; exact-key lookup) is a checklist item and comes before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. P2-7's storing half has its file and layer-2 code but no writer: ADR-0072 fixes the case file `db/<hw_profile_key>/<op_signature>/case-<run_id>-<RRRR>.json` and says "The writer role is the promotion step … Which agent or tool holds that step is OD-23"; `hilclaw/cases.py` (`build`, `validate`) and `hilclaw/cases_file.py` (`final_name`, `write`, once-only) exist and nothing calls them; `run.commit` (ADR-0127, `hilclaw/run_commit.py`) already takes in the case files of the rounds it commits, but ADR-0127 decision 4 says the case file must exist before its round's commit and leaves "the order of the promotion write against the write that ends the round (OD-23) and whether every round is promoted (ADR-0072 Boundaries)" open. OD-23 lists as open whether `promoter` is inlined or a sub-agent. Without this record the first run (P2-5) cannot store a case (FR-18) without inventing its writer.

This record does not depend on T-0361 (ADR-0132, BLOCKED on HQ-0048): the promotion reads the round's `decision/hypotheses.json` and `eval/verdicts.json` as files, whoever wrote them, and must not assume any content of the unlanded ADR-0132. OD-23, OD-30, OD-29 and OD-17 are design-level ODs, not owner-only (DRIVER §9: owner-only means #5 A/B items, C-6, OD-25 and OD-3), so under DRIVER §6 and §9 this task writes the ADR. It must not answer HQ-0043 (#5 A-3 and the turn that ends before its round ends; owner-only), HQ-0031, HQ-0040, HQ-0041, or OD-25.

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0362-<slug>`, trailer `Task: T-0362`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`: all rules. In particular "미결은 발명하지 않는다", 문서 커버리지 재검사, the A-13 branch/merge procedure (doc mode: reviewer cycle, rebase onto `origin/main`, one squashed commit with the `Reviewed-by` and `Task:` trailers, direct push to main), the BLOCKED reasons (a data-plane schema change is one), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` decision 1 (the *name* form) and §"Record format".
- The case record, read whole: `ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md` (150 lines; decisions 1 to 4 at lines 23-69, Boundaries "Promotion" at lines 128-143).
- The commit step: `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md` decisions 2 to 4 (lines 37-68; line 61 "What the case files need"), decision 8 (lines 92-96, the HQ-0043 point this record must not answer) and Boundaries (lines 149-160).
- The model for a role plus a write tool: `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md` (152 lines; decisions 1 to 7 at lines 26-92, Consequences and Boundaries at lines 112-145) and `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md` decision 3 (lines 40-60) and Consequences (lines 131-151; runtime acceptance item (xxii)).
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md` decisions 1, 2 and 6 (lines 25-49, 82-85; a hypothesis without a verdict entry has no verdict; an invalid verdicts file is not used).
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md` decisions 1 and 5 (lines 24-31, 84-87) and Boundaries (lines 140-155).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md` decisions 4 and 5 (lines 98-111: one writer role per directory; the knowledge tree, `best.json` and `technique_stats.json` written by the promotion step).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md` decision 2 (lines 57-66, the turn that ends with its round and the one that does not), `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md` decision 1 (the runs in scope), `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` decisions 2 and 3 (lines 37-63; the Round-Manager's typed registry tools, not journaled).
- `ARCHITECTURE/Requirements.md`: FR-11, FR-17, FR-18, NFR-1; the OD register preamble **"행 형식"** (line 84); rows OD-17, OD-20, OD-23, OD-26, OD-29, OD-30.
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's **"기록 규칙"** (line 8); sections OD-17 (from line 263), OD-23 (from line 394), OD-29 (from line 453) and OD-30 (from line 463).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29) and §검사 결과 (from line 168) — **its first paragraph is the recording rule**; S0, S1, S6, S8.
- Code, read only as observations (this record binds no code): `hilclaw/cases.py` (`build`, `validate`), `hilclaw/cases_file.py` (`parse`, `final_name`, `write` and what each raises; a missing key directory fails the write), `hilclaw/run_commit.py` module docstring and `commit` (which case files a commit takes in), `hilclaw/hypotheses_file.py` and `hilclaw/verdicts_file.py` (`parse`), `hilclaw/verdicts_tool.py` and `hilclaw/hypotheses_tool.py` (kinds and their order), `hilclaw/tools.py` `default_registry`, `hilclaw/layout.py`, `orchestration/round-manager.md`, `orchestration/agents/evaluator.md`.
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (CLAUDE.md 세션 진입 점검). Open PR #186 (T-0324) touches only `hilclaw/start_instance.py` and its test. The unlanded branches `claude/T-0361-*` (ADR-0132; rows and sections OD-23 and OD-30; runtime acceptance items (xxiii) and (xxiv)), `claude/T-0318-*` and `claude/T-0231-*` (OD-30) edit the same rows and sections: do not take their content, do not decide what they decide, and note the overlap in the Result. If an open PR touches the same tables or sections, stop and return BLOCKED.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Alternatives considered, Consequences, Boundaries, References. ADR-0132 is taken by the unlanded branch `claude/T-0361-*`; before the push, confirm that ADR-0133 is free on `origin/main` and every remote branch, and if not take the next free number and update every reference. Keep the record at about 190 lines or fewer.
2. Scope: the runs of ADR-0120 decision 1 (the first case), rounds ≥ 1 (ADR-0072 decision 3: round 0 has no case). Each point below is weighed against at least one alternative, and every sentence of the record's own is marked as such (the "cited" versus "this record's own" convention of ADR-0128):
   - (a) **The holder of the promotion step** in a turn: the Round-Manager itself (inline) or a `promoter` sub-agent it issues. Weigh the OD-23 note (a sub-agent pays a fresh context each round) against the fact that the step is deterministic given the round's files.
   - (b) **What writes the case**: a typed registry tool through the MCP front (for example `case.write`, taking `run_id` and `round`, reading the round's two files and the run's `instance.json` for the key, building the case with `hilclaw.cases.build` and storing it with `hilclaw.cases_file.write`), or another means. If a tool is chosen: its request members, its result, its refusals and their order, which existing kinds it reuses and with what meaning, any new kind (a *name* of ADR-0001; grep `hilclaw/`, `tests/` and `ARCHITECTURE/` on the day; report equality with existing kinds as on purpose), what it answers when the key directory is missing (ADR-0072 decision 1: the write creates none) and when the name is already taken, and whether it journals (ADR-0124 decision 3 as precedent).
   - (c) **Which rounds are promoted** (ADR-0072 Boundaries "Promotion"): a round with both valid files; a round with a valid hypothesis record and no verdicts file; a round whose verdicts file is present but invalid or whose pair breaks ADR-0071's rules; a round with no hypothesis record. Answer each for these runs or say plainly that it stays open and why.
   - (d) **When**: the order of the case write against the `STATE.json` write that ends the round and the `run.commit` of ADR-0127 (ADR-0127 decision 4, line 61; the #4 §3c sketch it cites). State what a death between the case write and the round-ending write leaves on disk and what the next turn's entry then does with it, citing the landed behaviour of `run.commit`, **without answering HQ-0043** (whether such a turn's end is committed; ADR-0127 decision 8).
   - (e) **The definition's place**: the round steps of `orchestration/round-manager.md` or a file under `orchestration/agents/`, and the tool names it would carry (names only; no model key — HQ-0041).
   - (f) A Walk-through table: a round with both files; a round whose verdicts are all `inconclusive` (the evaluator's state until the comparison exists, ADR-0131 decision 6); a round with no verdicts file; a missing key directory; a second write for the same round; a round-0 request.
3. **Not decided, said openly**: who creates the key directory and its record files, and when (OD-26; ADR-0127 Boundaries) — if the record finds that a first-case run cannot store a case without it, say so and name it as the next record, do not decide it; `best.json` and `technique_stats.json` (OD-20, OD-7); promotion across repositories and PR policy (OD-25, owner-only); k and Best-of-N (OD-29 beyond N = 1, OD-15); the lookup and selection side (ADR-0073, ADR-0132 unlanded); HQ-0043; HQ-0031; models and token accounting (HQ-0041, #5 A-8); whether any agent has a shell (HQ-0040); hooks and permissions (P2-4); a resumed round (OD-17 beyond what (d) states); runs outside ADR-0120 decision 1. Do not invent an owner decision.
4. **No data-plane schema change.** No member, file, path, `events.ndjson` kind, value or version of the case file or any other data-plane file is added or changed; tool-failure kinds may be named, with the A-13 reading stated in Consequences as ADR-0128 did. If the design you judge right needs a data-plane change or a new external dependency, stop and return BLOCKED with the question.
5. No earlier record is edited. Consequences lists the earlier sentences that become less exact, at least ADR-0072 decision 1 ("Which agent or tool holds that step is OD-23") and Boundaries "Promotion", ADR-0127 decision 4 (line 61) and Boundaries, ADR-0128 Boundaries ("the promoter"), and, as observations, `orchestration/round-manager.md` "The round steps" and the `hilclaw/tools.py` `default_registry` docstring if a tool is added.
6. Consequences names the code slices this record makes possible (for example the tool module and its test file, registration in `default_registry`, and the definition change), each testable with a stub `claude` or none (D16), and names any new runtime acceptance item of the turn-session series. Number such items after the highest number on `origin/main` **and** on the branch `claude/T-0361-*` (that branch uses (xxiii) and (xxiv), so start at (xxv) if it still does), and say so in the Result.
7. **Register edits follow the recording rules written in those files, not earlier task files**:
   - `ARCHITECTURE/Requirements.md`: in rows OD-23 and OD-30 (and OD-17, OD-29 or OD-26 only if the record answers part of them), follow the register's "행 형식": add one link to ADR-0133 with a few words of topic after `**확정분**:`, rewrite `**잔여**:` in place, no restatement of the record and no dated paragraph. Status words stay unchanged.
   - `ARCHITECTURE/OpenDecisionProposals.md`: in sections OD-23 and OD-30 (and others only as in the line above), follow the header's "기록 규칙": one `- **채택분** [ADR-0133](…) — …` line per section after the last adopted line, and rewrite in place the state at the end of each sub-question or open bullet this record answers in part or whole (for OD-23, the `promoter` inlining question). No restatement, no dated note.
   - `ARCHITECTURE/StandardScenarios.md`: re-check S0, S1, S6 and S8 by §검사 규칙 and record the result exactly as the first paragraph of §검사 결과 says (a re-check with no verdict change leaves no dated line there).
8. Doc mode: reviewer cycle (dev-item-address steps 10 to 12), then rebase onto `origin/main` and push **one squashed commit** to `main` carrying `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0362`. Do not chain the rebase and the push in one command; check the rebase finished before pushing. Then post the DRIVER §9 owner notice on #5 with the `— posted by driver` footer and put its URL in the Result; give any runtime acceptance HQ text to the driver in the Result.

## Out of Scope

- Any code, test, CI, prompt, agent definition or settings change, including `orchestration/`, `hilclaw/` and `.claude/`.
- The selection side (ADR-0132, T-0361), the round steps beyond promotion (P2-1), the coder call (P2-2), the comparison and `eval.json` (OD-20), the lookup read tool.
- HQ-0043, HQ-0031, HQ-0040, HQ-0041 and every owner-only point (#5 A/B items, C-6, OD-25, OD-3).
- Editing earlier ADRs, FR/NFR text, UsageCases, the README or the index documents.
- Starting `claude` or any program that needs a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- Expected next for the planner if the record chooses a tool: the code slice (tool module and test file, `default_registry`, the `cases_file.py`/`cases.py` docstrings), then the definition slice with P2-1's round steps.
- If the record finds the key directory's creation (OD-26) is needed before a first-case run can store a case: an OD-26 record for first-case runs.

## Result

- **Outcome**: DONE. Document mode. ADR-0133 (`ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md`, 134 lines) landed on `main` as one squashed commit, 67b6d6a (`Reviewed-by: reviewer agent (6 rounds, Approve)`, `Task: T-0362`). The task branch was deleted locally and remotely. ADR-0133 was confirmed free on `origin/main` and every remote branch before the push.
- **Review**: 6 context-isolated rounds (dev-reviewer, dev-code-review).
  - Rounds 1, 2, 3, 5 and 6: Approve, with minor findings and nits; each one was addressed except the last.
  - Round 4: Request changes, because the record claimed the whole `promoter` role. It was narrowed to the case write; the writer of `best.json` and `technique_stats.json` stays open in the record and in the register.
  - Round 6's optional nit was not applied, to stay clear of the 7-round limit. It suggested citing `hilclaw/case_lookup.py` beside `key_records.lookup`. That is a hint for the code slice: `case_lookup.find` folds a collision into a report and also lists cases, so step ⑤ cannot reuse it as is.
- **What the record decides** (first-case runs only): the Round-Manager holds the case write inline and calls a new registry tool `case.write`.
  - Request and result: the request is `run_id` and `round`; the result is `with_verdicts`.
  - Checks, in order: request; data root; `STATE.json` `round` (`round_not_current`); `instance.json`; key stored (`key_not_stored`, `key_record_invalid`, `key_record_unreadable`); hypotheses (`hypotheses_*`); verdicts (`verdicts_invalid`, `verdicts_unsupported`, `verdicts_unreadable`; a missing file is no failure); pair rules (`verdicts_mismatch`); write (`case_exists`, `case_not_written`).
  - The tool is not journaled, and it widens ADR-0019 decision 2 the way ADR-0124 did.
  - Order: the case write comes right before the write that ends the round. A round with a valid hypothesis record is promoted with or without a verdicts file. A refusal does not stop the round from ending. HQ-0043 is not answered.
- **Register**:
  - `Requirements.md`: rows OD-23 and OD-30 (확정분 link and 잔여 rewritten).
  - `OpenDecisionProposals.md`: OD-23 and OD-30 (채택분 lines; the `promoter` inline question and 파일 자리 ③ states rewritten).
  - `StandardScenarios.md`: S0, S1, S6 and S8 re-checked with no verdict change. The 최근 재검사 line was updated, and the notes of S0 step 6 and S6 step 4 now name OD-26. OD-17, OD-26 and OD-29 rows were not edited (the record answers no part of them).
- **Runtime acceptance items (new)**: (xxv) and (xxvi). They are numbered after (xxii) on `main` and after (xxiii) and (xxiv) on the unlanded `claude/T-0361-*`. HQ text for the driver: "ADR-0133 (T-0362, main 67b6d6a) adds turn-session runtime acceptance items **(xxv)** the main session of a `-p` turn session sees `mcp__hilclaw__case_write` and may call it under the means item (vii) gets, and **(xxvi)** a live Round-Manager calls `case.write` once per round >= 1, after the round's verdicts work and before the write that ends the round, and goes on to that write after a failure. Under D16 these are closed by the owner's check by hand or the runtime's self-check; non-blocking."
- **DRIVER §9 owner notice**: not posted by the executor, per the driver's instruction not to post to #5. Text for the driver to post, ending with the `— posted by driver` footer: "### ADR-0133 accepted — T-0362: the case write of a first-case round's promotion step (part of OD-23 and OD-30) / Under PROCESS/DRIVER.md §9 the driver accepted ADR-0133 (main 67b6d6a; context-isolated review, 6 rounds, Approve). For first-case runs, the Round-Manager writes the round's case inline through a new registry tool `case.write`. It writes right before the write that ends the round, and only into a stored key directory. Rounds without a verdicts file are promoted; an invalid verdicts file gives no case. OD-23 and OD-30 stay 논의중/제안됨. Note: nothing creates a key directory for these runs yet, so no case is stored until an OD-26 record. You may object within 7 days."
- **Overlap**: the unlanded branch `claude/T-0361-adr-first-case-selection-hypotheses-write` (ADR-0132, HQ-0048) edits the same rows OD-23 and OD-30 in `Requirements.md` and the same sections in `OpenDecisionProposals.md`. Whichever of the two lands later will need a rebase there. `claude/T-0318-*` and `claude/T-0231-*` (OD-30) overlap the same way. None of their content was taken.
- **Follow-ups**:
  1. Code slice: the tool `case.write` with its test file, registered in `default_registry`, plus the `cases.py` and `cases_file.py` docstrings.
  2. Definition slice: the promotion step in "The round steps" of `orchestration/round-manager.md`, written with P2-1.
  3. **An OD-26 record for first-case runs**: who stores the two key record files (`key_records.store_*` has no caller), when, and how they enter a commit. Without it every `case.write` answers `key_not_stored`, so P2-7's storing half cannot store a case.
