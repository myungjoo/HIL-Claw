---
id: T-0154
title: State in README.md that a logged-in Claude Code command line of the runtime user is a precondition of an instance (the owner's answer to HQ-0006, b-2; ADR-0054 decision 8; PLAN P1-9) - one short passage, README only, no code, and no `claude` process is started
phase: P1
status: DONE
commitMode: doc
coversReq: [C-7, FR-10, OD-18, "#5 D16"]
dependsOn: [T-0153]
touchesFiles: [README.md]
estimatedSize: {loc: 10, files: 1}
hq: []   # nothing to decide: the sentence is the owner's (HQ-0006 answer, b-2) and is already recorded in ADR-0054 and UC-1. HQ-0015 (CI starts no job) does not touch a document-mode task
---
## Why
The owner's answer to HQ-0006 (2026-10-13, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858), part (b-2), says of the record of the runtime self-check: "Its ADR records, as a derived consequence of C-7 ② and ③, that the runtime user's command-line login is a precondition of an instance (to be stated in README and UsageCases)". T-0153 landed the record (ADR-0054, commit `a5ed142`) and the UsageCases half (UC-1 "선행조건"). **The README half is still missing**: ADR-0054 Consequences says "The README sentence the owner asked for (O5) is a follow-up; README is not edited here", and `README.md` on `main` at `eb6410c` holds no sentence about a login (`grep -n -i -E "로그인|login" README.md` is empty). This task writes it. It ticks **no PLAN checkbox** (P1-9 stays open until its code lands); it closes the one documentation part of P1-9 that needs no code.

Planner's judgements (**the reviewer is asked to re-check each**):
- **Nothing is decided here.** The precondition is the owner's sentence and ADR-0054 decision 8 already records it; this task restates it in the README with links and adds nothing. DRIVER §9 is therefore not in play: no OD is closed, no ADR is written, no owner notice is due.
- **Why this item now.** GitHub Actions starts no job (HQ-0015, unanswered), so only a document-mode task can land. Of the document-mode follow-ups, the record of the run-tool contracts (PLAN P1-1; OD-13 sub-question 10) and the next slice of `correctness.check` wait on where the kernel of an attempt is (OD-23; OD-18 sub-question 10), and OD-8 sub-question 34 waits on a writer of `instance.json` and of specs no record has (OD-23, P2-1, P2-2) - a record of either would have to invent that (judgement of the T-0152 and T-0153 planners, taken over). The record of the owner's `T-0106 live check (owner)` cannot be made: no such comment exists on #5 (newest comments at planning time: the ADR-0054 notice 6146428610 and the HQ-0016 mirror 6146444000). This item has every input landed.
- **A-13 reading**: document mode (`README.md` only).
- **Coverage re-check**: CLAUDE.md asks for the StandardScenarios re-check when an `ARCHITECTURE/` document changes. None changes here, so none is due; say so in the commit body. If you find that an `ARCHITECTURE/` file must change, return BLOCKED instead of widening the task.
- **Session entry check (planner, 2026-10-13)**: one open pull request, #105 (branch `claude/T-0151-guard-refuses-child-claude-process`; files `hilclaw/merge_guard.py`, `tests/test_merge_guard.py`) - it does not touch `README.md`. HQ-0013, HQ-0014, HQ-0016 (`runtime-acceptance`) and HQ-0015 are unanswered.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap, commit trailers) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; the forbidden actions, the start of a `claude` child process among them; a denied or failed tool call is BLOCKED), §2 last bullets (never touch `PROCESS/STATE.json`), §3 "BLOCKED 사유" paragraph, §11 row D16
- CLAUDE.md - whole file; in particular "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer)
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15); .claude/skills/dev-code-review/SKILL.md (document-mode return path)
- **README.md - whole file (92 lines)**: the status note (line 3), "현재 상태와 MVP 범위" (lines 22-26), "세 층 모델" (lines 28-38; the 3층 row names the coder `claude -p`), "개발 절차" (lines 56-61; line 59 separates the development process from the runtime), "로컬 검사" (lines 63-75; what a developer needs on the development machine)
- **Issue #5, the owner's answer to HQ-0006**: `gh api repos/myungjoo/HIL-Claw/issues/comments/6135246858 --jq .body` - part (b-2) and the closing "Not decided here" sentence; quote from the comment, not from this file
- ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md: Context, the owner sentences O1 to O8 (lines 16-24; **O5** line 21, **O8** line 24), Limits L4 and L7 (lines 63, 66), **decision 8 "The precondition"** (lines 142-145), Consequences "The README sentence" (line 189), Boundaries (lines 194-203)
- ARCHITECTURE/UsageCases.md **UC-1 "선행조건"** (line 71) - the wording T-0153 landed; the README passage must say the same and no more
- ARCHITECTURE/Requirements.md **C-7** (line 64; ② Max subscription, ③ the orchestrator is a Claude Code session whose sub-agents call `claude -p`). The row is long: read it with a script, not as a whole file
- PROCESS/PLAN.md item **P1-9** (line 33), for what exists and what does not (the self-check has a record and no code)

