---
id: T-0179
title: Write the ADR that settles what the committed GEMM spec example of PLAN P1-5 is - its technique list (a DRIVER §9 judgement on an empty `guidance.techniques`), which op_signatures it covers, which example values it carries, where the files live and in which text form, and what still has to land for P1-5 to be ticked - and reflect it in the ARCHITECTURE registers; no code
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-5, FR-8, OD-6, OD-22, "#5 B-4", "#5 D6"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0058 at planning time; T-0176 is BLOCKED and takes its number only when it runs)
estimatedSize: {loc: 220, files: 4}   # one new record of about 140-180 lines; the rest are in-place edits of a few lines each
hq: []
---
## Why

PLAN P1-5 ("GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 — OD-6 종결 필요(§9 ADR 경로)") is open. Every value the first example needs has been closed by a landed record except one:

- `op_signature` records and keys, `task.contract`: ADR-0008 decisions 4, 5 and 9 (the twelve op_signatures of the four projections × M ∈ {1, 32, 512}).
- `task.objective` and `schema_version` 2: ADR-0050 (owner answer HQ-0009; the first committed example carries no constraint value, O2).
- a run id: the example id of ADR-0027 decision 2; a machine: the fictitious machine of the ADR-0035 Example.
- the spec file's text form and name: ADR-0029 as carried over by ADR-0051; code in `hilclaw/spec.py` (version 2) and `hilclaw/spec_file.py`.
- **the technique: still lacking.** ADR-0050's restated example keeps `{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}` ("no source gives a technique of the stand-in catalog (OD-22)"). The planner follow-ups of T-0153..T-0159 name the way out: "a judgement under DRIVER §9 on whether the first example may carry an empty `guidance.techniques` (ADR-0002 allows the empty array)".

ADR-0002 Boundaries and ADR-0050 Boundaries leave "committed example files" to later code tasks, so the example files themselves are code mode. Before that code task can be written without inventing, one record has to settle the open design points of the example. **This task writes that record.** It ticks **no PLAN checkbox** (the files and their check are the next code task).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR. T-0176 (PLAN P1-1, OD-18 sub-question ⑰) is BLOCKED on HQ-0020; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are `runtime-acceptance` and block nothing here. P1-8's next records and ADR-0052 decision 7 (c) wait on the run-tool contracts of P1-1. P0.5-4 waits on the owner's hook registration. P2 items need OD-23 / OD-30 records that themselves rest on P1-1. P1-5 is the one PLAN item whose inputs are all landed.

**Planner's judgements (the reviewer is asked to re-check each):**
- **Authority (DRIVER §9).** OD-6 and OD-22 are design-level; neither is on the owner-only list (#5 A/B items, C-6, OD-25, OD-3). #5 B-4 (the first instance: shapes, M, fp32) is answered and is only cited. So the record may decide, with the owner notice and the 7-day window.
- **No invented technique.** FR-8 says "P1에서는 기법 후보 = repo 내 문서로 시작", but no catalog document exists. Writing a technique `id` or `text` would invent a catalog entry and settle part of OD-22; the record must not do that. Its choice is between an empty array and keeping a placeholder, or a reason why neither works (then BLOCKED, see Acceptance point 8).
- **No data-plane change.** An empty `guidance.techniques` is already valid in version 2 (ADR-0002 decision 2 table, "may be empty"; `hilclaw/spec.py` `_array(..., empty=True)`). The example files live in the code repository, not in a data plane. No member, value or version of any data-plane file changes.
- **No new dependency.** If the record says anything about a JSON Schema file for "the `spec.json` 스키마" of P1-5, it must not adopt a JSON Schema validator package (a new external dependency, CLAUDE.md A-13). Whether `hilclaw/spec.py` stands for the schema is the record's design.
- **D16.** The record is written from documents and source alone. Nothing is built or run, and no `claude`, board or API key is needed.

## Required Reading

Line numbers are those of `main` at `77b4ee4`; the text wins. Several ARCHITECTURE lines are very long: read them with `sed -n '<line>p' | cut -c...` or `fold`, never whole files at once. Read Python sources with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, size cap D4, trailers). Also §8 (lines 135-139: HQ and comment format) and **§9 whole (lines 141-148)**.
- CLAUDE.md, the whole file; above all "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer), "바이너리 금지".
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15); .claude/skills/dev-code-review/SKILL.md (document-mode path; the "no invented decisions" check).
- PROCESS/PLAN.md line 29 (P1-5) and the header (line 3: the "OD-n 종결 필요(§9)" convention).
- ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md: decision 2 (lines 30-72, the `guidance.techniques` row at line 63 and `feedback.attempts`), decision 3 (lines 73-76, `relation`), decision 7 (lines 97-102), **decision 8 (lines 103-132, the first example and its table)**, Boundaries (lines 161-171, especially line 164).
- **ARCHITECTURE/decisions/ADR-0050-od6-task-objective-members.md**: the model of form for this record. Status (3-12), decision 4 (65-74, O2), **Example (121-170)**, Consequences (189-196, slice (d)), Boundaries (197-206).
- ARCHITECTURE/decisions/ADR-0051-od6-spec-file-version-2.md: Limits and decisions 1 to 3 (lines 27-82), Boundaries (126-136).
- ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md: decisions 4, 5 (46-79) and **9 (113-132, the twelve op_signature records and keys)**; Boundaries (162-173).
- ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md: decision 2 (34-39) and Example (118-137). ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md decision 2 (32-46).
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md decision 7 and its example (around lines 80-100).
- `hilclaw/spec.py` lines 1-108 (module docstring and `validate`; `SCHEMA_VERSION = 2`, the technique and array rules) and `hilclaw/spec_file.py` lines 1-170 (module docstring: `parse`, `final_name`, `write`). Read only.
- ARCHITECTURE/Requirements.md: line 26 (FR-8), line 95 (OD-6 row), line 111 (OD-22 row).
- ARCHITECTURE/OpenDecisionProposals.md: the OD-6 section (from line 61) and the OD-22 section (lines 342-347).
- ARCHITECTURE/StandardScenarios.md: 검사 규칙 (lines 13-28) and the 검사 결과 section (from line 168), including its newest dated paragraph as the model for yours.
- PROCESS/tasks/T-0169-adr-od18-runtime-self-check-as-landed.md `## Acceptance Criteria` "Process" bullets: the model for the document-mode procedure and the owner-notice text.

