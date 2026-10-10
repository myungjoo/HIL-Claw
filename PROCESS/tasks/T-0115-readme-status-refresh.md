---
id: T-0115
title: Bring the status sections of README.md up to date with what main holds
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: ["#5 A-12", "#5 A-13", "#9"]
dependsOn: []
touchesFiles: [README.md]
estimatedSize: {loc: 60, files: 1}
hq: []   # no owner-only decision and no OD closure: every sentence to be written states what a file on main already shows
---
## Why
`README.md` got its status sections from T-0005 (PLAN P0-5, 2026-10-06, commit `1ddc2d3`) and has not been touched since. 109 tasks later five of its statements are false, and one of them was already filed for a later document-mode edit (T-0021 `## Result`, line 222: "`README.md` line 36 ... is partly outdated now") that no task took up. A reader or a fresh agent session that starts at the README is told the following (line numbers of `README.md` at `main` `bb9311f`):

| Line | README says | What `main` shows |
|---|---|---|
| 3, 26 | "이 저장소는 아직 골격(bootstrap) 단계이다" | `PROCESS/STATE.json` `phase` is `P1`; PLAN P0 is ticked in full; `hilclaw/` holds 33 modules and the `harness/` sub-package. The second half of line 26 is **still true**: no runtime that performs an optimisation run exists (PLAN P2 has no ticked item). |
| 34 | "`.claude/agents/`와 기법 Skill은 아직 없다" | `.claude/agents/` holds `dev-planner.md`, `dev-executor.md`, `dev-reviewer.md` (PLAN P0-6). They are agents of the **development process**. Runtime agent definitions and technique Skills still do not exist. |
| 35 | "현재는 패키지 버전과 `PROCESS/STATE.json` 검증기만 있고" | See the module list of `hilclaw/` and `hilclaw/harness/`. |
| 36 | "저장 위치를 정하는 데이터 plane 레이아웃은 미결이다(Requirements OD-8)" | The directory tree is fixed by `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md` (OD-8 register row: confirmed for the P1 minimum). The isolation means and the form of a coder call's `output/` are still open. |
| 44-49 | The repository map | Missing: `ARCHITECTURE/decisions/` (37 records), `ARCHITECTURE/reviews/`, `.claude/agents/`, `.github/workflows/ci.yml`, `hilclaw.config.json`, `pyproject.toml`, `PROCESS/STATE.schema.json`, `PROCESS/proposals/`. |
| 60 | "CI는 아직 구축되지 않았으며, 그때까지는 아래의 로컬 실행이 CI를 대신한다" | `.github/workflows/ci.yml` runs on every pull request and push with five jobs (PLAN P0-3, P0.5-1 to P0.5-3, all ticked). The install line below it also misses the runtime dependency `numpy` (`pyproject.toml` `dependencies`). |

**This task corrects those statements and nothing else.** The README stays a pointer page (T-0005: "a pointer page, not a second source of truth").

It ticks **no PLAN checkbox**. It is upkeep of the deliverable of PLAN P0-5.