## Acceptance Criteria
### Fixed inputs (not re-decided)
- **Owner** (HQ-0006 answer, b-2 / ADR-0054 O5): the runtime user's command-line login is a precondition of an instance, a derived consequence of C-7 ② and ③, to be stated in README and UsageCases. **Owner, kept open** (O8): the credential form for unattended runs (a login or a `setup-token`) and whether the command line is updated.
- D16 (CLAUDE.md): the precondition is of the machine that runs an instance, never of the development machine.

### The edit (`README.md` only)
1. **One short passage in Korean** (the language of the surrounding text), one bullet or one to three sentences, saying: on the machine that runs an instance, the Claude Code command line (`claude`) of the runtime user must be logged in before an instance starts; this follows from Requirements C-7 ② and ③. It links to the owner's answer (the #5 comment URL above), to `ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md` and to UC-1 of `ARCHITECTURE/UsageCases.md` (or to the file, if no stable anchor exists - check the anchor before using it).
2. **Placement** is the executor's, argued in the commit body in one line. The planner's suggestion: a new bullet at the end of "현재 상태와 MVP 범위" (after line 26). It must not go into "로컬 검사" or "개발 절차" in a way that reads as a requirement of a developer or of the development driver.
3. **The passage says the truth about today's state**: no runtime exists yet (README lines 3 and 26), and the self-check that will observe the precondition at an instance start has a design record and **no code** (PLAN P1-9 is open). It may say in one clause that ADR-0054 designs that check; it must not say or imply that anything checks the login today.
4. **The passage says that the development machine needs no such login** only if that can be said in one clause with a link to CLAUDE.md "개발 드라이버와 런타임의 구분"; otherwise it is left out. It restates no rule of that section.
5. **A sentence of README that the new passage would make false or inexact** (search the whole file for `claude`, `런타임`, `전제`, `필요`) is corrected in the same commit only if the correction is a few words; list every such hit and what was done in `## Result`. The planner found none.
6. No other line of `README.md` changes. In particular the 3층 row (line 36, less exact since ADR-0049) and the 2층 cell (line 35, stale since T-0124) are **not** edited - they are listed for the integrator in the `## Result` of T-0121 and T-0126.

### Do not invent
- No credential form (a login, a `setup-token`, an API key), no statement that an API key does or does not satisfy the precondition (ADR-0054 L7; OD-18 sub-question ⑯ (다)), no minimum version of Claude Code, no rule about updating the command line.
- No installation or sign-in instructions beyond naming the precondition; if a command is named at all, only `claude auth login` as the owner's sentence names it, and not as a step of a procedure this repository defines.
- No statement about what happens when the login is missing or expires during a run beyond what the owner said (the check "stops with the instruction to run `claude auth login`") - and that only if point 3 is kept true (the check has no code).
- No statement that the MCP front works in a live session, that the self-check exists, or about what a real `claude` does.
- **If writing the passage turns out to need a decision the owner's sentence and ADR-0054 do not carry, decide nothing, land nothing and return BLOCKED ("requirement unclear") with the exact question.**

