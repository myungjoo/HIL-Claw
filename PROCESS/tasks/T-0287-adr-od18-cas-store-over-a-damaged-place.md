---
id: T-0287
title: Write ADR-0095 on what the store step of `hilclaw.cas` does when the place of a hash already holds a file whose content is not its name, or something that is no regular file (first part of OD-18 sub-question 13); no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, C-3, NFR-2, OD-18, "#5 A-2", "#5 D6"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/ADR-0095-od18-cas-store-over-a-damaged-place.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 110, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts, `blob.push` / `blob.fetch`) and P1-6 (the CAS blob store, C-3) rest on `hilclaw/cas.py`. ADR-0039 (the local `blob.push` / `blob.fetch`) registered sub-question 13 under OD-18. It asks what is done about two things in the local store:

- a file at the place of a hash whose content is not that hash;
- a place of a hash that holds something that is no regular file (for example a directory).

It asks who removes or replaces such a thing, "given that `hilclaw.cas` keeps an existing file when the same content is stored again". It also asks whether anything records the finding, and whether a call of the pair should show that a place is occupied. ADR-0039 itself only reports such a file and leaves it as it is (decisions 4 and 6). Its alternatives table rejects a push that removes or repairs the file, because "a deletion, and a repair needs the content from somewhere; removal belongs with retention and GC (C-3), which are not decided".

One part of the question does not need the GC design: the **store step** of `hilclaw.cas` (`put_bytes`, `put_file`). That step has the full content in hand and computes its hash. Today it moves the new file into place only when no regular file is there (`if not target.is_file()`), so a damaged file at that place is kept, and a directory there makes `os.replace` fail. No module of `hilclaw/` calls `put_bytes` or `put_file` yet; only `tests/test_cas.py` does. That makes now the cheapest time to decide what the store step should do.

This task writes that record. It is a design-level answer under OD-18 sub-question 13. The driver may close such an answer by an ADR (DRIVER §9). It touches no owner-only item: #5 A/B, C-6, OD-25 or OD-3. The owner's sentences of #5 A-2 (C-3) are cited, not reinterpreted. This task is apart from the `clang_build` / `local_run` series and from every open HQ (HQ-0021 to HQ-0029).

The planner does not decide the answer. The executor weighs the alternatives and decides. Alternatives to weigh at least:

- (a) the store step replaces a non-intact regular file at the place with the new, verified content (a re-hash of the existing file when one is there, then the existing atomic move);
- (b) keep today's behaviour and leave the part open;
- (c) the store step refuses with an error when the existing file is not intact;
- for a place that holds something that is no regular file: today's error, or a named error, or anything else the executor finds. The executor must not remove a directory or any other entry it did not create.

The executor may find that (a) conflicts with a cited sentence. For example, C-3 or #5 A-2 on what git records, the docstring "Blobs are only ever added", or ADR-0005 decision 10. If so, it says so and weighs it, and does not take any lead on trust.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0287` trailer;
  - §9 (lines 141-147): ADR closure by the driver, the #5 notice and the 7-day window.
- `CLAUDE.md`, standing rules: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분", "바이너리 금지".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/cas.py` on `main` (whole file, 120 lines): the module docstring, `has_blob`, `verify_blob` and `_store`. Read it as a file; do not run it.
- `tests/test_cas.py` on `main`: `test_a_repeated_put_keeps_the_stored_file` (about line 173), `test_verify_blob_detects_altered_content` (about line 227), `test_a_failed_move_into_place_leaves_no_temporary_file` (about line 300) and `test_a_blob_path_occupied_by_a_directory_is_an_error` (about line 341). Cite them; do not run them.
- `hilclaw/blob_tools.py` on `main`: how the pair reads the place (it must stay as ADR-0039 decides).
- `ARCHITECTURE/decisions/ADR-0039-od18-blob-push-fetch-local.md`: Context (lines 13-19), decision 4 (lines 43-61), decision 6 (lines 69-75), Limits (lines 81-89), the walk-through rows (lines 90-104), the alternatives of points 4 and 6 (lines 105-126), Consequences (lines 127-135) and Boundaries (lines 136-147, sub-question 13 at about line 145). Use its shape for the new record.
- `ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md`: decision 10 and Boundaries (what a blob record does and does not guarantee; `gc_at`).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decision 1 (`blobs/` in the layout).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (from line 146).
- `ARCHITECTURE/Requirements.md`: C-3 (line 60) and NFR-2.
- Issue #5, the A-2 comment (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5495860612) and the D6 comment (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506), via `gh issue view 5 --repo myungjoo/HIL-Claw --comments`.
- `PROCESS/tasks/T-0008-cas-blob-store.md`: `## Result` (why the store keeps an existing file).
- The recording rules of the three files this task edits. Follow them as written there:
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and the OD-18 register row (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet in the header (line 8), the `채택분` lines of OD-18 (lines 254-305) and the sub-question 13 bullet (line 313);
  - `ARCHITECTURE/StandardScenarios.md`: the first paragraph of `# 검사 결과` (line 170), the "최근 재검사" line (line 172) and the S10 row (line 198).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md "세션 진입 점검"). Before editing anything:
   - Run `gh pr list`. Read issues #4, #5, #7 and #8 for anything newer than ADR-0039 on sub-question 13, the local store, `hilclaw.cas`, retention or GC.
   - If an open PR changes any file in `touchesFiles`, stop and return BLOCKED (open-PR conflict risk). PR #179 touches only `hilclaw/clang_build.py` and `tests/test_clang_build.py`, so it does not overlap.
   - If an owner comment on #5 speaks to this subject, follow it. If it conflicts with this task, return BLOCKED.
   - Confirm that `ADR-0095` is unused on `main` and on the remote branches. ADR-0068, ADR-0074 and ADR-0088 are held by unlanded branches and must not be reused. If ADR-0095 is taken, use the next free number and say so in `## Result`.
