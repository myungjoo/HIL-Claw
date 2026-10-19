---
id: T-0333
title: Write ADR-0120 — who writes the first runtime STATE.json of a first-case run, in which order against instance.json, and what a run directory with instance.json and no STATE.json means (OD-8 sub-question 10, for the runs of ADR-0076 decision 1)
phase: P2
status: DONE
commitMode: doc
coversReq: [FR-1, OD-8, OD-23, S0, S1, S2]
dependsOn: [T-0329, T-0332]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is still the first unchecked item of the P2 order (D18), and this is one of its slices, so the D18 priority rule does not apply. P1 has nothing plannable now:
- P0.5-4 waits on the owner's hook registration;
- the rest of P1-1 waits on HQ-0021, HQ-0025, HQ-0026 and OD-14 ①;
- P1-8's D18 completion criterion is the driver's to tick.

T-0332's Result names the round-0 part of `orchestration/round-manager.md` as the next slice and says it still waits on OD-18 ⑯ (가), OD-8 ⑩ and ⑪, and the baseline's record. Of these, OD-8 ⑩ comes first in time: nothing in a new run can happen before a first `STATE.json` exists, and the P2-5 run (`cpu_standin` × GEMM, N=1, 5 rounds) cannot start without an answer. Today:
- ADR-0012 decision 2 fixes what the first file holds (`round` 0 and the start values of decision 4) and that a missing file means "no round has begun", but not who writes it.
- ADR-0013 decision 6 fixes how the first file is written, and leaves open "who writes the first file; when, in relation to `instance.json`; and what a run directory means that holds other files, or nothing, but not this one".
- ADR-0004 gives `STATE.json` to "Round-Manager only (#4 roster revision)" and `instance.json` to the start of the instance.
- ADR-0115 makes one layer-2 function the start of a first-case instance and says that if a later record lets the start write `STATE.json`, that record says whether the function does so.
- ADR-0118's Walk-through, first row, has the loop start the round-0 turn and leaves "which side writes the first `STATE.json`" to OD-8 ⑩.
- ADR-0109 decision 5 and ADR-0111 decision 5 hand their findings on the order of the first files to ⑩.

OD-8 is a design-level OD and not on the owner-only list of DRIVER §9, so this task writes the ADR that closes the first-case part of ⑩ by the §9 path. The ADR is a document; the code that follows from it (in the start function, the turn loop or the Round-Manager prompt) is a later task. ADR-0120 is the next free number on `origin/main`; ADR-0112 is held by the unlanded branch of T-0318.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0333` trailer, size cap;
  - §9 (lines 142-149): the ADR path and the owner notice on #5.
- `CLAUDE.md`, these rules: "미결은 발명하지 않는다", "세션 진입 점검", "문서 커버리지 재검사", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/Requirements.md`: FR-1 (line 19); the "행 형식" paragraph (line 84); register rows OD-8 (line 99), OD-17 (line 108), OD-19 (line 110), OD-23 (line 114).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header, in particular its "기록 규칙" bullet (lines 1-10); § OD-8 (lines 87-163), in particular sub-questions ⑩-⑬ (line 129), ⑰ (line 132), ㉓ (line 137) and ㉗ (line 141).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-26); S0, S1, S2 (lines 30-75); the first paragraph of §검사 결과 and the "최근 재검사" line (lines 168-172); the S0, S1 and S2 rows of the verdict table (lines 186-189).
- `ARCHITECTURE/UsageCases.md`: UC-0 and UC-1 (search `UC-0`, `UC-1`), for what a start of an instance is to a user.
- Accepted records:
  - ADR-0001 "Record format" (from line 146), the format to follow;
  - ADR-0004: the file tree and the path table (lines 25-70), and the sentence on writers (line 104);
  - ADR-0012: decisions 2-3 (lines 29-56), Boundaries (lines 142-152);
  - ADR-0013: decision 2 (lines 29-48) and decision 6 (lines 77-83);
  - ADR-0025: decision on creating the run directory (line 57) and Alternatives row 5 (line 100);
  - ADR-0030: decision 3 (lines 41-52) and the Consequences line 100 ("No call passes ⓢ for a run before its `instance.json` is under its final name");
  - ADR-0076 decision 1 (lines 25-30), the scope "first case";
  - ADR-0109 decisions 4-5 (lines 45-56);
  - ADR-0111 decision 5 (lines 51-54);
  - ADR-0115: Decision 1-2 and Boundaries (lines 46-80, 137-149);
  - ADR-0118: decision 3 and Walk-through (lines 67-134), and Boundaries (lines 186-200);
  - ADR-0119 Boundaries (search "first `STATE.json`").