## Acceptance Criteria

### The record (one new ADR, English, under `ARCHITECTURE/decisions/`, number = next free at execution time)

Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References, as ADR-0050 has them. It is accepted under DRIVER §9 (owner notice, 7-day window). It answers each point below, citing landed records for what they decided and deciding nothing they leave open:

1. **The technique list of the example.** Decide whether the committed example carries `"guidance": {"techniques": []}`, keeps a placeholder entry, or neither (then see point 8). State what an empty list means in a spec of a real call ("no technique is prescribed for this call") only as far as ADR-0002 already gives it, and say plainly that the judgement **does not close OD-22** and names no catalog entry. Write no technique `id` or `text`.
2. **Which op_signatures.** Decide whether the committed example is one file (for instance gate/up at M = 1, as ADR-0002 and ADR-0050 show), the twelve of ADR-0008 decision 9, or another set, and why. `id` values (`round`, `candidate`, `attempt`, `candidates`, `relation`) and the empty `feedback.attempts` are cited from ADR-0002 decision 8.
3. **Example values.** State that the run id is the ADR-0027 example and the machine the fictitious one of ADR-0035, and therefore that a committed example is a spec of correct form and **not the spec of a real call**. Do not pick a real machine's strings. `task.objective` is ADR-0050's `{"objectives": [{"type": "latency_minimisation"}], "constraints": []}`, with no constraint value (O2).
4. **Where and in which form.** Decide the repository path and file names of the committed example(s) (outside `ARCHITECTURE/`, outside `hilclaw/` unless you give a reason, never in a data plane), and whether their bytes must be accepted by `hilclaw.spec_file.parse` (the written form of ADR-0029/ADR-0051) or only by `hilclaw.spec.validate`. Say how a later test checks them; the test itself is the code task's.
5. **"`spec.json` 스키마" of P1-5.** Say whether the version-2 validator `hilclaw/spec.py` stands for the schema, or a JSON Schema file is also to be written; in the second case, no validator package is adopted (new external dependency) and the record says how the file is kept in step with `spec.py`. Then state the **completion criterion of P1-5**: what must land for the driver to tick it.
6. Keep every value the example shows exactly as the cited records spell it (the op_signature keys of ADR-0008 decision 9, the hw key of the ADR-0035 Example). If a value cannot be cited, do not make it up.
7. **Sentences of earlier records that become less exact**: list them (ADR-0002 decision 8 and Boundaries line 164, ADR-0050 Example table "the technique: still lacking" and Consequences slice (d), others you find) and **edit none of them**.
8. **Guarded exit.** If a point can only be answered by an owner-only item (#5 A/B, C-6, OD-25, OD-3), a data-plane schema change or a new external dependency, do not decide it: return BLOCKED ("requirement unclear" or the matching A-13 reason) with the question written for an HQ, before landing anything.

### Register edits (in-place, a few lines each, Korean as the documents are)

- `ARCHITECTURE/Requirements.md` OD-6 row (line 95): one clause that names the new record and what it settles. The OD-6 status word stays 확정 (P1 minimum already closed); do not change the OD-22 row's status (제안됨). Keep the register to a one-line summary (CLAUDE.md).
- `ARCHITECTURE/OpenDecisionProposals.md` OD-6 section: one "채택분" line for the record, in the style of the existing ones. Optionally one line in the OD-22 section saying that the example's empty list leaves OD-22 open.
- `ARCHITECTURE/StandardScenarios.md`: re-run the coverage check by its rules (lines 13-28) and add a dated 2026-10-14 (or execution date) paragraph to the 검사 결과 section with the outcome; change no verdict unless the rules require it.
- No other file. Not README, PLAN, DRIVER.md, CLAUDE.md, any code, test, schema or example file.

### Document checks

- Every relative link in the new record and the edited lines resolves. `git diff --check` is clean; `git ls-files --eol` shows `i/lf` for the new file.
- Size: the diff stays within 300 changed lines and 4 files.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0179'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0179 --state all`. Then the session entry check of CLAUDE.md: `gh pr list --repo myungjoo/HIL-Claw --state open` and issues #4, #5, #7, #8. An open PR that edits the OD-6 or OD-22 row or section, the 검사 결과 section, ADR-0002, ADR-0050 or a file of `touchesFiles` makes the task BLOCKED ("open PR conflict"); none was open at planning time (2026-10-14T10:18Z).
- Read the comments on issue #5 after `https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6164154089` (the HQ-0020 mirror). Skip the driver's own comments (ending `— posted by driver`). An owner comment that objects to ADR-0002, ADR-0008, ADR-0050 or ADR-0051, or that speaks to the technique catalog, makes the task BLOCKED ("requirement unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0020 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing needs to be built or run. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0179-adr-od6-committed-gemm-spec-example` from `origin/main`; **no PR**. Reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round, given the branch name and this file's path; at most 7 rounds (past the cap without a final Approve: BLOCKED). A result starting with `SECURITY` is BLOCKED. If no reviewer can be spawned, BLOCKED; do not review your own work. Ask the reviewer to (a) re-check the planner's judgements in `## Why`; (b) check every cited value and sentence against the cited record and the code on `main`; (c) attack point 1 for an invented technique or a hidden closing of OD-22, and points 4-5 for a new dependency or a data-plane change; (d) run the coverage re-check independently.
- **Landing**: `git fetch origin`, rebase onto `origin/main`, squash to one commit (`git reset --soft origin/main` after the rebase; a rebase that changed content goes back to review), `git push origin HEAD:main` (fast-forward; if rejected, fetch, rebase, retry at most 3 times). Commit message in English; subject starts with `T-0179:`; the body says what the record decides, what it leaves open, the register edits and the coverage outcome, and that nothing was built or run. Trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0179`, then any attribution trailer the session requires. Delete the task branch only after the push is confirmed (remote and local in separate commands), then check out `main` at `origin/main`.
- **Owner notice (DRIVER §9)**: put a ready-to-post English text in `## Result`, in the form of the earlier OD notices (heading `### OD-6 - the committed GEMM spec example fixed by ADR-NNNN under DRIVER §9 (T-0179)`; what the record decides in six lines or fewer; what is cited and what is its own; the most contestable choice first; that OD-22 stays open; the date the 7-day window ends; last line `— posted by driver`). Do not post it; the driver does.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **`## Result`**: fill it in on `main` after the push and leave it uncommitted for the driver (DRIVER §3-6). Record the commit, review rounds and findings, the answer to each of points 1-5 as landed, the less-exact sentences of point 7, the register edits, the coverage outcome, the owner-notice text and follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- The committed example files, any test, any code, any JSON Schema file (the next code task).
- Any technique catalog entry, any part of OD-22 beyond the judgement of point 1, FR-8's catalog documents.
- `memory_ceiling` or any constraint value (ADR-0050 O2, ADR-0052 decision 7).
- Editing ADR-0002, ADR-0008, ADR-0050, ADR-0051 or any other accepted record (point 7 lists, edits none).
- OD-18 sub-question ⑰ and HQ-0020 (T-0176); the run-tool contracts of P1-1; OD-23 (who writes a spec and how it reaches the coder).

## Follow-ups

- (planner, code mode, PLAN P1-5) Commit the example file(s) the record names, with a test that checks them as the record says; that task ticks P1-5 if the record's completion criterion is met by it.
- (driver) Post the OD-6 owner notice from `## Result` (DRIVER §9).
- (driver/planner) T-0176 stays BLOCKED until HQ-0020 is answered.

## Result

**DONE.** Landed on `main` as **aa00f86** (document mode, one squashed commit, fast-forward push; trailers `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0179`). The task branch was deleted locally and on the remote. This `## Result` edit is left uncommitted for the driver.

- **Record**: `ARCHITECTURE/decisions/ADR-0058-od6-committed-gemm-spec-example.md` (next free number; T-0176 took none).
- **Checks before work**: no earlier landing or PR for T-0179; no open PR; no comment on #5 after the HQ-0020 mirror (6164154089), so there was no owner objection and no answer to HQ-0013, HQ-0014 or HQ-0016..HQ-0020.
- **Review**: 7 rounds, a fresh `dev-reviewer` (opus) each round. Every round returned Approve with no blocking finding. Rounds 1-6 raised non-blocking findings and nits, all fixed: a wrong claim that "`repair` exactly when attempt > 1" cannot be stated in JSON Schema (it can, with if/then); a too-wide reading of OD-6 sub-question ③ (which is about several values of M only); S5-3 and S11 missing from the coverage paragraph; cited and own content marked inconsistently across the ADR and the register lines; the decision numbers of the "builds on" list; a redundant register clause. Round 7 approved and was the last round allowed. Its four non-blocking findings were not applied, because changing the text after the last round would have landed unreviewed content. They are listed under Follow-ups.
- **Answers as landed**:
  1. **Techniques**: the example carries `"guidance": {"techniques": []}`. By ADR-0002 this only means that no technique is named for this call. The record writes no `id` or `text`, does not close OD-22, and decides nothing about whether a real call may carry an empty list. The placeholder entry was rejected because it passes validation and would therefore state a catalog entry that does not exist.
  2. **Op_signatures**: one file, gate/up at M = 1. Twelve files would need twelve identifying tuples, and the records give only one. Whether one run may cover several op_signatures is said by no record (for M it is sub-question ③, still open). The twelve shapes are covered instead by check T4: for each shape in `FIRST_SHAPES`, the example with that shape's op side substituted passes `spec.validate`. The `id` values and the empty `feedback.attempts` are cited from ADR-0002 decision 8.
  3. **Values**: the run id is the ADR-0027 example; the machine is the fictitious one from the ADR-0035 Example; `task.objective` comes from ADR-0050 with no constraint. The example is a spec of correct form, not the spec of a real call.
  4. **Place and form**: `examples/spec/gemm-485b9bc494d477eb.json`, outside `ARCHITECTURE/`, `hilclaw/`, `tests/` and any data plane. Its bytes must be accepted by `hilclaw.spec_file.parse` and be in the written form (LF line ends, final line feed). It is not a file under a spec path. Checks for the later test: T1 parse accepts the bytes; T2 final LF and no CR; T3 the document equals the Example, with values from `gemm_contract` and `keys`; T4 the form check over the twelve shapes.
  5. **Schema**: the "`spec.json` 스키마" of P1-5 is the records (ADR-0002 + ADR-0050 for the document, ADR-0029 + ADR-0051 for the file), checked by `hilclaw/spec.py` and `hilclaw/spec_file.py`. No JSON Schema file is written, because some cross-field rules cannot be expressed in it and checking it would need a new dependency or a second validator. **Completion criterion of P1-5**: tick it when all of these are on `main`: (i) ADR-0058 and its register edits; (ii) the version-2 code (already there, T-0148); (iii) the example file with the Example content; (iv) a test under `tests/` that performs T1-T4 and passes CI.
- **Sentences of other records that are now less exact (point 7; none edited)**:
  - ADR-0002: decision 8, Consequences (JSON Schema; "The example becomes a valid spec only after…"), Boundaries (the first-GEMM values bullet, the JSON Schema files)
  - ADR-0050: the Example ("still lacking" and the sentence after it), Consequences slice (d), Boundaries
  - ADR-0035: Consequences line 175, Boundaries
  - ADR-0029: Boundaries ("a committed example with real values … a JSON Schema file")
  - ADR-0008: Consequences (still true of a real instance)
  - ADR-0004: the `spec.json` path-table row
- **Register edits**:
  - `Requirements.md` OD-6 row: one ADR-0058 clause added, and the closing "미정" clause narrowed to the values of a real call. Status stays 확정; the OD-22 row is unchanged (제안됨).
  - `OpenDecisionProposals.md`: an "채택분(ADR-0058 …)" line in the OD-6 section, and one line in the OD-22 section saying the empty list leaves OD-22 as it is.
- **Coverage re-check**: `StandardScenarios.md` 검사 결과, new paragraph "2026-10-14 (3차 …)" plus the heading suffix. No verdict changes and no gap; the reviewer re-checked independently each round and agreed.
- **Document checks**: all relative links resolve; `git diff --check` is clean; the new file is `i/lf`; the diff is 4 files, +161/−2.
- **D16**: nothing was built or run, and no `claude` process was started by the executor or by any reviewer.

**Owner notice (DRIVER §9), posted by the driver as https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6166739084:**

### OD-6 - the committed GEMM spec example fixed by ADR-0058 under DRIVER §9 (T-0179)

`ARCHITECTURE/decisions/ADR-0058-od6-committed-gemm-spec-example.md` (commit aa00f86; 7 review rounds, Approve). It is a design record: no code, nothing was run, no `claude` process was started.

**What it decides**
- The committed example of PLAN P1-5 is one version-2 spec file, `examples/spec/gemm-485b9bc494d477eb.json`: the first call of round 1 for `cpu_standin` x gate/up (2048->8192) at M = 1.
- Its `guidance.techniques` is the empty array. No technique `id` or `text` is written.
- Its bytes must pass `hilclaw.spec_file.parse` and be in the written form. A later test makes four checks, including a form check over all twelve first shapes in place of twelve files.
- The "spec.json schema" of P1-5 is the records plus `hilclaw/spec.py` and `hilclaw/spec_file.py`. No JSON Schema file is written.
- P1-5 is ticked once the example file and a passing test of those checks land; the version-2 code is already on main.

**Cited, not re-decided**: every value of the example. The run id is the ADR-0027 example, the machine is the fictitious one from ADR-0035, the op side and contract come from ADR-0008, `task.objective` comes from ADR-0050 (your HQ-0009 answer: no constraint value in the first committed example), and the `id`/`feedback` values come from ADR-0002. The example is a spec of correct form, not the spec of a real call.

**The record's own, most contestable first**
1. **P1-5 is satisfied by a fictitious-machine example plus a form check, not by real values or twelve files.** ADR-0029 Boundaries spoke of "a committed example with real values", and PLAN names M in {1, 32, 512}. If you want a real machine's profile or one file per M and projection, that is an objection to this point.
2. **No JSON Schema file.** Some cross-field rules (key derivation, candidate <= candidates, ordering of repair failures, operand shapes) cannot be stated in JSON Schema, and checking such a file would need a validator package (a new dependency) or a second validator.
3. **An empty technique list instead of the placeholder.** The placeholder would pass validation and so would name a catalog entry that does not exist.

**Stays open**: OD-22 (the technique catalog and any technique; the register row stays 제안됨); whether a real call may carry an empty list; OD-6 sub-question ③; real-machine values; OD-23. The OD-6 register word stays 확정.

The 7-day objection window ends on 2026-10-21 if this notice is posted on 2026-10-14; otherwise it ends 7 days after the posting date.

— posted by driver

**Follow-ups**
- (planner, code mode, PLAN P1-5) Commit `examples/spec/gemm-485b9bc494d477eb.json` with the content of the ADR-0058 Example, and a test under `tests/` that makes checks T1-T4 of decision 4. That task ticks P1-5 by the criterion of decision 5.
- (planner, document mode, small) Apply the four non-blocking round-7 findings to ADR-0058 and `StandardScenarios.md`:
  1. OD-12 is cited as the OD about whether a coder chooses a technique, but OD-12 covers only the coder's own search. This appears in decision 1, in Boundaries, and in ⑵ of the 3차 paragraph; make it "(OD-23; the coder's own search is OD-12)".
  2. In the Alternatives row 3, ADR-0035 is given a purpose it does not state; use its own words ("not the driver machine and not the repository owner's PC").
  3. Add S0-4 to the steps of the 3차 paragraph.
  4. In decision 5 (a), "sha256-derived" is not ADR-0002's wording; use "the name derived from its `record` (`hilclaw.keys`)".
- (driver) Post the OD-6 notice above on #5.
- (driver/planner) T-0176 stays BLOCKED until HQ-0020 is answered.
