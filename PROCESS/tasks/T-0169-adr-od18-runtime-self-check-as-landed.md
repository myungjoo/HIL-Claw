---
id: T-0169
title: Write the ADR that brings the record of the runtime self-check (ADR-0054) in line with the code landed by T-0160 to T-0167 - it records the values and conventions the record left to "the code task", settles the places where the record and the code now differ, and answers or registers the wording questions those tasks left - and reflect it in the ARCHITECTURE documents; no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, C-7, OD-18, "D16", "#5 D6"]
dependsOn: [T-0153, T-0160, T-0161, T-0162, T-0163, T-0164, T-0165, T-0166, T-0167]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0057 at planning time, after ADR-0056); Requirements.md only if the OD-18 register row must change, which the planner does not expect
estimatedSize: {loc: 260, files: 4}   # one new record of about 170-220 lines; the rest are in-place edits of a few lines each
hq: []   # design-level (DRIVER §9, D6): OD-18 is not on the owner-only list. O7 and O8 of ADR-0054 (where the record is stored; the credential form; whether the command line is updated before the owner's check) stay the owner's and are not touched. HQ-0016 is a runtime acceptance HQ and does not block a document task
---
## Why

ADR-0054 (T-0153, accepted 2026-10-13, inside its objection window until 2026-10-20) designed the runtime self-check of PLAN P1-9 and left several values explicitly to "the code task". Eight code tasks (T-0160 to T-0167) then built it in `hilclaw/selfcheck_*.py` and `hilclaw/selfcheck.py`; PLAN P1-9 is ticked. Each of T-0163 to T-0168 left the same document follow-up, now the oldest open one: the record is in places **less exact than the code**, the values the code chose are recorded **nowhere but in task files**, and three wording questions of the outcome table were applied in one reading without a record. P2-1 (the bring-up, the check's first caller) will be planned against ADR-0054; it must find one record that says what the landed check does.

Planner's judgements, for the reviewer to re-check:
- **Design-level, not owner-only.** Everything here is ADR-0054's "own design" or a value it gave to the code task (OD-18; DRIVER §9). No item is #5 A/B, C-6, OD-25 or OD-3. The owner's sentences O1 to O8 are not widened or narrowed; O7 and O8 stay open.
- **A new record, not an edit of ADR-0054.** The repository's convention (ADR-0045 Status, ADR-0054 Status: "No earlier record is edited; sentences of theirs that are now less exact are listed under Consequences") is followed: the new record states which sentences of ADR-0054 it makes less exact or replaces, and ADR-0054 is not edited.
- **Document mode** (CLAUDE.md A-13): only `ARCHITECTURE/` files change. **No code is changed.** Where the record would choose a reading that differs from the landed code, it does not edit code: it names a code follow-up instead (see point 3).
- **Why this item now**: it is the follow-up every one of T-0163 to T-0168 named as the next candidate; no TODO task exists, no PR is open, and the remaining code candidates (ADR-0055 bring-in, ADR-0052 harness slice) do not depend on it but P2-1 does.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, landed check, time limit) and §5 (task format, naming convention, size cap, test rules), §8 (HQ format), §9 (OD closing authority; owner notice; 7-day window).
- `CLAUDE.md` (all; especially "미결은 발명하지 않는다", "문서 커버리지 재검사", "개발 드라이버와 런타임의 구분" (D16), the branch and merge procedure, document mode).
- `.claude/skills/dev-item-address/SKILL.md` steps 10 to 12 (reviewer cycle of document mode).
- `ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md` - all 212 lines. The sentences most concerned: line 70 and line 91 (time limits "the code task's"), line 93 (the directory "only a check whose process is killed leaves it behind"), line 124 (row `front_refused`, conditions (a) and (b)), lines 125-127 (`passed`, `no_call`, `session_failed`), lines 137-140 (decision 7: members, the bound, "built from named members", exit status), line 187 (Consequences: "no module, entry or value is named or decided here"), line 188 (runtime acceptance items (i) to (viii)).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` section "Record format" (line 146 on).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md` lines 1-14 (the Status form of a record that makes sentences of earlier records less exact without editing them).
- The `## Result` sections (they hold the conventions as landed) of:
  - `PROCESS/tasks/T-0163-selfcheck-outcome-table.md` line 134 to end (the expressions of each row; "Conventions chosen"; the three wording questions under Follow-ups).
  - `PROCESS/tasks/T-0164-selfcheck-stream-evidence.md` line 140 to end (the constants read from the output and their standing; exactly one `system/init` event; the status-word rule; the two costs).
  - `PROCESS/tasks/T-0165-selfcheck-session-run.md` line 136 to end (the command-line constants and their standing; the three provisional names; the directory and `removed=False`; "Where the record and the code now differ").
  - `PROCESS/tasks/T-0166-selfcheck-report.md` line 135 to end (members as written; the bound of 64 characters and of 16 entries; the system-facts bound; exit statuses 10 to 15; "What the record's bound lets through").
  - `PROCESS/tasks/T-0167-selfcheck-command.md` line 128 to end (`python -m hilclaw.selfcheck`; 30 s and 300 s; `EXIT_FAULT = 20` shared with bad usage; no data root configured; a missing standard output refused before step one; standard error).
