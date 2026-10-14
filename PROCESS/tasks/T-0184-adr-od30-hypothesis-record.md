---
id: T-0184
title: Write the ADR that settles the first part of OD-30 - the hypothesis record of a round (its file under the round's `decision/`, its frame, the members of one hypothesis, the vocabulary of its origin, how it maps to the round's candidates, and round 0) - and reflect it in the ARCHITECTURE registers; no verdict, no case file, no injection path, no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-11, FR-17, FR-15, OD-30, OD-8, OD-23, "#5 D6"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0059 at planning time; T-0176 is BLOCKED and takes its number only when it runs)
estimatedSize: {loc: 240, files: 4}   # one new record of about 160-200 lines; the rest are in-place edits of a few lines each
hq: []
---
## Why

PLAN P2-6 ("가설 레코드와 판정 ... 스키마·파일 자리는 **OD-30 종결 필요(§9 ADR 경로)**; 2층의 스키마 검증·쓰기와 1층 프롬프트(P2-1·P2-3)에의 반영을 포함. 수행 순서는 나열 순서(P2-5보다 앞) — 첫 run이 사례를 남기도록") is open, and no record of OD-30 exists. FR-17 (owner decision 2026-10-13) requires that the technique selection of a round leaves a **structured hypothesis record** - ① hypothesis ② basis ③ expected effect ④ origin (system or injected; the vocabulary = OD-30) - and FR-11 makes that record part of the decision log of the round. ADR-0004 gives the round a `decision/` directory owned by the selection role and leaves "further files" there open (its path table: "Further files: OD-23"). **This task writes the record that settles the hypothesis record itself** - the first and smallest part of OD-30. It ticks **no PLAN checkbox** (the verdict, the code and the prompts are later tasks).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-14 after `4bac339`). T-0176 (PLAN P1-1, OD-18 sub-question ⑰) is BLOCKED on HQ-0020; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are `runtime-acceptance` and block nothing here (T-0121, T-0149, T-0153, T-0155, T-0156 and T-0169 are DONE). P0.5-4 waits on the owner's hook registration; the run-tool contracts of P1-1 and what rests on them (P1-8's next records, P2-1's baseline, the `cpu_standin` operation of `correctness.check`) wait on HQ-0020. The "now less exact" sentences named by ADR-0047 / ADR-0053 are integrator follow-ups, not driver tasks. The hypothesis record needs neither a run tool nor the build answer: its members are statements, references and names, and every input it needs (FR-11/15/17/18, ADR-0002 `id.relation`, ADR-0004, ADR-0050 objective type) is landed. DRIVER §6 allows an item whose `dependsOn` is met to be taken across the phase boundary.

