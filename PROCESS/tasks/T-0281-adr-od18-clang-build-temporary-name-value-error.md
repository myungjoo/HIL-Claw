---
id: T-0281
title: Write ADR-0093 on which row of `correctness.check` the error that `clang_build.build` now names "output" when forming the temporary name (`PurePath.with_name`) lets an operation place, and what is left of U4 (more of OD-18 sub-question 18 part (ma)); no code, no `local_run.run`
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18, "#5 D6"]
dependsOn: [T-0279, T-0280]
touchesFiles: [ARCHITECTURE/decisions/ADR-0093-od18-correctness-check-temporary-name-value-error.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 90, files: 4}
hq: []
---
## Why

ADR-0092 (T-0279, `1ac785b`) left U4 open. In its decision 3, U4 is the pre-start `ValueError` of `clang_build.build` that carries no `parameter`. It held three things:

- a `ValueError` from `with_name` other than its documented case;
- one from `time.monotonic`, if one arises;
- one from `subprocess.Popen` for what `build` hands it.

T-0280 (PR #177, `04b8a38`) changed the code. Only the `target.with_name(...)` call that forms the temporary name now runs inside `with _parameter("output"):`. So a `ValueError` or `TypeError` from it carries `parameter` `"output"` and no `path_role`. The pid and `secrets.token_hex(8)` are drawn just before, outside any step. T-0280's task file says that it "records no row of `correctness.check`". Its `## Result` records a Windows observation. That observation is not established by this task, and the record may cite it as such.

No accepted record yet says which row this newly named error gets. The record of OD-18 (ma) on `main` still lists `with_name` inside U4. This task writes that record.

- It is a design-level answer under OD-18 sub-question 18 part (ma). The driver may close such an answer by an ADR (DRIVER §9). It touches no owner-only item: #5 A/B, C-6, OD-25, OD-3.
- It does not depend on HQ-0027 (`local_run.run`) or HQ-0021 (`timing_build.py`), and it must not touch them.

The planner does not decide the answer. The executor weighs the alternatives and decides, as ADR-0092 did. Two leads from the landed records, which the executor must check rather than take on trust:

- ADR-0091 decision 2 and ADR-0092 decision 2 make a `ValueError` with `parameter` `"output"` no row. The operation cannot tell one such error from another.
- ADR-0087 decision 4 makes a `TypeError` named for an argument the operation forms no row.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0281` trailer;
  - §9 (lines 141-147): ADR closure by the driver, the #5 notice and the 7-day window.
- `CLAUDE.md`, standing rules:
  - "문서 커버리지 재검사";
  - "미결은 발명하지 않는다";
  - "브랜치·merge 절차" (document mode);
  - "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/clang_build.py` at `04b8a38`, read as a file:
  - the `parameter` paragraph of the `build` docstring (lines 252-268);
  - the check steps through the start (lines 304-345);
  - `_parameter` (line 474).
- `PROCESS/tasks/T-0280-clang-build-temporary-name-error-names-the-output.md`: `## Why` and `## Result` (the change, the tests and the `windows_only` observation).
- `ARCHITECTURE/decisions/ADR-0092-od18-correctness-check-output-name-value-errors.md`: the whole record. This is the record the new one builds on and narrows. Its J3, J4 and decision 3 are the reading of U4 that changes.
- `ARCHITECTURE/decisions/ADR-0091-od18-correctness-check-sources-output-kernel-sources-value-errors.md`: K4, decisions 1, 2, 3 and 7.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`: decisions 2, 4 and 5 (lines 32-55).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md`: decisions 4 to 6 (lines 64-93).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decisions 3 and 4 (lines 46-104).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (from line 146).
- The recording rules of the three files this task edits. Follow them as written there:
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and the OD-18 register row (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet in the header (line 8), the `채택분` lines of OD-18 (around line 303) and the sub-question 18 bullet (line 316);
  - `ARCHITECTURE/StandardScenarios.md`: the first paragraph of `# 검사 결과` (line 170) and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md "세션 진입 점검"). Before editing anything:
   - Run `gh pr list`. Read issues #4, #5, #7 and #8 for anything newer than ADR-0092 on OD-18 (ma), U4, `with_name` or `clang_build.build`.
   - If an open PR changes any file in `touchesFiles`, stop and return BLOCKED (open-PR conflict risk).
   - If an owner comment on #5 speaks to this subject, follow it. If it conflicts with this task, return BLOCKED.
   - Confirm that `ADR-0093` is unused on `main` and on the remote branches. If it is taken, use the next free number and say so in `## Result`.
2. **New record** `ARCHITECTURE/decisions/ADR-0093-od18-correctness-check-temporary-name-value-error.md`. Use the ADR-0001 "Record format", with Status, Context, Decision, Alternatives considered, Consequences, Boundaries and References. Its Status follows the shape of ADR-0092's:
   - acceptance under DRIVER §9;
   - the three kinds of content;
   - how far (ma) is answered;
   - no data-plane change;
   - the records it builds on, and that it falls with them;
   - the #5 notice and the 7-day window.

   The Decision must:
   - **Observe the code at `04b8a38`**, read as a file, and bind no code. Say which steps of `build` now carry `"output"`, and what runs after the `cwd` check and outside any step up to and including the start. That is at least `os.getpid`, `secrets.token_hex`, the command, `time.monotonic` and `subprocess.Popen`. Say what T-0280's tests show, citing them, and that nothing was established by running code in this task.
   - **Give the row** that `correctness.check` of the first case and of the mock gives the `ValueError`, and the `TypeError`, with `parameter` `"output"` from forming the temporary name. Give the reason. The executor decides the row by weighing the alternatives against ADR-0091 decision 2, ADR-0092 decision 2, ADR-0087 decision 4 and ADR-0060 decision 3. Show at least one alternative it rejects, with the reason. If the landed rules already answer the case, say so, and say that this record only confirms it.
   - **Restate U4 as it now is**, from the code. Say what is removed, which is the error from `with_name`. Say what stays: the unnamed draws of the pid and the random part, the command, the clock and `subprocess.Popen`. Do not claim what those raise beyond what is read and cited. Say whether U4 stays open and why. Name what would let it be placed, but do not decide it.
   - Say the log and message consequences in one or two sentences, citing ADR-0078 decision 2 and ADR-0045 decision 6 as ADR-0092 decision 4 does.
   - List "how far (ma) is answered": answered now, narrowed, and still open. Take the still-open list from the sub-question 18 bullet of OpenDecisionProposals on `main`, changed only as this record changes it.

   The Consequences section lists the sentences of earlier records that become less exact, without editing those records. At least the U4 sentences of ADR-0092 (J3, decision 3, decision 6) and of ADR-0091 (K4, decision 3) belong there. No earlier ADR is edited.
3. **Register and proposal records**:
   - `ARCHITECTURE/Requirements.md`, OD-18 row: follow the "행 형식" paragraph. Add one link to the new ADR after `**확정분**:`, with a few words of topic. Change `**잔여**:` only where its text no longer holds. Do not restate the record and do not add a dated chain. The status word stays as it is: OD-18 stays open.
   - `ARCHITECTURE/OpenDecisionProposals.md`, OD-18: follow the header's "기록 규칙". Add one `채택분` line for the new ADR, after the ADR-0092 line. In the sub-question 18 bullet, rewrite the status of (ma) in place. Add the ADR to the `→ 부분 답:` list, and rewrite the U4 entry of `남음:` so that it no longer lists `with_name`. Do not add a dated note and do not copy text from the register row.
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's own rules (CLAUDE.md "문서 커버리지 재검사"). Follow the first paragraph of `# 검사 결과`. Update the "최근 재검사" line in place. Add a "판정 변화 이력" entry only if a judgement changed or a gap was found or closed.
4. **Do not invent**. Write no new value of `error.kind` or `condition`, no data-plane member, no reserved kind, and no rule about which names `with_name` refuses on which platform. Do not add an owner decision. If the record can only be completed by such a value or by an owner-only choice, stop and return BLOCKED with the question. Do not decide it.
5. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0281-<slug>`.
   - Run the context-isolated reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Rebase on `origin/main` and push to `main` directly, with no PR. The commit carries the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0281`.
   - After landing, post the DRIVER §9 notice on #5 with the driver tail (§8), and record its URL in `## Result`.
6. **Size**: four files. The new record should be well under 140 lines, since its scope is narrower than ADR-0092's. The edits to the three existing files are a few lines each.
7. **Result** records:
   - the landed commit;
   - the review rounds and their findings;
   - the #5 notice URL;
   - the row decided, and what U4 now holds;
   - the follow-ups.

   The executor starts no `claude` program, compiler or container (D16).

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI or any settings file. Code follow-ups go in `## Follow-ups`.
- Placing U4, or any other open entry of (ma), in a row.
- `local_run.run` and everything waiting on HQ-0027. `hilclaw/harness/timing_build.py` (HQ-0021).
- The unlanded branches `claude/T-0210-*`, `claude/T-0225-*`, `claude/T-0231-*`, `claude/T-0233-*` and `claude/T-0264-*`. ADR-0088 is held by `claude/T-0264-*`: do not cite it or reuse its number.
- Editing any ADR from ADR-0001 to ADR-0092. Sub-questions 18 (ga), (da), (ra) and the size bound of (na). Owner-only items (DRIVER §9).

## Follow-ups

- Landed on `main` as `9706ed6` (document mode; trailers `Task: T-0281`, `Reviewed-by: reviewer agent (7 rounds, Approve)`). Branch `claude/T-0281-adr-od18-temporary-name-value-error` deleted locally and on the remote.
- Files (4): new `ARCHITECTURE/decisions/ADR-0093-od18-correctness-check-temporary-name-value-error.md`; one-line edits to `ARCHITECTURE/Requirements.md` (OD-18 confirmed part), `ARCHITECTURE/OpenDecisionProposals.md` (adopted-part line after ADR-0092; sub-question 18 partial answer and remainder rewritten in place) and `ARCHITECTURE/StandardScenarios.md` (latest re-check line). Coverage re-check of S0, S1-b, S2, S5, S6: no judgement changed, no gap.
- Decision: the `ValueError`/`TypeError` with `parameter` "output" raised while the temporary name is formed (`with_name`) gets no row of `correctness.check` (ADR-0087 decision 4, ADR-0091/0092 decision 2; reason ADR-0060 decision 3). S3, S4, keeping it in U4, and no row for the rest of U4 were rejected. U4 now: an unnamed pre-start `ValueError` from `os.getpid`/`secrets.token_hex`, the command, `time.monotonic` or `subprocess.Popen`; stays open. The open unnamed-`TypeError` entry now also names the draws, the command and the clock.
- Review: 7 rounds, all Approve (R1-R6 raised minor points that were fixed; R7 Info only).
- #5 notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6240707886
- Follow-ups: a later record or code task may read, or add a named check for, the rest of U4 (pid/token draws, the clock, what `subprocess.Popen` raises incl. an `env` without `items`); optionally list ADR-0087 T4 as a less-exact observation (R7 Info).
- No `claude`, compiler or container was started (D16).

## Result

- (filled by the executor)
