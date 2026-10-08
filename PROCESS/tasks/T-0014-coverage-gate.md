---
id: T-0014
title: Add the coverage gate for hilclaw/ (line >= 80%, function >= 80%) to CI
phase: P0.5
status: TODO
commitMode: code
coversReq: ["#5 D12", "#9"]
dependsOn: [T-0003, T-0009, T-0011]
touchesFiles: [.github/workflows/ci.yml, pyproject.toml]   # pyproject.toml only if HQ-0003 (1) = (a); a gate script file only if HQ-0003 (1)/(3) allow one — add its path here when the answer is in
estimatedSize: {loc: 150, files: 3}   # upper bound (stdlib tracer script); about 30 lines in 2 files with a pinned coverage tool
hq: [HQ-0003]
---
## Why
Owner decision D12 (2026-10-05, issue #5) adopted a coverage gate for the tool package: "**>= 80% line coverage and >= 80% function coverage** for the tool package; branch thresholds decided once data exists". CLAUDE.md test rule ① and DRIVER §5 rule ① already require every code-mode task to keep that level, but nothing measures it: executors have checked reachability by hand with the stdlib `trace` module (T-0004, T-0007, T-0008, T-0012, T-0013 `## Result`). PLAN P0.5-3 is the CI gate that makes the rule mechanical. It is the last item of phase P0.5 that is not waiting for another PLAN item (the rest of P0.5-1 waits for P1-2 / P1-3; the rest of P0.5-4 is the owner's hook registration).

The task is **BLOCKED on HQ-0003**. D12 fixes the two thresholds and the scope (`hilclaw/`) and nothing else. Three choices are open, and the first one is a reason for owner involvement under CLAUDE.md A-13 ("new external dependency"). HQ-0003, verbatim:

> PLAN P0.5-3 (coverage gate, D12: `hilclaw/` line >= 80% and function >= 80%) needs three choices D12 leaves open. (1) Tool: (a) add `coverage` (exact pin) to the `dev` dependency group, a new external dependency (A-13); or (b) a stdlib-only tracer (`sys.settrace` around pytest), a 100-150 line gate script that test rule 5 leaves untested? (2) Is "function coverage" = `def`s entered at least once / all `def`s in `hilclaw/` (methods and nested functions counted; lambdas, comprehensions and class bodies not)? (3) Are the thresholds on the package total, and may a CI check script live outside `hilclaw/` (a new top-level directory), or must it stay inline in the workflow as in T-0011?

Background of the three questions (facts, not answers):
- (1) `pyproject.toml` pins exactly two dev tools (`pytest==9.1.1`, `ruff==0.16.10`); the owner's HQ-0002 answer made pin changes deliberate tasks. No coverage tool is installed locally or in CI. The planner believes, but has not verified, that coverage.py reports per-function data in its JSON report from 7.6 on; a stock "function coverage" percentage is not part of its text report.
- (2) Neither D12 nor any repository document defines "function coverage".
- (3) T-0011 kept its check inline in the workflow because a script inside `hilclaw/` would need a test file (rule ④) that rule ⑤ forbids, and a new top-level directory is a layout convention nobody has decided (T-0011 `## Result`, "Provisional choices").

When the owner answers on #5 with `HQ-0003`, the driver sets this task back to `TODO` (DRIVER §3-2). The executor then reads the recorded `decision` in `PROCESS/STATE.json` and applies it to every criterion marked "pending HQ-0003" below. If the answer leaves one of the three points open, do not fill the gap: return BLOCKED ("requirement unclear") with the exact remaining question.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12 — rules ① and ⑤ in particular, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §8, §9, §11 row D12
- PROCESS/STATE.json — `humanQuestions[]` entry `HQ-0003`: `question` and, once answered, `decision` (the owner's reply is the requirement of this task; read the linked #5 comment in full: `gh issue view 5 --repo myungjoo/HIL-Claw --comments`)
- PROCESS/PLAN.md — P0.5-3 (this task); P0.5-1, P0.5-2, P0.5-4 for what is not touched
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성"), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- Issue #5, comment "D12 confirmed (owner, 2026-10-05)": `gh api repos/myungjoo/HIL-Claw/issues/comments/5996957869 --jq .body` (items 2, 3, 5); the HQ-0002 answer on pins: `gh api repos/myungjoo/HIL-Claw/issues/comments/6011684226 --jq .body`
- Issue #9 (`gh issue view 9 --repo myungjoo/HIL-Claw --json body,comments`) — the CI gates and "Revision (D10)"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks ("can CI block bad code")
- PROCESS/tasks/T-0010-ci-sh-gate-shellcheck.md and PROCESS/tasks/T-0011-ci-test-presence-check.md — `## Acceptance Criteria` and `## Result`: the conventions of the workflow (first-party actions pinned by full commit SHA, least privilege, a separate job per gate, explicit `shell: bash`, the one-time red/green check with temporary commits and no force push, run evidence format) and why T-0011 stayed inline
- PROCESS/tasks/T-0009-pin-dev-tools-ruff-fixes.md — `## Result`: how an exact pin was added and verified
- PROCESS/tasks/T-0012-data-repo-config.md — `## Result` "Process incident": never put a branch deletion in a command line that also contains another step
- Existing files: `.github/workflows/ci.yml` (whole file, 86 lines: jobs `python` with the 3.11 / 3.14 matrix, `sh`, `test-presence`), `pyproject.toml`, `.gitignore`, `.editorconfig`, `.gitattributes`, `hilclaw/*.py` and `tests/*.py` (what is measured; `tests/test_merge_guard.py`, `tests/test_driver_state.py` and `tests/test_config.py` run some code in subprocesses)

## Acceptance Criteria
Criteria without a mark hold for every answer to HQ-0003. Criteria marked **pending HQ-0003 (n)** take their content from the owner's answer; the alternatives listed there are the ones asked, not a decision. Choices that neither D12 nor the answer fixes (job id and name, Python version of the measuring job, report format) are conventions of this task, provisional: state each with one line of reason in the commit body, the PR body and `## Result`.

Gate behaviour:
- The gate runs in `.github/workflows/ci.yml` on every `pull_request` and every `push` to `main`, as its own check (a separate job; suggested id `coverage`, suggested name `Coverage gate (hilclaw)`), so that the merge guard (`hilclaw/merge_guard.py`) and the executor see it by name. `runs-on: ubuntu-latest`; the same `actions/checkout` and `actions/setup-python` commit SHAs, `persist-credentials: false` and dev-tool install steps as the `python` job (copied, not bumped).
- It measures the whole test suite (`python -m pytest`, all of `tests/`) against **every tracked Python file under `hilclaw/`**, taken from the tree and not from what the tests happened to import: a module that no test imports counts with 0 executed lines and 0 entered functions, it does not drop out of the denominator.
- It fails (non-zero exit of the step) when line coverage is below 80% or when function coverage is below 80%, and also when the test run itself fails or the measurement produces no data. Both thresholds are checked independently; exactly 80% passes. The two numbers 80 appear once each, in one place.
- The log shows both percentages and, when the gate fails, which threshold was missed and the files (for functions: the function names) that are not covered.
- No branch-coverage threshold (D12: "decided once data exists"). Printing branch data is allowed only if the chosen tool gives it without extra configuration; it never fails the gate.
- The existing jobs `python`, `sh` and `test-presence`, the triggers, the top-level `permissions` and the `concurrency` block stay byte-for-byte unchanged. In particular the `python` job keeps running the plain `python -m pytest` on 3.11 and 3.14.
- The measuring job uses one Python version of the matrix; say which and why. If the two versions could give different verdicts near the threshold, record that as a known limit.
- Code run in a child process (`python -m hilclaw.merge_guard`, `python -m hilclaw.driver_state` and similar subprocess tests) need not be measured; if it is not, say so in `## Result` as a known limit together with the lines it leaves uncounted.
- No coverage data file, report or cache is committed; if the tool writes such files into the tree, they are added to `.gitignore` (then `.gitignore` joins `touchesFiles`) or written outside the repository.
- No exclusion list, no `# pragma: no cover`-style markers and no per-file waivers are introduced by this task: `hilclaw/` is measured as it is. If the gate is red on `main`'s own code at the first run, do not lower a threshold or exclude code: return BLOCKED ("requirement unclear") with the measured numbers.

**pending HQ-0003 (1)** — the tool:
- If (a) `coverage`: add exactly one line to the `dev` group of `pyproject.toml`, an exact pin (`coverage==<version>`; `pytest-cov` only if the owner's answer names it), taking the newest release that supports CPython 3.11 and 3.14; record the version and how it was chosen. Upgrade the local tool to the same version before the local runs. Function data: verify on the pinned version that the tool's machine-readable report carries per-function results; if it does not, return BLOCKED with that finding instead of approximating. Any configuration goes into `pyproject.toml` (`[tool.coverage.*]`), not into a new file.
- If (b) stdlib only: no change to `pyproject.toml`; the measurement uses only the standard library and must work on CPython 3.11 and 3.14 (`sys.settrace` plus `threading.settrace`, or an equivalent that exists on 3.11). Tracing must start before any `hilclaw` module is imported, so that module-level lines are counted. The set of executable lines comes from the compiled code objects of each file (`co_lines()`), not from a line count of the source.
- Any other answer: implement what the answer says; if it needs something this file does not cover, return BLOCKED with the question.

**pending HQ-0003 (2)** — the meaning of "function coverage":
- Implement the definition the owner confirms. The definition asked is: functions entered at least once during the test run, divided by all functions defined in `hilclaw/`, where a function is every `def` / `async def` (methods and nested functions counted; lambdas, comprehensions, generator expressions and class bodies not counted).
- State the implemented definition in one sentence in the commit body, the PR body and `## Result`, and make the log line name it (for example `functions: 57/60 entered`).

**pending HQ-0003 (3)** — aggregation and location:
- Thresholds apply to the package total or per module, as answered. With per-module thresholds every module must reach both; say how `hilclaw/__init__.py` (one line, no function) is treated and why a module without functions does not fail the function threshold.
- Location of any gate logic beyond a few workflow lines, as answered: a script file outside `hilclaw/` in the directory the owner names, or inline in the workflow as T-0011 did. Never inside `hilclaw/` (rule ④ would demand a test file that rule ⑤ forbids). A script file is linted by the existing `ruff check .` / `ruff format --check .` and must pass both; it follows `.editorconfig` and CLAUDE.md "코멘트 최소화" (a file header docstring is fine).
- Language of the gate logic: within {Python, POSIX sh} per the CLAUDE.md language policy; one line of reason in the commit body and `## Result`. Workflow glue in bash is acceptable as in T-0010 / T-0011.

Tests:
- **No test file is added or changed.** The gate is a CI workflow plus, at most, a test / CI helper script: tests that target either are forbidden (CLAUDE.md test rule ⑤, DRIVER §5 rule ⑤, the owner's global rule). The two named exceptions (driver `STATE.json` validator, `gh pr merge` guard hook) do not include this gate. No module under `hilclaw/` is touched, so rules ②-④ are vacuous and rule ① is what the gate itself reports.
- The cases a code task would cover with tests are covered by the one-time check below instead: happy (the real tree passes), error (a failing test fails the gate), branch (line threshold and function threshold each fail on their own; an unimported module counts as 0), negative (no data / broken measurement fails the gate instead of passing).

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` exit 0 (623 tests at `9b00c5f`, 5 of them skipped locally because the driver machine has no `clang`). Run the measurement locally as well and record both percentages; local numbers are lower than CI's by the skipped real-clang tests — say by how much. `git ls-files --eol` shows `i/lf` for every changed file; `git status --short` after the runs shows no stray file.
- The PR's first run with the final workflow on the unchanged tree: `gh pr checks <PR> --watch` ends with **five** successful checks — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)` and the new job. Quote the two percentages from the new job's log; they are the first coverage data of the project.
- One-time check that the gate works in both directions (dev-code-review: "can CI block bad code"), done **before** requesting the review, with temporary commits on the PR branch and never a force push. Each step is its own commit and its own CI run:
  1. Function threshold alone: add a temporary module `hilclaw/tmp_t0014_a.py` with many trivial one-line functions and a temporary `tests/test_tmp_t0014_a.py` that imports it and calls none or few of them, sized so that package function coverage falls below 80% while line coverage stays at or above 80% (the `def` lines execute at import). Expect: the new job **fails** naming the function threshold; the other four checks stay green. With per-module thresholds (pending HQ-0003 (3)) the same module shows the per-module failure.
  2. Line threshold: change the temporary module to one function with a long body that the temporary test never calls, sized so that line coverage falls below 80%. Expect: the new job **fails** naming the line threshold.
  3. Unimported module: make the temporary test file import nothing from the temporary module (keep the file, so that `Test presence (hilclaw)` stays green). Expect: the module is listed with 0% and the gate is still red — it did not drop out of the denominator.
  4. Failing test: restore full coverage of the temporary module and add one failing assertion to the temporary test. Expect: the new job **fails** because the test run failed (the `python` job is red too, by design).
  5. Delete every temporary file. Expect: all five checks green. `git diff origin/main --stat` must then list only the files in `touchesFiles`.
  The deliberate red runs do **not** count toward the "CI 3 consecutive failures" BLOCKED counter. The squash-merge removes the temporary commits from `main`. The "no data" direction (the measurement step produced nothing) is shown by reading the step's logic in the review, or by one more temporary commit if it can be provoked without editing the final workflow lines; say which.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Code mode: branch `claude/T-0014-coverage-gate`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0014`; executor commits end with the trailer `Task: T-0014`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (≤ 7 rounds).
- Squash-merge per CLAUDE.md A-13 with `Task: T-0014` as the last line of the PR body, using `gh pr merge <number> --squash --body-file <file>` with a literal PR number. Merge only when every check of the final head is successful. Delete the branch **after** the merge is confirmed, in a separate command.
- Commit body: the owner's answers to HQ-0003 (1)-(3) with the link to the #5 comment; the provisional choices with one line of reason each; the first measured percentages; the language line if a script was written.
- `## Result`: hand the text to the driver in the final report instead of committing this task file on the branch, so that the diff check holds (as T-0008, T-0012 and T-0013 did). `PROCESS/STATE.json`, `PROCESS/journal/` and the `PROCESS/PLAN.md` checkbox belong to the driver. **PLAN P0.5-3 is ticked** when this task is DONE.
- Pushing a file under `.github/workflows/` needs the `workflow` scope on the `gh` / git token (present for T-0003, T-0010, T-0011). If the push is rejected for that reason, return BLOCKED and name the missing scope.
- Size: at most 3 non-test files and about 150 changed lines in the largest variant; below 300 LOC / 5 files. If the answered variant turns out larger, propose a split in Follow-ups and finish the current scope only (DRIVER §5).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.

## Out of Scope
- Deciding any of HQ-0003 (1)-(3), or any dependency beyond the one the owner's answer names.
- A branch-coverage threshold, a per-PR "coverage must not drop" rule, diff coverage, coverage badges, uploading reports to a third-party service, any third-party GitHub action.
- Raising coverage: no change to `hilclaw/` or `tests/` on `main` (if the first measurement is below a threshold, that is a BLOCKED report, see above).
- Measuring code run in subprocesses, C or sh code, or anything outside `hilclaw/`.
- The C gate (rest of P0.5-1), registering the merge guard hook (rest of P0.5-4, an owner action), bumping `pytest`, `ruff` or the action SHAs, changing the `python`, `sh` or `test-presence` jobs.
- Editing CLAUDE.md, the skills, README.md, DRIVER.md, PLAN.md or `ARCHITECTURE/` (document mode, separate changes).

## Follow-ups
- (integrator, document mode) Once the gate is on `main`: CLAUDE.md test rule ① and DRIVER §5 rule ① can name the job as the mechanical check; task files no longer need the hand-run `python -m trace` reachability check; README "로컬 검사" gains the local command. The "CI 미구축" notes are still pending from T-0003 / T-0010 / T-0011.
- (owner, with data) Branch threshold (D12: "once data exists"): this task's first measurement is the first data point.
- (decision to revisit) Whether subprocess-run code should be measured, and whether the gate should run on both matrix versions.
- (P0.5-1, C gate) Coverage of C code is not covered by D12's wording ("the tool package" measured here is its Python part); raise it when the first C file lands in `hilclaw/`.
- (driver, D15 migration) With this gate, CI on `main` carries five checks; the remaining precondition of the D15 migration is still the owner's hook registration (P0.5-4).

## Result
