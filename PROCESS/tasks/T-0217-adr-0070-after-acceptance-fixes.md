---
id: T-0217
title: Correct ADR-0070 after acceptance - the NumPy-at-build observation T-0216 made untrue and the three round-7 nits of T-0214; coverage re-check recorded
phase: P1
status: DONE
commitMode: doc
coversReq: [OD-18, FR-10, "CLAUDE.md 문서 커버리지 재검사"]
dependsOn: [T-0214, T-0215, T-0216]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md
  - ARCHITECTURE/Requirements.md            # OD-18 row: add ⑩ to the "정하지 않았고" list only
  - ARCHITECTURE/StandardScenarios.md
  - ARCHITECTURE/OpenDecisionProposals.md   # only if the ADR-0070 adopted bullet (line 319) needs the same alignment as nit 3
estimatedSize: {loc: 12, files: 4}   # a few clauses and one Status bullet in ADR-0070; one symbol in Requirements; a heading clause and one dated paragraph in StandardScenarios; at most one clause in OpenDecisionProposals
hq: []
---
## Why

T-0214 landed ADR-0070 (`3c78714`, document mode) after 7 review rounds, the last allowed. Round 7 approved with three nits that were deliberately not applied, because a change after the last round would have landed unreviewed text (`PROCESS/tasks/T-0214-od18-correctness-check-registration.md`, `## Result`, the `**Review**` bullet):

1. ADR-0070 calls the ADR-0056 Consequences sentence "replaced" while the same-shaped "Not yet possible ... registration" sentences of ADR-0043/ADR-0044 are listed as "less exact".
2. The Requirements OD-18 row's "정하지 않았고" list omits ⑩ (the ADR Status and the OpenDecisionProposals note include it).
3. ADR-0070 decision 2 (c) cites ADR-0047 decision 5 for `operation_failure_invalid` and omits the `end_line_failed` case.

Then T-0216 (PR #144, squash `dca5f2d`) made `correctness.check` import its NumPy-pulling modules only at its first call. ADR-0070 Consequences (line 110) still says "Building the default registry then imports NumPy through `hilclaw/mock_check.py`, a dependency the package already has (`pyproject.toml`)." That observation is now untrue of the code: building imports no NumPy; the first call of `correctness.check` does (T-0216 `## Result`, Follow-up 1).

These are corrections of an accepted record during its objection window. They need no design decision, change no decision, change no OD status and touch no data-plane schema. They tick **no PLAN checkbox** (P1-1 continues). Precedent: T-0190 (ADR-0060), T-0193 (ADR-0061), T-0197 (ADR-0062), T-0207 (ADR-0066) and T-0213 (ADR-0069, `94271f0`): an accepted record is edited in place with a Status bullet that says so. The objection window of ADR-0070 runs 7 days from the notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6205474647 (posted 2026-10-16T00:49Z, so until about 2026-10-23).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked at `502e54f`). The open HQs are HQ-0013, HQ-0014, HQ-0016..HQ-0019 (`runtime-acceptance` items on DONE tasks) and HQ-0021 (T-0210, ADR-0068 on an unlanded branch, about `sim.run` / `board.run`); none bears on this task. The next `correctness.check` work (the `cpu_standin` operation of the tool) will cite ADR-0070, so cleaning it first keeps that work on a correct base. Do not depend on, read for content or reconcile with the unlanded branch `claude/T-0210-od18-run-tools-operation-tool-failure`.

**Planner's reading** (line numbers of `main` at `502e54f`; the executor and the reviewer re-check each; the text wins):