2. **New record** `ARCHITECTURE/decisions/ADR-0095-od18-cas-store-over-a-damaged-place.md` in the ADR-0001 "Record format": Status, Context, Decision, Alternatives considered, Consequences, Boundaries and References. Its Status has the same parts as ADR-0039's:
   - acceptance under DRIVER §9;
   - which content is owner, cited or this record's own;
   - how far sub-question 13 is answered;
   - no data-plane schema change;
   - the records it builds on;
   - the #5 notice and the 7-day window.

   The Decision must:
   - **Observe the code on `main`**, read as a file, binding no code. Say what the store step does today when the place holds nothing, an intact file, a non-intact regular file, or something that is no regular file, and cite the four tests named above. Say that nothing was established by running code in this task.
   - **Give the answer for a non-intact regular file at the place** when the same content is stored. Weigh at least alternatives (a), (b) and (c) of `## Why` against C-3, #5 A-2, ADR-0005 decision 10 and ADR-0039 decisions 4 and 6. Show every rejected alternative with its reason. If the record chooses replacement, say how a reader running at the same time sees the place (the existing move into place is atomic), and that nothing but the store's own temporary file is ever removed.
   - **Give the answer, or leave it open with reasons, for a place that holds something that is no regular file.** The store step must not remove or rename an entry it did not create.
   - **Say what stays open** of sub-question 13. At least: removal of a damaged file outside a store of the same content, whether anything records the finding, whether the pair shows an occupied place, and everything that belongs to retention, GC and `gc_at` (C-3). Name what would let each be placed, without deciding it.
   - **Name the code follow-up**, if the record changes behaviour: which function of `hilclaw/cas.py` changes, and which existing test of `tests/test_cas.py` would then be edited (most likely `test_a_repeated_put_keeps_the_stored_file`). Name it; do not write it.

   The Consequences section lists the sentences of earlier records and docstrings that become less exact, without editing them. At least ADR-0039's alternatives row of point 6 and its sub-question 13 sentence belong there, and the `hilclaw/cas.py` docstring sentence "Storing content that is already present keeps the stored file as it is", if the answer changes it. No earlier ADR is edited.
3. **Register and proposal records.** Follow the recording rules written in each file. Do not copy the wording of earlier task files.
   - `ARCHITECTURE/Requirements.md`, OD-18 row: apply the "행 형식" rule. Add one link to the new ADR after `**확정분**:` with a few words of topic. Rewrite `**잔여**:` in place only where its text no longer holds. Do not restate the record or add a dated paragraph. The status word stays, so OD-18 stays open.
   - `ARCHITECTURE/OpenDecisionProposals.md`, OD-18: apply the header's "기록 규칙". Add one `채택분` line for the new ADR after the ADR-0094 line. In the sub-question 13 bullet, rewrite its status in place (for example `미결` → `일부 답함`, with `→ 부분 답:` and `남음:`), changed only as this record changes it. Do not add a dated note or copy text from the register row.
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's own rules (CLAUDE.md "문서 커버리지 재검사"), at least S10 and every scenario that cites OD-18. Under the first paragraph of `# 검사 결과`, update the "최근 재검사" line in place. Add a "판정 변화 이력" entry only if a judgement changed or a gap was found or closed.
4. **Do not invent.** Write no new data-plane member, no `artifacts.json` or `gc_at` rule, no retention or GC rule, no new result member or reserved kind of the pair, and no new tool failure kind. Add no owner decision. If the record can only be completed by such a value or an owner-only choice, stop and return BLOCKED with the question; do not decide it. Choosing (b) and leaving the part open with stated reasons is a valid outcome if the weighing leads there.
5. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0287-<slug>`.
   - Run the context-isolated reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Rebase on `origin/main` and push to `main` directly, with no PR. The commit carries the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0287`.
   - After landing, post the DRIVER §9 notice on #5 with the driver tail (§8), and record its URL in `## Result`.
6. **Size**: four files. The new record should be well under 130 lines. The edits to the three existing files are a few lines each.
7. **Result** records:
   - the landed commit;
   - the review rounds and their findings;
   - the #5 notice URL;
   - the answer for each kind of occupied place, and what is left open;
   - the follow-ups (the code task, if any).

   The executor starts no `claude` program, compiler or container (D16).

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI or any settings file. The code follow-up goes in `## Follow-ups`.
- Any change to what `blob.push` / `blob.fetch` answer (ADR-0039 decisions 3 to 6), and any new member of their result.
- Retention, GC, `gc_at`, `artifacts.json` members and data governance (C-3, #5 A-2, OD-25).
- `hilclaw/clang_build.py`, `hilclaw/local_run.py`, their tests, and OD-18 sub-question 18. Everything waiting on HQ-0021 to HQ-0029.
- The unlanded branches `claude/T-0210-*`, `claude/T-0225-*`, `claude/T-0231-*`, `claude/T-0233-*`, `claude/T-0264-*` and `claude/T-0284-*`. Do not cite them or reuse their ADR numbers.
- Editing any ADR from ADR-0001 to ADR-0094. Owner-only items (DRIVER §9).

## Follow-ups

- (code, if the record changes behaviour) Apply ADR-0095 in `hilclaw/cas.py` with tests in `tests/test_cas.py`, editing only the existing tests the record names.

## Result