**Planner's judgements (the reviewer is asked to re-check each):**
- **Authority (DRIVER §9).** OD-30 is design-level and not on the owner-only list (#5 A/B items, C-6, OD-25, OD-3). The owner's decision of 2026-10-13 (FR-15/17/18) and its supplement are cited, not widened. So the record may decide, with the owner notice and the 7-day window. The OD-30 section of OpenDecisionProposals itself says that **gate-time and mid-run injection (② and ③) are a scope decision for the owner (HQ)**: this record must not touch them.
- **Data-plane schema.** CLAUDE.md A-13 lists "데이터 plane 스키마 변경(STATE/spec/eval/artifacts)" as a BLOCKED reason. This record **adds a new file in a slot ADR-0004 left open** (`decision/`, not `eval/`) and changes no member, value or version of an existing file (`STATE.json`, `instance.json`, `spec.json`, `eval.json`, `artifacts.json`, `events.ndjson`, key records) - along the D6 route that ADR-0029 (the spec file) and ADR-0018 (the `instance.json` frame) took. The verdict (whose natural place is `eval/`) is deliberately left to a later record. If the executor or a reviewer finds that the design needs any change to an existing file (for instance a member of `instance.json` for injected hypotheses, or a member of `spec.json` pointing to a hypothesis), that part is **not** decided: it goes to Boundaries, or, if the record cannot stand without it, the task is BLOCKED (`data-plane-schema-change`) with the question written for an HQ.
- **No invented catalog.** FR-17 and the OD-30 proposal mention "the catalog id of the technique to apply"; no catalog exists (OD-22 open; ADR-0058 decision 1 kept `guidance.techniques` empty for that reason). The record may say how a hypothesis refers to the technique entries of the round's specs (ADR-0002 `guidance.techniques`) or leave the reference open; it names no catalog entry and does not close OD-22.
- **No invented metric vocabulary.** The expected effect names "which metric moves in which direction". The only landed name is the objective type `latency_minimisation` (ADR-0050 decision 3). The record either builds the expected effect on landed names only, or leaves the metric vocabulary open with a stated placeholder rule; it does not coin metric names that FR-3 ④ / OD-1 / OD-13 leave open.
- **No writer assigned.** ADR-0004 decision 4: `decision/` belongs to the selection role, and which agent holds a role is OD-23. The record says the file is the selection role's and assigns no agent, prompt or tool. Enforcement ("가설 없는 기법 선택을 허용하지 않는다") is OD-18 and is not decided.
- **D16.** The record is written from documents and source alone. Nothing is built or run; no `claude`, board or API key is needed.

## Required Reading

Line numbers are those of `main` at `4bac339`; the text wins. Several ARCHITECTURE lines are very long: read them with `sed -n '<line>p' | cut -c...` or `fold`, never whole files at once. Read Python sources with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, size cap D4, trailers). Also §8 (lines 135-139: HQ and comment format) and **§9 whole (lines 141-148)**.
- CLAUDE.md, the whole file; above all "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer and the A-13 BLOCKED reasons).
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15); .claude/skills/dev-code-review/SKILL.md (document-mode path; the "no invented decisions" check).
- PROCESS/PLAN.md lines 37-44 (P2-1 to P2-8; above all **P2-6** line 41 and P2-7 line 42) and the header (line 3).
- ARCHITECTURE/Requirements.md: line 29 (FR-11), line 33 (FR-15), **line 35 (FR-17)**, line 36 (FR-18); the OD register rows OD-8 (line 97), OD-20 (109), OD-22 (111), OD-23 (112), **OD-30 (119)**.
- **ARCHITECTURE/OpenDecisionProposals.md, the OD-30 section (lines 411-426)**; the OD-23 section (from line 351) for the roster; the OD-8 section's paragraph on remaining files (line 106).
- ARCHITECTURE/StandardScenarios.md: 검사 규칙 (lines 13-28), S6 (lines 101-111), S11 (lines 122-131), and the 검사 결과 section (from line 168), including its newest dated paragraph as the model for yours.
- **ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md**: the tree (lines 23-79, the round at 36-51 and the path table row of `decision.md` at line 70), decision 4 (98-105, one writer role per directory), decision 9 (131-145, the layout version), Boundaries (178-188).
- ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md: decision 2 (30-72, the `id.relation`/`id.variant` rows at 52-53 and `guidance.techniques`), decision 3 (73-76).
- ARCHITECTURE/decisions/ADR-0050-od6-task-objective-members.md decisions 2 and 3 (48-64; the only landed objective type) and decision 5 (75-82). ARCHITECTURE/decisions/ADR-0058-od6-committed-gemm-spec-example.md decision 1 (35-42; why no technique is named).
- The model of form for a new data-plane file and its write: **ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md** (Status 3-11, decisions 1-7 at 26-91, Boundaries 121-134); ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md decision 2 (28-41, how a file's frame lets later records add members); ARCHITECTURE/decisions/ADR-0014-od8-whole-file-writes.md decisions 3-7 (37-85); ARCHITECTURE/decisions/ADR-0025-od8-instance-file-write.md decisions 3-7 (36-87). ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md decision 1 (the *string*/*integer* conventions) and "Record format" (line 146 on).
- ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md decision headings only (what "a turn" and the journal are), for the Boundaries on a round that never reaches evaluate.
- PROCESS/tasks/T-0179-adr-od6-committed-gemm-spec-example.md `## Acceptance Criteria` "Process" bullets: the model for the document-mode procedure and the owner-notice text.

## Acceptance Criteria

### The record (one new ADR, English, under `ARCHITECTURE/decisions/`, number = next free at execution time)

Sections in the order of ADR-0001 "Record format" (Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References), accepted under DRIVER §9 (owner notice, 7-day window). The Status says it answers **one part of OD-30** and that OD-30 keeps its status word `제안됨`. It quotes the owner only where an owner sentence exists (FR-15/17/18 decision of 2026-10-13 and its supplement, linked) and marks everything else as its own design. It decides:

1. **Place and name.** The file of the hypothesis record of round `<RRRR>`: one file under `runs/<run_id>/rounds/<RRRR>/decision/` (name it; for instance `hypotheses.json`), beside `decision.md`, which stays the human-readable narrative. Say why one file per round and not one per candidate (ADR-0004 decision 4 and the `decision/` row). Say whether it is written once (as ADR-0025 / ADR-0029) or may be replaced, and under which rule of ADR-0014; cite, do not restate, the steps.
2. **Frame.** The file as a whole: one JSON object in the text form the record chooses (cite ADR-0029 decision 2 if it adopts that form), its top-level members, and how later records add members (as ADR-0018 decision 2 does). Whether the file carries its own version or relies on the run's layout version (ADR-0004 decision 9, ADR-0024) - decide and give the reason.
3. **One hypothesis.** The members of one entry, at least: an `id` unique in the round; the statement (FR-17 ①); the basis (FR-17 ②: which kinds of basis exist - observation of an earlier attempt of the same run, a stored case (FR-18), external material identified by identifier + version (FR-14 ②) - and how each is referred to; where a referent has no landed form, say the reference is open rather than invent one); the expected effect (FR-17 ③; see the metric judgement in `## Why`); the origin (FR-17 ④ with its vocabulary, at least "system" and "injected" - spell the values); and the reference to the technique entries it applies, or a stated reason to leave it open (no catalog id). Give each member's type with ADR-0001's conventions and the values that are not values.
4. **Hypotheses and candidates.** How the record says which candidates of the round test which hypothesis, consistent with ADR-0002 `id.candidates` / `id.relation` (`single`, `same_technique`, `different_techniques`) and the N of the run (`candidates_per_round`, ADR-0028); whether a candidate may test more than one hypothesis and a hypothesis span several candidates. Say what the record does about causal misattribution (OD-30 proposal) - a rule, a recommendation, or a Boundaries item.
5. **Round 0.** Whether round `0000` (bring-up and baseline) has a hypothesis record; the OD-30 proposal says no - adopt or reject with the reason.
6. **An example** of one file for a round of N = 1 with one system hypothesis, built from cited example values only (the ADR-0027 run id, a round of `0001`); placeholder text where no source gives a value, as ADR-0050 / ADR-0058 do.
7. **Guarded exit.** If a point can only be answered by an owner-only item (#5 A/B, C-6 - including whether gate-time or mid-run injection is in the MVP -, OD-25, OD-3), by a change to an existing data-plane file, or by a new external dependency, do not decide it: return BLOCKED ("requirement-unclear", "owner-only-decision" or "data-plane-schema-change") with the question written for an HQ, before landing anything.

**Boundaries must name at least:** the verdict and cause of each hypothesis and its file (FR-17, `eval/` - the next record of OD-30); what happens to the hypotheses of a round that never reaches evaluate (NFR-1, OD-17); the case file under `db/` and the lookup (FR-18, P2-7); the form and place of hypotheses injected at instance start (FR-15 - whether `instance.json` or another run file carries them) and gate-time or mid-run injection (owner HQ per the OD-30 section); the order and share of injected versus system hypotheses; who derives hypotheses from material; the S6 metric (P2-8); which agent writes the file and how its presence is enforced (OD-23, OD-18); the code and the prompts (P2-6's later slices).

**Sentences of earlier records that become less exact**: list them (for instance ADR-0004's `decision/` row "Further files: OD-23") and **edit none of them**.

### Register edits (in-place, a few lines each, Korean as the documents are)

- `ARCHITECTURE/Requirements.md` OD-30 row (line 119): one **확정분** clause naming the new record and what it settles; the status word stays `제안됨`. Keep the register to a one-line summary (CLAUDE.md). No edit of FR-11/15/17/18 text unless a sentence there is made false (then report it under Follow-ups instead of editing).
- `ARCHITECTURE/OpenDecisionProposals.md` OD-30 section: one "채택분" line for the record in the style of the other sections; mark which proposal bullets it adopts, which it rejects, and which stay proposals.
- `ARCHITECTURE/StandardScenarios.md`: re-run the coverage check by its rules (lines 13-28) - S6, S11 and S0 are the ones touched - and add a dated paragraph (execution date) to the 검사 결과 section with the outcome; change no verdict unless the rules require it.
- No other file. Not README, PLAN, DRIVER.md, CLAUDE.md, any code, test, schema or `.claude/` file.

### Document checks

- Every relative link in the new record and the edited lines resolves. `git diff --check` is clean; `git ls-files --eol` shows `i/lf` for the new file.
- Size: the diff stays within 300 changed lines and 4 files.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0184'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0184 --state all`. Then the session entry check of CLAUDE.md: `gh pr list --repo myungjoo/HIL-Claw --state open` and issues #4, #5, #7, #8. An open PR that edits the OD-30 row or section, the 검사 결과 section, ADR-0004 or a file of `touchesFiles` makes the task BLOCKED ("open PR conflict"); none was open at planning time.
- Read the comments on issue #5 after `https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6166739084` (the OD-6 notice of T-0179). Skip the driver's own comments (ending `— posted by driver`). An owner comment that speaks to hypotheses, cases, injection or OD-30, or objects to ADR-0004 or ADR-0029, makes the task BLOCKED ("requirement-unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0020 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing needs to be built or run. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0184-adr-od30-hypothesis-record` from `origin/main`; **no PR**. Reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round, given the branch name and this file's path; at most 7 rounds (past the cap without a final Approve: BLOCKED). A result starting with `SECURITY` is BLOCKED. If no reviewer can be spawned, BLOCKED; do not review your own work. Ask the reviewer to (a) re-check the planner's judgements in `## Why`; (b) check every cited value and sentence against the cited record on `main`; (c) attack points 1-4 for a hidden change to an existing data-plane file, an invented catalog id or metric name, an assigned writer agent, and any decision on gate-time or mid-run injection; (d) run the coverage re-check independently.
- **Landing**: `git fetch origin`, rebase onto `origin/main`, squash to one commit (`git reset --soft origin/main` after the rebase; a rebase that changed content goes back to review), `git push origin HEAD:main` (fast-forward; if rejected, fetch, rebase, retry at most 3 times). Commit message in English; subject starts with `T-0184:`; the body says what the record decides, what it leaves open, the register edits and the coverage outcome, and that nothing was built or run. Trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0184`, then any attribution trailer the session requires. Delete the task branch only after the push is confirmed (remote and local in separate commands), then check out `main` at `origin/main`.
- **Owner notice (DRIVER §9)**: put a ready-to-post English text in `## Result`, in the form of the earlier OD notices (heading `### OD-30 - the hypothesis record of a round fixed by ADR-NNNN under DRIVER §9 (T-0184)`; what the record decides in six lines or fewer; what is cited from the owner and what is its own; the most contestable choice first; that verdicts, cases and injection stay open and OD-30 stays `제안됨`; the date the 7-day window ends; last line `— posted by driver`). Do not post it; the driver does.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **`## Result`**: fill it in on `main` after the push and leave it uncommitted for the driver (DRIVER §3-6). Record the commit, review rounds and findings, the answer to each of points 1-5 as landed, the less-exact sentences, the register edits, the coverage outcome, the owner-notice text and follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- The verdict and cause of a hypothesis and any file under `eval/` (next OD-30 record).
- Case files under `db/`, the lookup, the selection and quantity of cases (P2-7); the S6 metric (P2-8).
- The form and place of injected hypotheses at instance start, and gate-time or mid-run injection (owner HQ per the OD-30 section); any member of `instance.json`, `spec.json`, `STATE.json`, `eval.json`, `artifacts.json` or `events.ndjson`.
- Any technique catalog entry or catalog id (OD-22); any metric name beyond the landed ones.
- Which agent writes the file, prompts, hooks and enforcement (OD-23, OD-18, P2-1, P2-3, P2-4).
- Any code, test or schema file (the later code slice of P2-6); editing any accepted record.
- OD-18 sub-question ⑰ and HQ-0020 (T-0176); the run-tool contracts of P1-1.

## Follow-ups

- (planner, document mode, §9) The next part of OD-30: the verdict and cause of each hypothesis, its file and vocabulary (FR-17), building on this record; check first whether a file under `eval/` falls under the A-13 "data-plane schema change" reason.
- (planner, code mode) A reader/validator and writer of the hypothesis file in `hilclaw/`, once the record lands (P2-6's 2층 slice).
- (driver) Post the OD-30 owner notice from `## Result` (DRIVER §9).
- (driver/planner) T-0176 stays BLOCKED until HQ-0020 is answered.

## Result