- **NumPy sentence**: ADR-0070 line 110, last sentence of the bullet "Code sentences a code task changes". The bullet is an observation list; the rest of it (the docstrings and the test it names, "Each stays true of the code until the slice lands") is not made wrong by later landings (same judgement as T-0213 criterion 1, last sub-bullet) and is not edited. `grep NumPy ARCHITECTURE/` at planning time found this sentence only once in ADR-0070 and no copy in Requirements, OpenDecisionProposals line 319 or StandardScenarios line 230.
- **Nit 1**: the Status bullet at line 9 and decision 2 (line 39, "The choice is (a). It replaces the sentences of ADR-0060 Consequences and ADR-0056 Consequences that tie the registration to the operation of `cpu_standin`") name what is replaced; line 111 lists "the Consequences items "Not yet possible" of ADR-0040 to ADR-0048 as far as they name the registration" as less exact. The executor reads the cited sentences (ADR-0056 line 188 area, ADR-0060 line 156 area, ADR-0043 line 179, ADR-0044 line 162; search "Not yet possible" / "*Not yet possible*") and states, in one clause, the difference the record relies on (the planner's reading: the ADR-0056 and ADR-0060 sentences make the registration **wait on** the `cpu_standin` operation - "and so the tool's registration" - while the ADR-0040 to ADR-0048 items only list the registration among what was not yet possible at that record). If the texts do not support that difference, see criterion 5.
- **Nit 2**: ADR-0070 Status line 7 says sub-questions ①, ⑤, ⑧, ⑩, ⑭ and ⑱ stay open; the Requirements OD-18 row (line 107, the ADR-0070 sentence ending "(반영: [ADR-0070](...))") reads "하위 질문 ①·⑤·⑧·⑭·⑱, run 도구의 등록, ..., 정하지 않았고". ⑩ is missing.
- **Nit 3**: ADR-0070 line 38, alternative (c): "... without one, the kind it raised is outside the contract and the call ends with `operation_failure_invalid` (cited: ADR-0047 decision 5)". ADR-0047 line 77 (decision 5) and line 96 say such a call ends with `operation_failure_invalid`, "or with `end_line_failed` when the append of its end line fails" (ADR-0026 decision 3). OpenDecisionProposals line 319 (the ADR-0070 adopted bullet) paraphrases the same alternative: "계약 밖의 종류여서 `operation_failure_invalid`로 끝나고 — ADR-0047 결정 5 —". Whether it must be aligned too is the executor's call (criterion 2).

## Required Reading

ARCHITECTURE lines are very long: read them with `sed -n '<line>p' <file> | fold -w 400`, never whole files at once. Line numbers are those of `main` at `502e54f`; the text wins.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, size cap D4, trailers). Also §2 (doc mode), §8 (lines 135-139, the comment format) and §9 (lines 141-148).
- `CLAUDE.md`, the whole file; above all "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16) and "브랜치·merge 절차" (document mode and the `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md` (document mode: steps 9 to 12 and 15); `.claude/skills/dev-code-review/SKILL.md` (document-mode path).
- `PROCESS/tasks/T-0214-od18-correctness-check-registration.md` `## Result` (the `**Review**` bullet: the three nits as given).
- `PROCESS/tasks/T-0216-defer-check-imports-default-registry.md` `## Result` (the mechanism bullet and Follow-up 1).
- `PROCESS/tasks/T-0213-adr-0069-r7-nit.md` `## Acceptance Criteria` and `## Result`: the model for the Status bullet of an edit after acceptance and for recording the re-check. `ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md` Status, last bullet (the wording of T-0213's Status bullet).
- `ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md`: Status (lines 3-13), decision 2 (lines 31-45, above all lines 36-39), Consequences (lines 107-114, above all lines 110-111), References (lines 127-132).
- `ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md` lines 70-101 (decision 5 at line 77; line 96).
- The "Not yet possible" Consequences items of `ADR-0043` (line 179), `ADR-0044` (line 162), `ADR-0056` (line 188) and `ADR-0060` (line 156) in `ARCHITECTURE/decisions/` - read only, for nit 1.
- Code, read only, to confirm the new observation: `hilclaw/check_definition.py` (module docstring and `definition`) and `hilclaw/tools.py` `default_registry` docstring.
- `ARCHITECTURE/Requirements.md` line 107 (OD-18 row; search `ADR-0070`).
- `ARCHITECTURE/OpenDecisionProposals.md` line 319 (the ADR-0070 adopted bullet of OD-18) and line 324 (sub-question ⑩).
- `ARCHITECTURE/StandardScenarios.md`: 검사 규칙 (lines 13-29), the `# 검사 결과` heading (line 168), the `2026-10-16 (3차, 승인된 기록의 정정 ...)` paragraph (line 228) as the model of a correction paragraph, and the `2026-10-16 (4차, ...)` paragraph (line 230, the steps it re-checked).

## Acceptance Criteria

1. **ADR-0070**:
   - **NumPy sentence (line 110)**: the last sentence becomes true of the code at `dca5f2d` and later, in the observation voice of the bullet, e.g. "Building the default registry then imported NumPy through `hilclaw/mock_check.py`, a dependency the package already has (`pyproject.toml`); since task T-0216 (`dca5f2d`) it imports the modules that pull NumPy only at the first call of `correctness.check`, so building the registry imports none." The executor confirms the second half against `hilclaw/check_definition.py` before writing it. No other sentence of the bullet is edited.
   - **Nit 1**: one clause, in the Status bullet at line 9 or at line 111 (executor's choice; not both unless needed), saying why the ADR-0056 and ADR-0060 sentences are replaced while the "Not yet possible" items of ADR-0040 to ADR-0048 are only less exact, as the cited texts support it. The list of what is replaced and what is less exact is unchanged.
   - **Nit 3 (line 38)**: alternative (c) also names `end_line_failed` when the append of the end line fails, citing ADR-0047 decision 5 (and ADR-0026 decision 3 if the record cites it there), e.g. "... ends with `operation_failure_invalid`, or with `end_line_failed` when the append of its end line fails (cited: ADR-0047 decision 5)". The reason given against (c) ("it would start a step and end the identity with a `failure` for a fault of registration") stays; if adding `end_line_failed` makes that reason less exact (the identity may stay open), adjust its wording minimally and say so in `## Result`. The choice of (a) is unchanged. If References lack an entry the edit cites, add it.
   - **One Status bullet** after the T-0213 pattern: "**Edited after acceptance on <execution date>** by task T-0217 (document mode)": the three edits in one sentence each or one sentence together, "No decision changed meaning", and that the objection window of the notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6205474647 (until 2026-10-23) is unchanged.
   - Nothing else of ADR-0070 changes: decisions 1 to 5, the Walk-through, Limits, Alternatives, A-13 reading, Name check, Boundaries.
2. **Other ARCHITECTURE files**:
   - **Requirements OD-18 row (line 107)**: in the ADR-0070 sentence, "하위 질문 ①·⑤·⑧·⑭·⑱" becomes "하위 질문 ①·⑤·⑧·⑩·⑭·⑱". Nothing else of the row changes; OD-18 stays `제안됨`; the register keeps 30 rows.
   - **OpenDecisionProposals line 319**: align its paraphrase of alternative (c) the same way as nit 3 (Korean, like its neighbours) only if the executor judges it states the ending as complete; otherwise leave it and say why in `## Result`. No other line is edited. If it is not edited, it is not in the final diff.
   - Other records named in ADR-0070's "less exact" list (ADR-0016, ADR-0021, ADR-0040 to ADR-0048, ADR-0069) and ADR-0056/ADR-0060 are **not edited**; that list stays a follow-up for the integrator, as ADR-0070 says.
3. **StandardScenarios**:
   - Run the coverage re-check (CLAUDE.md "문서 커버리지 재검사") by the 검사 규칙 over the steps the `2026-10-16 (4차, ...)` paragraph re-checked.
   - Record it as a clause appended to the `# 검사 결과` heading list (e.g. "ADR-0070의 승인 뒤 정정(관찰 하나를 T-0216 뒤의 코드에 맞춤, 대안 (c)의 끝맺음에 `end_line_failed`, 대체/덜 정확함 구분의 근거 한 구절 — 판정·결정 변화 없음)") and as one dated paragraph with the next free ordinal for the execution date (`2026-10-16 (5차, 승인된 기록의 정정 — ...)` if the date is 2026-10-16; on a later date, `(1차, ...)` of that date), in Korean, after the model of the 3차 paragraph at line 228. It names the edits (including the Requirements row) and gives the verdict - no verdict change and no gap, if that is what the re-check finds.
   - No scenario step or 비고 row is edited; earlier paragraphs are unchanged.
4. **No other file changes**: `README.md`, `PROCESS/PLAN.md`, `PROCESS/DRIVER.md`, `CLAUDE.md`, `.claude/`, `hilclaw/`, tests and CI stay untouched.
5. **Guarded exit**: if a nit turns out wrong on the cited texts, leave that part unchanged and record the argument in `## Result`. If a fix would change what ADR-0070 decides or which earlier sentence it replaces (for nit 1: moving a sentence between "replaced" and "less exact"), leave it unapplied and record it as a follow-up; do not invent a rule or an OD. If every part is left unchanged, finish DONE with no landing commit.
6. **Document checks**: every relative link in edited lines resolves; `git diff --check` is clean; line endings are LF; `git diff --stat origin/main` lists only files in `touchesFiles`.
7. **`## Result`** records the landed commit, the review rounds and findings, the exact new wording of each edit, the re-check outcome, any follow-up left, and any reviewer judgement on editing an accepted record in place during its objection window.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0217'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0217 --state all`. Then the session entry check of CLAUDE.md: `gh pr list --repo myungjoo/HIL-Claw --state open`, and issues #4, #5, #7, #8. An open PR that edits ADR-0070, the OD-18 row of Requirements, the OD-18 passages of OpenDecisionProposals or the 검사 결과 section makes the task BLOCKED ("open PR conflict"). None was open at planning time. The unlanded branch of T-0210 is not an open PR and does not block this task.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6205474647 (the ADR-0070 notice). Skip the driver's own comments, which end `— posted by driver`. An owner objection to ADR-0070 makes the task BLOCKED ("requirement unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0019 or HQ-0021 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing is built or run except read-only git/gh, grep and link checks. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0217-adr-0070-after-acceptance-fixes` from `origin/main`; **no PR**. Run the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round, given the branch name and this file's path. At most 7 rounds; past the cap without a final Approve, the task is BLOCKED. A result starting with `SECURITY` is BLOCKED. If no reviewer can be spawned, the task is BLOCKED; do not review your own work. Ask the reviewer to (a) re-check the planner's reading in `## Why` against the cited lines and the code, (b) confirm that no decision changed meaning, and (c) run the coverage re-check independently.
- **Landing**:
  - `git fetch origin`, rebase onto `origin/main`, and squash to one commit (`git reset --soft origin/main` after the rebase). A rebase that changed content goes back to review.
  - `git push origin HEAD:main` (fast-forward). If rejected: fetch, rebase, and retry at most 3 times.
  - Commit message in English. The subject starts with `T-0217:`. The body names the corrections and the coverage outcome, and says that nothing was built.
  - Trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0217`, then any attribution trailer the session requires.
  - Delete the task branch only after the push is confirmed, remote and local in separate commands. Then check out `main` at `origin/main`.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`. Do not edit `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call means BLOCKED; do not work around it. If the task-branch push is rejected, rebase and retry once, then return BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- No #5 comment is needed (DRIVER §9 is not triggered: no OD status change, no decision changed), unless the reviewer judges that a correction changes a reason for a decision; then record that judgement and leave posting to the driver.
- Fill in `## Result` on `main` after the push and leave it uncommitted for the driver (DRIVER §3-6). `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Any change to what ADR-0070 decides (the registration now, the mock-only default table, `no_backend` for `cpu_standin` runs, the seed source, the predicate, the one-parameter `default_registry`) and any change to `hilclaw/` or tests.
- Editing the earlier records ADR-0070 lists as "less exact" or replaced (ADR-0016, ADR-0021, ADR-0040 to ADR-0048, ADR-0056, ADR-0060, ADR-0069).
- A `correctness.check` call with fd 2 closed on Windows (T-0216's remaining limit); the `cpu_standin` operation of `correctness.check`; OD-18 sub-questions ①, ⑤, ⑧, ⑩, ⑭, ⑱; the run tools (T-0210, HQ-0021).
- PLAN checkboxes (P1-1 stays open).

## Follow-ups

## Result

- **Outcome**: DONE. Landed as `f9f2038` on `main` (document mode, fast-forward push from `408b15f`, one squashed commit, trailers `Reviewed-by: reviewer agent (1 rounds, Approve)`, `Task: T-0217`). No PR; the branch `claude/T-0217-adr-0070-after-acceptance-fixes` was never pushed and the local branch is deleted. Nothing was built or run; no `claude` process was started.
- **Checks before work**: `git log origin/main --grep='^Task: T-0217'` and `gh pr list --search T-0217 --state all` empty; no open PR. Issue #5 after the ADR-0070 notice (comment 6205474647): no further comment, so no owner objection and no answer to HQ-0013, HQ-0014, HQ-0016..HQ-0019 or HQ-0021. No new comment on #4/#7/#8 since 2026-10-15.
- **Code confirmed** (read only): `hilclaw/check_definition.py` imports `check_tool` / `mock_check` only inside functions (module docstring, `default_table`, the closure of `definition`); `default_registry` docstring says building imports no NumPy.
- **Edits (exact wording)**:
  - ADR-0070 Consequences, last sentence of "Code sentences a code task changes": "Building the default registry then imported NumPy through `hilclaw/mock_check.py`, a dependency the package already has (`pyproject.toml`); since task T-0216 (`dca5f2d`) the modules that pull NumPy are imported only at the first call of `correctness.check`, so building the registry imports none."
  - ADR-0070 decision 2 (c): "... the kind it raised is outside the contract and the call ends with `operation_failure_invalid`, or with `end_line_failed` when the append of its end line fails (cited: ADR-0047 decision 5). Either way it would start a step and end the identity with a `failure` (or, where that end line cannot be appended, leave it open or ended) for a fault of registration - ..." (the reason against (c) adjusted minimally, since with `end_line_failed` the identity may stay open; ADR-0047 line 96, in decision 5, carries both endings; ADR-0047 was already in References).
  - ADR-0070 Consequences "Not edited and now less exact" (nit 1, placed here, not in Status line 9): after "... as far as they name the registration" added "(each names it beside the tool function of `correctness.check`, itself not yet possible at that record, where the two replaced sentences name it beside the operation of `cpu_standin` alone, ADR-0060 as following from it: "and so")". The lists of replaced and less exact sentences are unchanged.
  - ADR-0070 Status, new last bullet: "**Edited after acceptance on 2026-10-16** by task T-0217 (document mode): ..." naming the three edits and the two aligned passages, "No decision changed meaning", and the objection window of https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6205474647 (until 2026-10-23) unchanged.
  - Requirements OD-18 row: "하위 질문 ①·⑤·⑧·⑩·⑭·⑱, run 도구의 등록". OD-18 stays `제안됨`; 30 rows.
  - OpenDecisionProposals line 319 (aligned, since it stated the ending as complete): "계약 밖의 종류여서 `operation_failure_invalid`로(끝 줄의 추가가 실패하면 `end_line_failed`로) 끝나고 — ADR-0047 결정 5 —". "어느 쪽이든 등록의 결함이 식별을 써 버린다" stays true and was not edited.
  - StandardScenarios: heading clause ", ADR-0070의 승인 뒤 정정(관찰 하나를 T-0216 뒤의 코드에 맞춤, 대안 (c)의 끝맺음에 `end_line_failed`, 대체/덜 정확함 구분의 근거 한 구절, 등록부 OD-18 행의 미결 하위 질문에 ⑩ — 판정·결정 변화 없음)" before " 후)"; new paragraph `2026-10-16 (5차, 승인된 기록의 정정 — ADR-0070의 결정 2 대안 (c)와 Consequences 두 항목, 등록부의 OD-18 행; 결정 변화 없음)` after the 4차 paragraph.
- **Coverage re-check**: rules re-applied to the four groups of the 4차 paragraph (S0-5·6, S1-3·4·6, S1-b-2·S2-2·S3-4·S6-3·S11-3, S8-2·3; S0-7, S2-3, S3-1~4; S5-1·2·3; S7-2, S9-3, S10-3): no verdict change, no gap; confirmed independently by the reviewer. No scenario step or 비고 row edited.
- **Review**: 1 round, Approve (fresh-context `dev-reviewer`, opus). It confirmed the planner's reading, the code observation, that no decision changed meaning and the re-check. Three optional nits, not applied (any change would need another round; none affects correctness): (1) the 5차 paragraph title does not name the Proposals alignment (its body ⑵ does); (2) the task's `## Why` cites "ADR-0047 line 77 (decision 5)", but line 77 is in decision 4 - decision 5's sentence is line 96, so the ADR's "cited: ADR-0047 decision 5" is right; (3) a denser alternative wording for the nit-1 clause quoting "its registration".
- **Reviewer judgement on editing in place during the objection window**: acceptable - follows T-0190/T-0193/T-0197/T-0207/T-0213, disclosed by the Status bullet; an objection would revert the record with its edits (Status line 11); the #5 notice text mentions none of the edited points, so no new §9 notice is needed.
- **Follow-ups**: none new; the ADR-0070 "less exact" list stays the integrator's follow-up, as the record says.