- Code, read only (this task changes no code): `hilclaw/run_state_file.py` (`replace`, line 53) and `hilclaw/turn_loop.py` (how step 1 asks the caller's predicate).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md).
   - Run `gh pr list` and read issues #4, #5, #7 and #8 for OD-8 ⑩ and the first `STATE.json`.
   - Open Draft PR #186 (T-0324) touches only `hilclaw/` and `tests/`, none of this task's files.
   - If an open PR edits the OD-8 row, § OD-8, the S0/S1/S2 rows or the "최근 재검사" line, stop and report.
   - Check with `git ls-tree` that `ADR-0120` is free on `origin/main` and on every remote branch. If it is taken, take the next free number, rename the file and its touchesFiles entry, and say so in Result.

2. **Owner-sentence search, before writing any decision.**
   - Search #4 (body and comments), the comments of #5 without the "posted by driver" marker, #7 and #8. Use English and Korean terms: first STATE.json, STATE.json, Round-Manager, roster, instance start, 첫 STATE, 라운드 0, 시작, 로스터.
   - List in Status the sentences that touch the point, each quoted for what it says and no further.
   - Say whether the "Round-Manager only" writer of `STATE.json` in ADR-0004 (its "#4 roster revision") is an owner sentence or an integrator's, and treat it as what it is.
   - **Write no ADR and return BLOCKED (`requirement-unclear`) with the question** if:
     - an owner sentence decides the point differently or reads two ways about it; or
     - the only answer that holds needs a writer other than the Round-Manager and that writer rule is an owner sentence; or
     - the choice needs an owner-only item: #5 A/B, C-6, OD-25 or OD-3.

3. **New `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`**, in the ADR-0001 record format and in English: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References. Mark each sentence as cited (source named) or as this record's own. Scope is **the runs of ADR-0076 decision 1** only, started by the function of ADR-0115.
   - It decides at most these three points of ⑩. Each point it does not decide is named in Boundaries.
     - **(a) Who writes the first `STATE.json`.** Consider at least: the start function of ADR-0115 (after `instance.json`), the turn loop of ADR-0118 before the round-0 turn, and the Round-Manager of the round-0 turn. Each candidate goes in Alternatives with what it would contradict or leave open: ADR-0004's writer row; ADR-0115's "no judgement"; ADR-0118 decision 3's "makes no judgement"; FR-1's round 0. Writing goes through the ADR-0013 steps (`hilclaw.run_state_file.replace`); the record does not restate them.
     - **(b) The order against `instance.json`.** Use the findings of ADR-0109 decision 5 and ADR-0111 decision 5, and ADR-0030 decision 3, as the grounds. Cite them; do not restate them.
     - **(c) What a run directory that holds `instance.json` and no `STATE.json` means**, and whether the turn loop takes it up as a run whose round 0 has not begun (ADR-0012 decision 2: a missing file means no round has begun). A directory with neither file, or with other files only, may be answered only to the extent that (a) and (b) settle it. Otherwise it is left open.
   - **Not decided:**
     - the caller of the start function and whether the loop calls it (ADR-0115 decision 1; ADR-0118 decision 3);
     - the predicate of the loop's step 1 and the member that says a run is over, stopped or waiting (rest of OD-8, OD-19);
     - the commit of the first files and of round ends (⑪);
     - the lock of two loops or two starts on one run (rest of OD-17);
     - the self-check in round 0 (OD-18 ⑯ (가));
     - a top-level member the writer does not know (⑫);
     - runs outside ADR-0076 decision 1, and resumed or branched runs (①).
   - **No member, file, kind, value or version of the data plane is added or changed.** The first file holds what ADR-0012 already says. If the decision cannot be stated without such a change, stop and return BLOCKED (`data-plane schema change`).
   - Consequences:
     - search `ARCHITECTURE/decisions/` for "⑩" and "first `STATE.json`". List the accepted records whose sentences are now less exact, as integrator follow-ups; do not edit them;
     - name the code slice that the decision enables (which module would write the first file, or which part of the Round-Manager prompt) and what that slice still waits on;
     - list runtime acceptance items only if any exists (D16).
   - About 150-220 lines. No dated paragraphs.

4. **`ARCHITECTURE/Requirements.md`, OD-8 row only**, edited by that file's "행 형식" rule (line 84). Mark the edit as a partial answer, by the §9 path, with the 7-day objection period. Edit no other row and no FR text.

5. **`ARCHITECTURE/OpenDecisionProposals.md`, § OD-8 only**, edited by the "기록 규칙" bullet of that file's header. Sub-question ⑩ is rewritten in place to say what remains. Touch ⑰, ㉓ or ㉗ only where the new ADR answers part of them, and say which in Result.

6. **`ARCHITECTURE/StandardScenarios.md`** (CLAUDE.md "문서 커버리지 재검사"). Re-check S0, S1 and S2 by §검사 규칙. Record the result as the first paragraph of §검사 결과 prescribes. In the S0, S1 and S2 rows, change only the OD pointers that the ADR narrows.

7. **Scope.**
   - `git diff --stat origin/main` lists only touchesFiles, plus this task file's Result.
   - No edit to: FR or NFR text, UsageCases, earlier ADRs, `orchestration/`, `hilclaw/`, tests, CI, `.claude/`, `CLAUDE.md`, README, or other `PROCESS/` files.
   - No new dependency.

8. **D16.** Neither the executor nor the reviewer starts `claude` (no subcommand, no flag). Nothing here needs a board, an accelerator or an API key.

9. **Merge (document mode, CLAUDE.md A-13).**
   - Branch `claude/T-0333-adr-od8-first-state-file`.
   - Context-isolated reviewer cycle (dev-code-review), at most 7 rounds, until Approve.
   - Rebase on `origin/main`. Push to main with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0333`.
   - Then post the OD-8 notice on #5 (DRIVER §9; its last line is `— posted by driver`) and put its URL in Result.

## Out of Scope

- Code: the writer of the first file in `hilclaw/` (including `hilclaw/start_instance.py` of Draft PR #186), the turn loop's command-line entry, and the round-0 text of `orchestration/round-manager.md`. These are the next slices.
- OD-8 ⑪ and ⑫, the run-status member, OD-17's lock, OD-18 ⑯ (가), OD-19, and HQ-0032's question (a given id).
- Edits to earlier ADRs that this record makes less exact, and integrator follow-ups of ADR-0118 and ADR-0119.
- Anything in PLAN's 보류 section, and anything blocked by HQ-0021..HQ-0029, HQ-0031, HQ-0032 or HQ-0034.

## Follow-ups

- The code slice that writes the first `STATE.json` where the ADR puts it, with tests against a stub `claude` where the turn loop is involved (D16).
- The remaining P2-1 slices: OD-18 ⑯ (가) (self-check in round 0), OD-8 ⑪ (commit step), the run-status member (rest of OD-8, OD-19), then the round-0 part of the Round-Manager prompt.

## Result

**DONE.** Landed on `main` as 1386ace, one document-mode commit (subject `T-0333: add ADR-0120 ...`, trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0333`); the branch `claude/T-0333-adr-od8-first-state-file` is deleted (local and remote). OD-8 notice on #5 (DRIVER §9): https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6262794405