- The module docstrings (not the bodies, unless a statement must be checked) of `hilclaw/selfcheck.py`, `hilclaw/selfcheck_login.py`, `hilclaw/selfcheck_outcome.py`, `hilclaw/selfcheck_stream.py`, `hilclaw/selfcheck_session.py`, `hilclaw/selfcheck_report.py`, `hilclaw/selfcheck_server.py`, `hilclaw/selfcheck_wire.py`. The code on `main` is the authority where a task Result and the code differ; say so in `## Result` if you find such a difference.
- `ARCHITECTURE/OpenDecisionProposals.md` the OD-18 section, lines 275-311 (especially line 299, the adopted part of ADR-0054, and line 311, sub-question ⑯).
- `ARCHITECTURE/Requirements.md` line 107 (the OD-18 register row).
- `ARCHITECTURE/StandardScenarios.md` lines 13-26 (검사 규칙) and line 168 on (검사 결과; the newest re-check paragraph near line 184 concerns ADR-0054).
- Issue #5 comments after the answer to HQ-0015 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`) - only to see whether the owner objected to ADR-0054 or answered HQ-0016.

## Acceptance Criteria

### The record (one new file `ARCHITECTURE/decisions/ADR-NNNN-od18-runtime-self-check-as-landed.md`, NNNN the next free number; the slug may be shortened)

