---
id: T-0414
title: Write ADR-0151 - the spec of the first coder call of a round >= 1 in a first-case run with one candidate per round: the source of each member, how the writer turns catalog ids into guidance.techniques, which earlier attempts feedback shows and how, and the widening of spec.write (rest of OD-6, part of OD-23; PLAN P2-2, for P2-5)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-1, FR-5, FR-8, FR-17, OD-6, OD-22, OD-23, "PLAN P2-2", "PLAN P2-5"]
dependsOn: [T-0412, T-0413]
touchesFiles: [ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 260, files: 4}
hq: []
---
## Why

**Where PLAN P2 stands** (as of `main` `0b30e82`):
- PLAN P2 runs its items in the listed order: P2-1 to P2-4, P2-6, P2-7, then P2-5 (PLAN, P2 head).
- P2-4's only open part is the gate half. It is owner-only (OD-3, #5 A-5; T-0411 Result).
- Each other open part in the way of a round >= 1 is held by an open HQ:
  - the selection role and the writer of `decision/hypotheses.json`: unlanded ADR-0132, HQ-0048;
  - the coder's container start: unlanded ADR-0137, HQ-0053;
  - `sim.run`, `board.run` and the `cpu_standin` operations: HQ-0021, HQ-0026.
- ADR-0150 (T-0412) and its code slice (T-0413, `hilclaw/catalog.py`, `catalog/cpu_standin/`) have landed. T-0412's planner follow-up names the next item: "the round >= 1 spec record (rest of OD-6) can name catalog ids; its selection half still waits on HQ-0048".

**The gap this record fills.**
- A coder call of a round >= 1 needs a spec. The coder's whole input is that spec (ADR-0002 decision 1).
- Today a spec can be written for one tuple only: round 0, candidate 1, attempt 1. `spec.write` refuses every other tuple with `invalid_request` (ADR-0138 decisions 1 and 3).
- ADR-0138 Boundaries and ADR-0150 Boundaries leave the rest to "rest of OD-6":
  - the specs of later rounds;
  - the selection of `feedback`, `feedback.base` and profiles;
  - how `{id, text}` reaches `spec.write`, and what checks ADR-0150 decision 4's rule when a spec is composed.
- Without this record, no round >= 1 of P2-5 can have a coder call, whatever HQ-0048 answers. The record is also P2-2's "spec 전달" for later rounds.

**This is a PLAN checklist item (P2-2 "spec 전달"), so the D18 deferral rule does not apply.** It also serves P2-5 (S1 steps 4 to 6). The reviewer is asked to confirm that this record crosses none of the open HQs (criterion 4).

**What must stay outside, and why.** Which technique ids a round's spec carries, who chooses them, and how the choice reaches the coder-driver are the selection side's (HQ-0048; ADR-0150 decision 4 "Not decided here"). This record may decide only the **writer's end**: the form in which ids are handed to the writer, and what the writer does with them (look them up with `hilclaw.catalog`, check ADR-0150 decision 4's rule, copy `{id, text}`). If the executor finds that even this crosses HQ-0048, the record leaves the technique list's source open, and says so (criterion 3 (c)).

**Not owner-only.** No #5 A or B item, C-6, OD-25 or OD-3 is decided. Nothing of OD-31 is touched. The open owner HQs are cited, not answered: HQ-0048, HQ-0053, HQ-0021, HQ-0026, HQ-0031, HQ-0034 and HQ-0032.

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED) touches `hilclaw/start_instance.py` and three test files only.

**D16.** Nothing here starts `claude` or a container, or needs a board or an API key. A fact that only a live turn session can show becomes a runtime acceptance item, numbered from **(lxvii)**. The last item on `main` is ADR-0148's (lxvi); ADR-0149 and ADR-0150 added none.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0414-<slug>`, trailer `Task: T-0414`);
  - §8 (lines 136-142): HQ form, used only if you return BLOCKED;
  - §9 (lines 144-151): OD closing authority and the #5 notice with the `— posted by driver` footer.
