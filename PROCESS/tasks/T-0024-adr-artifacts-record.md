---
id: T-0024
title: Write ADR-0005 fixing the blob record of artifacts.json (a part of the rest of OD-8, for PLAN P1-6) and reflect it in the ARCHITECTURE documents
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, C-3, FR-6, FR-13, NFR-2, NFR-7, "#5 A-2", "#5 D6"]
dependsOn: [T-0008, T-0021]
touchesFiles: [ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md, ARCHITECTURE/UsageCases.md]
estimatedSize: {loc: 170, files: 5}   # one new record of about 90-130 lines, the rest are in-place edits of a few lines each
hq: []   # the fields of the files of ADR-0004 are the registered rest of OD-8, a design-level OD (DRIVER §9: not among #5 A/B items still open, C-6, OD-25, OD-3); C-3 / #5 A-2 is an answered owner item and is taken as a fixed input
---
## Why
C-3 (owner decision #5 A-2) says that binaries live in the content-addressed store `blobs/sha256/<hh>/<hash>` outside git and that git holds only `artifacts.json` records with "hash, size, type, producing round, retention class"; a GC later writes `gc_at` into the record. ADR-0004 (`ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`) decision 6 fixed the **place**: one file per run, `runs/<run_id>/artifacts.json`, one record per blob the run produced, written by the tool layer together with the blob store. It fixed **no field**: its path table says "Fields: PLAN P1-6; retention and GC: C-3", and its Boundaries and the OD-8 register row list "각 파일의 필드·스키마" as the open rest of OD-8.

So the five members are named by the owner, but nothing says how a record is written down: the member names and value types, the shape of the file, what "type" may hold, how the producing round is expressed, what identifies a record, and which changes a record may undergo. `hilclaw/cas.py` (T-0008) stores blobs and returns `BlobRef(digest, size)` but writes no record; `hilclaw/layout.py` (T-0022) builds the path of `artifacts.json` but touches no file. The remaining code slice of PLAN P1-6 (the record writer and validator) cannot be written without these choices, and every earlier planner note stopped here: "the `artifacts.json` record defines new data-plane fields and needs an ADR first or an HQ" (journal 2026-10-06, T-0023).

Owner decision D6 (DRIVER §9) lets the driver close **design-level** ODs by a decision record (ADR) + a context-isolated reviewer's Approve + an owner notice with a 7-day objection window. This task writes that record for **one part of the rest of OD-8: the blob record of `artifacts.json`** and keeps the ARCHITECTURE documents consistent with it. It is a prerequisite slice of PLAN P1-6 and ticks **no PLAN checkbox**. The validator and writer are a later code task.

Why this item now (planner's judgement, DRIVER §6, 2026-10-07):
- Phase P0.5 has no actionable item: P0.5-3 is BLOCKED on HQ-0003 (T-0014, unanswered on #5); the C gate of P0.5-1 waits for P1-2 / P1-3; the rest of P0.5-4 is the owner's hook registration, and the forbidden-command guard needs the owner's word on its tests (T-0007 Follow-ups).
- In P1: P1-3 is marked "오너 확정 필요" and is skipped, and with it P1-4, the rest of P1-2 and P1-5 slice 3. P1-1 needs request / result shapes that hang on OD-10 / 13 / 18 / 23. The P1-8 schemas (`STATE.json`, `instance.json`, `events.ndjson`) touch OD-17, OD-11 and gate fields of the owner-only OD-3.
- The `artifacts.json` record is the one remaining file whose members the owner has already named (C-3), and it depends on no owner item that is still open.
- No open PR at planning time; the latest comment on #5 is the ADR-0004 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6021138854, 2026-10-06T16:52Z); no objection to ADR-0001..0004.

Planner's judgement that this slice is design-level and hangs on no open owner item — the reviewer is asked to re-check it:
- DRIVER §9 lists the owner-only items (#5 A/B items, C-6, OD-25, OD-3). #5 A-2 is **answered**; this record adds nothing to the owner's answer and must not contradict a word of it. How the five named members are spelled and typed is not "a fact or value judgement only the user has".
- Next to it and untouched: #5 B-2 (the backend of `blob.push` / `blob.fetch`), #5 A-3 (push is never automatic), the GC tool and the grace period (C-3: "MVP는 class 기록만 하고 GC 도구는 후속"), OD-25, #5 B-8, C-6.
- If the executor finds that a record member cannot be defined without one of those, that is BLOCKED, not a gap to fill.

A-13 check (planner's reading): "데이터 plane 스키마 변경(STATE/spec/eval/artifacts)" names `artifacts`. As with ADR-0002 for the spec, this is the **first definition** of that schema along the D6 route, in document mode, with no schema file and no code; the reviewers of T-0017 and T-0018 read the BLOCKED reason as not applying to a first definition. Ask the reviewer explicitly; if the reviewer reads it differently, return BLOCKED with the question instead of arguing it out.

Known risk, accepted: ADR-0001..0004 are inside their 7-day objection windows (notices of 2026-10-06). This record builds on ADR-0004 decision 6 and on the `id.round` of ADR-0002; its Status must say that it is revisited if either is reverted.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) — mandatory for every task (§6)
- PROCESS/DRIVER.md §0 last bullet, §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §8 (the driver tail on #5 comments), **§9 (the whole section)**, §11 row D6
- CLAUDE.md — 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", **"세션 진입 점검"** (before the first edit: `gh pr list`, issues #4, #5, #7, #8), "세 층 모델", "브랜치·merge 절차" (document mode and the BLOCKED reasons); "현재 프로젝트 상태 주의사항" (바이너리 금지)
- .claude/skills/dev-item-address/SKILL.md — the procedure (document mode: steps 2, 7, 9-12, 15); .claude/skills/dev-code-review/SKILL.md — what the reviewer checks (in particular "no invented decisions")
- **ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md** — Status (as a model), decision 1 (the path table row of `artifacts.json`; "a directory exists only when something was written into it"), decision 2 (what changes after a round is at run level), **decision 6** (blob records), decision 7, decision 9 (layout version versus `schema_version`), decision 10 (limits), Consequences, Boundaries
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — the closing **"Record format"** section (this record must follow it) and decision 6 (`schema_version`; reading older versions is OD-11); ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md — the `id` rows (`run_id`, `round`, `candidate`, `attempt`: types and first values) and how it states value types
- ARCHITECTURE/Requirements.md — rows FR-6, FR-10 (the 2nd-layer package validates "STATE/spec/eval/artifacts"), FR-13, NFR-1, NFR-2, **NFR-7 ②**, C-2, **C-3**, C-6; the whole "Open Decisions" preamble (status vocabulary, update rule, one-line rule); register rows **OD-8**, OD-11, OD-17, OD-20, OD-25
- ARCHITECTURE/OpenDecisionProposals.md — the header and sections **OD-8** (the "채택분", "제안으로 남는 부분" and "하위 질문" bullets), OD-11, OD-17, OD-20
- ARCHITECTURE/StandardScenarios.md — "계층", "검사 규칙", every step that names `artifacts`, CAS or a blob (search; S10 step 2 at least), and "검사 결과" (heading, history paragraph, the affected rows); ARCHITECTURE/UsageCases.md — the glossary entries "CAS" and "데이터 plane" and UC-E4
- Issue #5 comments (owner inputs; fixed): **A-2** `gh api repos/myungjoo/HIL-Claw/issues/comments/5495860612 --jq .body` (the decision, the principle "git = 지식, CAS = 재생산 가능한 산출물", the three supplements: the two-function sync contract, the retention class vocabulary as a **required field**, `gc_at` on GC); A-3 `.../comments/5537233759` (local commit is the durability boundary; `blob.push` is never called automatically); A-1 `.../comments/5046307826`; D6 `.../comments/5986348506`. Then read every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6021138854 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`)
- Issue #4 body §1 (single entry point, no whole-directory scan), §2a-§2c, §3b; issue #8 for the session-entry check
- `hilclaw/cas.py` (module docstring, `BlobRef`, `blob_path`, the digest form), `hilclaw/layout.py` (`RUN_FILES`, `run_file`, the number forms of round / candidate / attempt) — existing code the record must not contradict. Not edited
- PROCESS/tasks/T-0021-adr-od8-data-plane-layout.md — `## Result` (how ADR-0004 landed: the register precedent used, the review findings, the notice text); PROCESS/tasks/T-0008-cas-blob-store.md — `## Result` and Follow-ups; PROCESS/PLAN.md item P1-6

## Acceptance Criteria
What is **fixed** and must be taken as input, not re-decided:
- C-3 / #5 A-2: the record members hash, size, type, producing round, retention class; the retention classes `best`, `final`, `intermediate`, `failed` and their meaning (`best` / `final` permanent; `intermediate` / `failed` subject to GC after a grace period); the class is a required member; a GC writes `gc_at` into the record and that edit is committed; the MVP records the class and builds no GC tool.
- ADR-0004 decision 6: one `artifacts.json` per run at `runs/<run_id>/artifacts.json`, one record per blob the run produced, written by the tool layer with the blob store; a file that needs a binary names it by hash. Decision 2: a record may change after its round because the file is at run level.
- `hilclaw/cas.py`: a blob is identified by its SHA-256 as 64 lowercase hexadecimal characters; its size is a number of bytes.
- ADR-0002: the round is a non-negative integer, `0` being the bring-up round.
- NFR-7 ②: a persistent artefact carries a `schema_version`. NFR-2: the history of the data repository is the audit record and is not rewritten.
- #5 A-3: nothing pushes automatically.

What the ADR **decides** (this part of the rest of OD-8: the blob record). The content of each decision is the executor's to work out and justify from the fixed inputs; the reviewer's Approve is what confirms it. For every point give the choice, the alternatives considered and one or two lines of reason; mark every choice no source gives as this record's own:
1. **Scope**: that the record fixes the content of `runs/<run_id>/artifacts.json` — the shape of the file and the members of one blob record — and nothing of any other file.
2. **Shape of the file**: the top-level value, where `schema_version` stands (version 1), how the records are held (for example a list in the order they were added, or a map by hash) and in which order, argued from line-wise diffs in the data repository's history (NFR-2) and from "no scan" (#4 §1).
3. **Members of a record**: for each of the five members of C-3 and for `gc_at` — the member name, the value type and form, and whether it is required. At least: the hash (form as in `hilclaw.cas`; whether and how the algorithm is named), the size (bytes), the retention class (exactly the four values of C-3), `gc_at` (absent until a GC; its time form if it can be fixed without designing the GC, otherwise only "a time, form open").
4. **Producing round**: how the round is expressed (the integer of ADR-0002). Whether a record also names the candidate and attempt, or the step or role that produced the blob: C-3 names only the round, so anything more is this record's addition and needs a stated need (ADR-0004 already lets the file that uses a binary name it by hash). Prefer the minimum unless a reader could not otherwise do something a requirement asks for.
5. **`type`**: what the member says (the kind of content). No source gives its values. Either a closed P1 list argued from the artefacts the tree of ADR-0004 can produce, or an open token with a constrained form and no fixed list — prefer the constraint-only answer unless a requirement needs a closed list, as ADR-0004 decision 8 did for `run_id`. Do not present an invented list as a requirement.
6. **Identity and duplicates**: what identifies a record within the file; what happens when a run produces the same content twice (one record or two), given that the store keeps one blob per hash; whether the same hash may appear in the files of two runs.
7. **Allowed changes**: which changes a record may undergo after it was written — at least the `gc_at` edit of C-3; whether the retention class may change (a blob recorded as `intermediate` that later backs a best) and that such a change is an edit of the record at run level; that a record is never removed (NFR-2). **Who** chooses the class and **when** it changes may hang on OD-20 / OD-29 / OD-23: if so, fix only that the writer of the record is given the class, and leave the policy to those ODs.
8. **Record and store**: the relation between a record and the blob — what a record asserts at the time it is written, that a blob may later be absent (GC; a checkout that never fetched it) without the record being wrong, and that the tree gives no atomicity between the store and the file (ADR-0004 decision 10). Say what a reader may and may not conclude from a record.
9. **Versioning**: `schema_version` 1 of this file, when it is raised, its relation to the layout version of ADR-0004 decision 9, and that reading an older version is OD-11 — refer, do not decide.
10. **Limits**: what the record does not guarantee.

What the ADR must **not** decide — name each as a boundary in the record, with the place where it is decided:
- The GC tool, when it runs, the grace period, where that period is configured, what "run end" means for it (C-3 follow-up; no OD registered — if a new OD is needed, say so in `## Result` as a proposal and do not add a register row).
- `blob.push` / `blob.fetch`: their meaning on one machine, their backend, any "pushed" or "location" member of a record (#5 B-2, #5 A-3).
- Which artefacts are stored as blobs beyond "binaries" (A-2), and a list of producing tools; whole-model binaries (C-6); datasets (#5 B-8).
- The policy of who assigns a retention class and when (OD-20, OD-29, OD-23), `best.json` and how the knowledge tree refers to a blob (OD-20, OD-7).
- Fields of `STATE.json`, `instance.json`, `events.ndjson` and the result files (PLAN P1-8; OD-17, OD-11, OD-3, OD-13); whether an event is logged for a blob.
- Locking, concurrency and atomic writes (OD-17; C-2), the isolation means (rest of OD-8, OD-14, OD-18), who may write the file beyond "the tool layer" (OD-23).
- OD-25, OD-3, and every other owner-only item.
- Any code, test, JSON Schema file, CI change, or any change to the `HIL-Claw-data` repository.

If a point of 1-10 cannot be written without one of the excluded items, do not fill the gap: narrow the point and say so, or return BLOCKED ("design choice needing an owner-only decision" or "requirement unclear") with the exact question (DRIVER §3, §9).

The record (`ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md`, new; the slug may be adjusted, the number may not):
- Follow the "Record format" section of ADR-0001: sections Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References, in this order; one closure per record; written in English.
- **Status** says: accepted under DRIVER §9 (D6) by reviewer approval, the acceptance date, that it closes one part of the rest of OD-8 (the blob record of `artifacts.json`) and what stays open, that it builds on ADR-0004 and ADR-0002 and is revisited if one of them is reverted, and that the owner may object on #5 within 7 days of the notice, in which case a reverting task is created. Do not write that the owner confirmed it.
- One table "member — type and form — required — source (C-3 / this record)" and one short example of a file in a code block with clearly synthetic values (a hash of repeated digits, not a real digest of a real artefact). Length about 90-130 lines; enough for the author of the P1-6 code task to write the validator and the writer without reading the issues again.
- **Consequences** list what follows for existing code and documents without changing them: `hilclaw/cas.py` and `hilclaw/layout.py` (consistent, or what a follow-up must add), and the code task that follows.
- **References** cite sources by stable handle: Requirements IDs, issue comment URLs, the proposal section, PLAN P1-6, ADR-0001 / 0002 / 0004.

Edits of existing documents (same commit as the record — register update rule):
- `ARCHITECTURE/Requirements.md`: the **OD-8** row only — add the confirmed part (the blob record, with the link to ADR-0005) in the style the row already uses for ADR-0004, and keep the open rest visible (the isolation candidates, the fields of the other files, the `run_id` form, the five sub-questions). Keep the row to one line. Do not renumber, add or remove any OD row. Do not edit the body of C-3 or of any FR / NFR / C row: if the record makes a sentence of C-3 more precise, name the proposed wording as a follow-up for the integrator.
- `ARCHITECTURE/OpenDecisionProposals.md`, section **OD-8**: extend the heading note and the "채택분" / "제안으로 남는 부분" bullets (the fields of `artifacts.json` leave the open list; the other files stay); add any sub-question the record raises; delete no proposal text.
- `ARCHITECTURE/StandardScenarios.md`: re-run the coverage check (CLAUDE.md "문서 커버리지 재검사") with the document's own rules for every step that names `artifacts`, CAS or a blob, and update "검사 결과": heading date / note, one new dated passage in the history paragraph, and the affected rows. State the outcome in the commit body even if no verdict changes.
- `ARCHITECTURE/UsageCases.md`: only if a sentence that names `artifacts.json` or the CAS has become false or now has a more precise pointer. If nothing needs to change, do not touch the file and say so in `## Result`.
- In-place edits of these documents keep the language of the text around them (Korean), as in T-0015 / T-0017 / T-0020 / T-0021.
- No edit to ADR-0001..0004, `CLAUDE.md`, `README.md`, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills, the agents, `hilclaw.config.json`, or any file under `hilclaw/`, `tests/`, `.github/`.

Tests:
- None. Document mode: no code changes, so CLAUDE.md test rules ①-④ do not apply. The document checks below replace steps 4, 6 and 8 of dev-item-address.

Document checks (record the outcome of each in `## Result`):
- Session-entry check done before the first edit: `gh pr list --repo myungjoo/HIL-Claw --state open` (the planner saw none on 2026-10-07) and issues #4, #5, #7, #8 read for anything newer than this task file about OD-8, `artifacts.json`, the CAS, retention or GC (the planner found nothing: the latest #5 comment is the ADR-0004 notice 6021138854; HQ-0003 is unanswered and unrelated). If an open PR edits the OD register or the OD-8 sections, stop and return BLOCKED ("open PR conflict"). If the owner has meanwhile objected to ADR-0002 or ADR-0004 in a way that changes what this record builds on, do not start: return BLOCKED ("requirement unclear") quoting the comment.
- Every relative link in the new record and in the edited lines resolves to an existing file or anchor (`ARCHITECTURE/decisions/` is one level below `ARCHITECTURE/`).
- OD numbers: `git diff origin/main -- ARCHITECTURE/Requirements.md` touches the OD-8 row only (and at most the sentence above the table that lists the ADRs of OD-8); the count (29) and numbering of register rows are unchanged.
- Nothing in the record contradicts C-3 / #5 A-2 word for word (five members, four classes, `gc_at`), and nothing states an excluded item as decided: no GC rule, no grace period, no push or fetch semantics, no class-assignment policy, no field of another file.
- The record is consistent with ADR-0004 decision 6, with the digest form of `hilclaw/cas.py` and with the round number of ADR-0002.
- `git ls-files --eol` shows `i/lf` for the changed files; `git diff origin/main --stat` lists only files in `touchesFiles` (four or five).
- CI is not a gate for document mode, but the push to `main` triggers the workflow: check the `push` run with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion; if it is not `success`, do not fix forward — record it and say so in the returned summary.

Process (document mode, CLAUDE.md A-13, dev-item-address steps 9-12 and 15):
- Before anything else, the §3-5 landed check: `git log origin/main --grep='^Task: T-0024'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0024 --state all`.
- Branch `claude/T-0024-adr-artifacts-record` from `origin/main`. Commit and push the branch; **no PR**.
- Reviewer cycle: spawn a fresh-context `dev-reviewer` sub-agent, give it the branch name (review target = diff against `origin/main`) and this task file's path, and receive the verdict and findings as its return value. Ask it explicitly to check (a) the planner's judgement in `## Why` that the record is design-level and hangs on no open owner item, and the A-13 reading (first definition of the `artifacts` schema along the D6 route); (b) that nothing of C-3 / #5 A-2 is contradicted and no excluded item is decided — in particular no GC, push / fetch or class-assignment policy, and no invented `type` list presented as a requirement; (c) that each decision follows from a cited source or is argued as a design choice with alternatives and is marked as the record's own; (d) the register and coverage-check updates. Address findings and re-request review until Approve with nothing trivially fixable left; more than 7 rounds is BLOCKED. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Landing: `git fetch origin`, rebase the branch onto `origin/main`, then squash to **one** commit (`git reset --soft origin/main` + commit — only after the rebase). `git show --stat HEAD` must list only files in `touchesFiles`. If the rebase needed conflict resolution that changed content, go back to review.
- Commit message: English; subject starts with `T-0024:`; the body gives the decisions 1-10 in one line each, the boundaries, how the OD-8 row was updated and the coverage re-check outcome; it ends with the trailers, in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0024`, then any attribution trailer your session requires.
- Push with `git push origin HEAD:main` (fast-forward). If rejected because `main` moved, fetch, rebase and retry (at most 3 times); never `git push --force*`, and never push the rewritten branch back to its remote branch. Delete the remote branch and the local branch in **separate** commands and only after the push to `main` is confirmed (T-0012 incident), then check out `main` at `origin/main`.
- **Owner notice (DRIVER §9)**: do not post it yourself — the driver is the notifier (DRIVER §7, §8). Put the ready-to-post English text in `## Result`: what was decided in six lines or fewer with the example record in a short code block, the record's path and commit, the boundaries left open (GC and grace period, push / fetch, class-assignment policy, the other files' fields), the A-13 reading, the dependence on ADR-0002 / ADR-0004, and the date on which the 7-day window ends. The driver posts it on #5 with its tail.
- `## Result`: fill it in **after** the push, on `main`, and leave that edit to this task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The landed commit must not contain the task file. Record: commit hash, review rounds and findings with how each was handled, the decisions with their reasons, the boundaries, the document-check outcomes, the notice text, follow-ups.
- `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. This task ticks **no** PLAN checkbox; say so in `## Result`.
- Size: one new file of about 90-130 lines and three or four small edits; within 300 LOC / 5 files. If consistency turns out to need a sixth file, do not exceed the cap: finish the five and list the sixth as a proposed follow-up (DRIVER §5).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- The record writer, the validator, a JSON Schema file and their tests (the next code task of PLAN P1-6).
- A GC tool, the grace period, `blob.push` / `blob.fetch` and their backends.
- Fields of any other data-plane file; closing or changing any OD other than this part of OD-8; choosing the isolation means.
- Any change to the `HIL-Claw-data` repository, to `hilclaw.config.json`, or to code and tests.
- Editing the body of C-3 or FR-13, issue bodies, ADR-0001..0004, or posting on GitHub issues (the driver posts the owner notice).
- Answering #5 B-2, B-8, OD-25 or OD-3 on the owner's behalf.

## Follow-ups
- (driver, after the wrap-up push) Post the §9 owner notice on #5 from the text in `## Result`, with the driver tail.
- (planner, next — code mode, P1-6 slice 3) `hilclaw/artifacts.py`: validate an `artifacts.json` document and add a blob record per ADR-0005, using `cas.BlobRef` and `layout.run_file`; standard library only, with `tests/test_artifacts.py`. From then on a change of what it accepts is an `artifacts` schema change under A-13.
- (planner) The rest of PLAN P1-6 after that: `blob.push` / `blob.fetch` — what a local implementation means is not stated by C-3 and may be an owner question (#5 B-2).
- (planner) PLAN P1-3 is still marked "오너 확정 필요"; its owner questions are listed in T-0021 `## Follow-ups` (oracle of `cpu_standin`, memory layout / operand order / C prototype of the first GEMM, `hw_source`). The P1-8 schemas need an ADR in scope and a judgement on the gate fields (OD-3 is owner-only).
- (integrator, from T-0021) `README.md` line 36, the FR-13 pointer to ADR-0004, the commit hash in the OD-8 register row, the `HIL-Claw-data` README.
- (if the owner objects to ADR-0002 or ADR-0004 within its window) Revisit this record together with the reverting task.

## Result