The record answers the points below. For each, it says whose the sentence is (**owner** with the O-number of ADR-0054, **cited** with the record, task or module, or **this record's own**), in the manner of ADR-0054 decision headers.

1. **Values the record left to the code task, as landed** (cited: the module and the task; the record adopts them as its own provisional values, and says they are provisional because no run on a runtime machine stands behind them):
   - the command `python -m hilclaw.selfcheck` (no argument, no option, nothing read from standard input) and the public `check()` composition; which module does which step, in one short table (the eight modules above);
   - the two time limits, 30 s for step one and 300 s for the session, fixed constants; what a too-short limit costs (`login_unreadable` or `session_failed`, never a pass);
   - the exit statuses: 0 for `passed`, 10 to 15 for the six other outcomes in table order, 20 for a fault of the check itself **and** for a bad usage (one value; standard error tells the two apart), and the list of values avoided (1, 2, 3, 4, 120, 126 and above);
   - standard error: nothing when a report was written, otherwise one fixed line naming the exception class, never its text;
   - a missing standard output refused before step one, so no session is spent for a report that cannot be written;
   - no data root configured: the check goes on with an empty `keep_out`, and what that leaves unchecked;
   - the member names and grouping of the report (`outcome`, `refused_a`, `refused_b`, `instruction`, groups `login`, `system`, `session`, `wire`), the absent-or-null rule, the bound (1 to 64 characters; at most 16 entries per list with a `..._dropped` member), and that the report is the output of a process and **not a data-plane schema** (ADR-0054 decision 7 stands);
   - the command-line constants of the session (`COMMAND` of `hilclaw/selfcheck_session.py`), the prompt text by reference to the module (not copied), and the configuration file named by its file name alone.
2. **Where the record and the code differ - settle each one.** For each, the record states the sentence of ADR-0054 it makes less exact and the sentence that now holds:
   - ADR-0054 line 93 ("only a check whose process is killed leaves it behind") against `removed=False` after a failed removal (T-0165), and the report member `session.directory_removed` (T-0166);
   - line 138 (a method name may hold `/`) against line 139 ("may hold … a path under the user's name"): a method name such as `/home/alice/x` passes the bound; and a 32-hex-character string (token-shaped) passes it too (T-0166 "What the record's bound lets through"). The record either accepts this as the cost of the bound as written, or narrows the bound **for later code** and names a code follow-up - it does not claim the landed code already narrows it;
   - "as the interpreter states them" (line 137) against the bound the code applies to the system facts (`+` allowed, else `other`);
   - line 187 ("no module, entry or value is named or decided here"), now overtaken by point 1;
   - "the report says which" (line 126, `no_call`) and the report members that say it.
3. **The wording questions of the outcome table** (T-0163, T-0164). For each, the record either decides (this record's own, with the reason) or registers it as an open part of OD-18 (a new part of sub-question ⑯, or a new sub-question with the next free number - check it on `origin/main` at the push). Wherever it decides, the decision must equal what the landed code does; **if the reviewer cycle concludes that the code's reading is wrong, the record registers the question instead of deciding against the code, and names a code follow-up** (no code change in this task):
   - (q1) whether a -32602 answered by the front to a `tools/call` of an unknown tool name (which the model, not the front, may cause) is an error of condition (a) of `front_refused` (code: yes, as written);
   - (q2) whether an `mcp_server_errors` entry for another server only undoes condition (b) of row 4 (code of `decide`: no, only an entry naming `hilclaw`; but the reader of T-0164 cannot produce that case, because any non-empty `mcp_server_errors` sets both members);
   - (q3) whether a connected `hilclaw` that is also named in `mcp_server_errors`, with something of the model's part missing, is `no_call` (code) or `session_failed` (row 7's example).
4. **The costs the code took to the safe side** (T-0164), stated plainly as consequences, with which runtime acceptance item would show whether they bite: a second `system/init` event makes every check `session_failed`; an omitted or mistyped `mcp_servers` reads a dropped front as `session_failed`, not `front_refused`; the `result` message is told by its `type` member alone; exactly one `system/init` event is read.
5. **What the report does not carry beyond decision 7** (T-0166): the error codes of condition (a), the server's status word, `torn`, an unplaceable line. Decide whether that is right for a report "built from named members" (this record's own), or register it; adding members is a code follow-up, not this task.
6. **Runtime acceptance items added** (D16): the provisional names and values the code took and that only a real `claude` on a runtime machine shows - at least `mcpServers` as the member of the configuration file, the comma form of one `--allowedTools` argument, the configuration file read by its file name against the working directory, the event-kind names `type`/`subtype`/`system`/`init`/`result` and the reply member `result`, whether a real session ends within 300 s and `claude auth status` within 30 s. List them as continuing ADR-0054's list (ix), (x), … or as a list of the record's own, and say that **none is closed by a driver task** and that HQ-0016 holds ADR-0054's items. Nothing here closes any item of HQ-0016.
7. **Limits and Boundaries**: what stays open, at least - everything of sub-question ⑯ (가) to (바); O7 and O8 (owner); what P2-1 does after each outcome and after status 20; whether the check runs again at a resume; the way a run gives the server to its agents (ADR-0010; OD-23); OD-18 sub-question ① (stays open; this record is not an observation).

