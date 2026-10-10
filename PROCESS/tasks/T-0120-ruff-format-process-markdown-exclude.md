---
id: T-0120
title: Keep `ruff format --check .` of the Python gate off the Markdown files under `PROCESS/`, so that a Python code block in a task file, a journal or a driver document, pushed to `main` by an unreviewed driver state commit, cannot turn `main` red again (the T-0063 / T-0064 incident); configuration only, no change of behaviour of the package
phase: P1
status: DONE
commitMode: code
coversReq: ["#9", "CLAUDE.md language policy (Python gate: pytest + ruff)", "DRIVER §2 (driver state commits)", "T-0064 follow-up"]
dependsOn: []
touchesFiles: [pyproject.toml]
estimatedSize: {loc: 4, files: 1}   # one setting of two or three lines in the ruff tables of pyproject.toml
hq: []   # no owner-only decision and no OD: the scope of a format check over process files; see the guarded exit in `## Why`
---
## Why
The Python gate runs `python -m ruff format --check .` (`.github/workflows/ci.yml`, step "ruff format --check"), on pull requests and on pushes to `main`. ruff 0.16.10, the pinned version, also formats the Python code blocks of Markdown files, and `.` reaches every tracked `.md` file. The driver pushes its state commits to `main` **without review and without a PR** (DRIVER §2: `STATE.json`, the journal, the `## Result` of a task file, a task file a planner wrote), so a Python block in such a file is first seen by CI on `main` itself.

That happened once. The `## Result` of T-0063 held a Python block that ruff would format differently; the driver's wrap-up commit `b6076cb` turned `main` red, the two first CI runs of the next PR (T-0064, #49) failed on a file that was no part of that PR, with the `pytest` step skipped, and `main` stayed red until the driver commit `b0e0595` ("fix the format of a code block in the T-0063 result"). T-0064 `## Result` recorded it "**For the planner**: whether Markdown under `PROCESS/` should be excluded from `ruff format --check .` (a change of `pyproject.toml` or of the workflow, a task of its own), so that a `Result` with a Python code block cannot turn `main` red again", and its last list repeats it as a planner follow-up. It was never planned. What stands in its place is a sentence, "No fenced code block in it", repeated in the `## Process` part of the task files since (54 matches of "fenced code block" under `PROCESS/tasks/` at planning time): a rule held by each executor's attention, for a failure that costs a red `main` and a failed PR of somebody else. **This task removes the cause.**

Facts at planning time (`main` at `6a08532`, ruff 0.16.10; verify each at execution time, the files win):
- `python -m ruff format --check .` reports "261 files already formatted": 84 tracked `.py` files and 177 tracked `.md` files (128 under `PROCESS/`, 42 under `ARCHITECTURE/`, 5 under `.claude/`, `CLAUDE.md`, `README.md`). With `--exclude PROCESS` on the command line it reports 133 files (84 + 49).
- `PROCESS/` holds no Python file: besides Markdown only `PROCESS/STATE.json` and `PROCESS/STATE.schema.json`.
- `python -m ruff check` does not read Markdown: `ruff check --show-files .` lists no `.md` file, and a Markdown text with an unused import in a Python block passes it. Only the format step is concerned.
- A Markdown text with the block `x = {  "a":1 }` piped to `python -m ruff format --check --diff --stdin-filename PROCESS/tasks/_probe.md -` is reported (exit code 1). The same call with `--force-exclude --exclude PROCESS` exits 0.
- `pyproject.toml` has `[tool.ruff]` with `target-version = "py311"` only, `[tool.ruff.lint]` with `extend-select = ["SLF001"]` and `[tool.ruff.lint.per-file-ignores]` (T-0119). No exclusion of any kind.

It ticks **no PLAN checkbox**. It is upkeep of the Python gate of #9 / PLAN P0-3, in the manner of T-0119.