- **Session entry check**: open PRs = #186 only (`hilclaw/`, `tests/`), none of this task's files. `ADR-0120` was free on `origin/main` and every remote branch; no rename.
- **Owner-sentence search**: #4 body and 6 comments, #5 body and the 38 of 190 comments without the driver marker, #7 (2) and #8 (6). No owner sentence decides the writer, the order or the meaning. The "Round-Manager only" writer of ADR-0004 comes from the #4 §3a revision, condition 2 (owner account, "[합의]"); ADR-0120 treats it as an owner sentence and its answer holds under both readings of it, so no BLOCKED. UC-1 step 2 ("STATE를 초기화한다" before round 0) is kept.
- **Decision** (ADR-0120, first-case new runs only): (a) the Round-Manager of the round-0 turn writes the first `STATE.json` as its first write into the run; the start function and the turn loop write no `STATE.json`. (b) `instance.json` comes first: the first file is written only into a fresh run directory (`instance.json` and no other file of the tree). (c) A fresh run directory is a started run whose round 0 has not begun, and the loop takes it up; other directory states stay open. No data-plane change.
- **Register/proposals**: Requirements OD-8 row (확정분 link, 잔여 rewritten; status cell already covers the §9 path and the 7-day objection period). OpenDecisionProposals § OD-8: 채택분 line, ⑩ and ㉓ (가) rewritten in place, and the "쓰기와 작성자" item of the open proposal bullet; ⑰ and ㉗ not touched (not answered).
- **StandardScenarios**: S0, S1, S2 re-checked: no verdict change, no gap; no OD pointer of the three rows changes (S0 and S2 have no ⑩ pointer; S1's ⑩ pointers concern runs outside the first case). "최근 재검사" line updated.
- **Review**: 7 rounds (dev-reviewer, document mode); round 7 Approve. The ADR is 142 lines of long lines (target about 150-220); the reviewer judged the content sufficient.
- **Follow-ups**:
  - Round-7 nits, not addressed to stay within the 7-round cap: narrow decision 3's "a check of existence is all this decision asks" to the order, and note in slice (1) that telling the scope reads `instance.json` (ADR-0076 decision 1; stamp = ㉗ (가)); add ADR-0019 (decision 3) and ADR-0025 (decisions 3, 6) to the Status "builds on" list.
  - Integrator: the less-exact sentences listed in ADR-0120 Consequences (ADR-0012, 0013, 0018, 0019, 0022, 0025, 0027, 0029, 0030, 0051, 0059, 0071, 0076, 0109, 0111, 0115, 0118, 0119 and the writer Boundaries of 0020-0034, 0053) and the docstrings of `hilclaw/run_state_file.py`, `instance_file.py`, `run_journal.py`.
  - Code slices: the round-0 entry of `orchestration/round-manager.md` (and optionally a layer-2 helper that writes the start values into a fresh directory), waiting on how the Round-Manager reaches `replace` (OD-23/OD-18), ⑪, OD-18 ⑯ (가) and the baseline record; the fresh-directory part of the loop's step-1 predicate.