### Do not invent (each stays open; a sentence that decides one is a review finding)

- Where the record of the check is stored (O7), the credential form for unattended runs and whether the command line is updated before the owner's check (O8) - owner.
- What round 0 does after any outcome or after status 20 (⑯ (가)); what the instance's log is (⑯ (나)); budget (⑯ (라)).
- That any provisional value is verified, or that any runtime acceptance item holds.
- Any value for a future bound, list cap or time limit that the code does not already have.

### Reflection in the ARCHITECTURE documents

- `ARCHITECTURE/OpenDecisionProposals.md`, OD-18 section: one adopted-part bullet for the new record after the ADR-0054 bullet (Korean, in the style of line 299); if point 3 or 5 registers anything, the sub-question line (Korean, one line per part). The OD-18 register row in `Requirements.md` keeps its status word; edit it only if the row names ADR-0054 in a way the new record changes (the planner expects no edit).
- `ARCHITECTURE/StandardScenarios.md`: re-check coverage under 검사 규칙 (CLAUDE.md "문서 커버리지 재검사"), extend the heading list of the 검사 결과 section with this record, and add a short dated paragraph saying what changed in the verdicts (the planner expects: no verdict change for S0-S11, since the check was already "designed"; state the outcome either way).

### Size

About 260 changed lines over at most 4 files. If the record cannot stay inside the cap with all seven points, keep points 1, 2 and 6 and register points 3 to 5 as open questions in one line each - and say so in `## Result` as a split proposal.

### Document checks (document mode replaces tests; record each outcome in `## Result`; scripts used are not committed)