Planner's judgements (2026-10-10T04:4xZ, from the files at `main` `bb9311f`; **the reviewer is asked to re-check each**):
- **Why this item now.** No lock, no TODO / INTERRUPTED task file, no open PR. T-0088, T-0106 and T-0107 are BLOCKED on HQ-0005, HQ-0006 and HQ-0007 (no owner answer on #5). The planner re-checked the open PLAN items and the registered sub-questions of OD-4, OD-6, OD-8, OD-13, OD-16, OD-17 and OD-18 and found no slice that neither waits on the repository owner nor would have to invent its form: the rest of P1-1 waits on HQ-0005 (`blob.push` / `blob.fetch` on #5 B-2 and A-3; `profiler.collect` runs at an execution point, so it follows HQ-0005); P1-5 on #5 A-4; the rest of P0.5-4 on HQ-0007; the rest of P1-8 on the start of an instance, OD-23, OD-20, OD-29, OD-3 and the rest of OD-17; the result files and `build.json` on who builds and where an experiment runs (weighed and not taken by the planners of T-0104 and T-0106 as well). `hilclaw/layout.py` already covers every path of ADR-0004 and `hilclaw/harness/measurement.py` every function ADR-0007 names. The shared once-only write helper is deferred until 2026-10-16.
- **The weakest point, and the reviewer must weigh it first**: this is not an unchecked PLAN item, and T-0021 filed the line-36 part under "(integrator, document mode)". The planner reads that label as "outside that task's `touchesFiles`", not as a reservation: `README.md` is on the document-mode list of CLAUDE.md A-13, PLAN P0-5 was a driver task, and every sentence to be written is a fact a file on `main` shows. **If a reviewer reads the README as the integrator's or the repository owner's to edit, do not argue it out: land nothing and return BLOCKED ("requirement unclear") with that reading as the question.**
- **Second weak point - CLAUDE.md line 24** says "**CI 미구축**: 프로세스의 CI 단계는 CI 구축 전까지 로컬 테스트 재수행으로 대체한다". That sentence is the repository owner's rule text and **is not edited by this task** (nor is any other line of CLAUDE.md). The README states what exists (the workflow file and its jobs) and does not state, restate or change a rule of the process. The stale CLAUDE.md sentence is named in Follow-ups and in `## Result` for the integrator.
- **No decision is taken.** No OD is touched, no ADR is written, no file under `ARCHITECTURE/` changes, so the coverage re-check rule of CLAUDE.md does not apply.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) - mandatory for every task (§6)
- PROCESS/DRIVER.md line 3, §0, §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2, §3 "BLOCKED 사유" paragraph, §7 (the three development-process agents)
- CLAUDE.md - whole file. In particular "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer), "미결은 발명하지 않는다", and "현재 프로젝트 상태 주의사항" (read line 24 against `.github/workflows/ci.yml`; do not edit it)
- README.md - whole file (83 lines)
- PROCESS/tasks/T-0005-readme-three-layer-pointers.md - `## Acceptance Criteria` and `## Result`: the conventions the existing sections follow (Korean body, the owner's sections untouched, pointers instead of restatement, no per-item progress)
- PROCESS/PLAN.md - whole file (what is ticked); PROCESS/STATE.json - `phase` only
- `.github/workflows/ci.yml` - whole file (triggers, the five job names, the install steps, the commands each job runs)
- `pyproject.toml` - whole file (`requires-python`, `dependencies`, the `dev` group)
- ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md - "Decision" 1 (the tree and the table), 3 (the bullet on `output/`) and 10; ARCHITECTURE/Requirements.md - the OD-8 register row
- Listings and docstrings to look at, not to change: `ls hilclaw hilclaw/harness .claude/agents ARCHITECTURE ARCHITECTURE/decisions ARCHITECTURE/reviews PROCESS PROCESS/proposals`; the module docstring (first paragraph) of each module of `hilclaw/` and `hilclaw/harness/`; `hilclaw/tools.py` `default_registry` (lines 181-193: "The set is empty"); `hilclaw.config.json`
- PROCESS/STATE.json `humanQuestions` HQ-0007 (the merge guard `hilclaw/merge_guard.py` is on `main` and is **not registered** as a hook)
- .claude/skills/dev-item-address/SKILL.md (document mode: document checks instead of tests, steps 9 to 12 and 15) and .claude/skills/dev-code-review/SKILL.md (document-mode return path; the "no invented decisions" check)

## Acceptance Criteria
Conventions kept from T-0005 (not requirements of the owner; state them in one line each in the commit body):
- New and changed README text is **Korean**, like the sections it replaces; identifiers, paths, commands and job names stay as they are. The commit message is English.
- The owner's sections - the `# HIL-Claw` title, `## Objectives`, `## Agent 실행 시 참고 사항`, `## References`, `# License` - keep their wording **unchanged**, typos, the empty `- ` bullet and blank lines included (Requirements cites the README objectives as a requirements source). `git diff origin/main -- README.md` shows no changed or removed line inside them.
- The section names and their order under "현재 상태와 MVP 범위" to "로컬 검사" stay; sentences that are still true stay as they are. Change only what the table in `## Why` shows as false or missing, plus what the points below ask for.
- The README points and summarises; it does not restate rules. No per-task, per-module or per-ADR inventory and no count that goes stale with the next task (no "33 modules", no "37 records", no list of ADR numbers, no coverage percentage). For progress it keeps pointing at `PROCESS/PLAN.md` and `PROCESS/STATE.json`.

Content - **verify each statement against the files at execution time, not against this task file**; if a file says otherwise, the file wins and the difference is named in `## Result`:
1. **Status note (line 3) and "현재 상태와 MVP 범위" (line 26)**: no longer "골격(bootstrap) 단계". Say what is true: parts of the layer-2 tool package and the verification harness exist and are tested; the runtime that performs an optimisation run does not exist yet (no layer-1 runtime orchestration, PLAN P2). Do not name the phase as a literal in the README; point to `PROCESS/STATE.json` as it does today.
2. **Layer table (lines 34-36)**, column "현재 저장소에 있는 것":
   - Layer 1: `CLAUDE.md`, `.claude/skills/` (the two development-process skills) and `.claude/agents/` (the three development-process agents `dev-planner`, `dev-executor`, `dev-reviewer`, DRIVER §7). Say plainly that all of these serve the **development process** and that the runtime's own agent definitions, prompts and technique Skills do not exist yet.
   - Layer 2: the Python package `hilclaw/` (keep "가칭") with the C sources of the harness under `hilclaw/harness/`, tests in `tests/`. Describe what it holds **by kind, in one or two sentences**, each kind checked against the module docstrings - for example: validators and writers for the files of the data plane, the key schema, the content-addressed blob store, the frame in which tools are defined and exposed (command line and stdio MCP server) with a mock backend, the local build and run wrappers of `cpu_standin`, the timing and verification harness, and the two development tools (the `PROCESS/STATE.json` validator and the `gh pr merge` guard). Three limits must be stated or at least not contradicted: **no FR-10 tool is registered yet** (`tools.default_registry` is empty by design); the merge guard is **not** described as active or registered (HQ-0007 is open); nothing is said to be "complete" (PLAN P1-1, P1-5 and P1-8 are unticked).
   - Layer 3: still nothing in the source repository. Replace "레이아웃은 미결이다" by what ADR-0004 fixes: the output of a coder call belongs to the data plane, below the attempt directory of the run tree (link ADR-0004 instead of copying the path if the path makes the cell unwieldy); what the files of `output/` are and how they get there is open (OD-23, the isolation means of OD-8). Do not present the calibration kernels under `tests/harness/calibration/` as layer-3 output: they are test fixtures of the harness.
3. **Repository map (lines 44-49)**: keep the existing rows; add, one line each and linked, `ARCHITECTURE/decisions/` (decision records, ADR; say in a few words that a design-level Open Decision is closed there by the route of `PROCESS/DRIVER.md` §9 and link the section rather than restating the 7-day rule), `.claude/agents/`, `.github/workflows/ci.yml`, `pyproject.toml`, `hilclaw.config.json` (binding to the data repository, #5 A-1). `ARCHITECTURE/reviews/`, `PROCESS/STATE.schema.json` and `PROCESS/proposals/` may be folded into the existing `ARCHITECTURE/` and `PROCESS/` rows. No file-by-file inventory beyond this.
4. **"개발 절차"**: change a sentence only if it is false now. Check in particular the sentence on code mode ("Draft PR, 리뷰 사이클, 테스트 통과") against CLAUDE.md A-13 ("CI green(CI 구축 전: 로컬 테스트)"): it may stay, or name CI beside the tests; it must keep pointing at CLAUDE.md for the details and must not copy the BLOCKED list or the test rules.
5. **"로컬 검사" (line 60 onward)**: replace the first sentence. State that CI is `.github/workflows/ci.yml`, that it runs on pull requests and pushes, and name its jobs by what they check (Python gate - ruff and pytest; sh gate - shellcheck; C gate - clang build of the C sources and the harness calibration; test presence for every module of `hilclaw/`; line and function coverage of `hilclaw/`), with the thresholds pointed at (CLAUDE.md test rule), not restated as a rule of the README. Do **not** write that CI replaces, or is replaced by, the local runs: which of the two a process step relies on is CLAUDE.md's to say. Then keep the block of local commands and make it sufficient for what it claims: the runtime dependency has to be installed as well (take the way from `pyproject.toml` and the workflow; keep it to commands that work in a POSIX shell, C-7), and say in one line that the harness tests that build C need `clang` on the PATH (check how those tests behave without it - skip or fail - and write what you saw). **Run every command you write down** in the driver clone and confirm it exits 0; do not run an install command when the tools are already present in the pinned versions, and install nothing that `pyproject.toml` does not name. If a command cannot be run here (for example no `clang`), say so in `## Result` and write the sentence as "the workflow runs ..." instead of as a verified local instruction.

Do not invent (CLAUDE.md "미결은 발명하지 않는다"):
- No statement about when the runtime, a tool, the first run or a real backend will exist; no roadmap beyond the pointer to PLAN.
- No statement that an Open Decision is closed beyond what its register row says; no summary of an ADR's content beyond the few words asked for above.
- No README language policy, no badge, no new section, no contributor or installation guide.

Document checks (document mode replaces tests; list each with its outcome in `## Result`):
- Every relative link of the README resolves to an existing path (check with a short shell loop or by hand; `gh` is not needed), and every in-page anchor matches a heading.
- `git diff --stat origin/main` shows `README.md` only.
- A sweep of the changed sentences for the words "아직", "없다", "미결", "모든", "완료": each is true of `main` at the commit under review.
- The three limits of point 2 and the "do not" of point 5 are met (quote the sentences in `## Result`).

Process:
- Document mode (CLAUDE.md A-13): branch `claude/T-0115-readme-status-refresh`, the reviewer cycle of dev-item-address steps 10 to 12, then rebase on `origin/main` and push to `main` without a PR. The commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and the trailer `Task: T-0115`, and with the attribution line the session's instructions give, if any.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Delete the task branch only after the push to `main` is confirmed, with `git branch -d` and `git push origin --delete` as separate commands.

## Out of Scope
- Any edit of `CLAUDE.md` (line 24 "CI 미구축" included), `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills, the agents, any file under `ARCHITECTURE/`, `hilclaw/`, `tests/`, `.github/`, `.claude/`, `pyproject.toml`, `hilclaw.config.json`.
- The owner's README sections (Objectives, "Agent 실행 시 참고 사항", References, License).
- The README of the `HIL-Claw-data` repository (T-0021 follow-up, "owner or integrator").
- The sentences of Requirements, UsageCases, StandardScenarios or earlier ADRs that later records list as "less exact" (the integrator's).
- Anything HQ-0005, HQ-0006 or HQ-0007 asks; the registration of any hook.

## Follow-ups
- (integrator / repository owner) CLAUDE.md line 24 "**CI 미구축**" and the "(CI 구축 전: 로컬 테스트)" clause of A-13 describe a state that ended with PLAN P0-3; the rule text is the owner's and was not touched here.
- (driver / owner) HQ-0005 (T-0088): the rest of PLAN P1-1. HQ-0006 (T-0106): the live check of the MCP front. HQ-0007 (T-0107): the forbidden-command guard and the hook registration of PLAN P0.5-4. PLAN P1-5: `task.objective` (#5 A-4).
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`) (T-0094 `## Result`).
- (planner, when a caller exists) Whether `clang_build.compiler_version` is kept, changed to the rule of ADR-0035 or removed (T-0109); whether the refusal of a 0 in `gemm_contract` gets an exception class of its own (T-0113).
- (planner) After this task the planner of T-0115 knows of no further task that is executable without an owner answer before 2026-10-16; the next iterations may find no selectable task (DRIVER §3-3).

## Result
