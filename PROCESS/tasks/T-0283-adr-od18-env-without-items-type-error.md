---
id: T-0283
title: Write ADR-0094 on which row of `correctness.check` the `TypeError` with `parameter` "env" that `clang_build.build` now raises for an `env` with no `items` method gets (more of OD-18 sub-question 18 part (ma)); no code, no `local_run.run`
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18, "#5 D6"]
dependsOn: [T-0281, T-0282]
touchesFiles: [ARCHITECTURE/decisions/ADR-0094-od18-correctness-check-env-without-items.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 90, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. ADR-0093 (T-0281, `9706ed6`) left U4 open. U4 is the pre-start `ValueError` of `clang_build.build` that carries no `parameter`. ADR-0093 decision 3 kept, inside what stays open, what `subprocess.Popen` raises "for the command, `cwd` and `env` `build` hands it, an `env` with no `items` method included". Under "What would let it be placed" it named a code change that makes `build` refuse such an `env` in a named check before the start.

T-0282 (PR #178, `4e05627`) made that code change:

- `_check_env` of `hilclaw/clang_build.py` now raises `TypeError` for an `env` that is not `None` and has no `items` method.
- The raise is inside the existing `with _parameter("env"):` step. So the error carries `parameter` `"env"` and no `path_role`. It is raised before the temporary name and the clock are drawn, and nothing is started.
- The docstring of `build` now says this is the one exception to "the class it would raise for the same single defect", because `subprocess` has no single class for it.
- T-0282's task file says it "records no row of `correctness.check`".

No accepted record yet says which row this newly named error gets. ADR-0089 decision 2 places a named `TypeError` or `ValueError` with `parameter` `"env"` in S4 `settings_refused`. The same decision also says "An `env` with no `items` method is not checked (P2) and stays under what `build` passes on from `subprocess` (decision 9)". That sentence no longer holds. This task writes the record.

- It is a design-level answer under OD-18 sub-question 18 part (ma). The driver may close such an answer by an ADR (DRIVER §9). It touches no owner-only item: #5 A/B, C-6, OD-25, OD-3.
- It does not depend on HQ-0027 (`local_run.run`) or HQ-0021 (`timing_build.py`), and it must not touch them.

The planner does not decide the answer. The executor weighs the alternatives and decides. The lead from the landed records is ADR-0089 decision 2 (S4 for `"env"`, "whether the setting is refused for its value or for its type"), read with ADR-0060 decisions 3 and 4 and ADR-0087 decision 3. The executor must check that lead rather than take it on trust.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0283` trailer;
  - §9 (lines 141-147): ADR closure by the driver, the #5 notice and the 7-day window.
- `CLAUDE.md`, standing rules:
  - "문서 커버리지 재검사";
  - "미결은 발명하지 않는다";
  - "세션 진입 점검";
  - "브랜치·merge 절차" (document mode);
  - "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/clang_build.py` at `4e05627`, read as a file:
  - the docstring of `build` from "After the compiler is found" (line 239) through the `parameter` paragraph;
  - the check steps (lines 307-340);
  - `_parameter` (line 477), `_check_env` (line 485) and `_env_text`.
- `PROCESS/tasks/T-0282-clang-build-refuses-an-env-without-items.md`: `## Why` and `## Result` (the change, the tests, and the class `Popen` raised before it, observed on native Windows and read for POSIX).
- `tests/test_clang_build.py` at `4e05627`: the tests from `NO_ITEMS_ENVS` / `test_an_env_without_items_is_a_type_error_naming_env` (about line 2154) through `test_an_env_without_items_keeps_its_parameter_through_pickling`. Cite them; do not run them.
- `ARCHITECTURE/decisions/ADR-0093-od18-correctness-check-temporary-name-value-error.md`: the whole record. This is the record the new one narrows; its decision 3 and decision 5 hold the entry that changes. Use its shape for the new record.
- `ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`: P2 (line 20), decision 2 (lines 32-36), the message paragraph for `"env"` (line 65), decision 9 (lines 71-75) and the walk-through rows (lines 83-84).
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`: T4, and decisions 2 to 5 and 8.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decisions 3 to 5 (from line 46).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md`: decisions 4 to 6 (lines 64-93).
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: decision 2.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (from line 146).
- The recording rules of the three files this task edits. Follow them as written there:
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and the OD-18 register row (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet in the header (line 8), the `채택분` lines of OD-18 (lines 290-304) and the sub-question 18 bullet (line 317);
  - `ARCHITECTURE/StandardScenarios.md`: the first paragraph of `# 검사 결과` (line 170) and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md "세션 진입 점검"). Before editing anything:
   - Run `gh pr list`. Read issues #4, #5, #7 and #8 for anything newer than ADR-0093 on OD-18 (ma), U4, the `env` check or `clang_build.build`.
   - If an open PR changes any file in `touchesFiles`, stop and return BLOCKED (open-PR conflict risk).
   - If an owner comment on #5 speaks to this subject, follow it. If it conflicts with this task, return BLOCKED.
   - Confirm that `ADR-0094` is unused on `main` and on the remote branches. If it is taken, use the next free number and say so in `## Result`.
2. **New record** `ARCHITECTURE/decisions/ADR-0094-od18-correctness-check-env-without-items.md`, in the ADR-0001 "Record format": Status, Context, Decision, Alternatives considered, Consequences, Boundaries and References. Its Status has the same parts as ADR-0093's:
   - acceptance under DRIVER §9;
   - the three kinds of content;
   - how far (ma) is answered;
   - no data-plane change;
   - the records it builds on, and that it falls with them;
   - the #5 notice and the 7-day window.

   The Decision must:
   - **Observe the code at `4e05627`**, read as a file, and bind no code. Say where the new check runs (inside the `"env"` step, after the compiler is found and before `cwd`), what it raises, and what its message holds (the type name, never the value). Cite what T-0282's tests show. Say that nothing was established by running code in this task.
   - **Give the row** that `correctness.check` of the first case and of the mock gives this `TypeError` with `parameter` `"env"`, and the reason. Decide it by weighing the alternatives against ADR-0089 decision 2, ADR-0060 decisions 3 and 4, and ADR-0087 decisions 3 and 4. Show at least one rejected alternative with its reason. If the landed rules already answer the case, say so, and say that this record only confirms it.
   - **Say what is left open.** State what this removes from the open entries of (ma): an `env` with no `items` method is no longer among what `build` passes on from `subprocess`. Say what of U4 and of "what `subprocess` passes on" stays, from the code. Claim nothing about what `subprocess` raises beyond what is read and cited. Name what would let the rest be placed, without deciding it. Also cover an `env` that has `items` but that `subprocess` still refuses on some platform (T-0282 Out of Scope names three); say whether this record places it or leaves it open.
   - **Log and message**, in one or two sentences: cite ADR-0078 decision 2 for the absent log, and the message rule of `settings_refused` for `"env"` (ADR-0089, line 65; ADR-0060 decision 5).
   - **List "how far (ma) is answered"**: answered now, narrowed, and still open. Take the still-open list from the sub-question 18 bullet of OpenDecisionProposals on `main`, changed only as this record changes it.

   The Consequences section lists the sentences of earlier records that become less exact, without editing those records. At least these belong there: ADR-0089 P2 ("any other `env` is left to `subprocess`") and decision 2 ("An `env` with no `items` method is not checked …"), and ADR-0093 decision 3 ("an `env` with no `items` method included"). No earlier ADR is edited.
3. **Register and proposal records.** Follow the recording rules written in each file. Do not copy the wording of earlier task files.
   - `ARCHITECTURE/Requirements.md`, OD-18 row, under "행 형식": one link to the new ADR after `**확정분**:`, with a few words of topic. Rewrite `**잔여**:` in place only where its text no longer holds. Do not restate the record and do not add a dated paragraph or chain. The status word stays as it is, so OD-18 stays open.
   - `ARCHITECTURE/OpenDecisionProposals.md`, OD-18, under the header's "기록 규칙": one `채택분` line for the new ADR, after the ADR-0093 line. In the sub-question 18 bullet, rewrite the status of (ma) in place: add the ADR to `→ 부분 답:`, and rewrite the open entries of `남음:` only as this record changes them. Do not add a dated note and do not copy text from the register row.
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's own rules (CLAUDE.md "문서 커버리지 재검사"). Under the first paragraph of `# 검사 결과`, update the "최근 재검사" line in place. Add a "판정 변화 이력" entry only if a judgement changed or a gap was found or closed.
4. **Do not invent**. Write no new value of `error.kind` or `condition`, no data-plane member, no reserved kind. Write no rule about what `subprocess` raises on which platform or start path. Add no owner decision. If the record can only be completed by such a value or by an owner-only choice, stop and return BLOCKED with the question. Do not decide it.
5. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0283-<slug>`.
   - Run the context-isolated reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Rebase on `origin/main` and push to `main` directly, with no PR. The commit carries the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0283`.
   - After landing, post the DRIVER §9 notice on #5 with the driver tail (§8), and record its URL in `## Result`.
6. **Size**: four files. The new record should be well under 120 lines, since its scope is narrower than ADR-0093's. The edits to the three existing files are a few lines each.
7. **Result** records:
   - the landed commit;
   - the review rounds and their findings;
   - the #5 notice URL;
   - the row decided, and what is left open;
   - the follow-ups.

   The executor starts no `claude` program, compiler or container (D16).

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI or any settings file. Code follow-ups go in `## Follow-ups`.
- Placing U4, or any other open entry of (ma), in a row beyond the `env` with no `items` method.
- `local_run.run`, `tests/test_local_run.py` and everything waiting on HQ-0027. `hilclaw/harness/timing_build.py` (HQ-0021).
- The unlanded branches `claude/T-0210-*`, `claude/T-0225-*`, `claude/T-0231-*`, `claude/T-0233-*` and `claude/T-0264-*`. ADR-0088 is held by `claude/T-0264-*`: do not cite it or reuse its number.
- Editing any ADR from ADR-0001 to ADR-0093. Sub-questions 18 (ga), (da), (ra) and the size bound of (na). Owner-only items (DRIVER §9).

## Follow-ups

- The same `env` change for `local_run.run`, after HQ-0027 is answered or if the planner finds it free of that HQ.

## Result

- (filled by the executor)