### Document checks (document mode replaces tests; record each outcome in `## Result`; scripts used are not committed)
- The passage was compared clause by clause with the owner's sentence (the #5 comment), ADR-0054 decision 8 and UC-1 line 71: it says no more than they do, and nothing on the "Do not invent" list.
- Every link of the passage resolves (relative paths exist; an anchor, if used, exists in the target as GitHub renders it; the #5 URL is the comment 6135246858).
- `git diff --stat origin/main` lists `README.md` only; `git ls-files --eol README.md` shows `i/lf`; `git diff --check` is clean; `python -m ruff format --check .` exits 0 (if `ruff` is not installed on this machine, say so and skip - no Python file changes).
- After landing, read the `push` run on `main` once (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion. **A run that started no job for the reason of HQ-0015 is recorded as that and is neither re-run nor fixed forward**; it is not a BLOCKED reason of a document-mode task.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0154'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0154 --state all`; then the session entry check of CLAUDE.md (`gh pr list --repo myungjoo/HIL-Claw --state open`; issues #4, #5, #7, #8). An open PR that edits `README.md` is BLOCKED ("open PR conflict") - PR #105 does not. A newer owner comment on #5 that changes the answer to HQ-0006, objects to ADR-0054, or speaks of the login or the precondition is taken as fixed input or is BLOCKED ("requirement unclear") quoting it. An answer to HQ-0013 to HQ-0016 does not stop this task; name it in `## Result`.
- **D16, in practice**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag (not `claude --version`, not `claude auth status`); no stub of it is written or run. Nothing only the runtime has is required of this machine. Reviewers are spawned with the session's own agent tool.
- Document mode (CLAUDE.md A-13): branch `claude/T-0154-readme-runtime-login-precondition` from `origin/main`; **no PR**; the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round, given the branch name and this task file's path (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Tell each reviewer to write no file and to start no `claude` process. Ask the reviewer explicitly to (a) re-check the planner's judgements in `## Why`; (b) compare the passage with the owner's sentence, ADR-0054 decision 8 and UC-1 and look for a clause that widens or narrows them; (c) look for anything on the "Do not invent" list and for any wording that reads as a requirement of the development machine or as a claim that the check exists; (d) check the links and that no other line changed. **If a reviewer reads a point as needing the owner, return BLOCKED with the question instead of arguing it out.**
- Landing: `git fetch origin`, rebase onto `origin/main`, one commit; push with `git push origin HEAD:main` (fast-forward; if rejected, fetch, rebase, retry at most 3 times; a rebase that changed content goes back to review). Commit message: English; subject starts with `T-0154:`; the body says in a few lines what was added and where, that it restates the owner's sentence and decides nothing, that no `ARCHITECTURE/` document changed and so no coverage re-check was due, and that no `claude` process was started; trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0154`, then any attribution trailer your session requires.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Delete the task branch only after the push to `main` is confirmed, remote and local in separate commands, then check out `main` at `origin/main`.
- `## Result`: fill it in after the push, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). Record: the commit, review rounds and findings, the passage as landed and its place, the hits of point 5, the document checks, the conclusion of the push run, follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Any file other than `README.md`: every `ARCHITECTURE/` document (UC-1 and ADR-0054 are landed and are not reworded), `CLAUDE.md`, `PROCESS/`, `hilclaw/`, `tests/`, `.github/`, `.claude/`.
- The stale README sentences other tasks listed for the integrator (the 3층 row, the 2층 cell).
- The self-check code, a stub `claude`, starting the Claude Code program in any form.
- The credential form for unattended runs, the update of the command line, where the record of the check is stored (owner, open).
- PR #105 and anything HQ-0013 to HQ-0016 ask.

## Follow-ups
- (planner, code mode, only once GitHub Actions runs again - HQ-0015) The self-check of ADR-0054 in slices against a stub `claude` written by the tests (hints in the `## Result` of T-0153, "Note for the next planner"); the last slice ticks PLAN P1-9. Also then: the member `objective` in `hilclaw/instance.py` (ADR-0053), the harness slice of ADR-0052, the slices of ADR-0049 that need no container runtime.
- (planner, document mode, only when the comment exists) The recording of the owner's `T-0106 live check (owner)` observation in OD-18 sub-question ① (HQ-0006 answer, b-1).
- (planner, document mode, §9 judgement first) The record of the run-tool contracts (PLAN P1-1; OD-13 sub-question 10) and OD-8 sub-question 34 - both wait on OD-23 / OD-18 sub-question 10; a planner who takes one must first show that the record can be written without inventing where the kernel of an attempt is.
- (integrator, document mode) The README 3층 row and 2층 cell (T-0121 and T-0126 `## Result`).
- (driver / owner) HQ-0015 (T-0151, PR #105 waits for a green CI run); HQ-0013, HQ-0014, HQ-0016 (`runtime-acceptance`).

## Result
- **DONE.** Commit `ab7f27f` on `main` (document mode, no PR; `4d35986..ab7f27f`, fast-forward at the first push). Task branch deleted, remote and local. No new HQ.
- **Review**: 1 round, Approve (fresh-context `dev-reviewer`). Findings: (Low) the commit body of the branch commit lacked the lines the task's "Landing" asks for - written into the landed commit's message, no content change; (Nit) one bullet holds three sentences and six links - within the limit of point 1, no change asked. The reviewer agreed with every judgement of `## Why` it re-checked; it did not reproduce the "Why this item now" claims about HQ-0015 and the other follow-ups. No point was read as needing the owner.
- **The passage as landed** - one bullet, `README.md` line 27, the last bullet of "현재 상태와 MVP 범위" (placement: that section states what holds of an instance and of the runtime today; "로컬 검사" and "개발 절차" address a developer and the driver):
  > - instance의 선행조건: instance를 실행하는 머신에서 런타임 사용자의 Claude Code 명령줄(`claude`)이 로그인되어 있어야 한다(Requirements C-7 ②·③의 파생 — [오너 답변 HQ-0006](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858), [ADR-0054](ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md) 결정 8, [UsageCases.md UC-1](ARCHITECTURE/UsageCases.md#uc-1-loop-instance-정의실행) "선행조건"). instance 시작 때 이 조건을 관찰할 런타임 자체 점검은 ADR-0054에 설계 기록만 있고 코드는 아직 없다([PROCESS/PLAN.md](PROCESS/PLAN.md) P1-9). 이 선행조건은 개발 머신에 대한 요구가 아니다([CLAUDE.md](CLAUDE.md) "개발 드라이버와 런타임의 구분").
  - Point 4: the clause is "this precondition is not a requirement of the development machine", not "the development machine needs no login" - the host session that runs the driver is a Claude Code session, and CLAUDE.md keeps that apart from D16.
  - `claude auth login`, a credential form, a version, and what happens when the login is missing are not named.
- **Point 5 hits** (`claude`, `런타임`, `전제`, `필요` over the whole README): lines 3 and 26 ("런타임은 아직 없다" - consistent, unchanged); 35, 49, 50 (`.claude/` paths); 37 (3층 row, `claude -p` - out of scope, unchanged); 52 and 68 ("런타임 의존성", "필요하고" - Python dependencies and local checks, another sense); 59, 60 (development process). None is made false or inexact; none was edited.
- **Document checks**: clause-by-clause comparison with the owner's sentence (comment 6135246858, fetched), ADR-0054 decision 8 and UC-1 line 71 - no more than they say (executor and reviewer). Links: the four relative paths exist; the anchor `#uc-1-loop-instance-정의실행` is present in the HTML GitHub renders for `ARCHITECTURE/UsageCases.md` (contents API, `application/vnd.github.html`); the #5 URL is comment 6135246858. `git diff --stat origin/main`: `README.md | 1 +` only; `git ls-files --eol README.md`: `i/lf w/lf`; `git diff --check` clean; `python -m ruff format --check .` exit 0 (178 files). No `ARCHITECTURE/` file changed, so no coverage re-check was due. No `claude` process was started and no stub was written.
- **Process checks**: landed check empty (no `Task: T-0154` on `origin/main`, no PR); open PRs: #105 only (`hilclaw/merge_guard.py`, `tests/test_merge_guard.py`); newest #5 comments are 6146428610 (ADR-0054 notice) and 6146444000 (HQ-0016 mirror) - no newer owner comment, no answer to HQ-0013 to HQ-0016.
- **Push run on `main`**: run 38404509449 for `ab7f27f`, conclusion `failure` - all six jobs ended with 0 steps, annotation "The job was not started because recent account payments have failed or your spending limit needs to be increased". This is the HQ-0015 condition; not re-run, not fixed forward.
- **Follow-ups**: none new; those of `## Follow-ups` stand.