- Every statement about the landed code was checked against the module on `main` (not only the task Result); every citation of ADR-0054 names the right decision and line; every sentence marked owner equals its source word for word.
- Negative sweep before the first review: no sentence states an item of "Do not invent" as decided; every enumerating sentence ("exactly", "only", "every", "closed") was checked item by item; every exit status named was checked against `hilclaw/selfcheck.py` and `hilclaw/selfcheck_report.py`.
- Every relative link resolves; the ADR number and any sub-question number are free on `origin/main` at the push; the count and numbering of OD rows are unchanged.
- `git diff --stat origin/main` lists only the new record and the edited documents; `git ls-files --eol` shows `i/lf` for the changed files; `git diff --check` is clean.
- After landing, read the `push` run on `main` once (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; it is not a BLOCKED reason of a document-mode task.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0169'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0169 --state all`; then the session entry check of CLAUDE.md (`gh pr list --repo myungjoo/HIL-Claw --state open`; issues #4, #5, #7, #8). An open PR that edits the OD-18 row or section, the 검사 결과 section, ADR-0054 or a file of `touchesFiles` is BLOCKED ("open PR conflict"); at planning time no PR was open. A newer owner comment on #5 that objects to ADR-0054 is BLOCKED ("requirement unclear") quoting it. An answer to HQ-0013, HQ-0014, HQ-0016, HQ-0017 or HQ-0018 does not stop this task; name it in `## Result` (an answer to HQ-0016 that reports a real observation is quoted as cited fact, not as the record's own).
- **ADR-0054 is inside its objection window until 2026-10-20**: build on it as landed and say in the new record's Status that it builds on a record still open to objection, and that it falls with ADR-0054 if that is reverted.
- **D16, in practice**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag, and nothing of `hilclaw.selfcheck*` is run - not even the test suite is needed for this task. Reviewers are spawned with the session's own agent tool and told to write no file and start no `claude`. Put the runtime acceptance items of point 6 in `## Result` with a ready-to-post notice text in the form of the HQ-0018 mirror (first line `### HQ-NNNN — T-0169: ...`, last line `— posted by driver`) and **do not post it** - the driver raises the HQ (DRIVER §8, reason `runtime-acceptance`).
- Document mode (CLAUDE.md A-13): branch `claude/T-0169-adr-od18-runtime-self-check-as-landed` from `origin/main`; **no PR**; the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round, given the branch name and this task file's path (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) re-check the planner's judgements in `## Why`; (b) check each statement about the landed code against the module on `main`; (c) attack point 3 - whether any decided answer differs from the code, and whether a registered question is in fact already decided by ADR-0054's words; (d) attack point 2 - whether the record now claims a privacy property (no path, no token in the report) the code does not have; (e) the negative sweep of "Do not invent".
- Landing: `git fetch origin`, rebase onto `origin/main`, one commit (`git reset --soft origin/main` and commit, only after the rebase; a rebase that changed content goes back to review); push with `git push origin HEAD:main` (fast-forward; if rejected, fetch, rebase, retry at most 3 times). Commit message: English; subject starts with `T-0169:`; the body says in a few lines what the record decides, what it registers, what it leaves open, the register edits, the coverage re-check outcome and that nothing was built or run; trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0169`, then any attribution trailer your session requires.
- **Owner notice (DRIVER §9)**: put the ready-to-post English text in `## Result` in the form of the ADR-0054 and ADR-0056 notices (heading `### OD-18 - the runtime self-check as landed (values, conventions and the record's corrections) fixed by ADR-NNNN under DRIVER §9 (T-0169)`; what the record decides in six lines or fewer; what is cited and what is its own; the provisional choices, most contestable first; what it registers; the register status word; the date the 7-day window ends; last line `— posted by driver`). Do not post it yourself unless the driver's spawn prompt tells you to; if you post it, record the comment URL.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Delete the task branch only after the push to `main` is confirmed, remote and local in separate commands, then check out `main` at `origin/main`.
- `## Result`: fill it in after the push, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6), unless the spawn prompt asks for it inside the landed commit (then say so as a deviation and touch nothing else under `PROCESS/`). No fenced code block in it. Record: the commit, review rounds and findings, the answer to each of the seven points as landed (for point 3, decided or registered, and the code follow-up if any), the sentences of ADR-0054 made less exact, the register status word before and after, the coverage re-check outcome, the document checks, the runtime acceptance notice text, the owner notice text or URL, and follow-ups with a "Note for the next planner". `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope

- Any code or test: `hilclaw/selfcheck*.py`, `hilclaw/__main__.py`, `pyproject.toml`, `tests/`. A reading that would change the code becomes a follow-up.
- Editing ADR-0054 or any earlier record, `README.md`, `ARCHITECTURE/UsageCases.md` (UC-1 already states the precondition - T-0154), PLAN, DRIVER.md, CLAUDE.md, the #5 body.
- P2-1 (round 0, what follows each outcome), the instance's log, where the report is kept (O7), the credential form (O8), budget, the nightly routine (D17, P2-10).
- The other follow-ups of T-0163 to T-0168 not about ADR-0054: the bring-in function of ADR-0055, the harness slice of ADR-0052, the docstrings of `check_tool.py`/`check_seed.py`, ADR-0055 decision 3's "not verified", ADR-0053 Consequences sentences and the `hilclaw/spec.py` docstring, OD-18 sub-question 17 and the run-tool contracts (PLAN P1-1).
- Closing any item of HQ-0013, HQ-0014, HQ-0016, HQ-0017 or HQ-0018.

## Follow-ups

- (planner, code mode, D12) Any code change point 2, 3 or 5 names (a narrower bound for method names, other report members, a different reading of q1-q3), as one small task each.
- (planner, code mode, D12) The bring-in function of ADR-0055 (B1 to B6; `output/` already existing is OD-23 sub-question 1 (가) and must not be invented); the harness slice of ADR-0052 (`hilclaw/local_run.py` must change how it waits).
- (planner, document mode, small) ADR-0055 decision 3's "not verified" include expectation (shown by T-0157's clang test on the CI runner); the ADR-0053 Consequences sentences and the `hilclaw/spec.py` docstring sentence that can now name `objective` (T-0168).
- (driver) The owner notice of this record; a `runtime-acceptance` HQ for the items of point 6.

## Result
