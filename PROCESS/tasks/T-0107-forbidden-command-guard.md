---
id: T-0107
title: Let the `PreToolUse` guard of `hilclaw/merge_guard.py` also refuse the three commands DRIVER §1-5 forbids under Bypass permissions (`git push --force*` / `-f`, `rm -rf`, `gh repo delete`) - as the repository owner answers the HQ of this task (whether the guard is wanted, where it lives, and whether it gets tests) - without registering the hook
phase: P0.5
status: IN_PROGRESS
commitMode: code
coversReq: ["#5 D10", "#5 D12", "#5 D13", OD-18, "DRIVER §1-5"]
dependsOn: [T-0007]
touchesFiles: [hilclaw/merge_guard.py, tests/test_merge_guard.py]   # tests/test_merge_guard.py only under answer (2)(a); no settings file, no file under .claude/, .github/ or PROCESS/
estimatedSize: {loc: 130, files: 1}   # non-test: hilclaw/merge_guard.py only (262 lines today); the test file is excluded from the cap (D4)
hq: [HQ-0007]   # not to be executed before the repository owner has answered
---
## Why
PLAN P0.5-4 is the only unchecked item of phase P0.5. Its first half landed with T-0007 (`hilclaw/merge_guard.py`, the `gh pr merge` guard, PR #17, `438fa36`). Two things are left of it:

1. The registration of the hook in `.claude/settings.json` - the repository owner's action; the driver and its agents never edit that file (DRIVER §1-5).
2. PLAN P0.5-4, last clause: "D13(2026-10-06) 이후 금지 명령(`git push --force*`·`rm -rf *`·`gh repo delete *`)의 PreToolUse 가드도 같은 hook에서 검토(follow-up — 범위 포함 여부는 P0.5-4 task 작성 시 planner/executor가 §9 기준으로 정함; 오너 전용 결정 아님)". DRIVER §1-5 says the same and gives the reason: under Bypass permissions no permission prompt and no classifier stands between a session and these commands, and the deny list of `.claude/settings.json` works on the CLI path only; they are held "by discipline" today.

**This task is part 2.** It ticks **no PLAN checkbox**: P0.5-4 stays open until the hook is registered.

**Why it cannot start without the repository owner** (planner, 2026-10-10 UTC, from the files at `main` `fcf37c8`). Whether to write the guard is the planner's to judge, and the planner judges it worth writing: the three commands are the only actions DRIVER §1-5 forbids outright, and a guard is the only means that holds when discipline fails. What the planner cannot settle is the **test rule**, which is the repository owner's own (D12):
- CLAUDE.md test rule 5 and DRIVER §5: no test is added for hook scripts; the named exceptions are exactly two - the driver `STATE.json` validator and "the `gh pr merge` guard hook" - and for those two tests are mandatory. The repository owner's user-level rule says the same more strictly: no test for tooling code unless the user asks for it explicitly, and that rule overrides the repository's.
- The same rules require tests for every public function of a touched module of `hilclaw/` (rule 3) and a test file for every new module of `hilclaw/` (rule 4, enforced by the CI job `Test presence (hilclaw)`).
- A guard that reads shell command lines needs the quote-aware tokeniser of `hilclaw/merge_guard.py` (T-0007 took four review rounds to get it right, and its tests found the errors); a pattern over the raw command string would refuse every commit message, PR body or issue comment that only *mentions* `rm -rf` - and the task files of this repository mention it in nearly every `## Process` section. So the guard belongs in that module, "the same hook" as PLAN says. Then the two readings part: either the new part is part of "the `gh pr merge` guard hook" and its tests are mandatory, or it is a third tool and gets none.
- T-0007 `## Follow-ups` already recorded this: "the D12 exceptions name exactly two tested tools, so whether this guard gets tests needs the owner's word". The question was never put.

The planner does not choose between the two readings (CLAUDE.md "미결은 발명하지 않는다"; BLOCKED reason "요구 불명확").

## HQ question
(for the driver to record under DRIVER §8; reason `requirement-unclear`)

PLAN P0.5-4 leaves one part to the planner: a `PreToolUse` guard for the commands DRIVER §1-5 forbids under Bypass permissions (`git push --force*` / `-f`, `rm -rf`, `gh repo delete`), "in the same hook" as the merge guard of T-0007. T-0007 put it off with a question on your test rule that was never asked. (1) Do you want this guard written: (a) yes; (b) no - the discipline of DRIVER §1-5 and the deny list of `.claude/settings.json` on the CLI path are enough, and T-0107 is closed without a change? (2) If yes, where and with which tests - your rule (CLAUDE.md test rule 5, D12, and your user-level rule) allows tests for exactly two tools: (a) inside `hilclaw/merge_guard.py` - one hook command, one registration, the tokeniser that is already tested - and the new part counts as part of "the `gh pr merge` guard hook" (exception 2), so tests in `tests/test_merge_guard.py` are required; (b) inside `hilclaw/merge_guard.py`, with **no** test for the new part (the package total stays far above 80 %; test rule 3 is set aside for it by this answer); (c) something else (name the place and the tests)? (3) The merge guard has been on `main` since 2026-10-06 and is not registered in `.claude/settings.json`, which only you edit; PLAN P0.5-4 and the D15 migration wait on that. Is the registration still intended: (a) yes, you will register `python -m hilclaw.merge_guard` as a `PreToolUse` hook; (b) not for now? Not asked here: what exactly the guard matches (the executor's choice under review, listed in the task result), and any change of DRIVER.md or CLAUDE.md.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §8, §11 rows D10, D12, D13
- PROCESS/PLAN.md P0.5-4
- **The repository owner's answer to the HQ of this task** in `PROCESS/STATE.json` (`humanQuestions`, the entry whose `taskId` is `T-0107`: `decision`) and the comment it links on issue #5. **If that entry has no `decision`, do not start: return BLOCKED.**
- CLAUDE.md - 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" 1 to 5, "코멘트 최소화"
- **`hilclaw/merge_guard.py` - whole (262 lines)**: the module docstring (what the guard does and never does; exit 0 / exit 2; fails closed), `merge_invocations`, `_simple_commands` (the tokeniser: quotes, backslash and backtick continuation, `#` comments, redirections dropped, the separators), `_merges_in` (a `gh` word anywhere in a simple command), `_split_flags`, `evaluate`, `main`, `_LOOKS_LIKE_MERGE` (what makes an untokenisable command a refusal)
- `tests/test_merge_guard.py` (484 lines): `payload`, `FakeGh`, `run_main`, `NOT_A_MERGE`, `MERGES`, `REFUSALS`, the `evaluate` and `main` cases, `run_module` and the two entry-point cases
- PROCESS/tasks/T-0007-merge-guard-hook.md `## Result` ("Provisional choices", the review findings of rounds 1 to 4, "known limits") and `## Follow-ups`
- `.claude/settings.json` - **read only**: the `deny` list (`Bash(git push --force*)`, `Bash(git push -f *)`, `Bash(rm -rf *)`, `Bash(gh repo delete *)`) is the wording of the three commands on the CLI path
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md
- `.github/workflows/ci.yml` - read only (the six jobs; `Coverage gate (hilclaw)` holds the package total at 80 % lines and functions)

## Acceptance Criteria
### By the answer
- Answer (1)(b): change nothing. Write "not wanted (owner answer)" into `## Result`, with the link of the answer, and return; no branch, no PR.
- Answer (2)(a): everything below, the tests included.
- Answer (2)(b): everything below **except** the section "Tests"; no file under `tests/` changes, no test is added for the new part, and the existing tests still pass unedited. Say in the commit body, the PR body and `## Result` that test rule 3 is set aside for the new part by the repository owner's answer, with its link.
- Answer (2)(c), or an answer that fits none of these: do not implement. Return BLOCKED ("task needs re-planning") quoting the answer; the planner rewrites this file.
- The answer to (3) changes nothing in this task: the hook is registered by nobody here.

### Files
- `hilclaw/merge_guard.py` (edit) and, under (2)(a) only, `tests/test_merge_guard.py` (edit). **Nothing else.** No new module, no new dependency (standard library only), no edit of `.claude/settings.json`, `.claude/settings.local.json`, `.github/`, `pyproject.toml`, `CLAUDE.md`, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills or the agents.
- Python, because the module exists in Python and the tokeniser is reused - one line in the commit body and `## Result`.

### What must not change
- Everything the module does for `gh pr merge`: the return values and the errors of `merge_invocations`, `checks_problem`, `evaluate` for a command that holds none of the three forbidden commands, the exit statuses, the `merge guard: ` prefix on stderr, `TIMEOUT_SECONDS`, the signatures of the four public functions. Every existing test passes unedited.
- The guard only refuses. It grants no permission, prints nothing on stdout, runs nothing but the read-only `gh pr checks` it runs today, and deletes, pushes or edits nothing.
- The command line stays `python -m hilclaw.merge_guard` with no argument: one registration covers both the merge check and the new refusals.

### The refusals
A tool call whose `tool_input.command` holds, as a simple command (outside quotes, in any position a `gh pr merge` is recognised today - after `;`, `&&`, `|`, inside `$( )`, after `env X=1`, after `then`), one of the following is refused with exit status 2 and a one-line reason that names the forbidden command; `gh` is not called for it:
- **`git push` with a force flag**: at least `--force`, `--force-with-lease` (with or without `=<value>`), `--force-if-includes`, and a short-flag word that holds `f` (`-f`, `-fu`, `-uf`), in any position among the arguments of `push`; a `git` word is recognised the way a `gh` word is (`git`, `git.exe`, a path ending in either, any case), and options between `git` and `push` (`-C <dir>`, `-c <name>=<value>`) do not hide it.
- **`rm` with both a recursive and a force flag**: `-rf`, `-fr`, `-Rf`, `-r -f`, `-rvf`, `--recursive --force` and mixed forms, whatever the operands are (DRIVER §1-5 forbids the command, not a target).
- **`gh repo delete`**, with or without an operand or flags.
- A command line that cannot be tokenised (an unclosed quote) and that looks like one of the three - by a pattern in the manner of `_LOOKS_LIKE_MERGE` - is refused; one that cannot be tokenised and looks like none of the three and not like a merge proceeds, as today.
- **Text inside a quoted argument is never a forbidden command**: `git commit -m "never use rm -rf or git push --force"`, `gh pr create --body "... gh repo delete ..."`, `echo 'rm -rf x'` proceed. This is the reason the tokeniser is reused; a check of the raw string is not acceptable.
- Not refused: `git push`, `git push origin HEAD:main`, `git push --delete origin <branch>`, `git push -u origin <branch>`, `rm <file>`, `rm -f <file>`, `rm -r <dir>`, `rmdir <dir>`, `gh repo view`, `gh repo clone`, `git fetch --force`, `git checkout -f`, `git clean -fd`, `git reset --hard` (DRIVER §3-0 uses the last two).
- The forbidden commands are checked before any `gh pr checks` is run; a command line that holds both a forbidden command and a merge is refused for the forbidden command without a call of `gh`.
- A payload without a string `tool_input.command` proceeds, as today; no filter on `tool_name`.

### Cases left to this task - choose, implement, list each with one line of reason in the commit body, the PR body and `## Result`
- The names and the shape of the new code (recommended: one public function, for example `forbidden_command(command) -> str | None`, called from `evaluate`; private helpers beside `_merges_in`), and whether `merge_invocations` and the new function share one tokenisation.
- `git push` with a `+<refspec>` (a force push without a flag); `--no-force` and `--no-force-with-lease`; a short-flag word of `rm` or `git push` built from a variable (`$FLAGS`); `rm` reached through `xargs`, `find -exec`, `sudo`, `command`, a shell function or an alias; PowerShell forms (`Remove-Item -Recurse -Force`, `rd /s /q`, `del /s`) and `git push` in PowerShell quoting; a here-document body that holds one of the three as text (today's known limit for merges: refused).
- Each of these is a choice between a false refusal and a miss. Prefer the refusal where a refusal costs one BLOCKED task and a miss costs data; say which forms are **not** recognised under "known limits" - the guard is a second line behind the discipline of DRIVER §1-5, not a sandbox, and the docstring must not claim more.
- Update the module docstring and the `description` of the argument parser to what the guard now does. Keep comments minimal (CLAUDE.md "코멘트 최소화"); docstrings of the public functions may be as long as needed.
- If you read a point as changing what DRIVER §1-5 forbids (a fourth command, an exception for a path such as a scratch directory, a way to switch the guard off), do not decide it: return BLOCKED ("requirement unclear") with the exact question.

### Tests (answer (2)(a) only; `tests/test_merge_guard.py`, excluded from the size cap)
Helpers live in the test file and get no tests of their own (test rule 5). The tests pass on Linux (CI) and on Windows (the driver's clone). **No test runs a real `git push`, `rm` or `gh`**: every case goes through the functions, `main` with a replaced stdin, or the module entry point with a payload, and asserts the exit status and the reason only. Model the tables on `NOT_A_MERGE`, `MERGES` and `REFUSALS`.
- happy: every form of the three commands named under "The refusals" is refused through the new function, through `evaluate` and through `main` (exit 2, a `merge guard: ` line on stderr that names the command, nothing on stdout), also after a separator, inside `$( )`, after `env X=1`, with a Windows path of `git` or `gh`, on a continued line, and for a `tool_name` other than `Bash`.
- branch: every command of the "Not refused" list proceeds and `gh` is not called; a forbidden command together with a green merge is refused without a call of `gh`; a merge without a forbidden command behaves as before (the existing cases, unedited).
- negative: quoted mentions proceed (single quotes, double quotes, inside a `--body` value, after `#` in a comment); an untokenisable command that looks like one of the three is refused and one that looks like none proceeds; a payload without a command, with a command that is no string, and a payload that is no object behave as today.
- error: the guard still fails closed - a failure inside the new check ends in exit 2 with "the guard itself failed" (replace the new function by one that raises, as the existing case does for `evaluate`).
- each case chosen under "Cases left to this task" has at least one row that pins the choice, a known limit included (a row that shows what is not recognised).
- Test rules of CLAUDE.md / DRIVER §5 (D12): 1 the package total stays at or above 80 % lines and functions (99.47 / 100.00 on the T-0105 head) - record the two figures of the final head; 2 the four kinds of cases above; 3 every public function of `hilclaw.merge_guard` has tests, the new one included; 4 no new module; 5 no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (record the pass and skip counts on `origin/main` and on the final head), `python -m ruff check .` and `python -m ruff format --check .` exit 0. Install nothing.
- `git diff origin/main --stat` lists only files of `touchesFiles` (under (2)(b): `hilclaw/merge_guard.py` only); `git diff origin/main -- .claude` is empty; `git ls-files --eol` shows `i/lf` for the changed files. Record the line count of the non-test diff (cap 300 LOC / 5 files).
- CI on the PR: `gh pr checks <PR> --watch` ends with every check of the final head successful (six at planning time: `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`, `Coverage gate (hilclaw)`). Record the names, the run URL and the two coverage lines. Merge only then.
- After the squash-merge, check the `push` run on `main` and record its conclusion; if it is not `success`, do not fix forward: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0107'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0107 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (a PR touching a file of `touchesFiles` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0107-forbidden-command-guard` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0107`; executor commits end with the trailer `Task: T-0107`.
- **Your own shell calls**: the hook is not registered, so nothing checks them; hold DRIVER §1-5 yourself. Write commit and PR bodies to files outside the repository and pass them with `-F` / `--body-file`, so that a text naming the three commands is never an inline argument.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; past the cap without a final Approve, return BLOCKED). Ask the reviewer explicitly to (a) try command lines that hide one of the three commands from the guard and command lines that are refused though they hold none (quoting, continuation, separators, flags in other positions), and report each as a finding or as a known limit to be listed; (b) confirm that nothing of the `gh pr merge` behaviour changed; (c) confirm that the guard only refuses, runs nothing new and fails closed; (d) confirm that the test decision follows the repository owner's answer and nothing else; (e) confirm that no docstring claims the guard is complete or that the hook is registered; (f) re-check each provisional choice. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED - do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm that every check of the final head is successful, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0107`**. Delete the remote branch and the local branch in separate commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- After a failed CI run, read the whole failed log and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: return BLOCKED ("CI 3 consecutive failures").
- `## Result`: fill it in after the merge, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). No fenced code block in it. Record: the owner answer followed (with its link), PR and commit, review rounds and findings, the public API as landed, exactly which forms are refused and which are **known limits**, the provisional choices, the verification outcomes, the line counts, the language line, what the repository owner needs to know for the registration (the hook command is unchanged; a here-document body or an unquoted mention may be refused), and that this task ticks **no** PLAN checkbox.
- `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`. If a needed tool call is denied or fails, return BLOCKED rather than working around it.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Registering the hook, any edit of a settings file, any other way of activating the guard; confirming in a live session that the hook fires under Bypass permissions (the repository owner's, with the registration - T-0007 Follow-ups).
- Any change of what DRIVER §1-5 forbids; a guard for anything else (editing the settings files through a shell command, `git reset --hard` on a shared tree, merges through `gh api` or the web UI, `git branch -D`, `git clean`).
- The known limits of the merge part of the guard (T-0007 `## Result`), the hook timeout, the repository a merge really targets.
- The wording of CLAUDE.md ("CI 미구축"), dev-item-address step 13 and DRIVER §1-5 once the guard is active (integrator, with the registration).
- The runtime hooks of the product (PLAN P2-4, OD-18, OD-19): this guard belongs to the development process.
- A POSIX sh wrapper, a console-script entry point, a separate module or a script outside `hilclaw/`.

## Follow-ups
- (repository owner) The registration of `python -m hilclaw.merge_guard` as a `PreToolUse` hook in `.claude/settings.json` completes PLAN P0.5-4 and is the remaining precondition of the D15 migration; the notes for it are in T-0007 `## Follow-ups` and, after this task, in `## Result` here.
- (integrator, with the registration) CLAUDE.md "CI 미구축" and "(CI 구축 전: 로컬 테스트)" are out of date since P0-3 and P0.5-1 to P0.5-3 landed; dev-code-review line 15 likewise; DRIVER §1-5 "금지 동작은 드라이버·executor 규율로" once a guard is active.
- (driver / owner) HQ-0005 (T-0088): the rest of PLAN P1-1. HQ-0006 (T-0106): the live check of the MCP front. PLAN P1-5: `task.objective` (#5 A-4).
- (planner - not before 2026-10-16, the end of the objection windows of ADR-0025 and ADR-0029; code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`).
- (planner - judged and not planned on 2026-10-10) OD-13 sub-question 7 (the seed policy of a timing run) and OD-16 sub-question 6 (one build or equal flags for the verification and the timing executable) are design-level by DRIVER §9, but each touches a defence of OD-16 that no record has adopted and has no caller before HQ-0005 is answered; a record now would have to choose without a consumer. Re-judge when the contracts of `sim.run` / `board.run` exist.

## Result