- `CLAUDE.md`, 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode; BLOCKED reasons, data-plane schema change among them).
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md`, all 144 lines. It is the direct model: scope (decision 1), member source table (decision 2), `spec.write` (decision 3: request, result, checks in order, kinds, not journaled), Alternatives, Consequences, Boundaries. Do not copy its wording; follow its structure where it fits.
- `ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md`:
  - decisions 1 to 5 (lines 21-90): the spec's members, the `feedback.attempts` entry (`round`, `candidate`, `attempt`, `techniques`, `failure {stage, report}`, `profile`), `feedback.base`, and the repair call;
  - the "No field carries verification inputs" rule (line 71);
  - Boundaries (lines 161-171).
- `ARCHITECTURE/decisions/ADR-0150-od22-first-case-technique-catalog.md`:
  - decisions 1 to 4 (lines 48-83). Decision 4 gives the rule an entry's spec must meet and the "Not decided here" list.
  - Boundaries (lines 150-160).
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md` decisions 1, 3, 4 and 5 (lines 20-87): a hypothesis names no technique; hypotheses and candidates; round 0 has no record.
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md` decisions 3 and 4 (lines 43-64): the call function takes the spec as written (`spec_unreadable`); the `coder/` role is the coder-driver's.
- `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md` decision 6 (around lines 85-99): the round-0 delegation and the stop that follows step 1 in other rounds.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: path table (lines 60-78) and decisions 3 and 4 (lines 86-105). They give where an attempt's spec and measurement results live.
- Sources of `failure` and `profile` for earlier attempts. Read what each decides, and only as far as you need it:
  - `ADR-0063-od18-run-tools-result-members.md` decisions 1 to 7: the members of a `sim.run`/`board.run` result, i.e. timing samples and the memory figure;
  - the owner's answer to HQ-0025 as ADR-0144 Context line 24 cites it: on `cpu_standin` the profile is what `sim.run`/`board.run` return;
  - `ADR-0060-od18-correctness-check-build-answers-and-settings.md` decision 4 (build answers) and `ADR-0078-od18-correctness-check-compiler-log-file.md` (the compiler's log file). Its code slice is held by HQ-0026; the design is on `main`;
  - `ADR-0131-od23-attempt-check-results-read.md` decision 3 (`checks.read`) and `ADR-0140-od16-first-case-attempt-comparison.md` decisions 3 and 4 (`timings.compare`): what the run's journal holds of an attempt and how it is read today.
- `ADR-0029-od8-spec-file.md` decision 4 and `ADR-0051-od6-spec-file-version-2.md` decision 3: the write's steps and the one version written.
- Code, as observation only: `hilclaw/spec_tool.py` (314 lines: `_checked`, `_admitted`, `_compose`), `hilclaw/catalog.py` (`check`, `technique`, module docstring), `hilclaw/spec.py` lines 60-130 (`validate`, `_technique`).
- **Not a source**: the unlanded draft ADR-0132 on branch `origin/claude/T-0361-adr-first-case-selection-hypotheses-write` (`git show <branch>:ARCHITECTURE/decisions/ADR-0132-od23-first-case-selection.md`). You may read it only to avoid a collision. Its decision 6 puts the record of a round >= 1 before the round's first spec write; its Boundaries line 146 leaves "how a spec is composed from the record" to rest of OD-6. Do not cite it, rely on it, or decide anything it decides.
- `PROCESS/STATE.json` `humanQuestions`: HQ-0048, HQ-0053, HQ-0021, HQ-0026, HQ-0031, HQ-0034. Read each `question`, so that you cite them and do not answer them.
- Register rules. Follow them; do not copy earlier task files' wording:
  - `ARCHITECTURE/Requirements.md` line 84 ("행 형식"), with the OD-6 row (line 97), the OD-22 row (line 113) and the OD-23 row (line 114);
  - `ARCHITECTURE/OpenDecisionProposals.md` line 9 ("기록 규칙"), with § OD-6 (lines 59-77), § OD-22 (from line 401) and § OD-23 (lines 410-438);
  - `ARCHITECTURE/StandardScenarios.md`, the first paragraph of § 검사 결과 (line 170) and the "최근 재검사" line (line 172), with the coverage rules near line 26.

## Acceptance Criteria

### The record `ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md`
1. **Status.** It has:
   - the §9 acceptance line ("written by the development driver's executor, accepted by the approval of a context-isolated reviewer; the owner has not confirmed it");
   - the split between **cited** content (owner decisions, requirements, scenarios, accepted records, code docstrings, each with its source) and the record's **own** content;
   - an owner-sentence search (#4, #5 without driver-posted comments, #7, #8) with its terms and the sentences found, each read for what it says and no further;
   - "It builds on" with decision numbers;
   - "Answers" stating which part of rest of OD-6 (and of OD-23, if any) is answered and for which runs;
   - an explicit statement that **no member, file, kind, value or version of the data plane is added or changed and no validator changes** (new failure kinds of a tool's result are not data plane, as ADR-0138 reads them). If the design you find needs a data-plane change, stop and return BLOCKED (A-13), with the change described in `Result`.
2. **Scope (decision 1).** Exactly one spec: that of the first coder call (`candidate` 1, `attempt` 1) of a round `r` >= 1, in a run of ADR-0120 decision 1 whose `instance.json` states `candidates_per_round` 1. Outside:
   - round 0, which stays ADR-0138's;
   - repair attempts (`attempt` > 1);
   - other candidates and runs whose N is not 1;
   - everything under Boundaries.

   State what the record gives a run whose hw_profile names the mock, for which ADR-0150 gives no catalog. Choose, with the reason: either the technique list is always empty, or such a spec is refused.
3. **The source of each member (decision 2)**, in a table like ADR-0138 decision 2. Every member of a version-2 spec gets a source and the record that makes it right. In particular:
   - (a) `id.*`, `hw_profile`, `task.*` and `ext`. Say whether they are taken as in ADR-0138, and why. `id.round` is `r`.
   - (b) `guidance.techniques`. An entry is `{id, text}`, given by `hilclaw.catalog.technique` for the run's accelerator (ADR-0150 decisions 2 and 4). The writer checks ADR-0150 decision 4's rule against the spec it composes. State what the writer does:
     - when an id is unknown or does not apply;
     - when the same id appears twice;
     - when the catalog directory fails its check;
     - how the order is kept;
     - whether a list may be empty, and how long it may be.
   - (c) **The source of the ids.** Decide the form in which they reach the writer (for example a member of the `spec.write` request). Do **not** decide who chooses them, by what criteria, or how the choice reaches the coder-driver; those are the selection side's (HQ-0048). If you judge that any writer-end form crosses HQ-0048, leave the source open and say so. Then the record states what a round >= 1 spec carries until the selection record exists (for example an empty list), with the reason and the cost. Do not invent a placeholder id (ADR-0138 Alternatives (f)).
   - (d) `feedback.attempts`. State which earlier attempts are shown (all, the previous round only, or another rule; the contrastive top-k/bottom-k proposal of § OD-6 may be adopted for this scope, rejected or left open, with the reason) and in what order. For each entry, give the source of:
     - `techniques`: the ids of that attempt's own spec;
     - `failure`: `stage` and `report`;
     - `profile`.

     Where the only source of a member is code or a record held by an open HQ (HQ-0021: the run tools' operations; HQ-0026: the compiler log's code slice), name the landed design that defines it and state the dependency. Do not answer the HQ. If an optional member (`profile`) cannot be sourced, say whether it is left absent and what that costs. A required member (`failure` of a failed attempt) must have a stated source, or the record must say why such an attempt is not shown. ADR-0002's "No field carries verification inputs" rule binds every report and profile.
   - (e) `feedback.base`. Name the attempt the call starts from for this scope, or keep it absent, with the reason. Lineage stays OD-20's. Do not decide what "best" is beyond what landed records state.
   - (f) `repair` absent. `task.build` absent unless a landed record says otherwise.
4. **What composes and writes it (decision 3).** Say whether `spec.write` is widened (preferred: one writer for every spec of these runs) or another means is adopted, weighed in Alternatives. If widened, give:
   - the new request (members, which are required for which tuple, and what stays `invalid_request`);
   - the result;
   - the checks in order, with what each reads (the run's `instance.json`; earlier attempts' specs; journal lines; the catalog) and that every check before the write creates nothing;
   - the kinds: reused kinds with their meanings, and new kinds named and defined;
   - whether `id.round` is held against `STATE.json`. That check is open in ADR-0138 Boundaries; decide it or leave it, with the reason;
   - "not journaled", or why it now is.

   The coder-driver keeps the `coder/` role (ADR-0126 decision 4). **Do not** define:
   - the Round-Manager's round >= 1 steps;
   - the coder-driver's round >= 1 delegation;
   - `coder.run` for round >= 1;
   - anything ADR-0132's draft decides.

   Name these in Boundaries.
5. **Walk-through.** A table of situations, at least:
   - round 1 after a round 0 whose attempt passed;
   - round 1 after a round 0 whose attempt failed to build;
   - a later round with several earlier attempts;
   - an unknown or non-applicable technique id;
   - a mock run;
   - a request for `attempt` 2;
   - `spec_exists` after a dead turn;
   - an `instance.json` changed after the start.
6. **Alternatives considered.** Include:
   - ids read from a run file instead of the request (no file names a round's techniques: ADR-0059 decision 3; adding one is a data-plane change);
   - the coder-driver composing `text` itself;
   - a separate tool for later rounds;
   - each `feedback` selection rule weighed;
   - folding composition into the coder-call function (ADR-0138 decision 4's reason).
7. **Consequences.**
   - Code slices for the planner, each within the D4 cap, tested with fixture files only, no `claude`. Name what each changes, for example `hilclaw/spec_tool.py` and its tests.
   - Runtime acceptance items from **(lxvii)**, or "none" with the reason.
   - "Less exact, not edited": found by a search of `ARCHITECTURE/decisions/` and `hilclaw/` for sentences this record makes less exact, for example ADR-0138's "no record defines that spec yet" and `spec_tool.py` docstrings.
   - The A-13 reading: document mode, no data-plane schema change.
   - UsageCases and StandardScenarios effects.
   - "The cost, plainly".
8. **Boundaries.** List what is not decided:
   - the selection side and its means (HQ-0048);
   - the Round-Manager's round >= 1 steps (P2-1);
   - the coder call of a round >= 1 and the coder's start (HQ-0053);
   - repair specs and their limit (OD-19);
   - N > 1 (OD-29);
   - the profile summary structure (B4), (S7) and (B5) beyond what is adopted;
   - lineage and `best.json` (OD-20);
   - statistics (OD-7);
   - injected inputs and cases in a spec (FR-15, HQ-0031; ADR-0073);
   - OpenMP (HQ-0034);
   - other kinds, dtypes, layouts and languages, and OD-31;
   - the run tools' and compiler log's open code (HQ-0021, HQ-0026).
9. **References** section with every cited source (ADR file links and #5 comment URLs).
10. **Mark your own choices.** Every value or rule that no source gives is marked as the record's own choice, with its reason. Nothing is presented as an owner decision unless a cited owner sentence says it (CLAUDE.md "미결은 발명하지 않는다").

### Register and coverage updates
11. `ARCHITECTURE/Requirements.md`. Follow "행 형식" (line 84): in the OD-6 row, add one `**확정분**` link with a few words and rewrite `**잔여**` in place. Touch the OD-23 row (and OD-22's) only if this record answers part of it, the same way. Status cells keep their status word and a short date/path. No restatement of the record, no dated chain.
12. `ARCHITECTURE/OpenDecisionProposals.md`. Follow "기록 규칙" (line 9):
    - in § OD-6, add one `- **채택분** [ADR-0151](…) — …` line;
    - rewrite the end of each sub-question or open-part sentence this record answers in place (`→ 부분 답: … 남음: …` / `→ 답함: …`);
    - do the same in § OD-23 and § OD-22 only where they are answered;
    - write no dated paragraph.
13. `ARCHITECTURE/StandardScenarios.md`. Re-check coverage by its rules (S0, S1 and any scenario the record touches) and update the "최근 재검사" line in place. Add a "판정 변화 이력" item only if a verdict changes or a gap appears or closes (the first paragraph of § 검사 결과).

### Process checks
14. Before the review, check:
    - `git diff origin/main --stat` lists only `touchesFiles`;
    - `git diff origin/main -- hilclaw tests orchestration catalog .claude .github PROCESS pyproject.toml` is empty, except this task file's `Result` if the executor prompt has it written on the branch;
    - the new file is LF (`git ls-files --eol` after staging).

    Record the changed line count; the cap is 300 LOC in 5 files. If the record outgrows it, narrow the scope (for example leave `feedback.base` or the selection rule open) rather than split the file. Say what was narrowed in `Result`.
15. Run the reviewer cycle with a fresh-context `dev-reviewer` (dev-code-review, document-mode return path), for at most 7 rounds. Ask the reviewer explicitly to:
    - (a) find any sentence that decides something HQ-0048, HQ-0053, HQ-0021, HQ-0026, HQ-0031 or HQ-0034 leaves to the owner or to an unlanded record, including anything of draft ADR-0132;
    - (b) check that no member, file, kind, value or version of the data plane changes;
    - (c) check every row of the member table against ADR-0002 decisions 2 to 5, ADR-0150 decision 4 and ADR-0059 decision 3;
    - (d) check that each "this record's choice" is marked and each citation says what it is cited for;
    - (e) check the register edits against "행 형식", "기록 규칙" and the § 검사 결과 rule;
    - (f) re-check the D18 reading in Why.

    A finding that starts with `SECURITY` is BLOCKED.
16. On Approve, land in document mode (CLAUDE.md A-13):
    - rebase on `origin/main`;
    - one commit with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0414` trailers;
    - push to `main` directly (no force push);
    - delete the branch;
    - post the DRIVER §9 notice on #5: the record, the OD parts it closes, the 7-day objection window, and the last line `— posted by driver`.

    Record the landed commit and the notice URL in `Result`.

## Out of Scope

- Any code: `hilclaw/spec_tool.py`, `hilclaw/catalog.py`, `hilclaw/coder_tool.py`, tests and `orchestration/`. The code slices are later tasks.
- The selection side: the technique-selector, `hypotheses.write`, a `Skill`, and who chooses technique ids (HQ-0048). The Round-Manager's round >= 1 steps. `coder.run` for round >= 1. The coder's container and sign-in (HQ-0053).
- Repair specs, N > 1, statistics and ranking (OD-7), lineage and `best.json` (OD-20), cold-start methods (OD-22 rest), and catalog entries or their texts.
- Any data-plane member, file, kind value or version. Any edit of `PROCESS/` other than this task's `Result`, `.claude/`, `.github/`, settings files or the `HIL-Claw-data` repository.
- Editing earlier ADRs. Sentences they make less exact are listed under "Less exact, not edited".

## Follow-ups

- (planner) If the record widens `spec.write`, its code slice(s) are the next tasks (PLAN P2-2), each within the D4 cap. The Round-Manager's round >= 1 steps and the coder-driver's round >= 1 delegation still wait on HQ-0048 and HQ-0053.

## Result

- (executor fills)