Planner's judgements (2026-10-11, **the reviewer is asked to re-check each**):
- **Why this item now.** No lock, no TODO / INTERRUPTED task file, no open PR. T-0088, T-0106, T-0107, T-0116 and T-0117 are BLOCKED on HQ-0005 to HQ-0009, all unanswered on #5. No PLAN slice is executable without one of those answers (journal 2026-10-10); the shared once-only write helper stays deferred until 2026-10-16; the move of the OD-18 register row waits for T-0088 and T-0116. This is a planner-tagged follow-up that waits on nothing and answers a failure that did occur.
- **The weakest point, weigh it first - whether narrowing what the gate formats is this task's to do.** No document states which files the format step covers: T-0002 left ruff at its defaults, T-0003 wrote `ruff format --check .`, CLAUDE.md and #9 say "pytest + ruff" for the Python of layer 2 (CLAUDE.md: the language policy and its gates concern layer 2 only; `PROCESS/` is process state, not layer 2). DRIVER §9 lists the owner-only items and this is none of them; it is not a Requirements OD, so no ADR is in scope. No pin and no dependency changes. **If a reviewer reads the coverage of the gate as the repository owner's, or holds that process Markdown should stay under the format check, do not argue it out: land nothing and return BLOCKED ("requirement unclear") with that reading as the question.**
- **Second weak point - why `PROCESS/` only.** The follow-up names `PROCESS/`, and `PROCESS/` is where unreviewed commits land. The 49 other Markdown files (`ARCHITECTURE/`, `.claude/`, `CLAUDE.md`, `README.md`) change only through a reviewed task; a document-mode task also pushes to `main` without a PR, so the same failure is possible there, but whether those documents leave the format check is a wider choice and is left as a follow-up, not taken here.
- **Third - `pyproject.toml`, not the workflow.** A setting in `pyproject.toml` holds for the local run every task asks for (`python -m ruff format --check .`) and for CI alike; an option in `ci.yml` would make the two differ.
- **A-13 reading**: code mode (`pyproject.toml`). No new dependency, no data-plane schema, no workflow edit.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers, test rules D12) - mandatory for every task (§6)
- PROCESS/DRIVER.md §0, §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §2 (which commits are driver state commits and go unreviewed), §3 "BLOCKED 사유" paragraph
- CLAUDE.md - whole file; in particular "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙" (rule 5: no test for CI or tooling configuration)
- `pyproject.toml` (whole file) and `.github/workflows/ci.yml` lines 25-46 (how the gate installs and calls ruff; read only)
- PROCESS/tasks/T-0064-hw-tool-path-over-backend.md `## Result`: the paragraph on the first two CI runs of the PR and the line "**For the planner**" (search for `ruff format`); `git show --stat b0e0595` (the repair)
- PROCESS/tasks/T-0119-ruff-private-member-guard.md: `## Why` "Planner's judgements" and the review part of `## Result` (how a change of the gate's configuration with a guarded exit was handled)
- .claude/skills/dev-item-address/SKILL.md and .claude/skills/dev-code-review/SKILL.md

## Acceptance Criteria
### `pyproject.toml` - one setting
- After the change `python -m ruff format --check .` reads no Markdown file under `PROCESS/` and reads every other file it read before: all tracked `.py` files and the Markdown files outside `PROCESS/`.
- The form is yours among the settings ruff 0.16.10 offers; state the choice and the reason in `## Result` and the commit body. Order of preference, take the first that works as shown by the verification below:
  1. an exclusion that concerns the formatter only and Markdown under `PROCESS/` only (for example `[tool.ruff.format]` with `exclude = ["PROCESS/**/*.md"]`), so that a Python file added under `PROCESS/` later is still linted and formatted;
  2. an exclusion of the directory for ruff as a whole (for example `extend-exclude = ["PROCESS"]` under `[tool.ruff]`; not `exclude`, which would drop ruff's default exclusions). `PROCESS/` holds no Python file today; if this form is taken, say in `## Result` that a Python file added there later is outside both ruff steps.
- Nothing else changes: `target-version`, the `[tool.ruff.lint]` tables of T-0119, the pins, the dependencies, the pytest table. No file-type setting that turns Markdown formatting off for the whole repository, no preview mode.
- No other file changes: not `.github/workflows/ci.yml`, no file under `PROCESS/` (the driver's files; the sentence "No fenced code block in it" of older task files is not edited), no file under `hilclaw/` or `tests/`.

### Tests
- **No test is added and none is changed**: the change is configuration of a CI tool (CLAUDE.md test rule 5 and the repository owner's user-level rule on tooling).

### Verification (list each with its outcome in `## Result`)
- The facts of `## Why`, re-checked before the change (the file counts, that `ruff check` reads no Markdown, the incident commits).
- `python -m ruff check .` and `python -m ruff format --check .` pass. The number of files the format step reports before and after, and that the difference equals the number of tracked `.md` files under `PROCESS/` (`git ls-files 'PROCESS/*.md' 'PROCESS/**/*.md'`, counted without duplicates). `python -m ruff format --check --show-files .` or an equal means shows that no path under `PROCESS/` is left and that no path outside it was lost (compare the two lists, before and after).
- **The exclusion holds, shown without committing a file**: a Markdown text with a Python block that ruff would reformat (for example the block `x = {  "a":1 }`) piped to `python -m ruff format --check --force-exclude --stdin-filename PROCESS/tasks/_probe.md -` exits 0 with the new configuration (`--force-exclude` makes a named input obey the configured exclusions) and exited 1 on `origin/main`. If the stdin form cannot show it for the chosen setting, write the probe as an untracked file under `PROCESS/tasks/`, run `python -m ruff format --check .`, and remove that one file again by its name; `git status --short` is empty afterwards.
- **The check still bites elsewhere**: the same text with `--stdin-filename ARCHITECTURE/_probe.md` is still reported, and an unformatted Python text with `--stdin-filename hilclaw/_probe.py` is still reported.
- `python -m pytest` passes with the same number of tests as on `origin/main` (no test is concerned; this is the gate's own run).
- `git diff --stat origin/main` lists `pyproject.toml` only; `git ls-files --eol pyproject.toml` shows `i/lf`; the lines added and removed.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0120'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0120 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open`. An open PR that edits `pyproject.toml` is BLOCKED ("open PR conflict").
- Code mode (CLAUDE.md A-13): branch `claude/T-0120-ruff-format-process-markdown-exclude`, Draft PR with `T-0120` in the title and `Task: T-0120` as the last line of the body; the reviewer cycle with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) **re-check the planner's judgements in `## Why`, the weakest point first**; (b) run the probes itself; (c) confirm by the two file lists that nothing outside `PROCESS/` left the format step; (d) confirm that the lint tables of T-0119 and ruff's default exclusions are unchanged.
- Merge only with the PR checks green: `gh pr merge --squash --body` with the PR body (keeping `Task: T-0120`), then confirm the `push` run on `main` and delete the branch, remote and local in separate commands. Commit and PR text in English; the commit body names the incident (`b6076cb`, `b0e0595`), says why `PROCESS/` only and why `pyproject.toml`, and what the chosen form leaves uncovered. The only language touched is the TOML configuration of the Python gate; one line on that in `## Result`.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around.
- `## Result`: fill it in after the merge, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). Until this task's merge is on `main` the old rule still holds, so write this `## Result` without a Python code block. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- The Markdown files outside `PROCESS/`; turning Markdown formatting off as a whole; any lint rule, preview mode or pin bump; `.github/workflows/ci.yml`; a custom check script.
- Editing a task file, the journal, `PROCESS/DRIVER.md` or `PROCESS/PLAN.md`; removing the sentence "No fenced code block in it" from existing task files.
- CLAUDE.md, `ARCHITECTURE/`, `README.md`, `.claude/`, `hilclaw/`, `tests/`.
- Anything HQ-0005 to HQ-0009 ask; the task files of T-0088, T-0106, T-0107, T-0116 and T-0117.

## Follow-ups
- (planners, from the next task on) A task file no longer needs the sentence "No fenced code block in it" for the sake of the gate; whether it is kept for readability is the planner's choice.
- (planner / integrator) Whether the reviewed Markdown outside `PROCESS/` (`ARCHITECTURE/`, `.claude/`, `CLAUDE.md`, `README.md`) stays under the format check: a document-mode task pushes to `main` without a PR as well, so a Python block there is also first seen by CI on `main`.
- (planner, when ruff makes the rule stable or a second private import appears) A guard for `from hilclaw.x import _name` (`PLC2701`; T-0119).
- (driver / planner) T-0116 `## Required Reading` says "search the long OD-8 row for `blob`"; since T-0118 that text is in the OD-8 section of `ARCHITECTURE/OpenDecisionProposals.md`. To be corrected when T-0116 is taken up again.
- (planner - after T-0088 and T-0116 are done or re-planned, document mode) The move of T-0118 for the OD-18 row, then a judgement on the rows of 1,100 to 1,800 characters (T-0118 `## Follow-ups`).
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`) (T-0094 `## Result`).
- (integrator / repository owner) CLAUDE.md "CI 미구축" and "(CI 구축 전: 로컬 테스트)" no longer match `main`; DRIVER §3-3 / §6 do not say whether the planner may create upkeep tasks for ticked PLAN items (journal 2026-10-10, T-0115).
- (driver / owner) HQ-0005 (T-0088) and HQ-0008 (T-0116): the rest of PLAN P1-1. HQ-0006 (T-0106). HQ-0007 (T-0107) and the hook registration of PLAN P0.5-4. HQ-0009 (T-0117): PLAN P1-5.

## Result
**DONE** - PR #86 (https://github.com/myungjoo/HIL-Claw/pull/86), squash commit `1bc96b6` on `main`; 1 review round (Approve, no Blocker / Major / Minor); branch deleted, remote and local.

### What changed
- `pyproject.toml`: a new table `[tool.ruff.format]` with `exclude = ["PROCESS/**/*.md"]`. 3 lines added (one of them blank), none removed. `target-version`, the `[tool.ruff.lint]` tables of T-0119, the pins, the dependencies and the pytest table are unchanged; no other file changed.
- **The coverage of the gate is narrower from this commit on**: `python -m ruff format --check .` no longer reads the Markdown files under `PROCESS/`. The reviewer asked that this be stated here so that the repository owner can object.
- Language: the TOML configuration of the Python gate only.

### The chosen setting and the reason
- The first form of the order of preference: an exclusion of the formatter only, for Markdown under `PROCESS/` only. It works as the verification shows, so the second form (`extend-exclude` for ruff as a whole) was not needed.
- Reason: a Python file added under `PROCESS/` later is still linted and formatted (probe below), ruff's default exclusions are not touched (`exclude` of `[tool.ruff]` is not set), and the lint step is not concerned at all.
- The pattern is anchored at the project root: a directory named `PROCESS` elsewhere (`hilclaw/PROCESS/`, `tests/PROCESS/`) is not excluded (reviewer's probe). It also matches a Markdown file directly under `PROCESS/` (`PROCESS/DRIVER.md`, `PROCESS/PLAN.md`).
- What it leaves uncovered: the format of a Python block in a Markdown file under `PROCESS/` is checked by nothing now.

### Verification
- Landed check before starting: no commit with `Task: T-0120` on `origin/main`, no PR for T-0120, no open PR at all.
- Facts of `## Why` re-checked (`main` at `43a1888`, ruff 0.16.10). The counts are one higher than at planning time, because this task file was added: `ruff format --check .` reported 262 files (84 `.py`, 178 `.md`, of which 129 under `PROCESS/`). `PROCESS/` holds no Python file (besides Markdown only `STATE.json` and `STATE.schema.json`). `ruff check --show-files .` lists no `.md` file. `pyproject.toml` had no exclusion. `b6076cb` is the T-0063 wrap-up commit and `b0e0595` the repair (one line added to the T-0063 task file).
- `python -m ruff check .`: All checks passed, before and after.
- `python -m ruff format --check .`: 262 files before, 133 after. The difference, 129, equals the number of tracked `.md` files under `PROCESS/` (`git ls-files 'PROCESS/*.md' 'PROCESS/**/*.md'`, without duplicates).
- The two file lists: `ruff format` 0.16.10 has no `--show-files` option (it is refused as an unexpected argument), so the equal means was used: the `format_path; path=` lines of `python -m ruff format --check -v .`, before and after. 129 paths left, all Markdown under `PROCESS/`; no path outside `PROCESS/` left, none was added; 84 `.py` and 49 `.md` remain, none under `PROCESS/`.
- The exclusion holds, shown without a file in the tree: a Markdown text with the Python block of the task's example, piped to `python -m ruff format --check --force-exclude --stdin-filename PROCESS/tasks/_probe.md -`, exits 1 on `origin/main` and 0 with the change; with `PROCESS/_probe.md` it exits 0 as well.
- The check still bites elsewhere: the same text as `ARCHITECTURE/_probe.md` exits 1; the unformatted Python text as `hilclaw/_probe.py` exits 1, and as `PROCESS/x/_probe.py` exits 1 too (a Python file under `PROCESS/` stays under the check).
- `python -m pytest`, local (Windows, Python 3.14): 12089 passed, 295 skipped, the figures recorded for `origin/main` by T-0119 (no Python file changed; the local run was made on the branch only). CI (Linux): 12384 passed on the PR run and on the push run, the figure of the push run of T-0119.
- `git diff --stat origin/main`: `pyproject.toml` only, 3 insertions; `git ls-files --eol pyproject.toml`: `i/lf`.
- PR checks green before the merge (run 38071618993: Python gate 3.11 and 3.14, Coverage gate, Test presence, sh gate, C gate; the format step reports 133 files). The push run on `main` for `1bc96b6` (run 38071807205) succeeded, all six jobs, 133 files in the format step.
- No test was added and none was changed.

### Review (1 round, Approve)
- The reviewer re-checked the planner's judgements and agreed with each, the weakest point first: no document puts Markdown under ruff; CLAUDE.md applies the Python gate to layer 2 and `PROCESS/` Markdown is process state; the present coverage came from the default behaviour of the pinned ruff and the `.` of the workflow, not from a recorded decision; it is no owner-only item of DRIVER §9, no Requirements OD and no BLOCKED reason. It weighed the opposite reading (a process loosening its own gate) and found that only the format of Python blocks in files DRIVER §2 already exempts from review is given up. The "requirement unclear" exit was not taken.
- It ran the probes itself on both revisions (eight Markdown names and four Python names, with the results above), compared the two file lists (262 and 133, the 129 lost paths equal to the tracked Markdown under `PROCESS/`), and found by `ruff check --show-settings` that the only difference is `formatter.exclude`: the default exclusions of the file resolver, `extend_exclude` and the linter section are identical, and `SLF001` behaves as before.
- Nit, no change asked: the figures 261 / 128 / 177 of `## Why` are 262 / 129 / 178 on the base of the PR (this task file). The figures above are the current ones.

### Follow-ups
- None new. Those of `## Follow-ups` stand; the first two are the ones this task opens: the sentence "No fenced code block in it" is no longer needed for the sake of the gate from the next task file on, and whether the reviewed Markdown outside `PROCESS/` stays under the format check is still to be judged.
